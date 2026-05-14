import { FARES, FareModeId } from "./fares";

export type OriginId =
  | "manhattan"
  | "newark"
  | "jfk"
  | "lga"
  | "hoboken"
  | "jersey_city";

export interface Origin {
  id: OriginId;
  name: string;
  hint: string;
}

export const ORIGINS: Origin[] = [
  { id: "manhattan", name: "Manhattan (Midtown / Penn)", hint: "NYC, NY" },
  { id: "newark", name: "Newark (Penn Station)", hint: "Newark, NJ" },
  { id: "jfk", name: "JFK Airport", hint: "Queens, NY" },
  { id: "lga", name: "LaGuardia Airport", hint: "Queens, NY" },
  { id: "hoboken", name: "Hoboken Terminal", hint: "Hoboken, NJ" },
  { id: "jersey_city", name: "Jersey City (Journal Sq)", hint: "Jersey City, NJ" },
];

export interface RouteOption {
  mode: FareModeId;
  modeLabel: string;
  priceUsd: number;
  originalUsd?: number;
  doorMinutes: number;
  transfers: number;
  pathSummary: string;
  reliability: "high" | "medium" | "low";
}

type OriginRoutes = Record<OriginId, RouteOption[]>;

const r = (
  mode: FareModeId,
  modeLabel: string,
  doorMinutes: number,
  transfers: number,
  pathSummary: string,
  reliability: RouteOption["reliability"],
  priceOverride?: number,
): RouteOption => {
  const fare = FARES[mode];
  return {
    mode,
    modeLabel,
    priceUsd: priceOverride ?? fare.baseUsd,
    originalUsd: fare.originalUsd,
    doorMinutes,
    transfers,
    pathSummary,
    reliability,
  };
};

export const ROUTES: OriginRoutes = {
  manhattan: [
    r("njt_train", "NJ Transit Train", 55, 1, "Penn Station NY → Secaucus → Meadowlands Rail", "high"),
    r("official_shuttle", "Official Fan Shuttle", 65, 0, "Port Authority → MetLife direct coach", "high"),
    r("path_walk", "PATH + NJT", 80, 2, "33rd St PATH → Hoboken/Secaucus → Meadowlands", "medium", 8.25),
    r("rideshare", "Rideshare", 50, 0, "Uber/Lyft via Lincoln Tunnel (surge likely)", "low", 110),
    r("drive_park", "Drive + Park", 60, 0, "I-495 → MetLife Lot, match-day parking pass", "low"),
  ],
  newark: [
    r("njt_train", "NJ Transit Train", 45, 1, "Newark Penn → Secaucus → Meadowlands Rail", "high"),
    r("official_shuttle", "Official Fan Shuttle", 50, 0, "Newark Penn → MetLife direct coach", "high"),
    r("path_walk", "PATH + NJT", 70, 2, "Newark PATH → Hoboken/Secaucus → Meadowlands", "medium", 8.25),
    r("rideshare", "Rideshare", 35, 0, "Uber/Lyft via NJ Turnpike", "medium", 75),
    r("drive_park", "Drive + Park", 35, 0, "NJ Turnpike → MetLife Lot", "low"),
  ],
  jfk: [
    r("official_shuttle", "Official Fan Shuttle", 90, 0, "JFK AirTrain → Jamaica → fan coach to MetLife", "high"),
    r("njt_train", "NJ Transit Train", 110, 3, "AirTrain → LIRR/E → Penn NY → NJT → Secaucus → Meadowlands", "medium"),
    r("path_walk", "PATH + NJT", 130, 4, "AirTrain → Subway → PATH → Secaucus → Meadowlands", "low", 11.25),
    r("rideshare", "Rideshare", 75, 0, "Uber/Lyft via Belt Pkwy + Lincoln Tunnel", "low", 140),
    r("drive_park", "Drive + Park", 80, 0, "Rental via Belt Pkwy → MetLife Lot", "low"),
  ],
  lga: [
    r("official_shuttle", "Official Fan Shuttle", 75, 0, "LGA → fan coach to MetLife", "high"),
    r("njt_train", "NJ Transit Train", 95, 2, "Q70 → 74 St → Penn NY → NJT → Meadowlands", "medium"),
    r("path_walk", "PATH + NJT", 115, 3, "Q70 → 74 St → 33 St PATH → Secaucus → Meadowlands", "low", 11.0),
    r("rideshare", "Rideshare", 55, 0, "Uber/Lyft via GW Bridge or Lincoln Tunnel", "low", 120),
    r("drive_park", "Drive + Park", 55, 0, "Rental via GW Bridge → MetLife Lot", "low"),
  ],
  hoboken: [
    r("njt_train", "NJ Transit Train", 35, 1, "Hoboken Terminal → Secaucus → Meadowlands Rail", "high"),
    r("official_shuttle", "Official Fan Shuttle", 45, 0, "Hoboken Terminal → MetLife direct coach", "high"),
    r("path_walk", "PATH + NJT", 55, 2, "PATH Hoboken → Secaucus → Meadowlands", "medium", 8.25),
    r("rideshare", "Rideshare", 30, 0, "Uber/Lyft via NJ-3", "medium", 65),
    r("drive_park", "Drive + Park", 30, 0, "NJ-3 → MetLife Lot", "low"),
  ],
  jersey_city: [
    r("njt_train", "NJ Transit Train", 50, 2, "JSQ PATH → Hoboken/Newark → NJT → Meadowlands", "medium"),
    r("official_shuttle", "Official Fan Shuttle", 55, 0, "Journal Sq → MetLife coach link", "high"),
    r("path_walk", "PATH + NJT", 65, 2, "JSQ PATH → Hoboken → Secaucus → Meadowlands", "medium", 8.25),
    r("rideshare", "Rideshare", 35, 0, "Uber/Lyft via NJ-3", "medium", 70),
    r("drive_park", "Drive + Park", 35, 0, "NJ-3 → MetLife Lot", "low"),
  ],
};

export function rankOptions(originId: OriginId): RouteOption[] {
  const opts = ROUTES[originId] ?? [];
  return [...opts].sort((a, b) => a.priceUsd - b.priceUsd);
}

export function endsLate(endsHHMM: string): boolean {
  const [h, m] = endsHHMM.split(":").map(Number);
  return h > 22 || (h === 22 && m > 0);
}
