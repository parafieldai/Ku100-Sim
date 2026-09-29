/** Small orthographic geometry viewer. Geometry and motion always come from the export. */
export class FixtureView {
  constructor(canvas, onViewChange = () => {}) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.geometry = null;
    this.row = null;
    this.columns = new Map();
    this.trajectory = [];
    this.azimuth = 0.75;
    this.elevation = 0.22;
    this.zoom = 1;
    this.detail = false;
    this.onViewChange = onViewChange;
    let drag = null;
    canvas.addEventListener('pointerdown', event => { drag = {x: event.clientX, y: event.clientY}; canvas.setPointerCapture(event.pointerId); canvas.focus({preventScroll: true}); });
    canvas.addEventListener('pointermove', event => {
      if (!drag) return;
      this.azimuth -= (event.clientX - drag.x) * 0.008;
      this.elevation = Math.max(-1.2, Math.min(1.2, this.elevation + (event.clientY - drag.y) * 0.007));
      drag = {x: event.clientX, y: event.clientY}; this.draw();
    });
    for (const name of ['pointerup', 'pointercancel', 'lostpointercapture']) canvas.addEventListener(name, () => { drag = null; });
    canvas.addEventListener('wheel', event => { event.preventDefault(); this.zoom = Math.max(0.5, Math.min(7, this.zoom * Math.exp(-event.deltaY * 0.001))); this.draw(); }, {passive: false});
    canvas.addEventListener('keydown', event => {
      const keys = ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', '+', '=', '-', '0'];
      if (!keys.includes(event.key)) return;
      event.preventDefault();
      if (event.key === 'ArrowLeft') this.azimuth -= 0.12;
      if (event.key === 'ArrowRight') this.azimuth += 0.12;
      if (event.key === 'ArrowUp') this.elevation = Math.min(1.2, this.elevation + 0.1);
      if (event.key === 'ArrowDown') this.elevation = Math.max(-1.2, this.elevation - 0.1);
      if (event.key === '+' || event.key === '=') this.zoom = Math.min(7, this.zoom * 1.12);
      if (event.key === '-') this.zoom = Math.max(0.5, this.zoom / 1.12);
      if (event.key === '0') this.reset();
      this.draw();
    });
    this.resizeObserver = new ResizeObserver(() => this.draw());
    this.resizeObserver.observe(canvas);
    this.draw();
  }

  setBundle(bundle) {
    this.geometry = bundle.geometry;
    this.columns = new Map(bundle.trace.columns.map((column, i) => [column, i]));
    const indices = ['actuator_x_m', 'actuator_y_m', 'actuator_z_m'].map(c => this.columns.get(c));
    this.trajectory = indices.every(i => i !== undefined) ? bundle.trace.rows.filter((_, i) => i % Math.max(1, Math.floor(bundle.trace.rows.length / 400)) === 0).map(row => indices.map(i => row[i])) : [];
    this.row = null;
    this.reset();
  }

  setTime(row) { this.row = row; this.draw(); }
  setDetail(detail) { this.detail = detail; this.zoom = detail ? 3.2 : 1; this.draw(); this.onViewChange(detail); }
  reset() { this.azimuth = 0.75; this.elevation = 0.22; this.zoom = this.detail ? 3.2 : 1; this.draw(); }

  draw() {
    const canvas = this.canvas, ctx = this.ctx, rect = canvas.getBoundingClientRect();
    const width = Math.max(1, rect.width), height = Math.max(1, rect.height), dpr = Math.min(window.devicePixelRatio || 1, 2);
    if (canvas.width !== Math.round(width * dpr) || canvas.height !== Math.round(height * dpr)) { canvas.width = Math.round(width * dpr); canvas.height = Math.round(height * dpr); }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, width, height);
    if (!this.geometry) {
      ctx.fillStyle = '#758691'; ctx.font = '11px system-ui'; ctx.textAlign = 'center';
      ctx.fillText('Load a native export to view its geometry', width / 2, height / 2);
      return;
    }
    const {head, ears, contact} = this.geometry;
    const contactEar = ears.find(ear => ear.side === contact.side);
    const target = this.detail ? contactEar.center_m : head.center_m;
    const az = this.azimuth, el = this.elevation, s = Math.min(width, height) * 2.75 * this.zoom;
    const right = [Math.sin(az), -Math.cos(az), 0], up = [-Math.cos(az) * Math.sin(el), -Math.sin(az) * Math.sin(el), Math.cos(el)], forward = [Math.cos(az) * Math.cos(el), Math.sin(az) * Math.cos(el), Math.sin(el)];
    const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
    const project = point => { const v = point.map((x, i) => x - target[i]); return [width * 0.5 + dot(v, right) * s, height * 0.48 - dot(v, up) * s, dot(v, forward)]; };
    const line = (points, color, lineWidth = 1, closed = false) => {
      if (!points.length) return;
      ctx.beginPath(); points.forEach((point, i) => { const p = project(point); if (i) ctx.lineTo(p[0], p[1]); else ctx.moveTo(p[0], p[1]); });
      if (closed) ctx.closePath(); ctx.strokeStyle = color; ctx.lineWidth = lineWidth; ctx.stroke();
    };
    const floor = head.center_m[2] - head.radii_m[2] - 0.025;
    for (let i = -5; i <= 5; i++) {
      const pos = i * 0.04;
      line([[-0.22, pos, floor], [0.22, pos, floor]], i === 0 ? '#40515b66' : '#35454f3d');
      line([[pos, -0.22, floor], [pos, 0.22, floor]], i === 0 ? '#40515b66' : '#35454f3d');
    }
    const shapes = [{center: head.center_m, radii: head.radii_m, color: [51, 64, 72], kind: 'head'}, ...ears.map(ear => ({center: [ear.center_m[0], ear.center_m[1] - (ear.side === 'left' ? 0.009 : -0.009), ear.center_m[2]], radii: [0.018, 0.009, 0.029], color: ear.side === 'left' ? [47, 89, 91] : [78, 71, 105], kind: ear.side}))];
    const faces = [];
    for (const shape of shapes) {
      const point = (lat, lon) => shape.center.map((c, i) => c + shape.radii[i] * [Math.cos(lat) * Math.cos(lon), Math.cos(lat) * Math.sin(lon), Math.sin(lat)][i]);
      const slices = shape.kind === 'head' ? 24 : 16, stacks = 12;
      for (let j = 0; j < stacks; j++) for (let k = 0; k < slices; k++) {
        const a = -Math.PI / 2 + j * Math.PI / stacks, b = a + Math.PI / stacks, c = k * 2 * Math.PI / slices, d = c + 2 * Math.PI / slices;
        const vertices = [point(a, c), point(a, d), point(b, d), point(b, c)].map(project);
        const normal = [Math.cos((a + b) / 2) * Math.cos((c + d) / 2), Math.cos((a + b) / 2) * Math.sin((c + d) / 2), Math.sin((a + b) / 2)];
        const light = 0.55 + 0.5 * Math.max(0, dot(normal, [0.35, 0.2, 0.8]));
        faces.push({vertices, depth: vertices.reduce((sum, p) => sum + p[2], 0) / 4, color: shape.color.map(v => Math.round(v * light)), kind: shape.kind});
      }
    }
    faces.sort((a, b) => a.depth - b.depth);
    for (const face of faces) {
      ctx.beginPath(); face.vertices.forEach((p, i) => i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1])); ctx.closePath();
      ctx.fillStyle = `rgb(${face.color.join(',')})`; ctx.fill();
      ctx.strokeStyle = face.kind === 'head' ? '#93b5c018' : '#b1cacc21'; ctx.lineWidth = 0.5; ctx.stroke();
    }
    // The nose indicator establishes orientation without claiming scanned anatomy.
    line([[head.radii_m[0] + head.center_m[0], head.center_m[1], head.center_m[2] + 0.01], [head.radii_m[0] + head.center_m[0] + 0.017, head.center_m[1], head.center_m[2] - 0.008], [head.radii_m[0] + head.center_m[0], head.center_m[1], head.center_m[2] - 0.015]], '#96b3bd77', 1.2);
    line(this.trajectory, '#ffb37075', 1.1);
    const patchCenter = [...contactEar.center_m];
    const patch = Array.from({length: 48}, (_, i) => { const a = i / 48 * 2 * Math.PI; return [patchCenter[0] + Math.cos(a) * contact.patch_radius_m, patchCenter[1], patchCenter[2] + Math.sin(a) * contact.patch_radius_m]; });
    line(patch, '#ffb370', 1.5, true);
    for (const ear of ears) {
      const p = project(ear.center_m), color = ear.side === 'left' ? '#68d9d3' : '#a99af6';
      ctx.beginPath(); ctx.arc(p[0], p[1], 3, 0, Math.PI * 2); ctx.fillStyle = color; ctx.fill();
      ctx.font = '9px ui-monospace, monospace'; ctx.textAlign = ear.side === 'left' ? 'left' : 'right'; ctx.fillText(ear.side === 'left' ? 'L' : 'R', p[0] + (ear.side === 'left' ? 11 : -11), p[1] - 9);
    }
    if (this.row) {
      const indices = ['actuator_x_m', 'actuator_y_m', 'actuator_z_m'].map(c => this.columns.get(c));
      if (indices.every(i => i !== undefined)) {
        const p = project(indices.map(i => this.row[i]));
        ctx.beginPath(); ctx.arc(p[0], p[1], 9, 0, Math.PI * 2); ctx.fillStyle = '#ffb37020'; ctx.fill();
        ctx.beginPath(); ctx.arc(p[0], p[1], 4, 0, Math.PI * 2); ctx.fillStyle = '#ffb370'; ctx.fill();
      }
    }
    // A fixed screen-space axis triad preserves the exported coordinate convention.
    const axisOrigin = [width - 50, height - 90];
    for (const [i, label, color] of [[0, 'x', '#e1a28a'], [1, 'y', '#9ec2a2'], [2, 'z', '#92b9d7']]) {
      const unit = [0, 0, 0]; unit[i] = 1;
      const end = [axisOrigin[0] + dot(unit, right) * 22, axisOrigin[1] - dot(unit, up) * 22];
      ctx.beginPath(); ctx.moveTo(...axisOrigin); ctx.lineTo(...end); ctx.strokeStyle = color; ctx.lineWidth = 1.1; ctx.stroke();
      ctx.fillStyle = color; ctx.font = '8px ui-monospace, monospace'; ctx.textAlign = 'center'; ctx.fillText(label, end[0], end[1] - 4);
    }
  }
}
