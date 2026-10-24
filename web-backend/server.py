"""VESPRA local evaluation server. Python 3.11+; no third-party dependencies."""
import os, json, sqlite3, secrets, hashlib, time, datetime, re
import services, adapters
from urllib.parse import urlsplit, parse_qs
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from http.cookies import SimpleCookie
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).parent
DB = os.environ.get('VESPRA_DB', str(ROOT / 'vespra.sqlite3'))
HOST = os.environ.get('VESPRA_HOST', '127.0.0.1')
PORT = int(os.environ.get('VESPRA_PORT', '8765'))
ZONE = os.environ.get('VESPRA_TIMEZONE', 'America/New_York')
CITY = os.environ.get('VESPRA_CITY', 'New York')
MODE = os.environ.get('VESPRA_MODE', 'demo')
DEMO = MODE == 'demo'
PUBLIC_ORIGIN = os.environ.get('VESPRA_PUBLIC_ORIGIN', f'http://127.0.0.1:{PORT}').rstrip('/')
SECURE = PUBLIC_ORIGIN.startswith('https://')
if MODE not in ('demo','private'):
    raise RuntimeError('Only demo and private evaluation modes are supported. Real-member production release requires an independent readiness review.')

class Connection(sqlite3.Connection):
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()

def connect():
    db = sqlite3.connect(DB, timeout=15, factory=Connection)
    db.row_factory = sqlite3.Row
    if DB!=':memory:':os.chmod(DB,0o600)
    db.execute('PRAGMA foreign_keys=ON')
    return db

