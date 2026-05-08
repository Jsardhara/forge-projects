import { z } from 'zod';

export const ClusterSchema = z.object({
  id: z.string(),
  location: z.string(),
  lat: z.number(),
  lng: z.number(),
  status: z.enum(['confirmed', 'suspected', 'monitoring']),
  cases: z.number().int().nonnegative(),
  suspected: z.number().int().nonnegative(),
  updated: z.string(),
  source_url: z.string().url(),
  source_label: z.string(),
  note: z.string(),
});
export type Cluster = z.infer<typeof ClusterSchema>;

export const ShipSchema = z.object({
  name: z.string(),
  operator: z.string(),
  route: z.string(),
  dates: z.object({ start: z.string(), end: z.string() }),
  ports: z.array(z.object({ name: z.string(), date: z.string() })),
  status: z.string(),
  advisory: z.string(),
});
export type Ship = z.infer<typeof ShipSchema>;
