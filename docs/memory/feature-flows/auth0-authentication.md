# Feature: Authentication Mode System

> **⚠️ DEPRECATED (2025-12-29)**: This document describes the legacy Auth0/Dev Mode authentication system.
> The login page has been simplified to use **Email Authentication** (primary) and **Admin Login** (secondary).
> See [email-authentication.md](email-authentication.md) for the current authentication flow.
> Auth0 OAuth and Dev Mode are no longer exposed in the login UI.

---

## Historical Summary

This document previously described a dual-mode authentication system:

1. **Dev Mode** (`DEV_MODE_ENABLED=true`): Username/password login for local development
2. **Production Mode** (`DEV_MODE_ENABLED=false`): Auth0 OAuth with Google

### What Changed (2025-12-29)

- **Removed**: `DEV_MODE_ENABLED` environment variable
- **Removed**: Auth0/Google OAuth from login UI
- **Removed**: `devModeEnabled` state from frontend

### Current Authentication (See [email-authentication.md](email-authentication.md))

| Method | Description |
|--------|-------------|
| **Email Login** (primary) | Email → 6-digit code → Verify |
| **Admin Login** (secondary) | Password-based for 'admin' user |

### Preserved from Legacy System

The following concepts from the old system are still used:

- **JWT tokens** with mode claim (`email` or `admin` instead of `dev` or `prod`)
- **Bcrypt password hashing** for admin password
- **SECRET_KEY** handling and security warnings
- **Token expiration** and automatic logout

---

## Related

- **Current Auth**: [email-authentication.md](email-authentication.md)
- **First-Time Setup**: [first-time-setup.md](first-time-setup.md)

---

**Status**: ❌ Deprecated (2025-12-29)
**Replaced By**: Email Authentication + Admin Login
