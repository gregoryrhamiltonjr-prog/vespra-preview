"""V2 account, privacy, moderation, inbox and provider boundaries.
All routes run inside the caller's SQLite transaction. Never log request bodies.
"""
import base64, datetime as dt, hashlib, hmac, json, os, re, secrets, sqlite3, time
from pathlib import Path

POLICY='2026-10-23.v1'
DEMO_IDS=('alex','marcus','daniel','rafael','eli','james')

class APIError(Exception):
    def __init__(self,status,message):self.status=status;self.message=message

def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def digest(s):return hashlib.sha256(s.encode()).hexdigest()
def text(value,minimum=1,maximum=500):
    if not isinstance(value,str) or not minimum<=len(value.strip())<=maximum:raise APIError(400,f'Use {minimum}–{maximum} characters.')
    return value.strip()
def email(value):
    value=text(value,3,254).lower()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',value):raise APIError(400,'Enter a valid email address.')
    return value

def migrate(db):
    db.executescript('''
    CREATE TABLE IF NOT EXISTS schema_versions(version INTEGER PRIMARY KEY,applied TEXT);
    CREATE TABLE IF NOT EXISTS accounts(user_id TEXT PRIMARY KEY REFERENCES profiles(id),email TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,email_verified INTEGER DEFAULT 0,status TEXT DEFAULT 'active',role TEXT DEFAULT 'member',visible INTEGER DEFAULT 0,notify INTEGER DEFAULT 1,created TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS consents(id INTEGER PRIMARY KEY,user_id TEXT,policy TEXT,adult INTEGER,created TEXT);
    CREATE TABLE IF NOT EXISTS auth_challenges(id TEXT PRIMARY KEY,user_id TEXT,kind TEXT,expires REAL,used INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS limits(bucket TEXT PRIMARY KEY,count INTEGER,expires REAL);
    CREATE TABLE IF NOT EXISTS inbox(id INTEGER PRIMARY KEY,user_id TEXT,kind TEXT,entity TEXT,title TEXT,created TEXT,seen INTEGER DEFAULT 0,dedupe TEXT UNIQUE);
    CREATE TABLE IF NOT EXISTS mail_outbox(id INTEGER PRIMARY KEY,recipient TEXT,subject TEXT,body TEXT,status TEXT DEFAULT 'queued',attempts INTEGER DEFAULT 0,available REAL,created TEXT,last_error TEXT);
    CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,actor TEXT,action TEXT,entity TEXT,created TEXT);
    CREATE TABLE IF NOT EXISTS report_reviews(report_id INTEGER PRIMARY KEY REFERENCES reports(id),severity TEXT DEFAULT 'medium',version INTEGER DEFAULT 1,outcome TEXT,member_reason TEXT,updated TEXT);
    CREATE TABLE IF NOT EXISTS appeals(id INTEGER PRIMARY KEY,user_id TEXT,report_id INTEGER,body TEXT,status TEXT DEFAULT 'pending',response TEXT,created TEXT);
    CREATE TABLE IF NOT EXISTS reservation_requests(id TEXT PRIMARY KEY,date_id TEXT,revision INTEGER,requester TEXT,status TEXT,provider_reference TEXT,created TEXT,UNIQUE(date_id,revision));
    CREATE INDEX IF NOT EXISTS idx_messages_match ON messages(match_id,id);
    CREATE INDEX IF NOT EXISTS idx_dates_match ON dates(match_id);
    CREATE INDEX IF NOT EXISTS idx_inbox_user ON inbox(user_id,id);
    CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status,id);
    CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
    CREATE INDEX IF NOT EXISTS idx_challenges_expiry ON auth_challenges(expires);
    CREATE TRIGGER IF NOT EXISTS sessions_cap AFTER INSERT ON sessions BEGIN
      DELETE FROM sessions WHERE token IN (SELECT token FROM sessions WHERE user_id=NEW.user_id ORDER BY expires DESC LIMIT -1 OFFSET 10);
    END;
    ''')
    columns={r[1] for r in db.execute('PRAGMA table_info(report_reviews)')}
    for column in ('suspended_by','suspension_reason'):
        if column not in columns:db.execute(f'ALTER TABLE report_reviews ADD COLUMN {column} TEXT')
    if 'restriction_active' not in columns:db.execute('ALTER TABLE report_reviews ADD COLUMN restriction_active INTEGER DEFAULT 0')
    db.execute('INSERT OR IGNORE INTO schema_versions VALUES(2,?)',(now(),))

