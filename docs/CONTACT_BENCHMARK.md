# Additional native contact-coupon benchmark

A separate, executed research benchmark is available in [`benchmarks/contact-coupon`](../benchmarks/contact-coupon/INTEGRATION.md). It complements, and does not replace, the main native renderer or private Pages configuration.

It includes a C++17 coupled plate/contact/cavity/radiation model, a measured KU100 airborne fixture with provenance, an independently assembled continuous-ODE reference, native sanitizer checks, an unfitted rigid-sphere comparison, and a native-output web viewer.

Its local evidence records 67 native acceptance checks, 13 sanitizer-exercised invariants and seven offline Chromium checks. It also preserves important failures: the default integration setting misses a strict late-decay target, structural refinement is not complete, and the generated source is not validated as realistic wet-ear ASMR. These results are scoped to the benchmark source hash; they are not test results for the main renderer.

See [benchmark validation](../benchmarks/contact-coupon/docs/VALIDATION.md), [research sources](../benchmarks/contact-coupon/docs/RESEARCH.md), and [machine-readable evidence](../benchmarks/contact-coupon/research/summary.json). The full reports can be regenerated with the commands in its README. User reference performances are not included as runtime assets.

The benchmark was integrated after a concurrent native implementation landed on main. No existing main-path file was replaced. The standalone experimental branch remains `native-physics-audit` for its original development history.
