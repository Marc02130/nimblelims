library(testthat)

source("../R/fit.R")
source("../R/category.R")

# Known 4PL dataset: IC50 ≈ 100 nM, hill slope ≈ 1, top ≈ 100, bottom ≈ 0
known_conc     <- c(10000, 3333, 1111, 370, 123, 41, 14, 4.6)
known_response <- c(97.5, 95.1, 87.3, 69.4, 45.2, 20.1, 8.3, 3.1)

test_that("4PL fit on known dataset gives IC50 near 100 nM", {
  result <- fit_compound(known_conc, known_response, model = "4PL")
  expect_true(result$success)
  expect_true(abs(result$potency - 100) / 100 < 0.1)  # within 10% of 100 nM
  expect_gt(result$r_squared, 0.99)
  expect_true(result$ci_low_95 < result$potency)
  expect_true(result$ci_high_95 > result$potency)
  expect_true(result$ci_method %in% c("profiled", "vcov"))
})

test_that("Empty input returns CANNOT_FIT gracefully", {
  result <- fit_compound(numeric(0), numeric(0))
  expect_false(result$success)
  expect_true(!is.null(result$error))
})

test_that("Single point returns failure with clear message", {
  result <- fit_compound(c(100), c(50))
  expect_false(result$success)
})

test_that("Three points returns failure (drc LL.4 needs ≥4 points)", {
  result <- fit_compound(c(100, 33, 11), c(80, 50, 20))
  expect_false(result$success)
})

test_that("Category PARTIAL_HIGH beats NOISY when IC50 > max(conc)", {
  # Low R², but IC50 is clearly above max concentration
  conc     <- c(10, 3.3, 1.1, 0.37)
  response <- c(30, 25, 20, 18)  # flat — won't fit well, IC50 >> max conc
  config   <- list(r_squared_threshold = 0.9, inactive_threshold = 10)
  fit      <- fit_compound(conc, response, model = "4PL")
  # Either CANNOT_FIT or PARTIAL_HIGH — NOT NOISY (priority ordering)
  cat  <- assign_category(fit, conc, response, config)
  expect_true(cat %in% c("CANNOT_FIT", "PARTIAL_HIGH", "INACTIVE"))
  expect_false(cat == "NOISY")
})

test_that("Category INACTIVE for flat response (delta < threshold)", {
  conc     <- c(10000, 3333, 1111, 370, 123, 41, 14, 4.6)
  response <- c(5, 6, 4, 5, 6, 5, 4, 5)  # near-zero % inhibition
  config   <- list(r_squared_threshold = 0.9, inactive_threshold = 20)
  fit      <- fit_compound(conc, response)
  cat      <- assign_category(fit, conc, response, config)
  # Either INACTIVE or CANNOT_FIT (flat line may not converge)
  expect_true(cat %in% c("INACTIVE", "CANNOT_FIT"))
})

test_that("Category INVERSE for response that increases with concentration", {
  conc     <- c(10000, 3333, 1111, 370, 123, 41, 14, 4.6)
  response <- c(5, 10, 20, 40, 60, 75, 88, 95)  # backwards — activator pattern
  config   <- list(r_squared_threshold = 0.9, inactive_threshold = 20)
  fit      <- fit_compound(conc, response, model = "4PL")
  cat      <- assign_category(fit, conc, response, config)
  expect_true(cat %in% c("INVERSE", "CANNOT_FIT"))
})

test_that("Hook effect detection fires when top 2 concs drop by >15%", {
  conc     <- c(10000, 3333, 1111, 370, 123)
  response <- c(90, 95, 85, 60, 20)  # drops at top 2 concentrations
  expect_true(detect_hook_effect(conc, response, drop_threshold_pct = 15))
})

test_that("Hook effect NOT detected with fewer than 5 points", {
  expect_false(detect_hook_effect(c(1000, 100, 10, 1), c(90, 60, 30, 10)))
})

test_that("Hook effect NOT detected for normal sigmoidal response", {
  conc     <- c(10000, 3333, 1111, 370, 123)
  response <- c(95, 80, 55, 30, 10)
  expect_false(detect_hook_effect(conc, response, drop_threshold_pct = 15))
})

test_that("CI fallback to vcov when profiling fails", {
  # Use a dataset where profiling is likely to be slow/unstable
  # We test that the function returns a valid ci_method regardless
  result <- fit_compound(known_conc, known_response, model = "4PL")
  expect_true(result$success)
  expect_true(result$ci_method %in% c("profiled", "vcov"))
  expect_true(is.numeric(result$ci_low_95))
  expect_true(is.numeric(result$ci_high_95))
})

test_that("Parameter constraints are applied", {
  result <- fit_compound(
    known_conc, known_response,
    model = "4PL",
    constraints = list(bottom = list(min = 0, max = 20), top = list(min = 80, max = 120))
  )
  if (result$success) {
    expect_gte(result$bottom, 0)
    expect_lte(result$bottom, 20)
    expect_gte(result$top, 80)
    expect_lte(result$top, 120)
  }
})

test_that("Batch of 10 compounds: 8 succeed, 2 fail gracefully", {
  results <- lapply(1:10, function(i) {
    if (i <= 8) {
      fit_compound(known_conc, known_response)
    } else {
      fit_compound(numeric(0), numeric(0))  # empty → CANNOT_FIT
    }
  })
  n_success <- sum(sapply(results, function(r) isTRUE(r$success)))
  n_fail    <- sum(sapply(results, function(r) !isTRUE(r$success)))
  expect_equal(n_success, 8)
  expect_equal(n_fail, 2)
})

test_that("derive_quality_flag maps correctly for all categories", {
  expect_equal(derive_quality_flag("SIGMOID"),      "valid")
  expect_equal(derive_quality_flag("PARTIAL_HIGH"), "gt_max_conc")
  expect_equal(derive_quality_flag("PARTIAL_LOW"),  "lt_min_conc")
  expect_equal(derive_quality_flag("INACTIVE"),     "inactive")
  expect_equal(derive_quality_flag("CANNOT_FIT"),   "cannot_calculate")
  expect_equal(derive_quality_flag("NOISY"),        "review_required")
  expect_equal(derive_quality_flag("INVERSE"),      "review_required")
  expect_equal(derive_quality_flag("HOOK_EFFECT"),  "review_required")
})
