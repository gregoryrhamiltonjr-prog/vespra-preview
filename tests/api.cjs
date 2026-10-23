const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),ts=require('typescript');
const source=ts.transpileModule(fs.readFileSync('api.ts','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
function make(url,dev=true){const storage=new Map(),calls=[];let result={csrf:'test-csrf',access_token:'test-session-placeholder'};let status=200;
 const secure={WHEN_UNLOCKED_THIS_DEVICE_ONLY:1,getItemAsync:async k=>storage.get(k)||null,setItemAsync:async(k,v)=>{storage.set(k,v)},deleteItemAsync:async k=>{storage.delete(k)}};
 const context=vm.createContext({exports:{},require:n=>{if(n==='expo-secure-store')return secure;throw Error('Unexpected import')},process:{env:{EXPO_PUBLIC_API_URL:url}},__DEV__:dev,URL,AbortController,setTimeout,clearTimeout,fetch:async(u,options)=>{calls.push({u,options});return {ok:status<400,status,json:async()=>result}}});vm.runInContext(source,context);
 return {api:context.exports,storage,calls,reply:(r,s=200)=>{result=r;status=s}};
}
(async()=>{
 let x=make('',false);await assert.rejects(()=>x.api.api('config'),/HTTPS/);assert.equal(x.calls.length,0);console.log('PASS release build refuses an unconfigured endpoint');
 x=make('http://untrusted.example.invalid',true);await assert.rejects(()=>x.api.api('config'),/HTTPS/);assert.equal(x.calls.length,0);console.log('PASS remote HTTP is refused even in development');
 x=make('http://127.0.0.1:8765',true);await x.api.api('login',{email:'test@example.invalid',password:'test-only-placeholder'});assert.equal(x.storage.size,1);x.reply({ok:true});await x.api.api('message',{body:'test-only-body'});assert.equal(x.calls[1].options.headers.Authorization,'Bearer test-session-placeholder');assert.equal(x.calls[1].options.headers['X-CSRF-Token'],'test-csrf');console.log('PASS native session uses SecureStore and authenticated headers');
 await x.api.clearSession();assert.equal(x.storage.size,0);await x.api.api('config');assert.equal(x.calls[2].options.headers.Authorization,undefined);console.log('PASS logout clears in-memory and persisted credentials');
 x=make('https://evaluation.example.invalid',false);await x.api.api('login',{});x.reply({error:'Expired'},401);await assert.rejects(()=>x.api.api('state'),/Expired/);assert.equal(x.storage.size,0);console.log('PASS expired native sessions are removed from secure storage');
 x=make('https://evaluation.example.invalid',false);x.storage.set('vespra.evaluation.session',JSON.stringify({origin:'https://different.example.invalid',token:'test-only-other-origin',csrf:'test-only-csrf'}));await x.api.restoreSession();assert.equal(x.storage.size,0);x.reply({ok:true});await x.api.api('config');assert.equal(x.calls[0].options.headers.Authorization,undefined);console.log('PASS sessions cannot migrate to a different API origin');
})().catch(e=>{console.error(e.message);process.exitCode=1});
