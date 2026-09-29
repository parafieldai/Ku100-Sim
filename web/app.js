import {validateBundle, verifyAudioHash, validateScene, normalizeManifest, traceAt, envelope, formatNumber, MAX_FILE_BYTES} from './core.js';
import {FixtureView} from './view3d.js';

const $ = id => document.getElementById(id);
const audio = $('audio');
const colors = {left: '#68d9d3', right: '#a99af6', stored: '#ffb370', work: '#b2d5a0', dissipated: '#899da9'};
let loaded = null, audioURL = null, loadEpoch = 0, currentLabel = '', originalScene = '', examples = [], activeChoice = '';
let waveEnvelopes = null, frame = null;
const traceCaches = new Map();

function message(text, isError = false) {
  $('message').textContent = text;
  $('message').classList.toggle('error', isError);
  $('message').hidden = !text;
}

const fixture = new FixtureView($('geometry-canvas'), detail => {
  for (const [id, active] of [['view-full', !detail], ['view-detail', detail]]) { $(id).classList.toggle('active', active); $(id).setAttribute('aria-pressed', String(active)); }
});
$('view-full').addEventListener('click', () => fixture.setDetail(false));
$('view-detail').addEventListener('click', () => fixture.setDetail(true));
$('reset-view').addEventListener('click', () => fixture.reset());

function chartContext(canvas) {
  const rect = canvas.getBoundingClientRect(), dpr = Math.min(devicePixelRatio || 1, 2), width = Math.max(1, rect.width), height = Math.max(1, rect.height);
  if (canvas.width !== Math.round(width * dpr) || canvas.height !== Math.round(height * dpr)) { canvas.width = Math.round(width * dpr); canvas.height = Math.round(height * dpr); }
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, width, height);
  return {ctx, width, height, x0: 40, x1: Math.max(42, width - 8), y0: 7, y1: height - 16};
}

function grid(chart, min, max, duration) {
  const {ctx, width, height, x0, x1, y0, y1} = chart;
  ctx.font = '7px ui-monospace, monospace'; ctx.lineWidth = 1;
  for (let i = 0; i < 3; i++) {
    const y = y0 + i * (y1 - y0) / 2;
    ctx.strokeStyle = '#36434d65'; ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(x1, y); ctx.stroke();
    ctx.textAlign = 'right'; ctx.fillStyle = '#728591'; ctx.fillText(formatNumber(max - i * (max - min) / 2, 2), x0 - 5, y + 2);
  }
  for (let i = 0; i < 5; i++) {
    const x = x0 + i * (x1 - x0) / 4;
    ctx.strokeStyle = '#35414b45'; ctx.beginPath(); ctx.moveTo(x, y0); ctx.lineTo(x, y1); ctx.stroke();
    ctx.textAlign = i === 0 ? 'left' : i === 4 ? 'right' : 'center'; ctx.fillStyle = '#637684'; ctx.fillText(`${formatNumber(i * duration / 4, 2)}s`, x, height - 3);
  }
  if (min < 0 && max > 0) {
    const y = y1 - (0 - min) / (max - min) * (y1 - y0);
    ctx.strokeStyle = '#60717c50'; ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(x1, y); ctx.stroke();
  }
  if (!loaded) { ctx.fillStyle = '#657580'; ctx.textAlign = 'center'; ctx.fillText('No render loaded', width / 2 + 10, height / 2); }
}

function cursor(chart, time, duration) {
  const {ctx, x0, x1, y0, y1} = chart;
  const x = x0 + Math.max(0, Math.min(1, time / duration)) * (x1 - x0);
  ctx.strokeStyle = '#dce9edaa'; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(x, y0 - 2); ctx.lineTo(x, y1 + 2); ctx.stroke();
  ctx.fillStyle = '#dce9ed'; ctx.beginPath(); ctx.moveTo(x - 3, y0 - 3); ctx.lineTo(x + 3, y0 - 3); ctx.lineTo(x, y0 + 1); ctx.closePath(); ctx.fill();
}

