import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash, webcrypto} from 'node:crypto';
import {validateBundle, verifyAudioHash, parseWave, traceAt, normalizeManifest, validateScene, envelope} from '../core.js';

function waveBytes({format = 3, bits = 32, sampleRate = 48000, channels = 2, values = [[0, 0.5, -0.25, 0.125], [0, -0.125, 0.0625, 0]]} = {}) {
  const frames = values[0].length, block = channels * bits / 8, bytes = new Uint8Array(44 + frames * block), view = new DataView(bytes.buffer);
  const str = (at, text) => [...text].forEach((c, i) => { bytes[at + i] = c.charCodeAt(0); });
  str(0, 'RIFF'); view.setUint32(4, bytes.length - 8, true); str(8, 'WAVE'); str(12, 'fmt '); view.setUint32(16, 16, true);
  view.setUint16(20, format, true); view.setUint16(22, channels, true); view.setUint32(24, sampleRate, true); view.setUint32(28, sampleRate * block, true); view.setUint16(32, block, true); view.setUint16(34, bits, true); str(36, 'data'); view.setUint32(40, frames * block, true);
  for (let i = 0; i < frames; i++) for (let c = 0; c < channels; c++) {
    const at = 44 + i * block + c * bits / 8, value = values[c][i];
    if (format === 3) view.setFloat32(at, value, true);
    else if (bits === 16) view.setInt16(at, value * 32768, true);
    else if (bits === 24) { const n = value * 8388608; bytes[at] = n & 255; bytes[at + 1] = (n >> 8) & 255; bytes[at + 2] = (n >> 16) & 255; }
    else view.setInt32(at, value * 2147483648, true);
  }
  return bytes;
}

function bundle() {
  return {version: 'ku100-render/1', scene: {version: 'ku100-scene/1', name: 'Fixture', preset: 'stroke', side: 'left', duration_s: 1, physics: {load_n: 0.6}, receiver: {mode: 'contact'}},
    audio: {mime: 'audio/wav', base64: Buffer.from(waveBytes()).toString('base64'), channels: 2, sha256: createHash('sha256').update(waveBytes()).digest('hex')}, sample_rate_hz: 48000, duration_s: 4 / 48000,
    trace: {columns: ['time_s', 'normal_force_n'], rows: [[0, 0], [2 / 48000, 1], [3 / 48000, 0.5]]},
    geometry: {units: 'm', axes: {x: 'forward', y: 'left', z: 'up'}, head: {radii_m: [0.09, 0.075, 0.11], center_m: [0, 0, 0]}, ears: [{side: 'left', center_m: [0, 0.0875, 0]}, {side: 'right', center_m: [0, -0.0875, 0]}], contact: {side: 'left', patch_radius_m: 0.004}}, metrics: {finite: true}, provenance: {renderer: 'test-only'}};
}

test('native Float32 stereo samples retain polarity, ear level and absolute amplitude', () => {
  const result = validateBundle(bundle());
  assert.deepEqual([...result.wave.samples[0]], [0, 0.5, -0.25, 0.125]);
  assert.deepEqual([...result.wave.samples[1]], [0, -0.125, 0.0625, 0]);
  assert.equal(result.wave.peak, 0.5);
  assert.ok(result.wave.rms[0] > result.wave.rms[1]);
  assert.equal(result.bytes.length, 76);
});

for (const bits of [16, 24, 32]) test(`PCM ${bits}-bit decode preserves sign and stereo order`, () => {
  const result = parseWave(waveBytes({format: 1, bits}));
  assert.equal(result.samples[0][2], -0.25);
  assert.equal(result.samples[1][1], -0.125);
});

test('truncated, mono and non-finite WAV data fail before playback', () => {
  assert.throws(() => parseWave(waveBytes().subarray(0, 70)), /length|truncated/);
  assert.throws(() => parseWave(waveBytes({channels: 1})), /two-channel/);
  const bytes = waveBytes(); new DataView(bytes.buffer).setFloat32(44, NaN, true);
  assert.throws(() => parseWave(bytes), /non-finite/);
});

