# Unit tests for the R-side catalog routes (calculations S3). Not KATs: the
# data below is generated here from stated parameters, and no case is a
# released-version KAT or carries a source citation. Run inside the pinned
# image:
#   docker run --rm --network none --entrypoint Rscript <image> tests/test_catalog.R

library(plumber)
library(jsonlite)

root <- getwd()
if (!file.exists(file.path(root, "plumber.R"))) {
  stop("run from services/r-calculator (the image WORKDIR)")
}

in_pinned_image <- function() {
  base <- Sys.getenv("R_BASE_DIGEST", "")
  tree <- Sys.getenv("R_TREE", "")
  isTRUE(file.exists("/app/renv.lock")) &&
    identical(normalizePath(root), "/app") &&
    grepl("^[0-9a-f]{64}$", base) &&
    grepl("^[0-9a-f]{40}$|^[0-9a-f]{64}$", tree)
}
if (!in_pinned_image()) {
  stop("not inside the pinned image: a host-R run of the catalog route test does not count")
}

make_req <- function(verb, path, body = "") {
  req <- new.env(parent = emptyenv())
  req$REQUEST_METHOD <- verb
  req$PATH_INFO <- path
  req$QUERY_STRING <- ""
  raw <- charToRaw(body)
  req$rook.input <- list(
    read_lines = function() rawToChar(raw),
    read = function() raw,
    rewind = function() length(raw)
  )
  req$bodyRaw <- raw
  req
}

response_text <- function(res) {
  body <- res$body
  if (is.null(body)) {
    return("")
  }
  if (is.raw(body)) {
    return(rawToChar(body))
  }
  paste(as.character(body), collapse = "\n")
}

pr <- plumber::plumb(file.path(root, "plumber.R"))

post <- function(path, body) {
  text <- if (is.character(body)) body else jsonlite::toJSON(body, auto_unbox = TRUE)
  res <- pr$call(make_req("POST", path, as.character(text)))
  list(
    status = as.integer(res$status),
    body = jsonlite::fromJSON(response_text(res), simplifyVector = FALSE)
  )
}

expect_ok <- function(out, label) {
  if (!identical(out$status, 200L)) {
    stop(label, ": status ", out$status, " ", jsonlite::toJSON(out$body, auto_unbox = TRUE))
  }
  if (!is.null(out$body$stop)) {
    stop(label, ": unexpected stop ", out$body$stop, " ", out$body$detail)
  }
}

expect_stop <- function(out, code, label) {
  if (!identical(out$status, 200L) || !identical(out$body$stop, code)) {
    stop(label, ": expected stop ", code, ", got ", out$status, " ",
         jsonlite::toJSON(out$body, auto_unbox = TRUE))
  }
  stopifnot(is.character(out$body$detail))
}

expect_refused <- function(out, pattern, label) {
  if (!identical(out$status, 400L) || !identical(out$body$code, "invalid_input")) {
    stop(label, ": expected refusal, got ", out$status, " ",
         jsonlite::toJSON(out$body, auto_unbox = TRUE))
  }
  if (!grepl(pattern, out$body$detail, fixed = TRUE)) {
    stop(label, ": refusal detail ", out$body$detail, " lacks ", pattern)
  }
}

# Every numeric output is a JSON string that parses to a finite double.
num <- function(text) {
  stopifnot(is.character(text), length(text) == 1L)
  stopifnot(grepl(CATALOG_DECIMAL_RE, text, perl = TRUE))
  as.numeric(text)
}

near <- function(got, want, rel) {
  abs(got - want) <= rel * max(abs(want), 1e-300)
}

strs <- function(x) lapply(x, shortest_round_trip)

# ---- fit_4pl / inverse_4pl -------------------------------------------------
# Responses generated from LL.4 with b = 1.5, c = 0.05, d = 2.5, e = 40.
b0 <- 1.5; c0 <- 0.05; d0 <- 2.5; e0 <- 40
ll4 <- function(x) c0 + (d0 - c0) / (1 + exp(b0 * (log(x) - log(e0))))
conc <- c(5, 10, 20, 40, 80, 160, 320)
fit_body <- list(concentration = strs(conc), response = strs(ll4(conc)))

