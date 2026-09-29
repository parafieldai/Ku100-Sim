#!/usr/bin/env node
/** Audio-only target comparison, local import privacy, exact downloads and blank judgments. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';
import http from 'node:http';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const site=path.resolve(process.env.KU100_SITE_DIR||path.join(root,'dist'));
const out=path.resolve(process.env.KU100_TARGET_REPORT_DIR||path.join(root,'validation/local/target-browser'));
const modulePath=process.env.KU100_PLAYWRIGHT_MODULE||path.join(root,'web/node_modules/playwright/index.mjs');
const {chromium,request}=await import(pathToFileURL(modulePath).href);
const hash=b=>createHash('sha256').update(b).digest('hex');
let server,browser,context,api;const report={schema:'target-review-browser/1',passed:false,checks:[],errors:[],human_listening_performed:false};
await fs.mkdir(out,{recursive:true});
async function check(name,fn){await fn();report.checks.push(name);console.log('PASS '+name);}
try{
 let url=process.env.KU100_TARGET_URL;
 if(!url){server=http.createServer(async(req,res)=>{try{let name=decodeURIComponent(new URL(req.url,'http://localhost').pathname).replace(/^\//,'')||'index.html';const p=path.resolve(site,name);if(!p.startsWith(site+path.sep))throw Error('path');const b=await fs.readFile(p);const type={'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json'}[path.extname(p)]||'application/octet-stream';res.writeHead(200,{'Content-Type':type});res.end(b);}catch{res.writeHead(404);res.end();}});await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));url=`http://127.0.0.1:${server.address().port}/target.html`;}
 report.url=url;const remote=url.startsWith('https:');
 if(remote){api=await request.newContext({ignoreHTTPSErrors:false});await check('public target assets are exact tested build bytes',async()=>{for(const name of ['target.html','target.js','target.css','target-study.json','target-reference-summary.json','triggers.json']){const expected=hash(await fs.readFile(path.join(site,name)));let got;for(let k=0;k<5;k++){const r=await api.get(new URL(name,url).href);got={status:r.status(),hash:hash(await r.body())};if(got.status===200&&got.hash===expected)break;await new Promise(r=>setTimeout(r,5000));}assert.equal(got.status,200);assert.equal(got.hash,expected,name);}});}
 browser=await chromium.launch({headless:true,executablePath:process.env.KU100_CHROMIUM_EXECUTABLE||undefined,args:['--mute-audio']});report.browser=browser.version();context=await browser.newContext({acceptDownloads:true,viewport:{width:1440,height:1000}});const page=await context.newPage();let uploads=0;
 page.on('pageerror',e=>report.errors.push(String(e)));page.on('request',r=>{if(r.method()!=='GET')uploads++;});
 await page.route('**/*',route=>{const u=route.request().url();if(u.startsWith('http')&&new URL(u).origin!==new URL(url).origin){report.errors.push('External request '+u);return route.abort();}return route.continue();});
 await page.goto(url,{waitUntil:'networkidle'});await page.waitForFunction(()=>document.documentElement.dataset.targetReady==='true');
 const study=JSON.parse(await fs.readFile(path.join(site,'target-study.json'),'utf8'));
 async function saved(selector){const event=page.waitForEvent('download');await page.locator(selector).click();const d=await event;assert.equal(await d.failure(),null);return fs.readFile(await d.path());}
 await check('four new sources download unchanged and all have actual playback',async()=>{for(const c of study.cases){await page.locator('#candidate-select').selectOption(c.id);await page.waitForFunction(title=>document.querySelector('#candidate-description').textContent===title&&document.querySelector('#candidate-audio').readyState>=2,c.limits); // limits are shared; wait below on exact WAV hash
 await page.waitForFunction(async expected=>{const u=document.querySelector('#candidate-audio').src;const b=await(await fetch(u)).arrayBuffer();const h=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',b)),v=>v.toString(16).padStart(2,'0')).join('');return h===expected;},c.audio.sha256);
 assert.equal(hash(await saved('#download-candidate')),c.audio.sha256);await page.locator('#candidate-audio').evaluate(a=>a.play());await page.waitForFunction(()=>document.querySelector('#candidate-audio').currentTime>.1);await page.locator('#candidate-audio').evaluate(a=>a.pause());}});
 const reference=Buffer.from(study.cases[0].audio.base64,'base64');
 await check('local synthetic reference imports without any upload or channel remix',async()=>{await page.locator('#target-file').setInputFiles({name:'synthetic-test-reference.wav',mimeType:'audio/wav',buffer:reference});await page.waitForFunction(()=>document.querySelector('#reference-audio').readyState>=2&&document.querySelector('#reference-info').textContent.includes('Custom local excerpt'));assert.match(await page.locator('#reference-info').textContent(),/Custom local excerpt/);assert.equal(uploads,0);const ears=await page.locator('#reference-audio').evaluate(async a=>{const b=await(await fetch(a.src)).arrayBuffer();const w=await new OfflineAudioContext(2,1,48000).decodeAudioData(b);const rms=[0,1].map(i=>{const x=w.getChannelData(i);let e=0;for(const v of x)e+=v*v;return Math.sqrt(e/x.length);});return {rate:w.sampleRate,rms,duration:w.duration};});assert.equal(ears.rate,48000);assert.equal(ears.duration,4);assert.ok(ears.rms[0]>ears.rms[1]*5);});
 await check('local judgment begins empty and retains exact identities, not a pass claim',async()=>{for(const key of ['transient','wet','spatial'])assert.equal(await page.locator('#rating-'+key).inputValue(),'');const j=JSON.parse((await saved('#save-review')).toString());assert.equal(j.ratings.wet_texture,null);assert.equal(j.reference.source_sha256,hash(reference));assert.equal(j.physical_calibration_claim,false);await page.locator('#rating-wet').selectOption('Missing / mismatch');const rated=JSON.parse((await saved('#save-review')).toString());assert.equal(rated.ratings.wet_texture,'Missing / mismatch');});
 await check('reference and candidate do not play together',async()=>{await page.locator('#candidate-audio').evaluate(a=>a.play());await page.locator('#reference-audio').evaluate(a=>a.play());await page.waitForFunction(()=>document.querySelector('#candidate-audio').paused&&!document.querySelector('#reference-audio').paused);await page.locator('#reference-audio').evaluate(a=>a.pause());});
 await check('invalid local input is rejected rather than uploaded',async()=>{await page.locator('#target-file').setInputFiles({name:'bad.wav',mimeType:'audio/wav',buffer:Buffer.from('not a WAV')});await page.waitForFunction(()=>!document.querySelector('#target-error').hidden);assert.equal(uploads,0);});
 await check('rejected baseline and twelve research statuses remain explicit',async()=>{await page.locator('#candidate-select').selectOption('plate-baseline');await page.waitForFunction(()=>document.querySelector('#candidate-description').textContent.includes('user rejected'));assert.equal(await page.locator('.trigger-card').count(),12);assert.match(await page.locator('.hero').textContent(),/Full target: not met/);});
 await check('desktop and mobile comparison have no horizontal overflow',async()=>{for(const w of [1440,390]){await page.setViewportSize({width:w,height:w===390?844:1000});await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth+1);await page.screenshot({path:path.join(out,w===390?'mobile.png':'desktop.png'),fullPage:true});}});
 assert.deepEqual(report.errors,[]);report.passed=true;
}catch(e){report.error=String(e.stack||e);process.exitCode=1;console.error(report.error);}
finally{await fs.writeFile(path.join(out,'target-browser.json'),JSON.stringify(report,null,2)+'\n');if(context)await context.close();if(browser)await browser.close();if(api)await api.dispose();if(server)await new Promise(r=>server.close(r));console.log(JSON.stringify({passed:report.passed,checks:report.checks.length}));}
