// The 36 states, each with a governorship seat (the FCT has none, so it is not listed).
const names = [
  'Abia', 'Adamawa', 'Akwa Ibom', 'Anambra', 'Bauchi', 'Bayelsa', 'Benue', 'Borno', 'Cross River', 'Delta',
  'Ebonyi', 'Edo', 'Ekiti', 'Enugu', 'Gombe', 'Imo', 'Jigawa', 'Kaduna', 'Kano', 'Katsina', 'Kebbi', 'Kogi',
  'Kwara', 'Lagos', 'Nasarawa', 'Niger', 'Ogun', 'Ondo', 'Osun', 'Oyo', 'Plateau', 'Rivers', 'Sokoto',
  'Taraba', 'Yobe', 'Zamfara',
];

export type State = { slug: string; name: string };
export const states: State[] = names.map((name) => ({ name, slug: name.toLowerCase().replace(/\s+/g, '-') }));
export const getState = (slug: string) => states.find((s) => s.slug === slug.toLowerCase());
