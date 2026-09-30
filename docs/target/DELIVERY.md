# Build, review and publish the target comparison

## Status of this delivery

This update was implemented in local Git on `target-listening`. The GitHub
connection exposed read operations but no commit/push operation; there was no
authenticated GitHub CLI in the runtime. **No remote branch or live Pages update
was made in this work.** The previously verified remote main was
`42472a45d2cb2b786993cea0d6cacb57b74e2981`.

The local source bundle base is `f578d1ff8c247e745d59261834702bd28579bcae`.
GitHub compare confirmed only four unrelated files changed between that base and
the then-current main: the live verification workflow/script, research index and
cloud audit receipt. This patch does not overwrite those files. Apply it to an
up-to-date working copy with normal Git conflict checks; do not force a push.

## Reproduce the generated-only public build

```bash
python -m pip install -r requirements.txt
python scripts/build_native.py
python scripts/prepare_ku100.py --download
python scripts/generate_examples.py
python scripts/build_target_study.py
python scripts/assess_target_study.py
python -m unittest discover -s tests -v
npm ci --prefix web
npm --prefix web test
python scripts/build_site.py
npx --prefix web playwright install --with-deps chromium
node scripts/browser_target.mjs
```

The builders refuse unexpected or private files. A prior target build must be
removed explicitly from its known `web/target/generated` location before
regeneration. Do not remove original models, reference reports or user audio to
get past a freeze/overwrite guard.

`dist/target/` contains the study, generated audio and local-import interface.
`dist/` retains the original engineering viewer and now links to the target
comparison with a target-failure warning. The modified native CI builds and checks
both pages before the existing Pages workflow publishes the tested `dist` artifact.
The new target live-check workflow compares its public assets to that exact CI
artifact. Those remote workflows have not run for this unpushed local change.

## Private immediate listening

```bash
python scripts/package_target_preview.py --input-root /path/to/original-wavs \
  --out /path/outside/repository/Ku100-Target-Comparison-PRIVATE.html
```

This separate file includes 24 seconds of exact user-provided reference audio.
It is only for the user's review. **Do not add it to Git, `web`, `dist`, a public
release or a public Pages artifact.** Public reference import is local-only and
uses full-source hashes plus exact crop samples. The interface never uploads the
source file or the listener's notes. Download result JSON to retain observations.

## What was actually tested locally

Normal localhost HTTP navigation and `file:` navigation were both refused by the
browser environment with `ERR_BLOCKED_BY_ADMINISTRATOR`. No browser security policy
was disabled. Tests then loaded the self-authored, self-contained private HTML
into an in-memory document and exercised actual audio, hash-checked downloads,
ratings, source reveal and layouts. This is **not** a successful HTTP, file-open,
GitHub Actions or deployed-site test. The public HTTP test remains available for
an ordinary browser runner and future CI.

The private browser test validates actual supplied crop hashes. The public CI
reference-import test instead uses a clearly identified synthetic stereo fixture,
because private source recordings are intentionally not in the repository. It
must not be represented as a CI listening assessment on real contact recordings.
Automated test ratings are test inputs, not human listening judgments.

## Git publication

Apply the supplied format-patch in a working copy that is authenticated for writes:

```bash
git switch main
git pull --ff-only
git am /path/to/Ku100-Target-Listening.patch
git push origin main
```

The existing main CI → Pages → live-check chain should then run. Verify all jobs
and the actual `/Ku100-Sim/target/` URL; a prepared zip, successful local unit test,
or skipped deploy does not mean the live site changed. No target-realism pass is
implied by a successful delivery workflow.
