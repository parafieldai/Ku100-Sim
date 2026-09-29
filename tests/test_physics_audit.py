"""Independent equation, port-work and native CLI tests for the physical fixture.

These tests use synthetic physical inputs. They do not use a performance
recording, a learned sound model, or a loudness-matching target.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from numpy.polynomial.hermite import hermgauss
from numpy.polynomial.legendre import leggauss
from scipy import integrate, linalg, optimize, signal
from scipy.io import wavfile

ROOT = Path(__file__).resolve().parents[1]

# Including the implementation in a temporary test translation unit exposes
# its anonymous-namespace equation helpers without changing the public API.
# This adapter contains no alternate implementation of the equations.
PROBE = r'''
#include "physics.cpp"
#include <iomanip>
#include <iostream>
int main(int argc,char** argv) {
    try {
        if(argc<2) return 2;
        ku100::PhysicsParams p;
        const std::string op=argv[1];
        std::cout << std::setprecision(17);
        if(op=="block") {
            if(argc!=11) return 2;
            unsigned m=std::stoul(argv[2]),n=std::stoul(argv[3]);
            p.young_modulus_pa=std::stod(argv[4]);p.poisson_ratio=std::stod(argv[5]);
            p.density_kg_m3=std::stod(argv[6]);p.plate_width_m=std::stod(argv[7]);
            p.plate_height_m=std::stod(argv[8]);p.plate_thickness_m=std::stod(argv[9]);
            p.contact_radius_m=std::stod(argv[10]);
            const auto modes=ku100::mindlin_block(p,m,n);
            std::cout << '[';
            for(unsigned i=0;i<3;++i){if(i)std::cout << ',';const auto& x=modes[i];
                std::cout << '['<<x.omega2<<','<<x.b<<','<<x.t<<','<<x.area<<']';}
            std::cout << ']';
        } else if(op=="modes") {
            if(argc!=3) return 2;
            p.modes_per_plate=std::stoul(argv[2]);double compliance;
            const auto modes=ku100::make_modes(p,compliance);
            std::cout << "{\"compliance\":" << compliance << ",\"modes\":[";
            for(unsigned i=0;i<modes.size();++i){if(i)std::cout << ',';const auto& x=modes[i];
                std::cout << '['<<x.omega2<<','<<x.b<<','<<x.t<<','<<x.area<<']';}
            std::cout << "]}";
        } else if(op=="gradient") {
            if(argc!=5) return 2;
            std::cout << ku100::spring_gradient(std::stod(argv[2]),std::stod(argv[3]),std::stod(argv[4]));
        } else if(op=="contact") {
            if(argc!=13) return 2;
            p.wetness=std::stod(argv[11]);
            auto x=ku100::contact_solve(std::stod(argv[2]),std::stod(argv[3]),std::stod(argv[4]),
                std::stod(argv[5]),std::stod(argv[6]),std::stod(argv[7]),std::stod(argv[8]),
                std::stod(argv[9]),std::stod(argv[10]),p,std::stod(argv[12]));
            std::cout << "{\"normal\":"<<x.normal<<",\"tangent\":"<<x.tangent
                      <<",\"vn\":"<<x.vn<<",\"vt\":"<<x.vt<<",\"delta\":"<<x.delta
                      <<",\"loss_rate\":"<<x.loss_rate<<",\"residual\":"<<x.residual<<'}';
        } else return 2;
        std::cout << '\n';
        return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 2;}
}
'''


def averaged_contact_force(a, b, stiffness):
    """Integrate the continuous Hertz force along the indentation segment."""
    crossing = -a / (b - a) if a != b else -1
    points = [crossing] if 0 < crossing < 1 else None
    return integrate.quad(lambda u: stiffness * max(0, (1-u)*a + u*b)**1.5,
                          0, 1, points=points, epsabs=2e-14, epsrel=2e-13)[0]


def block_by_energy_quadrature(p, m, n):
    """Assemble kinetic, bending and shear energies from spatial basis fields.

    Unlike the C++ block constructor, this integrates the physical fields and
    solves the resulting generalized symmetric eigenproblem with LAPACK.
    """
    width, height, thickness = (p[k] for k in ('plate_width_m', 'plate_height_m', 'plate_thickness_m'))
    young, nu, density = (p[k] for k in ('young_modulus_pa', 'poisson_ratio', 'density_kg_m3'))
    z, weight = leggauss(max(48, 4 * max(m, n) + 4))
    x, y = (z + 1) * width / 2, (z + 1) * height / 2
    xy_weight = np.outer(weight, weight) * width * height / 4
    alpha, beta = m*np.pi/width, n*np.pi/height
    ss = np.outer(np.sin(alpha*x), np.sin(beta*y))
    cs = np.outer(np.cos(alpha*x), np.sin(beta*y))
    sc = np.outer(np.sin(alpha*x), np.cos(beta*y))
    cc = np.outer(np.cos(alpha*x), np.cos(beta*y))
    zero = np.zeros_like(ss)
    sx = np.stack((alpha*cs, -cs, zero), axis=-1)
    sy = np.stack((beta*sc, zero, -sc), axis=-1)
    bend_x = np.stack((zero, -alpha*ss, zero), axis=-1)
    bend_y = np.stack((zero, zero, -beta*ss), axis=-1)
    twist = np.stack((zero, beta*cc, alpha*cc), axis=-1)
    product = lambda a, b: np.einsum('ij,ija,ijb->ab', xy_weight, a, b)
    rigidity = young * thickness**3 / (12*(1-nu**2))
    shear = (5/6) * young * thickness / (2*(1+nu))
    stiffness = (shear*(product(sx, sx)+product(sy, sy))
                 + rigidity*(product(bend_x, bend_x)+product(bend_y, bend_y)
                 + nu*(product(bend_x, bend_y)+product(bend_y, bend_x))
                 + (1-nu)/2 * product(twist, twist)))
    mass = np.diag([density*thickness*np.sum(xy_weight*ss**2),
                    density*thickness**3/12*np.sum(xy_weight*cs**2),
                    density*thickness**3/12*np.sum(xy_weight*sc**2)])
    omega2, phi = linalg.eigh(stiffness, mass)
    # Independent Gaussian expectation, rather than its closed-form Fourier
    # factor, for the fixed normal and tangential traction projections.
    nodes, weights = hermgauss(48)
    sigma = p['contact_radius_m']/2
    gx = .43*width + np.sqrt(2)*sigma*nodes
    gy = .47*height + np.sqrt(2)*sigma*nodes
    weights = weights / np.sqrt(np.pi)
    normal = np.sum(weights*np.sin(alpha*gx))*np.sum(weights*np.sin(beta*gy))
    tangent = -thickness/2*np.sum(weights*np.cos(alpha*gx))*np.sum(weights*np.sin(beta*gy))
    volume = np.sum(xy_weight*ss)
    ports = (np.diag([normal, tangent, 0]) @ phi)[:2]
    ports = np.vstack((ports, volume*phi[0]))
    return omega2, ports.T


def reference_static_compliance(p):
    """Direct static elasticity solve for the complete fixed candidate space."""
    m, n = np.meshgrid(np.arange(1, 97), np.arange(1, 97), indexing='ij')
    a = m*np.pi/p['plate_width_m']; b = n*np.pi/p['plate_height_m']
    h, young, nu = p['plate_thickness_m'], p['young_modulus_pa'], p['poisson_ratio']
    bending = young*h**3/(12*(1-nu**2)); shear = (5/6)*young*h/(2*(1+nu))
    area4 = p['plate_width_m']*p['plate_height_m']/4
    matrix = np.zeros((96, 96, 3, 3))
    matrix[:, :, 0, 0] = shear*(a*a+b*b)
    matrix[:, :, 0, 1] = matrix[:, :, 1, 0] = -shear*a
    matrix[:, :, 0, 2] = matrix[:, :, 2, 0] = -shear*b
    matrix[:, :, 1, 1] = bending*(a*a+(1-nu)*b*b/2)+shear
    matrix[:, :, 2, 2] = bending*(b*b+(1-nu)*a*a/2)+shear
    matrix[:, :, 1, 2] = matrix[:, :, 2, 1] = bending*(1+nu)*a*b/2
    matrix *= area4
    traction = (np.sin(.43*m*np.pi)*np.sin(.47*n*np.pi)
                * np.exp(-.5*(p['contact_radius_m']/2)**2*(a*a+b*b)))
    force = np.zeros((96, 96, 3, 1)); force[:, :, 0, 0] = traction
    deformation = np.linalg.solve(matrix, force)
    return float(np.sum(traction*deformation[:, :, 0, 0]))


def linear_fixture(p, modes):
    """Dense continuous equations, assembled before implicit midpoint.

    This independently implements the original pressure/flow/modal ODEs, not
    the native acoustic elimination or its two-port Schur complement.
    """
    nm, cells = len(modes), p['duct_cells']
    npres, nflow = cells+2, cells+1
    cursor = 0
    q, v = [], []
    for _ in range(2):
        q.append(np.arange(cursor, cursor+nm)); cursor += nm
        v.append(np.arange(cursor, cursor+nm)); cursor += nm
    pressure = np.arange(cursor, cursor+npres); cursor += npres
    flow = np.arange(cursor, cursor+nflow); cursor += nflow
    vent = np.arange(cursor, cursor+2); cursor += 2
    radiation = np.arange(cursor, cursor+2); cursor += 2
    matrix = np.zeros((cursor, cursor)); ports = np.zeros((cursor, 2)); energy = np.zeros(cursor)
    rho, c = p['air_density_kg_m3'], p['sound_speed_m_s']
    dx, area = p['duct_length_m']/cells, np.pi*p['duct_radius_m']**2
    cap = np.full(npres, area*dx/(rho*c*c)); cap[[0, -1]] = p['cavity_volume_m3']/(rho*c*c)
    lengths = np.full(nflow, dx); lengths[[0, -1]] = dx/2
    inertance = rho*lengths/area
    resistance = 8*p['air_viscosity_pa_s']*lengths/(np.pi*p['duct_radius_m']**4)
    vent_l = rho*p['vent_length_m']/(np.pi*p['vent_radius_m']**2)
    vent_r = 8*p['air_viscosity_pa_s']*p['vent_length_m']/(np.pi*p['vent_radius_m']**4)
    rad_r = rho*c/(4*np.pi*p['vent_radius_m']**2); tau = p['vent_radius_m']/c
    omega2, b, t, a = modes.T
    for ear in range(2):
        pp = pressure[0 if ear == 0 else -1]
        matrix[q[ear], v[ear]] = 1
        matrix[v[ear], q[ear]] = -omega2
        matrix[v[ear], v[ear]] = -2*p['modal_loss_ratio']*np.sqrt(omega2)
        matrix[v[ear], pp] = -a
        matrix[pp, v[ear]] = a/cap[0 if ear == 0 else -1]
        if ear == (0 if p['side'] == 'left' else 1):
            ports[v[ear], 0] = b; ports[v[ear], 1] = t
        matrix[pp, vent[ear]] = -1/cap[0 if ear == 0 else -1]
        matrix[vent[ear], pp] = 1/vent_l
        matrix[vent[ear], vent[ear]] = -(vent_r+rad_r)/vent_l
        matrix[vent[ear], radiation[ear]] = rad_r/vent_l
        matrix[radiation[ear], vent[ear]] = 1/tau
        matrix[radiation[ear], radiation[ear]] = -1/tau
        energy[q[ear]] = omega2; energy[v[ear]] = 1
    for edge in range(nflow):
        matrix[pressure[edge], flow[edge]] = -1/cap[edge]
        matrix[pressure[edge+1], flow[edge]] = 1/cap[edge+1]
        matrix[flow[edge], pressure[edge]] = 1/inertance[edge]
        matrix[flow[edge], pressure[edge+1]] = -1/inertance[edge]
        matrix[flow[edge], flow[edge]] = -resistance[edge]/inertance[edge]
    energy[pressure] = cap; energy[flow] = inertance
    energy[vent] = vent_l; energy[radiation] = rad_r*tau
    observations = {'pressure': pressure[[0, -1]], 'vent': vent, 'radiation': radiation,
                    'radiation_scale': rad_r*p['vent_radius_m']/.25}
    return matrix, ports, energy, observations


class PhysicsAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='ku100-physics-audit-')
        cls.work = Path(cls.temporary.name); cls.binary = cls.work/'ku100-native'
        compiled = subprocess.run([sys.executable, str(ROOT/'scripts/build_native.py'), '--out', str(cls.binary)],
                                  capture_output=True, text=True, check=False)
        if compiled.returncode:
            raise RuntimeError(compiled.stdout+compiled.stderr)
        cls.compiler_warnings = compiled.stderr
        cls.build_identity = json.loads(cls.binary.with_suffix('.build.json').read_text())
        cls.defaults = json.loads(subprocess.check_output([str(cls.binary), '--describe'], text=True))['physics_defaults']
        cls.probe = cls.work/'physics-probe'; cpp = cls.work/'probe.cpp'; cpp.write_text(PROBE)
        built = subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Wpedantic',
                                '-I', str(ROOT/'native'), str(cpp), '-o', str(cls.probe)],
                               capture_output=True, text=True, check=False)
        if built.returncode:
            raise RuntimeError(built.stderr)
        cls.compiler_warnings += built.stderr
        cls.observations = {}; cls.serial = 0

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def call_probe(self, *args):
        run = subprocess.run([str(self.probe), *map(str, args)], capture_output=True,
                             text=True, timeout=30, check=False)
        self.assertEqual(run.returncode, 0, run.stderr)
        return json.loads(run.stdout)

    def render(self, **options):
        type(self).serial += 1
        out = self.work/f'render-{self.serial}'
        args = [str(self.binary), '--out', str(out)]
        for key, value in options.items():
            args += ['--'+key.replace('_', '-'), str(value)]
        run = subprocess.run(args, cwd=self.work, capture_output=True, text=True, timeout=90, check=False)
        self.assertEqual(run.returncode, 0, run.stderr)
        meta = json.loads((out/'native.json').read_text())
        trace = np.genfromtxt(out/'trace.csv', delimiter=',', names=True)
        return out, meta, trace

    def test_mindlin_modes_and_work_ports_match_spatial_energy_quadrature(self):
        configurations = [(self.defaults, m, n) for m, n in ((1, 1), (2, 3), (7, 5))]
        altered = dict(self.defaults, young_modulus_pa=2.4e6, poisson_ratio=.2, plate_thickness_m=.005)
        configurations.append((altered, 3, 2))
        frequency_error = port_error = 0.0
        for p, m, n in configurations:
            keys = ('young_modulus_pa', 'poisson_ratio', 'density_kg_m3', 'plate_width_m',
                    'plate_height_m', 'plate_thickness_m', 'contact_radius_m')
            actual = np.asarray(self.call_probe('block', m, n, *(p[k] for k in keys)))
            actual = actual[np.argsort(actual[:, 0])]
            expected_omega2, expected_ports = block_by_energy_quadrature(p, m, n)
            frequency_error = max(frequency_error, float(np.max(np.abs(actual[:, 0]/expected_omega2-1))))
            np.testing.assert_allclose(actual[:, 0], expected_omega2, rtol=2e-9, atol=1e-6)
            # Eigenvector signs are arbitrary; port outer products preserve all
            # physically meaningful self and cross-work projections.
            native_outer = np.einsum('ni,nj->nij', actual[:, 1:], actual[:, 1:])
            expected_outer = np.einsum('ni,nj->nij', expected_ports, expected_ports)
            port_error = max(port_error, float(np.max(np.abs(native_outer-expected_outer))))
            np.testing.assert_allclose(native_outer, expected_outer, rtol=2e-8, atol=2e-8)
        self.observations[self._testMethodName] = {'max_eigenvalue_relative_error': frequency_error,
                                                  'max_port_outer_product_absolute_error': port_error}

    def test_reference_static_compliance_is_correct_and_independent_of_retained_count(self):
        expected = reference_static_compliance(self.defaults)
        values = [self.call_probe('modes', count)['compliance'] for count in (1, 16, 128)]
        np.testing.assert_allclose(values, expected, rtol=2e-9, atol=1e-14)
        self.assertEqual(len(set(values)), 1)
        self.observations[self._testMethodName] = {'independent_compliance_m_per_n': expected,
                                                  'native_compliance_m_per_n': values[0]}

    def test_hertz_discrete_gradient_matches_force_quadrature_across_release(self):
        stiffness = self.defaults['contact_stiffness_n_m15']; maximum = 0.0
        for a, b in ((-2e-4, -1e-4), (-1e-4, 2e-4), (2e-4, -1e-4),
                     (1e-4, 1e-4), (1e-4, 1e-4+1e-16), (1e-5, 4e-4), (0, 2e-4)):
            actual = self.call_probe('gradient', a, b, stiffness)
            expected = averaged_contact_force(a, b, stiffness)
            maximum = max(maximum, abs(actual-expected))
            self.assertAlmostEqual(actual, expected, delta=2e-12)
            self.assertGreaterEqual(actual, 0)
        self.observations[self._testMethodName] = {'max_force_error_n': maximum}

    def test_contact_solver_matches_independent_root_and_nonnegative_work_loss(self):
        p = self.defaults; maximum = 0.0; minimum_loss = float('inf')
        cases = [(1e-4, .02, .03, 0), (1e-4, -.02, -.04, 1),
                 (-1e-4, 2, .05, .4), (1e-4, -2, -.03, .7),
                 (-1e-4, 0, .03, 1), (1e-4, 0, 0, 0)]
        dt, ynn, ynt, ytt, bn, bt = 1e-4, .01, -.003, .006, .001, -.002
        for d0, driver_n, driver_t, wet in cases:
            actual = self.call_probe('contact', d0, driver_n, driver_t, bn, bt,
                                     ynn, ynt, ytt, dt, wet, 0)
            film_n = wet*3*np.pi*p['film_viscosity_pa_s']*p['contact_radius_m']**4/(2*p['film_thickness_m']**3)
            film_t = wet*p['film_viscosity_pa_s']*np.pi*p['contact_radius_m']**2/p['film_thickness_m']
            def equations(f):
                fn, ft = f
                vn = driver_n-bn-ynn*fn-ynt*ft; vt = driver_t-bt-ynt*fn-ytt*ft
                d1 = d0+dt*vn
                damp = (p['contact_damping_n_s_m']+film_n) if max(d0, d1)>0 else 0
                return [fn-averaged_contact_force(d0, d1, p['contact_stiffness_n_m15'])-damp*max(0, vn),
                        ft-p['friction_coefficient']*fn*np.tanh(vt/p['friction_velocity_m_s'])
                        -(film_t if fn>0 else 0)*vt]
            solved = optimize.root(equations, [p['contact_stiffness_n_m15']*max(d0, 0)**1.5, 0], tol=1e-10)
            self.assertLess(float(np.max(np.abs(equations(solved.x)))), 2e-10)
            observed = np.array([actual['normal'], actual['tangent']])
            maximum = max(maximum, float(np.max(np.abs(observed-solved.x))))
            np.testing.assert_allclose(observed, solved.x, rtol=2e-8, atol=2e-10)
            self.assertGreaterEqual(actual['normal'], -1e-14)
            self.assertGreaterEqual(actual['loss_rate'], -1e-14)
            minimum_loss = min(minimum_loss, actual['loss_rate'])
        self.observations[self._testMethodName] = {'max_force_error_n': maximum,
                                                  'min_dissipation_power_w': minimum_loss}

    def test_native_linear_coupling_and_energy_match_independent_dense_midpoint(self):
        overrides = dict(sample_rate=48000, modes_per_plate=3, duct_cells=3, duration_s=.05,
                         trace_stride=1, load_n=.004, roughness_rms_m=0, wetness=.4,
                         speed_m_s=.02, action='stroke', side='left')
        out, meta, trace = self.render(**overrides)
        p = dict(self.defaults, **overrides)
        modes = np.asarray(self.call_probe('modes', p['modes_per_plate'])['modes'])
        matrix, ports, energy, observed = linear_fixture(p, modes)
        dt = 1/p['sample_rate']; size = len(energy)
        # Energy coordinates avoid ill-conditioning from mixing Pa, m^3/s and
        # modal displacement in the independent dense linear algebra.
        scale = np.sqrt(energy)
        matrix = scale[:, None]*matrix/scale[None, :]
        ports = scale[:, None]*ports
        lhs = linalg.lu_factor(np.eye(size)-dt/2*matrix)
        rhs_matrix = np.eye(size)+dt/2*matrix
        normalized_state = np.zeros(size); pressure = []; airborne = []; stored = []
        for row in trace:
            forcing = np.array([row['normal_force_n'], row['friction_force_n']])
            normalized_state = linalg.lu_solve(lhs, rhs_matrix@normalized_state+dt*ports@forcing)
            state = normalized_state/scale
            pressure.append(state[observed['pressure']].copy())
            airborne.append(observed['radiation_scale']*(state[observed['vent']]-state[observed['radiation']]))
            potential = p['contact_stiffness_n_m15']*max(row['indentation_m'], 0)**2.5/2.5
            stored.append(.5*np.sum(energy*state**2)+potential)
        pressure, airborne = np.asarray(pressure), np.asarray(airborne)
        native_pressure = np.column_stack((trace['cavity_left_pa'], trace['cavity_right_pa']))
        pressure_error = float(np.max(np.abs(pressure-native_pressure)))
        energy_error = float(np.max(np.abs(stored-trace['stored_energy_j'])))
        np.testing.assert_allclose(pressure, native_pressure, rtol=2e-8, atol=2e-9)
        np.testing.assert_allclose(stored, trace['stored_energy_j'], rtol=2e-8, atol=2e-13)
        rate, native_airborne = wavfile.read(out/'airborne-source.wav')
        self.assertEqual(rate, 48000)
        np.testing.assert_allclose(airborne, native_airborne, rtol=2e-7, atol=1e-10)
        self.assertGreater(float(np.max(np.abs(native_pressure[:, 1]))), 1e-4)
        self.assertTrue(np.all(np.diff(trace['dissipated_energy_j']) >= -1e-13))
        self.assertLess(float(np.max(np.abs(trace['balance_error_j']))), 2e-11)
        # The physics observes end-of-step states. At identity decimation the
        # first WAV frame is the trace state at dt, not a fictitious zero state.
        _, cavity = wavfile.read(out/'cavity-pressure.wav')
        np.testing.assert_array_equal(cavity, native_pressure.astype(np.float32))
        np.testing.assert_allclose(trace['time_s'], (np.arange(len(trace))+1)*dt, atol=1e-16)
        self.assertEqual(meta['simulation_first_sample_s'], dt)
        self.observations[self._testMethodName] = {
            'max_cavity_pressure_error_pa': pressure_error, 'max_stored_energy_error_j': energy_error,
            'max_energy_balance_error_j': float(np.max(np.abs(trace['balance_error_j']))),
            'frames': len(trace), 'integration_rate_hz': p['sample_rate'],
            'known_input': overrides, 'native_regime': meta['physics'].get('regime_valid')}

    def test_cli_capture_gain_changes_audio_only_without_normalization(self):
        options = dict(duration_s=.05, sample_rate=48000, trace_stride=48, modes_per_plate=8,
                       load_n=.004, action='press', sensitivity_mv_pa=20, adc_full_scale_v=2)
        a, ma, _ = self.render(**options, preamp_gain_db=-20)
        b, mb, _ = self.render(**options, preamp_gain_db=0)
        self.assertEqual((a/'cavity-pressure.wav').read_bytes(), (b/'cavity-pressure.wav').read_bytes())
        self.assertEqual((a/'airborne-source.wav').read_bytes(), (b/'airborne-source.wav').read_bytes())
        self.assertEqual(ma['physics'], mb['physics'])
        _, xa = wavfile.read(a/'render.wav'); _, xb = wavfile.read(b/'render.wav')
        self.assertAlmostEqual(mb['digital_gain_per_pa']/ma['digital_gain_per_pa'], 10)
        np.testing.assert_allclose(xb, 10*xa, rtol=2e-7, atol=2e-10)
        self.observations[self._testMethodName] = {
            'digital_gain_a_per_pa': ma['digital_gain_per_pa'],
            'digital_gain_b_per_pa': mb['digital_gain_per_pa'],
            'raw_pressure_and_source_bytes_identical': True}

    def test_cli_airborne_composition_uses_default_bank_and_selected_source(self):
        # This deliberately uses a synthetic bank with distinguishable ears.
        # It tests native CLI routing independently of measured-bank provenance.
        data = self.work/'data'; data.mkdir(exist_ok=True)
        bank = np.zeros((1, 360, 2, 4), dtype='<f4')
        bank[:, :, 0] = [1, .25, -.1, .05]; bank[:, :, 1] = [.2, -.1, .05, 0]
        (data/'ku100_bank.bin').write_bytes(struct.pack('<8s4I', b'KUHRIR01', 48000, 1, 360, 4)
                                          + struct.pack('<d', .25) + bank.tobytes())
        out, meta, _ = self.render(duration_s=.05, sample_rate=48000, modes_per_plate=8,
                                   load_n=.004, action='press', side='right', receiver='airborne',
                                   azimuth_deg=270, distance_m=.25, preamp_gain_db=-20)
        _, source = wavfile.read(out/'airborne-source.wav'); _, actual = wavfile.read(out/'render.wav')
        delay = .25/self.defaults['sound_speed_m_s']*48000
        integer, fraction = math.floor(delay), delay-math.floor(delay)
        h = np.sinc(np.arange(63)-31-fraction)*signal.windows.kaiser(63, 9, sym=True); h /= h.sum()
        delayed = np.pad(np.convolve(source[:, 1].astype(float), h), (integer, 0))
        expected = np.column_stack([np.convolve(delayed, ear.astype(float)) for ear in bank[0, 270]])
        expected *= meta['digital_gain_per_pa']
        np.testing.assert_allclose(actual, expected, rtol=3e-6, atol=2e-10)
        self.assertEqual(meta['frames'], len(expected))
        self.assertEqual(meta['fractional_delay_latency_s'], 31/48000)
        self.assertAlmostEqual(meta['modeled_propagation_delay_s'], .25/self.defaults['sound_speed_m_s'])
        self.observations[self._testMethodName] = {
            'relative_l2_error_after_float32_source_export': float(np.linalg.norm(actual-expected)/np.linalg.norm(expected)),
            'frames': len(expected), 'source_side': 'right', 'bank': 'synthetic fixture'}

    def test_render_bundle_trace_times_match_audio_grid(self):
        scene = self.work/'scene.json'
        scene.write_text(json.dumps({'version': 'ku100-scene/1', 'preset': 'press', 'duration_s': .05,
                                     'physics': {'sample_rate': 192000, 'modes_per_plate': 8,
                                                 'load_n': .004, 'trace_stride': 192},
                                     'capture': {'preamp_gain_db': -20}}))
        out = self.work/'bundle'
        run = subprocess.run([sys.executable, str(ROOT/'scripts/render.py'), '--scene', str(scene),
                              '--out', str(out), '--binary', str(self.binary)],
                             cwd=ROOT, capture_output=True, text=True, timeout=90, check=False)
        self.assertEqual(run.returncode, 0, run.stderr)
        bundle = json.loads((out/'render.ku100.json').read_text())
        columns = bundle['trace']['columns']; rows = np.asarray(bundle['trace']['rows'])
        latencies = bundle['provenance']['latency']
        total = sum(latencies[k] for k in ('decimation_latency_s', 'fractional_delay_latency_s', 'modeled_propagation_delay_s'))
        expected = rows[:, columns.index('simulation_time_s')]-1/192000+total
        np.testing.assert_allclose(rows[:, columns.index('time_s')], expected, atol=1e-15, rtol=0)
        self.assertEqual(latencies['simulation_first_sample_s'], 1/192000)
        self.assertAlmostEqual(rows[0, columns.index('time_s')], 64/48000)
        self.observations[self._testMethodName] = {'first_trace_audio_time_s': float(rows[0, 0]),
                                                  'simulation_first_sample_s': 1/192000}


if __name__ == '__main__':
    unittest.main(verbosity=2)
