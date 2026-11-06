// Every number we show is a Claim: a value plus the evidence behind it.
// The hover/tap card (components/Stat.astro) renders whatever sources are attached, so adding
// evidence = adding to `sources`; verifying = a person changing `status` and filling `verifiedBy`.
import { register, logistics } from './inec-stats';

export type Status = 'unverified' | 'verified' | 'disputed';
export type Source = {
  kind: 'video' | 'website' | 'press' | 'document' | 'testimony';
  label: string;
  url?: string;
  /** Video timestamp, HH:MM:SS. */
  t?: string;
  /** What the source actually said, verbatim where possible. */
  heard?: string;
  /** The value this source gives, when it differs from the claim's value. */
  value?: string;
  note?: string;
};
export type Claim = {
  id: string;
  label: string;
  value: number | string | null;
  status: Status;
  sources: Source[];
  verifiedBy?: string;
  verifiedAt?: string;
};

// Video sources link to this at their `t` timestamp (as &t=<seconds>s).
export const VIDEO_URL = 'https://www.youtube.com/watch?v=tVDmUqcOLck';
export const VIDEO_ID = new URL(VIDEO_URL).searchParams.get('v')!;
const ARISE = 'ARISE News: INEC World Press Conference (100 days to 2027)';
const video = (t: string, heard: string, note?: string): Source => ({ kind: 'video', label: ARISE, url: VIDEO_URL, t, heard, note });
const INEC = 'https://www.inecnigeria.org';

export const toSeconds = (t: string) => t.split(':').reduce((s, n) => s * 60 + +n, 0);
export const videoLink = (url: string | undefined, t: string | undefined) => (url && t ? `${url}${url.includes('?') ? '&' : '?'}t=${toSeconds(t)}s` : url);

export const claims: Claim[] = [
  {
    id: 'register-total',
    label: 'Registered voters',
    value: register.total,
    status: 'disputed',
    sources: [
      video('00:40:20', '"stands at 103 million"'),
      video('00:44:56', '"103.43 million"'),
      { kind: 'document', label: 'Derived: male + female', value: '103,428,715', note: 'Male 53,528,218 + female 49,900,497; all stated percentages reconcile.' },
      { kind: 'website', label: 'inecnigeria.org home page', url: INEC, value: '93M+', note: 'Likely the 2023 figure; site not updated.' },
      { kind: 'testimony', label: 'Heard live by team', value: '100,000,003', note: 'Conflicts with the transcript. Needs a listen-back.' },
    ],
  },
  {
    id: 'register-male',
    label: 'Male voters',
    value: register.male.count,
    status: 'unverified',
    sources: [video('00:43:03', '"53 million 528 218, representing 51.75%"')],
  },
  {
    id: 'register-female',
    label: 'Female voters',
    value: register.female.count,
    status: 'unverified',
    sources: [video('00:43:03', '"49,900,497, representing 42.25%"', 'Transcript says 42.25%; the counts give 48.25%.')],
  },
  {
    id: 'polling-units',
    label: 'Polling units',
    value: logistics.pollingUnits,
    status: 'unverified',
    sources: [
      video('00:55:51', '"176,008 46 polling units"', 'Garbled here; the same figure is clear at 01:11:39 and 01:20:04.'),
      { kind: 'website', label: 'inecnigeria.org/polling-units', url: `${INEC}/polling-units`, value: '176,846', note: 'Agrees.' },
    ],
  },
  {
    id: 'registration-areas',
    label: 'Registration areas',
    value: logistics.registrationAreas,
    status: 'disputed',
    sources: [
      video('00:55:51', '"8838 registration areas"', 'Heard four times as 8,838.'),
      video('01:02:15', '"8809 registration area centers"', 'Heard once as 8,809.'),
      { kind: 'website', label: 'inecnigeria.org/polling-units', url: `${INEC}/polling-units`, value: '8,809' },
    ],
  },
  {
    id: 'adhoc-staff',
    label: 'Ad hoc staff per election',
    value: logistics.adHocStaffPerElection,
    status: 'unverified',
    sources: [video('01:19:20', '"707,384 ad hoc staff personnel"', 'Same number for both elections: 1,414,768 in total (01:20:04).')],
  },
];
claims.push(
  { id: 'registered-parties', label: 'Registered political parties', value: 22, status: 'unverified', sources: [
    video('00:49:59', '"18 out of the 22 registered political parties"'),
    { kind: 'website', label: 'inecnigeria.org/parties', url: `${INEC}/parties`, value: '22', note: 'Agrees: the site lists 22 parties (see /parties here).' },
  ] },
  { id: 'presidential-parties', label: 'Parties with a presidential candidate', value: 18, status: 'unverified', sources: [
    video('00:49:59', '"18 out of the 22 registered political parties submitted 36 presidential stroke vice presidential candidates"', '36 names = 18 president/VP tickets. NNPP later withdrew (00:50:43), so the live count may be 17.'),
  ] },
  { id: 'senate-candidates', label: 'Senate candidates', value: 1_313, status: 'unverified', sources: [video('00:50:43', '"21 of 22 political parties sponsored 1313 candidates for the Senate"')] },
  { id: 'reps-candidates', label: 'House of Representatives candidates', value: 3_547, status: 'unverified', sources: [video('00:50:43', '"…and 3547 candidates for the House of Representatives"')] },
  { id: 'governorship-candidates', label: 'Governorship candidates', value: null, status: 'unverified', sources: [video('00:51:38', '"936 governorship to Deputy Governor ship candidates"', 'Garbled and implausibly low; needs a listen-back.')] },
  { id: 'state-assembly-candidates', label: 'State House of Assembly candidates', value: 9_692, status: 'unverified', sources: [video('00:51:38', '"…and 9692 state House of Assembly candidates"')] },
);
export const claimById = (id: string) => claims.find((c) => c.id === id)!;