def audit(db,actor,action,entity=''):
    db.execute('INSERT INTO audit(actor,action,entity,created) VALUES(?,?,?,?)',(actor,action,str(entity),now()))

def rate(db,bucket,maximum=60,seconds=60):
    t=time.time();row=db.execute('SELECT * FROM limits WHERE bucket=?',(digest(bucket),)).fetchone()
    if row and row['expires']>t:
        if row['count']>=maximum:raise APIError(429,'Too many attempts. Please wait and try again.')
        db.execute('UPDATE limits SET count=count+1 WHERE bucket=?',(digest(bucket),))
    else:db.execute('INSERT OR REPLACE INTO limits VALUES(?,1,?)',(digest(bucket),t+seconds))

def password_hash(password):
    if not isinstance(password,str) or not 12<=len(password)<=128:raise APIError(400,'Choose a password of 12–128 characters.')
    salt=secrets.token_bytes(16)
    key=hashlib.scrypt(password.encode(),salt=salt,n=16384,r=8,p=1,dklen=32)
    return 'scrypt$'+salt.hex()+'$'+key.hex()

def password_matches(password,stored):
    try:
        _,salt,key=stored.split('$')
        if not isinstance(password,str) or len(password)>128:return False
        actual=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1,dklen=32)
        return hmac.compare_digest(actual,bytes.fromhex(key))
    except (ValueError,TypeError):return False

def account(db,uid):return db.execute('SELECT * FROM accounts WHERE user_id=?',(uid,)).fetchone()

def issue_session(db,uid):
    token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(24)
    db.execute('INSERT INTO sessions VALUES(?,?,?,?)',(digest(token),uid,csrf,time.time()+86400))
    return token,csrf

def challenge(db,uid,kind):
    code=secrets.token_urlsafe(24)
    db.execute('DELETE FROM auth_challenges WHERE user_id=? AND kind=?',(uid,kind))
    db.execute('INSERT INTO auth_challenges VALUES(?,?,?,?,0)',(digest(code),uid,kind,time.time()+1800))
    a=account(db,uid)
    subject='Your account verification' if kind=='verify' else 'Your account recovery'
    body=f'Your {kind} code is:\n{code}\n\nIt expires in 30 minutes and can be used once. If you did not request this, ignore it.'
    db.execute('INSERT INTO mail_outbox(recipient,subject,body,available,created) VALUES(?,?,?,?,?)',(a['email'],subject,body,time.time(),now()))
    return code # Internal test seam; routes never return this value.

def consume(db,code,kind):
    row=db.execute('SELECT * FROM auth_challenges WHERE id=? AND kind=? AND expires>? AND used=0',(digest(text(code,10,128)),kind,time.time())).fetchone()
    if not row:raise APIError(400,'That code is invalid or expired. Request a new one.')
    db.execute('UPDATE auth_challenges SET used=1 WHERE id=?',(row['id'],))
    return row['user_id']

