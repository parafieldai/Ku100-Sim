#!/usr/bin/env node
/** Local HTTP tests use a SYNTHETIC import fixture; --private tests actual user crops. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import os from 'node:os';
import {createHash} from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const memory=process.argv.includes('--memory');
const at=process.argv.indexOf('--private');const privateFile=at>=0?path.resolve(process.argv[at+1]):null;
const mod=process.env.KU100_PLAYWRIGHT_MODULE||path.join(root,'web/node_modules/playwright/index.mjs');
const {chromium}=await import(pathToFileURL(mod).href);
const out=path.resolve(process.env.KU100_TARGET_REPORT_DIR||path.join(root,'validation/local/saved-listening-browser'));
await fs.mkdir(out,{recursive:true});
const hash=x=>createHash('sha256').update(x).digest('hex');
const report={schema:'target-browser/1',passed:false,checks:[],actual_user_reference_crops:!!privateFile,
  reference_import_fixture:privateFile?'actual supplied crops embedded privately':'synthetic generated stereo, NOT a physical/realism validation',
  execution_mode:memory?'self-authored HTML in memory; file/HTTP navigation not tested':'normal browser navigation',human_listening_performed:false,errors:[],external_requests:[]};
let browser,server,temp;
try{
  const site=path.join(root,'dist');const study=JSON.parse(await fs.readFile(path.join(site,'target/generated/study.json'),'utf8'));
  let base;
  if(!privateFile){
    server=http.createServer(async(req,res)=>{
      try{
        const pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);if(pathname.includes('..'))throw Error('Path traversal');
        const rel=pathname.endsWith('/')?pathname+'index.html':pathname;
        const p=path.resolve(site,'.'+rel);if(!p.startsWith(site+path.sep))throw Error('Bad path');
        const body=await fs.readFile(p);const mime={'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json','.wav':'audio/wav'}[path.extname(p)]||'application/octet-stream';res.writeHead(200,{'Content-Type':mime});res.end(body);
      }catch(e){res.writeHead(404);res.end('not found');}
    });await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));base=`http://127.0.0.1:${server.address().port}/target/`;
  }else base=pathToFileURL(privateFile).href;
  browser=await chromium.launch({headless:true,...(process.env.KU100_BROWSER_EXECUTABLE?{executablePath:process.env.KU100_BROWSER_EXECUTABLE}:{}),args:['--mute-audio']});
  report.browser=browser.version();const context=await browser.newContext({viewport:{width:1380,height:1000},acceptDownloads:true});const page=await context.newPage();
  page.on('pageerror',e=>report.errors.push(String(e)));
  page.on('request',r=>{if(/^https?:/.test(r.url())&&(privateFile||!r.url().startsWith(base.split('/target/')[0])))report.external_requests.push(r.url());});
  let imported;
  if(!privateFile){
    const fixture=await fs.readFile(path.join(site,'target/generated/burst-right-a.wav'));
    const altered=structuredClone(study);const r=altered.references[0];r.sha256=hash(fixture);r.source_rate_hz=48000;r.source_frames=288000;r.crop_frames=[0,288000];r.crop_s=[0,6];r.crop_pcm_f32_sha256=hash(fixture.subarray(44));r.title='SYNTHETIC import test fixture';
    await page.route('**/target/generated/study.json',route=>route.fulfill({contentType:'application/json',body:JSON.stringify(altered)}));
    temp=await fs.mkdtemp(path.join(os.tmpdir(),'target-browser-'));imported=path.join(temp,'synthetic-reference.wav');await fs.writeFile(imported,fixture);
  }
  if(memory){if(!privateFile)throw Error('--memory only tests the self-contained local document');await page.setContent(await fs.readFile(privateFile,'utf8'),{waitUntil:'load'});}else await page.goto(base,{waitUntil:'networkidle'});await page.waitForFunction(()=>document.querySelector('#candidate-audio').readyState>=2);
  assert.match(await page.locator('.notice').textContent(),/not passed/);
  assert.equal(await page.locator('#identity').isVisible(),false);
  assert.match(await page.locator('#candidate-select option').first().textContent(),/Empirical/);
  report.checks.push('Honest failure label; stable named auditions are the default');
  await page.locator('#blind-mode').check();
  await page.waitForFunction(()=>document.querySelector('#candidate-select option').textContent==='Candidate A'&&document.querySelector('#candidate-audio').readyState>=2);
  if(!privateFile){
    assert.equal(await page.locator('#play-reference').isDisabled(),true);
    const wrong=path.join(temp,'wrong.wav');await fs.writeFile(wrong,Buffer.from('wrong file'));
    await page.locator('#reference-files').setInputFiles(wrong);await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('not one of the exact'));
    await page.locator('#reference-files').setInputFiles(imported);await page.waitForFunction(()=>document.querySelector('#reference-audio').readyState>=2);
    report.checks.push('Wrong reference file rejected; synthetic reference hash and exact crop accepted locally');
  }else{
    await page.waitForFunction(()=>document.querySelector('#reference-audio').readyState>=2);report.checks.push('Actual supplied reference crops load with original stereo sample hashes');
  }
  assert.equal(await page.locator('#save-rating').isDisabled(),true);
  // A paused seek is not evidence that audio playback occurred.
  for(const which of ['reference','candidate']){
    await page.locator('#'+which+'-audio').evaluate(a=>{a.currentTime=.3;a.dispatchEvent(new Event('timeupdate'));});
  }
  assert.equal(await page.locator('#save-rating').isDisabled(),true);
  report.checks.push('Paused seeking does not qualify as playback for listener feedback');
  for(const which of ['reference','candidate']){
    await page.locator('#play-'+which).click();await page.waitForFunction(which=>{const a=document.querySelector('#'+which+'-audio');return a.currentTime>.2&&!a.paused;},which);
    await page.locator('#stop').click();assert.equal(await page.locator('#'+which+'-audio').evaluate(a=>a.paused),true);
  }
  report.checks.push('Actual reference/candidate playback progresses; both must play before a rating');
  await page.locator('input[name=rating][value="2"]').check();await page.locator('#notes').fill('<script>window.fake=true</script> test observation');
  await page.locator('#save-rating').click();assert.match(await page.locator('#feedback-status').textContent(),/1 observation/);
  const get=async selector=>{const e=page.waitForEvent('download');await page.locator(selector).click();const d=await e;assert.equal(await d.failure(),null);return {bytes:await fs.readFile(await d.path()),name:d.suggestedFilename()};};
  const feedback=JSON.parse((await get('#download-feedback')).bytes.toString());assert.equal(feedback.observations[0].rating_1_to_5,2);assert.equal(feedback.observations[0].identity_hidden_at_rating,true);assert.equal(await page.evaluate(()=>window.fake),undefined);
  report.checks.push('No prefilled results; actual submitted observation exports locally without executing notes');
  const raw=await get('#download-candidate');assert.equal(hash(raw.bytes),study.candidates.find(c=>c.file===raw.name).sha256);
  await page.locator('#level-condition').selectOption('original');await page.waitForFunction(()=>document.querySelector('#candidate-audio').readyState>=2);assert.equal(hash((await get('#download-candidate')).bytes),hash(raw.bytes));
  report.checks.push('Listening gain does not change original WAV download bytes');
  await page.locator('#reveal').click();assert.equal(await page.locator('#identity').isVisible(),true);assert.match(await page.locator('#identity').textContent(),/target_accepted/);
  report.checks.push('Method reveal exposes separate spectrum/stereo discrepancies, never a realism percentage');
  if(privateFile){
    for(const ref of study.references){
      await page.locator('#reference-select').selectOption(ref.id);await page.waitForFunction(()=>document.querySelector('#reference-audio').readyState>=2);
      const crop=(await get('#download-ref')).bytes;assert.equal(hash(crop.subarray(44)),ref.crop_pcm_f32_sha256);
    }
    report.checks.push('All four original reference crop downloads preserve exact stereo samples');
  }
  const seen=new Set();
  for(const ref of [study.references[0],study.references[2]]){
    await page.locator('#reference-select').selectOption(ref.id);
    const count=await page.locator('#candidate-select option').count();
    for(let i=0;i<count;i++){
      await page.locator('#candidate-select').selectOption(String(i));
      await page.waitForFunction(()=>document.querySelector('#candidate-audio').readyState>=2);
      const d=await get('#download-candidate'),c=study.candidates.find(c=>c.file===d.name);
      assert.ok(c);assert.equal(hash(d.bytes),c.sha256);seen.add(c.id);
      await page.locator('#play-candidate').click();await page.waitForFunction(()=>document.querySelector('#candidate-audio').currentTime>.12&&!document.querySelector('#candidate-audio').paused);await page.locator('#stop').click();
    }
  }
  assert.equal(seen.size,6);report.generated_candidate_ids=[...seen].sort();report.checks.push('All six generated candidates play and download with their original SHA-256 identities');
  await page.locator('#trigger-filter').selectOption('Primary target');assert.equal(await page.locator('.trigger').count(),4);
  await page.locator('#trigger-filter').selectOption('all');assert.equal(await page.locator('.trigger').count(),18);
  report.checks.push('18 research entries distinguish primary target, controls and unimplemented future items');
  for(const width of [1380,390]){
    await page.setViewportSize({width,height:width===390?844:1000});await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth+1);
    await page.screenshot({path:path.join(out,(privateFile?'private-':'public-')+(width===390?'mobile.png':'desktop.png')),fullPage:true});
  }
  report.checks.push('Desktop/mobile layout fits without horizontal overflow');
  assert.deepEqual(report.errors,[]);assert.deepEqual(report.external_requests,[]);report.checks.push('No uncaught browser errors or external/network upload requests');report.passed=true;
  await context.close();
}catch(e){report.error=String(e.stack||e);console.error(report.error);process.exitCode=1;}
finally{
 if(browser)await browser.close();if(server)await new Promise(resolve=>server.close(resolve));if(temp)await fs.rm(temp,{recursive:true,force:true});
 const file=path.join(out,privateFile?'private-reference-check.json':'public-target-check.json');await fs.writeFile(file,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({passed:report.passed,checks:report.checks.length,report:file}));
}
