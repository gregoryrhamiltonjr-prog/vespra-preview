import json, os, sqlite3, subprocess, tempfile, unittest
from pathlib import Path
from contextlib import closing
ROOT=Path(__file__).resolve().parents[1]

class OperationalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.d=Path(self.tmp.name);self.env={**os.environ,'VESPRA_DB':str(self.d/'active.sqlite3'),'VESPRA_MODE':'private','PYTHONDONTWRITEBYTECODE':'1'}
    def tearDown(self):self.tmp.cleanup()
    def command(self,*args,success=True):
        r=subprocess.run(args,cwd=ROOT,env=self.env,text=True,capture_output=True)
        self.assertEqual(r.returncode==0,success,r.stderr if success else 'Unexpected success')
        return r
    def test_private_migration_is_idempotent_and_does_not_seed(self):
        self.command('python3','manage.py','migrate');self.command('python3','manage.py','migrate')
        with closing(sqlite3.connect(self.env['VESPRA_DB'])) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM profiles').fetchone()[0],0);self.assertEqual(db.execute('SELECT COUNT(*) FROM schema_versions').fetchone()[0],1)
    def test_authenticated_backup_restore_and_tamper_rejection(self):
        self.command('python3','manage.py','migrate');key=self.d/'private.key';snapshot=self.d/'encrypted.backup';restore=self.d/'restored.sqlite3'
        self.command('node','ops/backup.mjs','init-key',str(key));self.assertEqual(key.stat().st_mode&0o077,0)
        self.command('python3','manage.py','backup',str(snapshot),'--key-file',str(key));self.command('python3','manage.py','verify-backup',str(snapshot),'--key-file',str(key));self.command('python3','manage.py','restore',str(snapshot),str(restore),'--key-file',str(key))
        with closing(sqlite3.connect(restore)) as db:self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
        self.command('python3','manage.py','restore',str(snapshot),str(restore),'--key-file',str(key),success=False)
        raw=bytearray(snapshot.read_bytes());raw[-1]^=1;snapshot.write_bytes(raw)
        self.command('node','ops/backup.mjs','decrypt',str(snapshot),str(self.d/'bad.sqlite3'),str(key),success=False);self.assertFalse((self.d/'bad.sqlite3').exists())
    def test_key_permissions_and_overwrite_are_rejected(self):
        key=self.d/'private.key';self.command('node','ops/backup.mjs','init-key',str(key));self.command('node','ops/backup.mjs','init-key',str(key),success=False)
        key.chmod(0o644);source=self.d/'plain';source.write_text('test-only-data');self.command('node','ops/backup.mjs','encrypt',str(source),str(self.d/'out'),str(key),success=False)
    def test_check_exposes_counts_not_secrets(self):
        r=self.command('python3','manage.py','check');data=json.loads(r.stdout);self.assertEqual(data['database'],'ok');self.assertEqual(data['mode'],'private');self.assertNotIn('password',r.stdout);self.assertNotIn('token',r.stdout)

if __name__=='__main__':unittest.main(verbosity=2)
