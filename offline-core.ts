/* Fictional, single-device preview. Never a live member service or booking provider. */
export type Store={load():Promise<any>;save(value:any):Promise<void>};
const zone='America/New_York';
const rows=[
 ['alex','Alex',32,'Architect','Brooklyn','Making room for good conversation and long dinners.',['Architecture','Cooking','Long walks']],
 ['marcus','Marcus',34,'Community health lead','Fort Greene','Big on small gestures and dinner with friends.',['Food','Museums','Cycling']],
 ['daniel','Daniel',29,'Creative producer','Lower East Side','Queer, coffee curious, and always up for a film.',['Film','Coffee','Design']],
 ['rafael','Rafael',38,'Teacher','Astoria','Trans man, amateur gardener, enthusiastic home cook.',['Gardening','Theatre','Cooking']],
 ['eli','Eli',31,'Independent illustrator','Park Slope','Bi, Brooklyn-based, and learning to leave my sketchbook at home.',['Art','Pizza','Hiking']],
 ['james','James',42,'Public interest lawyer','Harlem','Good company over impressive credentials.',['Jazz','Running','Volunteering']]
];
export function fresh(){return {version:1,actor:null,people:rows.map(r=>({id:r[0],name:r[1],age:r[2],role:r[3],area:r[4],bio:r[5],interests:r[6],company_private:1,prompt:'A small joy',answer:'A good question and nowhere to rush.'})),likes:[{sender:'marcus',recipient:'alex'}],matches:[],messages:[],dates:[],reflections:{},blocks:[],reports:[],inbox:[],next:1}}
function fail(message:string,status=400):never{throw Object.assign(new Error(message),{status})}
function text(value:unknown,min=1,max=2000){if(typeof value!=='string'||value.trim().length<min||value.trim().length>max)fail(`Use ${min}–${max} characters.`);return value.trim()}
function blocked(s:any,a:string,b:string){return s.blocks.some((x:any)=>(x.actor===a&&x.target===b)||(x.actor===b&&x.target===a))}
function member(s:any,id:string){return s.people.find((x:any)=>x.id===id)||fail('Fictional profile unavailable.')}
function connection(s:any,id:string){const m=s.matches.find((x:any)=>x.id===id&&(x.a===s.actor||x.b===s.actor));if(!m||blocked(s,m.a,m.b))fail('Connection unavailable.');return m}
function event(s:any,who:string,kind:string,entity:string){s.inbox.push({id:s.next++,user_id:who,kind,entity,title:'You have a fictional preview update',created:new Date().toISOString(),seen:0})}
function localParts(timestamp:number,timeZone:string){const p=new Intl.DateTimeFormat('en-CA',{timeZone,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date(timestamp));const n=(k:string)=>Number(p.find(x=>x.type===k)?.value);return [n('year'),n('month'),n('day'),n('hour'),n('minute')]}
export function localTime(value:string,timeZone=zone,now=Date.now()){
 const match=/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(value||'');if(!match)fail('Use local time YYYY-MM-DDTHH:mm.');
 const [y,m,d,h,min]=match!.slice(1).map(Number),naive=Date.UTC(y,m-1,d,h,min),v=new Date(naive);
 if(v.getUTCFullYear()!==y||v.getUTCMonth()!==m-1||v.getUTCDate()!==d||h>23||min>59)fail('Choose a valid local date and time.');
 const candidates=new Map<number,number>();
 try{for(const delta of [-36,-24,-12,0,12,24,36]){const sample=naive+delta*3600000,[a,b,c,e,f]=localParts(sample,timeZone);const offset=(Date.UTC(a,b-1,c,e,f)-sample)/60000;const candidate=naive-offset*60000;if(localParts(candidate,timeZone).join(',')===[y,m,d,h,min].join(','))candidates.set(candidate,offset)}}catch(_){fail('Choose a valid IANA timezone.')}
 if(candidates.size!==1)fail(candidates.size?'This time is ambiguous during a clock change. Choose another.':'That local time does not exist. Choose another.');
 const [timestamp,offset]=[...candidates][0];if(timestamp<=now)fail('Choose a future time.');const abs=Math.abs(offset),two=(n:number)=>String(n).padStart(2,'0');return value+':00'+(offset>=0?'+':'-')+two(Math.floor(abs/60))+':'+two(abs%60)
}
export async function dispatch(store:Store,path:string,data?:Record<string,any>){
 const original=await store.load(),s=JSON.parse(JSON.stringify(original||fresh())),p=data||{},uid=s.actor;
 const commit=async(result:any={ok:true})=>{await store.save(s);return result};
 if(path==='config')return {demo:true,offlinePreview:true,mode:'offline-fictional-preview',city:'New York',timezone:zone,policy:'2026-10-23.v1',mail_configured:false};
 if(path==='demo'){if(p.adult!==true)fail('This preview is for adults 18 and older.');member(s,p.user||'alex');s.actor=p.user||'alex';return commit({csrf:'local-demo',offlinePreview:true})}
 if(['register','login','recovery/request','recovery/complete','email/verify','email/resend'].includes(path))fail('Offline preview uses fictional adult personas only. No real accounts, email or recovery service are connected.');
 if(!uid)fail('Start an adult fictional preview session.',401);
 if(path==='account')return {account:null,policy:'2026-10-23.v1',demo:true,csrf:'local-demo'};
 if(path==='state'){
  const matches=s.matches.filter((m:any)=>(m.a===uid||m.b===uid)&&!blocked(s,m.a,m.b)),ids=matches.map((m:any)=>m.id);
  return {me:member(s,uid),people:s.people.filter((x:any)=>x.id!==uid&&!blocked(s,uid,x.id)),likes:s.likes.filter((x:any)=>(x.sender===uid||x.recipient===uid)&&!blocked(s,x.sender,x.recipient)),matches,messages:s.messages.filter((x:any)=>ids.includes(x.match_id)),dates:s.dates.filter((x:any)=>ids.includes(x.match_id)).map((d:any)=>({...d,reflection:s.reflections[d.id+':'+uid]||null})),csrf:'local-demo',config:{city:'New York',timezone:zone,demo:true,offlinePreview:true,mode:'offline-fictional-preview',verification:'unavailable',reservationProvider:'manual'}};
 }
 if(path==='logout'){s.actor=null;return commit()}
 if(path==='preview/reset'){const clean=fresh();clean.actor=uid;await store.save(clean);return {ok:true,message:'Fictional data on this phone has been reset. No remote records exist.'}}
 if(path==='like'){
  member(s,p.target);if(p.target===uid||blocked(s,uid,p.target))fail('Profile unavailable.');if(!s.likes.some((x:any)=>x.sender===uid&&x.recipient===p.target)){s.likes.push({sender:uid,recipient:p.target});event(s,p.target,'interest',uid)}
  const mutual=s.likes.some((x:any)=>x.sender===p.target&&x.recipient===uid);if(mutual){const [a,b]=[uid,p.target].sort();if(!s.matches.some((x:any)=>x.a===a&&x.b===b))s.matches.push({id:a+'_'+b,a,b})}return commit({matched:mutual});
 }
 if(path==='message'){const m=connection(s,p.match_id);s.messages.push({id:s.next++,match_id:m.id,sender:uid,body:text(p.body),created:new Date().toISOString()});event(s,m.a===uid?m.b:m.a,'message',m.id);return commit()}
 if(path==='date'){
  const m=connection(s,p.match_id),starts=localTime(p.starts,p.timezone||zone),venue=text(p.venue,2,160),id='preview-date-'+s.next++;
  s.dates.push({id,match_id:m.id,proposer:uid,venue,starts,timezone:p.timezone||zone,revision:1,status:'proposed',reservation:'not_requested',accepted_by:[uid]});event(s,m.a===uid?m.b:m.a,'plan',id);return commit()
 }
 if(['accept','revise','cancel','reserve','complete','reflect'].includes(path)){
  const d=s.dates.find((x:any)=>x.id===p.date_id);if(!d)fail('Plan unavailable.');const m=connection(s,d.match_id);if(p.revision!==d.revision)fail('The plan changed. Review its latest details.',409);if(d.status==='cancelled')fail('This plan was cancelled.');
  if(path==='accept'){if(!['proposed','agreed'].includes(d.status))fail('This plan cannot be accepted.');if(!d.accepted_by.includes(uid))d.accepted_by.push(uid);if(d.accepted_by.length===2)d.status='agreed'}
  if(path==='revise'){if(!['proposed','agreed'].includes(d.status))fail('This plan cannot change.');d.venue=text(p.venue,2,160);d.starts=localTime(p.starts,d.timezone);d.revision++;d.accepted_by=[uid];d.status='proposed';d.reservation='not_requested'}
  if(path==='cancel'){if(!['proposed','agreed'].includes(d.status))fail('This plan is no longer active.');d.status='cancelled';d.reservation='not_requested'}
  if(path==='reserve'){if(d.status!=='agreed')fail('Both people must agree first.');d.reservation='manual_action_required';return commit({status:'manual_action_required',message:'No reservation has been made. This offline preview cannot contact venues. Contact the venue yourself for any real booking.'})}
  if(path==='complete'){if(d.status!=='agreed'||Date.parse(d.starts)>Date.now())fail('Mark a date met only after its agreed start time.');d.status='met'}
  if(path==='reflect'){if(d.status!=='met')fail('Reflect after meeting.');s.reflections[d.id+':'+uid]=text(p.body)}
  else event(s,m.a===uid?m.b:m.a,'plan',d.id);
  return commit()
 }
 if(path==='profile'){const me=member(s,uid);if(p.bio!==undefined)me.bio=typeof p.bio==='string'&&p.bio.length<=500?p.bio:fail('Keep your bio under 500 characters.');for(const [key,max] of [['name',60],['role',80],['area',80],['prompt',100],['answer',500]] as const){if(p[key]!==undefined)me[key]=text(p[key],1,max)}if(p.interests!==undefined){if(!Array.isArray(p.interests)||p.interests.length>8)fail('Choose up to eight interests.');me.interests=p.interests.map((x:unknown)=>text(x,1,30))}me.company_private=1;return commit()}
 if(path==='block'||path==='report'){
  member(s,p.target);if(p.target===uid)fail('Choose another fictional person.');
  if(path==='block'){if(!s.blocks.some((x:any)=>x.actor===uid&&x.target===p.target))s.blocks.push({actor:uid,target:p.target});const [a,b]=[uid,p.target].sort(),mid=a+'_'+b,dids=s.dates.filter((d:any)=>d.match_id===mid).map((d:any)=>d.id);s.inbox=s.inbox.filter((x:any)=>!([uid,p.target].includes(x.user_id)&&[uid,p.target,mid,...dids].includes(x.entity)));return commit()}
  s.reports.push({id:s.next++,actor:uid,target:p.target,reason:text(p.reason,3,1000),created:new Date().toISOString(),status:'device_only_not_sent'});return commit({message:'Fictional report saved only on this phone. No report was sent to a moderator or emergency service.'})
 }
 if(path==='notifications'){const items=s.inbox.filter((x:any)=>x.user_id===uid);return {items:items.slice(-50).reverse(),unread:items.filter((x:any)=>!x.seen).length}}
 if(path==='notifications/read'){for(const x of s.inbox)if(x.user_id===uid&&x.id<=p.through)x.seen=1;return commit()}
 if(path==='sessions')return {sessions:[{id:'device-only',current:true,expires:0}]};
 if(path==='sessions/revoke')return {ok:true,message:'This is a device-only preview. No server sessions or other phones are connected.'};
 if(path==='appeals')return {decisions:[],appeals:[]};
 if(path==='verification'||path==='membership')return {status:'unavailable',message:'Offline fictional preview: identity/age verification, payments and subscriptions are not connected.'};
 fail('This feature requires a connected service and is not part of the offline preview.',404)
}
