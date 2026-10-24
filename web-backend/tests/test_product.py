import unittest, tempfile, threading, json, urllib.request, urllib.error, http.cookiejar, datetime, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server

class Client:
    def __init__(self):
        self.jar=http.cookiejar.CookieJar();self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar));self.csrf=''
    def request(self,path,data=None,csrf=True):
        headers={'Content-Type':'application/json'}
        if csrf:headers['X-CSRF-Token']=self.csrf
        req=urllib.request.Request(BASE+'/api/'+path,data=json.dumps(data).encode() if data is not None else None,headers=headers)
        try:
            with self.opener.open(req) as r:return r.status,json.loads(r.read())
        except urllib.error.HTTPError as e:return e.code,json.loads(e.read())
    def login(self,uid):
        code,r=self.request('demo',{'user':uid,'adult':True});assert code==200,r;self.csrf=r['csrf'];return self
    def state(self):return self.request('state')[1]

class ProductTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global BASE
        cls.tmp=tempfile.TemporaryDirectory();server.DB=cls.tmp.name+'/test.sqlite3';server.initialize()
        cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler);BASE='http://127.0.0.1:'+str(cls.http.server_port)
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):cls.http.shutdown();cls.http.server_close();cls.tmp.cleanup()
    def setUp(self):
        with server.connect() as db:
            for table in ['reflections','acceptances','dates','messages','matches','likes','reports','blocks','sessions']:db.execute('DELETE FROM '+table)
            db.execute("INSERT INTO likes VALUES('marcus','alex')")
        self.a=Client().login('alex');self.b=Client().login('marcus');self.c=Client().login('daniel')
    def match(self):
        code,r=self.a.request('like',{'target':'marcus'});self.assertEqual(code,200);self.assertTrue(r['matched']);return self.a.state()['matches'][0]['id']
    def date(self):
        mid=self.match();future=(datetime.datetime.now()+datetime.timedelta(days=2)).strftime('%Y-%m-%dT18:30')
        code,r=self.a.request('date',{'match_id':mid,'venue':'A public café','starts':future,'timezone':'America/New_York'});self.assertEqual(code,200,r)
        return self.a.state()['dates'][0]
    def test_adult_gate_and_session(self):
        c=Client();self.assertEqual(c.request('state')[0],401);self.assertEqual(c.request('demo',{'adult':False})[0],400)
        self.assertTrue(self.a.state()['config']['demo'])
    def test_mutual_interest_and_idempotency(self):
        self.assertEqual(self.a.request('like',{'target':'daniel'})[1]['matched'],False)
        self.assertEqual(self.a.state()['matches'],[]);self.match();self.match();self.assertEqual(len(self.a.state()['matches']),1)
    def test_chat_authorization_and_storage(self):
        mid=self.match();self.assertEqual(self.c.request('message',{'match_id':mid,'body':'No'})[0],400)
        self.assertEqual(self.a.request('message',{'match_id':mid,'body':'Hello, Marcus.'})[0],200)
        self.assertEqual(self.b.state()['messages'][0]['body'],'Hello, Marcus.');self.assertEqual(self.c.state()['messages'],[])
    def test_csrf_and_origin(self):
        self.assertEqual(self.a.request('like',{'target':'marcus'},csrf=False)[0],403)
        req=urllib.request.Request(BASE+'/api/demo',data=b'{"adult":true}',headers={'Origin':'https://evil.example'})
        with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(req)
        self.assertEqual(e.exception.code,403)
    def test_agree_before_reservation_and_honest_fallback(self):
        d=self.date();payload={'date_id':d['id'],'revision':1}
        self.assertEqual(self.a.request('reserve',payload)[0],400)
        self.assertEqual(self.b.request('accept',payload)[0],200)
        self.assertEqual(self.a.state()['dates'][0]['status'],'agreed')
        code,r=self.a.request('reserve',payload);self.assertEqual(code,200);self.assertEqual(r['status'],'manual_action_required');self.assertIn('No reservation',r['message'])
    def test_revisions_invalidate_consent(self):
        d=self.date();p={'date_id':d['id'],'revision':1};self.b.request('accept',p)
        self.assertEqual(self.b.request('revise',{**p,'venue':'Another public café','starts':d['starts'][:16]})[0],200)
        self.assertEqual(self.a.request('accept',p)[0],409)
        revised=self.a.state()['dates'][0];self.assertEqual(revised['accepted_by'],['marcus']);self.assertEqual(revised['status'],'proposed')
    def test_block_is_bidirectional_and_revokes_access(self):
        mid=self.match();self.a.request('block',{'target':'marcus'})
        self.assertEqual(self.b.state()['matches'],[]);self.assertFalse(any(p['id']=='alex' for p in self.b.state()['people']))
        self.assertEqual(self.b.request('message',{'match_id':mid,'body':'Hi'})[0],400)
    def test_report_has_no_false_review_claim(self):
        self.assertEqual(self.a.request('report',{'target':'marcus','reason':'Unwanted messages'})[0],200)
        with server.connect() as db:self.assertEqual(db.execute('SELECT status FROM reports').fetchone()[0],'received_not_reviewed')
    def test_reflection_is_private_and_meet_is_time_gated(self):
        d=self.date();p={'date_id':d['id'],'revision':1};self.b.request('accept',p)
        self.assertEqual(self.a.request('complete',p)[0],400)
        with server.connect() as db:db.execute('UPDATE dates SET starts=? WHERE id=?',((datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(hours=2)).isoformat(),d['id']))
        self.assertEqual(self.a.request('complete',p)[0],200)
        self.assertEqual(self.a.request('reflect',{**p,'body':'Felt comfortable.'})[0],200)
        self.assertEqual(self.a.state()['dates'][0]['reflection'],'Felt comfortable.');self.assertIsNone(self.b.state()['dates'][0]['reflection'])
        self.assertEqual(self.c.request('reflect',{**p,'body':'Intrusion'})[0],400)
    def test_cancel_does_not_allow_accept_or_reserve(self):
        d=self.date();p={'date_id':d['id'],'revision':1};self.a.request('cancel',p)
        self.assertEqual(self.b.request('accept',p)[0],400);self.assertEqual(self.a.request('reserve',p)[0],400)
    def test_dst_and_future_validation(self):
        for dt in ['2027-03-14T02:30','2027-11-07T01:30','2000-01-01T12:00']:
            with self.assertRaises(ValueError):server.validate_time(dt,'America/New_York')
    def test_profile_and_logout(self):
        self.a.request('profile',{'bio':'An updated bio','company_private':True});self.assertEqual(self.a.state()['me']['bio'],'An updated bio')
        self.a.request('logout',{});self.assertEqual(self.a.request('state')[0],401)
    def test_security_headers(self):
        with urllib.request.urlopen(BASE) as r:
            self.assertIn("frame-ancestors 'none'",r.headers['Content-Security-Policy']);self.assertEqual(r.headers['X-Content-Type-Options'],'nosniff')

if __name__=='__main__':unittest.main(verbosity=2)
