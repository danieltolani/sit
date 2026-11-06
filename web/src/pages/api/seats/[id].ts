import type { APIRoute } from 'astro';
import { reserve } from '../../../data/seats';
export const prerender = false;
// TODO: auth + access levels (e.g. PVC holders, proof-of-vote photo) decide the weight of `by`.
export const POST: APIRoute = ({ params }) => {
  const seat = reserve(params.id!);
  return seat ? Response.json(seat) : new Response('Not found', { status: 404 });
};
