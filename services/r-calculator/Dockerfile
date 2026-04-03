FROM rocker/r-ver:4.4

# System libraries for R source builds. Without these, install.packages() prints
# errors but Rscript still exits 0 — plumber/drc end up missing at runtime.
# - plumber: httpuv (zlib), sodium (libsodium), webutils (R curl → libcurl)
# - drc → car → lme4 → nloptr (cmake; optional system nlopt via pkg-config)
# - svglite: systemfonts / textshaping (font + harfbuzz stack)
# curl: docker-compose healthcheck uses curl against localhost:8000
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

# Single-line RUN: multi-line strings without trailing \ are parsed as new Dockerfile instructions.
RUN Rscript -e "install.packages(c('plumber','drc','ggplot2','svglite','jsonlite','MASS','R.utils','testthat'), repos='https://cloud.r-project.org')" \
    && Rscript -e "stopifnot('plumber' %in% rownames(installed.packages()), 'drc' %in% rownames(installed.packages()))"

COPY . /app
WORKDIR /app
EXPOSE 8000
CMD ["Rscript", "-e", "pr <- plumber::plumb('plumber.R'); pr$run(host='0.0.0.0', port=8000)"]
