// Authenticated encrypted snapshots. Keys stay in private files, never arguments or logs.
import fs from 'node:fs';
import crypto from 'node:crypto';
const [command,...args]=process.argv.slice(2);
function privateKey(path){const stat=fs.statSync(path);if((stat.mode&0o077)!==0)throw Error('Key file must be mode 600 or stricter.');const key=fs.readFileSync(path);if(key.length!==32)throw Error('Expected a 32-byte key file.');return key}
function writeExclusive(path,data){fs.writeFileSync(path,data,{mode:0o600,flag:'wx'})}
try{
 if(command==='init-key'&&args.length===1){writeExclusive(args[0],crypto.randomBytes(32));console.log('Private backup key created. Keep it outside source control and backups.');}
 else if(command==='encrypt'&&args.length===3){const [source,target,keyfile]=args,key=privateKey(keyfile),iv=crypto.randomBytes(12),header=Buffer.from('VESPRA2\0');const cipher=crypto.createCipheriv('aes-256-gcm',key,iv);cipher.setAAD(header);const data=Buffer.concat([cipher.update(fs.readFileSync(source)),cipher.final()]);writeExclusive(target,Buffer.concat([header,iv,cipher.getAuthTag(),data]));console.log('Encrypted snapshot created.');}
 else if(command==='decrypt'&&args.length===3){const [source,target,keyfile]=args,key=privateKey(keyfile),raw=fs.readFileSync(source),header=raw.subarray(0,8);if(!header.equals(Buffer.from('VESPRA2\0')))throw Error('Invalid snapshot format.');const decipher=crypto.createDecipheriv('aes-256-gcm',key,raw.subarray(8,20));decipher.setAAD(header);decipher.setAuthTag(raw.subarray(20,36));const plain=Buffer.concat([decipher.update(raw.subarray(36)),decipher.final()]);writeExclusive(target,plain);console.log('Snapshot authenticated and decrypted.');}
 else throw Error('Usage: backup.mjs init-key KEYFILE | encrypt SOURCE TARGET KEYFILE | decrypt SOURCE TARGET KEYFILE');
}catch(_){console.error('Backup operation failed. Check arguments, file permissions, key, and snapshot integrity. No existing destination was overwritten.');process.exitCode=1;}
