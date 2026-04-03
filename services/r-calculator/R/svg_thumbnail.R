library(ggplot2)
library(svglite)

#' Generate a fixed-size 200x120px SVG thumbnail for a dose-response curve.
#'
#' No axes labels, no legend — just the curve + data points for thumbnail display.
#' Excluded points shown in grey if excluded_indices is provided.
#'
#' @param conc             Concentration vector (averaged replicates, log scale).
#' @param response         Response vector (averaged replicates).
#' @param fit              Result from fit_compound() — used to draw the fitted curve.
#' @param curve_category   Category string for color coding.
#' @param excluded_indices Integer vector of indices in conc/response that are excluded.
#' @return Character: SVG string with explicit width="200" height="120" attributes.
generate_thumbnail_svg <- function(conc, response, fit,
                                   curve_category = "SIGMOID",
                                   excluded_indices = integer(0)) {
  # Color by category
  curve_color <- switch(curve_category,
    "SIGMOID"      = "#2563eb",  # blue
    "INACTIVE"     = "#6b7280",  # grey
    "NOISY"        = "#f59e0b",  # amber
    "CANNOT_FIT"   = "#ef4444",  # red
    "PARTIAL_HIGH" = "#f97316",  # orange
    "PARTIAL_LOW"  = "#f97316",  # orange
    "INVERSE"      = "#8b5cf6",  # purple
    "HOOK_EFFECT"  = "#ec4899",  # pink
    "#2563eb"
  )

  df <- data.frame(
    conc     = conc,
    response = response,
    excluded = seq_along(conc) %in% excluded_indices
  )

  p <- ggplot(df, aes(x = log10(conc), y = response)) +
    geom_point(aes(color = excluded), size = 1.5, show.legend = FALSE) +
    scale_color_manual(values = c("FALSE" = curve_color, "TRUE" = "#d1d5db")) +
    theme_void() +
    theme(
      plot.margin      = margin(4, 4, 4, 4),
      panel.background = element_rect(fill = "white", color = NA)
    )

  # Draw fitted curve if fit succeeded
  if (isTRUE(fit$success) && !curve_category %in% c("CANNOT_FIT", "INACTIVE")) {
    conc_seq  <- 10^seq(log10(min(conc)), log10(max(conc)), length.out = 100)
    pred_resp <- tryCatch({
      b <- fit$hill_slope
      c <- fit$bottom
      d <- fit$top
      e <- fit$potency
      c + (d - c) / (1 + (e / conc_seq)^b)
    }, error = function(err) NULL)

    if (!is.null(pred_resp)) {
      curve_df <- data.frame(x = log10(conc_seq), y = pred_resp)
      p <- p + geom_line(data = curve_df, aes(x = x, y = y),
                         color = curve_color, linewidth = 0.8, inherit.aes = FALSE)
    }
  }

  svg_string <- svgstring(width = 200 / 72, height = 120 / 72, pointsize = 6)
  print(p)
  dev.off()
  svg_out <- as.character(svg_string())

  # Force explicit pixel dimensions on the svg element
  svg_out <- sub('width="[^"]*"', 'width="200"', svg_out)
  svg_out <- sub('height="[^"]*"', 'height="120"', svg_out)
  return(svg_out)
}