def public_auth(db,path,data,ip):
    """Returns response plus optional session pair. None for a non-auth route."""
    if path not in ('/api/register','/api/login','/api/recovery/request','/api/recovery/complete','/api/email/verify'):return None
    rate(db,'auth-ip:'+ip,30,900)
    if path=='/api/register':
        if data.get('adult') is not True or data.get('policy')!=POLICY:raise APIError(400,'Confirm you are 18+ and accept the current terms and privacy notice.')
        birth=dt.date.fromisoformat(data.get('birth_date',''))
        today=dt.datetime.now(dt.timezone.utc).date();age=today.year-birth.year-((today.month,today.day)<(birth.month,birth.day))
        if age<18 or age>110:raise APIError(400,'This service is for adults 18 and older.')
        address=email(data.get('email'));pw=password_hash(data.get('password'));name=text(data.get('name'),1,60)
        if db.execute('SELECT 1 FROM accounts WHERE email=?',(address,)).fetchone():
            # Same response as new registration. Never reveal whether an email exists.
            return {'ok':True,'message':'If eligible, your account is ready. Check your email for verification, then sign in.'},None
        uid=secrets.token_hex(16)
        db.execute('INSERT INTO profiles(id,name,age,role,area,bio,prompt,answer,interests) VALUES(?,?,?,?,?,?,?,?,?)',(uid,name,age,'Curious about life',os.environ.get('VESPRA_CITY','New York'),'','A small joy','A conversation with possibility.','[]'))
        db.execute('INSERT INTO accounts(user_id,email,password_hash,created) VALUES(?,?,?,?)',(uid,address,pw,now()))
        db.execute('INSERT INTO consents(user_id,policy,adult,created) VALUES(?,?,1,?)',(uid,POLICY,now()))
        challenge(db,uid,'verify');audit(db,uid,'account.registered')
        return {'ok':True,'message':'If eligible, your account is ready. Check your email for verification, then sign in.'},None
    if path=='/api/login':
        address=email(data.get('email'));rate(db,'login:'+address,8,900)
        a=db.execute('SELECT * FROM accounts WHERE email=?',(address,)).fetchone()
        # Perform equivalent password work for unknown addresses.
        stored=a['password_hash'] if a else 'scrypt$'+'00'*16+'$'+'00'*32
        valid=password_matches(data.get('password'),stored)
        if not a or not valid:raise APIError(401,'Email or password was not recognized.')
        token,csrf=issue_session(db,a['user_id']);audit(db,a['user_id'],'account.login')
        return {'ok':True,'csrf':csrf,'account_status':a['status']},(token,csrf)
    if path=='/api/recovery/request':
        address=email(data.get('email'));rate(db,'recovery:'+address,3,1800)
        a=db.execute('SELECT * FROM accounts WHERE email=?',(address,)).fetchone()
        if a:challenge(db,a['user_id'],'reset')
        return {'ok':True,'message':'If the account exists, recovery instructions will be delivered. Delivery requires a configured email transport.'},None
    if path=='/api/recovery/complete':
        # Validate first: invalid replacement must not burn a usable challenge.
        hashed=password_hash(data.get('password'));uid=consume(db,data.get('code'),'reset')
        db.execute('UPDATE accounts SET password_hash=? WHERE user_id=?',(hashed,uid));db.execute('DELETE FROM sessions WHERE user_id=?',(uid,));audit(db,uid,'account.password_reset')
        return {'ok':True,'message':'Password updated. Sign in again on your devices.'},None
    uid=consume(db,data.get('code'),'verify');db.execute('UPDATE accounts SET email_verified=1 WHERE user_id=?',(uid,));audit(db,uid,'account.email_verified')
    return {'ok':True,'message':'Email verified. This does not verify identity or age.'},None

def allowed_profile(db,viewer,target):
    va=account(db,viewer);ta=account(db,target)
    if bool(va)!=bool(ta):return False # Fictional and registered pools never mix.
    return not ta or (ta['status']=='active' and bool(ta['visible']) and bool(ta['email_verified']))

def ensure_actor(db,uid,path):
    a=account(db,uid)
    if not a:return
    safe={'/api/account','/api/appeals','/api/appeal','/api/account/export','/api/account/delete','/api/logout','/api/email/resend','/api/sessions','/api/sessions/revoke','/api/password','/api/email/verify'}
    if a['status']!='active' and path not in safe:raise APIError(403,'Your account is restricted. Open account settings to view the decision or appeal.')


