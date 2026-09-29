#!/usr/bin/env node
/** Verify the anonymous HTTPS deployment against the exact successful CI artifact. */
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const site = path.resolve(process.env.KU100_SITE_DIR || path.join(root, 'verified/dist'));
const out = path.resolve(process.env.KU100_LIVE_REPORT_DIR || path.join(root, 'validation/local/live-pages'));
const base = 'https://parafieldai.github.io/Ku100-Sim/';
const {chromium, request} = await import(pathToFileURL(path.join(root, 'web/node_modules/playwright/index.mjs')).href);
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const index = JSON.parse(await fs.readFile(path.join(site, 'examples/index.json'), 'utf8'));
assert.equal(index.examples.length, 7);
await fs.mkdir(out, {recursive: true});
const report = {schema: 'live-pages-check/1', checked_utc: new Date().toISOString(), url: base,
  tested_application_sha: process.env.KU100_EXPECTED_SHA || null, passed: false,
  checks: [], http_assets: [], examples: [], browser_errors: [], request_failures: [],
  anonymous_public_access: true, human_listening_performed: false};
let browser, context, api;
async function check(name, action) { await action(); report.checks.push(name); console.log(`PASS ${name}`); }
try {
  api = await request.newContext({ignoreHTTPSErrors: false, timeout: 30000});
  const names = ['index.html', 'app.js', 'core.js', 'styles.css', 'view3d.js', 'examples/index.json',
    ...index.examples.map(entry => {
      assert.match(entry.path, /^[A-Za-z0-9._-]+$/); return 'examples/' + entry.path;
    })];
  await check('anonymous HTTPS site assets match the successful native CI artifact', async () => {
    for (const name of names) {
      const expected = hash(await fs.readFile(path.join(site, name)));
      let row;
      // Bounded wait for Pages/CDN propagation. A wrong artifact never counts as a pass.
      for (let attempt = 0; attempt < 5; attempt++) {
        const response = await api.get(new URL(name, base).href, {headers: {'Cache-Control': 'no-cache'}});
        row = {path: name, status: response.status(), url: response.url(), sha256: hash(await response.body()), expected_sha256: expected};
        if (row.status === 200 && row.sha256 === expected) break;
        if (attempt < 4) await new Promise(resolve => setTimeout(resolve, 8000));
      }
      report.http_assets.push(row);
      assert.equal(row.status, 200, name); assert.equal(row.sha256, expected, name);
      assert.equal(new URL(row.url).origin, new URL(base).origin, 'No authentication redirect');
    }
  });
  browser = await chromium.launch({headless: true, args: ['--mute-audio']});
  report.browser = browser.version();
  context = await browser.newContext({viewport: {width: 1440, height: 1000}, acceptDownloads: true, ignoreHTTPSErrors: false});
  const page = await context.newPage();
  page.on('pageerror', e => report.browser_errors.push(String(e)));
  page.on('requestfailed', r => { if (!r.url().endsWith('/favicon.ico')) report.request_failures.push({url:r.url(), error:r.failure()?.errorText}); });
  await page.route('**/*', route => {
    const url=route.request().url();
    if (url.startsWith('http') && new URL(url).origin !== new URL(base).origin) {
      report.browser_errors.push('Unexpected external request: '+url); return route.abort();
    }
    return route.continue();
  });
  const navigation = await page.goto(base, {waitUntil: 'networkidle'});
  assert.equal(navigation.status(), 200);
  assert.equal(await page.evaluate(() => isSecureContext), true);
  async function awaitName(name) {
    await page.waitForFunction(name => document.querySelector('#playback-name').textContent === name && document.querySelector('#audio').readyState >= 2, name);
  }
  async function download(selector) {
    const event=page.waitForEvent('download'); await page.locator(selector).click();
    const saved=await event; assert.equal(await saved.failure(), null); return fs.readFile(await saved.path());
  }
  await check('all seven public examples decode, play, pause and download unchanged', async () => {
    for (const entry of index.examples) {
      const bundle=JSON.parse(await fs.readFile(path.join(site,'examples',entry.path),'utf8'));
      await page.locator('#example-select').selectOption(entry.id); await awaitName(bundle.scene.name);
      const decoded=await page.evaluate(async () => {
        const buffer=await (await fetch(document.querySelector('#audio').src)).arrayBuffer();
        const {parseWave}=await import('./core.js'); const parsed=parseWave(new Uint8Array(buffer));
        const decoded=await new OfflineAudioContext(2,1,parsed.sampleRate).decodeAudioData(buffer.slice(0));
        let max=0;
        for (let ear=0;ear<2;ear++) for(let i=0;i<decoded.length;i++) max=Math.max(max,Math.abs(decoded.getChannelData(ear)[i]-parsed.samples[ear][i]));
        return {channels:decoded.numberOfChannels,rate:decoded.sampleRate,frames:decoded.length,maximum_sample_error:max};
      });
      assert.deepEqual(decoded,{channels:2,rate:48000,frames:bundle.metrics.frames,maximum_sample_error:0});
      const original=hash(await download('#download-wav')); assert.equal(original,bundle.audio.sha256);
      await page.locator('#play-button').click();
      await page.waitForFunction(()=>document.querySelector('#audio').currentTime>0.15&&!document.querySelector('#audio').paused);
      await page.locator('#play-button').click(); assert.equal(await page.locator('#audio').evaluate(a=>a.paused),true);
      report.examples.push({id:entry.id,...decoded,wav_sha256:original,playback_passed:true});
    }
  });
  await page.locator('#example-select').selectOption(index.examples[0].id);
  const first=JSON.parse(await fs.readFile(path.join(site,'examples',index.examples[0].path),'utf8'));
  await awaitName(first.scene.name);
  await check('seeking updates telemetry and scene editing leaves loaded sound unchanged',async()=>{
    await page.locator('#seek').evaluate(input=>{input.value='0.75';input.dispatchEvent(new Event('input',{bubbles:true}));});
    await page.waitForFunction(()=>Math.abs(document.querySelector('#audio').currentTime-0.75)<0.002);
    assert.notEqual(await page.locator('#metric-force').textContent(),'—');
    const source=await page.locator('#audio').getAttribute('src');
    await page.locator('#scene-side').selectOption('right');
    assert.match(await page.locator('#edit-status').textContent(),/re-render required/);
    assert.equal(await page.locator('#audio').getAttribute('src'),source);
    assert.equal(JSON.parse((await download('#download-scene')).toString()).side,'right');
    assert.equal(hash(await download('#download-wav')),first.audio.sha256);
    await page.locator('#reset-scene').click();
  });
  await check('desktop and mobile site layouts fit the viewport',async()=>{
    for (const width of [1440,390]) {
      await page.setViewportSize({width,height:width===390?844:1000});
      await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth+1);
      await page.screenshot({path:path.join(out,width===390?'mobile.png':'desktop.png'),fullPage:true});
    }
  });
  assert.deepEqual(report.browser_errors,[]); assert.deepEqual(report.request_failures,[]);
  report.checks.push('no uncaught browser errors or failed application requests');
  report.passed=true;
} catch (e) {report.error=String(e?.stack||e);process.exitCode=1;console.error(report.error);}
finally {
  await fs.writeFile(path.join(out,'live-pages.json'),JSON.stringify(report,null,2)+'\n');
  if(context)await context.close(); if(browser)await browser.close(); if(api)await api.dispose();
  console.log(JSON.stringify({passed:report.passed,checks:report.checks.length,url:base,report:path.join(out,'live-pages.json')}));
}
