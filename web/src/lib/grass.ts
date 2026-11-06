// Procedural grass patch with footprints. Technique after Bruno Simon's portfolio devlog #2
// (docs/Grass-New-portfolio-Devlog-2.txt, from ~08:25 and ~12:05), adapted:
//   - one merged geometry; every vertex stores its blade's CENTRE, and the shader builds the blade around it;
//   - a fixed oval patch, dense right up to the rim: the blades get smaller towards the edge and that
//     shrinking is what fades the patch out (the disc under them only tidies the very last bit);
//   - meadow colouring: a slow noise field picks lighter yellow-greens, the front of the mound goes cool;
//   - wind: gust fronts rolling across the patch plus a small flutter; the blades bow along a curve;
//   - instead of wheel tracks, feet stamp soft prints into an off-screen top-down render target
//     ("ground data"), which slowly fades back to zero; the grass reads it to flatten blades.
import * as THREE from 'three';

/** Half-axes of the patch on the ground (world x / z). */
export type Patch = { a: number; b: number };

// Rim wobble: 0 = a clean ellipse (the sand apron and the sparse tufts do the softening), 1 = the old uneven rim.
// Same formula in JS (`reach`) and GLSL (`reachAt`).
const WOBBLE = 0;
const REACH_GLSL = /* glsl */ `float reachAt(float ang) { return 1.0 + ${WOBBLE.toFixed(2)} * (0.045 * sin(3.0 * ang + 0.7) + 0.03 * sin(7.0 * ang + 2.1) + 0.018 * sin(13.0 * ang + 1.3)); }`;
// Dry-brush streaks. Each point gets a stroke direction: horizontal at the two sides of the oval (the strokes
// stream off into the page, like the reference) bending round to follow the rim at the front and back. The
// noise is stretched along that direction and fine across it, so the strokes always run with the flow and
// never radiate outwards. `local` is a point on a unit disc (0 centre .. 1 edge).
// Tune: STROKE.x = stroke length (lower = longer), STROKE.y = how many bands across; CURVE = how far the
// following-the-rim zone spreads from the front/back towards the sides (1 = even, <1 = wider).
const STREAK_GLSL = /* glsl */ `
const vec2 STROKE = vec2(3.4, 16.0);
const float CURVE = 1.0;
float streakAt(vec2 local) {
  float r = max(length(local), 1e-4);
  vec2 tangent = vec2(-local.y, local.x) / r;          // along the rim
  tangent *= tangent.x < 0.0 ? -1.0 : 1.0;             // always pointing +x so it blends with horizontal
  float w = pow(local.y * local.y / (r * r), CURVE);   // 0 at the sides, 1 at the front/back
  vec2 d = normalize(mix(vec2(1.0, 0.0), tangent, w)); // stroke direction
  vec2 n = vec2(-d.y, d.x);                            // across the stroke
  vec2 q = vec2(dot(local, d) * STROKE.x, dot(local, n) * STROKE.y);
  return vnoise(q + 7.0) * 0.6 + vnoise(q * 2.4 + 2.0) * 0.4;
}`;

const NOISE_GLSL = /* glsl */ `
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p) {
  vec2 i = floor(p), f = fract(p), u = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
}`;

const GROUND_UV_GLSL = /* glsl */ `
uniform sampler2D uGround; uniform vec2 uGroundMin; uniform vec2 uGroundSize;
// world xz -> ground-data uv (the ground camera looks straight down with -z at the top)
vec2 groundUv(vec2 xz) { return vec2((xz.x - uGroundMin.x) / uGroundSize.x, 1.0 - (xz.y - uGroundMin.y) / uGroundSize.y); }`;

const quadVert = /* glsl */ `varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`;

export type Print = { set(x: number, z: number, angle: number, length: number, width: number, strength: number): void };

/** Top-down pressure map of the patch. Red = how flattened the grass is (0..1). */
export class GroundData {
  readonly texture: THREE.Texture;
  readonly uniforms: { uGround: { value: THREE.Texture }; uGroundMin: { value: THREE.Vector2 }; uGroundSize: { value: THREE.Vector2 } };
  private target: THREE.WebGLRenderTarget;
  private scene = new THREE.Scene();
  private camera: THREE.OrthographicCamera;
  private fade: THREE.ShaderMaterial;
  private minStep: number;
  private cleared = false;

