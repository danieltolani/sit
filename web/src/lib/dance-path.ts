// Musical-chairs motion: the clip drives everything.
//
// A dancer's clip carries its own travel: besides the bone tracks it has two tracks on the figure itself
// ("Mover.position", "Mover.quaternion"), so playing the clip moves the dancer round the chair. Nothing in the
// render loop pushes or rotates the figures, and pausing the clip (e.g. when the music stops) stops them dead.
//
// Custom dances: export them from Blender with their travel on the armature root and convert that root motion
// into these two tracks (or animate an object named "Mover"); they then play with no code changes.
//
// Placeholders: the downloaded ActorCore clips dance in place, so `withRingPath` bakes a path into them. The path
// is measured from the dance's own feet: the dancer only moves forward while a planted foot pushes back, so when
// the dance pauses, the dancer pauses. The distance is then scaled very slightly so that one loop of the clip
// covers a whole number of laps, which keeps the loop seamless.
import * as THREE from 'three';

export const MOVER = 'Mover'; // name the figure's root object must have for the travel tracks to bind to it

/** An ellipse (half-axes a, b on the ground) walked clockwise as seen from above, by arc length. */
export function ringPath(a: number, b: number, samples = 720) {
  const len = new Float64Array(samples + 1);
  let prevX = a, prevZ = 0;
  for (let i = 1; i <= samples; i++) {
    const th = -(i / samples) * Math.PI * 2; // theta decreases: the direction the original walkers went
    const x = a * Math.cos(th), z = b * Math.sin(th);
    len[i] = len[i - 1] + Math.hypot(x - prevX, z - prevZ);
    prevX = x; prevZ = z;
  }
  const length = len[samples];
  /** Point and facing at arc length s (any value; wraps). */
  const at = (s: number) => {
    s = ((s % length) + length) % length;
    let lo = 0, hi = samples;
    while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (len[mid] <= s) lo = mid; else hi = mid; }
    const f = (s - len[lo]) / (len[hi] - len[lo] || 1);
    const th = -((lo + f) / samples) * Math.PI * 2;
    const x = a * Math.cos(th), z = b * Math.sin(th);
    const dx = a * Math.sin(th), dz = -b * Math.cos(th); // direction of travel
    return { x, z, yaw: Math.atan2(dx, dz) };             // the model faces +z
  };
  return { length, at };
}

/** How far the dance's feet would carry the body over one loop, sampled at `fps`. */
export function footTravel(actor: THREE.Object3D, clip: THREE.AnimationClip, scale: number, fps = 30, maxStep = 0.1) {
  const probe = actor.clone(true);
  const mixer = new THREE.AnimationMixer(probe);
  mixer.clipAction(clip).play();
  const feet = ['L', 'R'].map((s) => probe.getObjectByName(`CC_Base_${s}_Foot`)).filter(Boolean) as THREE.Object3D[];
  const steps = Math.max(2, Math.round(clip.duration * fps));
  const times = new Float32Array(steps + 1);
  const dist = new Float32Array(steps + 1);
  const p = new THREE.Vector3();
  let prevZ: number[] | undefined;
  for (let i = 0; i <= steps; i++) {
    const t = (i / steps) * clip.duration;
    mixer.setTime(i === steps ? clip.duration - 1e-4 : t);
    probe.updateMatrixWorld(true);
    // the planted foot is the lower one; its slide backwards (-z in the figure's space) is the stride
    const zs: number[] = [], ys: number[] = [];
    for (const f of feet) { p.setFromMatrixPosition(f.matrixWorld); ys.push(p.y); probe.worldToLocal(p); zs.push(p.z); }
    const k = ys[0] <= (ys[1] ?? Infinity) ? 0 : 1;
    const step = prevZ ? THREE.MathUtils.clamp((prevZ[k] - zs[k]) * scale, 0, maxStep) : 0;
    times[i] = t;
    dist[i] = (i ? dist[i - 1] : 0) + step;
    prevZ = zs;
  }
  mixer.stopAllAction();
  return { times, dist, total: dist[steps] };
}

/** A copy of `clip` that also travels round `path`, starting `startAt` along it. */
export function withRingPath(
  clip: THREE.AnimationClip,
  travel: ReturnType<typeof footTravel>,
  path: ReturnType<typeof ringPath>,
  startAt: number,
) {
  const laps = Math.max(1, Math.round(travel.total / path.length)); // whole laps per loop, so the loop is seamless
  const k = travel.total > 0 ? (laps * path.length) / travel.total : 0;
  const n = travel.times.length;
  const pos = new Float32Array(n * 3);
  const rot = new Float32Array(n * 4);
  const q = new THREE.Quaternion(), prev = new THREE.Quaternion(), up = new THREE.Vector3(0, 1, 0);
  for (let i = 0; i < n; i++) {
    const { x, z, yaw } = path.at(startAt + travel.dist[i] * k);
    pos.set([x, 0, z], i * 3);
    q.setFromAxisAngle(up, yaw);
    if (i && q.dot(prev) < 0) q.set(-q.x, -q.y, -q.z, -q.w); // keep neighbours on the same hemisphere
    rot.set([q.x, q.y, q.z, q.w], i * 4);
    prev.copy(q);
  }
  return new THREE.AnimationClip(clip.name + '@ring', clip.duration, [
    ...clip.tracks,
    new THREE.VectorKeyframeTrack(`${MOVER}.position`, travel.times, pos),
    new THREE.QuaternionKeyframeTrack(`${MOVER}.quaternion`, travel.times, rot),
  ]);
}
