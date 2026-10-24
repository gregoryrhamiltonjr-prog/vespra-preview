# V2 API contract

Same-origin JSON, no third-party API compatibility implied. All authenticated POSTs require the session CSRF value in `X-CSRF-Token`. Browser clients use the HttpOnly cookie. Native requests include `X-Vespra-Client: native`; successful login/demo responses then include the bearer token for SecureStore. Native sends it in `Authorization: Bearer …` plus the CSRF header. Do not place tokens in URLs or logs.

Common failure codes: 400 validation, 401 unauthenticated/expired, 403 forbidden/CSRF/restricted, 404 absent, 409 stale revision/review or pending appeal, 413 body limit, 415 non-JSON, 429 attempt limit, 503 storage. Errors contain an `error` string. No success response is emitted before a mutation commits.

## Public

| Method/path | Input / output |
|---|---|
| GET /healthz | Schema readiness, version, evaluation mode |
| GET /api/config | Demo availability, city, timezone, policy version, mail-configured flag |
| POST /api/demo | `adult: true`, fictional `user`; unavailable in private mode; cannot target a registered ID |
| POST /api/register | `name`, `email`, `password`, ISO `birth_date`, `adult: true`, exact `policy`; generic result, email queued, no session returned |
| POST /api/login | `email`, `password`; session + CSRF + account status |
| POST /api/email/verify | `code`; single-use email verification, not identity/age verification |
| POST /api/recovery/request | `email`; generic response whether or not an account exists |
| POST /api/recovery/complete | `code`, new `password`; consumes code and revokes sessions |

## Member product

| Method/path | Input / behavior |
|---|---|
| GET /api/state | Actor’s profile, allowed profile projections, accessible matches, latest 200 messages, plans with actor-only reflections, CSRF, config |
| GET /api/discover | Query `cursor`, `limit` (1–100), `min_age`, `max_age`, `area`, `interest`; `items`, `next_cursor` |
| GET /api/messages | Query `match_id`, optional `before`, `limit` (1–100); chronological `items`, `next_before`; match authorization on every request |
| POST /api/like | `target`; one-sided interest, match only if reciprocal; returns `matched` |
| POST /api/message | `match_id`, `body` (1–2000 chars); matched, unblocked actors only |
| POST /api/date | `match_id`, `venue`, future local `starts` without offset, IANA `timezone`; proposer accepts first revision |
| POST /api/accept | `date_id`, exact `revision`; agreement only when both participants accept current details |
| POST /api/revise | `date_id`, `revision`, `venue`, future local `starts`; keeps stored timezone, increments revision and resets consent/handoff |
| POST /api/reserve | `date_id`, `revision`; requires agreed state; durable unique request for that revision; manual-action result, never a confirmation |
| POST /api/cancel | `date_id`, `revision`; shared plan only, not any outside booking |
| POST /api/complete | `date_id`, `revision`; self-reported meeting only after agreed start |
| POST /api/reflect | `date_id`, `revision`, `body`; met plans only; private to author |
| POST /api/profile | `bio`, optional `name`, `role`, `area`, `prompt`, `answer`, up to eight `interests`, `company_private`; actor only |
| POST /api/block | `target`; bidirectional discovery/shared-access revocation, relevant inbox removal |
| POST /api/report | `target`, `reason`; queues unreviewed report, no automated decision |
| GET /api/verification | Honest unavailable result; no document upload |
| GET /api/membership | Honest unavailable result; no payment |

## Account / rights

| Method/path | Input / behavior |
|---|---|
| GET /api/account | Own email, status, email-confirmation flag, role, preferences, policy and CSRF; no password/session hash |
| POST /api/preferences | `visible`, `notify` booleans; email confirmation required to publish |
| POST /api/email/resend | Queues new verification, rate-limited; requires configured transport for delivery |
| POST /api/password | `current_password`, new `password`; revokes every session |
| GET /api/sessions | Own session identifiers, expiry, current flag; no raw tokens |
| POST /api/sessions/revoke | `all_other: true` or own session `id` |
| POST /api/account/export | Password reauthentication; own-data export excluding other authors’ private data/credentials |
| POST /api/account/delete | Password reauthentication plus `confirmation: DELETE`; active data deletion, no outside/backup erasure claim |
| GET /api/notifications | Latest 50 generic in-app items plus unread count |
| POST /api/notifications/read | `through` own inbox ID; read state scoped to actor |
| GET /api/appeals | Current appealable decisions and own appeals; no reporter disclosure |
| POST /api/appeal | Active `report_id`, `body`; one pending appeal per case/member |
| POST /api/logout | Deletes current server session |

Suspended members retain rights/account/appeal/password/revocation/logout access but not dating operations. Login does not silently unsuspend an account.

## Moderator only

| Method/path | Input / behavior |
|---|---|
| GET /api/admin/reports | Latest 100 cases and pending appeals; queue read audited |
| POST /api/admin/action | `report_id`, current `version`, `severity` low/medium/high/urgent, `outcome` triage/resolve/suspend/reinstate, `member_reason`; conflict and recusal checks |
| POST /api/admin/appeal | Pending appeal `id`, `decision` upheld/overturned, member-visible `response`; separate reviewer required |

The OS operator assigns moderator roles; no public role-creation API exists. Human staffing, MFA, emergency escalation and final legal policies are not supplied by these endpoints.
