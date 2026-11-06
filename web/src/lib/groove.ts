// Afrobeats groove layer: a rhythmic bounce laid over whatever dance clip is playing, so the body keeps the
// beat even when the clip is a gentle one. Each frame, after the clip has posed the skeleton, small extra
// rotations are added to a few bones: knees dip on every beat (hip drops, thighs fold, calves fold back),
// the chest dips with the knees and sways side to side every two beats, shoulders pulse alternately, the head
// nods a touch behind the beat. Everything scales with `amount`; 0 is off.
import * as THREE from 'three';

export type Groove = { amount: number; bpm: number };

const deg = THREE.MathUtils.degToRad;
const BONES = {
  hip: 'CC_Base_Hip', waist: 'CC_Base_Waist', spine1: 'CC_Base_Spine01', spine2: 'CC_Base_Spine02',
  head: 'CC_Base_Head', neck: 'CC_Base_NeckTwist01',
  lThigh: 'CC_Base_L_Thigh', rThigh: 'CC_Base_R_Thigh', lCalf: 'CC_Base_L_Calf', rCalf: 'CC_Base_R_Calf',
  lClav: 'CC_Base_L_Clavicle', rClav: 'CC_Base_R_Clavicle', lArm: 'CC_Base_L_Upperarm', rArm: 'CC_Base_R_Upperarm',
} as const;

// Which local axis each bone bends around on this rig (checked on the ActorCore/CC character: X folds forward,
// Z bends sideways, Y twists). If a new character comes in with a different rig, these are the lines to revisit.
const FOLD = new THREE.Vector3(1, 0, 0);
const SWAY = new THREE.Vector3(0, 0, 1);

export class GrooveLayer {
  private bones: Partial<Record<keyof typeof BONES, THREE.Object3D>> = {};
  private hipRest = 0;
  private q = new THREE.Quaternion();

  constructor(fig: THREE.Object3D, private groove: Groove) {
    for (const [k, name] of Object.entries(BONES) as [keyof typeof BONES, string][]) {
      const b = fig.getObjectByName(name);
      if (b) this.bones[k] = b;
    }
  }

  private add(bone: THREE.Object3D | undefined, axis: THREE.Vector3, rad: number) {
    if (!bone || !rad) return;
    bone.quaternion.multiply(this.q.setFromAxisAngle(axis, rad));
  }

  /** `time` is the dancer's own clock in seconds; `phase` offsets this dancer within the bar (0..1). */
  apply(time: number, phase = 0) {
    const a = this.groove.amount;
    if (a <= 0) return;
    const beats = time * this.groove.bpm / 60 + phase;
    const ph = beats * Math.PI * 2;              // one beat
    const dip = 0.5 - 0.5 * Math.cos(ph);         // 0 at the top, 1 at the bottom of each bounce
    const dip2 = 0.5 - 0.5 * Math.cos(ph * 2);    // double-time pulse for the shoulders
    const sway = Math.sin(ph / 2);                // left/right every two beats
    const nod = 0.5 - 0.5 * Math.cos(ph - 0.6);   // head follows a touch late
    const b = this.bones;

    // knees: the bounce. Hip comes down, thighs fold forward, calves fold back so the feet stay roughly put.
    if (b.hip) {
      b.hip.position.y -= 0.025 * dip * a;     // model units (the model is 2 tall)
    }
    this.add(b.lThigh, FOLD, deg(7) * dip * a);
    this.add(b.rThigh, FOLD, deg(7) * dip * a);
    this.add(b.lCalf, FOLD, deg(-13) * dip * a);
    this.add(b.rCalf, FOLD, deg(-13) * dip * a);

    // chest: dips with the knees, sways side to side, a little twist against the sway
    this.add(b.waist, FOLD, deg(3) * dip * a);
    this.add(b.spine1, FOLD, deg(4) * dip * a);
    this.add(b.spine1, SWAY, deg(5) * sway * a);
    this.add(b.spine2, FOLD, deg(3) * dip * a);
    this.add(b.spine2, SWAY, deg(-3) * sway * a);

    // shoulders: pulse on the half-beat, alternating lead
    this.add(b.lClav, FOLD, deg(6) * dip2 * a * (0.6 + 0.4 * sway));
    this.add(b.rClav, FOLD, deg(6) * dip2 * a * (0.6 - 0.4 * sway));
    this.add(b.lArm, FOLD, deg(-4) * dip2 * a);
    this.add(b.rArm, FOLD, deg(-4) * dip2 * a);

    // head: nod
    this.add(b.neck, FOLD, deg(3) * nod * a);
    this.add(b.head, FOLD, deg(4) * nod * a);
    this.add(b.head, SWAY, deg(-2) * sway * a);
  }
}
