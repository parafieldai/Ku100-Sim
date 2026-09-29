# Isolated contact-coupon benchmark

This directory preserves the separately tested native benchmark developed on `native-physics-audit`, commit `318602a368be33f440704e3fd1d32f20a3d9bd29`. While that work was underway, the main native implementation landed at `127f9093b5adb05e06eca67d7462c3a62adda1b2`. It is preserved unchanged by this integration.

The benchmark is intentionally separate from the main renderer: its assumed plates, cavities, contact law, units, parameter schema and tests are not automatically interchangeable with the main implementation. The numerical results here apply only to this benchmark's hashed source, not to every simulator in the repository.

Run this benchmark from its own directory:

```sh
cd benchmarks/contact-coupon
python -m pip install -r requirements.txt
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j2
python tests/verify.py
python tools/compare_receivers.py
python tools/sphere.py
python tools/build_site.py --out _site
```

The benchmark's original standalone workflow files are omitted from this nested copy. The repository's existing main simulator, CI and private Pages workflow are not replaced. A separate contact-benchmark workflow checks this directory. The offline viewer remains usable without Pages.

For a meaningful future cross-implementation comparison, first reconcile force, displacement, pressure and radiation-observation definitions. Reusing a 67-check pass label from this benchmark for the main engine would be incorrect. The useful portable checks are separately assembled linear dynamics, energy/potential identities, independently actuated mirror symmetry, FIR/convolution correctness, and explicit temporal/spatial refinement failures.
