"""Actual Chromium e2e over a local HTTP server; no listening-quality inference."""
import argparse, functools, http.server,json,pathlib,threading
from playwright.sync_api import sync_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--site',type=pathlib.Path,default=ROOT/'_site');p.add_argument('--chromium',default='/usr/bin/chromium');p.add_argument('--offline',action='store_true');a=p.parse_args()
    handler=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(a.site))
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    results=[];errors=[]
    try:
      with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=a.chromium,headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1360,'height':1050},accept_downloads=True)
        page.on('pageerror',lambda e:errors.append(str(e)))
        if a.offline:page.set_content((a.site/'offline.html').read_text())
        else:page.goto(f'http://127.0.0.1:{server.server_port}/')
        page.wait_for_function('window.labReady===true')
        page.wait_for_function('document.getElementById("audio").readyState>=1')
        results.append({'check':'native scene and WAV metadata load','passed':True})
        page.locator('#audio').click(position={'x':25,'y':25})
        page.wait_for_function('!document.getElementById("audio").paused && document.getElementById("audio").currentTime>.15')
        results.append({'check':'native browser control starts audio playback','passed':True})
        page.locator('#audio').evaluate('(e)=>{e.pause();e.currentTime=.6}')
        page.wait_for_function('Math.abs(window.labTelemetry.time-.6)<.02')
        results.append({'check':'seek updates solved telemetry','passed':True})
        page.locator('#take').select_option('1');page.wait_for_function('document.getElementById("status").textContent.startsWith("Ready") && window.labSceneId==="stroke-right"')
        page.locator('#audio').evaluate('(e)=>{e.currentTime=.6}')
        page.wait_for_function('Math.abs(window.labTelemetry.right)>Math.abs(window.labTelemetry.left)*2')
        results.append({'check':'right contact scene has right-dominant displayed cavity pressure','passed':True})
        with page.expect_download() as info:page.locator('#scenejson').click()
        down=info.value;f=down.path();scene=json.loads(pathlib.Path(f).read_text())
        assert scene['side']=='right' and scene['action']=='stroke'
        results.append({'check':'scene JSON export contains actual settings','passed':True})
        page.locator('#take').select_option('0');page.wait_for_timeout(500)
        (ROOT/'research').mkdir(exist_ok=True);page.screenshot(path=str(ROOT/'research/browser-desktop.png'),full_page=True)
        page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(200)
        assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
        page.screenshot(path=str(ROOT/'research/browser-mobile.png'),full_page=True)
        results.append({'check':'mobile viewport has no horizontal overflow','passed':True})
        results.append({'check':'no uncaught browser exceptions','passed':not errors,'errors':errors})
        browser.close()
    finally:server.shutdown();server.server_close()
    report={'checks':results,'passed':all(r['passed'] for r in results),'count':len(results),'transport':'offline embedded native-output bundle' if a.offline else 'HTTP server', 'scope':'Real Chromium playback/telemetry/download checks. Does not establish audible realism, headphone quality or ASMR response.'}
    (ROOT/'research/browser.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    if not report['passed']:raise SystemExit(1)
if __name__=='__main__':main()
