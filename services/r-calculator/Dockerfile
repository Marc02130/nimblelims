FROM rocker/r-ver:4.4

# System libraries for R package native code.
# - plumber: httpuv (zlib), sodium (libsodium), webutils (libcurl)
# - drc → car → lme4 → nloptr (cmake; system nlopt)
# - svglite: systemfonts / textshaping (font + harfbuzz stack)
# curl: docker-compose healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    cmake \
    curl \
    libcurl4-openssl-dev \
    libfontconfig1-dev \
    libfreetype6-dev \
    libfribidi-dev \
    libharfbuzz-dev \
    libjpeg-dev \
    libnlopt-dev \
    libpng-dev \
    libsodium-dev \
    libssl-dev \
    libtiff-dev \
    pkg-config \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Install R packages using rocker's default Posit Package Manager binary repo
# (Ubuntu noble). Do NOT force repos='https://cloud.r-project.org' — that
# installs from source and regularly breaks the drc dependency chain
# (Deriv → doBy → pbkrtest → car → drc).
#
# Depends + Imports + LinkingTo (R default for TRUE, but without Suggests).
# LinkingTo is required for header packages like cpp11 (systemfonts → svglite).
# Suggests are omitted so we do not pull optional geospatial stacks (sf/gdal).
# Runtime packages only (testthat is for host/dev tests, not the service image).
RUN Rscript -e " \
    options(Ncpus = max(1L, parallel::detectCores())); \
    pkgs <- c('plumber', 'drc', 'ggplot2', 'svglite', 'jsonlite', 'MASS', 'R.utils'); \
    install.packages(pkgs, dependencies = c('Depends', 'Imports', 'LinkingTo')); \
    missing <- setdiff(pkgs, rownames(installed.packages())); \
    if (length(missing)) stop('Failed to install: ', paste(missing, collapse = ', ')); \
    "

COPY . /app
WORKDIR /app
EXPOSE 8000
CMD ["Rscript", "-e", "pr <- plumber::plumb('plumber.R'); pr$run(host='0.0.0.0', port=8000)"]
