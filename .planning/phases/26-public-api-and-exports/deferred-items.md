# Phase 26 — Deferred Items

Out-of-scope issues discovered during plan execution. Pre-existing — not caused by 26-x plan changes; logged here per the GSD scope-boundary rule. Owner can address in a follow-up phase or dedicated cleanup plan.

## Pre-existing test failures (observed during 26-03)

Both failures predate the worktree base (`4736009`) and reproduce before any 26-03 changes are applied. Neither involves the GMT exporter or any Reactome surface.

| Test                                                       | Failure                  | Likely cause                                                                 |
| ---------------------------------------------------------- | ------------------------ | ---------------------------------------------------------------------------- |
| `tests/test_app.py::TestRoutes::test_login_redirect`       | `assert 404 == 302`      | Route registration or test fixture drift — `/login` returns 404 not 302.     |
| `tests/test_app.py::TestGuestAuth::test_guest_login_page_renders` | (same area, login pages) | Same area as above; likely the guest-login route is no longer at the path the test expects, or the test client lacks an auth provider config. |

Both should be triaged separately; they do not block any 26-x plan.
