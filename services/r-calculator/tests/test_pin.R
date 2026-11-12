# Base-R checks for the S1 pin. Run inside the pinned image:
#   Rscript tests/test_pin.R
# Host R does not satisfy CALC-REQ-5; this file is the pin, not a KAT.

args_root <- Sys.getenv("PIN_TEST_ROOT", "")
root <- if (nzchar(args_root)) args_root else normalizePath("..", mustWork = FALSE)
# When invoked as `Rscript tests/test_pin.R` from services/r-calculator, cwd is that dir.
if (!file.exists(file.path(root, "R", "pin.R"))) {
  root <- getwd()
}

source(file.path(root, "R", "request_timeout.R"))
source(file.path(root, "R", "pin.R"))

stopifnot(identical(REQUEST_TIMEOUT_SECONDS, 50))
stopifnot(isTRUE(legacy_dose_response_path("/fit")))
stopifnot(isTRUE(legacy_dose_response_path("/svg/full")))
stopifnot(!isTRUE(legacy_dose_response_path("/health")))
stopifnot(!isTRUE(legacy_dose_response_path("/calculations")))

vector_hash <- lock_hash_hex("ab", "cd", "ef")
stopifnot(identical(
  vector_hash,
  "911f0cdd0689cf114775478c242760865d67d1816e3586fbc6529f24fbb000a2"
))
stopifnot(identical(lock_hash_hex("ab", "cd", "ef"), vector_hash))

preimage_file <- tempfile()
writeBin(charToRaw("ab\ncd\nef"), preimage_file)
stopifnot(identical(sha256_file(preimage_file), vector_hash))
unlink(preimage_file)

one <- charToRaw("version-a")
two <- charToRaw("version-b")
stopifnot(!identical(sha256_text(rawToChar(one)), sha256_text(rawToChar(two))))

writable <- c(
  "36 35 98:0 / / rw,relatime - overlay overlay rw"
)
readonly <- c(
  "36 35 98:0 / / ro,relatime - overlay overlay ro",
  "40 36 0:40 / /tmp rw,nosuid,nodev - tmpfs tmpfs rw,mode=1777"
)
stopifnot(!isTRUE(root_read_only_from_lines(writable)))
stopifnot(isTRUE(root_read_only_from_lines(readonly)))
stopifnot(isTRUE(scratch_tmpfs_from_lines(readonly, "/tmp")))
stopifnot(!isTRUE(scratch_tmpfs_from_lines(readonly, "/var")))
stopifnot(!isTRUE(scratch_tmpfs_from_lines(writable, "/tmp")))

stopifnot(!isTRUE(cgroup_value_limited("max 100000", cpu = TRUE)))
stopifnot(isTRUE(cgroup_value_limited("100000 100000", cpu = TRUE)))
stopifnot(!isTRUE(cgroup_value_limited("max", cpu = FALSE)))
stopifnot(isTRUE(cgroup_value_limited("1073741824", cpu = FALSE)))
stopifnot(!isTRUE(cgroup_value_limited("", cpu = FALSE)))

stopifnot(isTRUE(forbidden_env_absent_from_names(c("HOME", "R_IMAGE_DIGEST", "PATH"))))
stopifnot(!isTRUE(forbidden_env_absent_from_names(c("HOME", "DATABASE_URL"))))
stopifnot(!isTRUE(forbidden_env_absent_from_names(c("SECRET_KEY"))))
stopifnot(!isTRUE(forbidden_env_absent_from_names(c("JWT_SECRET"))))
stopifnot(isTRUE(forbidden_env_absent_from_names(c("R_BASE_DIGEST"))))

boxed <- sandbox_from_measurements(
  uid = "1000",
  mountinfo_lines = readonly,
  scratch = "/tmp",
  cpu_text = "100000 100000",
  memory_text = "1073741824",
  pids_text = "256",
  env_names = c("HOME", "PATH", "R_IMAGE_DIGEST"),
  egress_blocked = TRUE
)
stopifnot(identical(boxed$uid, 1000L))
stopifnot(isTRUE(boxed$root_read_only))
stopifnot(isTRUE(boxed$scratch_tmpfs))
stopifnot(isTRUE(boxed$egress_blocked))
stopifnot(isTRUE(boxed$cpu_limited))
stopifnot(isTRUE(boxed$memory_limited))
stopifnot(isTRUE(boxed$pids_limited))
stopifnot(isTRUE(boxed$forbidden_env_absent))

# setTimeLimit stops R evaluation. A pure C sleep is not the check.
err <- tryCatch(
  run_with_wall_timeout(
    {
      start <- proc.time()[[3]]
      repeat {
        if (proc.time()[[3]] - start > 3) break
      }
      "not-stopped"
    },
    1
  ),
  error = function(e) e
)
stopifnot(inherits(err, "error"))
stopifnot(isTRUE(is_r_timeout(err)))

cat("test_pin.R ok\n")
