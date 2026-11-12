# Lock hash and sandbox self-attestation for CALC-REQ-2, 3, 4, and 4a.
# /health gets <base> and <tree> from build args baked into the image, and
# computes <renv> from the renv.lock copied into the image (Spec §2).

sha256_file <- function(path) {
  line <- system2("sha256sum", path, stdout = TRUE)
  if (length(line) < 1L) {
    stop("sha256sum returned no output for ", path)
  }
  sub(" .*", "", line[[1L]])
}

sha256_text <- function(text) {
  tmp <- tempfile(pattern = "lock-preimage-")
  on.exit(unlink(tmp), add = TRUE)
  writeBin(charToRaw(text), tmp)
  sha256_file(tmp)
}

#' SHA-256 of `<base>\\n<renv>\\n<tree>` with no trailing LF (Spec §2).
lock_hash_hex <- function(base, renv, tree) {
  sha256_text(paste0(base, "\n", renv, "\n", tree))
}

mountinfo_record <- function(line) {
  parts <- strsplit(line, " ", fixed = TRUE)[[1L]]
  dash <- match("-", parts)
  if (is.na(dash) || dash < 7L || dash >= length(parts)) {
    return(NULL)
  }
  list(
    mount_point = parts[[5L]],
    options = strsplit(parts[[6L]], ",", fixed = TRUE)[[1L]],
    fs_type = parts[[dash + 1L]]
  )
}

root_read_only_from_lines <- function(lines) {
  for (line in lines) {
    info <- mountinfo_record(line)
    if (is.null(info)) {
      next
    }
    if (identical(info$mount_point, "/")) {
      return(isTRUE("ro" %in% info$options))
    }
  }
  FALSE
}

scratch_tmpfs_from_lines <- function(lines, scratch) {
  best <- NULL
  best_len <- -1L
  for (line in lines) {
    info <- mountinfo_record(line)
    if (is.null(info)) {
      next
    }
    mp <- info$mount_point
    exact <- identical(mp, scratch)
    prefix <- startsWith(scratch, paste0(mp, "/"))
    if (exact || prefix) {
      if (nchar(mp) > best_len) {
        best <- info
        best_len <- nchar(mp)
      }
    }
  }
  if (is.null(best)) {
    return(FALSE)
  }
  identical(best$fs_type, "tmpfs")
}

#' A cgroup limit is set when the value is present and is not `max`.
#' `cpu.max` is `<quota> <period>`; only the quota is compared to `max`.
cgroup_value_limited <- function(text, cpu = FALSE) {
  if (is.null(text) || !nzchar(text)) {
    return(FALSE)
  }
  token <- trimws(text)
  if (isTRUE(cpu)) {
    token <- strsplit(token, " ", fixed = TRUE)[[1L]][[1L]]
  }
  !identical(token, "max")
}

read_cgroup_text <- function(name) {
  direct <- file.path("/sys/fs/cgroup", name)
  path <- direct
  if (!file.exists(path) && dir.exists("/sys/fs/cgroup")) {
    hits <- list.files(
      "/sys/fs/cgroup",
      pattern = paste0("^", name, "$"),
      recursive = TRUE,
      full.names = TRUE
    )
    if (length(hits) > 0L) {
      path <- hits[[1L]]
    }
  }
  if (!file.exists(path)) {
    return("")
  }
  paste(readLines(path, warn = FALSE), collapse = "\n")
}

forbidden_env_absent_from_names <- function(names) {
  if (length(names) == 0L) {
    return(TRUE)
  }
  bad <- names == "DATABASE_URL" | grepl("_(KEY|SECRET)$", names)
  !any(bad)
}

egress_blocked_now <- function() {
  # An outbound TCP probe. Failure means egress is blocked. A probe that
  # cannot be attempted is not evidence of a block (fail closed: FALSE).
  old <- getOption("timeout")
  on.exit(options(timeout = old), add = TRUE)
  options(timeout = 2)
  con <- tryCatch(
    socketConnection(
      host = "1.1.1.1",
      port = 443,
      open = "wb",
      blocking = TRUE,
      timeout = 2
    ),
    error = function(e) NULL
  )
  if (is.null(con)) {
    return(TRUE)
  }
  close(con)
  FALSE
}

sandbox_from_measurements <- function(
  uid,
  mountinfo_lines,
  scratch,
  cpu_text,
  memory_text,
  pids_text,
  env_names,
  egress_blocked
) {
  uid_num <- suppressWarnings(as.integer(uid))
  if (length(uid_num) != 1L || is.na(uid_num)) {
    uid_num <- NA_integer_
  }
  list(
    uid = uid_num,
    root_read_only = isTRUE(root_read_only_from_lines(mountinfo_lines)),
    scratch_tmpfs = isTRUE(scratch_tmpfs_from_lines(mountinfo_lines, scratch)),
    egress_blocked = isTRUE(egress_blocked),
    cpu_limited = isTRUE(cgroup_value_limited(cpu_text, cpu = TRUE)),
    memory_limited = isTRUE(cgroup_value_limited(memory_text, cpu = FALSE)),
    pids_limited = isTRUE(cgroup_value_limited(pids_text, cpu = FALSE)),
    forbidden_env_absent = isTRUE(forbidden_env_absent_from_names(env_names))
  )
}

measure_sandbox <- function(scratch = Sys.getenv("R_SCRATCH_PATH", "/tmp")) {
  uid <- tryCatch(system2("id", "-u", stdout = TRUE), error = function(e) NA_character_)
  lines <- tryCatch(readLines("/proc/self/mountinfo", warn = FALSE), error = function(e) character())
  sandbox_from_measurements(
    uid = uid,
    mountinfo_lines = lines,
    scratch = scratch,
    cpu_text = read_cgroup_text("cpu.max"),
    memory_text = read_cgroup_text("memory.max"),
    pids_text = read_cgroup_text("pids.max"),
    env_names = names(Sys.getenv()),
    egress_blocked = egress_blocked_now()
  )
}

#' Fields /health adds for the pin. `R_IMAGE_DIGEST` is NA when unset so JSON
#' reports null rather than dropping the field.
health_pin_report <- function(
  base = Sys.getenv("R_BASE_DIGEST", ""),
  tree = Sys.getenv("R_TREE", ""),
  lock_path = "/app/renv.lock",
  image_digest = Sys.getenv("R_IMAGE_DIGEST", ""),
  sandbox = measure_sandbox()
) {
  renv <- if (file.exists(lock_path)) sha256_file(lock_path) else ""
  digest <- image_digest
  if (is.null(digest) || !nzchar(digest)) {
    digest <- NA_character_
  }
  list(
    base = base,
    renv = renv,
    tree = tree,
    lock_hash = lock_hash_hex(base, renv, tree),
    R_IMAGE_DIGEST = digest,
    sandbox = sandbox
  )
}
