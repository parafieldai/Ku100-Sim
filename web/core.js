/** Pure validation and time-series helpers; no network or browser state. */
export const BUNDLE_VERSION = 'ku100-render/1';
export const MAX_FILE_BYTES = 64 * 1024 * 1024;
const finite = value => typeof value === 'number' && Number.isFinite(value);
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
function assert(condition, message) { if (!condition) throw new Error(message); }
function vector(value, name, positive = false) {
  assert(Array.isArray(value) && value.length === 3 && value.every(finite), `${name} must contain three finite coordinates.`);
  assert(value.every(x => Math.abs(x) <= 10 && (!positive || x > 0)), `${name} is outside the supported metre scale.`);
}
function finiteTree(value, path, depth = 0) {
  assert(depth < 24, `${path} is nested too deeply.`);
  if (typeof value === 'number') assert(finite(value), `${path} contains a non-finite number.`);
  if (object(value) || Array.isArray(value)) for (const [key, child] of Object.entries(value)) finiteTree(child, `${path}.${key}`, depth + 1);
}

export function parseWave(bytes) {
  assert(bytes instanceof Uint8Array && bytes.byteLength >= 44, 'Audio is not a complete WAV file.');
  assert(bytes.byteLength <= MAX_FILE_BYTES, 'Audio exceeds the 64 MiB viewer limit.');
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const text = (at, count) => String.fromCharCode(...bytes.subarray(at, at + count));
  assert(text(0, 4) === 'RIFF' && text(8, 4) === 'WAVE', 'Audio must be a little-endian RIFF/WAVE file.');
  const declaredEnd = view.getUint32(4, true) + 8;
  assert(declaredEnd === bytes.length && declaredEnd >= 44, 'WAV header length must match the complete file.');
  let format, data;
  let at = 12;
  while (at < declaredEnd) {
    assert(at + 8 <= declaredEnd, 'WAV contains an incomplete chunk header.');
    const kind = text(at, 4), size = view.getUint32(at + 4, true), start = at + 8;
    assert(start + size <= declaredEnd, 'WAV contains a truncated chunk.');
    if (kind === 'fmt ') {
      assert(!format && size >= 16, 'WAV format chunk is incomplete or duplicated.');
      let codec = view.getUint16(start, true);
      format = {codec, channels: view.getUint16(start + 2, true), sampleRate: view.getUint32(start + 4, true), byteRate: view.getUint32(start + 8, true), blockAlign: view.getUint16(start + 12, true), bits: view.getUint16(start + 14, true)};
    }
    if (kind === 'data') { assert(!data, 'WAV data chunk is duplicated.'); data = {start, size}; }
    at = start + size + (size % 2);
  }
  assert(at === declaredEnd && format && data, 'WAV requires complete format, audio data and chunk padding.');
  const {codec, channels, sampleRate, byteRate, blockAlign, bits} = format;
  assert(channels === 2, 'The viewer requires two-channel binaural audio.');
  assert(sampleRate >= 8000 && sampleRate <= 192000, 'WAV sample rate is unsupported.');
  assert((codec === 3 && bits === 32) || (codec === 1 && [16, 24, 32].includes(bits)), 'WAV must contain Float32 or 16/24/32-bit PCM samples.');
  assert(blockAlign === channels * bits / 8 && byteRate === sampleRate * blockAlign && data.size % blockAlign === 0, 'WAV frame dimensions are inconsistent.');
  const frames = data.size / blockAlign;
  assert(frames > 0 && frames / sampleRate <= 600, 'WAV duration must be between zero and ten minutes.');
  const samples = [new Float32Array(frames), new Float32Array(frames)];
  let peak = 0;
  const squared = [0, 0];
  for (let i = 0; i < frames; i++) for (let channel = 0; channel < 2; channel++) {
    const offset = data.start + i * blockAlign + channel * bits / 8;
    let value;
    if (codec === 3) value = view.getFloat32(offset, true);
    else if (bits === 16) value = view.getInt16(offset, true) / 32768;
    else if (bits === 32) value = view.getInt32(offset, true) / 2147483648;
    else { let n = view.getUint8(offset) | (view.getUint8(offset + 1) << 8) | (view.getUint8(offset + 2) << 16); if (n & 0x800000) n -= 0x1000000; value = n / 8388608; }
    assert(finite(value), 'WAV contains non-finite samples.');
    samples[channel][i] = value;
    peak = Math.max(peak, Math.abs(value));
    squared[channel] += value * value;
  }
  return {samples, sampleRate, frames, duration: frames / sampleRate, peak, rms: squared.map(x => Math.sqrt(x / frames)), bits, codec};
}

