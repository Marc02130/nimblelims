library(drc)
library(MASS)
library(R.utils)

#' Fit a dose-response curve using drc::drm().
#'
#' @param conc     Numeric vector of concentrations (pre-normalized, same units as template).
#' @param response Numeric vector of responses (% inhibition, 0-100 scale).
#' @param model    One of "4PL", "3PL_FB", "3PL_FT", "5PL".
#' @param constraints Named list with optional bottom/top min/max constraints.
#'   e.g. list(bottom=list(min=0, max=20), top=list(min=80, max=120))
#' @return Named list with success, potency, hill_slope, bottom, top,
#'   r_squared, ci_low_95, ci_high_95, ci_method. On failure: success=FALSE, error=message.
fit_compound <- function(conc, response, model = "4PL", constraints = list()) {
  if (length(conc) < 4) {
    return(list(
      success = FALSE,
      error   = paste0("Insufficient data points: ", length(conc), " (minimum 4 required)")
    ))
  }

  fct <- switch(model,
    "4PL"    = LL.4(),
    "3PL_FB" = LL.3(),
    "3PL_FT" = LL.3u(),
    "5PL"    = LL.5(),
    LL.4()
  )

  # Translate parameter_constraints → drm lowerl/upperl vectors
  # drm parameter order for LL.4: b (hill_slope), c (bottom), d (top), e (IC50/EC50)
  lowerl <- c(-Inf, -Inf, -Inf, 0)   # IC50 must be positive
  upperl <- c( Inf,  Inf,  Inf, Inf)
  if (!is.null(constraints$bottom$min)) lowerl[2] <- constraints$bottom$min
  if (!is.null(constraints$bottom$max)) upperl[2] <- constraints$bottom$max
  if (!is.null(constraints$top$min))    lowerl[3] <- constraints$top$min
  if (!is.null(constraints$top$max))    upperl[3] <- constraints$top$max

  tryCatch({
    fit    <- drm(response ~ conc, fct = fct,
                  lowerl = lowerl, upperl = upperl)
    params <- coef(fit)
    ss_res <- sum(residuals(fit)^2)
    ss_tot <- sum((response - mean(response))^2)
    r_sq   <- if (ss_tot == 0) 1.0 else 1 - ss_res / ss_tot

    # Profiled CI (accurate but slow for poorly-conditioned fits).
    # Falls back to vcov-based (approximate) if profiling takes > 5s or fails.
    ci_result <- tryCatch({
      ci <- withTimeout(confint(fit, level = 0.95), timeout = 5, onTimeout = "error")
      list(
        low    = unname(ci["e:(Intercept)", "2.5 %"]),
        high   = unname(ci["e:(Intercept)", "97.5 %"]),
        method = "profiled"
      )
    }, error = function(e) {
      # vcov-based fallback: ± 1.96 * SE
      se       <- sqrt(diag(vcov(fit)))["e:(Intercept)"]
      ic50_est <- unname(params["e:(Intercept)"])
      list(
        low    = ic50_est - 1.96 * se,
        high   = ic50_est + 1.96 * se,
        method = "vcov"
      )
    })

    list(
      success    = TRUE,
      potency    = unname(params["e:(Intercept)"]),
      hill_slope = unname(params["b:(Intercept)"]),
      bottom     = unname(params["c:(Intercept)"]),
      top        = unname(params["d:(Intercept)"]),
      r_squared  = r_sq,
      ci_low_95  = ci_result$low,
      ci_high_95 = ci_result$high,
      ci_method  = ci_result$method
    )
  }, error = function(e) {
    list(success = FALSE, error = conditionMessage(e))
  })
}