  /** `recover`: seconds for a full-strength print to grow back. */
  constructor(renderer: THREE.WebGLRenderer, patch: Patch, private recover = 5, resolution = 512) {
    const { a, b } = patch;
    const half = renderer.extensions.has('EXT_color_buffer_half_float') || renderer.extensions.has('EXT_color_buffer_float');
    this.minStep = half ? 0 : 1.5 / 255; // 8-bit fallback: make sure each fade step actually changes a value
    this.target = new THREE.WebGLRenderTarget(resolution, Math.round((resolution * b) / a), {
      type: half ? THREE.HalfFloatType : THREE.UnsignedByteType, depthBuffer: false,
      minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter,
    });
    this.texture = this.target.texture;
    this.uniforms = { uGround: { value: this.texture }, uGroundMin: { value: new THREE.Vector2(-a, -b) }, uGroundSize: { value: new THREE.Vector2(2 * a, 2 * b) } };

    this.camera = new THREE.OrthographicCamera(-a, a, b, -b, 0.1, 10);
    this.camera.position.set(0, 5, 0);
    this.camera.up.set(0, 0, -1);
    this.camera.lookAt(0, 0, 0);

    // Each frame, first subtract a little from every pixel (dst - src), so prints fade out...
    this.fade = new THREE.ShaderMaterial({
      uniforms: { uAmount: { value: 0 } },
      vertexShader: quadVert,
      fragmentShader: /* glsl */ `uniform float uAmount; void main() { gl_FragColor = vec4(uAmount); }`,
      blending: THREE.CustomBlending, blendEquation: THREE.ReverseSubtractEquation,
      blendSrc: THREE.OneFactor, blendDst: THREE.OneFactor,
      depthTest: false, depthWrite: false, transparent: true,
    });
    const quad = new THREE.Mesh(new THREE.PlaneGeometry(2 * a, 2 * b).rotateX(-Math.PI / 2), this.fade);
    quad.renderOrder = 0;
    this.scene.add(quad);
  }

  /** ...then stamp the prints on top, keeping the stronger of old and new (MAX blending). */
  addPrint(): Print {
    const mat = new THREE.ShaderMaterial({
      uniforms: { uStrength: { value: 0 } },
      vertexShader: quadVert,
      fragmentShader: /* glsl */ `
        uniform float uStrength; varying vec2 vUv;
        void main() {
          vec2 p = vUv * 2.0 - 1.0;          // y runs heel (-1) to toe (+1)
          p.x *= 1.0 - 0.2 * p.y;            // a touch wider at the ball of the foot
          float v = 1.0 - smoothstep(0.45, 1.0, length(p));
          gl_FragColor = vec4(v * uStrength, 0.0, 0.0, 1.0);
        }`,
      blending: THREE.CustomBlending, blendEquation: THREE.MaxEquation,
      depthTest: false, depthWrite: false, transparent: true,
      side: THREE.DoubleSide, // the quad is flipped to put the toe on local +z
    });
    // Flat quad; local +z is the foot's length after rotateX, so rotation.y = atan2(dx, dz) points it heel->toe.
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(1, 1).rotateX(Math.PI / 2), mat);
    mesh.renderOrder = 1;
    mesh.visible = false;
    this.scene.add(mesh);
    return {
      set(x, z, angle, length, width, strength) {
        mesh.visible = strength > 0.01;
        mesh.position.set(x, 0, z);
        mesh.rotation.y = angle;
        mesh.scale.set(width, 1, length);
        mat.uniforms.uStrength.value = strength;
      },
    };
  }

  update(renderer: THREE.WebGLRenderer, dt: number) {
    this.fade.uniforms.uAmount.value = dt > 0 ? Math.max(dt / this.recover, this.minStep) : 0;
    const prevTarget = renderer.getRenderTarget();
    const prevAuto = renderer.autoClear;
    renderer.setRenderTarget(this.target);
    if (!this.cleared) {
      const prevColor = renderer.getClearColor(new THREE.Color());
      const prevAlpha = renderer.getClearAlpha();
      renderer.setClearColor(0x000000, 0);
      renderer.clear();
      renderer.setClearColor(prevColor, prevAlpha);
      this.cleared = true;
    }
    renderer.autoClear = false;
    renderer.render(this.scene, this.camera);
    renderer.autoClear = prevAuto;
    renderer.setRenderTarget(prevTarget);
  }
}

