#!/usr/bin/env node
// Same test against a local server or the published HTTPS subpath.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const site=path.resolve(process.env.KU100_SITE_DIR||path.join(root,'dist'));
const out=path.resolve(process.env.KU100_UNIFIED_REPORT_DIR||path.join(root,'validation/local/unified-browser'));
const {chromium,request}=await import(pathToFileURL(process.env.KU100_PLAYWRIGHT_MODULE||path.join(root,'web/node_modules/playwright/index.mjs')).href);
const sha=b=>createHash('sha256').update(b).digest('hex');
const result={passed:false,assets:[],samples:[],errors:[],source_recordings_included:false,human_listening_assessed:false};
await fs.mkdir(out,{recursive:true});let server,browser,api,base=process.env.KU100_UNIFIED_URL;
try{
 const m=JSON.parse(await fs.readFile(path.join(site,'unified/generated/manifest.json'),'utf8'));
 if(!base){server=http.createServer(async(req,res)=>{try{
  let name=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  // Exercise the actual GitHub-project-style prefix locally too.
  if(!name.startsWith('/Ku100-Sim/'))throw Error('Bad prefix');name=name.slice('/Ku100-Sim'.length);
  const p=path.resolve(site,'.'+(name.endsWith('/')?name+'index.html':name));if(!p.startsWith(site+path.sep))throw Error('Bad path');
  const bytes=await fs.readFile(p);res.writeHead(200,{'Content-Type':{'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json','.wav':'audio/wav'}[path.extname(p)]||'application/octet-stream'});res.end(bytes);
 }catch{res.writeHead(404);res.end('Not found');}});await new Promise(r=>server.listen(0,'127.0.0.1',r));base=`http://127.0.0.1:${server.address().port}/Ku100-Sim/unified/`;}
 result.url=base;api=await request.newContext({ignoreHTTPSErrors:false,timeout:30000});
 const names=['index.html','app.js','style.css','generated/manifest.json',...m.samples.flatMap(x=>[x.audio,x.scene,x.trace].map(y=>'generated/'+y))];
 for(const name of names){const expected=sha(await fs.readFile(path.resolve(site,'unified',name)));let record;
  for(let j=0;j<5;j++){const r=await api.get(new URL(name,base).href,{headers:{'Cache-Control':'no-cache'}});record={path:name,status:r.status(),sha256:sha(await r.body()),expected};if(record.status===200&&record.sha256===expected)break;await new Promise(r=>setTimeout(r,5000));}
  result.assets.push(record);assert.equal(record.status,200);assert.equal(record.sha256,expected);
 }
 browser=await chromium.launch({headless:true,args:['--mute-audio'],...(process.env.KU100_BROWSER_EXECUTABLE?{executablePath:process.env.KU100_BROWSER_EXECUTABLE}:{})});result.browser=browser.version();
 const context=await browser.newContext({acceptDownloads:true,viewport:{width:1380,height:1100}}),page=await context.newPage();
 page.on('pageerror',e=>result.errors.push(String(e)));page.on('request',r=>{if(/^https?:/.test(r.url())&&(r.method()!=='GET'||new URL(r.url()).origin!==new URL(base).origin))result.errors.push('Unexpected request '+r.url());});
 assert.equal((await page.goto(base,{waitUntil:'networkidle'})).status(),200);
 for(const item of m.samples){await page.selectOption('#scene',item.id);await page.waitForFunction(name=>document.querySelector('#name').textContent===name&&!document.querySelector('#play').disabled,item.name);
  const decoded=await page.locator('#audio').evaluate(async a=>{const raw=await(await fetch(a.src)).arrayBuffer();const {parseWave}=await import('../target/core.js');const p=parseWave(new Uint8Array(raw));const b=await new OfflineAudioContext(2,1,p.sampleRate).decodeAudioData(raw.slice(0));let error=0,difference=0;for(let i=0;i<b.length;i++)difference=Math.max(difference,Math.abs(b.getChannelData(0)[i]-b.getChannelData(1)[i]));for(let c=0;c<2;c++)for(let i=0;i<b.length;i++)error=Math.max(error,Math.abs(b.getChannelData(c)[i]-p.samples[c][i]));return {rate:b.sampleRate,channels:b.numberOfChannels,frames:b.length,max_error:error,difference};});
  const {difference,...format}=decoded;assert.ok(difference>1e-10);assert.deepEqual(format,{rate:48000,channels:2,frames:Math.round(item.seconds*48000),max_error:0});
  await page.click('#play');await page.waitForFunction(()=>document.querySelector('#audio').currentTime>.15&&!document.querySelector('#audio').paused);
  await page.locator('#audio').evaluate(a=>{a.pause();a.currentTime=2.5;});await page.waitForFunction(()=>{const a=document.querySelector('#audio');return !a.seeking&&Math.abs(a.currentTime-2.5)<.005;});
  const down=page.waitForEvent('download');await page.click('#download');const d=await down;assert.equal(await d.failure(),null);assert.equal(sha(await fs.readFile(await d.path())),item.files_sha256[item.audio]);
  result.samples.push({id:item.id,...decoded,played:true,seeked:true,download_unchanged:true});
 }
 const before=await page.locator('#audio').getAttribute('src');await page.fill('#stiffness','1.2');await page.fill('#damping','2');
 const down=page.waitForEvent('download');await page.click('#export');const d=await down;const edited=JSON.parse(await fs.readFile(await d.path(),'utf8'));
 const last=m.samples.at(-1),original=JSON.parse(await fs.readFile(path.join(site,'unified/generated',last.scene),'utf8'));
 assert.equal(edited.nodes[0].k2_n_m,1.2*original.nodes[0].k2_n_m);assert.equal(edited.nodes[0].damping_n_s_m,2*original.nodes[0].damping_n_s_m);
 assert.equal(edited.microphone.model,'KU100_NF');assert.deepEqual(edited.microphone,original.microphone);
 assert.equal(await page.locator('#audio').getAttribute('src'),before);assert.match(await page.locator('#edit-status').textContent(),/Playback above is unchanged/);result.edited_scene_export_and_no_fake_rerender=true;
 await page.selectOption('#scene','plastic-snap');await page.waitForFunction(()=>document.querySelector('#name').textContent.startsWith('Plastic-like'));await page.locator('#audio').evaluate(a=>{a.currentTime=.8;});await page.waitForTimeout(100);
 for(const width of [1380,390]){await page.setViewportSize({width,height:width===390?844:1100});await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth+1);await page.screenshot({path:path.join(out,width===390?'mobile.png':'desktop.png'),fullPage:true});}
 assert.deepEqual(result.errors,[]);result.passed=true;await context.close();
}catch(e){result.error=String(e.stack||e);console.error(result.error);process.exitCode=1;}
finally{await fs.writeFile(path.join(out,'unified-browser.json'),JSON.stringify(result,null,2)+'\n');if(browser)await browser.close();if(api)await api.dispose();if(server)await new Promise(r=>server.close(r));console.log(JSON.stringify({passed:result.passed,url:base,samples:result.samples.length}));}
