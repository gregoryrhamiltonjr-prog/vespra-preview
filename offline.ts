import * as SQLite from 'expo-sqlite';
import {dispatch,fresh} from './offline-core';
let database:Promise<SQLite.SQLiteDatabase>|null=null;
function db(){if(!database)database=(async()=>{const d=await SQLite.openDatabaseAsync('vespra-fictional-preview.sqlite3');await d.execAsync('PRAGMA journal_mode=WAL; CREATE TABLE IF NOT EXISTS preview_store(id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL);');return d})();return database}
const store={async load(){const d=await db();const row=await d.getFirstAsync<{value:string}>('SELECT value FROM preview_store WHERE id=1');if(!row)return fresh();return JSON.parse(row.value)},async save(value:any){const d=await db();await d.runAsync('INSERT INTO preview_store(id,value) VALUES(1,?) ON CONFLICT(id) DO UPDATE SET value=excluded.value',JSON.stringify(value))}};
let tail:Promise<unknown>=Promise.resolve();
function serialize<T>(fn:()=>Promise<T>){const result=tail.then(fn);tail=result.catch(()=>{});return result}
export function offlineApi(path:string,data?:Record<string,unknown>){return serialize(()=>dispatch(store,path,data))}
export function offlineLogout(){return serialize(async()=>{const s=await store.load();s.actor=null;await store.save(s)})}