export type GrassOptions = {
  count?: number;      // blades in the whole patch
  height?: number;     // world units, at the centre
  width?: number;      // half-width at the base
  /** Normalised radius where the blades start shrinking, and how small they get at the rim (0..1). */
  edge?: { from: number; rimSize: number };
  colors?: {
    root?: THREE.ColorRepresentation;   // bottom of every blade
    blade?: THREE.ColorRepresentation;  // the ordinary green
    tip?: THREE.ColorRepresentation;    // bright tips
    meadow?: THREE.ColorRepresentation; // the lighter, yellower patches
    shade?: THREE.ColorRepresentation;  // cool colour the front of the mound falls into
    trodden?: THREE.ColorRepresentation; // what flattened grass (footprints) turns into
  };
  wind?: { dir: [number, number]; strength: number };
  /** Overall brightness of the grass (blades and the disc under them): 1 = the colours as set, 0.8 = darker. */
  brightness?: number;
  /** Sand apron around the grass: how far it reaches (× the patch), where its fade starts (0..1 of that), colours. */
  sand?: { reach?: number; fadeFrom?: number; near?: THREE.ColorRepresentation; far?: THREE.ColorRepresentation };
  /** Sparse tufts on the sand just outside the grass: how far out (× the patch) and how dense (0..1). */
  tufts?: { reach?: number; density?: number };
};

