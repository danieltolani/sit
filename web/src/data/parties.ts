// The 22 registered political parties, read from https://www.inecnigeria.org (the list is baked into the
// Nuxt entry bundle as a JSON array, like the calendar). Only organisation-level fields are kept: officers'
// phone numbers, emails and addresses are on INEC's site but we have no need to republish them.
import snapshot from './parties.snapshot.json';

export type Party = { slug: string; name: string; acronym: string; logo: string; chairman: string; website?: string };

const BASE = 'https://www.inecnigeria.org';
const TTL_MS = 60 * 60 * 1000;
const localLogos = new Set(snapshot.map((p) => p.logo));

/** Pull the `[{"id":...,"acronym":...}]` array out of a JS chunk by bracket-matching, then JSON-parse it. */
export function extractParties(js: string): Party[] {
  const at = js.indexOf('"acronym":"');
  const start = at < 0 ? -1 : js.lastIndexOf('[{"id":"', at);
  if (start < 0) return [];
  let depth = 0, inStr = false, esc = false;
  for (let i = start; i < js.length; i++) {
    const c = js[i];
    if (inStr) { if (esc) esc = false; else if (c === '\\') esc = true; else if (c === '"') inStr = false; continue; }
    if (c === '"') inStr = true;
    else if (c === '[' || c === '{') depth++;
    else if (c === ']' || c === '}') {
      if (--depth === 0) {
        try {
          const rows = JSON.parse(js.slice(start, i + 1)) as Record<string, string>[];
          return rows.filter((r) => r.slug && r.name && r.acronym).map((r) => {
            const local = `/img/parties/${r.logo?.split('/').pop()}`;
            const website = r.website && r.website !== 'N/A' ? r.website : undefined;
            return { slug: r.slug, name: r.name, acronym: r.acronym, chairman: r.chairman ?? 'N/A', website, logo: localLogos.has(local) ? local : `${BASE}${r.logo}` };
          });
        } catch { return []; }
      }
    }
  }
  return [];
}

async function scrape(): Promise<Party[]> {
  const get = (url: string) => fetch(url, { headers: { 'user-agent': 'RAS-countdown/0.1 (hourly cache)' }, signal: AbortSignal.timeout(10_000) }).then((r) => (r.ok ? r.text() : Promise.reject(new Error(`${r.status} ${url}`))));
  const html = await get(`${BASE}/parties`);
  for (const chunk of new Set(html.match(/\/_nuxt\/[\w.-]+\.js/g) ?? [])) {
    const rows = extractParties(await get(BASE + chunk));
    if (rows.length) return rows;
  }
  throw new Error('party list not found in any chunk');
}

type Cache = { at: number; source: 'inec' | 'snapshot'; parties: Party[] };
let cache: Cache | undefined;

export async function getParties(): Promise<Cache> {
  if (cache && Date.now() - cache.at < TTL_MS) return cache;
  try {
    cache = { at: Date.now(), source: 'inec', parties: await scrape() };
  } catch (err) {
    console.warn('[parties] scrape failed, using', cache ? 'stale cache' : 'snapshot', err);
    cache = { at: Date.now() - TTL_MS + 5 * 60 * 1000, source: cache?.source ?? 'snapshot', parties: cache?.parties ?? (snapshot as Party[]) };
  }
  return cache;
}