def notify(db,uid,kind,entity,dedupe=None):
    a=account(db,uid)
    if a and (not a['notify'] or a['status']!='active'):return
    db.execute('INSERT OR IGNORE INTO inbox(user_id,kind,entity,title,created,dedupe) VALUES(?,?,?,?,?,?)',(uid,kind,entity,'You have an update',now(),dedupe))

def on_mutation(db,uid,path,data):
    """Transactional, generic in-app updates. No dating/chat content in notifications."""
    if path=='/api/like':
        other=data['target'];notify(db,other,'interest',uid,'like:'+uid+':'+other)
        a,b=sorted([uid,other]);m=db.execute('SELECT id FROM matches WHERE a=? AND b=?',(a,b)).fetchone()
        if m:
            for who in (uid,other):notify(db,who,'match',m[0],'match:'+m[0]+':'+who)
    elif path=='/api/message':
        m=db.execute('SELECT * FROM matches WHERE id=?',(data['match_id'],)).fetchone();other=m['b'] if m['a']==uid else m['a']
        notify(db,other,'message',m['id'])
    elif path in ('/api/date','/api/accept','/api/revise','/api/cancel','/api/complete'):
        d=db.execute('SELECT * FROM dates WHERE id=?',(data.get('date_id'),)).fetchone()
        if d:
            m=db.execute('SELECT * FROM matches WHERE id=?',(d['match_id'],)).fetchone()
            notify(db,m['b'] if m['a']==uid else m['a'],'plan',d['id'])
    elif path=='/api/report':audit(db,uid,'report.created',data.get('target'))
    elif path=='/api/block':
        # Drop stale potentially revealing inbox entries for both sides of the connection.
        other=data['target'];a,b=sorted([uid,other]);mid=a+'_'+b
        dids=[x[0] for x in db.execute('SELECT id FROM dates WHERE match_id=?',(mid,))]
        for entity in [uid,other,mid,*dids]:db.execute('DELETE FROM inbox WHERE user_id IN (?,?) AND entity=?',(uid,other,entity))
        audit(db,uid,'member.blocked',other)


def export_account(db,uid):
    rows=lambda q,args=():[dict(r) for r in db.execute(q,args)]
    return {'exported_at':now(),'profile':dict(db.execute('SELECT * FROM profiles WHERE id=?',(uid,)).fetchone()),'account':rows('SELECT user_id,email,email_verified,status,visible,notify,created FROM accounts WHERE user_id=?',(uid,)),
      'consents':rows('SELECT policy,adult,created FROM consents WHERE user_id=?',(uid,)),
      'sent_interests':rows('SELECT recipient FROM likes WHERE sender=?',(uid,)),
      'sent_messages':rows('SELECT match_id,body,created FROM messages WHERE sender=?',(uid,)),
      'plans':rows('SELECT d.* FROM dates d JOIN matches m ON d.match_id=m.id WHERE m.a=? OR m.b=?',(uid,uid)),
      'private_reflections':rows('SELECT date_id,body FROM reflections WHERE user_id=?',(uid,)),
      'submitted_reports':rows('SELECT target,reason,created,status FROM reports WHERE actor=?',(uid,)),
      'appeals':rows('SELECT report_id,body,status,response,created FROM appeals WHERE user_id=?',(uid,))}

