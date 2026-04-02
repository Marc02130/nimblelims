#' Assign a curve category based on fit results and raw data.
#'
#' Priority order matches the design spec exactly:
#'   1. CANNOT_FIT   — drc failed to converge
#'   2. INACTIVE     — |top - bottom| < inactive_threshold
#'   3. INVERSE      — top - bottom < 0
#'   4. PARTIAL_HIGH — IC50 > max(conc)
#'   5. PARTIAL_LOW  — IC50 < min(conc)
#'   6. HOOK_EFFECT  — biphasic response
#'   7. NOISY        — R² < r_squared_threshold
#'   8. SIGMOID      — all checks pass
#'
#' @param fit        Result from fit_compound().
#' @param conc       Concentration vector (original, before averaging).
#' @param response   Response vector (original).
#' @param config     List with r_squared_threshold (default 0.9) and inactive_threshold (default 20).
#' @return Character string: one of the 8 categories.
assign_category <- function(fit, conc, response, config) {
  r_sq_thresh    <- if (!is.null(config$r_squared_threshold)) config$r_squared_threshold else 0.9
  inactive_thresh <- if (!is.null(config$inactive_threshold)) config$inactive_threshold else 20.0

  if (!isTRUE(fit$success))                          return("CANNOT_FIT")
  delta <- fit$top - fit$bottom
  if (abs(delta) < inactive_thresh)                  return("INACTIVE")
  if (delta < 0)                                     return("INVERSE")
  if (fit$potency > max(conc))                       return("PARTIAL_HIGH")
  if (fit$potency < min(conc))                       return("PARTIAL_LOW")
  if (detect_hook_effect(conc, response))            return("HOOK_EFFECT")
  if (fit$r_squared < r_sq_thresh)                   return("NOISY")
  return("SIGMOID")
}


#' Detect a hook (prozone) effect in dose-response data.
#'
#' Signature: mean response at the top 2 concentrations drops more than
#' drop_threshold_pct below the peak response.
#' Requires at least 5 data points (by design — not enough structure otherwise).
#'
#' @param conc              Concentration vector.
#' @param response          Response vector.
#' @param drop_threshold_pct Percent drop required to flag (default 15).
#' @return Logical.
detect_hook_effect <- function(conc, response, drop_threshold_pct = 15) {
  if (length(conc) < 5) return(FALSE)
  ord        <- order(conc)
  resp_sorted <- response[ord]
  n          <- length(resp_sorted)
  peak_resp  <- max(resp_sorted)
  if (peak_resp == 0) return(FALSE)
  top2_mean  <- mean(resp_sorted[(n - 1):n])
  drop_pct   <- (peak_resp - top2_mean) / abs(peak_resp) * 100
  return(drop_pct > drop_threshold_pct)
}


#' Derive CDD-style quality_flag from curve_category.
#'
#' @param category Character: one of the 8 curve categories.
#' @return Character: quality flag for export/reporting.
derive_quality_flag <- function(category) {
  switch(category,
    "SIGMOID"      = "valid",
    "PARTIAL_HIGH" = "gt_max_conc",
    "PARTIAL_LOW"  = "lt_min_conc",
    "INACTIVE"     = "inactive",
    "CANNOT_FIT"   = "cannot_calculate",
    "review_required"   # INVERSE, HOOK_EFFECT, NOISY all → review_required
  )
}
