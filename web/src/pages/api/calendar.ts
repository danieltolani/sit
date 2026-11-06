import type { APIRoute } from 'astro';
import { getCalendar } from '../../data/calendar';
export const prerender = false;
export const GET: APIRoute = async () => {
  const { at, source, elections } = await getCalendar();
  const next = elections.find((e) => e.status !== 'Concluded' && Date.parse(e.startsAt) > Date.now());
  return Response.json({ fetchedAt: new Date(at).toISOString(), source, next, elections }, { headers: { 'cache-control': 'public, max-age=300' } });
};
