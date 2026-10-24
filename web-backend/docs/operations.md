# Private evaluation operations

## Scope

No server has been deployed publicly. No scheduler or service configuration was installed. The attached Docker/compose and CI files are source artifacts. Docker, Xcode, Android SDK and emulators were absent here. The provided desktop browser cannot reach local addresses. Do not interpret these files as completed hosting or release approval.

## Isolated account evaluation

Run a new database instead of reusing the fictional pool:

```sh
VESPRA_MODE=private VESPRA_DB=private.sqlite3 python3 server.py
```

Keep mode, database and public-origin settings consistent for every management command. The default origin is local HTTP. A remotely accessible staging deployment needs operator-provided TLS, encrypted disk, trusted proxy configuration, network limits, access controls and monitoring. Set VESPRA_PUBLIC_ORIGIN to the actual HTTPS origin; setting that string alone does not create TLS. Host/Origin checks and Secure cookies derive from it. Production mode is deliberately unsupported.

`docker compose up --build` describes a loopback-only private evaluation, non-root user, read-only root filesystem and persistent `/data` volume. It has not been built in this environment. Inspect before use. Host-side encrypted backup tooling requires Node 18+; the minimal Python container does not include Node. The image does include `manage.py` for checks/mail/retention. Do not assume a named Docker volume is encrypted or safely exported by copying a live SQLite main file alone.

## Health, migration and roles

```sh
python3 manage.py migrate
python3 manage.py check
```

Startup migration is idempotent and preserves V1 data. `/healthz` checks schema access and returns readiness/mode/version without member data. `check` reports integrity, schema, queue counts and configured-mail status; it does not display addresses or credentials.

Moderator access is never self-selected in signup. A trusted OS operator grants it to a registered account ID:

```sh
python3 manage.py role ACCOUNT_ID moderator
```

Use an actual internal account ID in place of ACCOUNT_ID. Role changes are audited. At least two trained moderators are needed to exercise independent appeal review. In the web You tab, a moderator sees **Open safety console**. Never grant access merely to make a review look completed. MFA and staffing are still release gates.

## SMTP provisioning and worker

The operator provisions a protected JSON file **outside the workspace/source archive**, using their secure local setup. Do not paste its contents or credentials into chat, command arguments, URLs, logs, or environment variables. `VESPRA_MAIL_CONFIG_FILE` contains only the file’s path. The file must be mode 600 or stricter and contains these fields: `host`, optional `port` (465 by default), `from`, optional `username` and `password`. SMTP_SSL with certificate verification is used. Provider approval, sender-domain authorization, policies and live delivery testing are the operator’s responsibility.

```sh
python3 manage.py mail
```

The mail worker sends up to 20 eligible rows per invocation. No configured transport means deferred/failed statuses—not pretend delivery. Retry count is capped at five with exponential backoff; expired codes are not delivered. Successful bodies are scrubbed. Counts are logged, not recipient addresses or codes. A worker crash can cause duplicate email; challenge redemption remains one-use. Tests inject fake transports; no real email was sent here.

## Explicit retention

```sh
python3 manage.py retention
```

This clears expired sessions/challenges/rate limits, notifications older than 30 days, mail older than two days, audit older than 90 days. It does not invent a background schedule. Review policy and legal requirements before arranging recurring execution. The original suspension reviewer is stored with the case, so audit retention does not enable self-review of an appeal.

## Authenticated encrypted backup

Node’s built-in AES-256-GCM implementation encrypts a consistent SQLite online snapshot. Key material is never printed. Protect the operator machine and temporary storage; logical deletion of temporary plaintext is not a secure wipe.

```sh
node ops/backup.mjs init-key /private/operator/backup.key
python3 manage.py backup /private/backups/evaluation.backup --key-file /private/operator/backup.key
python3 manage.py verify-backup /private/backups/evaluation.backup --key-file /private/operator/backup.key
```

Paths are illustrative. Use directories the operator owns, keep the key separate from backups, restrict access, and define off-device storage and expiry. Neither encryption nor key generation provisions an offsite backup service. The key file and destinations are created exclusively; existing files are not overwritten. Losing the key makes snapshots unrecoverable. A corrupted/tampered snapshot is rejected before plaintext is written.

## Restore

```sh
python3 manage.py restore /private/backups/evaluation.backup /private/recovery/restored.sqlite3 --key-file /private/operator/backup.key
```

Restore authenticates, decrypts, checks SQLite integrity and writes **only a new destination**. It never replaces a running database. Review the restored data and stop the relevant evaluation server yourself before choosing a new VESPRA_DB path for a later start. Do not restore into active service until reconciling post-snapshot account deletions and moderation changes. Automatic tombstone reconciliation/legal holds are not implemented; old snapshots can resurrect deleted information. Backup expiration and deletion-after-restore drills are required release controls.

## Incident and release handling

- Reports need a staffed human, documented escalation and an incident contact. The UI never promises emergency response.
- Preserve appropriate evidence only under a legally reviewed policy; the evaluation delete path currently removes report records and has no legal-hold feature.
- Revoke sessions/rotate affected credentials through appropriate owner-controlled systems if compromised. Do not ask users for secrets in chat.
- Review `security/npm-audit.json`; the mobile dependency tree is not clean. Do not apply the suggested incompatible old Expo downgrade blindly.
- Run the full test suite and real browser/device, accessibility, load and security acceptance before any pilot. Get final policy, privacy, age-assurance, trademark/domain and app-store review.
