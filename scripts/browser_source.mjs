#!/usr/bin/env node
/** Actual generated audio, stable identities, stereo-only presentation and no reference upload. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import os from 'node:os';
import {createHash} from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const site=path.resolve(process.env.KU100_SITE_DIR||path.join(root,'dist'));
const out=path.resolve(process.env.KU100_SOURCE_REPORT_DIR||path.join(root,'validation/local/source-browser'));
const {chromium,request}=await import(pathToFileURL(process.env.KU100_PLAYWRIGHT_MODULE||path.join(root,'web/node_modules/playwright/index.mjs')).href);
const hash=x=>createHash('sha256').update(x).digest('hex');
let server,browser,api,temp,base=process.env.KU100_SOURCE_URL;
const report={schema:'source-browser/1',passed:false,checks:[],errors:[],assets:[],samples:[],human_listening_performed:false,reference_test:base?'invalid local file only; no private reference':'synthetic local fixture, not the target recording'};
await fs.mkdir(out,{recursive:true});
try {
 const manifest=JSON.parse(await fs.readFile(path.join(site,'source/generated/iteration.json'),'utf8'));
 assert.equal(manifest.samples.length,7);assert.equal(manifest.reference_audio_public,false);
 if(!base){
  server=http.createServer(async(req,res)=>{try{
   const name=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
   if(name.includes('..'))throw Error('Invalid path');
   const file=path.resolve(site,'.'+(name.endsWith('/')?name+'index.html':name));
   if(!file.startsWith(site+path.sep))throw Error('Invalid path');
   const body=await fs.readFile(file);const type={'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json','.wav':'audio/wav'}[path.extname(file)]||'application/octet-stream';
   res.writeHead(200,{'Content-Type':type});res.end(body);
  }catch{res.writeHead(404);res.end('not found');}});
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));base=`http://127.0.0.1:${server.address().port}/source/`;
 }
 report.url=base;api=await request.newContext({ignoreHTTPSErrors:false,timeout:30000});
 for(const name of ['../core.js','../target/core.js','index.html','app.js','style.css','generated/iteration.json',...manifest.samples.map(s=>'generated/'+s.file)]){
  const expected=hash(await fs.readFile(path.resolve(site,'source',name)));let row;
  for(let i=0;i<5;i++){
   const r=await api.get(new URL(name,base).href,{headers:{'Cache-Control':'no-cache'}});
   row={path:name,status:r.status(),url:r.url(),sha256:hash(await r.body()),expected_sha256:expected};
   if(row.status===200&&row.sha256===expected)break;
   if(i<4)await new Promise(r=>setTimeout(r,8000));
  }
  report.assets.push(row);assert.equal(row.status,200);assert.equal(row.sha256,expected);assert.equal(new URL(row.url).origin,new URL(base).origin);
 }
 report.checks.push('All source page assets and original WAVs match the tested site bytes');
 browser=await chromium.launch({headless:true,args:['--mute-audio'],...(process.env.KU100_BROWSER_EXECUTABLE?{executablePath:process.env.KU100_BROWSER_EXECUTABLE}:{})});report.browser=browser.version();
 const context=await browser.newContext({viewport:{width:1380,height:1000},acceptDownloads:true});
 const page=await context.newPage();page.on('pageerror',e=>report.errors.push(String(e)));
 page.on('request',r=>{if(/^https?:/.test(r.url())&&(new URL(r.url()).origin!==new URL(base).origin||r.method()!=='GET'))report.errors.push('Unexpected network request: '+r.method()+' '+r.url());});
 let fixture;
 temp=await fs.mkdtemp(path.join(os.tmpdir(),'source-browser-'));
 if(!process.env.KU100_SOURCE_URL){
  const bytes=await fs.readFile(path.join(site,'source/generated/revised-right-1.wav'));
  const amended=structuredClone(manifest),ref=amended.reference_descriptors[0];
  ref.sha256=hash(bytes);ref.source_rate_hz=48000;ref.source_frames=(bytes.length-44)/8;ref.crop_frames=[0,288000];ref.crop_s=[0,6];ref.crop_pcm_f32_sha256=hash(bytes.subarray(44,44+288000*8));
  await page.route('**/source/generated/iteration.json',r=>r.fulfill({contentType:'application/json',body:JSON.stringify(amended)}));
  fixture=path.join(temp,'synthetic-local-reference.wav');await fs.writeFile(fixture,bytes);
 }
 assert.equal((await page.goto(base,{waitUntil:'networkidle'})).status(),200);
 async function ready(id){await page.waitForFunction(id=>document.querySelector('#variant').value===id&&!document.querySelector('#play').disabled&&document.querySelector('#audio').readyState>=2,id);}
 await ready('revised-right-1');assert.match(await page.locator('#sound-name').textContent(),/Revised/);assert.equal(await page.locator('#notes').inputValue(),'');
 report.checks.push('Stable named revised source is ready by default without reference loading');
 async function download(selector){const p=page.waitForEvent('download');await page.locator(selector).click();const d=await p;assert.equal(await d.failure(),null);return fs.readFile(await d.path());}
 for(const side of ['right','left']){
  await page.locator('#side').selectOption(side);
  for(const s of manifest.samples.filter(x=>x.side===side)){
   await page.locator('#variant').selectOption(s.id);await ready(s.id);
   assert.equal(hash(await download('#download')),s.sha256);
   const decoded=await page.evaluate(async()=>{
    const buffer=await(await fetch(document.querySelector('#audio').src)).arrayBuffer();
    const {parseWave}=await import('../target/core.js');const p=parseWave(new Uint8Array(buffer));
    const d=await new OfflineAudioContext(2,1,p.sampleRate).decodeAudioData(buffer.slice(0));let error=0;
    for(let c=0;c<2;c++)for(let i=0;i<d.length;i++)error=Math.max(error,Math.abs(d.getChannelData(c)[i]-p.samples[c][i]));
    return {channels:d.numberOfChannels,frames:d.length,rate:d.sampleRate,error};
   });assert.deepEqual(decoded,{channels:2,frames:s.frames,rate:48000,error:0});
   await page.locator('#play').click();await page.waitForFunction(()=>document.querySelector('#audio').currentTime>.15&&!document.querySelector('#audio').paused);
   await page.locator('#stop').click();assert.equal(await page.locator('#audio').evaluate(a=>a.paused),true);
   report.samples.push({id:s.id,sha256:s.sha256,...decoded,played:true});
  }
 }
 report.checks.push('All seven named sources decode exactly, play, stop and download unchanged');
 await page.locator('#side').selectOption('right');await ready('revised-right-1');
 const original=hash(await download('#download'));
 assert.equal(await page.locator('#mode option[value="mono"]').count(),0);
 const stereoDifference=await page.evaluate(async()=>{
  const bytes=new Uint8Array(await(await fetch(document.querySelector('#audio').src)).arrayBuffer());const {parseWave}=await import('../target/core.js');const p=parseWave(bytes);let difference=0;for(let i=0;i<p.frames;i++)difference=Math.max(difference,Math.abs(p.samples[0][i]-p.samples[1][i]));return difference;
 });assert.ok(stereoDifference>0);assert.equal(hash(await download('#download')),original);
 report.checks.push('Stereo-only playback; no public mono mode; original download unchanged');
 const bad=path.join(temp,'bad.wav');await fs.writeFile(bad,'not a supplied recording');await page.locator('#reference-file').setInputFiles(bad);
 await page.waitForFunction(()=>document.querySelector('#reference-status').textContent.includes('not an exact'));
 if(fixture){await page.locator('#reference-file').setInputFiles(fixture);await page.waitForFunction(()=>document.querySelector('#reference-audio').readyState>=2);assert.match(await page.locator('#reference-status').textContent(),/verified locally/);}
 report.checks.push(fixture?'Synthetic reference identity/crop verified locally; bad input rejected; no upload':'Bad local reference rejected on live site without upload');
 for(const width of [1380,390]){await page.setViewportSize({width,height:width===390?844:1000});await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth+1);await page.screenshot({path:path.join(out,width===390?'mobile.png':'desktop.png'),fullPage:true});}
 report.checks.push('Desktop and mobile layouts fit');assert.deepEqual(report.errors,[]);report.passed=true;await context.close();
} catch(e){report.error=String(e.stack||e);console.error(report.error);process.exitCode=1;}
finally{await fs.writeFile(path.join(out,'source-browser.json'),JSON.stringify(report,null,2)+'\n');if(browser)await browser.close();if(api)await api.dispose();if(server)await new Promise(r=>server.close(r));if(temp)await fs.rm(temp,{recursive:true,force:true});console.log(JSON.stringify({passed:report.passed,checks:report.checks.length,url:base}));}
