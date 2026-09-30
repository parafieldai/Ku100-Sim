import {parseWave,digest,waveBytes} from '../target/core.js';
const $=id=>document.getElementById(id),cache=new Map(),players=[],urls=[];
const items=[['27_WoodPlate','wood-plate','Wood plate','24 fitted modes + generated transient texture'],['64_CeramicMug','ceramic-mug','Ceramic mug','24 fitted modes; the extra noise layer was rejected'],['94_GlassGoblet','glass-goblet','Glass goblet','24 fitted modes + generated transient texture']];
const variants=[['sharp','Shorter contact pulse'],['soft','Longer contact pulse'],['prior','Unmeasured prior · diagnostic']];
const ids=items.flatMap(([,slug])=>variants.map(([kind])=>slug+'-'+kind));
function volume(){const value=Number($('volume').value);$('volume-label').textContent=value+' dB';players.forEach(a=>a.volume=10**(value/20));}
$('volume').addEventListener('input',volume);$('stop').addEventListener('click',()=>players.forEach(a=>a.pause()));
try{
 const response=await fetch('./generated/manifest.json');if(!response.ok)throw Error('Manifest not available');const manifest=await response.json();
 if(manifest.schema!=='object-sfx-preview/1'||manifest.reference_audio_public!==false||manifest.physical_calibration!==false||manifest.render_from_recording!==false||manifest.old_ear_recordings_used!==false||manifest.samples.length!==9||new Set(manifest.samples.map(x=>x.id)).size!==9)throw Error('Unexpected object experiment');
 for(const row of manifest.samples){
  if(!ids.includes(row.id)||row.file!==row.id+'.wav'||!/^[a-f0-9]{64}$/.test(row.sha256))throw Error('Invalid file identity');
  const response=await fetch('./generated/'+row.file);if(!response.ok)throw Error('Missing '+row.file);const bytes=new Uint8Array(await response.arrayBuffer());
  if(await digest(bytes)!==row.sha256)throw Error('File hash mismatch');const wave=parseWave(bytes);
  if(wave.sampleRate!==48000||wave.frames!==row.frames||wave.samples.length!==2||wave.peak>.50004)throw Error('Unexpected audio format or peak');
  const url=URL.createObjectURL(new Blob([bytes],{type:'audio/wav'}));
  // Explicit code/32768 conversion avoids codec-dependent PCM scaling. The
  // downloadable original remains PCM16; Float32 preview preserves its samples.
  const preview=URL.createObjectURL(new Blob([waveBytes(wave.samples,wave.sampleRate)],{type:'audio/wav'}));urls.push(url,preview);cache.set(row.id,{...row,url,preview});
 }
 for(const [object,slug,title,description] of items){
  const card=document.createElement('article');card.dataset.object=object;
  const tag=document.createElement('span');tag.className='tag';tag.textContent='ITEM / TAPPING';card.append(tag);
  const name=document.createElement('h2');name.textContent=title;card.append(name);
  const desc=document.createElement('p');desc.className='description';desc.textContent=description;card.append(desc);
  const label=document.createElement('label');label.htmlFor=slug+'-variant';label.textContent='Excitation / model';card.append(label);
  const select=document.createElement('select');select.id=slug+'-variant';for(const [kind,text] of variants){const option=document.createElement('option');option.value=kind;option.textContent=text;select.append(option);}card.append(select);
  const audio=document.createElement('audio');audio.controls=true;audio.preload='metadata';players.push(audio);card.append(audio);
  const play=document.createElement('button');play.textContent='Play taps from start';card.append(play);
  const download=document.createElement('a');download.className='download';download.textContent='Download generated WAV';card.append(download);
  const detail=document.createElement('p');detail.className='detail';card.append(detail);
  function set(){audio.pause();const item=cache.get(slug+'-'+select.value);card.dataset.id=item.id;audio.src=item.preview;audio.load();download.href=item.url;download.download=item.file;detail.textContent=`${item.frames/48000} seconds · 48 kHz · PCM16 download / exact Float32 preview · dual mono. ${item.kind==='prior'?'Diagnostic prior, separate listening gain.':'Shorter/longer share the same gain.'}`;volume();}
  audio.addEventListener('play',()=>{if(!audio.paused)players.forEach(other=>{if(other!==audio)other.pause();});});
  play.addEventListener('click',async()=>{try{players.forEach(other=>{if(other!==audio)other.pause();});audio.currentTime=0;await audio.play();}catch(e){$('status').textContent=e.message;}});select.addEventListener('change',set);$('items').append(card);set();
 }
 $('status').textContent='All nine generated files verified. Choose an object and press Play.';
}catch(e){$('status').textContent='Unable to load object sounds: '+e.message;console.error(e);}
window.addEventListener('pagehide',()=>{players.forEach(a=>a.pause());urls.forEach(u=>URL.revokeObjectURL(u));});
