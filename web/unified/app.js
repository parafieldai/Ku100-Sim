import {parseWave,digest} from '../target/core.js';
const $=id=>document.getElementById(id),audio=$('audio');let manifest,selected,definition,trace,urls=[],loading=0;
const download=(blob,name)=>{const u=URL.createObjectURL(blob),a=document.createElement('a');a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);};
const safe=/^[a-z][a-z0-9-]*$/;
function volume(){audio.volume=10**(Number($('volume').value)/20);$('volume-label').textContent=$('volume').value+' dB';}
$('volume').addEventListener('input',volume);volume();
$('stop').onclick=()=>{audio.pause();audio.currentTime=0;};
$('play').onclick=async()=>{try{audio.currentTime=0;await audio.play();}catch(e){$('status').textContent=e.message;}};
async function file(name,row){
 const r=await fetch('generated/'+name);if(!r.ok)throw Error('Missing '+name);const b=new Uint8Array(await r.arrayBuffer());
 if(await digest(b)!==row.files_sha256[name])throw Error('Hash mismatch '+name);return b;
}
async function select(){
 const ticket=++loading;audio.pause();$('play').disabled=true;$('export').disabled=true;selected=manifest.samples.find(x=>x.id===$('scene').value);
 if(!selected||!safe.test(selected.id))throw Error('Invalid scene');
 $('status').textContent='Checking audio, scene and trace…';const row=selected;
 const [a,b,c]=await Promise.all([file(row.audio,row),file(row.scene,row),file(row.trace,row)]);if(ticket!==loading)return;
 const parsed=parseWave(a);if(parsed.sampleRate!==48000||parsed.frames!==Math.round(row.seconds*48000)||parsed.peak>.80001)throw Error('Invalid audio');
 definition=JSON.parse(new TextDecoder().decode(b));trace=JSON.parse(new TextDecoder().decode(c));
 if(definition.schema!=='shared-mechanics/1'||definition.evidence.status!=='unmeasured_reduced_model')throw Error('Invalid scope');
 urls.forEach(u=>URL.revokeObjectURL(u));urls=[];
 const au=URL.createObjectURL(new Blob([a],{type:'audio/wav'})),tu=URL.createObjectURL(new Blob([c],{type:'application/json'}));urls.push(au,tu);
 audio.src=au;$('download').href=au;$('download').download=row.audio;$('trace-download').href=tu;$('trace-download').download=row.trace;
 $('name').textContent=row.name;$('description').textContent=row.description;$('limits').textContent=row.limitations;$('parameters').textContent=JSON.stringify(definition,null,2);
 $('stats').replaceChildren();
 for(const [label,value] of [['Engine','SimulationEngine'],['Coordinates',row.report.node_count],['Time integration',row.report.integrator==='exact_linear_foh'?'Exact linear optimization':'Discrete-gradient'],['Physical balance residual',row.report.max_energy_balance_error_j.toExponential(2)+' J']]){
  const d=document.createElement('div'),s=document.createElement('span'),b=document.createElement('strong');s.textContent=label;b.textContent=value;d.append(s,b);$('stats').append(d);
 }
 $('stiffness').value=1;$('damping').value=1;$('play').disabled=false;$('export').disabled=false;$('status').textContent='Verified. This is the actual native-rendered audio.';
}
$('scene').onchange=()=>select().catch(fail);
function fail(e){$('status').textContent='Cannot load: '+e.message;console.error(e);}
$('export').onclick=()=>{
 try{
  const k=Number($('stiffness').value),d=Number($('damping').value);if(!Number.isFinite(k)||!Number.isFinite(d)||k<.1||k>10||d<.1||d>10)throw Error('Multipliers must be 0.1–10.');
  const s=structuredClone(definition);s.name+=' · edited parameters';
  for(const n of s.nodes){n.k2_n_m*=k;if(n.k4_n_m3)n.k4_n_m3*=k;n.damping_n_s_m=(n.damping_n_s_m||0)*d;if(n.memory)n.memory.stiffness_n_m*=k;if(n.driver?.stiffness_n_m)n.driver.stiffness_n_m*=k;}
  for(const e of s.couplings||[])e.stiffness_n_m*=k;
  download(new Blob([JSON.stringify(s,null,2)],{type:'application/json'}),'edited-scene.json');$('edit-status').textContent='Edited scene exported. Native validation and a new render are required. Playback above is unchanged.';
 }catch(e){$('edit-status').textContent=e.message;}
};
const canvas=$('state'),ctx=canvas.getContext('2d');
function draw(){
 ctx.clearRect(0,0,canvas.width,canvas.height);
 if(trace){const i=Math.min(trace.time_s.length-1,Math.max(0,Math.floor(audio.currentTime*240))),q=trace.coordinates_m[i],n=q.length;
  ctx.strokeStyle='#cad7c7';ctx.fillStyle='#65785f';ctx.font='17px system-ui';ctx.fillText('Coordinate state at '+audio.currentTime.toFixed(2)+' s',24,30);
  for(let j=0;j<n;j++){const x=50+(j+.5)*(canvas.width-100)/n,lim=definition.nodes[j].limit_m,y=120-75*q[j]/lim;
   ctx.beginPath();ctx.moveTo(x,55);ctx.lineTo(x,195);ctx.stroke();ctx.beginPath();ctx.arc(x,y,Math.min(12,canvas.width/n/6),0,2*Math.PI);ctx.fillStyle='#416447';ctx.fill();ctx.fillStyle='#60725e';ctx.fillText(String(j+1),x-5,214);
  }
 }requestAnimationFrame(draw);
}draw();
try{const r=await fetch('generated/manifest.json');if(!r.ok)throw Error('Missing manifest');manifest=await r.json();if(manifest.schema!=='shared-mechanics-examples/1'||manifest.single_engine!=='SimulationEngine'||manifest.source_recordings_included!==false)throw Error('Invalid source provenance');
 for(const row of manifest.samples){if(!safe.test(row.id)||row.audio!==row.id+'.wav'||row.scene!==row.id+'.json'||row.trace!==row.id+'-trace.json')throw Error('Invalid manifest path');const o=document.createElement('option');o.value=row.id;o.textContent=row.name;$('scene').append(o);}
 $('scene').disabled=false;await select();
}catch(e){fail(e);}
window.addEventListener('pagehide',()=>{audio.pause();urls.forEach(u=>URL.revokeObjectURL(u));});
