# rocker/r-ver tag 4.4, linux/amd64, resolved 2026-11-12.
# The tag is not the pin. CALC-REQ-2 requires the digest.
FROM rocker/r-ver@sha256:aa952afb35853aaf5c67bd224aa969caf6ad49395d69cf19a586f1554ed3bd05

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

# renv itself is the restore tool. Its version is the one recorded while
# services/r-calculator/renv.lock was snapshotted. The tarball is checksummed.
# CALC-REQ-3: the image build does not call install.packages.
ARG RENV_VERSION=1.3.1
ARG RENV_SHA256=e16281908ddf0ed6f8f6f8ad3f2cc4788af6de04c1ab223517aa1cc9acb30731
RUN curl -fsSL -o /tmp/renv.tar.gz \
      "https://cran.r-project.org/src/contrib/renv_${RENV_VERSION}.tar.gz" \
    && echo "${RENV_SHA256}  /tmp/renv.tar.gz" | sha256sum -c - \
    && R CMD INSTALL /tmp/renv.tar.gz \
    && rm -f /tmp/renv.tar.gz

WORKDIR /app
COPY renv.lock /app/renv.lock
COPY restore.R /tmp/restore.R
# A restore that cannot match the lock fails the build (CALC-REQ-3).
RUN Rscript /tmp/restore.R && rm -f /tmp/restore.R

COPY . /app

# <base> is the digest in the FROM line. <tree> is the git tree id of
# services/r-calculator, supplied by deploy/CI (git rev-parse <commit>:services/r-calculator).
# An empty tree fails closed: the backend's expected hash will not match.
ARG R_BASE_DIGEST=aa952afb35853aaf5c67bd224aa969caf6ad49395d69cf19a586f1554ed3bd05
ARG R_TREE=
ENV R_BASE_DIGEST=${R_BASE_DIGEST} \
    R_TREE=${R_TREE} \
    R_SCRATCH_PATH=/tmp

RUN useradd --uid 1000 --create-home --shell /usr/sbin/nologin rcalc \
    && chown -R rcalc:rcalc /app
USER rcalc

EXPOSE 8000
CMD ["Rscript", "-e", "pr <- plumber::plumb('plumber.R'); pr$run(host='0.0.0.0', port=8000)"]
