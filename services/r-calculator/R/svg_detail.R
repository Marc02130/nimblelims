library(ggplot2)
library(svglite)

#' Generate a full-size SVG for PDF export.
#'
#' Used by POST /svg/full — NOT by the Plotly detail view in the UI.
#' The UI renders client-side from fit parameters via Plotly.
#' This endpoint is the hook for future PDF report generation.
#'
#' @param conc              Concentration vector.
#' @param response          Response vector.
#' @param fit               Fit result from fit_compound().
#' @param excluded_indices  Excluded point indices.
#' @param x_label           X-axis label (e.g. "Concentration (nM)").
#' @param y_label           Y-axis label (e.g. "% Inhibition").
#' @param title             Chart title (e.g. compound name).
#' @return Character: full SVG string.
generate_detail_svg <- function(conc, response, fit,
                                excluded_indices = integer(0),
                                x_label = "Concentration",
                                y_label = "% Inhibition",
                                title = "") {
  df <- data.frame(
    log_conc = log10(conc),
    response = response,
    excluded = seq_along(conc) %in% excluded_indices
  )

  p <- ggplot(df, aes(x = log_conc, y = response)) +
    geom_point(aes(shape = excluded, color = excluded), size = 3, show.legend = TRUE) +
    scale_shape_manual(values = c("FALSE" = 16, "TRUE" = 4),
                       labels = c("FALSE" = "Used", "TRUE" = "Excluded")) +
    scale_color_manual(values = c("FALSE" = "#2563eb", "TRUE" = "#9ca3af"),
                       labels = c("FALSE" = "Used", "TRUE" = "Excluded")) +
    labs(x = x_label, y = y_label, title = title, color = NULL, shape = NULL) +
    theme_bw(base_size = 12) +
    theme(legend.position = "bottom")

  if (isTRUE(fit$success)) {
    conc_seq  <- 10^seq(log10(min(conc)), log10(max(conc)), length.out = 200)
    pred_resp <- tryCatch({
      b <- fit$hill_slope; c <- fit$bottom; d <- fit$top; e <- fit$potency
      c + (d - c) / (1 + (e / conc_seq)^b)
    }, error = function(err) NULL)

    if (!is.null(pred_resp)) {
      curve_df <- data.frame(x = log10(conc_seq), y = pred_resp)
      p <- p + geom_line(data = curve_df, aes(x = x, y = y),
                         color = "#2563eb", linewidth = 1, inherit.aes = FALSE)
    }

    # IC50 line
    if (!is.null(fit$potency) && fit$potency > 0) {
      p <- p + geom_vline(xintercept = log10(fit$potency),
                          linetype = "dashed", color = "#ef4444", linewidth = 0.8) +
        annotate("text", x = log10(fit$potency), y = Inf,
                 label = paste0("IC50 = ", signif(fit$potency, 3)),
                 hjust = -0.1, vjust = 1.5, size = 3.5, color = "#ef4444")
    }
  }

  svg_string <- svgstring(width = 6, height = 4)
  print(p)
  dev.off()
  as.character(svg_string())
}
