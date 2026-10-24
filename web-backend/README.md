# VESPRA web client and backend

This directory contains the full responsive five-tab web product and persisted Python/SQLite API, in addition to the native preview at the repository root. It is evaluation software, not an approved public dating service.

## Run locally

Requires Python 3.11+ with system timezone data. From this directory:

```sh
python3 server.py
```

Open http://127.0.0.1:8765 on the same computer. Demo mode uses fictional adults. For an isolated registered-account evaluation:

```sh
VESPRA_MODE=private VESPRA_DB=private.sqlite3 python3 server.py
```

These are local addresses, not hosted previews. No database or user/session data is shipped in this repository; startup creates it locally. Do not expose the development HTTP server publicly.

## Tests

```sh
python3 -m unittest discover -s tests -v
node tests/test_ui.cjs
python3 build_assets.py
```

Node is used for operator encrypted-backup tests and the DOM-stub web tests. No backend package install is required. Native tests/builds run from the repository root, not this directory.

## Included

- server.py / services.py / adapters.py: mutual matches, protected chat, revisioned bilateral Date Studio, accounts/recovery, privacy controls, human moderation/appeals and provider boundaries.
- public/: complete responsive interface, themes, account/safety controls, original SVG brand assets, icon art and evaluation policies.
- manage.py / ops/: migration, retention, mail, operator checks and authenticated encrypted backup/restore tooling.
- tests/: backend/operator and web-render tests.
- Dockerfile / compose.yaml: private-deployment scaffolding; Docker execution was not verified in the original environment.
- docs/: brand guide, architecture, API, QA, naming findings and original V2 delivery evidence. Historical native source paths/hashes in those V2 documents refer to the prior ZIP layout; the current native project lives at this repository’s root.

## Boundaries

Reservations are manual-only; identity/age assurance, billing and push are not live. SMTP needs secure owner-provisioned configuration. No live credentials or signing files belong in Git. The live SQLite database requires operator-provided protected storage. Review docs and security/review.md before any real-member pilot. Existing dependency advisories and browser/device/signing/legal/operational release gates are not waived by publishing source.

For the Mac-side signing task, use ../GROK_HANDOFF.md. GitHub source publication is not a signed build or TestFlight upload.
