# Base-R checks for the S1 pin. Run inside the pinned image:
#   Rscript tests/test_pin.R
# Host R does not satisfy CALC-REQ-5; this file is the pin, not a KAT.

args_root <- Sys.getenv("PIN_TEST_ROOT", "")
root <- if (nzchar(args_root)) args_root else normalizePath("..", mustWork = FALSE)
# When invoked as `Rscript tests/test_pin.R` from services/r-calculator, cwd is that dir.
if (!file.exists(file.path(root, "R", "pin.R"))) {
  root <- getwd()
}

source(file.path(root, "R", "request_timeout.R"))
source(file.path(root, "R", "pin.R"))

stopifnot(identical(REQUEST_TIMEOUT_SECONDS, 50))
stopifnot(isTRUE(legacy_dose_response_path("/fit")))
stopifnot(isTRUE(legacy_dose_response_path("/svg/full")))
stopifnot(!isTRUE(legacy_dose_response_path("/health")))
stopifnot(!isTRUE(legacy_dose_response_path("/calculations")))

vector_hash <- lock_hash_hex("ab", "cd", "ef")
stopifnot(identical(
  vector_hash,
  "911f0cdd0689cf114775478c242760865d67d1816e3586fbc6529f24fbb000a2"
))
stopifnot(identical(lock_hash_hex("ab", "cd", "ef"), vector_hash))

preimage_file <- tempfile()
writeBin(charToRaw("ab\ncd\nef"), preimage_file)
stopifnot(identical(sha256_file(preimage_file), vector_hash))
unlink(preimage_file)

one <- charToRaw("version-a")
two <- charToRaw("version-b")
stopifnot(!identical(sha256_text(rawToChar(one)), sha256_text(rawToChar(two))))

writable <- c(
  "36 35 98:0 / / rw,relatime - overlay overlay rw"
)
readonly <- c(
  "36 35 98:0 / / ro,relatime - overlay overlay ro",
  "40 36 0:40 / /tmp rw,nosuid,nodev - tmpfs tmpfs rw,mode=1777"
)
stopifnot(!isTRUE(root_read_only_from_lines(writable)))
stopifnot(isTRUE(root_read_only_from_lines(readonly)))
stopifnot(isTRUE(scratch_tmpfs_from_lines(readonly, "/tmp")))
stopifnot(!isTRUE(scratch_tmpfs_from_lines(readonly, "/var")))
stopifnot(!isTRUE(scratch_tmpfs_from_lines(writable, "/tmp")))

stopifnot(!isTRUE(cgroup_value_limited("max 100000", cpu = TRUE)))
stopifnot(isTRUE(cgroup_value_limited("100000 100000", cpu = TRUE)))
stopifnot(!isTRUE(cgroup_value_limited("max", cpu = FALSE)))
stopifnot(isTRUE(cgroup_value_limited("1073741824", cpu = FALSE)))
stopifnot(!isTRUE(cgroup_value_limited("", cpu = FALSE)))

stopifnot(isTRUE(forbidden_env_absent_from_names(c("HOME", "R_IMAGE_DIGEST", "PATH"))))
stopifnot(!isTRUE(forbidden_env_absent_from_names(c("HOME", "DATABASE_URL"))))
stopifnot(!isTRUE(forbidden_env_absent_from_names(c("SECRET_KEY"))))
stopifnot(!isTRUE(forbidden_env_absent_from_names(c("JWT_SECRET"))))
stopifnot(isTRUE(forbidden_env_absent_from_names(c("R_BASE_DIGEST"))))

boxed <- sandbox_from_measurements(
  uid = "1000",
  mountinfo_lines = readonly,
  scratch = "/tmp",
  cpu_text = "100000 100000",
  memory_text = "1073741824",
  pids_text = "256",
  env_names = c("HOME", "PATH", "R_IMAGE_DIGEST"),
  egress_blocked = TRUE
)
stopifnot(identical(boxed$uid, 1000L))
stopifnot(isTRUE(boxed$root_read_only))
stopifnot(isTRUE(boxed$scratch_tmpfs))
stopifnot(isTRUE(boxed$egress_blocked))
stopifnot(isTRUE(boxed$cpu_limited))
stopifnot(isTRUE(boxed$memory_limited))
stopifnot(isTRUE(boxed$pids_limited))
stopifnot(isTRUE(boxed$forbidden_env_absent))

# setTimeLimit stops R evaluation. A pure C sleep is not the check.
err <- tryCatch(
  run_with_wall_timeout(
    {
      start <- proc.time()[[3]]
      repeat {
        if (proc.time()[[3]] - start > 3) break
      }
      "not-stopped"
    },
    1
  ),
  error = function(e) e
)
stopifnot(inherits(err, "error"))
stopifnot(isTRUE(is_r_timeout(err)))

# The helper above calls the expression directly. The regression below goes
# through plumber. Wrapping plumber::forward() does not: forward() only sets
# a flag, setTimeLimit is cleared when the filter returns, and the handler
# then runs to completion. This request would return finished=TRUE under that
# bug. A short limit keeps the passing run fast. The product value stays 50.
library(plumber)
library(jsonlite)

pin_make_req <- function(verb, path, body = "") {
  req <- new.env(parent = emptyenv())
  req$REQUEST_METHOD <- verb
  req$PATH_INFO <- path
  req$QUERY_STRING <- ""
  if (is.character(body)) {
    body <- charToRaw(body)
  }
  req$rook.input <- list(
    read_lines = function() rawToChar(body),
    read = function() body,
    rewind = function() length(body)
  )
  req$bodyRaw <- body
  req
}

