import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {parseWave,waveBytes,playbackGain,previewBytes,referenceCrop,feedbackRow,shuffled,portableDigest} from '../target/core.js';
test('stereo RMS preview uses exactly one gain and preserves original samples',()=>{
 const s=[new Float32Array([.1,-.2,.05]),new Float32Array([.001,-.002,.0005])];
 const raw=waveBytes(s,48000),x=parseWave(raw),g=playbackGain(x,'stereo-rms'),p=parseWave(previewBytes(x,g.applied));
 assert.ok(Math.abs(p.samples[0][0]/p.samples[1][0]-100)<.00001);assert.deepEqual(parseWave(raw).samples,s);assert.ok(p.peak<=.500001);
 assert.equal(playbackGain(x,'original').applied,1);
});
test('reference crop preserves both ears and exact sample interval',()=>{
 const raw=waveBytes([new Float32Array([1,2,3,4]),new Float32Array([-1,-2,-3,-4])],44100);
 const crop=parseWave(referenceCrop(parseWave(raw),{source_rate_hz:44100,source_frames:4,crop_frames:[1,3]}));
 assert.deepEqual([...crop.samples[0]],[2,3]);assert.deepEqual([...crop.samples[1]],[-2,-3]);
 assert.throws(()=>referenceCrop(parseWave(raw),{source_rate_hz:44100,source_frames:4,crop_frames:[-1,3]}));
});
test('randomized ordering does not mutate or drop methods',()=>{
 const input=['native','empirical','ablation'];const a=shuffled(input,()=>.1);assert.deepEqual(input,['native','empirical','ablation']);assert.deepEqual([...a].sort(),[...input].sort());assert.throws(()=>shuffled(input,()=>1));
});
test('listening observations require real nonempty ratings and retain provenance',()=>{
 const a={ref:{id:'r',sha256:'a',crop_frames:[1,3],source_rate_hz:44100},candidate:{id:'c',sha256:'b'},rating:4,notes:'<script>alert(1)</script>',blind:true,condition:'original',gains:{},studyHash:'c'};
 assert.equal(feedbackRow(a).rating_1_to_5,4);assert.equal(feedbackRow(a).notes,a.notes);assert.throws(()=>feedbackRow({...a,rating:0}));
});
test('source and target roles are explicit and imported reference material is never sent',()=>{
 const s=fs.readFileSync(new URL('../target/app.js',import.meta.url),'utf8');
 assert.equal(s.includes('XMLHttpRequest'),false);assert.equal(s.includes('sendBeacon'),false);assert.equal(s.includes('method: \'POST\''),false);
 const html=fs.readFileSync(new URL('../target/index.html',import.meta.url),'utf8');assert.match(html,/Target acceptance: not passed/);assert.match(html,/no upload/);
});

import {createHash} from 'node:crypto';
test('portable offline SHA-256 matches independent known vectors and offset buffers',()=>{
 for(const n of [0,1,3,55,56,63,64,65,1000,200000]){
   const raw=Uint8Array.from({length:n+3},(_,i)=>i%251).subarray(3);
   assert.equal(portableDigest(raw),createHash('sha256').update(raw).digest('hex'));
 }
 assert.equal(portableDigest(new TextEncoder().encode('abc')),'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');
});
