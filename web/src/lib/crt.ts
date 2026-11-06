// CRT / VHS look, as a post-process. The scene is rendered to an off-screen texture, then drawn to the canvas
// through one shader that does, in this order: tape wobble and the odd tracking tear (horizontal jitter per
// line), VHS softness and colour bleed (red and blue pulled apart, luma slightly smeared), tube curvature,
// phosphor scanlines and aperture grille, a slow rolling head-switch bar, grain, vignette, and a tape-ish grade
// (lifted blacks, a touch less contrast, a touch more chroma). Every one of those is a dial in `CRTLook`;
// 0 turns it off. `enabled: false` skips the pass entirely.
import * as THREE from 'three';

export type CRTLook = {
  enabled: boolean;
  curvature: number;   // tube bulge (0 = flat). 0.08 is a gentle 90s set, 0.2 is a fishbowl
  scanlines: number;   // darkness of the lines between scanlines (0..1)
  scanPitch: number;   // scanline spacing in CSS pixels
  grille: number;      // RGB aperture-grille strength (0..1), very subtle
  bleed: number;       // chroma separation in CSS pixels
  softness: number;    // horizontal luma blur in CSS pixels (VHS resolution loss)
  wobble: number;      // tape jitter: horizontal offset as a fraction of the width
  tracking: number;    // strength of the occasional tracking tear band (0..1)
  rollBar: number;     // brightness of the slow rolling bar (0..1)
  grain: number;       // noise amount (0..1)
  vignette: number;    // corner darkening (0..1)
  grade: number;       // how far towards the tape grade (0 = untouched colours)
  /** Page background painted behind the scene so the effect covers the whole frame, as [centre, mid, edge]. */
  background: [string, string, string] | null;
};

export const CLEAN_LOOK: CRTLook = {
  enabled: false, curvature: 0, scanlines: 0, scanPitch: 3, grille: 0, bleed: 0, softness: 0, wobble: 0,
  tracking: 0, rollBar: 0, grain: 0, vignette: 0, grade: 0, background: null,
};

export const VHS_LOOK: CRTLook = {
  enabled: true,
  curvature: 0.07,
  scanlines: 0.28,
  scanPitch: 3,
  grille: 0.01,
  bleed: 1.84,
  softness: 0.2,
  wobble: 0.0002,
  tracking: 0.7,
  rollBar: 0.06,
  grain: 0.07,
  vignette: 1.32,
  grade: 0.96,
  background: ['#f3f3f3', '#e6e6e6', '#d8d8d8'], // the page's own radial gradient
};

const vert = /* glsl */ `varying vec2 vUv; void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }`;

const frag = /* glsl */ `
precision highp float;
uniform sampler2D tScene;
uniform vec2 uRes;          // drawing-buffer size in device px
uniform float uDpr, uTime;
uniform float uCurvature, uScanlines, uScanPitch, uGrille, uBleed, uSoftness, uWobble, uTracking, uRollBar, uGrain, uVignette, uGrade;
uniform vec3 uBg0, uBg1, uBg2;
uniform float uHasBg;
varying vec2 vUv;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise1(float x) { float i = floor(x), f = fract(x); return mix(hash(vec2(i, 0.0)), hash(vec2(i + 1.0, 0.0)), f * f * (3.0 - 2.0 * f)); }

// scene over the page gradient (the scene texture is premultiplied: colour already × alpha)
vec3 fetch(vec2 uv) {
  vec4 s = texture2D(tScene, uv);
  if (uHasBg < 0.5) return s.rgb;
  vec2 d = (uv - 0.5) / vec2(0.75, 0.70);           // ellipse 75% 70% at 50% 50%
  float r = length(d);
  vec3 bg = r < 0.6 ? mix(uBg0, uBg1, r / 0.6) : mix(uBg1, uBg2, clamp((r - 0.6) / 0.4, 0.0, 1.0));
  return s.rgb + bg * (1.0 - s.a);
}

void main() {
  vec2 uv = vUv;
  vec2 px = 1.0 / uRes;

  // --- tube curvature (corners stay pinned, so nothing goes black)
  vec2 c = uv * 2.0 - 1.0;
  float r2 = dot(c, c);
  c *= (1.0 + uCurvature * r2) / (1.0 + 2.0 * uCurvature);
  uv = c * 0.5 + 0.5;

  // --- tape wobble: every line drifts a little, and now and then a tracking band tears across
  float line = floor(uv.y * uRes.y / uDpr);
  float jitter = (noise1(line * 0.07 + uTime * 9.0) - 0.5) * 2.0 * uWobble;
  float bandY = fract(uTime * 0.11);                           // the tear travels up the frame slowly
  float band = smoothstep(0.0, 0.015, uv.y - bandY) * smoothstep(0.06, 0.02, uv.y - bandY);
  float gust = smoothstep(0.86, 1.0, noise1(uTime * 0.9 + 3.7)); // tears only happen now and then
  float tear = band * gust * uTracking;
  uv.x += jitter + tear * (0.012 + 0.02 * (hash(vec2(line, floor(uTime * 24.0))) - 0.5));

  // --- VHS softness + chroma bleed (luma smeared sideways, red and blue pulled apart)
  float sx = uSoftness * uDpr;
  float bx = uBleed * uDpr * (1.0 + tear * 6.0);
  vec3 col;
  col.r = fetch(uv - vec2(bx, 0.0) * px).r;
  col.b = fetch(uv + vec2(bx, 0.0) * px).b;
  col.g = (fetch(uv).g * 2.0 + fetch(uv - vec2(sx, 0.0) * px).g + fetch(uv + vec2(sx, 0.0) * px).g) * 0.25;
  // smear the luma a touch so the picture loses the crisp digital edge
  vec3 soft = (fetch(uv - vec2(sx * 1.5, 0.0) * px) + fetch(uv + vec2(sx * 1.5, 0.0) * px)) * 0.5;
  col = mix(col, soft, 0.35 * step(0.001, uSoftness));

  // --- tape grade: lifted blacks, a bit less contrast, a bit more chroma
  float lum = dot(col, vec3(0.299, 0.587, 0.114));
  vec3 graded = mix(vec3(lum), col, 1.18);                      // more chroma
  graded = graded * 0.9 + 0.035;                                // lift + compress
  graded = mix(graded, graded * vec3(1.02, 1.0, 0.96), 0.5);    // warm
  col = mix(col, graded, uGrade);

  // --- phosphor: scanlines + aperture grille
  float pitch = max(1.0, uScanPitch * uDpr);
  float scan = 0.5 + 0.5 * cos(gl_FragCoord.y * 6.2831853 / pitch);
  col *= 1.0 - uScanlines * scan * scan;
  float cell = mod(floor(gl_FragCoord.x / max(1.0, uDpr)), 3.0);
  vec3 grille = vec3(cell == 0.0 ? 1.0 : 0.0, cell == 1.0 ? 1.0 : 0.0, cell == 2.0 ? 1.0 : 0.0);
  col *= 1.0 - uGrille + uGrille * (0.7 + 0.9 * grille);

  // --- rolling head-switch bar
  float roll = fract(uTime * 0.07);
  float bar = smoothstep(0.0, 0.12, uv.y - roll) * smoothstep(0.25, 0.13, uv.y - roll);
  col *= 1.0 + uRollBar * bar;

  // --- grain
  col += (hash(gl_FragCoord.xy + fract(uTime) * 1000.0) - 0.5) * uGrain;

  // --- vignette
  vec2 v = vUv * (1.0 - vUv);
  col *= mix(1.0, pow(clamp(16.0 * v.x * v.y, 0.0, 1.0), 0.3), uVignette);

  gl_FragColor = vec4(col, 1.0);
  #include <colorspace_fragment>
}`;

