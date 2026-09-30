#!/usr/bin/env node
/** Post-deployment target-page verification. No reference recording or credentials sent to Pages. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const {chromium,request}=await import(pathToFileURL(path.join(root,'web/node_modules/playwright/index.mjs')).href);
const site=path.resolve(process.env.KU100_SITE_DIR||'verified/dist');
const base='https://parafieldai.github.io/Ku100-Sim/';
const out=path.resolve(process.env.KU100_SAVED_LISTENING_REPORT_DIR||'validation/local/live-pages/saved-listening');await fs.mkdir(out,{recursive:true});
const hash=x=>createHash('sha256').update(x).digest('hex');
const study=JSON.parse(await fs.readFile(path.join(site,'target/generated/study.json'),'utf8'));
assert.equal(study.reference_audio_public,false);assert.equal(study.physical_target_implemented,false);assert.equal(study.candidates.length,6);
const report={schema:'target-live/1',passed:false,url:base+'target/',source_commit:process.env.KU100_EXPECTED_SHA||null,checks:[],assets:[],human_listening_performed:false,private_references_tested:false,browser_errors:[]};
let browser,api;
try{
 api=await request.newContext({ignoreHTTPSErrors:false,timeout:30000});
 const names=['core.js','target/index.html','target/style.css','target/core.js','target/app.js','target/generated/study.json',...study.candidates.map(c=>{assert.match(c.file,/^[a-z][a-z0-9-]+\.wav$/);return 'target/generated/'+c.file;})];
 for(const name of names){
  const expected=hash(await fs.readFile(path.join(site,name)));let row;
  for(let retry=0;retry<5;retry++){
   const r=await api.get(new URL(name,base).href,{headers:{'Cache-Control':'no-cache'}});
   row={path:name,status:r.status(),url:r.url(),sha256:hash(await r.body()),expected_sha256:expected};
   if(row.status===200&&row.sha256===expected)break;if(retry<4)await new Promise(resolve=>setTimeout(resolve,7000));
  }
  report.assets.push(row);assert.equal(row.status,200,name);assert.equal(row.sha256,expected,name);assert.equal(new URL(row.url).origin,new URL(base).origin);
 }
 report.checks.push('Anonymous HTTPS target assets match the exact successful CI artifact');
 browser=await chromium.launch({headless:true,args:['--mute-audio']});report.browser=browser.version();
 const context=await browser.newContext({viewport:{width:1380,height:1000},acceptDownloads:true});const page=await context.newPage();
 page.on('pageerror',e=>report.browser_errors.push(String(e)));
 await page.goto(base+'target/',{waitUntil:'networkidle'});await page.waitForFunction(()=>document.querySelector('#candidate-audio').readyState>=2);
 assert.equal(await page.locator('#play-reference').isDisabled(),true);assert.equal(await page.locator('#save-rating').isDisabled(),true);assert.match(await page.locator('.notice').textContent(),/not passed/);
 report.checks.push('Public site contains no embedded private reference and makes no target-acceptance claim');
 const seen=new Set();
 for(const ref of [study.references[0],study.references[2]]){
  await page.locator('#reference-select').selectOption(ref.id);
  const count=await page.locator('#candidate-select option').count();
  for(let i=0;i<count;i++){
   await page.locator('#candidate-select').selectOption(String(i));await page.waitForFunction(()=>document.querySelector('#candidate-audio').readyState>=2);
   const event=page.waitForEvent('download');await page.locator('#download-candidate').click();const d=await event;assert.equal(await d.failure(),null);
   const c=study.candidates.find(c=>c.file===d.suggestedFilename());assert.ok(c);assert.equal(hash(await fs.readFile(await d.path())),c.sha256);seen.add(c.id);
   await page.locator('#play-candidate').click();await page.waitForFunction(()=>document.querySelector('#candidate-audio').currentTime>.15&&!document.querySelector('#candidate-audio').paused);await page.locator('#stop').click();
  }
 }
 assert.equal(seen.size,6);report.checks.push('All six generated examples play and download with exact original WAV identity');
 for(const width of [1380,390]){await page.setViewportSize({width,height:width===390?844:1000});await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth+1);await page.screenshot({path:path.join(out,width===390?'mobile.png':'desktop.png'),fullPage:true});}
 report.checks.push('Desktop and mobile layout fit');assert.deepEqual(report.browser_errors,[]);report.passed=true;await context.close();
}catch(e){report.error=String(e.stack||e);console.error(report.error);process.exitCode=1;}
finally{if(browser)await browser.close();if(api)await api.dispose();await fs.writeFile(path.join(out,'target-live.json'),JSON.stringify(report,null,2)+'\n');}
