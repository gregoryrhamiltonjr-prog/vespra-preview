# VESPRA Preview

Private, fictional-data iPhone evaluation. Provisional name; no trademark or store clearance claim.

The `testflight-preview` EAS profile enables `EXPO_PUBLIC_PREVIEW_MODE=offline`. The app stores fictional profiles, chats, revisioned plans, per-persona reflections and unsent reports only in on-device SQLite. Alex/Marcus switching simulates both sides on one phone. No real account, member messaging, venue booking, identity check, payment, push or staffed moderation is connected. No backend hosting is required for this preview.

## Check

Node 22.13+; `npm ci --ignore-scripts --no-audit --no-fund`, then `npm run typecheck` and `npm test`. `EXPO_PUBLIC_PREVIEW_MODE=offline npm run bundle` exports both platform JS bundles, not signed apps. EAS signing and App Store Connect processing are required before TestFlight installation.

## Release boundary

This is an internal preview, not a public dating service. Do not enter real sensitive data. Known dependency advisories are recorded under `security/`; this is not a clean security audit or release approval. Dependencies retain their own licenses in THIRD_PARTY_NOTICES.txt. No signing credentials, account passwords, backend data, or tokens belong in this repository.
