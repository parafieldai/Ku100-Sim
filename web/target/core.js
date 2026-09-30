/* Pure contracts for an acoustic listening study, NOT physical calibration. */
import {parseWave} from '../core.js';
export {parseWave};
export const CANDIDATE_IDS=['burst-right-a','burst-right-b','burst-left-a','continuous-right','fixture-right','fixture-left'];
export const REFERENCE_IDS=['chapter-03','chapter-05','chapter-04','chapter-06'];
export function portableDigest(bytes) {
  // Standard SHA-256 fallback for self-contained, non-secure local documents.
  // Checked against Web Crypto/Node vectors; never skip an integrity check.
  if(!(bytes instanceof Uint8Array)||bytes.length>64*1024*1024)throw Error('Invalid hash input');
  const k=new Uint32Array([0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2]);
  const h=new Uint32Array([0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19]);
  const n=Math.ceil((bytes.length+9)/64)*64,padded=new Uint8Array(n),v=new DataView(padded.buffer),w=new Uint32Array(64);
  padded.set(bytes);padded[bytes.length]=128;v.setUint32(n-8,Math.floor(bytes.length*8/2**32));v.setUint32(n-4,bytes.length*8>>>0);
  const r=(x,n)=>(x>>>n)|(x<<(32-n));
  for(let off=0;off<n;off+=64){
    for(let i=0;i<16;i++)w[i]=v.getUint32(off+4*i);
    for(let i=16;i<64;i++){const x=w[i-15],y=w[i-2],s0=r(x,7)^r(x,18)^(x>>>3),s1=r(y,17)^r(y,19)^(y>>>10);w[i]=(w[i-16]+s0+w[i-7]+s1)>>>0;}
    let [a,b,c,d,e,f,g,hh]=h;
    for(let i=0;i<64;i++){const s1=r(e,6)^r(e,11)^r(e,25),ch=(e&f)^((~e)&g),t1=(hh+s1+ch+k[i]+w[i])>>>0,s0=r(a,2)^r(a,13)^r(a,22),maj=(a&b)^(a&c)^(b&c),t2=(s0+maj)>>>0;hh=g;g=f;f=e;e=(d+t1)>>>0;d=c;c=b;b=a;a=(t1+t2)>>>0;}
    const state=[a,b,c,d,e,f,g,hh];for(let i=0;i<8;i++)h[i]=(h[i]+state[i])>>>0;
  }
  return [...h].map(x=>x.toString(16).padStart(8,'0')).join('');
}
export async function digest(bytes) {
  if(globalThis.crypto?.subtle)return [...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');
  return portableDigest(bytes);
}
export function waveBytes(samples, rate) {
  if(!Array.isArray(samples)||samples.length!==2||samples[0].length!==samples[1].length ||
     !Number.isInteger(rate)||rate<8000||rate>192000||!samples[0].length||samples[0].length>30*rate)throw Error('Invalid stereo crop');
  const n=samples[0].length, bytes=new Uint8Array(44+8*n), v=new DataView(bytes.buffer);
  for(const [at,s] of [[0,'RIFF'],[8,'WAVE'],[12,'fmt '],[36,'data']])for(let i=0;i<s.length;i++)bytes[at+i]=s.charCodeAt(i);
  v.setUint32(4,bytes.length-8,true);v.setUint32(16,16,true);v.setUint16(20,3,true);v.setUint16(22,2,true);
  v.setUint32(24,rate,true);v.setUint32(28,rate*8,true);v.setUint16(32,8,true);v.setUint16(34,32,true);v.setUint32(40,n*8,true);
  for(let i=0;i<n;i++)for(let e=0;e<2;e++){
    const x=samples[e][i];if(!Number.isFinite(x)||Math.abs(x)>3.402823466e38)throw Error('Nonfinite crop');v.setFloat32(44+8*i+4*e,x,true);
  }
  return bytes;
}
export function referenceCrop(parsed, ref) {
  if(parsed.sampleRate!==ref.source_rate_hz||parsed.frames!==ref.source_frames)throw Error('Reference shape mismatch');
  const [a,b]=ref.crop_frames;
  if(!Number.isInteger(a)||!Number.isInteger(b)||a<0||b<=a||b>parsed.frames)throw Error('Invalid reference interval');
  return waveBytes(parsed.samples.map(x=>x.slice(a,b)),parsed.sampleRate);
}
export function playbackGain(parsed, mode) {
  if(!['original','stereo-rms'].includes(mode))throw Error('Unknown listening condition');
  const rms=Math.sqrt((parsed.rms[0]**2+parsed.rms[1]**2)/2);
  let wanted=mode==='stereo-rms'&&rms>0?10**(-26/20)/rms:1;
  // Static shared peak guard is explicitly reported, not a limiter or per-ear match.
  const applied=parsed.peak>0?Math.min(wanted,.5/parsed.peak):wanted;
  return {requested:wanted,applied,peak_guard_active:applied<wanted,
    method:mode==='stereo-rms'?'One shared scalar to -26 dBFS stereo RMS; not perceptual loudness matching':'Original relative digital level; uncalibrated recording chains',
    gain_db:20*Math.log10(applied)};
}
export function previewBytes(parsed,gain) {
  if(!Number.isFinite(gain)||gain<0||gain>100000)throw Error('Invalid preview gain');
  return waveBytes(parsed.samples.map(x=>Float32Array.from(x,a=>a*gain)),parsed.sampleRate);
}
export function validateStudy(x) {
  if(x?.schema!=='target-listening-study/1'||x.reference_audio_public!==false||x.physical_target_implemented!==false||x.status!=='target_not_accepted')throw Error('Study must retain its target-failure and privacy labels');
  if(!Array.isArray(x.candidates)||x.candidates.length!==6||!Array.isArray(x.references)||x.references.length!==4)throw Error('Unexpected study population');
  if(new Set(x.candidates.map(e=>e.id)).size!==6||new Set(x.references.map(e=>e.id)).size!==4)throw Error('Duplicate study IDs');
  for(const c of x.candidates){
    if(!CANDIDATE_IDS.includes(c.id)||c.file!==c.id+'.wav'||!/^[a-f0-9]{64}$/.test(c.sha256)||!['empirical','ablation','fixture'].includes(c.kind))throw Error('Invalid generated audio identity');
  }
  for(const r of x.references){
    if(!REFERENCE_IDS.includes(r.id)||!/^[a-f0-9]{64}$/.test(r.sha256)||!Array.isArray(r.crop_frames)||r.crop_frames.length!==2)throw Error('Invalid reference identity');
  }
  if(!Array.isArray(x.sources)||x.sources.length>40||!Array.isArray(x.triggers)||x.triggers.length>100)throw Error('Invalid research inventory');
  for(const source of x.sources){if(typeof source.url!=='string'||new URL(source.url).protocol!=='https:')throw Error('Research source must use HTTPS');}
  return x;
}
export function shuffled(items, random=()=>crypto.getRandomValues(new Uint32Array(1))[0]/2**32){
  const copy=[...items];for(let i=copy.length-1;i>0;i--){const r=random();if(!Number.isFinite(r)||r<0||r>=1)throw Error('Invalid random draw');const j=Math.floor(r*(i+1));[copy[i],copy[j]]=[copy[j],copy[i]];}return copy;
}
export function feedbackRow({ref,candidate,rating,notes,blind,condition,gains,studyHash}){
  if(!Number.isInteger(rating)||rating<1||rating>5||typeof notes!=='string'||notes.length>4000||typeof blind!=='boolean')throw Error('Choose a real rating before saving');
  return {schema:'target-listening-observation/1',time_utc:new Date().toISOString(),reference_id:ref.id,
    original_source_sha256:ref.sha256,crop_frames:ref.crop_frames,source_sample_rate_hz:ref.source_rate_hz,
    candidate_id:candidate.id,candidate_sha256:candidate.sha256,rating_1_to_5:rating,notes,
    identity_hidden_at_rating:blind,condition,preview_gains:gains,study_sha256:studyHash,
    interpretation:'One user report, not controlled population evidence or physical calibration'};
}
