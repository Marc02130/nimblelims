library(plumber)
library(jsonlite)

source("R/request_timeout.R")
source("R/pin.R")
source("R/serialise.R")
source("R/fit.R")
source("R/category.R")
source("R/svg_thumbnail.R")
source("R/svg_detail.R")

#* @apiTitle r-calculator
#* @apiDescription Dose-response curve fitting service for NimbleLIMS.
#*   Receives pre-normalized response data from FastAPI, returns fit parameters,
#*   curve categories, quality flags, and SVG thumbnails.
#*   R never touches the database.

#* Log all requests
#* @filter logger
function(req) {
  cat(format(Sys.time()), req$REQUEST_METHOD, req$PATH_INFO, "\n")
  plumber::forward()
}

#* Health check
#* @get /health
#* @serializer unboxedJSON
function() {
  pin <- health_pin_report()
  pin$status <- "ok"
  pin$drc_version <- as.character(packageVersion("drc"))
  pin$r_version <- R.version.string
  pin
}

#* Fit dose-response curves for a batch of compounds.
#*
#* Synchronous. Blocks until all compounds are fitted.
#* Per-compound errors are non-fatal: failed compounds return success=false
#* with curve_category="CANNOT_FIT". The batch continues for remaining compounds.
#*
#* Expected body:
#*   {
#*     "compounds": [
#*       {
#*         "sample_id": "uuid",
#*         "points": [{"conc": 10000, "response": 85.2, "point_id": "uuid"}],
#*         "model": "4PL",
#*         "constraints": {"bottom": {"min": 0, "max": 20}, "top": {"min": 80, "max": 120}}
#*       }
#*     ],
#*     "config": {
#*       "r_squared_threshold": 0.9,
#*       "inactive_threshold": 20,
#*       "concentration_unit": "nM"
#*     }
#*   }
#*
#* @post /fit
#* @serializer unboxedJSON
function(req) {
  body <- tryCatch(
    jsonlite::fromJSON(req$postBody, simplifyVector = FALSE),
    error = function(e) NULL
  )
  if (is.null(body)) {
    stop("Invalid JSON body")
  }

  compounds <- body$compounds
  config    <- if (!is.null(body$config)) body$config else list()

  results <- lapply(compounds, function(cpd) {
    sample_id <- cpd$sample_id
    model     <- if (!is.null(cpd$model)) cpd$model else "4PL"
    constraints <- if (!is.null(cpd$constraints)) cpd$constraints else list()
    points    <- cpd$points

    conc     <- sapply(points, function(p) as.numeric(p$conc))
    response <- sapply(points, function(p) as.numeric(p$response))
    point_ids <- sapply(points, function(p) p$point_id)

    fit      <- fit_compound(conc, response, model = model, constraints = constraints)
    category <- assign_category(fit, conc, response, config)
    q_flag   <- derive_quality_flag(category)

    thumbnail <- tryCatch(
      generate_thumbnail_svg(conc, response, fit, curve_category = category),
      error = function(e) NULL
    )

    result <- list(
      sample_id      = sample_id,
      success        = isTRUE(fit$success),
      potency        = if (isTRUE(fit$success)) fit$potency    else NULL,
      potency_type   = if (isTRUE(fit$success)) "IC50"         else NULL,
      hill_slope     = if (isTRUE(fit$success)) fit$hill_slope else NULL,
      top            = if (isTRUE(fit$success)) fit$top        else NULL,
      bottom         = if (isTRUE(fit$success)) fit$bottom     else NULL,
      r_squared      = if (isTRUE(fit$success)) fit$r_squared  else NULL,
      ci_low_95      = if (isTRUE(fit$success)) fit$ci_low_95  else NULL,
      ci_high_95     = if (isTRUE(fit$success)) fit$ci_high_95 else NULL,
      ci_method      = if (isTRUE(fit$success)) fit$ci_method  else NULL,
      curve_category = category,
      quality_flag   = q_flag,
      thumbnail_svg  = thumbnail,
      error          = if (!isTRUE(fit$success)) fit$error else NULL
    )
    result
  })

  results
}

#* Generate a full-size SVG for a single compound (for PDF export).
#*
#* @post /svg/full
#* @serializer unboxedJSON
function(req) {
  body <- tryCatch(
    jsonlite::fromJSON(req$postBody, simplifyVector = FALSE),
    error = function(e) NULL
  )
  if (is.null(body)) stop("Invalid JSON body")

  conc      <- sapply(body$points, function(p) as.numeric(p$conc))
  response  <- sapply(body$points, function(p) as.numeric(p$response))
  excl_idx  <- if (!is.null(body$excluded_point_ids)) {
    point_ids <- sapply(body$points, function(p) p$point_id)
    which(point_ids %in% body$excluded_point_ids)
  } else integer(0)

  fit <- fit_compound(conc, response,
                      model = if (!is.null(body$model)) body$model else "4PL")

  svg <- generate_detail_svg(
    conc             = conc,
    response         = response,
    fit              = fit,
    excluded_indices = excl_idx,
    x_label          = if (!is.null(body$x_label)) body$x_label else "Concentration",
    y_label          = if (!is.null(body$y_label)) body$y_label else "% Inhibition",
    title            = if (!is.null(body$title))   body$title   else ""
  )

  list(svg = svg)
}

#* KAT harness fixture route (CALC-REQ-5 harness only). Not a catalog function.
#*
#* Parses one decimal string as an R double and returns that double's
#* shortest round-trip string. It does no arithmetic. It lets the backend KAT
#* runner prove the R-over-HTTP path on the pinned image before any catalog
#* route exists.
#*
#* Expected body: {"value": "0.026"}
#*
#* @post /kat-harness/round-trip
#* @serializer unboxedJSON
function(req, res) {
  body <- tryCatch(
    jsonlite::fromJSON(req$postBody, simplifyVector = FALSE),
    error = function(e) NULL
  )
  value <- if (is.list(body)) body$value else NULL
  parsed <- if (is.character(value) && length(value) == 1L) {
    suppressWarnings(as.numeric(value))
  } else {
    NA_real_
  }
  if (is.na(parsed) || !is.finite(parsed)) {
    res$status <- 400L
    return(list(code = "harness_input", detail = "value must be one finite decimal string"))
  }
  list(value = shortest_round_trip(parsed))
}

# The 50 s limit wraps endpoint execution via aroundexec.
# POST /fit and POST /svg/full are not given that hook.
#* @plumber
function(pr) {
  install_calculation_timeout(pr, REQUEST_TIMEOUT_SECONDS)
}
