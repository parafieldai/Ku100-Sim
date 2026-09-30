# Pressure capture boundary audit

The initial pressure research note and commit `cfb9030` describe eight capture-component tests. A follow-up boundary check adds a ninth test; together with the six longer-generation/publication checks, 15 local tests pass.

At exactly one-half quantization step below positive full scale, round-to-even could produce +1.0, which is outside the signed PCM code range. The capture component now rejects that boundary as well as values beyond it. The new test injects the exact numerical boundary at the resampler output for 16- and 24-bit configurations. This is a software boundary test, not a physical microphone measurement. The negative-side guard remains conservative. No normalization or clipping is introduced.

The longer-page browser check now waits for the actual seek target and completion rather than only exercising the seek setter. It still checks actual playback, exact decoded samples and unchanged downloads.

The texture synthesis code, fitted parameters, generation seeds, listening gains and physical solver are unchanged by this follow-up. The Pa-input capture diagnostic is not applied to the uncalibrated texture audio. GitHub CI and live deployment results must be checked separately at their actual commit.
