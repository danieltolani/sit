// Figures from the INEC World Press Conference & National Stakeholders Meeting (ARISE News broadcast),
// the "100 days to the 2027 general election" address by the INEC chairman.
// Source transcript: Assets/Media/VIDS + Transcripts/Transcripts/INEC-WORLD-PRESS-CONFERENCE-NATIONAL-STAKEHOLDERS-MEETING_ARISE_NEWS.txt
// Conference date: ~2026-10-08 (inferred: "exactly 100 days" before 2027-01-16).
//
// The transcript is auto-generated and garbled in places. Rules used here:
//   - a value is stored only if it is clear, or if it reconciles with a percentage/total the chairman also stated;
//   - otherwise it is `null` and the heard text is kept in `heard` so it can be checked against the video.
// `at` is the transcript timestamp (HH:MM:SS) where the figure is spoken.

export const source = {
  event: 'INEC World Press Conference & National Stakeholders Meeting (100 days to 2027 general election)',
  speaker: 'INEC Chairman',
  broadcaster: 'ARISE News',
  approxDate: '2026-10-08',
};

export const register = {
  at: '00:40:20',
  // TODO(verify): the user heard "100,000,003" live; the transcript says "103 million" (00:40:20-00:41:26) and "103.43 million" (00:44:56-00:46:13),
  // and male + female + every percentage reconcile to 103,428,715. Team member to confirm against the video before this is shown.
  total: 103_428_715, // male + female; chairman said "103 million" then "103.43 million"
  male: { count: 53_528_218, pct: 51.75 },
  female: { count: 49_900_497, pct: 48.25 }, // transcript says "42.25%"; 48.25% is what the counts give
  byAge: [
    { band: '18-34', count: 29_777_576, pct: 28.79 }, // transcript "29,000,777 576"; reconciles with 28.79%
    { band: '35-49', count: 43_265_946, pct: 41.83 },
    { band: '50-69', count: 22_982_900, pct: 22.22 },
    { band: '70+', count: 7_402_291, pct: 7.16 },
  ],
  // Age bands sum to 103,428,713 (2 short of the total): rounding in INEC's own table.
};

export const registration2025_26 = {
  at: '00:39:19',
  // Continuous Voter Registration (CVR)
  phases: [
    { phase: 1, from: '2025-08-25', to: '2025-12-10', registered: null as number | null, heard: '2,000,611 266', impliedByTotal: 2_782_589 },
    { phase: 2, from: '2026-01-05', to: '2026-04-17', registered: 4_121_835 },
    { phase: 3, from: '2026-05-11', to: '2026-07-26', registered: 3_867_997, note: 'first online registration portal + printable/downloadable PVC' },
  ],
  total: 10_772_421,
  // CHECK: phases 2+3 = 7,989,832, so phase 1 should be 2,782,589 to match the stated total; the transcript's phase-1 figure is unreadable.
};

export type StateCount = { rank: number; state: string | null; registered: number | null; heard: string; note?: string };
export const statesTop10: StateCount[] = [
  { rank: 1, state: 'Lagos', registered: 7_488_633, heard: 'Lagos 7,488,633' },
  { rank: 2, state: 'Kano', registered: null, heard: 'Kano 6,000,570 276', note: 'number garbled' },
  { rank: 3, state: 'Kaduna', registered: 4_662_640, heard: 'Cardona 4,662,640' },
  { rank: 4, state: 'Katsina', registered: 3_876_051, heard: 'Casino 3,876,051' },
  { rank: 5, state: 'Rivers', registered: 3_736_434, heard: 'River 3,736,434' },
  { rank: 6, state: null, registered: 3_588_111, heard: '"Your state" 3,588,111', note: 'state name misheard; possibly Oyo' },
  { rank: 7, state: 'Delta', registered: 3_525_988, heard: 'Delta 3,525,988' },
  { rank: 8, state: null, registered: 3_057_225, heard: '"When we state" 3,057,225', note: 'state name misheard' },
  { rank: 9, state: null, registered: 3_037_981, heard: '"States" 3,037,981', note: 'state name not captured' },
  { rank: 10, state: 'Bauchi', registered: 3_012_547, heard: 'Bauchi 3,012,547' },
];
export const statesBottom5: StateCount[] = [
  // Chairman read these from the bottom of the table upward; several names/numbers are unreliable.
  { rank: -1, state: null, registered: 1_055_708, heard: '"a state" 1,055,708', note: 'state name missing' },
  { rank: -2, state: 'Bayelsa', registered: null, heard: 'Bayelsa 1,000,200 691', note: 'number garbled' },
  { rank: -3, state: null, registered: null, heard: '"The EFCC" 1,000,732 43', note: 'name and number garbled' },
  { rank: -4, state: null, registered: 1_733_641, heard: '"UV state" 1,733,641', note: 'state name misheard' },
  { rank: -5, state: 'Gombe', registered: 1_768_566, heard: 'Gumby 1,768,566' },
];
// CHECK: the order read ("followed by") implies ascending values, which Bayelsa/"EFCC" as heard do not satisfy, so those three need the video.

