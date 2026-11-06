// INEC election calendar, scraped from https://www.inecnigeria.org/elections/calendar.
// The page is a Nuxt SPA with the table baked into one of its JS chunks (no API call),
// so we read the chunk list from the HTML and parse the `{sn,title,...}` literals.
export type Election = {
  sn: number;
  title: string;
  constituency: string;
  category: string;
  date: string;
  /** Moment polls open (08:30 WAT per INEC directives), ISO 8601. */
  startsAt: string;
  status: string;
};

const BASE = 'https://www.inecnigeria.org';
const TTL_MS = 60 * 60 * 1000;

const MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December'];
export function toISO(date: string): string | undefined {
  const m = date.match(/^(\w+) (\d{1,2}), (\d{4})$/);
  const mo = m && MONTHS.indexOf(m[1]);
  if (!m || mo === undefined || mo < 0) return undefined;
  return `${m[3]}-${String(mo + 1).padStart(2, '0')}-${m[2].padStart(2, '0')}T08:30:00+01:00`;
}

export function parseChunk(js: string): Election[] {
  const out: Election[] = [];
  const re = /\{sn:(\d+),title:"([^"]*)",constituency:"([^"]*)",category:"([^"]*)",date:"([^"]*)",status:"([^"]*)"\}/g;
  for (const m of js.matchAll(re)) {
    const startsAt = toISO(m[5]);
    if (startsAt) out.push({ sn: +m[1], title: m[2], constituency: m[3], category: m[4], date: m[5], startsAt, status: m[6] });
  }
  return out;
}

// Last known snapshot (2026-10-23), used if INEC is unreachable or the site changes shape.
const snapshot: Election[] = [
  ['GOMBE (Gombe/Kwami/Funakaye Federal Constituencies) Bye-Election', 'Federal Constituency, Gombe State', 'Bye-Election', 'September 19, 2026', 'Concluded'],
  ['BAUCHI (Disina and Sakwa State Constituencies) Bye-Election', 'State Constituency, Bauchi State', 'Bye-Election', 'September 19, 2026', 'Concluded'],
  ['DELTA (Udu State Constituency) Bye-Election', 'State Constituency, Delta State', 'Bye-Election', 'September 19, 2026', 'Concluded'],
  ['KANO (Dawakin Kudu State Constituency) Bye-Election', 'State Constituency, Kano State', 'Bye-Election', 'September 19, 2026', 'Concluded'],
  ['Presidential / National Assembly Election', 'Nationwide (36 States & FCT)', 'General Election', 'January 16, 2027', 'Upcoming'],
  ['Governorship / State House Of Assembly Election', 'Participating States & State Constituencies', 'Governorship', 'February 6, 2027', 'Upcoming'],
].map(([title, constituency, category, date, status], i) => ({ sn: i + 1, title, constituency, category, date, startsAt: toISO(date)!, status }));

async function scrape(): Promise<Election[]> {
  const get = (url: string) => fetch(url, { headers: { 'user-agent': 'RAS-countdown/0.1 (hourly cache)' }, signal: AbortSignal.timeout(10_000) }).then((r) => (r.ok ? r.text() : Promise.reject(new Error(`${r.status} ${url}`))));
  const html = await get(`${BASE}/elections/calendar`);
  const chunks = [...new Set(html.match(/\/_nuxt\/[\w.-]+\.js/g) ?? [])];
  for (const path of chunks) {
    const rows = parseChunk(await get(BASE + path));
    if (rows.length) return rows;
  }
  throw new Error('calendar table not found in any chunk');
}

type Cache = { at: number; source: 'inec' | 'snapshot'; elections: Election[] };
let cache: Cache | undefined;

export async function getCalendar(): Promise<Cache> {
  if (cache && Date.now() - cache.at < TTL_MS) return cache;
  try {
    cache = { at: Date.now(), source: 'inec', elections: await scrape() };
  } catch (err) {
    console.warn('[calendar] scrape failed, using', cache ? 'stale cache' : 'snapshot', err);
    cache = { at: Date.now() - TTL_MS + 5 * 60 * 1000, source: cache?.source ?? 'snapshot', elections: cache?.elections ?? snapshot }; // retry in 5 min
  }
  return cache;
}