test('duplicate chunks, trailing bytes, residual headers and incorrect byte rates fail', () => {
  const base = waveBytes();
  for (const chunk of [base.slice(12, 36), base.slice(36), new Uint8Array(3)]) {
    const bytes = new Uint8Array(base.length + chunk.length); bytes.set(base); bytes.set(chunk, base.length); new DataView(bytes.buffer).setUint32(4, bytes.length - 8, true);
    assert.throws(() => parseWave(bytes), /duplicated|incomplete/);
  }
  const trailing = new Uint8Array(base.length + 1); trailing.set(base); assert.throws(() => parseWave(trailing), /complete file/);
  const badRate = base.slice(); new DataView(badRate.buffer).setUint32(28, 48000, true); assert.throws(() => parseWave(badRate), /dimensions/);
});

test('declared audio hash is verified before playback and corruption is rejected', async () => {
  const valid = validateBundle(bundle());
  assert.equal(await verifyAudioHash(valid, webcrypto), valid.bundle.audio.sha256);
  valid.bytes[44] ^= 1;
  await assert.rejects(verifyAudioHash(valid, webcrypto), /SHA-256 does not match/);
  await assert.rejects(verifyAudioHash(valid, null), /HTTPS or a localhost/);
});

test('inconsistent audio metadata and future schemas are rejected', () => {
  const value = bundle(); value.sample_rate_hz = 44100;
  assert.throws(() => validateBundle(value), /sample rates disagree/);
  value.sample_rate_hz = 48000; value.duration_s = 0.1;
  assert.throws(() => validateBundle(value), /durations disagree/);
  value.version = 'ku100-render/2';
  assert.throws(() => validateBundle(value), /ku100-render\/1/);
});

test('trace column ambiguity, dimensions, backwards time and invalid values are rejected', () => {
  const changes = [v => { v.trace.columns[1] = 'time_s'; }, v => { v.trace.rows[0].push(1); }, v => { v.trace.rows[1][0] = 0; }, v => { v.trace.rows[1][1] = Infinity; }, v => { v.trace.rows[2][0] = 10; }];
  for (const change of changes) { const value = bundle(); change(value); assert.throws(() => validateBundle(value)); }
});

test('geometry units and coordinate orientation must be explicit', () => {
  const value = bundle(); value.geometry.units = 'cm'; assert.throws(() => validateBundle(value), /metres/);
  value.geometry.units = 'm'; value.geometry.axes.y = 'right'; assert.throws(() => validateBundle(value), /axes/);
  value.geometry.axes.y = 'left'; value.geometry.head.radii_m[0] = -0.09; assert.throws(() => validateBundle(value), /metre scale/);
});

test('trace interpolation follows audio-aligned timestamps without inventing tail state', () => {
  const trace = {columns: ['normal_force_n', 'time_s'], rows: [[2, 0.01], [6, 0.02], [0, 0.03]]};
  const row = traceAt(trace, 0.015);
  assert.ok(Math.abs(row[0] - 4) < 1e-10);
  assert.equal(row[1], 0.015);
  assert.equal(traceAt(trace, 0), null);
  assert.equal(traceAt(trace, 0.04), null);
  assert.deepEqual(traceAt(trace, 0.03), [0, 0.03]);
  assert.notEqual(traceAt(trace, 0.03), trace.rows[2]);
});

test('wave envelopes preserve short positive and negative transients', () => {
  const samples = new Float32Array(1000); samples[10] = 0.8; samples[11] = -0.7;
  const values = envelope(samples, 10);
  assert.ok(Math.abs(values[0][0] + 0.7) < 1e-6);
  assert.ok(Math.abs(values[0][1] - 0.8) < 1e-6);
  assert.deepEqual(values[1], [0, 0]);
});

test('example manifest permits local export basenames only', () => {
  const manifest = path => ({version: 1, examples: [{id: 'example', title: 'Example', path}]});
  assert.equal(normalizeManifest(manifest('stroke-left.ku100.json'))[0].id, 'example');
  for (const path of ['../private.ku100.json', 'https://host/file.ku100.json', '/file.ku100.json', 'file.wav']) assert.throws(() => normalizeManifest(manifest(path)), /local/);
  const value = manifest('test.ku100.json'); value.examples.push(value.examples[0]); assert.throws(() => normalizeManifest(value), /unique/);
});

