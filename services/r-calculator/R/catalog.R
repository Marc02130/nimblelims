# R-side catalog functions (CALC-REQ-8, 9, 12, 17, 24, 37).
#
# One route per function version. R does only the fits and the curve
# inversions. Every gate (missing data, level counts, the in-range check
# before an inversion, the non-positive log check) runs in the backend first;
# the checks repeated here only refuse or stop, they never substitute a value.
#
# Inputs are decimal strings in the JSON number grammar. A JSON number, an
# unknown field (for example `model`), or a missing field is refused with
# HTTP 400 and code `invalid_input`. Nothing falls back to a default model.
# Outputs are shortest round-trip strings (serialise.R). A NaN, Inf, -Inf, or
# NA output stops with `r_non_finite` and returns no number. A stage stop is
# HTTP 200 with `stop` and `detail`, so the backend can tell it from an error.

CATALOG_DECIMAL_RE <- "^-?(0|[1-9][0-9]*)([.][0-9]+)?([eE][+-]?[0-9]+)?$"

catalog_refuse <- function(detail) {
  stop(structure(
    class = c("catalog_refusal", "error", "condition"),
    list(message = detail, call = NULL)
  ))
}

catalog_stop <- function(code, detail) {
  list(stop = code, detail = detail)
}

# One decimal string to the nearest double. jsonlite parses with the C library
# strtod, which is correctly rounded, so the double matches the backend's
# reading of the same string.
parse_decimal_string <- function(value, name) {
  if (!is.character(value) || length(value) != 1L || is.na(value)) {
    catalog_refuse(paste0(name, " must be a decimal string"))
  }
  if (!grepl(CATALOG_DECIMAL_RE, value, perl = TRUE)) {
    catalog_refuse(paste0(name, " is not a decimal string"))
  }
  parsed <- jsonlite::parse_json(paste0("[", value, "]"), simplifyVector = TRUE)
  parsed <- as.double(parsed)
  if (length(parsed) != 1L || !is.finite(parsed)) {
    catalog_refuse(paste0(name, " is not a finite decimal"))
  }
  parsed
}

parse_decimal_array <- function(values, name) {
  if (!is.list(values) || !is.null(names(values))) {
    catalog_refuse(paste0(name, " must be an array of decimal strings"))
  }
  vapply(
    seq_along(values),
    function(i) parse_decimal_string(values[[i]], paste0(name, "[", i, "]")),
    numeric(1)
  )
}

# Shortest round-trip strings for named outputs, or the r_non_finite stop.
catalog_outputs <- function(values) {
  for (name in names(values)) {
    value <- values[[name]]
    if (!is.numeric(value) || length(value) != 1L || !is.finite(value)) {
      return(catalog_stop("r_non_finite", paste0("R output ", name, " is not finite")))
    }
  }
  out <- lapply(values, shortest_round_trip)
  names(out) <- names(values)
  out
}

catalog_body <- function(req, fields) {
  text <- req$postBody
  if (is.null(text) || !nzchar(text)) {
    catalog_refuse("body must be a JSON object")
  }
  body <- tryCatch(
    jsonlite::fromJSON(text, simplifyVector = FALSE),
    error = function(e) NULL
  )
  if (!is.list(body) || length(body) == 0L || is.null(names(body))) {
    catalog_refuse("body must be a JSON object")
  }
  extra <- setdiff(names(body), fields)
  if (length(extra) > 0L) {
    catalog_refuse(paste0("unknown field: ", paste(sort(extra), collapse = ", ")))
  }
  missing <- setdiff(fields, names(body))
  if (length(missing) > 0L) {
    catalog_refuse(paste0("missing field: ", paste(sort(missing), collapse = ", ")))
  }
  body
}

# Wrap one catalog function as a plumber handler. A refusal is HTTP 400.
catalog_route <- function(req, res, fields, compute) {
  tryCatch(
    compute(catalog_body(req, fields)),
    catalog_refusal = function(e) {
      res$status <- 400L
      list(code = "invalid_input", detail = conditionMessage(e))
    }
  )
}

