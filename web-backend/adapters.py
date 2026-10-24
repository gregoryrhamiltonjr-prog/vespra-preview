"""Provider-independent contracts; disabled capabilities fail honestly.
No invented partner endpoint or undocumented SDK integration.
"""
from dataclasses import dataclass
from typing import Protocol
import json, os, smtplib, ssl, time, datetime
from email.message import EmailMessage
from pathlib import Path

@dataclass(frozen=True)
class ReservationResult:
    status:str
    message:str
    reference:str|None=None

class BookingProvider(Protocol):
    def reserve(self,plan:dict,idempotency_key:str)->ReservationResult: ...
    def cancel(self,reference:str,idempotency_key:str)->ReservationResult: ...

class ManualBooking:
    def reserve(self,plan,idempotency_key):
        return ReservationResult('manual_action_required','No reservation has been made. Contact the venue directly. Both people can still see the agreed plan.')
    def cancel(self,reference,idempotency_key):
        return ReservationResult('manual_action_required','Contact the venue to cancel any outside booking. VESPRA has not cancelled it.')

class IdentityProvider(Protocol):
    def begin(self,user_id:str)->dict: ...

class DisabledIdentity:
    def begin(self,user_id):
        return {'status':'unavailable','message':'Identity and age assurance are not connected. Do not upload identity documents. Email confirmation is not identity verification.'}

class DisabledBilling:
    def checkout(self,user_id):
        return {'status':'unavailable','message':'Membership billing is not enabled. No payment or subscription has been created.'}

class DisabledPush:
    def send(self,device,notification):
        return {'status':'not_sent','message':'Push provider not configured. Updates remain in the in-app inbox.'}

class SMTPTransport:
    """Credentials are loaded only from an owner-provisioned, private mounted file."""
    def __init__(self,config):self.config=config
    def send(self,recipient,subject,body):
        c=self.config
        message=EmailMessage();message['From']=c['from'];message['To']=recipient;message['Subject']=subject;message.set_content(body)
        with smtplib.SMTP_SSL(c['host'],int(c.get('port',465)),context=ssl.create_default_context(),timeout=20) as smtp:
            if c.get('username'):smtp.login(c['username'],c['password'])
            smtp.send_message(message)

class UnconfiguredMail:
    def send(self,recipient,subject,body):raise RuntimeError('mail_not_configured')

def mail_transport():
    p=os.environ.get('VESPRA_MAIL_CONFIG_FILE')
    if not p:return UnconfiguredMail()
    path=Path(p)
    if path.stat().st_mode & 0o077:raise RuntimeError('Mail configuration file must not be group/world accessible.')
    return SMTPTransport(json.loads(path.read_text()))

def deliver_mail(db,transport=None,batch=20):
    """Operator-invoked durable retry queue. No body or address is logged.
    Mail may be retried after a crash between delivery and acknowledgement.
    """
    transport=transport or mail_transport();out={'sent':0,'deferred':0,'failed':0}
    rows=db.execute("SELECT * FROM mail_outbox WHERE status IN ('queued','retry') AND available<=? ORDER BY id LIMIT ?",(time.time(),min(batch,100))).fetchall()
    for r in rows:
        created=datetime.datetime.fromisoformat(r['created']).timestamp()
        if time.time()-created>=1800:
            db.execute("UPDATE mail_outbox SET status='expired',body='',last_error='expired_before_delivery' WHERE id=?",(r['id'],));out['failed']+=1;continue
        try:transport.send(r['recipient'],r['subject'],r['body'])
        except Exception:
            attempts=r['attempts']+1;terminal=attempts>=5
            db.execute('UPDATE mail_outbox SET status=?,attempts=?,available=?,last_error=? WHERE id=?',('failed' if terminal else 'retry',attempts,time.time()+min(3600,60*2**attempts),'delivery_unavailable',r['id']))
            out['failed' if terminal else 'deferred']+=1
        else:
            # Do not retain delivered verification/recovery codes in the active outbox.
            db.execute("UPDATE mail_outbox SET status='sent',body='',attempts=attempts+1,last_error=NULL WHERE id=?",(r['id'],));out['sent']+=1
    return out
