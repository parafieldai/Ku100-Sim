#!/usr/bin/env node
/** Exercise the built viewer with real native exports, including actual playback. */
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {createServer} from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const site = path.join(root, 'dist');
const out = path.join(root, 'validation', 'local', 'browser');
const modulePath = process.env.KU100_PLAYWRIGHT_MODULE || path.join(root, 'web', 'node_modules', 'playwright', 'index.mjs');
const {chromium} = await import(pathToFileURL(modulePath).href);
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const manifest = JSON.parse(await fs.readFile(path.join(site, 'examples', 'index.json'), 'utf8'));
assert.equal(manifest.examples.length, 5, 'The five native demonstration cases must be built first');
await fs.mkdir(out, {recursive: true});
const mime = {'.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json'};
const server = createServer(async (req, res) => {
  try {
    const requested = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    if (requested.endsWith('/favicon.ico')) { res.writeHead(204); res.end(); return; }
    // Also serve at a project subpath, matching GitHub project-site routing.
    const relative = requested.startsWith('/Ku100-Sim/') ? requested.slice('/Ku100-Sim'.length) : requested;
    const target = path.resolve(site, '.' + (relative.endsWith('/') ? relative + 'index.html' : relative));
    if (!target.startsWith(site + path.sep)) throw new Error('Invalid path');
    const content = await fs.readFile(target);
    res.writeHead(200, {'Content-Type': mime[path.extname(target)] || 'application/octet-stream', 'Content-Length': content.length});
    res.end(content);
  } catch { res.writeHead(404); res.end('Not found'); }
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const base = `http://127.0.0.1:${server.address().port}`;
let browser;
const checks = [];
const failures = [];
async function check(name, action) { await action(); checks.push(name); console.log(`PASS ${name}`); }
try {
  browser = await chromium.launch({headless: true, args: ['--no-sandbox', '--mute-audio'],
    ...(process.env.KU100_CHROMIUM_EXECUTABLE ? {executablePath: process.env.KU100_CHROMIUM_EXECUTABLE} : {})});
  const context = await browser.newContext({viewport: {width: 1440, height: 1100}, acceptDownloads: true});
  const page = await context.newPage();
  page.on('pageerror', error => failures.push(String(error)));
  page.on('request', request => { if (!request.url().startsWith(base) && !request.url().startsWith('blob:') && !request.url().startsWith('data:')) failures.push(`Unexpected external request: ${request.url()}`); });
  await page.goto(base, {waitUntil: 'networkidle'});
  const first = JSON.parse(await fs.readFile(path.join(site, 'examples', manifest.examples[0].path), 'utf8'));
  async function awaitName(name) {
    await page.waitForFunction(name => document.querySelector('#playback-name').textContent === name && document.querySelector('#audio').readyState >= 2, name);
  }
  await check('initial real native bundle, browser decoding and exact stereo samples', async () => {
    await awaitName(first.scene.name);
    const result = await page.evaluate(async () => {
      const array = await (await fetch(document.querySelector('#audio').src)).arrayBuffer();
      const {parseWave} = await import('./core.js');
      const parsed = parseWave(new Uint8Array(array));
      const ctx = new OfflineAudioContext(2, 1, parsed.sampleRate);
      const decoded = await ctx.decodeAudioData(array.slice(0));
      let error = 0;
      for (let ear = 0; ear < 2; ear++) {
        const values = decoded.getChannelData(ear);
        for (let i = 0; i < values.length; i++) error = Math.max(error, Math.abs(values[i] - parsed.samples[ear][i]));
      }
      return {frames: decoded.length, channels: decoded.numberOfChannels, rate: decoded.sampleRate, maximumSampleError: error};
    });
    assert.deepEqual(result, {frames: first.metrics.frames, channels: 2, rate: 48000, maximumSampleError: 0});
  });
  await check('actual audio playback advances and pauses', async () => {
    await page.locator('#play-button').click();
    await page.waitForFunction(() => document.querySelector('#audio').currentTime > 0.15 && !document.querySelector('#audio').paused);
    await page.locator('#play-button').click();
    assert.equal(await page.locator('#audio').evaluate(audio => audio.paused), true);
  });
  await check('seek, trace, common playback attenuation and geometry controls', async () => {
    await page.locator('#seek').evaluate(input => { input.value = '1.25'; input.dispatchEvent(new Event('input', {bubbles: true})); });
    await page.waitForFunction(() => Math.abs(document.querySelector('#audio').currentTime - 1.25) < 0.002);
    assert.notEqual(await page.locator('#metric-force').textContent(), '—');
    await page.locator('#volume').evaluate(input => { input.value = '-18'; input.dispatchEvent(new Event('input', {bubbles: true})); });
    assert.ok(Math.abs(await page.locator('#audio').evaluate(audio => audio.volume) - 10 ** (-18 / 20)) < 1e-12);
    await page.locator('#view-detail').click();
    assert.equal(await page.locator('#view-detail').getAttribute('aria-pressed'), 'true');
    await page.locator('#view-full').click();
    const box = await page.locator('#geometry-canvas').boundingBox();
    await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.5);
    await page.mouse.down(); await page.mouse.move(box.x + box.width * 0.6, box.y + box.height * 0.55, {steps: 5}); await page.mouse.up();
    await page.locator('#reset-view').click();
  });
  async function download(selector) {
    const event = page.waitForEvent('download');
    await page.locator(selector).click();
    return fs.readFile(await (await event).path());
  }
  await check('WAV download preserves original file bytes and stereo gain', async () => {
    assert.equal(hash(await download('#download-wav')), first.audio.sha256);
  });
  await check('scene edit/export retains loaded audio until a native rerender', async () => {
    const oldSource = await page.locator('#audio').getAttribute('src');
    await page.locator('#scene-side').selectOption('right');
    assert.match(await page.locator('#edit-status').textContent(), /re-render required/);
    assert.equal(await page.locator('#audio').getAttribute('src'), oldSource);
    const scene = JSON.parse((await download('#download-scene')).toString());
    assert.equal(scene.side, 'right');
    assert.equal(scene.physics.load_n, first.scene.physics.load_n);
    assert.equal(hash(await download('#download-wav')), first.audio.sha256);
    await page.locator('#reset-scene').click();
    assert.equal(await page.locator('#scene-side').inputValue(), 'left');
  });
  await check('all five real native examples decode and retain file identity', async () => {
    for (const entry of manifest.examples) {
      const bundle = JSON.parse(await fs.readFile(path.join(site, 'examples', entry.path), 'utf8'));
      await page.locator('#example-select').selectOption(entry.id);
      await awaitName(bundle.scene.name);
      assert.equal(hash(await download('#download-wav')), bundle.audio.sha256);
      assert.equal(await page.locator('#regime-warning').isVisible(), bundle.metrics.physics.regime_valid === false);
    }
  });
  await check('local import, invalid-regime display and corrupted-audio rejection', async () => {
    const imported = structuredClone(first);
    imported.scene.name = 'E2E local import';
    imported.metrics.physics.regime_valid = false;
    imported.metrics.physics.regime_warnings = ['Deliberately invalid test regime'];
    await page.locator('#bundle-file').setInputFiles({name: 'local.ku100.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(imported))});
    await awaitName(imported.scene.name);
    assert.equal(await page.locator('#regime-warning').isVisible(), true);
    assert.match(await page.locator('#regime-warning-text').textContent(), /Deliberately invalid/);
    const originalSource = await page.locator('#audio').getAttribute('src');
    const damaged = structuredClone(first);
    damaged.audio.sha256 = '0'.repeat(64);
    await page.locator('#bundle-file').setInputFiles({name: 'damaged.ku100.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(damaged))});
    await page.waitForFunction(() => document.querySelector('#message').classList.contains('error'));
    assert.match(await page.locator('#message').textContent(), /SHA-256|hash|checksum/i);
    assert.equal(await page.locator('#audio').getAttribute('src'), originalSource);
  });
  await page.locator('#example-select').selectOption(manifest.examples[0].id);
  await awaitName(first.scene.name);
  await page.locator('#seek').evaluate(input => { input.value = '0.75'; input.dispatchEvent(new Event('input', {bubbles: true})); });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({path: path.join(out, 'desktop.png'), fullPage: true});
  await check('desktop and mobile layouts have no horizontal overflow', async () => {
    for (const width of [1440, 390]) {
      await page.setViewportSize({width, height: width === 390 ? 844 : 1100});
      await page.waitForFunction(() => document.documentElement.scrollWidth <= innerWidth + 1);
    }
    await page.screenshot({path: path.join(out, 'mobile.png'), fullPage: true});
    await page.screenshot({path: path.join(out, 'mobile-viewport.png'), fullPage: false});
  });
  await check('project subpath resolves all assets and playback data', async () => {
    await page.goto(base + '/Ku100-Sim/', {waitUntil: 'networkidle'});
    await awaitName(first.scene.name);
    assert.equal(await page.locator('#play-button').isEnabled(), true);
  });
  assert.deepEqual(failures, [], 'No browser errors or external requests');
  const report = {version: 1, browser: browser.version(), checks, checks_passed: checks.length,
                  browser_errors: failures, examples: manifest.examples.map(example => example.id),
                  human_listening_performed: false,
                  note: 'Playback and decoded samples were verified by automation; this is not a human listening or perceptual fidelity assessment.'};
  await fs.writeFile(path.join(out, 'e2e.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report));
} finally {
  if (browser) await browser.close();
  await new Promise(resolve => server.close(resolve));
}