export function validateBundle(bundle) {
  assert(object(bundle) && bundle.version === BUNDLE_VERSION, `Expected a ${BUNDLE_VERSION} export.`);
  assert(object(bundle.scene) && bundle.scene.version === 'ku100-scene/1', 'Bundle scene must use ku100-scene/1.');
  validateScene(JSON.stringify(bundle.scene));
  assert(finite(bundle.duration_s) && bundle.duration_s > 0 && bundle.duration_s <= 600, 'Bundle duration must be between zero and ten minutes.');
  assert(Number.isInteger(bundle.sample_rate_hz), 'Bundle sample rate must be an integer.');
  assert(object(bundle.audio) && bundle.audio.mime === 'audio/wav', 'Bundle must embed audio/wav.');
  assert(typeof bundle.audio.sha256 === 'string' && /^[a-f0-9]{64}$/.test(bundle.audio.sha256), 'Bundle must declare an audio SHA-256 digest.');
  assert(bundle.audio.channels === 2, 'Bundle audio must declare two channels.');
  const encoded = bundle.audio.base64;
  assert(typeof encoded === 'string' && encoded.length > 0 && encoded.length <= MAX_FILE_BYTES * 4 / 3 + 4, 'Missing audio or audio exceeds the viewer size limit.');
  assert(/^[A-Za-z0-9+/]*={0,2}$/.test(encoded) && encoded.length % 4 === 0, 'Audio base64 is malformed.');
  let decoded;
  try { decoded = atob(encoded); } catch { throw new Error('Audio base64 could not be decoded.'); }
  const bytes = Uint8Array.from(decoded, ch => ch.charCodeAt(0));
  const wave = parseWave(bytes);
  assert(bundle.sample_rate_hz === wave.sampleRate, 'Bundle and WAV sample rates disagree.');
  assert(Math.abs(bundle.duration_s - wave.duration) <= Math.max(2 / wave.sampleRate, 0.001), 'Bundle and WAV durations disagree.');
  assert(object(bundle.trace) && Array.isArray(bundle.trace.columns) && Array.isArray(bundle.trace.rows), 'Trace must provide columns and rows.');
  const {columns, rows} = bundle.trace;
  assert(columns.length >= 2 && columns.length <= 128 && columns.every(c => typeof c === 'string' && /^[a-zA-Z][a-zA-Z0-9_]{0,79}$/.test(c)), 'Trace column names are invalid.');
  assert(new Set(columns).size === columns.length, 'Trace column names must be unique.');
  const timeColumn = columns.indexOf('time_s');
  assert(timeColumn >= 0, 'Trace must include time_s.');
  assert(rows.length > 0 && rows.length <= 250000, 'Trace is empty or exceeds 250,000 rows.');
  let previous = -Infinity;
  for (const row of rows) {
    assert(Array.isArray(row) && row.length === columns.length && row.every(finite), 'Every trace row must match its columns and contain finite numbers.');
    const time = row[timeColumn];
    assert(time >= 0 && time > previous && time <= wave.duration + 0.001, 'Trace times must increase and stay inside the audio duration.');
    previous = time;
  }
  assert(object(bundle.geometry) && bundle.geometry.units === 'm', 'Geometry must explicitly use metres.');
  const geometry = bundle.geometry;
  assert(geometry.axes?.x === 'forward' && geometry.axes?.y === 'left' && geometry.axes?.z === 'up', 'Geometry must use x-forward, y-left, z-up axes.');
  assert(object(geometry.head), 'Geometry is missing its generic head.');
  vector(geometry.head.center_m, 'Head centre');
  vector(geometry.head.radii_m, 'Head radii', true);
  assert(Array.isArray(geometry.ears) && geometry.ears.length === 2, 'Geometry must include two ears.');
  assert(new Set(geometry.ears.map(e => e.side)).size === 2 && geometry.ears.every(e => ['left', 'right'].includes(e.side)), 'Geometry must provide left and right ears.');
  geometry.ears.forEach(ear => vector(ear.center_m, `${ear.side} ear centre`));
  assert(object(geometry.contact) && ['left', 'right'].includes(geometry.contact.side), 'Geometry contact side is missing.');
  assert(finite(geometry.contact.patch_radius_m) && geometry.contact.patch_radius_m > 0 && geometry.contact.patch_radius_m < 1, 'Contact patch radius is invalid.');
  assert(object(bundle.metrics) && object(bundle.provenance), 'Metrics and provenance must be objects.');
  finiteTree(bundle.scene, 'Scene'); finiteTree(bundle.metrics, 'Metrics');
  return {bundle, bytes, wave, timeColumn, columnMap: new Map(columns.map((c, i) => [c, i]))};
}

