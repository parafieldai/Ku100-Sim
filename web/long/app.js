import {parseWave,digest} from '../target/core.js';
const $=id=>document.getElementById(id),urls=[],audios=[];
const IDS=['fresh-right-a','fresh-right-b','fresh-left-a','long-right'];
function volume(){const level=Number($('level').value);$('level-label').textContent=level+' dB';audios.forEach(a=>a.volume=10**(level/20));}
$('level').addEventListener('input',volume);
try{
 const response=await fetch('./generated/manifest.json');if(!response.ok)throw Error('Manifest is unavailable');const m=await response.json();
 if(m.schema!=='long-texture-examples/1'||m.physical_model!==false||m.reference_audio_public!==false||m.pressure_control_implemented!==false||m.samples.length!==4||new Set(m.samples.map(x=>x.id)).size!==4)throw Error('Invalid experiment scope');
 for(const item of m.samples){
  if(!IDS.includes(item.id)||item.file!==item.id+'.wav'||!/^[a-f0-9]{64}$/.test(item.sha256))throw Error('Invalid generated asset');
  const card=document.createElement('article');card.dataset.id=item.id;
  const title=document.createElement('h2');title.textContent=item.title;card.append(title);
  const detail=document.createElement('p');detail.className='small';detail.textContent=item.id==='long-right'?'Three fresh sections · seeds 5101, 5102, 5103 · 3 s crossfades':'Fresh seed '+item.generation.seed+' · same fitted statistics, new waveform';card.append(detail);
  const audio=document.createElement('audio');audio.controls=true;audio.preload='metadata';audios.push(audio);card.append(audio);
  const play=document.createElement('button');play.textContent='Play from start';play.disabled=true;card.append(play);
  const link=document.createElement('a');link.className='download';link.textContent='Original WAV';link.download=item.file;card.append(link);$('cards').append(card);
  const r=await fetch('./generated/'+item.file);if(!r.ok)throw Error('Missing '+item.file);const bytes=new Uint8Array(await r.arrayBuffer());if(await digest(bytes)!==item.sha256)throw Error('Hash mismatch '+item.file);
  const parsed=parseWave(bytes);if(parsed.sampleRate!==48000||parsed.frames!==item.frames||parsed.peak>.600001)throw Error('Invalid decoded audio');
  const u=URL.createObjectURL(new Blob([bytes],{type:'audio/wav'}));urls.push(u);audio.src=u;link.href=u;play.disabled=false;
  audio.addEventListener('play',()=>audios.forEach(other=>{if(other!==audio)other.pause();}));
  play.addEventListener('click',async()=>{try{audio.currentTime=0;await audio.play();}catch(e){$('status').textContent=e.message;}});volume();
 }
 $('status').textContent='All four generated WAVs verified. Choose Play from start.';
}catch(e){$('status').textContent='Could not load comparison: '+e.message;console.error(e);}
window.addEventListener('pagehide',()=>{audios.forEach(a=>a.pause());urls.forEach(u=>URL.revokeObjectURL(u));});
