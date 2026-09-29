"""Independent native receiver audit: synthetic fixtures, NumPy and SciPy.

Run from the repo root: python -m unittest discover -s tests -p test_receiver.py -v
The temporary C++ probe links only receiver.cpp. No reference audio is used.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

import numpy as np
from scipy import signal
from scipy.io import wavfile

ROOT = Path(__file__).resolve().parents[1]


def encode_bank(radii, ir, *, rate=48000, directions=360, taps=None):
    """Independent explicit little-endian encoder for KUHRIR01 test fixtures."""
    ir = np.asarray(ir, dtype='<f4')
    taps = ir.shape[-1] if taps is None else taps
    return (struct.pack('<8s4I', b'KUHRIR01', rate, len(radii), directions, taps)
            + np.asarray(radii, dtype='<f8').tobytes() + ir.tobytes())


def fractional_fir(fraction):
    # NumPy's normalized sinc and independent SciPy Kaiser window implement the
    # declared 63-tap interpolator, without copying the native Bessel routine.
    h = np.sinc(np.arange(63) - 31 - fraction) * signal.windows.kaiser(63, 9.0, sym=True)
    return h / h.sum()


def delayed_reference(x, samples):
    if not len(x):
        return np.array([])
    integer = math.floor(samples)
    h = fractional_fir(samples - integer)
    return np.pad(signal.convolve(x, h, mode='full', method='direct'), (integer, 0))


class NativeReceiverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='ku100-receiver-audit-')
        cls.work = Path(cls.temporary.name)
        cls.probe = cls.work / 'receiver-probe'
        command = [os.environ.get('CXX', 'g++'), '-std=c++17', '-O2', '-Wall', '-Wextra', '-Wpedantic',
                   '-I', str(ROOT / 'native'), str(ROOT / 'native/receiver.cpp'),
                   str(ROOT / 'tests/receiver_probe.cpp'), '-o', str(cls.probe)]
        built = subprocess.run(command, capture_output=True, text=True, check=False)
        if built.returncode:
            raise RuntimeError('Receiver probe failed to compile:\n' + built.stderr)
        cls.compile_stderr = built.stderr
        cls.observations = {}
        # Every dimension carries a distinguishable value; equality tests also
        # catch a receiver/azimuth/tap stride or channel-order error.
        cls.ir = np.empty((2, 360, 2, 5), dtype=np.float32)
        for ring in range(2):
            for azimuth in range(360):
                for ear in range(2):
                    cls.ir[ring, azimuth, ear] = (
                        (ring + 1) * .125 + azimuth * .000125 + ear * .03125
                        + np.arange(5) * .0078125)
        cls.radii = np.array([.25, 1.0])
        cls.bank = cls.work / 'valid-bank.bin'
        cls.bank.write_bytes(encode_bank(cls.radii, cls.ir))
        cls.serial = 0

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def text_signal(self, values):
        type(self).serial += 1
        path = self.work / f'signal-{self.serial}.txt'
        np.savetxt(path, np.asarray(values, dtype=float), fmt='%.17g')
        return path

    def call(self, *args, rejected=False):
        result = subprocess.run([str(self.probe), *map(str, args)], capture_output=True, text=True,
                                timeout=30, check=False)
        if rejected:
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertTrue(result.stderr.strip())
            return result.stderr.strip()
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def assert_samples(self, actual, expected, *, atol=2e-13, rtol=2e-13):
        actual, expected = np.asarray(actual), np.asarray(expected)
        self.assertEqual(actual.shape, expected.shape)
        observed = self.observations.setdefault(self._testMethodName, {'comparisons': 0, 'max_absolute_error': 0.0})
        observed['comparisons'] += 1
        if actual.size:
            observed['max_absolute_error'] = max(observed['max_absolute_error'],
                                                 float(np.max(np.abs(actual - expected))))
        np.testing.assert_allclose(actual, expected, atol=atol, rtol=rtol)

    def at_reference(self, azimuth, radius):
        angle = azimuth % 360
        lo = math.floor(angle)
        frac = angle - lo
        ring_weight = math.log(radius / .25) / math.log(1.0 / .25)
        rings = ((1 - frac) * self.ir[:, lo].astype(float)
                 + frac * self.ir[:, (lo + 1) % 360].astype(float))
        return (1 - ring_weight) * rings[0] + ring_weight * rings[1]

    def test_bank_header_and_exact_measurement_samples(self):
        self.assertEqual(self.call('load', self.bank),
                         {'rate': 48000, 'directions': 360, 'taps': 5, 'radii': [.25, 1.0]})
        for ring, radius in enumerate(self.radii):
            for angle in (0, 90, 180, 270, 359):
                with self.subTest(ring=ring, angle=angle):
                    actual = self.call('at', self.bank, angle, radius)
                    self.assert_samples([actual['left'], actual['right']], self.ir[ring, angle], atol=0, rtol=0)

    def test_angle_wrap_and_log_radius_interpolation_preserve_both_ears(self):
        for angle in (-720.5, -.5, .25, 89.5, 270.75, 359.5, 720.25):
            for radius in (.25, .4, .5, .9, 1.0):
                with self.subTest(angle=angle, radius=radius):
                    actual = self.call('at', self.bank, angle, radius)
                    self.assert_samples([actual['left'], actual['right']], self.at_reference(angle, radius))

    def test_one_ring_is_supported_without_radial_division(self):
        path = self.work / 'one-ring.bin'
        path.write_bytes(encode_bank([.25], self.ir[:1]))
        actual = self.call('at', path, 12.25, .25)
        expected = .75 * self.ir[0, 12].astype(float) + .25 * self.ir[0, 13]
        self.assert_samples([actual['left'], actual['right']], expected)

    def test_negative_epsilon_azimuth_does_not_index_direction_360(self):
        # Adding 360 to a tiny negative fmod result can round to exactly 360.
        # Direction 360 would read the next radius (or beyond the final ring).
        # At this scale the correct samples equal direction zero to tolerance.
        for angle in (-1e-15, -1e-14):
            for ring, radius in enumerate(self.radii):
                with self.subTest(angle=angle, radius=radius):
                    actual = self.call('at', self.bank, angle, radius)
                    self.assert_samples([actual['left'], actual['right']], self.ir[ring, 0])

    def test_rejects_truncated_trailing_and_nonfinite_bank_bytes(self):
        body = self.bank.read_bytes()
        altered = self.ir.copy()
        altered[0, 0, 0, 0] = np.nan
        cases = {'short_magic': b'KUHR', 'bad_magic': b'BADMAGIC' + body[8:],
                 'short_header': body[:20], 'short_radii': body[:30],
                 'short_samples': body[:-1], 'extra_byte': body + b'0',
                 'nan_sample': encode_bank(self.radii, altered)}
        for name, content in cases.items():
            with self.subTest(case=name):
                path = self.work / f'{name}.bin'
                path.write_bytes(content)
                self.call('load', path, rejected=True)

    def test_rejects_invalid_bank_shapes_and_radii(self):
        cases = {'wrong_rate': encode_bank(self.radii, self.ir, rate=44100),
                 'wrong_directions': encode_bank(self.radii, self.ir, directions=180),
                 'zero_taps': encode_bank(self.radii, self.ir, taps=0),
                 'zero_rings': encode_bank([], self.ir),
                 'negative_radius': encode_bank([-.25, 1], self.ir),
                 'duplicate_radius': encode_bank([.25, .25], self.ir),
                 'descending_radius': encode_bank([1, .25], self.ir),
                 'nan_radius': encode_bank([np.nan, 1], self.ir),
                 'inf_radius': encode_bank([.25, np.inf], self.ir),
                 'excessive_allocation': struct.pack('<8s4I', b'KUHRIR01', 48000, 32, 360, 8192)}
        for name, content in cases.items():
            with self.subTest(case=name):
                path = self.work / f'{name}.bin'
                path.write_bytes(content)
                self.call('load', path, rejected=True)

    def test_rejects_extrapolation_and_nonfinite_coordinates(self):
        for angle, radius in ((0, .249), (0, 1.001), (0, 0), (np.inf, .5),
                              (np.nan, .5), (0, np.inf), (0, np.nan)):
            with self.subTest(angle=angle, radius=radius):
                self.call('at', self.bank, angle, radius, rejected=True)

    def test_direct_convolution_matches_numpy_and_keeps_final_tail_sample(self):
        rng = np.random.default_rng(411)
        for x, h in (([1, -2, 3], [.5, -.25]), (rng.normal(size=73), rng.normal(size=19)),
                     ([0, 0, 1], [0, 0, 2]), ([], [1]), ([1], [])):
            actual = self.call('convolve', self.text_signal(x), self.text_signal(h))
            expected = np.convolve(x, h) if len(x) and len(h) else []
            self.assert_samples(actual, expected)

    def test_decimation_matches_scipy_causal_full_tail_and_latency(self):
        rng = np.random.default_rng(907)
        for rate in (48000, 96000, 192000, 384000, 768000):
            factor = rate // 48000
            for x in ([1.0], [0, 0, 1], rng.normal(size=157), []):
                with self.subTest(rate=rate, frames=len(x)):
                    result = self.call('decimate', rate, 48000, self.text_signal(x))
                    if factor == 1 or not len(x):
                        expected = x
                    else:
                        h = signal.firwin(128 * factor + 1, 20000, fs=rate, window=('kaiser', 9), scale=True)
                        expected = signal.upfirdn(h, x, down=factor)
                    self.assert_samples(result['samples'], expected)
                    self.assertEqual(result['delay_s'], 0 if factor == 1 else 64 / 48000)
                    if len(x) == 1 and factor > 1:
                        self.assertEqual(np.argmax(result['samples']), 64)

    def test_decimation_rejects_alias_band_with_shared_passband_gain(self):
        rate = 192000
        t = np.arange(rate // 10) / rate
        amplitudes = {}
        for frequency in (1000, 10000, 30000, 70000):
            result = self.call('decimate', rate, 48000, self.text_signal(np.sin(2 * np.pi * frequency * t)))
            y = np.asarray(result['samples'])[256:-256]
            amplitudes[frequency] = float(np.sqrt(2 * np.mean(y * y)))
        self.observations[self._testMethodName] = {'output_rms_equivalent_sine_amplitude': amplitudes}
        self.assertAlmostEqual(amplitudes[1000], 1, delta=.002)
        self.assertAlmostEqual(amplitudes[10000], 1, delta=.002)
        self.assertLess(amplitudes[30000], 1e-5)
        self.assertLess(amplitudes[70000], 1e-5)

    def test_decimation_rejects_unsupported_rates(self):
        path = self.text_signal([1])
        for rates in ((0, 48000), (44100, 48000), (144001, 48000), (96000, 44100), (816000, 48000)):
            self.call('decimate', *rates, path, rejected=True)

    def test_fractional_delay_matches_independent_kernel_without_tail_loss(self):
        x = np.array([1, -.2, .5, 0, -.7])
        for samples in (0, .1, .5, .99, 1, 11.375, 50):
            with self.subTest(samples=samples):
                result = self.call('delay', samples, self.text_signal(x))
                self.assert_samples(result, delayed_reference(x, samples))
                self.assertEqual(len(result), len(x) + 62 + math.floor(samples))
        self.assertEqual(self.call('delay', 1.5, self.text_signal([])), [])

    def test_integer_boundary_has_constant_31_sample_latency(self):
        impulse = self.text_signal([1])
        for delay in (0, 1, 2, 10):
            result = np.asarray(self.call('delay', delay, impulse))
            self.assertEqual(int(np.argmax(np.abs(result))), delay + 31)
            self.assertAlmostEqual(float(result.sum()), 1, places=13)
        around = [np.asarray(self.call('delay', d, impulse)) for d in (1 - 1e-8, 1, 1 + 1e-8)]
        length = max(map(len, around))
        around = [np.pad(x, (0, length - len(x))) for x in around]
        self.observations[self._testMethodName] = {
            'max_sample_difference_below_boundary': float(np.max(np.abs(around[0] - around[1]))),
            'max_sample_difference_above_boundary': float(np.max(np.abs(around[2] - around[1])))}
        self.assertLess(float(np.max(np.abs(around[0] - around[1]))), 2e-8)
        self.assertLess(float(np.max(np.abs(around[2] - around[1]))), 2e-8)

    def test_delay_phase_and_gain_below_declared_audio_cutoff(self):
        samples = 4.375
        h = np.asarray(self.call('delay', samples, self.text_signal([1])))
        # Frequency-domain identity tests actual delay, not only a coefficient comparison.
        w = 2 * np.pi * np.array([100, 1000, 10000, 18000]) / 48000
        _, response = signal.freqz(h, worN=w)
        expected = np.exp(-1j * w * (samples + 31))
        self.observations[self._testMethodName] = {
            'max_complex_response_error': float(np.max(np.abs(response / expected - 1)))}
        self.assertLess(float(np.max(np.abs(response / expected - 1))), 1e-4)

    def test_airborne_matches_delay_convolution_and_does_not_reapply_inverse_radius(self):
        x = np.array([.1, -.2, .03, .12])
        for azimuth, radius in ((0, .25), (89.25, .5), (270, 1.0)):
            with self.subTest(azimuth=azimuth, radius=radius):
                actual = self.call('airborne', self.bank, azimuth, radius, 343, self.text_signal(x))
                delayed = delayed_reference(x, radius / 343 * 48000)
                h = self.at_reference(azimuth, radius)
                expected = [np.convolve(delayed, channel) for channel in h]
                self.assert_samples([actual['left'], actual['right']], expected)

    def test_nonfinite_samples_and_invalid_delay_or_speed_are_rejected(self):
        valid = self.text_signal([1])
        for bad in (np.nan, np.inf, -np.inf):
            bad_input = self.text_signal([bad])
            self.call('convolve', bad_input, valid, rejected=True)
            self.call('delay', 1, bad_input, rejected=True)
            self.call('decimate', 192000, 48000, bad_input, rejected=True)
        for delay in (-.1, np.nan, np.inf, 480001):
            self.call('delay', delay, valid, rejected=True)
        for speed in (0, 249, 451, np.nan, np.inf):
            self.call('airborne', self.bank, 0, .25, speed, valid, rejected=True)

    def test_float_wav_bytes_preserve_stereo_levels_polarity_and_above_full_scale(self):
        left = np.array([0, .125, -.5, 1.25, -2.5, np.finfo(np.float32).tiny])
        right = np.array([.5, -.0625, 0, -1.75, 3, -np.finfo(np.float32).tiny])
        path = self.work / 'float-stereo.wav'
        self.call('wav', path, 48000, self.text_signal(left), self.text_signal(right))
        body = path.read_bytes()
        self.assertEqual(body[:4], b'RIFF')
        self.assertEqual(struct.unpack_from('<I', body, 4)[0] + 8, len(body))
        self.assertEqual(body[8:12], b'WAVE')
        chunks = {}
        pos = 12
        while pos < len(body):
            name, length = struct.unpack_from('<4sI', body, pos)
            self.assertNotIn(name, chunks)
            chunks[name] = body[pos + 8:pos + 8 + length]
            pos += 8 + length + (length % 2)
        self.assertEqual(pos, len(body))
        self.assertEqual(struct.unpack('<HHIIHHH', chunks[b'fmt ']), (3, 2, 48000, 384000, 8, 32, 0))
        self.assertEqual(struct.unpack('<I', chunks[b'fact']), (len(left),))
        expected = np.column_stack((left, right)).astype('<f4')
        self.assertEqual(chunks[b'data'], expected.tobytes())
        rate, actual = wavfile.read(path)
        self.assertEqual(rate, 48000)
        np.testing.assert_array_equal(actual, expected)

    def test_wav_rejects_invalid_rate_channels_and_float_overflow(self):
        path = self.work / 'invalid.wav'
        left, right = self.text_signal([1, 2]), self.text_signal([1])
        self.call('wav', path, 48000, left, right, rejected=True)
        self.call('wav', path, 7999, left, left, rejected=True)
        self.call('wav', path, 48000, self.text_signal([np.nan]), right, rejected=True)
        self.call('wav', path, 48000, self.text_signal([1e100]), right, rejected=True)

    def test_real_bank_when_available_matches_selected_binary_measurements(self):
        # The prepared bank is optional while source acquisition is in progress.
        paths = sorted(p for directory in ('data', 'assets')
                       for p in (ROOT / directory).glob('*.bin'))
        paths = [p for p in paths if p.read_bytes()[:8] == b'KUHRIR01']
        if not paths:
            self.skipTest('prepared KU100 measurement bank not present yet')
        for path in paths:
            body = path.read_bytes()
            magic, rate, rings, directions, taps = struct.unpack_from('<8s4I', body)
            radii = np.frombuffer(body, dtype='<f8', count=rings, offset=24)
            measurements = np.frombuffer(body, dtype='<f4', offset=24 + rings * 8).reshape(rings, directions, 2, taps)
            self.assertEqual(self.call('load', path)['radii'], radii.tolist())
            for ring in range(rings):
                for azimuth in (0, 90, 180, 270, 359):
                    actual = self.call('at', path, azimuth, radii[ring])
                    self.assert_samples([actual['left'], actual['right']], measurements[ring, azimuth], atol=0, rtol=0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
