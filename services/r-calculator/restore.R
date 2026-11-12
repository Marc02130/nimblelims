# Build-time only. renv::restore throws when it cannot match renv.lock, which
# fails the image build (CALC-REQ-3).
renv::restore(
  lockfile = "/app/renv.lock",
  library = "/usr/local/lib/R/site-library",
  prompt = FALSE
)
need <- c("plumber", "drc", "ggplot2", "svglite", "jsonlite", "MASS", "R.utils")
missing <- need[!vapply(need, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing)) {
  stop("restore missed: ", paste(missing, collapse = ", "), call. = FALSE)
}
cat("renv restore ok\n")
