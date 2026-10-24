# VESPRA · compact brand and interface guide

## Strategy

Promise: meet someone interesting and make the date happen. Audience: adults 18+, primarily gay men, explicitly including trans men and welcoming compatible bi and queer men. Professional means ambition, curiosity, kindness, and respect for time—not employer, degree, income, or prestige. NYC / English is the initial configuration.

Measure successful, mutually wanted dates and comfortable coordination. Do not optimize swipe volume or rank members by desirability. Future instrumentation should use aggregate, privacy-reviewed measures such as mutual match → agreed plan and optional private comfort feedback, not public ratings.

## Identity

Original vector wordmark: `public/brand/wordmark.svg`; reversed variant alongside it. Letterforms are editable path geometry, not outlined third-party typography. Symbol: two sloping paths meet the top edges of a doorway; the central spine and opening imply a subtle V-like convergence. Treat it as an invitation, not a closed badge. App-icon artwork is original SVG, not a release-ready app-store raster export.

Use midnight ink on pearl, or pearl on midnight. Citron is an accent, not a field of continuous visual noise. Do not add gradients to the symbol, skew it, use status-coded logo colors, or mimic another app’s icon.

Clear space: at least one symbol stroke width (4 units in the 48×40 master) on every side. For lockups, leave at least 12 units between symbol and wordmark. Recommended wordmark minimum: 112px wide; symbol minimum: 24px wide, with a dedicated 16px favicon exception. Below 24px use the symbol alone; omit any tagline. The included `size-specimen.svg` displays 16, 24, 32, and 48px versions. Raster checks are available in the delivery; real-device small-size recognition remains a QA item, not validated user research.

## Color

- Midnight ink `#111820`: anchor, inverse surfaces, primary text.
- Warm pearl `#F4F1EA`: warmth and breathing room.
- Electric citron `#D8F275`: sparing action and brand emphasis; use ink text.
- Slate `#8996A6`: decorative accent, **not** light-theme body text.
- Light theme: surface `#FFFDF8`, muted text `#52606D`, success `#216343`, warning `#805400`, error `#A32638`.
- Dark theme: surface `#1D2731`, muted `#B7C2CC`, success `#93D8B0`, warning `#F5CA7A`, error `#FF9DA8`.

`contrast.md` calculates every defined text/background token combination used by the interface. Twenty-five pairings pass 4.5:1. Borders and decorative artwork are not text and are not covered by that claim. Semantic meaning also appears in words, not color alone.

## Typography and assets

Editorial headings use the device’s Georgia / Times serif; UI text uses the system UI stack. These fonts are referenced on the user’s device, not redistributed, downloaded, or claimed as an included font license. Logo paths and member illustrations are original. No stock photos, branded venue assets, or third-party asset bundles are included. If custom fonts are introduced later, require documented redistribution and app-embedding licenses.

Heading: 38–64px, tight leading, restrained negative tracking. Section heading: 30px. Body: 15px / 1.55. Controls: 13–15px. Eyebrow: 11px with 2px tracking. Do not set long paragraphs in uppercase.

## Tokens and component contract

CSS source of truth: `public/style.css`, with tokens / base / components cascade layers.

- Spacing: 4, 8, 12, 16, 24, 32, 48px.
- Radii: 12px controls, 24px cards and sheets, pill action buttons.
- Elevation: restrained 16px/40px ink shadow; modal gets strongest elevation.
- Motion: 180ms ease on action hover; disabled by reduced-motion preference.
- Buttons: primary citron/ink, inverse ink/pearl, outlined, danger; 44–46px touch heights. Send/save forms disable submit while awaiting results. Pending requests have error toasts and can be retried.
- Inputs: persistent labels, visible focus outlines, native validation, server-side validation.
- Chips: interests and non-sensitive state, never wealth or desirability badges.
- Profile cards: original avatar, explicit fictional label, age, approximate neighborhood, role, bio, interests, interest action.
- Sheets: native modal dialog; labeled close button; Escape follows native dialog behavior.
- Navigation: five persistent tabs; bottom bar on mobile, sidebar on desktop; `aria-current`.
- Toasts: live status region; plain-language success and failure.
- Loading: explicit initial loading state; no imitation of live activity.
- Avatar: fictional original SVG, no external image calls.
- Date cards: proposal/agreement/meeting progression, revision number, bilateral acceptance count, explicit booking disclaimer.

## Voice

Warm, assured, direct, lightly playful: “Make room for someone new.” “Suggest a time.” “Find a table.” “Keep your company private.” Avoid “elite,” “high value,” “top tier,” and employer-based status. Never imply a reported person has been reviewed, identity-verified, or punished without operational evidence.

## Themes and accessibility

Respect initial system theme and save explicit changes locally. Respect reduced motion. Use semantic forms, navigation, heading hierarchy, skip link, accessible names, live feedback, and native modal focus handling. Browser/device verification is still required before asserting full accessibility compliance. There is no claim that contrast calculations alone establish WCAG conformance.
