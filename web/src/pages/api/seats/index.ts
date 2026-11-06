import type { APIRoute } from 'astro';
import { listSeats } from '../../../data/seats';
export const prerender = false;
export const GET: APIRoute = () => Response.json(listSeats());