def delete_account(db,uid):
    """Immediate logical deletion of personal records, not forensic disk erasure."""
    mids=[r[0] for r in db.execute('SELECT id FROM matches WHERE a=? OR b=?',(uid,uid))]
    for mid in mids:
        for d in db.execute('SELECT id FROM dates WHERE match_id=?',(mid,)).fetchall():
            for table in ('reflections','acceptances','reservation_requests'):db.execute(f'DELETE FROM {table} WHERE date_id=?',(d[0],))
            db.execute('DELETE FROM inbox WHERE entity=?',(d[0],))
        db.execute('DELETE FROM dates WHERE match_id=?',(mid,));db.execute('DELETE FROM messages WHERE match_id=?',(mid,));db.execute('DELETE FROM inbox WHERE entity=?',(mid,))
    db.execute('DELETE FROM matches WHERE a=? OR b=?',(uid,uid));db.execute('DELETE FROM likes WHERE sender=? OR recipient=?',(uid,uid));db.execute('DELETE FROM blocks WHERE actor=? OR target=?',(uid,uid))
    a=account(db,uid)
    if a:db.execute('DELETE FROM mail_outbox WHERE recipient=?',(a['email'],))
    for table in ('sessions','auth_challenges','consents','appeals'):db.execute(f'DELETE FROM {table} WHERE user_id=?',(uid,))
    db.execute('DELETE FROM inbox WHERE user_id=? OR entity=?',(uid,uid))
    # No staffed service / legal-hold feature exists: delete report text involving the account.
    rids=[r[0] for r in db.execute('SELECT id FROM reports WHERE actor=? OR target=?',(uid,uid))]
    for rid in rids:db.execute('DELETE FROM report_reviews WHERE report_id=?',(rid,));db.execute('DELETE FROM appeals WHERE report_id=?',(rid,))
    db.execute('DELETE FROM reports WHERE actor=? OR target=?',(uid,uid));db.execute('DELETE FROM audit WHERE actor=? OR entity=?',(uid,uid));db.execute('DELETE FROM accounts WHERE user_id=?',(uid,));db.execute('DELETE FROM profiles WHERE id=?',(uid,))


