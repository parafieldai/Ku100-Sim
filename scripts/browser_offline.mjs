#!/usr/bin/env node
/** Actual offline playback/export validation for the single-file main viewer. */
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const folder=path.resolve(process.argv[2]||path.join(root,'outputs/review'));
const source=process.env.KU100_PLAYWRIGHT_MODULE||path.join(root,'web/node_modules/playwright/index.mjs');
const {chromium}=await import(pathToFileURL(source).href);
const hash=x=>createHash('sha256').update(x).digest('hex');
const evidence=JSON.parse(await fs.readFile(path.join(folder,'example-evidence.json'),'utf8'));
assert.equal(evidence.length,7);
const output=path.join(root,'validation/local/offline-browser');await fs.mkdir(output,{recursive:true});
const failures=[],checks=[];
const browser=await chromium.launch({headless:true,args:['--no-sandbox','--mute-audio'],...(process.env.KU100_CHROMIUM_EXECUTABLE?{executablePath:process.env.KU100_CHROMIUM_EXECUTABLE}:{})});
try {
 const context=await browser.newContext({viewport:{width:1440,height:1100},acceptDownloads:true});const page=await context.newPage();
 page.on('pageerror',e=>failures.push(String(e)));
 page.on('request',r=>{if(!/^(file:|data:|blob:)/.test(r.url()))failures.push('External request: '+r.url());});
 await page.goto(pathToFileURL(path.join(folder,'Ku100-Research-Preview.html')).href,{waitUntil:'load'});
 for(const row of evidence){
  if(row!==evidence[0])await page.locator('#example-select').selectOption(row.id);
  await page.waitForFunction(name=>document.querySelector('#playback-name').textContent===name&&document.querySelector('#audio').readyState>=2,row.scene.name);
  const pending=page.waitForEvent('download');await page.locator('#download-wav').click();const download=await pending;
  assert.equal(hash(await fs.readFile(await download.path())),row.audio_sha256);
 }
 checks.push('All seven native WAVs load offline and download byte-identically');
 await page.locator('#play-button').click();await page.waitForFunction(()=>document.querySelector('#audio').currentTime>.12);await page.locator('#play-button').click();
 checks.push('Real audio playback time advances and pauses');
 assert.match(await page.locator('#bandwidth-note').textContent(),/3500|3.5.*03/);
 assert.match(await page.locator('#bandwidth-note').textContent(),/memory enabled/);checks.push('Fine-texture source bandwidth and viscous model are visible');
 const src=await page.locator('#audio').getAttribute('src');await page.locator('#scene-side').selectOption('right');
 assert.equal(await page.locator('#audio').getAttribute('src'),src);assert.match(await page.locator('#edit-status').textContent(),/re-render required/);checks.push('Editing a scene does not silently substitute audio');
 await page.screenshot({path:path.join(output,'desktop.png'),fullPage:true});await page.setViewportSize({width:390,height:844});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true);checks.push('Mobile layout fits the viewport');
 await page.screenshot({path:path.join(output,'mobile.png'),fullPage:true});
 assert.deepEqual(failures,[]);checks.push('No uncaught browser errors or external network requests');
 await fs.writeFile(path.join(output,'report.json'),JSON.stringify({passed:true,browser:browser.version(),checks,human_listening_assessment:false},null,2));
 console.log(JSON.stringify({passed:true,checks}));
} finally {await browser.close();}
