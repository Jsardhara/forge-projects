// Official prices reflect NY/NJ May 14, 2026 announcement.
// Train: $98 round-trip (down from $150). Shuttle: $20 round-trip (down from $80).
// Source: Al Jazeera, "World Cup train and shuttle bus ticket prices cut in New York, New Jersey" (2026-05-14).

export type FareModeId =
  | "njt_train"
  | "official_shuttle"
  | "path_walk"
  | "rideshare"
  | "drive_park";

export interface FareDef {
  id: FareModeId;
  baseUsd: number;
  originalUsd?: number;
  unit: "round-trip" | "one-way" | "per-ride" | "per-event";
  notes: string;
}

export const FARES: Record<FareModeId, FareDef> = {
  njt_train: {
    id: "njt_train",
    baseUsd: 98,
    originalUsd: 150,
    unit: "round-trip",
    notes:
      "NJ Transit Meadowlands Rail Line, Secaucus Junction to MetLife. Cut from $150 to $98.",
  },
  official_shuttle: {
    id: "official_shuttle",
    baseUsd: 20,
    originalUsd: 80,
    unit: "round-trip",
    notes: "Coach USA / NJ Transit fan shuttle network. Cut from $80 to $20.",
  },
  path_walk: {
    id: "path_walk",
    baseUsd: 5.5,
    unit: "round-trip",
    notes: "PATH train then transfer; combine with NJT or shuttle for last mile.",
  },
  rideshare: {
    id: "rideshare",
    baseUsd: 95,
    unit: "per-ride",
    notes: "Uber/Lyft surge estimate to MetLife on match day, one-way.",
  },
  drive_park: {
    id: "drive_park",
    baseUsd: 80,
    unit: "per-event",
    notes:
      "Match-day MetLife parking pass plus gas. Heavy queuing expected.",
  },
};
