# VESPRA TestFlight handoff for Grok on Greg’s iMac

## Requested result
Finish signing, building and uploading the EXISTING VESPRA Preview to Greg’s private/internal TestFlight. Do not redesign or rebuild the app, publish a public App Store release, or grant Otto new remote access. Greg authorized this VESPRA-only work; unrelated apps/repositories/certificates must remain unchanged.

## Existing project — reuse these records
- Private source: https://github.com/gregoryrhamiltonjr-prog/vespra-preview
- Branch: main. Last source commit verified by Sable: 388081630dc096e6fb4738aa34a222c929311870. Check for newer commits before changing anything.
- Expo account/team: ghamiltonjrs-team; project slug: vespra-preview.
- Expo project ID: 5156f493-e2b8-483e-afed-fd14516f9e53.
- EAS build AND submit profile: testflight-preview (already in eas.json).
- Apple team: JTRPY5VG8W.
- Registered bundle identifier: com.gregoryhamilton.vespra.preview.
- App Store Connect app: VESPRA Preview; Apple ID 6826424016; SKU VESPRA-PREVIEW-001.
- Native version: 0.3.0. EAS remote version/autoIncrement is configured.

## Preview behavior — preserve
The profile enables EXPO_PUBLIC_PREVIEW_MODE=offline. This is a clearly labeled, fictional, single-phone SQLite preview: Alex/Marcus switching simulates both participants. No backend or Railway is needed. No real accounts, cross-device member chat, venue bookings, payments, identity verification or monitored reports are connected. Keep those limitations explicit. Do not enter real sensitive data.

## Last verified progress / blocker
- Private source is pushed; Expo GitHub connection to ONLY this repository is confirmed.
- TypeScript, six native API groups, nine offline groups, and iOS/Android Hermes JavaScript exports passed. Those exports are NOT signed native builds.
- Apple App ID and App Store Connect record are created. Do not create duplicates or reuse the separate Sable/Plateflow app records.
- Expo first-build dialog warns there are no saved build credentials for THIS app.
- An existing saved distribution certificate was selected in an incomplete Expo credentials wizard. Its public serial is 74C42AED741163B0E8F87562AFE09F12. Reuse it if valid and available; do not export private keys into chat or source control.
- The only saved provisioning profile shown belonged to com.gregoryhamilton.plateflow. IT IS NOT VALID FOR VESPRA. A correct App Store distribution profile for VESPRA is still needed.
- Apple’s browser certificate rows were not accessible to Sable’s automation. Do not make Greg identify serial numbers manually. Use the standard guided EAS signing flow or appropriate local Apple developer tools to resolve the certificate/profile match.
- EAS CLI was not authenticated on Otto. Check the iMac’s own existing account/tool state; do not assume it matches Otto.
- Greg said he accepted Apple’s updated Developer Program Agreement, but an Apps-list notice still appeared. Verify current status. If legal acceptance is still required, ask Greg to review/accept securely; do not accept for him.
- No signed EAS build, TestFlight upload or invitation has yet been confirmed by Sable. Recheck before creating duplicate work.

## Execute safely on the iMac
1. Inspect local macOS/build tools and existing Expo/Apple authentication without dumping tokens, environment secrets or keychain contents. Use the actual local username, not a guessed one.
2. Obtain/update the private source with existing authorized GitHub access. Preserve newer work. Check the repo README, eas.json, app.json and security notices.
3. Use guided EAS iOS credential setup (or supported local Apple tooling) to associate a valid distribution certificate and a VESPRA-specific App Store provisioning profile. Do not revoke/replace certificates used by other apps or use a mismatched profile.
4. Keep authentication, 2FA and keychain approvals in the owner-controlled secure local interface. Never ask for passwords/codes/private keys in chat, put them in commands/URLs/logs/repository files, or send them back to Sable. If an owner-only step blocks progress, identify that exact step.
5. Run the existing validation checks, then an iOS App Store-distribution build using profile testflight-preview. Consult installed CLI help for exact syntax. Use existing included quota only; stop for Greg’s approval before any new charge, overage or plan upgrade.
6. Submit the finished signed build to the EXISTING App Store Connect app using the configured submit profile. This means TestFlight upload, not public-release submission. Monitor actual Apple processing/errors.
7. Once eligible, make the build available only to Greg/the existing account holder as an internal tester. Do not enable public links or invite unrelated users. Installation on his iPhone still requires TestFlight and his own Install action.

## Important review boundaries
The saved npm audit reports 15 high-severity dependency-tree findings rooted in braces/node-forge. This is an isolated fictional internal preview, NOT a clean security audit, production approval or authorization for real-member use. Read security/review.md; do not force an incompatible downgrade or silently claim findings resolved. Do not change legal/trader declarations, accept agreements, disable safeguards, expose services publicly or alter unrelated account settings.

## Return evidence — no credentials
Report the commit built, EAS build ID/link, signed build result, submission ID/status, Apple processing result, and internal TestFlight availability/invitation status. Clearly distinguish queued/building/uploaded/processing/available. Do not report success based only on a JS bundle or upload attempt. If blocked, give the precise blocker and last completed step. Never return passwords, recovery/verification codes, private keys, signing archives or access tokens.
