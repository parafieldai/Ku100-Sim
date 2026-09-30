import {parseWave,digest,referenceCrop,playbackGain,previewBytes,validateStudy,shuffled,feedbackRow} from './core.js';
const $=id=>document.getElementById(id);
const inline=window.__TARGET_INLINE__ || null;
let study, studyHash, activeReference, activeCandidate, order=[], revealed=false, generation=0;
const loadedReferences=new Map(), loadedCandidates=new Map(), observations=[];
const slots={reference:{element:$('reference-audio'),url:null,bytes:null,parsed:null,gain:null,heard:false},candidate:{element:$('candidate-audio'),url:null,bytes:null,parsed:null,gain:null,heard:false}};
function notice(text){$('status').textContent=text;}
function bytes64(s){const raw=atob(s);return Uint8Array.from(raw,c=>c.charCodeAt(0));}
function save(bytes,name,mime='application/octet-stream'){
  const url=URL.createObjectURL(new Blob([bytes],{type:mime}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),3000);
}
async function getAsset(name){
  if(inline){if(!inline.assets[name])throw Error('Missing inline generated asset');return bytes64(inline.assets[name]);}
  const response=await fetch('./generated/'+name);if(!response.ok)throw Error('Generated audio is unavailable: '+name);return new Uint8Array(await response.arrayBuffer());
}
function clearSlot(which){const s=slots[which];s.element.pause();s.element.removeAttribute('src');s.element.load();if(s.url)URL.revokeObjectURL(s.url);Object.assign(s,{url:null,bytes:null,parsed:null,gain:null,heard:false});}
function setSlot(which,bytes){
  clearSlot(which);const s=slots[which], parsed=parseWave(bytes),g=playbackGain(parsed,$('level-condition').value);
  const preview=previewBytes(parsed,g.applied);s.url=URL.createObjectURL(new Blob([preview],{type:'audio/wav'}));
  Object.assign(s,{bytes,parsed,gain:g});s.element.src=s.url;s.element.volume=10**(Number($('master').value)/20);s.element.load();
  $(which==='reference'?'ref-gain':'candidate-gain').textContent=`Preview: ${g.gain_db.toFixed(2)} dB shared clip gain${g.peak_guard_active?' · static peak guard active':''}, then headphone attenuation. Original WAV download unchanged.`;
}
function enable(){
  $('play-reference').disabled=!slots.reference.bytes;$('download-ref').disabled=!slots.reference.bytes;
  $('play-candidate').disabled=!slots.candidate.bytes;$('download-candidate').disabled=!slots.candidate.bytes;
  $('save-rating').disabled=!(slots.reference.heard&&slots.candidate.heard);
  $('download-feedback').disabled=!observations.length;
}
function renderIdentity(){
  $('identity').hidden=!revealed;$('reveal').textContent=revealed?'Method revealed for this comparison':'Reveal method & measurements';
  const el=$('identity');el.replaceChildren();if(!revealed||!activeCandidate)return;
  const h=document.createElement('h3');h.textContent=activeCandidate.title;el.append(h);
  const p=document.createElement('p');p.textContent=activeCandidate.claim;el.append(p);
  const match=study.comparisons.find(c=>c.reference===activeReference.id&&c.candidate===activeCandidate.id);
  const display={reference:activeReference.id,reference_ild_db:activeReference.metrics.ild_left_minus_right_db,
    candidate_ild_db:activeCandidate.metrics.ild_left_minus_right_db,
    ild_error_db:match?.ild_error_db,reference_bands_per_ear:activeReference.metrics.band_power_fraction_per_ear,
    candidate_bands_per_ear:activeCandidate.metrics.band_power_fraction_per_ear,
    bands_hz:activeReference.metrics.audio_bands_hz,
    reference_peak_rate_hz:activeReference.metrics.acoustic_peak_rate_hz,
    candidate_peak_rate_hz:activeCandidate.metrics.acoustic_peak_rate_hz,
    waveform_alignment:false,physical_controls_validated:false,target_accepted:false};
  const pre=document.createElement('pre');pre.textContent=JSON.stringify(display,null,2);el.append(pre);
  const note=document.createElement('p');note.textContent='These are discrepancies, not realism scores. All comparison excerpts were previously inspected; none is a newly blind physical validation.';el.append(note);
}
async function chooseCandidate(){
  const ticket=++generation,candidate=order[Number($('candidate-select').value)];activeCandidate=candidate;
  clearSlot('candidate');enable();$('candidate-letter').textContent=$('blind-mode').checked?'Candidate '+String.fromCharCode(65+Number($('candidate-select').value)):candidate.title;
  renderIdentity();$('feedback-form').reset();
  try{
    let bytes=loadedCandidates.get(candidate.id);
    if(!bytes){
      bytes=await getAsset(candidate.file);if(ticket!==generation)return;
      const sha=await digest(bytes);if(ticket!==generation)return;
      if(sha!==candidate.sha256)throw Error('Generated WAV hash mismatch');
      loadedCandidates.set(candidate.id,bytes);
    }
    if(ticket!==generation)return;setSlot('candidate',bytes);enable();notice('Comparison ready. Reference playback is required before recording a listening observation.');
  }catch(e){if(ticket===generation)notice(String(e.message||e));}
}
async function chooseReference(){
  activeReference=study.references.find(r=>r.id===$('reference-select').value);revealed=false;
  $('ref-title').textContent=`${activeReference.title} · ${activeReference.crop_s.join('–')} seconds in supplied file`;
  $('reference-description').textContent='Chapter label only: hardware, contact action, force and recording processing are unverified. This crop is excluded from the new parameter fit but was previously inspected.';
  clearSlot('reference');const bytes=loadedReferences.get(activeReference.id);if(bytes)setSlot('reference',bytes);
  $('reference-status').textContent=bytes?'Verified reference crop loaded locally.':'Load the original chapter WAV to hear this exact reference.';
  const options=study.candidates.filter(c=>c.side===activeReference.side_label);
  order=$('blind-mode').checked?shuffled(options):options;
  $('candidate-select').replaceChildren(...order.map((c,i)=>{const o=document.createElement('option');o.value=String(i);o.textContent=$('blind-mode').checked?'Candidate '+String.fromCharCode(65+i):c.title;return o;}));
  await chooseCandidate();
}
async function loadReferences(files){
  for(const file of files){
    try{
      if(file.size>64*1024*1024)throw Error('Reference file exceeds 64 MiB limit');
      const raw=new Uint8Array(await file.arrayBuffer());const sha=await digest(raw),r=study.references.find(r=>r.sha256===sha);
      if(!r)throw Error('This is not one of the exact supplied chapter WAVs; no guessed match accepted');
      const crop=referenceCrop(parseWave(raw),r);
      if(await digest(crop.slice(44))!==r.crop_pcm_f32_sha256)throw Error('Cropped stereo sample identity mismatch');
      loadedReferences.set(r.id,crop);notice(`Verified ${r.title} locally; no file uploaded.`);
    }catch(e){notice(`${file.name}: ${e.message}`);}
  }
  const bytes=loadedReferences.get(activeReference.id);if(bytes){setSlot('reference',bytes);$('reference-status').textContent='Original file SHA-256 and exact crop samples verified locally.';}enable();
}
function renderResearch(){
  const wanted=$('trigger-filter').value, box=$('triggers');box.replaceChildren();
  for(const row of study.triggers.filter(t=>wanted==='all'||t.family===wanted)){
    const el=document.createElement('article');el.className='trigger';
    const cat=document.createElement('p');cat.className='category';cat.textContent=row.family;el.append(cat);
    const h=document.createElement('h3');h.textContent=row.item+' · '+row.action;el.append(h);
    for(const [label,key] of [['Sound','sound_description'],['Hypothesis, not a label','mechanism_hypothesis'],['Needed evidence','minimum_observations'],['Listen for','listen_for']]){const p=document.createElement('p'),b=document.createElement('strong');b.textContent=label+': ';p.append(b,document.createTextNode(row[key]));el.append(p);}
    const state=document.createElement('p');state.className='implementation';state.textContent=row.implementation;el.append(state);
    const cites=document.createElement('p');for(const id of row.sources){const source=study.sources.find(s=>s.id===id);if(!source)continue;const a=document.createElement('a');if(new URL(source.url).protocol!=='https:')throw Error('Source must be HTTPS');a.href=source.url;a.target='_blank';a.rel='noopener noreferrer';a.textContent=source.title;cites.append(a,document.createTextNode(' · '));}el.append(cites);box.append(el);
  }
}
function renderSources(){
  for(const s of study.sources){const el=document.createElement('div');el.className='source';const a=document.createElement('a');a.href=s.url;a.textContent=s.title;a.target='_blank';a.rel='noopener noreferrer';el.append(a);
    for(const text of [s.authors+' · '+s.access,s.supports]){const p=document.createElement('p');p.textContent=text;el.append(p);}$('sources').append(el);}
}
for(const [which,s] of Object.entries(slots)){
  s.element.addEventListener('play',()=>slots[which==='reference'?'candidate':'reference'].element.pause());
  s.element.addEventListener('timeupdate',()=>{if(!s.element.paused&&s.element.currentTime>.1)s.heard=true;enable();});
}
$('reference-files').addEventListener('change',e=>loadReferences([...e.target.files]));
$('blind-mode').addEventListener('change',chooseReference);
$('reference-select').addEventListener('change',chooseReference);$('candidate-select').addEventListener('change',chooseCandidate);
$('trigger-filter').addEventListener('change',renderResearch);
$('master').addEventListener('input',()=>{const level=Number($('master').value);$('master-label').textContent=level+' dB';for(const s of Object.values(slots))s.element.volume=10**(level/20);});
$('level-condition').addEventListener('change',()=>{for(const which of Object.keys(slots)){const b=slots[which].bytes;if(b)setSlot(which,b);}enable();});
for(const which of ['reference','candidate'])$('play-'+which).addEventListener('click',async()=>{try{const a=slots[which].element;a.currentTime=0;await a.play();}catch(e){notice('Playback could not start: '+e.message);}});
$('stop').addEventListener('click',()=>Object.values(slots).forEach(s=>s.element.pause()));
$('reveal').addEventListener('click',()=>{revealed=true;renderIdentity();});
$('download-ref').addEventListener('click',()=>save(slots.reference.bytes,activeReference.id+'-reference-crop.wav','audio/wav'));
$('download-candidate').addEventListener('click',()=>save(slots.candidate.bytes,activeCandidate.file,'audio/wav'));
$('feedback-form').addEventListener('submit',e=>{
  e.preventDefault();try{
    if(!slots.reference.heard||!slots.candidate.heard)throw Error('Play both the actual reference and candidate first');
    const chosen=document.querySelector('input[name=rating]:checked');
    const gains=Object.fromEntries(Object.entries(slots).map(([k,s])=>[k,{...s.gain,element_volume:s.element.volume,muted:s.element.muted,playback_rate:s.element.playbackRate}]));
    observations.push(feedbackRow({ref:activeReference,candidate:activeCandidate,rating:Number(chosen?.value),notes:$('notes').value,blind:!!$('blind-mode').checked&&!revealed,condition:$('level-condition').value,gains,studyHash}));
    $('feedback-status').textContent=`${observations.length} observation(s) recorded in this page. Download to keep them.`;$('feedback-form').reset();enable();
  }catch(error){notice(error.message);}
});
$('download-feedback').addEventListener('click',()=>save(JSON.stringify({schema:'target-listening-session/1',observations},null,2),'target-listening-results.json','application/json'));
window.addEventListener('pagehide',()=>{for(const which of Object.keys(slots))clearSlot(which);});
try{
  if(inline){study=validateStudy(inline.study);}else{const response=await fetch('./generated/study.json');if(!response.ok)throw Error('Build the target study before publishing');study=validateStudy(await response.json());}
  studyHash=await digest(new TextEncoder().encode(JSON.stringify(study)));
  if(inline?.references){
    for(const r of study.references){const pack=inline.references[r.id];if(!pack)continue;const bytes=bytes64(pack.base64);if(await digest(bytes)!==pack.sha256||await digest(bytes.slice(44))!==r.crop_pcm_f32_sha256)throw Error('Private reference crop integrity failed');parseWave(bytes);loadedReferences.set(r.id,bytes);}
    $('reference-import').hidden=true;
  }
  $('reference-select').replaceChildren(...study.references.map(r=>{const o=document.createElement('option');o.value=r.id;o.textContent=r.title+' ('+r.crop_s.join('–')+' s)';return o;}));
  renderSources();renderResearch();await chooseReference();
}catch(e){notice('Study failed to load: '+(e.message||e));console.error(e);}