function drawWave(time) {
  const chart = chartContext($('wave-canvas')), {ctx, x0, x1, y0, y1} = chart;
  const actualPeak = loaded?.wave.peak || 0, peak = actualPeak || 1, duration = loaded?.wave.duration || 1;
  grid(chart, -actualPeak, actualPeak, duration);
  if (!loaded) return;
  const bins = Math.max(1, Math.floor(x1 - x0));
  if (!waveEnvelopes || waveEnvelopes[0].length !== bins) waveEnvelopes = loaded.wave.samples.map(samples => envelope(samples, bins));
  waveEnvelopes.forEach((series, channel) => {
    ctx.strokeStyle = channel === 0 ? colors.left : colors.right; ctx.globalAlpha = 0.78; ctx.lineWidth = 1;
    ctx.beginPath();
    series.forEach(([lo, hi], i) => { const x = x0 + i / bins * (x1 - x0); ctx.moveTo(x, y1 - (lo + peak) / (2 * peak) * (y1 - y0)); ctx.lineTo(x, y1 - (hi + peak) / (2 * peak) * (y1 - y0)); });
    ctx.stroke(); ctx.globalAlpha = 1;
  });
  cursor(chart, time, duration);
}

function drawTrace(canvasId, series, time) {
  const chart = chartContext($(canvasId)), {ctx, x0, x1, y0, y1, width, height} = chart;
  const duration = loaded?.wave.duration || 1;
  const bins = Math.max(1, Math.floor(x1 - x0));
  let cached = traceCaches.get(canvasId);
  if (!cached || cached.bins !== bins) {
    const available = loaded ? series.map(([name, color]) => ({index: loaded.columnMap.get(name), color})).filter(s => s.index !== undefined) : [];
    let min = 0, max = 0;
    if (loaded) for (const row of loaded.bundle.trace.rows) for (const item of available) { min = Math.min(min, row[item.index]); max = Math.max(max, row[item.index]); }
    const silent = min === 0 && max === 0;
    const delta = max - min || Math.max(Math.abs(max) * 0.1, 1);
    if (max === min) { min -= delta / 2; max += delta / 2; } else { min -= delta * 0.05; max += delta * 0.05; }
    const lines = available.map(item => {
      const values = Array.from({length: bins}, () => null);
      for (const row of loaded.bundle.trace.rows) {
        const bin = Math.min(bins - 1, Math.floor(row[loaded.timeColumn] / duration * bins)), value = row[item.index];
        if (!values[bin]) values[bin] = {first: value, last: value, min: value, max: value};
        else { values[bin].last = value; values[bin].min = Math.min(values[bin].min, value); values[bin].max = Math.max(values[bin].max, value); }
      }
      return {values, color: item.color};
    });
    cached = {bins, min, max, lines, silent}; traceCaches.set(canvasId, cached);
  }
  const {min, max, lines} = cached;
  grid(chart, cached.silent ? 0 : min, cached.silent ? 0 : max, duration);
  if (loaded && !lines.length) { ctx.fillStyle = '#788c98'; ctx.textAlign = 'center'; ctx.font = '8px system-ui'; ctx.fillText('This export has no matching native trace', width / 2 + 10, height / 2); return; }
  if (!loaded) return;
  // Preserve extrema when decimating dense traces, rather than skipping transient peaks.
  for (const item of lines) {
    const yy = value => y1 - (value - min) / (max - min) * (y1 - y0);
    ctx.strokeStyle = item.color; ctx.lineWidth = 1.1; ctx.beginPath(); let begun = false;
    item.values.forEach((value, i) => { if (!value) return; const x = x0 + i / bins * (x1 - x0); if (!begun) { ctx.moveTo(x, yy(value.first)); begun = true; } else ctx.lineTo(x, yy(value.first)); ctx.lineTo(x, yy(value.min)); ctx.lineTo(x, yy(value.max)); ctx.lineTo(x, yy(value.last)); });
    ctx.stroke();
  }
  // The blank interval after the final trace sample is a receiver tail, not extrapolated state.
  cursor(chart, time, duration);
}

function drawCharts(time = 0) {
  drawWave(time);
  drawTrace('force-canvas', [['normal_force_n', colors.stored], ['friction_force_n', colors.dissipated]], time);
  drawTrace('pressure-canvas', [['cavity_left_pa', colors.left], ['cavity_right_pa', colors.right]], time);
  drawTrace('energy-canvas', [['stored_energy_j', colors.stored], ['input_work_j', colors.work], ['dissipated_energy_j', colors.dissipated]], time);
}

