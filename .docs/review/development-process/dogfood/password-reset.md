# Dogfood: password reset email

**Stem:** `password-reset`  
**Branch:** `dev-seed-password-reset`  
**When:** 2026-10-04, local compose, before tester UAT in [`UAT_Scripts/uat-password-reset.md`](../../../../UAT_Scripts/uat-password-reset.md).  
**Ready for UAT:** Yes. This is not a UAT pass.

## Env

Local compose on this branch. Frontend `http://localhost:3000`. API `http://localhost:8000`. Mailbox `http://localhost:8025` (Mailpit). SMTP stays inside the compose network (`mail:1025`, no TLS).

| Account | Email | What happened |
|---------|--------|----------------|
| admin | `admin@lims.example.com` | Reset was completed. `password_epoch` is 1. `***REMOVED***` no longer signs in on this database. The new password is not written here. |
| lab-tech | `lab-tech@lims.example.com` | Not reset. Published `***REMOVED***` should still work (`password_epoch` 0). Use this for the scripted run unless you create a throwaway user. |

There is no **Reset demo passwords** control. After a successful reset, the old published password for that person is gone.

## Paths tried

1. **Forgot password.** Sign-in shows **Forgot password?** and does not show **Reset demo passwords**. Submitting `admin@lims.example.com` returned the same “if an account exists” message. Mailpit received **Reset your NimbleLIMS password**. The link is `/reset-password#token=...`, not `?token=`.
2. **Link bounced to login (fixed).** The first open of that link landed on the login page. A signed-out `/auth/me` returned 401, and the app sent the browser to `/login`, which dropped the token. Fixed. The same style of link now stays on **Choose a new password**.
3. **Reset completed.** The admin password was changed from the link. Sign-in is not forced through another change (`must_change_password` is false). The new password is not in this log.
4. **Stack.** One `docker compose down` then `up --build` failed with “No such container” on the database. A second `docker compose up -d` came up healthy. Not a product bug.

## Not tried here

Unknown address, inactive account, a second link retiring the first, the 3-per-hour cap, mail turned off (503), a too-short password, and an already-signed-in session dying after the reset. Those are the tester script. Backend tests for the API passed earlier on this branch (13). They are not this dogfood.

## Findings

| Severity | Issue | Action |
|----------|--------|--------|
| Blocker | Reset link opened the login page and lost the token | Fixed. Rechecked: the page stays on **Choose a new password**. |
| Minor | `***REMOVED***` is dead on this database | Accepted. Tester uses `lab-tech` or a throwaway user. Do not write the new admin password into the UAT results. |
| Minor | Compose sometimes errors on the first `up` after `down` | Accepted. Run `docker compose up -d` again. Do not rebuild. |

## Ready for UAT?

Yes. Blocker is fixed. Tester follows `UAT_Scripts/uat-password-reset.md`. Do not stamp a UAT pass from this log.
