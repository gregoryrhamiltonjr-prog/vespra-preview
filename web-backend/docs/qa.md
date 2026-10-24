# V2 QA evidence and remaining acceptance

## Executed checks

### Python backend and operator suite: 34 tests

`python3 -m unittest discover -s tests -v`

- Original 13 tests: adult demo gate, mutual interest/idempotency, matched-only chat, CSRF/Origin, bilateral plan agreement, honest reservation handoff, stale-revision rejection/reset, cancellation, block revocation, report truthfulness, meeting time gate, reflection privacy, profile/logout and security headers.
- V2 account/safety tests: consent and age eligibility; paused registration; demo/registered isolation; old demo sessions rejected in private mode; persistent failed-login throttling; generic single-use recovery/session revocation; email confirmation distinct from identity; session/password rotation; own-data export; deletion/shared-record cleanup; moderator RBAC/versioning/suspension; independent reviewer even after audit retention; independent case restrictions; private notifications/read state/block cleanup; paginated discovery/history and native session contract; mail retry/redaction; retention; unavailable providers.
- Operational tests: idempotent private migration/no seeds, authenticated encrypted backup/restore and tamper rejection, key-permission/exclusive-write checks, safe operator status output.

### Web tests: 12 groups

`node tests/test_ui.cjs` uses a minimal DOM stub, not a browser. Groups cover five-tab rendering, fictional labels, escaped message/profile names, proposal waiting/booking disclaimer, agreed actions, explicit timezone form, adult/provisional-name onboarding, private-mode demo hiding, account/privacy and moderator UI gating, masked credentials/consent, and retained CSRF on restricted-account rights/appeal mutations.

### Native tests: 6 groups plus strict TypeScript

`npm run typecheck` and `npm test` in `mobile/`.

API tests cover unconfigured release refusal, remote-HTTP refusal in development, SecureStore/authenticated headers, complete logout cleanup, expired-session cleanup, and origin-bound session restoration. SecureStore/network are mocked; real Keychain/Keystore behavior has not been tested on a device.

### Native JavaScript exports

`npm run bundle` produced separate iOS and Android Hermes bundles with Expo/Metro. Included in `mobile/dist/`. This is **not** an IPA/APK/AAB, native compiler/signing result, simulator run, device execution, or store submission. Build hashes are recorded in `docs/build-manifest.json`.

### Contrast and static checks

`python3 build_assets.py`: 25 actual text/background pairings pass 4.5:1; 4 control-boundary/background pairings pass 3:1. Numeric report in `contrast.md`. Placeholders use the tested muted token. Web reduced motion disables transitions; native modal observes the OS reduce-motion setting. These checks do not establish full WCAG conformance.

Python/JavaScript syntax checks pass. Original symbol/icon assets rasterized successfully; the size specimen was visually inspected. Convergent silhouette/doorway division is visible at 24/32/48px; conceptual detail is weak at 16px, reserved for favicon use. No human recognition study is claimed.

## Known release-blocking scan result

`npm audit --omit=dev` reports **15 high-severity dependency-tree findings** rooted in braces and node-forge. The machine-readable report and interpretation are under `security/`. No incompatible forced downgrade or unsupported clean-security claim was made.

## Checks blocked by this environment

- The provided desktop browser refused `http://127.0.0.1:8765`: “The browser cannot reach private or device-local addresses.” No bypass was used.
- Docker was not installed: Docker/compose build execution is unverified.
- Xcode, Android SDK and emulators were absent: native binaries, device rendering and signing were not executed.
- No hosting account/target or live partner configuration was supplied: no public preview, provider-confirmed booking, real email, identity/age check, payment or push was performed.

## Required acceptance before a real-member pilot

1. Safari/iOS, Chrome/Android and desktop engines at 320/375/390/768/1440px; large text and 200% zoom; long names and multilingual edge cases.
2. VoiceOver/TalkBack/keyboard: dialog focus/name/restoration, tab order, form validation, live feedback, readable large text, reduced motion, touch reach and safe areas.
3. Full two-device bilateral plan revision/acceptance and blocked/deleted/suspended actor cases; expired-session and weak-network states; calendar staleness comprehension.
4. Independent security/load review, moderator MFA, audit access controls, live age-assurance decision, encrypted hosting and deletion-after-restore drill.
5. Staffed moderation/escalation and second-reviewer appeal exercises, policy/contact/legal review, provider sandbox/live tests, trademark/domain/store checks.
6. Resolve or independently assess the recorded dependency advisories, rebuild/re-audit, then signed native builds and store privacy review.

Successful local tests are evidence of implemented behavior—not operational staffing, legal clearance, provider approval, accessibility certification or release readiness.
