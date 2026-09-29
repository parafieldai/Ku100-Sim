# Dataset research and applicability

Research checked 29 September 2026. Read-only retrieval scripts preserve source revisions, URLs, byte hashes, file schemas and access failures. Public metadata and a repository-level license are not assumed to establish rights or calibration for every linked performance. No downloaded performance is part of runtime synthesis or the public preview.

| Resource | Inspected evidence and use | Boundary |
|---|---|---|
| [OOPPEENN/ASMR_Dataset](https://huggingface.co/datasets/OOPPEENN/ASMR_Dataset) | Pinned dataset card and file listing. | Its pipeline explicitly removes saliva sounds and separates channels. Rejected as a wet-contact stereo calibration source. |
| [nyuuzyou/asmr](https://huggingface.co/datasets/nyuuzyou/asmr) | Card, revision and schema; transcribed 24 kHz speech/vocal clips. | Nonspeech was filtered out. No measured contact-force or KU100 identity field was established. |
| [Leying/DeepASMR-dataset](https://huggingface.co/datasets/Leying/DeepASMR-dataset) | Card, revision and listed transcript/speaker/episode/audio fields. | Speech data is not paired mechanical evidence; the stated CC BY-NC license also limits use. No audio trial downloaded here. |
| [OmniAICreator/ASMR-Archive-Processed](https://huggingface.co/datasets/OmniAICreator/ASMR-Archive-Processed) | Pinned processing card and archive listing. | A large processed archive is not a calibrated force-to-stereo contact experiment. No trial was accepted as such. |
| [Kaggle ASMR search](https://www.kaggle.com/datasets?search=asmr) | Public API response retrieved. The inspected ASMR YouTube channels result is labeled YouTube analytics. | Channel analytics is not acoustic/mechanical waveform data. This bounded search is not a claim that all Kaggle datasets were exhausted. |
| [Cluster Haptic Texture Dataset](https://doi.org/10.6084/m9.figshare.29438288) | Figshare v5 record, CC BY 4.0 license, archive directory inspection and a verified raw paired trial from the full release. | Rubber/surface sliding, not wet tongue/ear contact. Raw channel 0 is contact plus machine noise; channel 1 is the machine-noise reference, NOT the opposite ear. |
| [Leeds salivary lubricity](https://archive.researchdata.leeds.ac.uk/674/) | Institutional record describes numerical figure data, DOI 10.5518/816. | Tribology prior, not synchronized microphone pressure. Spreadsheet data was not newly downloaded by this audit. |
| [Leeds biomimetic tongue](https://archive.researchdata.leeds.ac.uk/757/) | Institutional data record, DOI 10.5518/917. | Surrogate material/topography evidence, not a KU100 force/acoustic transfer measurement. |
| [MRSAudio](https://mrsaudio.github.io/) | Authors describe synchronized spatial audio, video and trajectories. | Useful spatial-recording lead; no instrumented wet-contact trial inspected here. |

The [Cluster authors' data descriptor](https://www.nature.com/articles/s41597-026-06760-z) is particularly relevant because it records audio, force, acceleration and position for controlled motions. But its raw dual microphone arrangement is not binaural. Its force converter is described as 80 Hz even though values are transported/logged at 6 kHz, so the latter must not be mistaken for independent force-measurement bandwidth. Processed audio uses noise cancellation, which must also be accounted for before spectral comparison.

A separate 2026 experiment, [Screeching sound of peeling tape](https://doi.org/10.1103/p19h-9ysx), synchronizes microphone recordings with high-speed observations of fracture events. It illustrates why identifying an actual sound-generating event matters. Its fast adhesive fractures are not evidence that the same mechanism dominates slow wet artificial-ear contact; we do not transplant its shock model into this simulator.

## Retrieval commands

```sh
python scripts/audit_datasets.py
python scripts/inspect_cluster_trial.py
```

Both scripts are read-only, bound downloads, record failures, and do not execute downloaded code. The first inspected the processed mini archive; that did not contain the required raw paired path. The second explicitly selects the full release. It successfully retrieved trial `0_0_20_1000_0`: 216,395 stereo PCM16 audio frames at 44.1 kHz (4.9069 s), a matching processed mono WAV, 42,500 force rows, 42,500 acceleration rows and 493 position rows. All five member hashes were verified locally. The source file represents nominal 20 mm/s, 1 N dry sliding, not this simulator's 0.01 N generic ear fixture.

[The checked trial summary](../validation/dataset-paired-trial.json) records actual logging intervals, repeated force samples and raw-versus-processed spectra. The force CSV has repeated values: a dense timestamp series must not be labeled an equally high-bandwidth force measurement. Reproduce the summary using `python scripts/summarize_paired_trial.py PATH_TO_PAIRED_TRIAL --out trial-summary.json`. No source WAV or sensor array is committed or included in the site. The whole 15.2 GB archive was not downloaded or independently hash-verified; the accessed ZIP ranges and each extracted member were checked.

The near-field KU100 bank already used by this repository remains useful for airborne transfer. No resource inspected here establishes the complete wet contact → microphone chain. The practical next data work is a matched, bandwidth-qualified contact experiment, not indiscriminate expansion of speech-ASMR downloads.

In this inspected trial, 99.9247% of adjacent logged force values are identical. Raw contact-channel power below 250 Hz is 97.46% of its 20–20000 Hz power; after the dataset's noise cancellation it is 1.38%. These are measurements of this one trial and its processing, not a claim that the removed low-frequency content was all irrelevant. The processed spectrum must not be used as an unqualified physical target. In particular, high-frequency residuals at low signal levels can also reflect noise or quantization.

Dataset attribution: Michikuni Eguchi, Tomohiro Hayase, Yuichi Hiroi and Takefumi Hiraki, *Cluster Haptic Texture Dataset*, version 5, DOI 10.6084/m9.figshare.29438288.v5, CC BY 4.0. The checked summary is derived from one trial; the renderer does not consume that trial.