export class CRTPass {
  private target: THREE.WebGLRenderTarget;
  private quad: THREE.Mesh;
  private quadScene = new THREE.Scene();
  private quadCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  private uniforms: Record<string, THREE.IUniform>;

  constructor(private renderer: THREE.WebGLRenderer, look: CRTLook) {
    const size = renderer.getDrawingBufferSize(new THREE.Vector2());
    this.target = new THREE.WebGLRenderTarget(size.x, size.y, { samples: 4, depthBuffer: true });
    this.uniforms = {
      tScene: { value: this.target.texture },
      uRes: { value: size },
      uDpr: { value: renderer.getPixelRatio() },
      uTime: { value: 0 },
      uCurvature: { value: 0 }, uScanlines: { value: 0 }, uScanPitch: { value: 3 }, uGrille: { value: 0 },
      uBleed: { value: 0 }, uSoftness: { value: 0 }, uWobble: { value: 0 }, uTracking: { value: 0 },
      uRollBar: { value: 0 }, uGrain: { value: 0 }, uVignette: { value: 0 }, uGrade: { value: 0 },
      uBg0: { value: new THREE.Color() }, uBg1: { value: new THREE.Color() }, uBg2: { value: new THREE.Color() },
      uHasBg: { value: 0 },
    };
    this.setLook(look);
    const mat = new THREE.ShaderMaterial({ uniforms: this.uniforms, vertexShader: vert, fragmentShader: frag, depthTest: false, depthWrite: false });
    this.quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), mat);
    this.quad.frustumCulled = false;
    this.quadScene.add(this.quad);
  }

  setLook(look: CRTLook) {
    const u = this.uniforms;
    u.uCurvature.value = look.curvature; u.uScanlines.value = look.scanlines; u.uScanPitch.value = look.scanPitch;
    u.uGrille.value = look.grille; u.uBleed.value = look.bleed; u.uSoftness.value = look.softness;
    u.uWobble.value = look.wobble; u.uTracking.value = look.tracking; u.uRollBar.value = look.rollBar;
    u.uGrain.value = look.grain; u.uVignette.value = look.vignette; u.uGrade.value = look.grade;
    u.uHasBg.value = look.background ? 1 : 0;
    if (look.background) {
      u.uBg0.value.set(look.background[0]); u.uBg1.value.set(look.background[1]); u.uBg2.value.set(look.background[2]);
    }
  }

  /** Call after renderer.setSize. */
  resize() {
    const size = this.renderer.getDrawingBufferSize(new THREE.Vector2());
    this.target.setSize(size.x, size.y);
    this.uniforms.uRes.value = size;
    this.uniforms.uDpr.value = this.renderer.getPixelRatio();
  }

  render(scene: THREE.Scene, camera: THREE.Camera, time: number) {
    this.uniforms.uTime.value = time;
    const r = this.renderer;
    r.setRenderTarget(this.target);
    r.setClearColor(0x000000, 0);
    r.clear();
    r.render(scene, camera);
    r.setRenderTarget(null);
    r.render(this.quadScene, this.quadCam);
  }
}
