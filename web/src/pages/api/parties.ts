import type { APIRoute } from 'astro';
import { getParties } from '../../data/parties';
export const prerender = false;
export const GET: APIRoute = async () => {
  const { at, source, parties } = await getParties();
  return Response.json({ fetchedAt: new Date(at).toISOString(), source, count: parties.length, parties }, { headers: { 'cache-control': 'public, max-age=300' } });
};
