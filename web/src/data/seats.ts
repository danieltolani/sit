// Placeholder seed data. Replace with a real DB once the data model settles.
export type SeatType = 'presidential' | 'governorship' | 'senate' | 'house-of-reps' | 'state-assembly';
export type Seat = {
  id: string;
  type: SeatType;
  office: string;
  candidate: string;
  party: string;
  reservedBy: number;
  /** Optional satirical "taken" line shown on the tag. */
  takenBy?: string;
};

const seats: Seat[] = [
  { id: 'president-1', type: 'presidential', office: 'Presidential', candidate: 'Candidate A', party: 'PTY-A', reservedBy: 0, takenBy: 'Reserved by Wike' },
  { id: 'president-2', type: 'presidential', office: 'Presidential', candidate: 'Peter Obi', party: 'PTY-B', reservedBy: 0 },
  { id: 'president-3', type: 'presidential', office: 'Presidential', candidate: 'Candidate C', party: 'PTY-C', reservedBy: 0 },
  { id: 'governor-1', type: 'governorship', office: 'Governorship', candidate: 'Candidate D', party: 'PTY-A', reservedBy: 0 },
];

// Module-level store: resets on server restart. Fine for the skeleton.
export const listSeats = (type?: SeatType) => (type ? seats.filter((s) => s.type === type) : seats);

// The five kinds of seat on the ballot. `election` matches the INEC calendar entry it is decided in
// (title prefix), so the page can show the live date/status from data/calendar.ts.
export const seatTypes: { slug: SeatType; name: string; blurb: string; election: string; claimId?: string }[] = [
  { slug: 'presidential', name: 'Presidential', blurb: 'One seat: President of the Federal Republic.', election: 'Presidential / National Assembly', claimId: 'presidential-parties' },
  { slug: 'governorship', name: 'Governorship', blurb: 'Governor seats in the participating states.', election: 'Governorship / State House', claimId: 'governorship-candidates' },
  { slug: 'senate', name: 'Senate', blurb: 'Senate seats in the National Assembly.', election: 'Presidential / National Assembly', claimId: 'senate-candidates' },
  { slug: 'house-of-reps', name: 'House of Representatives', blurb: 'Federal constituency seats in the National Assembly.', election: 'Presidential / National Assembly', claimId: 'reps-candidates' },
  { slug: 'state-assembly', name: 'State House of Assembly', blurb: 'State constituency seats in each state assembly.', election: 'Governorship / State House', claimId: 'state-assembly-candidates' },
];
export const getSeatType = (slug: string) => seatTypes.find((t) => t.slug === slug);
export const getSeat = (id: string) => seats.find((s) => s.id === id);
export function reserve(id: string, by = 1) {
  const seat = getSeat(id);
  if (!seat) return undefined;
  seat.reservedBy += by;
  return seat;
}

// Offices shown on the home page card. Placeholder numbers until real counts exist.
export type Office = { id: string; name: string; occupant: string; contestants: number; reservations: string };
export const offices: Office[] = [
  { id: 'presidential', name: 'Presidential', occupant: 'Bola Ahmad Tinubu', contestants: 35, reservations: '100m' },
];