function timeState(time) {
  if (!loaded) return;
  time = Math.max(0, Math.min(time, loaded.wave.duration));
  const row = traceAt(loaded.bundle.trace, time, loaded.timeColumn);
  const get = name => row && loaded.columnMap.has(name) ? row[loaded.columnMap.get(name)] : null;
  $('current-time').textContent = time.toFixed(3);
  $('seek').value = time;
  $('metric-force').textContent = formatNumber(get('normal_force_n'));
  $('metric-balance').textContent = formatNumber(get('balance_error_j'));
  $('pressure-readout').textContent = row ? `L ${formatNumber(get('cavity_left_pa'))} / R ${formatNumber(get('cavity_right_pa'))}` : 'Outside native trace';
  $('geometry-state').textContent = row ? `${loaded.bundle.geometry.contact.side.toUpperCase()} CONTACT · t ${time.toFixed(3)} s` : 'RECEIVER OUTPUT · NO NATIVE STATE AT THIS TIME';
  $('state-info').textContent = row ? 'Native state · linear trace interpolation' : time < loaded.bundle.trace.rows[0][loaded.timeColumn] ? 'Receiver pre-roll · no state extrapolation' : 'Receiver tail · no state extrapolation';
  fixture.setTime(row);
  drawCharts(time);
}

function tick() {
  frame = null;
  if (loaded) timeState(audio.currentTime);
  if (!audio.paused) frame = requestAnimationFrame(tick);
}
function requestTick() { if (frame === null) frame = requestAnimationFrame(tick); }

function db(value) { return value === 0 ? 'Silence' : (20 * Math.log10(value)).toFixed(1); }

async function loadText(text, label, epoch) {
  if (text.length > MAX_FILE_BYTES) throw new Error('Bundle exceeds the 64 MiB import limit.');
  await new Promise(resolve => requestAnimationFrame(resolve));
  let bundle;
  try { bundle = JSON.parse(text); } catch { throw new Error('This file is not valid JSON. Import a native .ku100.json export.'); }
  const validated = validateBundle(bundle);
  await verifyAudioHash(validated);
  if (epoch !== loadEpoch) return false;
  audio.pause();
  if (audioURL) URL.revokeObjectURL(audioURL);
  loaded = validated; currentLabel = label; waveEnvelopes = null; traceCaches.clear();
  audioURL = URL.createObjectURL(new Blob([validated.bytes], {type: 'audio/wav'}));
  audio.src = audioURL; audio.load();
  $('play-button').disabled = false; $('seek').disabled = false; $('download-wav').disabled = false;
  $('seek').max = validated.wave.duration;
  $('total-time').textContent = validated.wave.duration.toFixed(3);
  $('playback-name').textContent = bundle.scene.name || label;
  $('render-badge').textContent = bundle.scene.receiver.mode === 'airborne' ? 'MEASURED TRANSFER SHAPE' : 'GENERIC CONTACT MODEL';
  $('audio-info').textContent = `${(validated.wave.sampleRate / 1000).toFixed(1)} kHz · stereo ${validated.wave.codec === 3 ? 'Float32' : `${validated.wave.bits}-bit PCM`} · no normalization`;
  $('metric-left').textContent = db(validated.wave.rms[0]);
  $('metric-right').textContent = db(validated.wave.rms[1]);
  $('metric-peak').textContent = formatNumber(validated.wave.peak);
  $('wave-scale').textContent = `±${formatNumber(validated.wave.peak)} · shared scale`;
  $('geometry-note').textContent = typeof bundle.geometry.label === 'string' ? bundle.geometry.label : 'Generic bilateral contact fixture. Geometry is not a KU100 scan.';
  const physics = bundle.metrics.physics;
  $('regime-warning').hidden = physics?.regime_valid !== false;
  $('regime-warning-text').textContent = Array.isArray(physics?.regime_warnings) && physics.regime_warnings.some(value => typeof value === 'string') ? physics.regime_warnings.filter(value => typeof value === 'string').join(' · ') : 'The native renderer marked this parameter regime invalid. Inspect the numerical metrics below.';
  const capture = bundle.scene.capture;
  $('capture-note').textContent = capture ? `${formatNumber(capture.sensitivity_mv_pa)} mV/Pa nominal sensitivity · ${capture.preamp_gain_db >= 0 ? '+' : ''}${formatNumber(capture.preamp_gain_db)} dB electronic gain · ${formatNumber(capture.adc_full_scale_v)} V ADC full scale. Ideal capture with no added device or self-noise. This gain is already in the WAV; the listening slider adds common playback attenuation only.` : 'No capture chain was declared in this export. Digital amplitude must not be interpreted as calibrated sound pressure.';
  $('provenance-json').textContent = JSON.stringify({version: bundle.version, sample_rate_hz: bundle.sample_rate_hz, duration_s: bundle.duration_s, provenance: bundle.provenance, metrics: bundle.metrics}, null, 2);
  fixture.setBundle(bundle);
  originalScene = JSON.stringify(bundle.scene, null, 2);
  $('scene-json').value = originalScene;
  for (const id of ['scene-preset', 'scene-side', 'scene-duration', 'scene-json', 'download-scene', 'reset-scene']) $(id).disabled = false;
  updateSceneEditor();
  timeState(0);
  message(validated.wave.peak > 1 ? 'This render contains samples above full scale. The original WAV is preserved; playback can clip. Listening gain affects both ears equally.' : '');
  return true;
}