export async function verifyAudioHash(validated, provider = globalThis.crypto) {
  assert(provider?.subtle, 'Audio integrity verification requires HTTPS or a localhost server.');
  const digest = await provider.subtle.digest('SHA-256', validated.bytes);
  const actual = [...new Uint8Array(digest)].map(value => value.toString(16).padStart(2, '0')).join('');
  assert(actual === validated.bundle.audio.sha256, 'Audio SHA-256 does not match this export. Playback was not loaded.');
  return actual;
}

export function traceAt(trace, time, timeColumn = trace.columns.indexOf('time_s')) {
  const rows = trace.rows;
  if (!rows.length || time < rows[0][timeColumn] || time > rows.at(-1)[timeColumn]) return null;
  let lo = 0, hi = rows.length - 1;
  while (lo < hi) { const mid = Math.ceil((lo + hi) / 2); if (rows[mid][timeColumn] <= time) lo = mid; else hi = mid - 1; }
  if (lo === rows.length - 1 || rows[lo][timeColumn] === time) return rows[lo].slice();
  const a = rows[lo], b = rows[lo + 1], u = (time - a[timeColumn]) / (b[timeColumn] - a[timeColumn]);
  return a.map((value, i) => value + u * (b[i] - value));
}

export function normalizeManifest(manifest) {
  assert(object(manifest) && manifest.version === 1 && Array.isArray(manifest.examples), 'Example manifest format is invalid.');
  assert(manifest.examples.length <= 24, 'Example manifest is too large.');
  const ids = new Set();
  return manifest.examples.map(example => {
    assert(object(example) && typeof example.id === 'string' && !ids.has(example.id), 'Example IDs must be unique.');
    ids.add(example.id);
    assert(typeof example.path === 'string' && /^[a-zA-Z0-9][a-zA-Z0-9._-]*\.ku100\.json$/.test(example.path), 'Example path must name a local .ku100.json file.');
    assert(typeof example.title === 'string' && example.title.length <= 120, 'Example title is invalid.');
    return {...example, description: typeof example.description === 'string' ? example.description : ''};
  });
}

