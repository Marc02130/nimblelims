# Shortest round-trip string for one R double (CALC-REQ-5 serialiser, CALC-REQ-37).
#
# The digit count is the fewest significant digits whose string parses back
# to the identical double under R's own parser and under a correctly rounded
# parser. R's as.numeric is not correctly rounded for every string, so it can
# accept a string that the backend's decimal reading maps to another double;
# jsonlite parses numbers with the C library strtod, which is correctly
# rounded. When R's parser misreads the shortest correctly rounded string, the
# result has one more digit than Python repr() would give. Notation follows the same range rule as Python repr(): fixed
# notation for 0 and when 1e-4 <= |x| < 1e16, else scientific. The backend
# reads the string as a decimal and never as binary.

round_trips <- function(text, x) {
  strtod <- jsonlite::parse_json(paste0("[", text, "]"), simplifyVector = TRUE)
  identical(as.numeric(text), x) && identical(as.double(strtod), x)
}

shortest_round_trip_digits <- function(x) {
  for (digits in 1:17) {
    text <- sprintf(paste0("%.", digits, "g"), x)
    if (round_trips(text, x)) {
      return(digits)
    }
  }
  stop("no round-trip string within 17 significant digits")
}

shortest_round_trip <- function(x) {
  if (!is.numeric(x) || length(x) != 1L || is.na(x) || !is.finite(x)) {
    stop("shortest_round_trip needs one finite double")
  }
  x <- as.double(x)
  digits <- shortest_round_trip_digits(x)
  scientific <- sprintf(paste0("%.", digits - 1L, "e"), x)
  exponent <- as.integer(sub("^.*e", "", scientific))
  if (x == 0 || (abs(x) >= 1e-4 && abs(x) < 1e16)) {
    places <- max(0L, digits - 1L - exponent)
    fixed <- sprintf(paste0("%.", places, "f"), x)
    if (round_trips(fixed, x)) {
      return(fixed)
    }
  }
  mantissa <- sub("e.*$", "", scientific)
  sign <- if (exponent < 0L) "-" else "+"
  paste0(mantissa, "e", sign, sprintf("%02d", abs(exponent)))
}