def route(db,method,path,uid,data,session):
    a=account(db,uid)
    if path=='/api/account' and method=='GET':
        return {'account':({k:a[k] for k in ('email','email_verified','status','role','visible','notify','created')} if a else None),'policy':POLICY,'demo':not bool(a),'csrf':session['csrf']}
    if path=='/api/notifications' and method=='GET':
        return {'items':[dict(r) for r in db.execute('SELECT * FROM inbox WHERE user_id=? ORDER BY id DESC LIMIT 50',(uid,))],'unread':db.execute('SELECT COUNT(*) FROM inbox WHERE user_id=? AND seen=0',(uid,)).fetchone()[0]}
    if path=='/api/notifications/read' and method=='POST':db.execute('UPDATE inbox SET seen=1 WHERE user_id=? AND id<=?',(uid,int(data.get('through',0))));return {'ok':True}
    if path=='/api/sessions' and method=='GET':
        return {'sessions':[{'id':r['token'][:16],'expires':r['expires'],'current':r['token']==session['token']} for r in db.execute('SELECT token,expires FROM sessions WHERE user_id=? AND expires>? ORDER BY expires DESC',(uid,time.time()))]}
    if path=='/api/sessions/revoke' and method=='POST':
        if data.get('all_other') is True:db.execute('DELETE FROM sessions WHERE user_id=? AND token!=?',(uid,session['token']))
        else:
            sid=text(data.get('id'),16,16)
            db.execute('DELETE FROM sessions WHERE user_id=? AND substr(token,1,16)=?',(uid,sid))
        audit(db,uid,'session.revoked');return {'ok':True}
    if path=='/api/preferences' and method=='POST':
        if not a:raise APIError(400,'Preferences require a registered account.')
        visible=data.get('visible') is True
        if visible and not a['email_verified']:raise APIError(400,'Verify your email before showing your profile. Email verification is not identity verification.')
        db.execute('UPDATE accounts SET visible=?,notify=? WHERE user_id=?',(int(visible),int(data.get('notify') is True),uid));return {'ok':True}
    if path=='/api/password' and method=='POST':
        if not a or not password_matches(data.get('current_password'),a['password_hash']):raise APIError(403,'Confirm your current password.')
        hashed=password_hash(data.get('password'));db.execute('UPDATE accounts SET password_hash=? WHERE user_id=?',(hashed,uid));db.execute('DELETE FROM sessions WHERE user_id=?',(uid,));audit(db,uid,'account.password_changed');return {'ok':True,'signed_out':True}
    if path=='/api/email/resend' and method=='POST':
        if not a:raise APIError(400,'Registered account required.')
        rate(db,'verify:'+uid,3,1800);challenge(db,uid,'verify');return {'ok':True,'message':'Verification queued. Delivery requires a configured email transport.'}
    if path=='/api/account/export' and method=='POST':
        if not a or not password_matches(data.get('password'),a['password_hash']):raise APIError(403,'Confirm your password to export your data.')
        audit(db,uid,'account.exported');return export_account(db,uid)
    if path=='/api/account/delete' and method=='POST':
        if not a or not password_matches(data.get('password'),a['password_hash']) or data.get('confirmation')!='DELETE':raise APIError(403,'Confirm your password and type DELETE to delete this account.')
        delete_account(db,uid);return {'ok':True,'message':'Account data deleted from the active database. Outside bookings and downloaded files are not removed. Backup expiry follows operator policy.'}
    if path=='/api/appeals' and method=='GET':
        return {'decisions':[dict(r) for r in db.execute("SELECT r.id,r.status,v.suspension_reason member_reason,v.updated FROM reports r JOIN report_reviews v ON v.report_id=r.id WHERE r.target=? AND v.suspended_by IS NOT NULL AND v.restriction_active=1",(uid,))],'appeals':[dict(r) for r in db.execute('SELECT id,report_id,body,status,response,created FROM appeals WHERE user_id=?',(uid,))]}
    if path=='/api/appeal' and method=='POST':
        rid=int(data.get('report_id',0));body=text(data.get('body'),3,2000)
        if not db.execute("SELECT 1 FROM reports r JOIN report_reviews v ON v.report_id=r.id WHERE r.id=? AND r.target=? AND v.suspended_by IS NOT NULL AND v.restriction_active=1",(rid,uid)).fetchone():raise APIError(404,'Decision unavailable.')
        if db.execute("SELECT 1 FROM appeals WHERE user_id=? AND report_id=? AND status='pending'",(uid,rid)).fetchone():raise APIError(409,'An appeal is already pending.')
        db.execute('INSERT INTO appeals(user_id,report_id,body,created) VALUES(?,?,?,?)',(uid,rid,body,now()));audit(db,uid,'appeal.submitted',rid);return {'ok':True,'message':'Appeal recorded. Review requires an assigned human moderator.'}
    if path.startswith('/api/admin/'):
        if not a or a['role']!='moderator' or a['status']!='active':raise APIError(403,'Moderator access required.')
        if path=='/api/admin/reports' and method=='GET':
            audit(db,uid,'moderation.queue_read')
            return {'reports':[dict(r) for r in db.execute('SELECT r.*,COALESCE(v.severity,\'medium\') severity,COALESCE(v.version,1) version,v.outcome,v.member_reason FROM reports r LEFT JOIN report_reviews v ON v.report_id=r.id ORDER BY r.id DESC LIMIT 100')],'appeals':[dict(r) for r in db.execute("SELECT * FROM appeals WHERE status='pending' ORDER BY id LIMIT 100")]}
        if path=='/api/admin/action' and method=='POST':
            rid=int(data.get('report_id',0));r=db.execute('SELECT * FROM reports WHERE id=?',(rid,)).fetchone()
            if not r:raise APIError(404,'Report unavailable.')
            if uid in (r['actor'],r['target']):raise APIError(403,'Another moderator must handle a report involving you.')
            review=db.execute('SELECT * FROM report_reviews WHERE report_id=?',(rid,)).fetchone();version=review['version'] if review else 1
            if data.get('version')!=version:raise APIError(409,'Another reviewer updated this case. Refresh the queue.')
            outcome=data.get('outcome');severity=data.get('severity','medium');reason=text(data.get('member_reason'),3,1000)
            if outcome not in ('triage','resolve','suspend','reinstate') or severity not in ('low','medium','high','urgent'):raise APIError(400,'Choose a supported moderation action.')
            target=account(db,r['target'])
            if outcome in ('suspend','reinstate'):
                if not target or target['role']=='moderator':raise APIError(400,'A registered non-moderator account is required.')
                db.execute('UPDATE accounts SET status=? WHERE user_id=?',('suspended' if outcome=='suspend' else 'active',r['target']))
                db.execute('DELETE FROM sessions WHERE user_id=?',(r['target'],))
            suspended_by=uid if outcome=='suspend' else (review['suspended_by'] if review else None)
            suspension_reason=reason if outcome=='suspend' else (review['suspension_reason'] if review else None)
            restriction_active=1 if outcome=='suspend' else 0 if outcome=='reinstate' else (review['restriction_active'] if review else 0)
            db.execute('INSERT OR REPLACE INTO report_reviews(report_id,severity,version,outcome,member_reason,updated,suspended_by,suspension_reason,restriction_active) VALUES(?,?,?,?,?,?,?,?,?)',(rid,severity,version+1,outcome,reason,now(),suspended_by,suspension_reason,restriction_active))
            if outcome in ('suspend','reinstate'):
                active=db.execute('SELECT 1 FROM report_reviews v JOIN reports r ON v.report_id=r.id WHERE r.target=? AND v.restriction_active=1',(r['target'],)).fetchone()
                db.execute('UPDATE accounts SET status=? WHERE user_id=?',('suspended' if active else 'active',r['target']))
            db.execute('UPDATE reports SET status=? WHERE id=?',('triaged' if outcome=='triage' else 'resolved',rid));audit(db,uid,'moderation.'+outcome,rid)
            return {'ok':True}
        if path=='/api/admin/appeal' and method=='POST':
            appeal=db.execute("SELECT * FROM appeals WHERE id=? AND status='pending'",(int(data.get('id',0)),)).fetchone()
            if not appeal:raise APIError(404,'Pending appeal unavailable.')
            report=db.execute('SELECT * FROM reports WHERE id=?',(appeal['report_id'],)).fetchone()
            if uid in (appeal['user_id'],report['actor']):raise APIError(403,'Another moderator must review this appeal.')
            # A second person must review appeals, not the original sanctioning moderator.
            original=db.execute('SELECT suspended_by FROM report_reviews WHERE report_id=?',(appeal['report_id'],)).fetchone()
            if original and original[0]==uid:raise APIError(403,'A different moderator must review this appeal.')
            response=text(data.get('response'),3,1000);decision=data.get('decision')
            if decision not in ('upheld','overturned'):raise APIError(400,'Choose uphold or overturn.')
            db.execute('UPDATE appeals SET status=?,response=? WHERE id=?',(decision,response,appeal['id']))
            if decision=='overturned':
                db.execute("UPDATE report_reviews SET outcome='reinstate',restriction_active=0,version=version+1,member_reason=?,updated=? WHERE report_id=?",(response,now(),appeal['report_id']))
                active=db.execute('SELECT 1 FROM report_reviews v JOIN reports r ON v.report_id=r.id WHERE r.target=? AND v.restriction_active=1',(appeal['user_id'],)).fetchone()
                db.execute('UPDATE accounts SET status=? WHERE user_id=?',('suspended' if active else 'active',appeal['user_id']))
            audit(db,uid,'appeal.'+decision,appeal['id']);return {'ok':True}
    return None


def retention(db):
    """Explicit operator-invoked maintenance; no hidden scheduler."""
    t=time.time();cut=lambda days:(dt.datetime.now(dt.timezone.utc)-dt.timedelta(days=days)).isoformat()
    counts={}
    for name,q,args in [
      ('sessions','DELETE FROM sessions WHERE expires<?',(t,)),
      ('challenges','DELETE FROM auth_challenges WHERE expires<? OR used=1',(t,)),
      ('rate_limits','DELETE FROM limits WHERE expires<?',(t,)),
      ('notifications','DELETE FROM inbox WHERE created<?',(cut(30),)),
      ('mail','DELETE FROM mail_outbox WHERE created<?',(cut(2),)),
      ('audit','DELETE FROM audit WHERE created<?',(cut(90),))]:counts[name]=db.execute(q,args).rowcount
    return counts
