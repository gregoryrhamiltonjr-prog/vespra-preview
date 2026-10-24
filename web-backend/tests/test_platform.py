import datetime, json, sqlite3, time, unittest
from unittest.mock import patch
import test_product as base
import services, adapters, server

PASSWORD='Test-only-long-phrase-2026'

class PlatformTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):base.ProductTests.setUpClass.__func__(cls)
    @classmethod
    def tearDownClass(cls):base.ProductTests.tearDownClass.__func__(cls)
    def setUp(self):
        with server.connect() as db:
            for table in ['reservation_requests','report_reviews','appeals','consents','auth_challenges','inbox','mail_outbox','audit','limits','accounts']:
                db.execute('DELETE FROM '+table)
            for table in ['reflections','acceptances','dates','messages','matches','likes','reports','blocks','sessions']:db.execute('DELETE FROM '+table)
            db.execute("DELETE FROM profiles WHERE id NOT IN ('alex','marcus','daniel','rafael','eli','james')")
            db.execute("INSERT INTO likes VALUES('marcus','alex')")
        self.a=base.Client().login('alex');self.b=base.Client().login('marcus')
    def registered(self,label='new',verified=True,moderator=False):
        c=base.Client();address=label+'@example.invalid'
        code,r=c.request('register',{'name':label,'email':address,'password':PASSWORD,'birth_date':'1990-01-01','adult':True,'policy':services.POLICY});self.assertEqual(code,200)
        code,r=c.request('login',{'email':address,'password':PASSWORD});self.assertEqual(code,200);c.csrf=r['csrf']
        uid=c.state()['me']['id']
        with server.connect() as db:db.execute('UPDATE accounts SET email_verified=?,visible=?,role=? WHERE user_id=?',(int(verified),int(verified),'moderator' if moderator else 'member',uid))
        return c,uid
    def test_registration_consent_and_underage(self):
        c=base.Client();p={'name':'New','email':'new@example.invalid','password':PASSWORD,'birth_date':'2015-01-01','adult':True,'policy':services.POLICY}
        self.assertEqual(c.request('register',p)[0],400);p['birth_date']='1990-01-01';p['policy']='old';self.assertEqual(c.request('register',p)[0],400)
        c,uid=self.registered(verified=False)
        self.assertFalse(c.request('account')[1]['account']['visible']);self.assertEqual(c.request('preferences',{'visible':True,'notify':True})[0],400)
        with server.connect() as db:
            self.assertNotIn(PASSWORD,db.execute('SELECT password_hash FROM accounts').fetchone()[0]);self.assertEqual(db.execute('SELECT policy FROM consents').fetchone()[0],services.POLICY)
    def test_demo_cannot_impersonate_registered_account(self):
        c,uid=self.registered();self.assertEqual(self.a.request('demo',{'adult':True,'user':uid})[0],400)
        self.assertEqual(c.state()['people'],[]);self.assertFalse(any(p['id']==uid for p in self.a.state()['people']))
    def test_private_mode_disables_demo_and_seed(self):
        with patch.object(server,'DEMO',False):
            self.assertEqual(base.Client().request('demo',{'adult':True,'user':'alex'})[0],404)
            self.assertEqual(self.a.request('state')[0],401)
    def test_failed_login_rate_limit_persists(self):
        c,uid=self.registered()
        results=[c.request('login',{'email':'new@example.invalid','password':'incorrect-password'})[0] for _ in range(9)]
        self.assertIn(429,results);self.assertIn(401,results)
    def test_recovery_is_generic_one_use_and_revokes_sessions(self):
        c,uid=self.registered()
        r1=c.request('recovery/request',{'email':'new@example.invalid'})[1];r2=c.request('recovery/request',{'email':'absent@example.invalid'})[1];self.assertEqual(r1,r2)
        with server.connect() as db:code=services.challenge(db,uid,'reset')
        d=base.Client();self.assertEqual(d.request('recovery/complete',{'code':code,'password':'Another-test-only-long-phrase'})[0],200)
        self.assertEqual(c.request('state')[0],401);self.assertEqual(d.request('recovery/complete',{'code':code,'password':PASSWORD})[0],400)
    def test_email_verification_is_not_identity(self):
        c,uid=self.registered(verified=False)
        with server.connect() as db:code=services.challenge(db,uid,'verify')
        self.assertEqual(c.request('email/verify',{'code':code})[0],200);self.assertEqual(c.request('email/verify',{'code':code})[0],400)
        self.assertEqual(c.request('preferences',{'visible':True,'notify':True})[0],200);self.assertIn('not',c.request('verification')[1]['message'].lower())
    def test_sessions_and_password_rotation(self):
        c,uid=self.registered();d=base.Client();r=d.request('login',{'email':'new@example.invalid','password':PASSWORD})[1];d.csrf=r['csrf']
        self.assertEqual(len(c.request('sessions')[1]['sessions']),2);c.request('sessions/revoke',{'all_other':True});self.assertEqual(d.request('state')[0],401)
        self.assertEqual(c.request('password',{'current_password':'wrong','password':PASSWORD})[0],403)
        self.assertEqual(c.request('password',{'current_password':PASSWORD,'password':'New-test-only-password-2026'})[0],200);self.assertEqual(c.request('state')[0],401)
    def test_export_excludes_other_private_data_and_secrets(self):
        c,uid=self.registered();d,other=self.registered('other')
        c.request('like',{'target':other});d.request('like',{'target':uid});mid=c.state()['matches'][0]['id'];c.request('message',{'match_id':mid,'body':'My own message'});d.request('message',{'match_id':mid,'body':'Their message'})
        self.assertEqual(c.request('account/export',{'password':'wrong'})[0],403)
        r=c.request('account/export',{'password':PASSWORD})[1];self.assertEqual(len(r['sent_messages']),1);self.assertEqual(r['sent_messages'][0]['body'],'My own message')
        self.assertNotIn('password_hash',json.dumps(r));self.assertNotIn('csrf',json.dumps(r));self.assertNotIn('Their message',json.dumps(r))
    def test_account_deletion_removes_shared_records_and_auth(self):
        c,uid=self.registered();d,other=self.registered('other');c.request('like',{'target':other});d.request('like',{'target':uid});mid=c.state()['matches'][0]['id'];c.request('message',{'match_id':mid,'body':'Hello'})
        self.assertEqual(c.request('account/delete',{'password':PASSWORD,'confirmation':'no'})[0],403)
        self.assertEqual(c.request('account/delete',{'password':PASSWORD,'confirmation':'DELETE'})[0],200);self.assertEqual(c.request('state')[0],401);self.assertEqual(d.state()['matches'],[])
        with server.connect() as db:
            self.assertIsNone(db.execute('SELECT 1 FROM accounts WHERE user_id=?',(uid,)).fetchone());self.assertIsNone(db.execute('SELECT 1 FROM profiles WHERE id=?',(uid,)).fetchone());self.assertEqual(db.execute('SELECT COUNT(*) FROM messages').fetchone()[0],0)
    def test_moderation_rbac_case_version_and_suspension(self):
        c,uid=self.registered();d,target=self.registered('other');mod,mid=self.registered('moderator',moderator=True)
        c.request('report',{'target':target,'reason':'Repeated unwanted contact'});self.assertEqual(c.request('admin/reports')[0],403)
        q=mod.request('admin/reports')[1];r=q['reports'][0];p={'report_id':r['id'],'version':r['version'],'outcome':'suspend','severity':'high','member_reason':'Repeated unwanted contact violates evaluation rules.'}
        self.assertEqual(mod.request('admin/action',p)[0],200);self.assertEqual(mod.request('admin/action',p)[0],409);self.assertEqual(d.request('state')[0],401)
        response=d.request('login',{'email':'other@example.invalid','password':PASSWORD})[1];d.csrf=response['csrf'];self.assertEqual(d.request('state')[0],403);self.assertEqual(d.request('account')[1]['account']['status'],'suspended')
        self.assertEqual(d.request('appeal',{'report_id':r['id'],'body':'Please review this decision.'})[0],200)
        self.assertEqual(d.request('appeal',{'report_id':r['id'],'body':'Please review this decision.'})[0],409)
        appeal=mod.request('admin/reports')[1]['appeals'][0]
        # Reviewer separation must survive the routine audit-retention window.
        with server.connect() as db:db.execute('DELETE FROM audit')
        self.assertEqual(mod.request('admin/appeal',{'id':appeal['id'],'decision':'overturned','response':'Reviewed context.'})[0],403)
        second,sid=self.registered('second',moderator=True)
        self.assertEqual(second.request('admin/appeal',{'id':appeal['id'],'decision':'overturned','response':'Reviewed context and restored access.'})[0],200);self.assertEqual(d.request('state')[0],200)
        with server.connect() as db:
            self.assertGreaterEqual(db.execute('SELECT COUNT(*) FROM audit').fetchone()[0],3)
            self.assertIsNotNone(db.execute("SELECT 1 FROM audit WHERE action='appeal.overturned'").fetchone())
    def test_independent_safety_restrictions_do_not_cancel_each_other(self):
        reporter,uid=self.registered();target,tid=self.registered('target');mod,mid=self.registered('mod',moderator=True)
        for reason in ('First concern','Second concern'):reporter.request('report',{'target':tid,'reason':reason})
        reports=mod.request('admin/reports')[1]['reports']
        for r in reports:self.assertEqual(mod.request('admin/action',{'report_id':r['id'],'version':1,'outcome':'suspend','severity':'high','member_reason':'Human-reviewed restriction.'})[0],200)
        self.assertEqual(mod.request('admin/action',{'report_id':reports[0]['id'],'version':2,'outcome':'reinstate','severity':'high','member_reason':'Cleared this case only.'})[0],200)
        with server.connect() as db:self.assertEqual(services.account(db,tid)['status'],'suspended')
    def test_notification_privacy_and_preference(self):
        self.a.request('like',{'target':'marcus'});mid=self.a.state()['matches'][0]['id'];self.a.request('message',{'match_id':mid,'body':'A very private message'})
        r=self.b.request('notifications')[1];self.assertGreater(r['unread'],0);self.assertNotIn('A very private message',json.dumps(r));self.b.request('notifications/read',{'through':r['items'][0]['id']});self.assertEqual(self.b.request('notifications')[1]['unread'],0)
        self.a.request('block',{'target':'marcus'});self.assertEqual(self.b.request('notifications')[1]['items'],[])
    def test_mail_retry_and_code_redaction_after_delivery(self):
        c,uid=self.registered();
        class Fail:
            def send(self,*args):raise RuntimeError('Do not log me')
        class Deliver:
            def send(self,*args):pass
        with server.connect() as db:
            r=adapters.deliver_mail(db,Fail());self.assertEqual(r['deferred'],1);row=db.execute('SELECT * FROM mail_outbox').fetchone();self.assertEqual(row['last_error'],'delivery_unavailable');db.execute('UPDATE mail_outbox SET available=0')
            r=adapters.deliver_mail(db,Deliver());self.assertEqual(r['sent'],1);self.assertEqual(db.execute('SELECT body FROM mail_outbox').fetchone()[0],'')
    def test_retention_purges_expired_operational_records(self):
        with server.connect() as db:
            db.execute("INSERT INTO auth_challenges VALUES('expired','alex','reset',0,0)");services.retention(db);self.assertEqual(db.execute('SELECT COUNT(*) FROM auth_challenges WHERE id=\'expired\'').fetchone()[0],0)
    def test_paginated_discovery_and_message_history(self):
        first=self.a.request('discover?limit=2')[1];self.assertEqual(len(first['items']),2);self.assertTrue(first['next_cursor'])
        second=self.a.request('discover?limit=2&cursor='+first['next_cursor'])[1];self.assertTrue(set(x['id'] for x in first['items']).isdisjoint(x['id'] for x in second['items']))
        self.a.request('like',{'target':'marcus'});mid=self.a.state()['matches'][0]['id']
        for n in range(3):self.a.request('message',{'match_id':mid,'body':'Message '+str(n)})
        one=self.a.request('messages?match_id='+mid+'&limit=2')[1];self.assertEqual(len(one['items']),2);self.assertIsNotNone(one['next_before'])
        two=self.a.request('messages?match_id='+mid+'&before='+str(one['next_before']))[1];self.assertEqual(len(two['items']),1)
        self.assertEqual(base.Client().login('daniel').request('messages?match_id='+mid)[0],400)
    def test_native_session_contract_and_secure_cookie(self):
        import urllib.request
        request=urllib.request.Request(base.BASE+'/api/demo',data=json.dumps({'adult':True,'user':'alex'}).encode(),headers={'Content-Type':'application/json','X-Vespra-Client':'native'})
        with urllib.request.urlopen(request) as response:r=json.loads(response.read())
        self.assertIn('access_token',r)
        request=urllib.request.Request(base.BASE+'/api/state',headers={'Authorization':'Bearer '+r['access_token']})
        with urllib.request.urlopen(request) as response:self.assertEqual(json.loads(response.read())['me']['id'],'alex')
        with patch.object(server,'SECURE',True):self.assertIn('; Secure',server.Handler.session_cookie(None,'test-placeholder'))
    def test_membership_and_push_never_fake_success(self):
        self.assertEqual(self.a.request('membership')[1]['status'],'unavailable');self.assertEqual(adapters.DisabledPush().send({},{} )['status'],'not_sent')

if __name__=='__main__':unittest.main(verbosity=2)
