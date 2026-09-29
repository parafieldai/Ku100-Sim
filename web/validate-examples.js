/** Apply the exact browser intake contract to every generated site example. */
import {readFile} from 'node:fs/promises';
import {webcrypto} from 'node:crypto';
import {normalizeManifest, validateBundle, verifyAudioHash} from './core.js';

const root = new URL('./examples/', import.meta.url);
const manifest = normalizeManifest(JSON.parse(await readFile(new URL('index.json', root), 'utf8')));
if (!manifest.length) throw new Error('Generate at least one native example before publication.');
for (const example of manifest) {
  const validated = validateBundle(JSON.parse(await readFile(new URL(example.path, root), 'utf8')));
  await verifyAudioHash(validated, webcrypto);
  console.log(`${example.id}: ${validated.wave.frames} stereo frames, ${validated.bundle.trace.rows.length} trace rows, SHA-256 verified`);
}