fit <- post("/catalog/fit_4pl/v1", fit_body)
expect_ok(fit, "fit_4pl")
# drc's default convergence tolerance leaves about 5e-6 relative error on exact data.
stopifnot(near(num(fit$body$slope), b0, 1e-4))
stopifnot(near(num(fit$body$bottom), c0, 1e-4))
stopifnot(near(num(fit$body$top), d0, 1e-4))
stopifnot(near(num(fit$body$inflection), e0, 1e-4))
stopifnot(num(fit$body$r_squared) > 1 - 1e-9)
stopifnot(setequal(names(fit$body), c("bottom", "top", "slope", "inflection", "r_squared")))

# Three levels (two replicates each) stop with curve_not_fitted.
three <- c(10, 10, 40, 40, 160, 160)
expect_stop(
  post("/catalog/fit_4pl/v1", list(concentration = strs(three), response = strs(ll4(three)))),
  "curve_not_fitted",
  "fit_4pl three levels"
)

# Unknown model name, unknown field, or a JSON number is refused. No LL.4 fallback runs.
with_model <- fit_body
with_model$model <- "5PL_unknown"
expect_refused(post("/catalog/fit_4pl/v1", with_model), "unknown field: model", "model field")
with_code <- fit_body
with_code$code <- "system('id')"
expect_refused(post("/catalog/fit_4pl/v1", with_code), "unknown field: code", "code field")
as_numbers <- list(concentration = as.list(conc), response = as.list(ll4(conc)))
expect_refused(post("/catalog/fit_4pl/v1", as_numbers), "must be a decimal string", "JSON numbers")
expect_refused(post("/catalog/fit_4pl/v1", list(concentration = strs(conc))), "missing field: response", "missing field")
expect_refused(post("/catalog/fit_4pl/v1", "not json"), "JSON object", "bad JSON")
bad_text <- fit_body
bad_text$response[[1]] <- "NaN"
expect_refused(post("/catalog/fit_4pl/v1", bad_text), "not a decimal string", "NaN text")
neg <- fit_body
neg$concentration[[1]] <- "-5"
expect_refused(post("/catalog/fit_4pl/v1", neg), "negative", "negative concentration")

# A path that is not a catalog route is not served.
for (path in c("/catalog/fit_5pl/v1", "/catalog/fit_4pl/v2", "/catalog/run", "/run-r")) {
  res <- pr$call(make_req("POST", path, jsonlite::toJSON(fit_body, auto_unbox = TRUE)))
  if (!identical(as.integer(res$status), 404L)) {
    stop(path, " was served: ", res$status)
  }
}

inv_body <- list(
  bottom = shortest_round_trip(c0),
  top = shortest_round_trip(d0),
  slope = shortest_round_trip(b0),
  inflection = shortest_round_trip(e0),
  response = shortest_round_trip(ll4(30))
)
inv <- post("/catalog/inverse_4pl/v1", inv_body)
expect_ok(inv, "inverse_4pl")
stopifnot(near(num(inv$body$concentration), 30, 1e-12))

# A response past the top asymptote has no inverse: R output is NaN.
past <- inv_body
past$response <- "3"
expect_stop(post("/catalog/inverse_4pl/v1", past), "r_non_finite", "inverse_4pl NaN")
with_model <- inv_body
with_model$model <- "LL.4"
expect_refused(post("/catalog/inverse_4pl/v1", with_model), "unknown field: model", "inverse model")

# ---- fit_loglog_linear / inverse_loglog_linear -----------------------------
# y = 10^0.5 * x^-0.8, so log10(y) = 0.5 - 0.8 log10(x) and r = -1.
x <- c(0.005, 0.05, 0.5, 5)
y <- 10^(0.5 - 0.8 * log10(x))
ll <- post("/catalog/fit_loglog_linear/v1", list(x = strs(x), y = strs(y)))
expect_ok(ll, "fit_loglog_linear")
stopifnot(near(num(ll$body$slope), -0.8, 1e-12))
stopifnot(near(num(ll$body$intercept), 0.5, 1e-12))
stopifnot(near(num(ll$body$r), -1, 1e-12))
stopifnot(setequal(names(ll$body), c("slope", "intercept", "r")))

up <- post("/catalog/fit_loglog_linear/v1", list(x = strs(x), y = strs(2 * x^1.25)))
expect_ok(up, "fit_loglog_linear positive")
stopifnot(num(up$body$slope) > 0)

