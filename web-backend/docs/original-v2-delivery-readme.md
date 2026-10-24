# VESPRA · v2 working product

**Good chemistry. Better plans.** VES-pruh. Provisional name—not cleared.

V2 adds working account security, recovery and email infrastructure, privacy controls, a human moderation console, appeals, a private inbox, encrypted backup tooling, deployment scaffolding, and a native React Native/Expo client to the original discovery-to-date product. It is **private-evaluation software, not a public-member launch**.

## Start the responsive web app

Python 3.11+ with system timezone data. No backend package installation or provider keys needed for the fictional demo.

```sh
cd vespra
python3 server.py
```

Open **http://127.0.0.1:8765** on the same computer. This is not a public preview URL. The supplied desktop browser cannot access device-local addresses, so it could not perform visual browser QA.

For a separate registered-account evaluation with persona login disabled:

```sh
VESPRA_MODE=private VESPRA_DB=private.sqlite3 python3 server.py
```

Private mode starts without seed profiles and rejects previously issued demo sessions. Registered accounts and fictional personas never share a discovery pool, even in demo mode. Registration/login work locally; email verification/recovery delivery requires the operator’s SMTP transport. Registered profiles start paused and cannot publish before email confirmation. Email confirmation is **not** identity or age verification.

## Test the full journey without integrations

1. Confirm 18+ and explore as fictional Alex.
2. In Connections, return Marcus’s incoming fictional interest to create a mutual match.
3. Send a message in Chats. No artificial reply is generated.
4. Suggest a future date in Date Studio: public place + local time + explicit IANA zone.
5. Switch to Marcus in You (also available in the native client), review, and agree.
6. Find a table returns the real manual-adapter fallback: **no reservation has been made**.
7. Download a discreet calendar event from the web You tab after agreement. It is a static export, not a synchronized calendar integration.
8. After the date’s start time, self-report “We met,” then save an author-only private reflection. No public ratings.
9. Change a proposal to test revision/consent reset. Block a member to revoke shared discovery/chat/plan access.

## New in V2

- Scrypt password hashes, 24-hour sessions, native secure storage, hashed single-use verification/recovery challenges, generic recovery responses, password rotation, session listing/revocation, bounded sessions, and persistent attempt limits.
- Versioned consent and adult eligibility calculation without retaining the submitted birth date. This is self-attestation—not age assurance.
- Editable profile details, visibility pause, email-gated discovery, privacy-preserving inbox preferences, password-confirmed data export and account deletion.
- Moderator-only report queue, severity triage, versioned human decisions, suspension/reinstatement, audited access, member appeals and different-reviewer enforcement. Independent restrictions do not accidentally clear one another.
- Generic in-app updates, foreground web refresh, paginated discovery/message history, indexed queries, serialized consent mutations, and commit-before-acknowledgement.
- Actual SMTP transport with durable bounded retries, expiry checks, and delivered-code redaction; no fake email delivery.
- Provider contracts and truthful disabled/manual implementations for bookings, identity/age assurance, billing and push.
- Native iOS/Android client source and exported Hermes JavaScript bundles, not just WebViews.
- AES-256-GCM encrypted snapshots, integrity/tamper tests, non-overwriting restore, operator checks/retention, non-root Docker scaffold, and CI workflow.

## Native client

See `mobile/README.md`. Requires Node 22.13+ and an appropriate Expo development environment.

```sh
cd mobile
npm ci --ignore-scripts --no-audit --no-fund
npm run typecheck
npm test
npm run start
```

For physical devices/release-style bundles, configure an operator-owned **HTTPS** API origin through `EXPO_PUBLIC_API_URL` before building. That variable is a public origin, never a secret. Unconfigured release builds refuse network requests instead of contacting an invented server. Local emulator HTTP is permitted only in development. `mobile/dist` contains built iOS/Android JS bundles; **no IPA, APK, AAB, signing, store upload or device runtime validation is claimed**.

## Verification

```sh
python3 -m unittest discover -s tests -v
node tests/test_ui.cjs
python3 build_assets.py
cd mobile
npm run typecheck
npm test
npm run bundle
```

Final evidence: **34 Python backend/operator tests; 12 web render/interaction groups; 6 native API groups; 25 text + 4 control-boundary contrast checks; strict TypeScript; iOS and Android JS bundle exports**. Web tests use a DOM stub, not a browser. See `docs/qa.md` and the source/bundle hash manifest.

### Security scan—release blocker

`npm audit --omit=dev` reports **15 high-severity findings** in the Expo dependency tree, rooted in `braces` and `node-forge`. Current installed versions match the registry’s latest versions; the audit suggests an incompatible old Expo downgrade, which was not applied. Full report: `security/npm-audit.json`. This is **not a clean dependency audit**. See `security/review.md`; resolve or formally review before release.

## Configuration

`VESPRA_MODE` = `demo` (default) or `private`; production mode is deliberately unsupported. `VESPRA_HOST` defaults to `127.0.0.1`; `VESPRA_PORT` to `8765`; `VESPRA_DB` to `vespra.sqlite3`; `VESPRA_CITY` to `New York`; `VESPRA_TIMEZONE` to `America/New_York`. `VESPRA_PUBLIC_ORIGIN` sets the exact browser origin. An HTTPS origin enables Secure cookies/HSTS; the operator must actually terminate TLS correctly. `VESPRA_MAIL_CONFIG_FILE` is a protected file path, never a credential value.

Do not expose the Python development HTTP server or demo mode publicly. The Docker recipe is a private evaluation scaffold, not a validated public deployment. No Docker, emulator, Xcode, or deployment account was available here.

## Delivery map

- `public/`: five-tab app, brand SVGs, light/dark design system, account/privacy/safety interfaces, evaluation policies.
- `server.py`, `services.py`, `adapters.py`: API, migrations, authorization, safety workflows, provider boundaries.
- `mobile/`: pinned native client, lockfile, tests and built JS bundles.
- `manage.py`, `ops/backup.mjs`: explicit operator tasks; no scheduler installed.
- `docs/`: brand, API/architecture, tested phase matrix, QA, deployment/operations and naming findings.
- `security/`: actual dependency advisory report and review.

Remaining external gates: approved live providers, hosted TLS/storage configuration, staffed safety operations, final legal/privacy/name clearance, dependency remediation, signing accounts, native binary builds and real-device/accessibility/security QA. These are not claimed complete. See `docs/phases.md` for the exact boundary.

The original specification ended after “Include dark and light themes,”. V2 builds out the remaining work identified in the first delivery; unseen specification sections have not been assumed delivered.
