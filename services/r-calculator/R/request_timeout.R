# Per-request wall-clock timeout for calculation calls (CALC-REQ-4a, OQ-CALC-16).
# The Spec default is 50 s. The shipped profiled-CI bound in fit.R (5 s) is not
# this timeout. Dose-response POST /fit and POST /svg/full do not use it.
#
# plumber::forward() only sets a flag. The router runs the endpoint later.
# A filter that does run_with_wall_timeout(plumber::forward(), ...) therefore
# clears setTimeLimit on exit, before the handler runs, and no request stops.
# The limit is an aroundexec hook: plumber invokes that hook with the endpoint
# function as .next, so setTimeLimit stays in force while the handler runs and
# is cleared after the handler returns. Attempt rows for r_timeout are S9.

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

# `.next` is plumber's continuation. It runs the endpoint (or the next
# aroundexec hook). Arguments are forwarded so handlers that take `req`
# still receive it. A timeout returns the PlumberResponse itself so the
# serializer cannot box `code` into a JSON array.
calculation_timeout_around <- function(seconds) {
  limit <- seconds
  function(req, res, .next, ...) {
    forwarded <- list(...)
    invoke <- function() {
      do.call(.next, c(list(req = req, res = res), forwarded))
    }
    if (isTRUE(legacy_dose_response_path(req$PATH_INFO))) {
      return(invoke())
    }
    tryCatch(
      run_with_wall_timeout(invoke(), limit),
      error = function(e) {
        if (is_r_timeout(e)) {
          detail <- paste0("R stopped the request after ", limit, " s")
          res$status <- 504L
          res$setHeader("Content-Type", "application/json")
          res$body <- paste0(
            '{"code":"r_timeout","detail":"',
            detail,
            '"}'
          )
          return(res)
        }
        stop(e)
      }
    )
  }
}

#' Register the wall-clock limit on endpoint execution.
#'
#' `seconds` is `REQUEST_TIMEOUT_SECONDS` in the service. A test may pass a
#' shorter limit. `/fit` and `/svg/full` do not get the hook, so dose-response
#' routes keep their existing timing, including the 5 s profiled-CI bound.
install_calculation_timeout <- function(pr, seconds = REQUEST_TIMEOUT_SECONDS) {
  if (length(seconds) != 1L || !is.numeric(seconds) || !is.finite(seconds) || seconds <= 0) {
    stop("calculation timeout seconds must be one positive number")
  }
  handler <- calculation_timeout_around(seconds)
  ends <- pr$endpoints
  for (i in seq_along(ends)) {
    group <- ends[[i]]
    for (j in seq_along(group)) {
      endpoint <- group[[j]]
      if (isTRUE(legacy_dose_response_path(endpoint$path))) {
        next
      }
      endpoint$registerHook("aroundexec", handler)
    }
  }
  invisible(pr)
}
