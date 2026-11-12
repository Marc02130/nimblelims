# Per-request wall-clock timeout for calculation calls (CALC-REQ-4a, OQ-CALC-16).
# The Spec default is 50 s. The shipped profiled-CI bound in fit.R (5 s) is not
# this timeout. Dose-response POST /fit and POST /svg/full do not use it.

REQUEST_TIMEOUT_SECONDS <- 50

legacy_dose_response_path <- function(path) {
  isTRUE(path %in% c("/fit", "/svg/full"))
}

is_r_timeout <- function(condition) {
  if (is.null(condition)) {
    return(FALSE)
  }
  msg <- tryCatch(conditionMessage(condition), error = function(e) "")
  isTRUE(grepl("elapsed time limit", msg, fixed = TRUE))
}

#' Evaluate expr under a wall-clock limit.
#'
#' R evaluates `expr` lazily, so the limit is in force while it runs.
#' On expiry the signaled condition matches `is_r_timeout`.
run_with_wall_timeout <- function(expr, seconds) {
  setTimeLimit(elapsed = seconds, transient = TRUE)
  on.exit(setTimeLimit(elapsed = Inf, transient = TRUE), add = TRUE)
  expr
}