zero_x <- list(x = strs(c(0, x[-1])), y = strs(y))
expect_stop(post("/catalog/fit_loglog_linear/v1", zero_x), "non_positive_log_input", "x = 0")
zero_y <- list(x = strs(x), y = strs(c(0, y[-1])))
expect_stop(post("/catalog/fit_loglog_linear/v1", zero_y), "non_positive_log_input", "y = 0")

# One point: lm gives no slope and cor gives NA, so the stage stops.
expect_stop(
  post("/catalog/fit_loglog_linear/v1", list(x = strs(x[1]), y = strs(y[1]))),
  "r_non_finite",
  "one point"
)
with_model <- list(x = strs(x), y = strs(y), model = "loglog")
expect_refused(post("/catalog/fit_loglog_linear/v1", with_model), "unknown field: model", "loglog model")

il <- post("/catalog/inverse_loglog_linear/v1", list(
  slope = "-0.8", intercept = "0.5", y = shortest_round_trip(10^(0.5 - 0.8 * log10(0.2)))
))
expect_ok(il, "inverse_loglog_linear")
stopifnot(near(num(il$body$x), 0.2, 1e-12))
expect_stop(
  post("/catalog/inverse_loglog_linear/v1", list(slope = "-0.8", intercept = "0.5", y = "0")),
  "non_positive_log_input",
  "inverse y = 0"
)
expect_refused(
  post("/catalog/inverse_loglog_linear/v1", list(slope = "0", intercept = "0.5", y = "2")),
  "slope is 0",
  "inverse slope 0"
)
zero_b <- inv_body
zero_b$slope <- "0"
expect_refused(post("/catalog/inverse_4pl/v1", zero_b), "slope is 0", "inverse_4pl slope 0")
# A result too large for a double is not finite: r_non_finite, no number.
expect_stop(
  post("/catalog/inverse_loglog_linear/v1", list(slope = "0.001", intercept = "0", y = "10")),
  "r_non_finite",
  "inverse overflow"
)

# ---- routes: timeout hook, no generic route, dose-response unchanged --------
find_endpoint <- function(router, path) {
  for (group in router$endpoints) {
    for (endpoint in group) {
      if (identical(endpoint$path, path)) {
        return(endpoint)
      }
    }
  }
  NULL
}
around_hooks <- function(endpoint) {
  recorded <- endpoint$.__enclos_env__$private$hooks[["aroundexec"]]
  if (is.null(recorded)) list() else if (is.function(recorded)) list(recorded) else as.list(recorded)
}
for (path in names(CATALOG_ROUTES)) {
  endpoint <- find_endpoint(pr, path)
  stopifnot(!is.null(endpoint))
  stopifnot(length(around_hooks(endpoint)) == 1L)
}
stopifnot(length(around_hooks(find_endpoint(pr, "/fit"))) == 0L)
stopifnot(length(around_hooks(find_endpoint(pr, "/svg/full"))) == 0L)

paths <- character(0)
for (group in pr$endpoints) {
  for (endpoint in group) {
    paths <- c(paths, endpoint$path)
  }
}
expected_paths <- c(
  "/health", "/fit", "/svg/full", "/kat-harness/round-trip", names(CATALOG_ROUTES)
)
if (!setequal(paths, expected_paths)) {
  stop("unexpected route set: ", paste(sort(paths), collapse = ", "))
}

dose_points <- lapply(seq_along(c(10000, 3333, 1111, 370, 123, 41, 14, 4.6)), function(i) {
  list(
    conc = c(10000, 3333, 1111, 370, 123, 41, 14, 4.6)[[i]],
    response = c(97.5, 95.1, 87.3, 69.4, 45.2, 20.1, 8.3, 3.1)[[i]],
    point_id = paste0("p", i)
  )
})
dose <- post("/fit", list(
  compounds = list(list(sample_id = "s1", points = dose_points, model = "4PL")),
  config = list(r_squared_threshold = 0.9, inactive_threshold = 20)
))
stopifnot(identical(dose$status, 200L))
stopifnot(isTRUE(dose$body[[1]]$success))
svg <- post("/svg/full", list(points = dose_points, model = "4PL"))
stopifnot(identical(svg$status, 200L))
stopifnot(grepl("<svg", svg$body$svg, fixed = TRUE))

cat("test_catalog.R ok\n")
