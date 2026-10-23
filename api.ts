import * as SecureStore from 'expo-secure-store';
export const isOfflinePreview=process.env.EXPO_PUBLIC_PREVIEW_MODE==='offline';
const base=(process.env.EXPO_PUBLIC_API_URL||(__DEV__?'http://127.0.0.1:8765':'')).replace(/\/$/,'');
function validBase(){
 try{const u=new URL(base);return !u.username&&!u.password&&!u.search&&!u.hash&&['','/'].includes(u.pathname)&&(u.protocol==='https:'||(__DEV__&&u.protocol==='http:'&&['127.0.0.1','localhost','10.0.2.2'].includes(u.hostname)))}catch(_){return false}
}
let token='',csrf='';
const key='vespra.evaluation.session';
export async function restoreSession(){if(isOfflinePreview)return;const s=await SecureStore.getItemAsync(key);if(s){try{const parsed=JSON.parse(s);if(parsed.origin!==base||typeof parsed.token!=='string'||typeof parsed.csrf!=='string'){await clearSession();return}token=parsed.token;csrf=parsed.csrf}catch(_){await clearSession()}}}
export async function clearSession(){token='';csrf='';if(isOfflinePreview){const local=await import('./offline');await local.offlineLogout();return}await SecureStore.deleteItemAsync(key)}
export async function api(path:string,body?:Record<string,unknown>):Promise<any>{
  if(isOfflinePreview){const local=await import('./offline');return local.offlineApi(path,body)}
  if(!validBase())throw new Error('Configure an HTTPS EXPO_PUBLIC_API_URL for this evaluation build. No server is contacted without a valid configuration.');
  const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),15000);
  try{
    const r=await fetch(base+'/api/'+path,{method:body?'POST':'GET',signal:controller.signal,headers:{'Content-Type':'application/json','X-Vespra-Client':'native',...(token?{'Authorization':'Bearer '+token}:{}),...(csrf?{'X-CSRF-Token':csrf}:{})},body:body?JSON.stringify(body):undefined});
    const data=await r.json();
    if(!r.ok){if(r.status===401&&!['login','recovery/complete'].includes(path))await clearSession();throw Object.assign(new Error(data.error||'Request failed. Try again.'),{status:r.status})}
    if(data.access_token){token=data.access_token;csrf=data.csrf;await SecureStore.setItemAsync(key,JSON.stringify({origin:base,token,csrf}),{keychainAccessible:SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY})}
    return data;
  }finally{clearTimeout(timeout)}
}
