"""Explicit operator tasks. No implicit scheduler and no credential output."""
import argparse, datetime, json, os, sqlite3, subprocess, tempfile
from pathlib import Path
from contextlib import closing
import server, services, adapters

def main():
    parser=argparse.ArgumentParser(description='VESPRA private evaluation operator tools')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('migrate');sub.add_parser('retention');sub.add_parser('mail');sub.add_parser('check')
    p=sub.add_parser('role');p.add_argument('user_id');p.add_argument('role',choices=['member','moderator'])
    p=sub.add_parser('backup');p.add_argument('destination');p.add_argument('--key-file',required=True)
    p=sub.add_parser('verify-backup');p.add_argument('snapshot');p.add_argument('--key-file',required=True)
    p=sub.add_parser('restore');p.add_argument('snapshot');p.add_argument('destination');p.add_argument('--key-file',required=True)
    args=parser.parse_args();os.umask(0o077)
    if args.command in ('verify-backup','restore'):
        with tempfile.TemporaryDirectory(prefix='vespra-restore-') as d:
            plain=Path(d)/'snapshot.sqlite3'
            subprocess.run(['node',str(server.ROOT/'ops'/'backup.mjs'),'decrypt',args.snapshot,str(plain),args.key_file],check=True)
            with closing(sqlite3.connect(plain)) as source:
                if source.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise RuntimeError('Snapshot integrity check failed.')
                if args.command=='restore':
                    dest=Path(args.destination)
                    # Restore is deliberately non-overwriting, avoiding running-database corruption.
                    with dest.open('xb') as target:target.write(plain.read_bytes())
        print('Authenticated backup verified.' if args.command=='verify-backup' else 'Restored to a new destination. Start a stopped server against that path after review.')
        return
    server.initialize()
    if args.command=='backup':
        with tempfile.TemporaryDirectory(prefix='vespra-backup-') as d:
            plain=Path(d)/'snapshot.sqlite3'
            with server.connect() as source,closing(sqlite3.connect(plain)) as dest:source.backup(dest)
            subprocess.run(['node',str(server.ROOT/'ops'/'backup.mjs'),'encrypt',str(plain),args.destination,args.key_file],check=True)
        print('SQLite online snapshot completed. Keep the decryption key separately.')
        return
    with server.connect() as db:
        if args.command=='migrate':print('Schema migrated to version 2; existing data preserved.')
        elif args.command=='retention':print(json.dumps(services.retention(db),sort_keys=True))
        elif args.command=='mail':
            db.execute('BEGIN IMMEDIATE');print(json.dumps(adapters.deliver_mail(db),sort_keys=True))
        elif args.command=='role':
            if not services.account(db,args.user_id):raise RuntimeError('Registered account not found.')
            db.execute('UPDATE accounts SET role=? WHERE user_id=?',(args.role,args.user_id));services.audit(db,'local-operator','role.'+args.role,args.user_id);print('Role updated and audited.')
        elif args.command=='check':
            print(json.dumps({'database':db.execute('PRAGMA quick_check').fetchone()[0],'schema':db.execute('SELECT MAX(version) FROM schema_versions').fetchone()[0],'mode':server.MODE,'mail_configured':bool(os.environ.get('VESPRA_MAIL_CONFIG_FILE')),'reports_waiting':db.execute("SELECT COUNT(*) FROM reports WHERE status!='resolved'").fetchone()[0],'pending_appeals':db.execute("SELECT COUNT(*) FROM appeals WHERE status='pending'").fetchone()[0]},sort_keys=True))
if __name__=='__main__':main()
