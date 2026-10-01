#!/usr/bin/env python3
"""Exercise the actual self-contained preview; never fabricates listening scores."""
import argparse, asyncio, hashlib, json
from pathlib import Path
from playwright.async_api import async_playwright

async def test(html,out,in_memory=False):
    out.mkdir(parents=True,exist_ok=True)
    report={'schema':'fork-radiation-browser/1','passed':False,'url':html.resolve().as_uri(),
            'navigation':'in-memory component check only' if in_memory else 'normal file URL','errors':[],'network_requests':[],'samples':[],'human_listening_performed':False}
    try:
        async with async_playwright() as p:
            browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--mute-audio'])
            report['browser']=browser.version
            ctx=await browser.new_context(viewport={'width':1400,'height':1000},accept_downloads=True)
            page=await ctx.new_page()
            page.on('pageerror',lambda e:report['errors'].append(str(e)))
            page.on('request',lambda r:report['network_requests'].append(r.url) if r.url.startswith(('http://','https://')) else None)
            if in_memory:
                report['url']='about:blank; self-contained app inserted for component testing'
                await page.set_content(html.read_text(),wait_until='load',timeout=45000)
            else:
                await page.goto(html.resolve().as_uri(),wait_until='load',timeout=45000)
            await page.wait_for_function("document.querySelector('#status').textContent.startsWith('All ')",timeout=30000)
            expected=await page.evaluate("JSON.parse(document.querySelector('#payload').textContent).samples.map(s=>({id:s.id,sha256:s.sha256,frames:s.frames}))")
            for row in expected:
                card=page.locator(f'article[data-id="{row["id"]}"]');audio=card.locator('audio')
                values=await audio.evaluate('''async a=>{
                    const b=await (await fetch(a.src)).arrayBuffer();const view=new DataView(b);
                    let pos=12,data;while(pos+8<=b.byteLength){let id=String.fromCharCode(...new Uint8Array(b,pos,4)),len=view.getUint32(pos+4,true);if(id==='data'){data={start:pos+8,len};break}pos+=8+len+(len%2)}
                    const decoded=await new OfflineAudioContext(2,1,48000).decodeAudioData(b.slice(0));let error=0,difference=0;
                    for(let i=0;i<decoded.length;i++){for(let c=0;c<2;c++)error=Math.max(error,Math.abs(decoded.getChannelData(c)[i]-view.getFloat32(data.start+8*i+4*c,true)));difference+=Math.abs(decoded.getChannelData(0)[i]-decoded.getChannelData(1)[i])}
                    return {frames:decoded.length,channels:decoded.numberOfChannels,rate:decoded.sampleRate,sample_error:error,difference};}''')
                assert values['frames']==row['frames'] and values['channels']==2 and values['rate']==48000 and values['sample_error']==0 and values['difference']>0
                await card.locator('button').click()
                await page.wait_for_function("id=>{let a=document.querySelector(`article[data-id=\"${id}\"] audio`);return a.currentTime>.15&&!a.paused}",arg=row['id'])
                assert await page.locator('audio').evaluate_all('(a)=>a.filter(x=>!x.paused).length')==1
                await audio.evaluate('(a)=>{a.pause();a.currentTime=5}')
                await page.wait_for_function("id=>{let a=document.querySelector(`article[data-id=\"${id}\"] audio`);return !a.seeking&&Math.abs(a.currentTime-5)<.005}",arg=row['id'])
                async with page.expect_download() as download:
                    await card.locator('a.download').click()
                d=await download.value;file=Path(await d.path());assert hashlib.sha256(file.read_bytes()).hexdigest()==row['sha256']
                report['samples'].append({**row,**values,'played':True,'seek_completed':True,'download_hash_matches':True})
            for width,name in ((1400,'desktop'),(390,'mobile')):
                await page.set_viewport_size({'width':width,'height':1000 if width==1400 else 844})
                assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                await page.screenshot(path=str(out/(name+'.png')),full_page=True)
            assert not report['errors'] and not report['network_requests']
            report['passed']=True
            await browser.close()
    except Exception as e:
        report['error']=str(e)
    (out/'browser.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return report['passed']

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('html',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--in-memory',action='store_true');a=p.parse_args()
    raise SystemExit(0 if asyncio.run(test(a.html,a.out,a.in_memory)) else 1)
