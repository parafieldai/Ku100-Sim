
import {digest,parseWave} from '../target/core.js';
const audios=[],urls=[];
const status=document.getElementById('status'),cards=document.getElementById('cards'),slider=document.getElementById('level');

function volume(){document.getElementById('level-text').textContent=slider.value+' dB';for(const a of audios)a.volume=10**(Number(slider.value)/20)}
slider.addEventListener('input',volume);
(async()=>{try{
 const response=await fetch('./generated/manifest.json');if(!response.ok)throw Error('Manifest unavailable');const data=await response.json();
 if(data.mono_output_allowed!==false||data.human_listening_pass!==null)throw Error('Invalid evaluation status');
 for(const row of data.samples){const card=document.createElement('article');card.className='card';card.dataset.id=row.id;const title=document.createElement('h2');title.textContent=row.title;card.append(title);const desc=document.createElement('p');desc.className='small';desc.textContent=row.description;card.append(desc);
 const c=document.createElement('canvas');c.width=900;c.height=180;c.setAttribute('aria-label','Rendered left and right audio envelopes');card.append(c);
 const ctx=c.getContext('2d'),max=Math.max(...row.envelope.flat());['#416d54','#807255'].forEach((color,ch)=>{ctx.strokeStyle=color;ctx.lineWidth=2;ctx.beginPath();row.envelope.forEach((v,i)=>{const x=i/(row.envelope.length-1)*c.width,y=160-140*v[ch]/max;i?ctx.lineTo(x,y):ctx.moveTo(x,y)});ctx.stroke()});
 if(!/^[a-z0-9-]+\.wav$/.test(row.file))throw Error('Invalid WAV path');const response=await fetch('./generated/'+row.file);if(!response.ok)throw Error('Missing generated file');const raw=new Uint8Array(await response.arrayBuffer());const parsed=parseWave(raw);let d=0;for(let i=0;i<parsed.frames;i++)d=Math.max(d,Math.abs(parsed.samples[0][i]-parsed.samples[1][i]));if(d<1e-9)throw Error('Mono output rejected');if(await digest(raw)!==row.sha256)throw Error('File hash mismatch');
 const url=URL.createObjectURL(new Blob([raw],{type:'audio/wav'}));urls.push(url);const audio=document.createElement('audio');audio.controls=true;audio.preload='metadata';audio.src=url;card.append(audio);audios.push(audio);audio.addEventListener('play',()=>audios.forEach(x=>{if(x!==audio)x.pause()}));
 const play=document.createElement('button');play.textContent='Play from start';play.onclick=async()=>{try{audio.currentTime=0;await audio.play()}catch(e){status.textContent=e.message}};card.append(play);
 const download=document.createElement('a');download.className='download';download.href=url;download.download=row.file;download.textContent='Stereo WAV';card.append(download);
 const p=document.createElement('p');p.className='small';p.textContent=`${(row.frames/row.sample_rate).toFixed(1)} s · 48 kHz · different left/right signals · no listening score`;card.append(p);cards.append(card);
 }
 volume();status.textContent='All '+data.samples.length+' stereo files verified. Choose Play from start.';
}catch(e){status.textContent='Unable to open comparison: '+e.message;console.error(e)}})();
window.addEventListener('pagehide',()=>{audios.forEach(x=>x.pause());urls.forEach(x=>URL.revokeObjectURL(x))});