export function createGrass(ground: GroundData, patch: Patch, opts: GrassOptions = {}) {
  const {
    count = 10_000, height = 0.09, width = 0.008, edge = { from: 0.45, rimSize: 0.42 },
    wind = { dir: [1, 0.035], strength: 0.4 },
  } = opts;
  const brightness = opts.brightness ?? 1;
  const sand = { reach: 1.7, fadeFrom: 0.5, near: '#dcc48e', far: '#e2ddd2', ...opts.sand };
  const tufts = { reach: 1.18, density: 0.9, ...opts.tufts };
  const colors = {
    root: '#007A4E', blade: '#6CB758', tip: '#D2FD55', meadow: '#e4ad7b', shade: '#000000', trodden: '#5a7a35',
    ...opts.colors,
  };
  const { a, b } = patch;

  // --- geometry: jittered grid inside the ellipse, same density all the way to the uneven rim.
  // 5 vertices per blade (base L/R, mid L/R, tip) so it can bow; all five sit at the blade's centre and the
  // shader builds the blade from gl_VertexID. Three triangles, drawn front-facing towards +z (the camera).
  const spacing = Math.sqrt((Math.PI * a * b) / count);
  const reach = (ang: number) => 1 + WOBBLE * (0.045 * Math.sin(3 * ang + 0.7) + 0.03 * Math.sin(7 * ang + 2.1) + 0.018 * Math.sin(13 * ang + 1.3));
  const centres: number[] = [];
  const rands: number[] = [];
  const index: number[] = [];
  let n = 0;
  const T = tufts.reach;
  for (let z = -b * T; z <= b * T; z += spacing) {
    for (let x = -a * T; x <= a * T; x += spacing) {
      const px = x + (Math.random() - 0.5) * spacing;
      const pz = z + (Math.random() - 0.5) * spacing;
      const r = Math.hypot(px / a, pz / b) / reach(Math.atan2(pz / b, px / a));
      if (r > T) continue;
      // outside the grass only a few tufts survive, thinning out towards the sand
      if (r > 1 && Math.random() > tufts.density * (1 - (r - 1) / (T - 1))) continue;
      const r1 = Math.random(), r2 = Math.random();
      for (let v = 0; v < 5; v++) { centres.push(px, 0, pz); rands.push(r1, r2); }
      index.push(n, n + 1, n + 3, n, n + 3, n + 2, n + 2, n + 3, n + 4);
      n += 5;
    }
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(centres, 3));
  geo.setAttribute('aRand', new THREE.Float32BufferAttribute(rands, 2));
  geo.setIndex(index);

  const uniforms = {
    ...ground.uniforms,
    uTime: { value: 0 },
    uPatch: { value: new THREE.Vector2(a, b) },
    uEdge: { value: new THREE.Vector2(edge.from, edge.rimSize) },
    uTuftReach: { value: tufts.reach },
    uHeight: { value: height },
    uWidth: { value: width },
    uWindDir: { value: new THREE.Vector2(...wind.dir).normalize() },
    uWindStrength: { value: wind.strength },
    uRoot: { value: new THREE.Color(colors.root) },
    uBlade: { value: new THREE.Color(colors.blade) },
    uTip: { value: new THREE.Color(colors.tip) },
    uMeadow: { value: new THREE.Color(colors.meadow) },
    uShade: { value: new THREE.Color(colors.shade) },
    uTrodden: { value: new THREE.Color(colors.trodden) },
    uBright: { value: brightness },
  };

  // Lambert, so the blades get the scene's lights and the walkers' shadows for free.
  const mat = new THREE.MeshLambertMaterial({ color: 0xffffff });
  mat.customProgramCacheKey = () => 'ras-grass';
  mat.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, uniforms);
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', /* glsl */ `#include <common>
        ${GROUND_UV_GLSL}
        ${REACH_GLSL}
        ${NOISE_GLSL}
        uniform float uTime, uHeight, uWidth, uWindStrength, uTuftReach;
        uniform vec2 uPatch, uEdge, uWindDir;
        attribute vec2 aRand;
        varying float vTip, vPress, vEdge, vVar, vMeadow, vFront;
        // Wind: slow gust fronts (sharpened so they read as waves rolling over), small ripples on top,
        // and a per-blade flutter so neighbours never move in perfect unison.
        vec2 windAt(vec2 p, float phase) {
          float gust = vnoise(p * 0.45 - uTime * 0.5 * uWindDir);
          gust = smoothstep(0.3, 0.85, gust);
          float ripple = vnoise(p * 2.2 - uTime * 1.5 * uWindDir) - 0.5;
          float flutter = sin(uTime * 3.2 + dot(p, uWindDir) * 4.0 + phase * 6.283) * 0.12 * (0.4 + gust);
          vec2 side = vec2(-uWindDir.y, uWindDir.x);
          return (uWindDir * (0.1 + gust * 0.85 + ripple * 0.25 + flutter) + side * ripple * 0.2) * uWindStrength;
        }`)
      // flat-up normals: every blade is lit like the ground, so the patch reads as one soft painted mass
      .replace('#include <beginnormal_vertex>', 'vec3 objectNormal = vec3(0.0, 1.0, 0.0);')
      .replace('#include <begin_vertex>', /* glsl */ `
        vec3 transformed = vec3(position);  // the blade centre, on the ground
        int vid = gl_VertexID - (gl_VertexID / 5) * 5; // which of the five blade vertices this is
        float t = vid < 2 ? 0.0 : (vid < 4 ? 0.5 : 1.0);           // 0 at the root, 1 at the tip
        float side = vid == 0 || vid == 2 ? -1.0 : (vid == 4 ? 0.0 : 1.0);
        vec2 c = position.xz;
        vec2 q = c / uPatch;
        float r = length(q) / reachAt(atan(q.y, q.x));
        // the edge: blades keep their density but shrink towards the rim — this is the fade
        float edge = mix(uEdge.y, 1.0, 1.0 - smoothstep(uEdge.x, 1.0, r));
        edge *= 1.0 - 0.6 * smoothstep(1.0, uTuftReach, r); // the tufts on the sand are smaller still
        float press = clamp(texture2D(uGround, groundUv(c)).r, 0.0, 1.0);
        float h = uHeight * mix(0.6, 1.0, aRand.x) * edge * (1.0 - 0.8 * press);
        float w = uWidth * mix(0.75, 1.25, aRand.y) * mix(0.55, 1.0, edge) * (1.0 - t) * (1.0 + 0.45 * t);
        float yaw = (aRand.y - 0.5) * 11.3;  // mostly facing the camera (which looks down -z)
        transformed.x += cos(yaw) * side * w;
        transformed.z -= sin(yaw) * side * w;
        // the blade bows along a curve: each blade has its own slight lean, the wind adds to it,
        // and a trodden blade lies down in its own random direction instead
        float la = aRand.x * 6.2832;
        vec2 own = vec2(cos(la), sin(la));
        vec2 lean = (own * 0.18 * aRand.y + windAt(c, aRand.x)) * (1.0 - press) + own * press * 1.1;
        float bow = t * t;                   // quadratic: stiff at the root, bends at the tip
        transformed.xz += lean * h * bow * 1.6;
        transformed.y += h * t * (1.0 - 0.35 * length(lean) * bow); // a bent blade is a little lower
        vTip = t; vPress = press; vEdge = edge; vFront = q.y;
        vVar = vnoise(c * 2.6 + 5.0);
        // meadow: slow noise, sharpened into soft patches of lighter grass
        vMeadow = smoothstep(0.45, 0.8, vnoise(c * 0.9 + 11.0) * 0.7 + vnoise(c * 2.4 + 3.0) * 0.3);`);
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>
        uniform vec3 uRoot, uBlade, uTip, uMeadow, uShade, uTrodden; uniform float uBright;
        varying float vTip, vPress, vEdge, vVar, vMeadow, vFront;`)
      .replace('#include <color_fragment>', /* glsl */ `#include <color_fragment>
        float t = smoothstep(0.0, 1.0, vTip);
        vec3 g = mix(uRoot, uBlade, pow(t, 0.8));            // dark at the root...
        g = mix(g, uTip, pow(t, 6.02) * 0.9);                  // ...bright at the very tip
        vec3 light = mix(uMeadow, uTip, t * 0.7);             // the lighter meadow version of the same blade
        g = mix(g, light, vMeadow * 0.85);
        g *= mix(0.9, 1.08, vVar);                            // small painterly variation blade to blade
        g = mix(g, uShade, 0.3 * smoothstep(0.15, 1.0, vFront)); // front of the mound falls into cool shade
        g = mix(g, uTrodden, vPress * 0.8);                   // trodden blades take the footprint colour
        diffuseColor.rgb *= g * uBright;`);
  };
  const blades = new THREE.Mesh(geo, mat);
  blades.frustumCulled = false;
  blades.receiveShadow = true;

  // --- the disc under the blades: fills the gaps between them and finishes the last sliver of the rim.
  // It is NOT the fade: it stays solid almost to the edge, so the shrinking blades do that job.
  const soilMat = new THREE.MeshLambertMaterial({ color: 0xffffff, transparent: true, depthWrite: false });
  soilMat.customProgramCacheKey = () => 'ras-grass-soil';
  soilMat.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, ground.uniforms, { uRoot: uniforms.uRoot, uBlade: uniforms.uBlade, uMeadow: uniforms.uMeadow, uShade: uniforms.uShade, uTrodden: uniforms.uTrodden, uBright: uniforms.uBright });
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec2 vLocal; varying vec2 vWorldXZ;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvLocal = position.xz; vWorldXZ = (modelMatrix * vec4(transformed, 1.0)).xz;');
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>\n${GROUND_UV_GLSL}\n${REACH_GLSL}\n${NOISE_GLSL}\n${STREAK_GLSL}\nuniform vec3 uRoot, uBlade, uMeadow, uShade, uTrodden; uniform float uBright;\nvarying vec2 vLocal; varying vec2 vWorldXZ;`)
      .replace('#include <color_fragment>', /* glsl */ `#include <color_fragment>
        float gr = length(vLocal) / reachAt(atan(vLocal.y, vLocal.x));
        float meadow = smoothstep(0.45, 0.8, vnoise(vWorldXZ * 0.9 + 11.0) * 0.7 + vnoise(vWorldXZ * 2.4 + 3.0) * 0.3);
        vec3 g = mix(mix(uRoot, uBlade, 0.55), uMeadow, meadow * 0.5);
        g = mix(g, uShade, 0.35 * smoothstep(0.15, 1.0, vLocal.y)); // same cool front as the blades
        g = mix(g, uRoot, 0.25 * smoothstep(0.8, 1.0, gr));          // a little deeper right at the rim
        float press = clamp(texture2D(uGround, groundUv(vWorldXZ)).r, 0.0, 1.0);
        diffuseColor.rgb *= mix(g, uTrodden, press * 0.6) * uBright;
        float streak = streakAt(vLocal);
        diffuseColor.a *= 1.0 - smoothstep(0.9, 1.0, gr + (streak - 0.5) * 0.08); // tight, with a ragged brush edge`);
  };
  const soilDisc = new THREE.Mesh(new THREE.CircleGeometry(1, 160).rotateX(-Math.PI / 2), soilMat);
  soilDisc.scale.set(a, 1, b);
  soilDisc.position.y = 0.001;
  soilDisc.renderOrder = -2; // drawn before the shadow floor, so the walkers' shadows land on top of it

  // --- the sand apron: brown-yellow right at the grass, dustier further out, fading into the page in
  // horizontal dry-brush streaks. Drawn under everything, so shadows and the grass sit on top of it.
  const sandMat = new THREE.MeshLambertMaterial({ color: 0xffffff, transparent: true, depthWrite: false });
  sandMat.customProgramCacheKey = () => 'ras-grass-sand';
  const sandUniforms = {
    uSandNear: { value: new THREE.Color(sand.near) },
    uSandFar: { value: new THREE.Color(sand.far) },
    uSandFade: { value: new THREE.Vector2(1 / sand.reach, sand.fadeFrom) }, // grass rim, where the fade starts (in sand-disc units)
    uShade: uniforms.uShade,
  };
  sandMat.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, sandUniforms);
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec2 vLocal; varying vec2 vWorldXZ;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvLocal = position.xz; vWorldXZ = (modelMatrix * vec4(transformed, 1.0)).xz;');
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>\n${NOISE_GLSL}\n${STREAK_GLSL}\nuniform vec3 uSandNear, uSandFar, uShade; uniform vec2 uSandFade;\nvarying vec2 vLocal; varying vec2 vWorldXZ;`)
      .replace('#include <color_fragment>', /* glsl */ `#include <color_fragment>
        float sr = length(vLocal);                                   // 0 centre .. 1 outer edge of the apron
        float outer = smoothstep(uSandFade.x - 0.02, 1.0, sr);        // 0 at the grass rim .. 1 at the outer edge
        float streak = streakAt(vLocal);
        vec3 col = mix(uSandNear, uSandFar, smoothstep(0.0, 0.85, outer)); // warm by the grass, dusty grey-beige far outer
        col *= mix(0.88, 1.1, streak);                               // the brush strokes
        col = mix(col, uShade, 0.12 * (1.0 - outer) * smoothstep(0.0, 1.0, vLocal.y)); // a little shadow under the front edge
        diffuseColor.rgb *= col;
        // the fade: driven by distance, roughened by the streaks so it ends in dry-brush wisps, not a soft disc
        diffuseColor.a *= 1.0 - smoothstep(uSandFade.y, 1.0, outer + (streak - 0.5) * 0.45);`);
  };
  const sandDisc = new THREE.Mesh(new THREE.CircleGeometry(1, 160).rotateX(-Math.PI / 2), sandMat);
  sandDisc.scale.set(a * sand.reach, 1, b * sand.reach);
  sandDisc.position.y = 0.0005;
  sandDisc.renderOrder = -3;

  const group = new THREE.Group();
  group.add(sandDisc, soilDisc, blades);
  return {
    group,
    bladeCount: n / 5,
    sandReach: sand.reach,
    setTime(t: number) { uniforms.uTime.value = t; },
  };
}
