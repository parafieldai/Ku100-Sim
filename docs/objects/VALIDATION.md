# Object experiment: executed development and acceptance boundary

This revision adds a data-assisted tapping experiment, not new wet-ear mechanics.
See [RESEARCH.md](RESEARCH.md) for exact source/model/test scope.

## Local checks

15 new tests cover the stable recurrence against its analytical response,
independent matrix-exponential state and energy, relative impulse scaling,
finite-pulse convolution, exact silence, parameter rejection, two-frequency
synthetic fitting recovery, parameter-only rendering with file reads blocked,
three distinct object profiles, and strict generated-only PCM16 publication.

The full prior float32 native bundle contract is unchanged. The new publication
validator requires canonical PCM16 stereo at 48 kHz, declared frame count and
hash, identical channels, nonzero data and bounded peak; it refuses private files,
extra chunks/trailing bytes, symlinks, malformed formats and unsupported physical
claims. The completed site remains below the original 80 MiB limit.

The first local browser invocation reached all 13 asset URLs and verified their
bytes, then Chromium refused navigation with `ERR_BLOCKED_BY_ADMINISTRATOR`.
That run is NOT a browser-playback pass. No security policy was changed. The
same browser test is included in GitHub CI and live verification; their actual
results must be checked before claiming deployment.

## Real-world evaluation

The first modal-only prototype was insufficient for wood and for transferring the
glass response. A parameterized stochastic transient layer improved those training
fits and was selected using training data only. It worsened the ceramic training
score and was not selected for ceramic. Current diagnostics pass 7/9 development
position cases, retaining the farthest ceramic and glass spectral failures.
No human listening scores have been entered and no cross-position loudness or
complete microphone model has been validated.

## Source identity and generation

The new models contain 24 damped modes each; wood/glass also contain 16 by 4
nonnegative band-variance weights with fixed decays. They do not contain PCM or
recorded residual buffers. Unlike the old texture models, modal residues retain
parametric phase. This is data-assisted synthesis, not a claim that real audio
was irrelevant or that every source mechanism was identified from first principles.

CI builds the exact new files alongside the previous examples; Pages publishes
only that tested site artifact. The post-deployment browser test compares all
13 object assets to the tested bytes, exercises each of the nine audio files,
checks playback, completed seeking, original downloads, exclusive playback,
Stop all and mobile/desktop layouts. Those are delivery tests, not listener tests.

## Browser PCM conversion audit

The first complete cloud object test passed 145 Python/native tests and all
13 asset hashes, but found a 0.00001335144 maximum difference between browser
PCM16 decoding and explicit sample-code/32768 conversion on the first file.
It was not recorded as a successful browser test. The original PCM16 WAVs stay
unchanged for downloads. The page now converts those verified codes explicitly
to a Float32 preview before playback. The browser test still requires zero
sample difference against the original PCM codes, while reporting the direct
PCM decoder difference separately. It does not loosen the sample-identity
assertion or alter the source model. No perceptual consequence is claimed.

The earlier temporary validation workflow also failed dependency installation
because combining two requirements files applied the PyTorch package index to
SciPy. Installing the existing requirements separately fixed the setup; no
numerical dependency version or test threshold was changed.

The next browser run verified all nine decoded previews, seeks and original
downloads, but caught overlapping playback while the asynchronous play event
was still queued. The Play button now pauses the other players synchronously
before starting its own audio; the play-event guard remains for native controls.
The exclusive-playback assertion is unchanged.