# fit_4pl v1: four-parameter log-logistic, drc::LL.4,
#   f(x) = c + (d - c) / (1 + exp(b * (log(x) - log(e))))
# bottom = c, top = d, slope = b, inflection = e. No weights and no parameter
# bounds are passed, so drm fits by ordinary least squares on the points
# received. r_squared = 1 - SS_res / SS_tot over those points.
catalog_fit_4pl <- function(body) {
  conc <- parse_decimal_array(body$concentration, "concentration")
  resp <- parse_decimal_array(body$response, "response")
  if (length(conc) != length(resp)) {
    catalog_refuse("concentration and response have different lengths")
  }
  if (any(conc < 0)) {
    catalog_refuse("a calibrator concentration is negative")
  }
  if (length(unique(conc)) < 4L) {
    return(catalog_stop("curve_not_fitted", "fewer than four calibrator levels"))
  }
  fit <- tryCatch(
    suppressWarnings(drc::drm(
      resp ~ conc,
      fct = drc::LL.4(names = c("b", "c", "d", "e"))
    )),
    error = function(e) e
  )
  if (inherits(fit, "error")) {
    return(catalog_stop("curve_not_fitted", paste0("the fit did not converge: ", conditionMessage(fit))))
  }
  params <- stats::coef(fit)
  ss_res <- sum(stats::residuals(fit)^2)
  ss_tot <- sum((resp - mean(resp))^2)
  catalog_outputs(list(
    bottom = unname(params[["c:(Intercept)"]]),
    top = unname(params[["d:(Intercept)"]]),
    slope = unname(params[["b:(Intercept)"]]),
    inflection = unname(params[["e:(Intercept)"]]),
    r_squared = 1 - ss_res / ss_tot
  ))
}

# inverse_4pl v1: x = e * ((d - c) / (y - c) - 1)^(1 / b).
catalog_inverse_4pl <- function(body) {
  c_ <- parse_decimal_string(body$bottom, "bottom")
  d_ <- parse_decimal_string(body$top, "top")
  b_ <- parse_decimal_string(body$slope, "slope")
  e_ <- parse_decimal_string(body$inflection, "inflection")
  y <- parse_decimal_string(body$response, "response")
  if (b_ == 0) {
    catalog_refuse("slope is 0; the curve has no inverse")
  }
  x <- e_ * ((d_ - c_) / (y - c_) - 1)^(1 / b_)
  catalog_outputs(list(concentration = x))
}

# fit_loglog_linear v1: lm(log10(y) ~ log10(x)); r is the Pearson correlation
# of log10(x) and log10(y).
catalog_fit_loglog_linear <- function(body) {
  x <- parse_decimal_array(body$x, "x")
  y <- parse_decimal_array(body$y, "y")
  if (length(x) != length(y)) {
    catalog_refuse("x and y have different lengths")
  }
  if (length(x) == 0L) {
    catalog_refuse("x and y are empty")
  }
  if (any(x <= 0) || any(y <= 0)) {
    return(catalog_stop("non_positive_log_input", "an x or y is not greater than 0"))
  }
  lx <- log10(x)
  ly <- log10(y)
  fit <- stats::lm(ly ~ lx)
  params <- stats::coef(fit)
  r <- suppressWarnings(stats::cor(lx, ly))
  catalog_outputs(list(
    slope = unname(params[["lx"]]),
    intercept = unname(params[["(Intercept)"]]),
    r = r
  ))
}

# inverse_loglog_linear v1: x = 10^((log10(y) - intercept) / slope).
catalog_inverse_loglog_linear <- function(body) {
  slope <- parse_decimal_string(body$slope, "slope")
  intercept <- parse_decimal_string(body$intercept, "intercept")
  y <- parse_decimal_string(body$y, "y")
  if (slope == 0) {
    catalog_refuse("slope is 0; the fit has no inverse")
  }
  if (y <= 0) {
    return(catalog_stop("non_positive_log_input", "y is not greater than 0"))
  }
  x <- 10^((log10(y) - intercept) / slope)
  catalog_outputs(list(x = x))
}

CATALOG_ROUTES <- list(
  "/catalog/fit_4pl/v1" = list(
    fields = c("concentration", "response"),
    compute = catalog_fit_4pl
  ),
  "/catalog/inverse_4pl/v1" = list(
    fields = c("bottom", "top", "slope", "inflection", "response"),
    compute = catalog_inverse_4pl
  ),
  "/catalog/fit_loglog_linear/v1" = list(
    fields = c("x", "y"),
    compute = catalog_fit_loglog_linear
  ),
  "/catalog/inverse_loglog_linear/v1" = list(
    fields = c("slope", "intercept", "y"),
    compute = catalog_inverse_loglog_linear
  )
)
