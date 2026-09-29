# Measured airborne receiver fixture

The repository vendors one 128-tap stereo response: azimuth 90 degrees, radius 0.25 m. It is sufficient to run the measured-route demo and independently verify native convolution without a network dependency. Its adjacent JSON preserves source attributes, raw channel positions, processing gain and hashes.

The local research also inspected both complete 360-direction SOFA circles at 0.25 m and 0.50 m and extracted six responses (0, 90, 270 degrees at each distance). Other bearings are not silently substituted by this fixture. Reproduce an additional response using the supplied original archives or the authors' dataset:

```sh
python tools/receiver.py /path/to/HRIR_CIRC360_NF050.sofa --azimuth 90 --out assets/ku100_0.50_90.txt
```

The extractor writes a new FIR and receipt and refuses to overwrite an existing one. Apply no additional filter gain: the authors' distance correction is already included. This is airborne measured impulse-response data, not a recorded ASMR performance used as excitation. See ../THIRD_PARTY_NOTICES.md for separate CC BY-SA 3.0 attribution.