async function loadExample(example) {
  const epoch = ++loadEpoch;
  message(`Loading ${example.title}…`);
  try {
    const response = await fetch(`./examples/${example.path}`);
    if (!response.ok) throw new Error(`Example fetch failed (${response.status}). Generate the bundled native examples before building the site.`);
    if (Number(response.headers.get('Content-Length')) > MAX_FILE_BYTES) throw new Error('Example exceeds the viewer size limit.');
    const accepted = await loadText(await response.text(), example.title, epoch);
    if (accepted) { activeChoice = example.id; $('example-select').value = example.id; $('example-description').textContent = example.description || 'A reproducible native render with its scene and numerical trace.'; }
  } catch (error) { if (epoch === loadEpoch) { message(error.message, true); $('example-select').value = activeChoice; } }
}

$('example-select').addEventListener('change', event => { const selected = examples.find(example => example.id === event.target.value); if (selected) loadExample(selected); });
$('bundle-file').addEventListener('change', async event => {
  const file = event.target.files?.[0]; if (!file) return;
  const epoch = ++loadEpoch;
  message(`Reading ${file.name} locally…`);
  try {
    if (file.size > MAX_FILE_BYTES) throw new Error('Bundle exceeds the 64 MiB import limit.');
    const accepted = await loadText(await file.text(), file.name, epoch);
    if (accepted) {
      let option = $('example-select').querySelector('option[value="__import__"]');
      if (!option) { option = document.createElement('option'); option.value = '__import__'; $('example-select').append(option); }
      option.textContent = file.name; activeChoice = '__import__'; $('example-select').value = activeChoice;
      $('example-description').textContent = 'Local import. This render stays in your browser; no file is uploaded.';
    }
  } catch (error) { if (epoch === loadEpoch) message(error.message, true); }
  event.target.value = '';
});

$('play-button').addEventListener('click', async () => {
  if (!loaded) return;
  if (!audio.paused) audio.pause();
  else { try { if (audio.currentTime >= loaded.wave.duration - 0.001) audio.currentTime = 0; await audio.play(); } catch (error) { message(`Playback could not start: ${error.message}. The original WAV can still be downloaded.`, true); } }
});
audio.addEventListener('play', () => { $('play-icon').textContent = 'Ⅱ'; $('play-button').setAttribute('aria-label', 'Pause render'); requestTick(); });
audio.addEventListener('pause', () => { $('play-icon').textContent = '▶'; $('play-button').setAttribute('aria-label', 'Play render'); requestTick(); });
audio.addEventListener('ended', () => { $('play-icon').textContent = '▶'; $('play-button').setAttribute('aria-label', 'Play render'); requestTick(); });
audio.addEventListener('seeked', requestTick);
audio.addEventListener('loadedmetadata', requestTick);
audio.addEventListener('error', () => { if (loaded) message('This browser cannot decode the exported WAV for playback. Download the original WAV or use a browser supporting PCM/Float32 WAV.', true); });
function seek(time) {
  if (!loaded) return;
  time = Math.max(0, Math.min(time, loaded.wave.duration));
  if (audio.readyState >= 1) audio.currentTime = time;
  timeState(time);
}
$('seek').addEventListener('input', event => seek(Number(event.target.value)));
for (const id of ['wave-canvas', 'force-canvas', 'pressure-canvas', 'energy-canvas']) $(id).addEventListener('click', event => {
  if (!loaded) return;
  const rect = event.currentTarget.getBoundingClientRect();
  seek((event.clientX - rect.left - 40) / (rect.width - 48) * loaded.wave.duration);
});
function updateVolume() { const gain = Number($('volume').value); audio.volume = 10 ** (gain / 20); $('volume-output').textContent = `${gain < 0 ? '−' : ''}${Math.abs(gain)} dB`; }
$('volume').addEventListener('input', updateVolume); updateVolume();