pin_call <- function(pr, verb, path, body = "") {
  pr$call(pin_make_req(verb, path, body))
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

busy_for <- function(seconds) {
  start <- proc.time()[[3]]
  repeat {
    if (proc.time()[[3]] - start > seconds) {
      break
    }
  }
  list(finished = TRUE)
}

find_endpoint <- function(pr, path) {
  found <- NULL
  ends <- pr$endpoints
  for (i in seq_along(ends)) {
    group <- ends[[i]]
    for (j in seq_along(group)) {
      if (identical(group[[j]]$path, path)) {
        found <- group[[j]]
      }
    }
  }
  found
}

around_hooks <- function(endpoint) {
  recorded <- endpoint$.__enclos_env__$private$hooks[["aroundexec"]]
  if (is.null(recorded)) {
    return(list())
  }
  if (is.function(recorded)) {
    return(list(recorded))
  }
  as.list(recorded)
}

# Test router only. These paths are not product routes.
# /fit and /svg/full here exist so the skip can be observed.
limit_s <- 1
overrun_s <- 6
legacy_s <- 2
pr_test <- plumber::pr()
pr_test$handle(
  "GET",
  "/slow",
  function() busy_for(overrun_s),
  serializer = plumber::serializer_unboxed_json()
)
pr_test$handle(
  "GET",
  "/who",
  function(req) list(path = req$PATH_INFO),
  serializer = plumber::serializer_unboxed_json()
)
pr_test$handle(
  "GET",
  "/boom",
  function() stop("nope"),
  serializer = plumber::serializer_unboxed_json()
)
pr_test$handle(
  "POST",
  "/fit",
  function() busy_for(legacy_s),
  serializer = plumber::serializer_unboxed_json()
)
pr_test$handle(
  "POST",
  "/svg/full",
  function() busy_for(legacy_s),
  serializer = plumber::serializer_unboxed_json()
)
install_calculation_timeout(pr_test, limit_s)

slow_started <- proc.time()[[3]]
slow <- pin_call(pr_test, "GET", "/slow")
slow_elapsed <- proc.time()[[3]] - slow_started
slow_body <- jsonlite::fromJSON(response_text(slow))
if (!identical(as.integer(slow$status), 504L)) {
  stop("slow route status ", slow$status, " body ", response_text(slow))
}
if (!identical(unname(slow_body$code), "r_timeout")) {
  stop("slow route was not an R timeout: ", response_text(slow))
}
if (isTRUE(slow_body$finished)) {
  stop("slow route ran to completion")
}
if (slow_elapsed >= overrun_s - 1) {
  stop("slow route was not stopped early: ", slow_elapsed, " s")
}
if (!grepl("1 s", slow_body$detail, fixed = TRUE)) {
  stop("timeout detail did not use the test limit: ", slow_body$detail)
}

who <- jsonlite::fromJSON(response_text(pin_call(pr_test, "GET", "/who")))
stopifnot(identical(unname(who$path), "/who"))

boom <- pin_call(pr_test, "GET", "/boom")
stopifnot(identical(as.integer(boom$status), 500L))
stopifnot(!grepl("r_timeout", response_text(boom), fixed = TRUE))

expect_legacy_finishes <- function(verb, path) {
  started <- proc.time()[[3]]
  res <- pin_call(pr_test, verb, path)
  elapsed <- proc.time()[[3]] - started
  parsed <- jsonlite::fromJSON(response_text(res))
  if (!identical(as.integer(res$status), 200L) || !isTRUE(parsed$finished)) {
    stop(path, " did not finish: ", res$status, " ", response_text(res))
  }
  if (elapsed < legacy_s - 0.3) {
    stop(path, " returned before its own work finished: ", elapsed, " s")
  }
  if (!is.null(parsed$code) && identical(unname(parsed$code), "r_timeout")) {
    stop(path, " was stopped by the calculation timeout")
  }
}
expect_legacy_finishes("POST", "/fit")
expect_legacy_finishes("POST", "/svg/full")

stopifnot(length(around_hooks(find_endpoint(pr_test, "/slow"))) == 1L)
stopifnot(length(around_hooks(find_endpoint(pr_test, "/fit"))) == 0L)
stopifnot(length(around_hooks(find_endpoint(pr_test, "/svg/full"))) == 0L)

# The shipped router installs the same hook at the production limit.
shipped <- plumber::plumb(file.path(root, "plumber.R"))
health_ep <- find_endpoint(shipped, "/health")
fit_ep <- find_endpoint(shipped, "/fit")
svg_ep <- find_endpoint(shipped, "/svg/full")
stopifnot(!is.null(health_ep), !is.null(fit_ep), !is.null(svg_ep))
health_hooks <- around_hooks(health_ep)
stopifnot(length(health_hooks) == 1L)
stopifnot(identical(environment(health_hooks[[1L]])$limit, REQUEST_TIMEOUT_SECONDS))
stopifnot(length(around_hooks(fit_ep)) == 0L)
stopifnot(length(around_hooks(svg_ep)) == 0L)

health <- pin_call(shipped, "GET", "/health")
health_body <- jsonlite::fromJSON(response_text(health))
if (!identical(as.integer(health$status), 200L)) {
  stop("health status ", health$status, " body ", response_text(health))
}
stopifnot(identical(unname(health_body$status), "ok"))

cat("test_pin.R ok\n")
