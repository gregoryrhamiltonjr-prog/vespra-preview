# Dependency and security review · 23 October 2026

## Result: release blocked, not clean

`npm audit --omit=dev --audit-level=high` returned **15 high-severity dependency-tree findings**. The two root advisories are:

- `braces` stack-exhaustion denial of service via deeply nested patterns: GHSA-vfj7-8cjw-p6xm.
- `node-forge` RSA PKCS#1 v1.5 signature verification accepting extra nested DigestAlgorithm elements: GHSA-86w9-cpqp-85rv.

The other reported packages are affected dependency paths through Expo/Metro and React Native tooling, not fifteen independent root flaws. The saved machine-readable report is `npm-audit.json`. Audit classification is retained, not silently downgraded because a package is used by tooling.

Installed `braces` 3.0.3 and `node-forge` 1.4.0 matched the registry’s latest versions at the check. Expo 58.0.17 and React Native 0.88.0 also matched current latest releases. The audit marks all available versions of the two root packages affected and suggests a breaking downgrade to Expo 44.0.6 for resolution. That downgrade was **not applied**: it would replace the current compatible platform stack and is not demonstrated to be a secure fix.

These dependency paths are associated with file-pattern processing and Expo CLI/code-signing tooling. This is not proof they are exploitable in this particular product, nor proof they are harmless. Device-runtime reachability, build-input threat modeling, and any mitigation need independent review. Do not publish, enable untrusted build inputs/updates, or assert clean supply-chain security based on successful compilation. Use trusted local build inputs only during isolated evaluation.

## Required next action

Before release, obtain a compatible upstream fix or a reviewed, tested replacement/patch; regenerate the lockfile; re-run typecheck, API and product tests, both bundles and the full audit; assess native runtime and signing/update paths. No forced or unreviewed dependency overrides are included. No deployment or store publication was performed.

## Application checks actually exercised

Authentication/CSRF/Origin/Host boundaries, cookie flags, demo isolation, rate limits, challenge reuse/revocation, actor-bound resource access, bilateral date revision consent, per-author reflection privacy, export/deletion boundaries, moderator RBAC and reviewer recusal, independent restrictions, mail retry/redaction, snapshot tamper detection and non-overwrite restore have automated coverage. This is **not a penetration test, cryptographic audit, full WCAG audit or SOC compliance claim**.

Remaining application release gates include MFA, age assurance, protected/admin operational infrastructure, encrypted live storage, safe deletion-history reconciliation after restore, final evidence-preservation policy, real-device/browser QA, load/concurrency analysis beyond the local tests, and independent security review.
