#!/usr/bin/env node
/** Read-only test of actual generated object WAVs, both locally and on Pages. */
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const site=path.resolve(process.env.KU100_SITE_DIR||path.join(root,'dist'));
const out=path.resolve(process.env.KU100_OBJECT_REPORT_DIR||path.join(root,'validation/local/object-browser'));
const {chromium,request}=await import(pathToFileURL(process.env.KU100_PLAYWRIGHT_MODULE||path.join(root,'web/node_modules/playwright/index.mjs')).href);
const hash=b=>createHash('sha256').update(b).digest('hex');
let server,browser,api,base=process.env.KU100_OBJECT_URL;
const report={schema:'object-browser/1',passed:false,checks:[],assets:[],samples:[],errors:[],human_listening_performed:false};
await fs.mkdir(out,{recursive:true});
try{
 const m=JSON.parse(await fs.readFile(path.join(site,'objects/generated/manifest.json'),'utf8'));
 assert.equal(m.samples.length,9);assert.equal(m.reference_audio_public,false);assert.equal(m.physical_calibration,false);
 if(!base){server=http.createServer(async(req,res)=>{try{
  const name=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  const file=path.resolve(site,'.'+(name.endsWith('/')?name+'index.html':name));
  if(!file.startsWith(site+path.sep))throw Error('Invalid path');
  const b=await fs.readFile(file);res.writeHead(200,{'Content-Type':{'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json','.wav':'audio/wav'}[path.extname(file)]||'application/octet-stream'});res.end(b);
 }catch{res.writeHead(404);res.end('not found');}});
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));base=`http://127.0.0.1:${server.address().port}/objects/`;}
 report.url=base;api=await request.newContext({ignoreHTTPSErrors:false,timeout:30000});
 for(const name of ['index.html','app.js','style.css','generated/manifest.json',...m.samples.map(s=>'generated/'+s.file)]){
  const expected=hash(await fs.readFile(path.resolve(site,'objects',name)));let row;
  for(let i=0;i<5;i++){const r=await api.get(new URL(name,base).href,{headers:{'Cache-Control':'no-cache'}});row={path:name,status:r.status(),sha256:hash(await r.body()),expected_sha256:expected};if(row.status===200&&row.sha256===expected)break;if(i<4)await new Promise(resolve=>setTimeout(resolve,8000));}
  report.assets.push(row);assert.equal(row.status,200);assert.equal(row.sha256,expected);
 }
 report.checks.push('All 13 object assets match exact tested bytes');
 browser=await chromium.launch({headless:true,args:['--mute-audio'],...(process.env.KU100_BROWSER_EXECUTABLE?{executablePath:process.env.KU100_BROWSER_EXECUTABLE}:{})});report.browser=browser.version();
 const context=await browser.newContext({viewport:{width:1380,height:1000},acceptDownloads:true});const page=await context.newPage();
 page.on('pageerror',e=>report.errors.push(String(e)));page.on('request',r=>{if(/^https?:/.test(r.url())&&(new URL(r.url()).origin!==new URL(base).origin||r.method()!=='GET'))report.errors.push('Unexpected network '+r.url());});
 assert.equal((await page.goto(base,{waitUntil:'networkidle'})).status(),200);await page.waitForFunction(()=>document.querySelector('#status').textContent.startsWith('All nine'));
 assert.match(await page.locator('.scope').textContent(),/not recording playback/);
 for(const item of m.samples){const card=page.locator(`article[data-object="${item.object}"]`);await card.locator('select').selectOption(item.kind);const audio=card.locator('audio');
  const decoded=await audio.evaluate(async(a,item)=>{
   const b=await(await fetch(a.src)).arrayBuffer();const raw=await(await fetch('./generated/'+item.file)).arrayBuffer();
   const {parseWave}=await import('../target/core.js');const p=parseWave(new Uint8Array(raw));
   const d=await new OfflineAudioContext(2,1,p.sampleRate).decodeAudioData(b.slice(0));
   const direct=await new OfflineAudioContext(2,1,p.sampleRate).decodeAudioData(raw.slice(0));
   let error=0,earDifference=0,nativePcmDecodeMaxError=0;
   for(let c=0;c<2;c++)for(let i=0;i<d.length;i++){
    error=Math.max(error,Math.abs(d.getChannelData(c)[i]-p.samples[c][i]));
    nativePcmDecodeMaxError=Math.max(nativePcmDecodeMaxError,Math.abs(direct.getChannelData(c)[i]-p.samples[c][i]));
   }
   for(let i=0;i<d.length;i++)earDifference=Math.max(earDifference,Math.abs(d.getChannelData(0)[i]-d.getChannelData(1)[i]));
   return {channels:d.numberOfChannels,frames:d.length,rate:d.sampleRate,error,earDifference,nativePcmDecodeMaxError};
  },item);
  const {nativePcmDecodeMaxError,...exact}=decoded;
  assert.ok(Number.isFinite(nativePcmDecodeMaxError));
  assert.deepEqual(exact,{channels:2,frames:item.frames,rate:48000,error:0,earDifference:0});
  await card.locator('button').click();await page.waitForFunction(id=>{const a=document.querySelector(`article[data-id="${id}"] audio`);return a.currentTime>.16&&!a.paused;},item.id);
  assert.equal(await page.locator('audio').evaluateAll(xs=>xs.filter(a=>!a.paused).length),1);
  await audio.evaluate(a=>{a.pause();a.currentTime=a.duration-.2;});await page.waitForFunction(id=>{const a=document.querySelector(`article[data-id="${id}"] audio`);return !a.seeking&&Math.abs(a.currentTime-(a.duration-.2))<.005;},item.id);
  const wait=page.waitForEvent('download');await card.locator('a.download').click();const download=await wait;assert.equal(await download.failure(),null);assert.equal(hash(await fs.readFile(await download.path())),item.sha256);
  report.samples.push({id:item.id,...decoded,played:true,seek_completed:true,download_sha256:item.sha256});
 }
 report.checks.push('Nine original PCM16 files download unchanged; explicit Float32 previews match original sample codes exactly, play and seek');
 const cards=page.locator('article');await cards.nth(0).locator('button').click();await cards.nth(1).locator('button').click();assert.equal(await page.locator('audio').evaluateAll(xs=>xs.filter(a=>!a.paused).length),1);await page.locator('#stop').click();assert.equal(await page.locator('audio').evaluateAll(xs=>xs.filter(a=>!a.paused).length),0);
 report.checks.push('Exclusive playback and Stop all work');
 for(const width of [1380,390]){await page.setViewportSize({width,height:width===390?844:1000});await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth+1);await page.screenshot({path:path.join(out,width===390?'mobile.png':'desktop.png'),fullPage:true});}
 report.checks.push('Desktop/mobile fit; no external requests or uncaught errors');assert.deepEqual(report.errors,[]);report.passed=true;await context.close();
}catch(e){report.error=String(e.stack||e);process.exitCode=1;console.error(report.error);}
finally{await fs.writeFile(path.join(out,'object-browser.json'),JSON.stringify(report,null,2)+'\n');if(browser)await browser.close();if(api)await api.dispose();if(server)await new Promise(resolve=>server.close(resolve));console.log(JSON.stringify({passed:report.passed,url:base}));}
