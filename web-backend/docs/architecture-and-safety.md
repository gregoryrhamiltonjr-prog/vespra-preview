# V2 architecture and safety boundaries

## Runtime and data

Same-origin responsive web and native bearer clients → Python JSON API → SQLite WAL. Native uses React Native/Expo and platform SecureStore; web uses HttpOnly/SameSite=Strict cookies. No remote fonts, stock photos, analytics or ad SDKs. `server.py` owns transport/core dating; `services.py` owns account/privacy/safety/inbox logic; `adapters.py` owns integration contracts and SMTP. Backend requests have no third-party Python dependencies.

Migrations are idempotent and preserve V1 tables. Added entities: registered accounts, versioned consent, hashed auth challenges, persistent rate buckets, private inbox, mail outbox, audit, report reviews, appeals, reservation requests, schema versions. Indexes support messages, plans, reports, sessions and inbox. POST operations acquire a SQLite immediate transaction so consent checks and writes serialize. Responses commit before acknowledging success. SQLite remains single-instance evaluation storage, not a horizontally scaled design.

API projections prevent email/password/session material from entering discovery. Discovery and message-history pagination bound retrieval. The aggregate state endpoint includes up to 200 discoverable profiles and the latest 200 accessible messages. Hidden-but-matched profiles are marked connection-only and do not re-enter discovery. Paused/unavailable one-sided interests are excluded to avoid exposing hidden profiles. Fictional and registered pools never mix; private mode rejects old demo sessions.

## Account and request security

Scrypt parameters: N=16384, r=8, p=1, 16-byte random salt, 32-byte result. Passwords 12–128 characters. Unknown-email login performs equivalent hash work and uses a generic error. Verification/recovery challenges have high entropy, only their hashes enter the challenge table, expire in 30 minutes, and are single-use. A valid password reset revokes every session. Email verification is explicitly not identity/age verification.

Sessions: random 32-byte URL-safe tokens hashed in SQLite; 24-hour expiry; maximum ten sessions/member. Web HttpOnly/SameSite cookies, Secure when public origin is HTTPS, and CSRF on authenticated mutations. Native receives a bearer token only when requesting the native contract and stores it in device-only SecureStore. Account settings provide session inventory/revocation and password rotation. Restricted members can use account/export/delete/appeal paths but not discovery/chat/date mutations. Registered account credentials cannot be acquired through demo impersonation.

POST requires JSON, caps body length, checks supplied Origin, limits authentication and actor writes, and uses parameterized SQL. Browser requests have CSP, nosniff, no-referrer, no-store and HTTPS-mode HSTS. Host validation limits rebinding exposure. Client text is escaped, including member names inside action labels. Database files are mode 600. There is no claim of an independent penetration test, volume encryption, TLS termination, MFA, or distributed rate limiting. Deploy behind a reviewed HTTPS infrastructure; do not expose the development HTTP server directly.

## Date Studio and notifications

`proposed → agreed → met`, with active-plan cancellation. The proposer accepts revision 1. Both participants must accept the exact current revision. Changes increment the revision, reset consent and clear the manual booking-handoff state. Stale writes return 409. Meeting is a participant’s self-report after the agreed start time, not attendance verification. Reflections are author-only and never rankings.

Each date stores an offset-bearing timestamp plus its IANA timezone. Nonexistent/ambiguous DST times and past proposals are rejected. A public place is required as text; venue identity, actual availability and the physical safety of a venue are not verified.

Transactional inbox events contain generic titles, kinds and opaque entity IDs, never chat previews. Foreground web refresh pauses while editing or a dialog is open. Native refreshes on foreground/pull. This is bounded refresh, not WebSocket delivery. No background push is sent. Blocks revoke both directions’ discovery and shared match access and delete relevant inbox entries. Cancelling a local plan does not claim to cancel an outside booking.

## Human safety workflows

A registered member can submit a report; receiving it does not mean judgment or review occurred. Only accounts explicitly assigned a moderator role by a trusted OS operator can read the queue. Queue reads and human actions are audited. Cases have severity and optimistic versions; stale reviews return 409. Moderators cannot handle cases involving themselves or a report they submitted. Suspension revokes current sessions; subsequent login is restricted to rights/appeal/account actions.

Active restrictions are per case. Reinstating one case does not clear another active restriction. Original suspension reviewer identity is retained with the case independently of routine audit retention. Appeals cannot be decided by the sanctioning moderator, the subject or reporter. A second moderator can uphold or overturn; no automatic favorable judgment is invented. Member-visible decisions omit reporter identity and internal queue content.

The console is working software, **not staffed operations**. It does not dispatch emergency services, provide coverage, automatically classify harm, or guarantee response times. There are no uploads/media features in this version; no claim of image scanning. Immediate US danger guidance is 911. Staff, escalation, preservation/holds, incident training, and a legal review are prerequisites to real-member use. Moderator MFA is not implemented.

## Privacy and retention

Registration records consent version and adult attestation. The birth date is used for age calculation then discarded; displayed age is the registration-time snapshot, not an automatically updated birthday record. Profiles start paused. No precise GPS or employer field is collected. Public role/bio text remains the member’s own disclosure; a company-privacy setting is not a parser that redacts free-text employer mentions.

Export requires password confirmation and includes the member’s own sent messages, profile, plans, consents, reports and reflections—not other members’ private reflections, password hashes, session tokens or internal audit records. Deletion requires password plus the exact DELETE confirmation and removes active account/credential/profile, shared chat/date records, related inbox/interest/report/reflection records. The other participant loses those local shared records. No forensic disk erasure, outside-booking deletion, downloaded-file deletion or backup deletion is claimed.

Operator-invoked retention removes expired sessions/challenges/buckets, 30-day inbox, two-day mail and 90-day audit. No scheduler is installed. Other records persist until deletion. Encrypted snapshots use AES-256-GCM with separately stored private key files, authenticated restore and no-overwrite destinations. The live database itself needs operator-provided encrypted storage. Restoring an old snapshot can resurrect previously deleted data; restoring into service requires reconciliation with deletion history and approved backup expiry. An automated tombstone/hold system is not implemented, so this is a release gate.

## Provider boundaries

SMTP is real stdlib SMTP-over-TLS with credentials loaded from a mode-600 owner-provisioned file. The transactional outbox retries at most five times with backoff, skips expired codes, scrubs bodies after delivery and never logs recipients/codes. The explicit mail worker must be run by an operator; a queue insert is not a delivery claim. At-least-once delivery is possible across a worker crash.

Bookings use a protocol with idempotency input, reserve/cancel methods and explicit status/reference output. The shipped provider is manual-only; durable `(date_id, revision)` requests prevent duplicate handoff records. There is no fabricated partner endpoint or confirmation. Identity, billing and push expose disabled implementations returning unavailable/not-sent. Live adapters need legitimate documented partner contracts, consent boundaries, host-owned credentials, sandbox validation and webhook verification. No named partner compatibility is claimed.

## Deployment and release

Non-root Docker/private compose and CI are supplied but Docker was unavailable to execute here. Expo produced iOS/Android JS bundles, not signed binaries. No deployment account was connected. The desktop browser rejected private addresses, preventing browser/device QA. There are 15 high-severity npm dependency-tree findings; see `security/review.md`.

Only `demo` and `private` evaluation modes are supported. Operational readiness, final policies/name clearance, provider integrations, dependency remediation, signed native builds, accessibility/device QA, load/security testing, encrypted hosting, backups and staffed safety remain explicit release gates.