test('scene editing validates its schema without mutating the loaded render', () => {
  const value = bundle(); const text = JSON.stringify({...value.scene, side: 'right'});
  assert.equal(validateScene(text).side, 'right'); assert.equal(value.scene.side, 'left');
  assert.throws(() => validateScene('{'), /JSON/);
  assert.throws(() => validateScene(JSON.stringify({...value.scene, duration_s: -1})), /duration/);
  assert.throws(() => validateScene(JSON.stringify({...value.scene, duration_s: 31})), /duration/);
  assert.throws(() => validateScene(JSON.stringify({...value.scene, receiver: {mode: '3dio'}})), /Receiver/);
  assert.throws(() => validateScene(JSON.stringify({...value.scene, physics: {load_n: [1, 2]}})), /finite number/);
  assert.throws(() => validateScene(JSON.stringify({...value.scene, physics: {plate_thickness_m: -0.1}})), /positive/);
  assert.throws(() => validateScene(JSON.stringify({...value.scene, physics: {modes_per_plate: 1.2}})), /integer/);
  assert.throws(() => validateScene(JSON.stringify({...value.scene, capture: {preamp_gain_db: 110}})), /native range/);
});

test('static app uses local scripts and styles, never inline remote executable dependencies', () => {
  const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
  assert.doesNotMatch(html, /<(?:script|link)[^>]+(?:src|href)=["']https?:\/\//i);
  assert.match(html, /id="force-canvas"/);
  assert.match(html, /Edits never change the audio currently loaded/);
});


test('native unsteady losses and texture-scale controls survive scene export', () => {
  const scene = bundle().scene;
  scene.physics = {unsteady_viscous_losses: 1, texture_min_wavelength_m: 1e-5, texture_max_wavelength_m: 0.003, texture_amplitude_exponent: 0.65};
  assert.deepEqual(validateScene(JSON.stringify(scene)).physics, scene.physics);
  for (const [field, value] of [['unsteady_viscous_losses', 2], ['texture_min_wavelength_m', 0], ['texture_amplitude_exponent', 3]]) {
    const bad = structuredClone(scene); bad.physics[field] = value;
    assert.throws(() => validateScene(JSON.stringify(bad)));
  }
  scene.physics.texture_max_wavelength_m = 1e-6;
  assert.throws(() => validateScene(JSON.stringify(scene)), /wavelengths/);
});
test('an undersampled spatial texture is rejected rather than rendered with hidden aliasing', () => {
  const scene = bundle().scene;
  scene.physics = {texture_min_wavelength_m: 1e-6, speed_m_s: 0.035, sample_rate: 192000};
  assert.throws(() => validateScene(JSON.stringify(scene)), /16 integration samples/);
});

test('partial geometry overrides are validated against omitted native defaults', () => {
  for (const physics of [{contact_radius_m: 0.04}, {plate_width_m: 0.9}, {plate_height_m: 0.001}, {plate_width_m: 0.025}]) {
    const value = bundle().scene; value.physics = physics;
    assert.throws(() => validateScene(JSON.stringify(value)), /aspect ratio|footprint/);
  }
  for (const physics of [{}, {plate_width_m: 0.03}, {contact_radius_m: 0.002},
                         {plate_width_m: 0.025, contact_radius_m: 0.001}]) {
    const value = bundle().scene; value.physics = physics;
    assert.deepEqual(validateScene(JSON.stringify(value)).physics, physics);
  }
});


test('exported integration rates stay within the native decimator range', () => {
  for (const rate of [48000, 96000, 192000, 384000, 768000]) {
    const value = bundle().scene; value.physics = {sample_rate: rate};
    assert.equal(validateScene(JSON.stringify(value)).physics.sample_rate, rate);
  }
  for (const rate of [1536000, 800000, 8000, 96000.5]) {
    const value = bundle().scene; value.physics = {sample_rate: rate};
    assert.throws(() => validateScene(JSON.stringify(value)), /sample_rate|Integration rate/);
  }
});