export function validateScene(text) {
  let scene;
  try { scene = JSON.parse(text); } catch (error) { throw new Error(`Scene JSON: ${error.message}`); }
  assert(object(scene) && scene.version === 'ku100-scene/1', 'Scene must use ku100-scene/1.');
  const allowed = new Set(['version', 'name', 'preset', 'side', 'duration_s', 'seed', 'physics', 'receiver', 'capture']);
  assert(Object.keys(scene).every(key => allowed.has(key)), 'Scene has unknown fields.');
  assert(scene.name === undefined || (typeof scene.name === 'string' && scene.name.trim().length > 0 && scene.name.length <= 160), 'Scene name must contain 1–160 characters.');
  assert(['stroke', 'press', 'tap', 'silence'].includes(scene.preset), 'Choose a supported native preset.');
  assert(['left', 'right'].includes(scene.side), 'Scene side must be left or right.');
  assert(finite(scene.duration_s) && scene.duration_s >= 0.02 && scene.duration_s <= 30, 'Scene duration must be between 0.02 and 30 seconds.');
  assert(scene.seed === undefined || (Number.isInteger(scene.seed) && scene.seed >= 0 && scene.seed <= 4294967295), 'Seed must be an unsigned 32-bit integer.');
  assert(object(scene.physics) && object(scene.receiver), 'Scene must contain physics and receiver objects.');
  const positive = new Set(['contact_radius_m', 'plate_width_m', 'plate_height_m', 'plate_thickness_m', 'young_modulus_pa', 'density_kg_m3', 'cavity_volume_m3', 'duct_length_m', 'duct_radius_m', 'vent_length_m', 'vent_radius_m', 'contact_stiffness_n_m15', 'friction_velocity_m_s', 'film_thickness_m', 'film_viscosity_pa_s', 'air_density_kg_m3', 'sound_speed_m_s', 'air_viscosity_pa_s', 'texture_min_wavelength_m', 'texture_max_wavelength_m']);
  const nonnegative = new Set(['load_n', 'speed_m_s', 'roughness_rms_m', 'modal_loss_ratio', 'contact_damping_n_s_m', 'friction_coefficient']);
  const integerRanges = {sample_rate: [48000, 768000], modes_per_plate: [1, 1024], trace_stride: [1, 4294967295], duct_cells: [1, 256], unsteady_viscous_losses: [0, 1]};
  for (const [key, value] of Object.entries(scene.physics)) {
    assert(finite(value), `physics.${key} must be a finite number.`);
    if (positive.has(key)) assert(value > 0, `physics.${key} must be positive.`);
    else if (nonnegative.has(key)) assert(value >= 0, `physics.${key} must be nonnegative.`);
    else if (integerRanges[key]) { const [min, max] = integerRanges[key]; assert(Number.isInteger(value) && value >= min && value <= max, `physics.${key} must be an integer in ${min}–${max}.`); }
    else if (key === 'texture_amplitude_exponent') assert(value >= 0 && value <= 2, 'Texture exponent must be in 0–2.');
    else if (key === 'wetness') assert(value >= 0 && value <= 1, 'Wetness must be in 0–1.');
    else if (key === 'poisson_ratio') assert(value > -1 && value < 0.5, 'Poisson ratio must be between −1 and 0.5.');
    else throw new Error(`Unknown physics parameter: ${key}.`);
  }
  const p = scene.physics;
  const minWave = p.texture_min_wavelength_m ?? 120e-6;
  const maxWave = p.texture_max_wavelength_m ?? 3e-3;
  assert(minWave >= 1e-6 && maxWave <= 0.1 && minWave < maxWave, 'Texture wavelengths require 1 micrometre <= minimum < maximum <= 0.1 m.');
  if (scene.preset === 'stroke') assert((p.speed_m_s ?? 0.035) / minWave <= (p.sample_rate ?? 192000) / 16, 'Texture advection needs at least 16 integration samples per shortest wavelength.');
  if (p.sample_rate !== undefined) assert(p.sample_rate * scene.duration_s <= 24000000 && p.sample_rate % 48000 === 0, 'Integration rate must be a multiple of 48 kHz and total samples at most 24 million.');
  // Scenes may override just one field. Use the native defaults for omitted
  // dimensions so an exported partial scene cannot bypass coupled bounds.
  const width = p.plate_width_m ?? 0.060;
  const height = p.plate_height_m ?? 0.085;
  const radius = p.contact_radius_m ?? 0.004;
  const aspect = width / height;
  assert(aspect >= 0.25 && aspect <= 4, 'Plate aspect ratio must be in 0.25–4.');
  assert(radius <= 0.15 * Math.min(width, height), 'Contact footprint is too large for the plate.');
  const receiver = scene.receiver;
  assert(Object.keys(receiver).every(key => ['mode', 'azimuth_deg', 'distance_m'].includes(key)) && ['contact', 'airborne'].includes(receiver.mode), 'Receiver must be generic contact or measured KU100 airborne.');
  assert(receiver.azimuth_deg === undefined || finite(receiver.azimuth_deg), 'Receiver azimuth must be finite.');
  assert(receiver.distance_m === undefined || (finite(receiver.distance_m) && receiver.distance_m >= 0.25 && receiver.distance_m <= 1.5), 'Receiver distance must be within the measured 0.25–1.5 m range.');
  if (scene.capture !== undefined) {
    assert(object(scene.capture) && Object.keys(scene.capture).every(key => ['sensitivity_mv_pa', 'preamp_gain_db', 'adc_full_scale_v'].includes(key)), 'Capture settings are malformed.');
    for (const [key, value] of Object.entries(scene.capture)) {
      const [min, max] = key === 'preamp_gain_db' ? [-120, 100] : [0, key === 'sensitivity_mv_pa' ? 1000 : 100];
      assert(finite(value) && value <= max && (key === 'preamp_gain_db' ? value >= min : value > min), `capture.${key} is outside the native range.`);
    }
  }
  finiteTree(scene, 'Scene');
  return scene;
}

export function formatNumber(value, digits = 3) {
  if (!finite(value)) return '—';
  if (value === 0) return '0';
  return Math.abs(value) < 0.001 || Math.abs(value) >= 10000 ? value.toExponential(2) : Number(value.toPrecision(digits)).toString();
}

export function envelope(samples, bins) {
  const result = [];
  for (let i = 0; i < bins; i++) {
    const start = Math.floor(i * samples.length / bins), end = Math.min(samples.length, Math.max(start + 1, Math.floor((i + 1) * samples.length / bins)));
    let min = 0, max = 0;
    for (let j = start; j < end; j++) { min = Math.min(min, samples[j]); max = Math.max(max, samples[j]); }
    result.push([min, max]);
  }
  return result;
}