def initialize():
    with connect() as db:
        db.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS profiles(id TEXT PRIMARY KEY,name TEXT,age INTEGER CHECK(age>=18),role TEXT,area TEXT,bio TEXT,prompt TEXT,answer TEXT,interests TEXT,company_private INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id TEXT REFERENCES profiles(id),csrf TEXT,expires REAL);
        CREATE TABLE IF NOT EXISTS likes(sender TEXT,recipient TEXT,PRIMARY KEY(sender,recipient));
        CREATE TABLE IF NOT EXISTS matches(id TEXT PRIMARY KEY,a TEXT,b TEXT,UNIQUE(a,b));
        CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY,match_id TEXT REFERENCES matches(id),sender TEXT,body TEXT,created TEXT);
        CREATE TABLE IF NOT EXISTS dates(id TEXT PRIMARY KEY,match_id TEXT REFERENCES matches(id),proposer TEXT,venue TEXT,starts TEXT,timezone TEXT,revision INTEGER DEFAULT 1,status TEXT DEFAULT 'proposed',reservation TEXT DEFAULT 'not_requested');
        CREATE TABLE IF NOT EXISTS acceptances(date_id TEXT REFERENCES dates(id),user_id TEXT,revision INTEGER,PRIMARY KEY(date_id,user_id));
        CREATE TABLE IF NOT EXISTS reflections(date_id TEXT REFERENCES dates(id),user_id TEXT,body TEXT,PRIMARY KEY(date_id,user_id));
        CREATE TABLE IF NOT EXISTS blocks(actor TEXT,target TEXT,PRIMARY KEY(actor,target));
        CREATE TABLE IF NOT EXISTS reports(id INTEGER PRIMARY KEY,actor TEXT,target TEXT,reason TEXT,created TEXT,status TEXT DEFAULT 'received_not_reviewed');
        ''')
        services.migrate(db)
        if not DEMO:return
        profiles = [
          ('alex','Alex',32,'Architect','Brooklyn','Making room for good conversation, long dinners, and a little spontaneity.','A very good Sunday','A bookstore detour, a long walk, then cooking for someone.', ['Architecture','Cooking','Long walks']),
          ('marcus','Marcus',34,'Community health lead','Fort Greene','Big on small gestures. Usually planning my next dinner with friends.','We’ll get along if','You’re curious about the world and kind to the waiter.', ['Food','Museums','Cycling']),
          ('daniel','Daniel',29,'Creative producer','Lower East Side','Queer, coffee curious, and always up for a film that makes us talk.','My ideal first date','A low-key table, a shared dessert, nowhere to rush.', ['Film','Coffee','Design']),
          ('rafael','Rafael',38,'Teacher','Astoria','Trans man, amateur gardener, enthusiastic home cook. Looking for something intentional.','A small joy','The first tomato of summer. And a genuinely good question.', ['Gardening','Theatre','Cooking']),
          ('eli','Eli',31,'Independent illustrator','Park Slope','Bi, Brooklyn-based, and learning to leave my sketchbook at home.','Let’s make time for','A gallery afternoon followed by a very opinionated pizza debate.', ['Art','Pizza','Hiking']),
          ('james','James',42,'Public interest lawyer','Harlem','Good company over impressive credentials. Tell me what you’re excited about.','Off the clock','Jazz, neighborhood volunteering, and a spectacularly slow run.', ['Jazz','Running','Volunteering'])]
        for p in profiles:
            db.execute('INSERT OR IGNORE INTO profiles(id,name,age,role,area,bio,prompt,answer,interests) VALUES(?,?,?,?,?,?,?,?,?)', (*p[:8],json.dumps(p[8])))
        # A fictional incoming like, never a fabricated match or automated conversation.
        db.execute("INSERT OR IGNORE INTO likes VALUES('marcus','alex')")

def profile(row):
    p=dict(row);p['interests']=json.loads(p['interests']);return p

def blocked(db,a,b):
    return db.execute('SELECT 1 FROM blocks WHERE (actor=? AND target=?) OR (actor=? AND target=?)',(a,b,b,a)).fetchone()

def match_access(db,mid,uid):
    m=db.execute('SELECT * FROM matches WHERE id=? AND (a=? OR b=?)',(mid,uid,uid)).fetchone()
    if not m or blocked(db,m['a'],m['b']): raise ValueError('Connection unavailable.')
    for member in (m['a'],m['b']):
        account=services.account(db,member)
        if account and account['status']!='active':raise ValueError('Connection unavailable.')
    return m

def validate_time(value,zone):
    dt=datetime.datetime.fromisoformat(value)
    if dt.tzinfo is not None: raise ValueError('Use local date and time with a separate timezone.')
    z=ZoneInfo(zone)
    aware=dt.replace(tzinfo=z)
    if aware.astimezone(datetime.timezone.utc).astimezone(z).replace(tzinfo=None)!=dt:
        raise ValueError('That local time does not exist. Choose another time.')
    if dt.replace(tzinfo=z,fold=0).utcoffset()!=dt.replace(tzinfo=z,fold=1).utcoffset():
        raise ValueError('That time is ambiguous during a clock change. Choose another time.')
    if aware <= datetime.datetime.now(z): raise ValueError('Choose a future time.')
    return aware.isoformat()

class ReservationAdapter:
    """No partner credentials configured: never claim a confirmed reservation."""
    def reserve(self, plan):
        result=adapters.ManualBooking().reserve(plan,plan['id']+':'+str(plan['revision']))
        return {'status':result.status,'message':result.message}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt,*args): pass # No sensitive profile/chat logs.
    def send(self,code,data,cookie=None):
        # Never acknowledge a mutation before its transaction commits.
        tx=getattr(self,'transaction',None)
        if tx is not None:tx.commit()
        body=json.dumps(data).encode();self.send_response(code)
        self.headers_common();self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)))
        if cookie:self.send_header('Set-Cookie',cookie)
        self.end_headers();self.wfile.write(body)
    def headers_common(self):
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer')
        if SECURE:self.send_header('Strict-Transport-Security','max-age=31536000')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
    def parse_request(self):
        if not super().parse_request():return False
        authority=self.headers.get('Host','')
        hostname=urlsplit('http://'+authority).hostname
        allowed=authority==urlsplit(PUBLIC_ORIGIN).netloc or (not SECURE and hostname in ('127.0.0.1','localhost','::1'))
        if not allowed:
            self.send(400,{'error':'Host not allowed.'});return False
        self.connection.settimeout(20)
        return True
    def do_GET(self):
        if self.path=='/healthz':
            try:
                with connect() as db:db.execute('SELECT MAX(version) FROM schema_versions').fetchone()
                return self.send(200,{'status':'ok','version':'2.0','mode':MODE})
            except sqlite3.Error:return self.send(503,{'status':'unavailable'})
        if self.path.startswith('/api/'):
            return self.api('GET')
        path=self.path.split('?')[0]
        file=ROOT/'public'/('index.html' if path=='/' else path.lstrip('/'))
        if not file.resolve().is_relative_to((ROOT/'public').resolve()) or not file.is_file(): return self.send(404,{'error':'Not found'})
        types={'.html':'text/html','.css':'text/css','.js':'text/javascript','.svg':'image/svg+xml','.png':'image/png','.webmanifest':'application/manifest+json'}
        body=file.read_bytes();self.send_response(200);self.headers_common();self.send_header('Content-Type',types.get(file.suffix,'application/octet-stream'));self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def do_POST(self):self.api('POST')
    def api(self,method):
        try:
            with connect() as db:
                self.transaction=db
                path=self.path.split('?')[0]
                if path=='/api/config' and method=='GET':return self.send(200,{'demo':DEMO,'mode':MODE,'city':CITY,'timezone':ZONE,'policy':services.POLICY,'mail_configured':bool(os.environ.get('VESPRA_MAIL_CONFIG_FILE'))})
                data={}
                if method=='POST':
                    origin=self.headers.get('Origin')
                    allowed={PUBLIC_ORIGIN}
                    if not SECURE:allowed.add(f'http://{self.headers.get("Host")}')
                    if origin and origin not in allowed:return self.send(403,{'error':'Origin rejected'})
                    if self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.send(415,{'error':'Send application/json.'})
                    n=int(self.headers.get('Content-Length','0'))
                    if n<0:return self.send(400,{'error':'Invalid request size'})
                    if n>16384:return self.send(413,{'error':'Request too large'})
                    data=json.loads(self.rfile.read(n) or b'{}')
                    if not isinstance(data,dict): raise ValueError('Invalid request.')
                    # Serialize plan checks and writes so revisions cannot race.
                    db.execute('BEGIN IMMEDIATE')
                if method=='POST':
                    try:result=services.public_auth(db,path,data,self.client_address[0])
                    except services.APIError as error:return self.send(error.status,{'error':error.message})
                    if result is not None:
                        response,pair=result
                        if pair:
                            if self.headers.get('X-Vespra-Client')=='native':response['access_token']=pair[0]
                            return self.send(200,response,self.session_cookie(pair[0]))
                        return self.send(200,response)
                if path=='/api/demo' and method=='POST':
                    if not DEMO:return self.send(404,{'error':'Demo access disabled.'})
                    if data.get('adult') is not True:raise ValueError('This experience is for adults 18 and older.')
                    uid=data.get('user','alex')
                    if uid not in services.DEMO_IDS or not db.execute('SELECT 1 FROM profiles WHERE id=?',(uid,)).fetchone():raise ValueError('Unknown demo member.')
                    token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(24)
                    db.execute('INSERT INTO sessions VALUES(?,?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),uid,csrf,time.time()+86400))
                    response={'csrf':csrf}
                    if self.headers.get('X-Vespra-Client')=='native':response['access_token']=token
                    return self.send(200,response,self.session_cookie(token))
                cookies=SimpleCookie();cookies.load(self.headers.get('Cookie',''));token=cookies.get('__Host-vespra' if SECURE else 'vespra')
                raw_token=token.value if token else ''
                if self.headers.get('Authorization','').startswith('Bearer '):raw_token=self.headers['Authorization'][7:]
                session=db.execute('SELECT * FROM sessions WHERE token=? AND expires>?',(hashlib.sha256(raw_token.encode()).hexdigest(),time.time())).fetchone()
                if not session:return self.send(401,{'error':'Sign in to continue.'})
                uid=session['user_id']
                if not DEMO and not services.account(db,uid):
                    db.execute('DELETE FROM sessions WHERE user_id=?',(uid,));return self.send(401,{'error':'Demo sessions are disabled in private mode.'})
                if method=='POST' and self.headers.get('X-CSRF-Token')!=session['csrf']:return self.send(403,{'error':'Invalid request token. Refresh and try again.'})
                try:
                    services.ensure_actor(db,uid,path)
                    if method=='POST':services.rate(db,'writes:'+uid,90,60)
                    extra=services.route(db,method,path,uid,data,session)
                except services.APIError as error:return self.send(error.status,{'error':error.message})
                if extra is not None:return self.send(200,extra)
                if path in ('/api/verification','/api/membership'):
                    result=adapters.DisabledIdentity().begin(uid) if path=='/api/verification' else adapters.DisabledBilling().checkout(uid)
                    return self.send(200,result)
                if path=='/api/messages' and method=='GET':
                    q=parse_qs(urlsplit(self.path).query);mid=q.get('match_id',[''])[0];match_access(db,mid,uid)
                    before=int(q.get('before',[str(2**62)])[0]);limit=max(1,min(100,int(q.get('limit',['50'])[0])))
                    rows=[dict(r) for r in db.execute('SELECT * FROM messages WHERE match_id=? AND id<? ORDER BY id DESC LIMIT ?',(mid,before,limit+1))]
                    return self.send(200,{'items':list(reversed(rows[:limit])),'next_before':rows[limit-1]['id'] if len(rows)>limit else None})
                if path=='/api/discover' and method=='GET':
                    q=parse_qs(urlsplit(self.path).query);cursor=q.get('cursor',[''])[0];area=q.get('area',[''])[0];interest=q.get('interest',[''])[0]
                    minimum=max(18,int(q.get('min_age',['18'])[0]));maximum=min(110,int(q.get('max_age',['110'])[0]));limit=max(1,min(100,int(q.get('limit',['50'])[0])))
                    registered=bool(services.account(db,uid))
                    rows=db.execute('''SELECT p.* FROM profiles p LEFT JOIN accounts a ON p.id=a.user_id WHERE p.id>? AND p.id!=? AND p.age BETWEEN ? AND ? AND (?='' OR p.area=?) AND (?='' OR EXISTS(SELECT 1 FROM json_each(p.interests) WHERE value=?)) AND ((?=1 AND a.status='active' AND a.visible=1 AND a.email_verified=1) OR (?=0 AND a.user_id IS NULL)) AND NOT EXISTS(SELECT 1 FROM blocks b WHERE (b.actor=? AND b.target=p.id) OR (b.actor=p.id AND b.target=?)) ORDER BY p.id LIMIT ?''',(cursor,uid,minimum,maximum,area,area,interest,interest,int(registered),int(registered),uid,uid,limit+1)).fetchall()
                    return self.send(200,{'items':[profile(r) for r in rows[:limit]],'next_cursor':rows[limit-1]['id'] if len(rows)>limit else None})
                if path=='/api/state' and method=='GET':
                    registered=bool(services.account(db,uid))
                    rows=db.execute('''SELECT p.* FROM profiles p LEFT JOIN accounts a ON p.id=a.user_id WHERE p.id!=? AND ((?=1 AND a.status='active' AND a.visible=1 AND a.email_verified=1) OR (?=0 AND a.user_id IS NULL)) ORDER BY p.name LIMIT 200''',(uid,int(registered),int(registered)))
                    people=[profile(p) for p in rows if not blocked(db,uid,p['id'])]
                    for m in db.execute('SELECT * FROM matches WHERE a=? OR b=?',(uid,uid)):
                        other=m['b'] if m['a']==uid else m['a']
                        p=db.execute('SELECT * FROM profiles WHERE id=?',(other,)).fetchone();a=services.account(db,other)
                        if p and not blocked(db,uid,other) and (not a or a['status']=='active') and not any(x['id']==other for x in people):people.append({**profile(p),'connection_only':True})
                    matches=[]
                    for m in db.execute('SELECT * FROM matches WHERE a=? OR b=?',(uid,uid)):
                        try:match_access(db,m['id'],uid)
                        except ValueError:continue
                        matches.append(dict(m))
                    mids=[m['id'] for m in matches]
                    dates=[dict(d) for d in db.execute('SELECT * FROM dates') if d['match_id'] in mids]
                    for d in dates:
                        d['accepted_by']=[r[0] for r in db.execute('SELECT user_id FROM acceptances WHERE date_id=? AND revision=?',(d['id'],d['revision']))]
                        r=db.execute('SELECT body FROM reflections WHERE date_id=? AND user_id=?',(d['id'],uid)).fetchone();d['reflection']=r[0] if r else None
                    return self.send(200,{'me':profile(db.execute('SELECT * FROM profiles WHERE id=?',(uid,)).fetchone()),'people':people,'likes':[dict(l) for l in db.execute('SELECT * FROM likes WHERE sender=? OR recipient=?',(uid,uid)) if not blocked(db,l['sender'],l['recipient']) and any(p['id']==(l['recipient'] if l['sender']==uid else l['sender']) for p in people)],'matches':matches,'messages':list(reversed([dict(m) for m in db.execute('SELECT * FROM messages WHERE match_id IN (SELECT id FROM matches WHERE a=? OR b=?) ORDER BY id DESC LIMIT 200',(uid,uid)) if m['match_id'] in mids])),'dates':dates,'csrf':session['csrf'],'config':{'city':CITY,'timezone':ZONE,'demo':not bool(services.account(db,uid)),'policy':services.POLICY,'mode':MODE,'reservationProvider':'manual','verification':'unavailable'}})
                if method!='POST':return self.send(404,{'error':'Not found'})
                if path=='/api/like':
                    other=data.get('target')
                    if other==uid or not db.execute('SELECT 1 FROM profiles WHERE id=?',(other,)).fetchone() or blocked(db,uid,other) or not services.allowed_profile(db,uid,other):raise ValueError('Profile unavailable.')
                    db.execute('INSERT OR IGNORE INTO likes VALUES(?,?)',(uid,other))
                    mutual=db.execute('SELECT 1 FROM likes WHERE sender=? AND recipient=?',(other,uid)).fetchone()
                    if mutual:
                        a,b=sorted([uid,other]);db.execute('INSERT OR IGNORE INTO matches VALUES(?,?,?)',(a+'_'+b,a,b))
                    services.on_mutation(db,uid,path,data)
                    return self.send(200,{'matched':bool(mutual)})
                if path=='/api/message':
                    match_access(db,data.get('match_id'),uid);body=str(data.get('body','')).strip()
                    if not 1<=len(body)<=2000:raise ValueError('Write a message of 1–2,000 characters.')
                    services.rate(db,'messages:'+uid,30,60)
                    db.execute('INSERT INTO messages(match_id,sender,body,created) VALUES(?,?,?,?)',(data['match_id'],uid,body,datetime.datetime.now(datetime.timezone.utc).isoformat()))
                elif path=='/api/date':
                    match_access(db,data.get('match_id'),uid)
                    venue=str(data.get('venue','')).strip()
                    if not 2<=len(venue)<=160:raise ValueError('Add a public meeting place (2–160 characters).')
                    zone=data.get('timezone',ZONE);starts=validate_time(data.get('starts',''),zone)
                    did=secrets.token_hex(12);data['date_id']=did
                    db.execute('INSERT INTO dates(id,match_id,proposer,venue,starts,timezone) VALUES(?,?,?,?,?,?)',(did,data['match_id'],uid,venue,starts,zone))
                    db.execute('INSERT INTO acceptances VALUES(?,?,1)',(did,uid))
                elif path in ['/api/accept','/api/reserve','/api/cancel','/api/reflect','/api/complete','/api/revise']:
                    d=db.execute('SELECT * FROM dates WHERE id=?',(data.get('date_id'),)).fetchone()
                    if not d:raise ValueError('Plan unavailable.')
                    match_access(db,d['match_id'],uid)
                    if data.get('revision')!=d['revision']:return self.send(409,{'error':'The plan changed. Review the latest details.'})
                    if d['status']=='cancelled':raise ValueError('This plan was cancelled.')
                    if path=='/api/accept':
                        if d['status'] not in ('proposed','agreed'):raise ValueError('This plan can no longer be accepted.')
                        db.execute('INSERT OR REPLACE INTO acceptances VALUES(?,?,?)',(d['id'],uid,d['revision']))
                        if db.execute('SELECT COUNT(*) FROM acceptances WHERE date_id=? AND revision=?',(d['id'],d['revision'])).fetchone()[0]==2:db.execute("UPDATE dates SET status='agreed' WHERE id=?",(d['id'],))
                    elif path=='/api/reserve':
                        if d['status']!='agreed':raise ValueError('Both people must agree before arranging a table.')
                        existing=db.execute('SELECT * FROM reservation_requests WHERE date_id=? AND revision=?',(d['id'],d['revision'])).fetchone()
                        result=ReservationAdapter().reserve(dict(d))
                        if not existing:db.execute('INSERT INTO reservation_requests(id,date_id,revision,requester,status,created) VALUES(?,?,?,?,?,?)',(secrets.token_hex(16),d['id'],d['revision'],uid,result['status'],services.now()))
                        db.execute('UPDATE dates SET reservation=? WHERE id=?',(result['status'],d['id']));return self.send(200,result)
                    elif path=='/api/revise':
                        if d['status'] not in ('proposed','agreed'):raise ValueError('This plan cannot be changed.')
                        venue=str(data.get('venue','')).strip()
                        if not 2<=len(venue)<=160:raise ValueError('Add a public meeting place.')
                        starts=validate_time(data.get('starts',''),d['timezone'])
                        db.execute("UPDATE dates SET venue=?,starts=?,revision=revision+1,status='proposed',reservation='not_requested' WHERE id=?",(venue,starts,d['id']))
                        db.execute('DELETE FROM acceptances WHERE date_id=?',(d['id'],));db.execute('INSERT INTO acceptances VALUES(?,?,?)',(d['id'],uid,d['revision']+1))
                    elif path=='/api/cancel':db.execute("UPDATE dates SET status='cancelled',reservation='not_requested' WHERE id=?",(d['id'],))
                    elif path=='/api/complete':
                        if d['status']!='agreed' or datetime.datetime.fromisoformat(d['starts'])>datetime.datetime.now(datetime.timezone.utc):raise ValueError('You can mark a date met after its agreed start time.')
                        db.execute("UPDATE dates SET status='met' WHERE id=?",(d['id'],))
                    else:
                        if d['status']!='met':raise ValueError('Reflect after meeting.')
                        body=str(data.get('body','')).strip()
                        if not 1<=len(body)<=2000:raise ValueError('Add a private reflection (up to 2,000 characters).')
                        db.execute('INSERT OR REPLACE INTO reflections VALUES(?,?,?)',(d['id'],uid,body))
                elif path in ['/api/block','/api/report']:
                    target=data.get('target')
                    if target==uid or not db.execute('SELECT 1 FROM profiles WHERE id=?',(target,)).fetchone():raise ValueError('Invalid profile.')
                    if path=='/api/block':db.execute('INSERT OR IGNORE INTO blocks VALUES(?,?)',(uid,target))
                    else:
                        reason=str(data.get('reason','')).strip()
                        if not 3<=len(reason)<=1000:raise ValueError('Describe the concern (3–1,000 characters).')
                        db.execute('INSERT INTO reports(actor,target,reason,created) VALUES(?,?,?,?)',(uid,target,reason,datetime.datetime.now(datetime.timezone.utc).isoformat()))
                elif path=='/api/profile':
                    bio=str(data.get('bio','')).strip()
                    if len(bio)>500:raise ValueError('Keep your bio under 500 characters.')
                    old=db.execute('SELECT * FROM profiles WHERE id=?',(uid,)).fetchone()
                    values={key:services.text(data.get(key,old[key]),1,maximum) for key,maximum in [('name',60),('role',80),('area',80),('prompt',100),('answer',500)]}
                    interests=data.get('interests',json.loads(old['interests']))
                    if not isinstance(interests,list) or len(interests)>8:raise ValueError('Choose up to eight interests.')
                    interests=[services.text(x,1,30) for x in interests]
                    db.execute('UPDATE profiles SET name=?,role=?,area=?,prompt=?,answer=?,interests=?,bio=?,company_private=? WHERE id=?',(*(values[k] for k in ('name','role','area','prompt','answer')),json.dumps(interests),bio,int(bool(data.get('company_private',True))),uid))
                elif path=='/api/logout':
                    db.execute('DELETE FROM sessions WHERE token=?',(session['token'],));return self.send(200,{'ok':True},self.session_cookie('').replace('Max-Age=86400','Max-Age=0'))
                else:return self.send(404,{'error':'Not found'})
                services.on_mutation(db,uid,path,data)
                self.send(200,{'ok':True})
        except services.APIError as error:
            self.transaction=None
            self.send(error.status,{'error':error.message})
        except ValueError as error:
            self.transaction=None
            self.send(400,{'error':str(error) if not isinstance(error,json.JSONDecodeError) else 'Invalid JSON request.'})
        except (KeyError,TypeError,OverflowError):
            self.transaction=None
            self.send(400,{'error':'Invalid request. Check your details and use a valid future time.'})
        except sqlite3.Error:
            self.transaction=None
            self.send(503,{'error':'Storage unavailable. Please try again.'})
        finally:self.transaction=None
    def session_cookie(self,token):
        return f'{"__Host-vespra" if SECURE else "vespra"}={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=86400'+('; Secure' if SECURE else '')

if __name__=='__main__':
    os.umask(0o077)
    initialize();print(f'VESPRA {MODE} evaluation: http://{HOST}:{PORT}',flush=True)
    ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
