# UAT: Password reset email

**Stem:** `password-reset`  
**Status:** Ready for a tester. Dogfood is logged. This is not a UAT pass.  
**Branch:** `dev-seed-password-reset`  
**Dogfood:** [`.docs/review/development-process/dogfood/password-reset.md`](../.docs/review/development-process/dogfood/password-reset.md)

## Purpose

A person who cannot sign in can request a one-time link to the email on their account and choose a new password. Sign-in has **Forgot password?** and no control that puts demo accounts back on the published passwords.

## Preconditions

| Item | Value |
|------|--------|
| App | `docker compose up -d --build` from this branch. Frontend `http://localhost:3000`. API `http://localhost:8000`. |
| Mail | Open `http://localhost:8025` (Mailpit). Every message sent by local compose lands there. |
| Account | `lab-tech` / `labtech123` / `lab-tech@lims.example.com`, unless that password was already changed. |
| Do not use | `admin` / `admin123` on the dogfood database. That reset already happened. `admin123` does not sign in there. |

If the first `up` after `down` says `No such container`, run `docker compose up -d` again. Do not rebuild.

Do not put the reset token, the new password, or any SMTP password in the results. Say only pass or fail.

Completing section 2 retires `labtech123` for that user. There is no button to put it back. Prefer a throwaway user with any email if you can still sign in as an administrator. Mailpit will catch that address too.

## 1. Request a link

| Step | Action | Expected |
|------|--------|----------|
| 1 | Open the sign-in page | **Forgot password?** is visible. There is no **Reset demo passwords** control. |
| 2 | Open **Forgot password?** and submit `lab-tech@lims.example.com` | The page says a link was sent if an account exists. It does not say that this address was found. |
| 3 | Submit an address that is not on any account, such as `nobody@example.com` | The same message as step 2. Mailpit gets no message for that address. |
| 4 | In Mailpit, open the message to `lab-tech@lims.example.com` | Subject is **Reset your NimbleLIMS password**. The link is `/reset-password#token=...`. The token is after `#`, not in `?`. The message has no password. |

## 2. Choose a new password

| Step | Action | Expected |
|------|--------|----------|
| 1 | Open the link from Mailpit | The address stays on `/reset-password#token=...`. The page is **Choose a new password**. It does not jump to the login page. |
| 2 | Enter a password shorter than 12 characters and leave the field | The field says at least 12 characters. The link still works. |
| 3 | Enter a password of at least 12 characters with upper, lower, digit, and symbol, and confirm it | "Password updated. Sign in with your new password." You are not signed in by the link. |
| 4 | Sign in with `labtech123` | Rejected. |
| 5 | Sign in with the new password | Signed in. You are not forced to change it again. |
| 6 | Open the same link and try another password | "This reset link is invalid or has expired." |
| 7 | If a browser was already signed in as that user before the reset, use that session | The next request is signed out (401). |

## 3. Quiet cases

| Step | Action | Expected |
|------|--------|----------|
| 1 | Request a link for an inactive account, if you can mark one inactive | Same message as a missing account. No email. |
| 2 | Request a second link before using the first | The first link no longer works. The second does. |
| 3 | Request more than 3 links in an hour for the same account | The page still shows the same message. Mailpit gets no fourth message. |
| 4 | Only if mail is turned off (`SMTP_HOST` empty, backend recreated). Skip on the default local stack. Submit any email, including a real one | **503**. The message asks an administrator to set a password. A real address and a fake address get that same message. |

## Results

| Section | Result | Tester | Date | Notes |
|---------|--------|--------|------|-------|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |

**UAT pass:** no
