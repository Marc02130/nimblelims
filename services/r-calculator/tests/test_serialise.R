# Serialiser unit test (CALC-REQ-5). Run inside the pinned image only:
#   docker run --rm --entrypoint Rscript <image> tests/test_serialise.R
# A host-R run does not meet CALC-REQ-5, so this file stops before any check
# when it is not inside the pinned image.

root <- getwd()
source(file.path(root, "R", "pin.R"))
source(file.path(root, "R", "serialise.R"))

in_pinned_image <- function() {
  lock_path <- "/app/renv.lock"
  base <- Sys.getenv("R_BASE_DIGEST", "")
  tree <- Sys.getenv("R_TREE", "")
  isTRUE(file.exists(lock_path)) &&
    identical(normalizePath(root), "/app") &&
    grepl("^[0-9a-f]{64}$", base) &&
    grepl("^[0-9a-f]{40}$|^[0-9a-f]{64}$", tree)
}

if (!in_pinned_image()) {
  stop("not inside the pinned image: a host-R run of the serialiser test does not count")
}

pin <- health_pin_report(sandbox = list())
stopifnot(grepl("^[0-9a-f]{64}$", pin$lock_hash))
cat("serialiser test lock_hash", pin$lock_hash, "\n")

# Expected strings are Python 3 repr() of the same IEEE double, a computation
# outside the R service, with repr's trailing ".0" dropped on whole numbers.
# The first four are the Spec's example strings.
cases <- list(
  list(value = 0.026, expected = "0.026"),
  list(value = -0.98, expected = "-0.98"),
  list(value = 0.1 + 0.2, expected = "0.30000000000000004"),
  list(value = 1 / 3, expected = "0.3333333333333333"),
  list(value = 2.522, expected = "2.522"),
  list(value = 100, expected = "100"),
  list(value = 1234.5, expected = "1234.5"),
  list(value = 1e-04, expected = "0.0001"),
  list(value = 1e-05, expected = "1e-05"),
  list(value = 1e16, expected = "1e+16"),
  list(value = 123456789012345680, expected = "1.2345678901234568e+17"),
  list(value = 5e-324, expected = "5e-324"),
  # R's as.numeric("5.1743385660594e-13") returns this double, but a correctly
  # rounded parser returns its neighbour. Sixteen digits are needed.
  list(value = as.numeric("0x1.234a13db1363ap-41"), expected = "5.174338566059401e-13"),
  # Python repr() gives 16 digits (-5.315895485450009e-276), but R's own parser
  # misreads that string, so the round trip under both parsers needs 17.
  list(value = as.numeric("-0x1.78ee76b873afcp-915"), expected = "-5.3158954854500086e-276"),
  list(value = 0, expected = "0")
)

for (case in cases) {
  got <- shortest_round_trip(case$value)
  if (!identical(got, case$expected)) {
    stop(sprintf("serialiser: expected %s, got %s", case$expected, got))
  }
  # Round trip under R's own parser (as.numeric and the expression parser)
  # and under the correctly rounded strtod parser.
  stopifnot(identical(as.numeric(got), case$value))
  stopifnot(identical(eval(parse(text = got)), case$value))
  stopifnot(isTRUE(round_trips(got, case$value)))
  # No shorter digit count round-trips.
  digits <- shortest_round_trip_digits(case$value)
  if (digits > 1L) {
    shorter <- sprintf(paste0("%.", digits - 1L, "g"), case$value)
    stopifnot(!isTRUE(round_trips(shorter, case$value)))
  }
}

for (bad in list(NaN, Inf, -Inf, NA_real_, c(1, 2), "1")) {
  err <- tryCatch(shortest_round_trip(bad), error = function(e) e)
  stopifnot(inherits(err, "error"))
}

cat("serialiser test ok (", length(cases), "cases )\n")