export const personsWithDisabilities = {
  at: '00:44:56',
  total: 232_658, // 0.23% of register
  categories: [
    { name: 'Others', count: 101_183, pct: 43.49 },
    { name: 'Albinism', count: 44_020, pct: 18.92 },
    { name: 'Physical impediment', count: 27_141, pct: 11.67 },
    { name: 'Blindness', count: 19_936, pct: 8.57 },
    { name: 'Deafness', count: 14_326, pct: 6.16 },
    { name: 'Autism', count: 8_832, pct: 3.8 },
    { name: 'Cognitive / learning', count: 7_723, pct: 3.32 },
    { name: '"little stutter" (speech impairment?)', count: 5_755, pct: 2.47 }, // label unclear
    { name: 'Down syndrome', count: 2_080, pct: 0.89 }, // transcript "eight 9%"
    { name: 'Spinal cord injury', count: 1_656, pct: 0.71 },
  ],
  // Categories sum to 232,652 (6 short of the total).
};

export const candidates = {
  at: '00:50:00',
  registeredParties: 22,
  presidential: {
    submittedBy: 18, // parties
    candidates: 36, // president + vice-president names, i.e. 18 tickets
    noCandidate: ['Accord (A)', 'APGA', 'Youth Party (YP)'], // heard "Accord, Abgar and Youth Party"; "Abgar" = APGA per INEC's party list
    withdrew: 'NNPP withdrew its presidential nomination during the substitution window',
  },
  senate: { parties: 21, candidates: 1_313 },
  reps: { parties: 21, candidates: 3_547 },
  governorship: { parties: 21, candidates: null as number | null, heard: '936' }, // heard "936 governorship to Deputy Governorship candidates"; implausible
  stateAssembly: { parties: 21, candidates: 9_692 },
  complaintsResolved: 112,
  keyDates: {
    senateRepsParticularsPublished: '2026-08-01',
    senateRepsFinalList: '2026-09-12',
    governorshipParticularsPublished: '2026-08-29',
    governorshipFinalList: '2026-10-10',
  },
};

export const logistics = {
  pollingUnits: 176_846, // heard three times; once garbled as "176,008 46"
  registrationAreas: 8_838, // once heard "8809"
  lgas: 774,
  statesPlusFct: 37,
  newBvas: 57_000,
  vehicles: '100,000+',
  boats: 4_000,
  adHocStaffPerElection: 707_384,
  adHocStaffTotal: 1_414_768, // two elections
  adHocStaff2023: 'about 1.2 million',
  pollingUnitsOpen: '07:30', // CHECK: INEC calendar page says voting 08:30-14:30
  restoredStateConstituencies: 27,
  newStateConstituencies: 2,
  timetable: { milestones: 14, completed: 9, revisedOn: '2026-02-26' },
  recruitmentPortal: { opened: '2026-09-18', closes: '2026-11-18' },
  bvasStressTest: { from: '2026-10-23', to: '2026-10-28' },
};

export const keyDates = [
  { date: '2026-10-09/15', what: 'Register of voters displayed for public scrutiny (Electoral Act s.19)' },
  { date: '2026-10-16', what: 'PVC collection continues at all LGA offices' },
  { date: '2026-11', what: 'Mock accreditation exercise; election observers accredited' },
  { date: '2026-12-13', what: 'Strategic briefing for registration-area technical support' },
  { date: '2026-12-15', what: 'Register of voters presented to political parties' },
  { date: '2027-01-16', what: 'Presidential / National Assembly election' },
  { date: '2027-02-06', what: 'Governorship / State House of Assembly election' },
];