function download(data, filename, type) {
  const url = URL.createObjectURL(data instanceof Blob ? data : new Blob([data], {type}));
  const anchor = document.createElement('a'); anchor.href = url; anchor.download = filename; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 30000);
}
$('download-wav').addEventListener('click', () => { if (loaded) download(new Blob([loaded.bytes], {type: 'audio/wav'}), 'render.wav'); });

function updateSceneEditor(syncControls = true) {
  try {
    const scene = validateScene($('scene-json').value);
    if (syncControls) { $('scene-preset').value = scene.preset; $('scene-side').value = scene.side; $('scene-duration').value = scene.duration_s; }
    const edited = JSON.stringify(scene, null, 2) !== originalScene;
    $('edit-status').textContent = edited ? 'Edited · native re-render required' : 'Original rendered scene';
    $('edit-status').style.color = edited ? 'var(--orange)' : 'var(--cyan)';
    $('download-scene').disabled = false;
    return scene;
  } catch (error) { $('edit-status').textContent = error.message; $('edit-status').style.color = 'var(--orange)'; $('download-scene').disabled = true; return null; }
}
$('scene-json').addEventListener('input', () => updateSceneEditor());
for (const [id, field] of [['scene-preset', 'preset'], ['scene-side', 'side'], ['scene-duration', 'duration_s']]) $(id).addEventListener('change', event => {
  try {
    const scene = JSON.parse($('scene-json').value);
    scene[field] = field === 'duration_s' ? Number(event.target.value) : event.target.value;
    $('scene-json').value = JSON.stringify(scene, null, 2); updateSceneEditor(false);
  } catch { message('Fix the scene JSON before using the parameter controls.', true); }
});
$('download-scene').addEventListener('click', () => { const scene = updateSceneEditor(); if (scene) download(`${JSON.stringify(scene, null, 2)}\n`, 'scene.json', 'application/json'); });
$('reset-scene').addEventListener('click', () => { $('scene-json').value = originalScene; updateSceneEditor(); });
$('copy-command').addEventListener('click', async () => { try { await navigator.clipboard.writeText($('render-command').textContent); $('copy-command').textContent = 'Copied'; setTimeout(() => { $('copy-command').textContent = 'Copy'; }, 1500); } catch { message('Clipboard access is unavailable. Select and copy the command shown below the scene editor.'); } });

const plotResize = new ResizeObserver(() => drawCharts(audio.currentTime));
for (const id of ['wave-canvas', 'force-canvas', 'pressure-canvas', 'energy-canvas']) plotResize.observe($(id));
drawCharts();

async function initExamples() {
  const epochBeforeFetch = loadEpoch;
  try {
    const response = await fetch('./examples/index.json');
    if (!response.ok) throw new Error('No bundled examples are available yet. Import a native .ku100.json export, or generate the examples locally.');
    examples = normalizeManifest(await response.json());
    const imported = $('example-select').querySelector('option[value="__import__"]');
    $('example-select').replaceChildren();
    for (const example of examples) { const option = document.createElement('option'); option.value = example.id; option.textContent = example.title; $('example-select').append(option); }
    if (imported) $('example-select').append(imported);
    if (!examples.length) { const option = document.createElement('option'); option.value = ''; option.textContent = 'Import a native render'; $('example-select').append(option); }
    if (epochBeforeFetch === loadEpoch && examples.length) await loadExample(examples[0]);
    else $('example-select').value = activeChoice;
  } catch (error) {
    if (!loaded) { $('example-select').replaceChildren(); const option = document.createElement('option'); option.textContent = 'Import a native render'; option.value = ''; $('example-select').append(option); message(error.message); }
  }
}
initExamples();
