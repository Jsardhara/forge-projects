import type { Incident, IncidentKind, RiskAssessment, RiskLevel } from "./types";

export const SEVERITY_WEIGHTS: Record<IncidentKind, number> = {
  attack: 3,
  "missile-near-miss": 2,
  advisory: 1,
  escort: 0,
};

export const RISK_BANDS: ReadonlyArray<{ level: RiskLevel; min: number; max: number }> = [
  { level: "GREEN", min: 0, max: 1 },
  { level: "AMBER", min: 2, max: 4 },
  { level: "RED", min: 5, max: 8 },
  { level: "BLACK", min: 9, max: Number.POSITIVE_INFINITY },
];

const HOUR = 60 * 60 * 1000;

export function assessRisk(
  incidents: ReadonlyArray<Incident>,
  now: Date = new Date(),
  windowHours = 24,
): RiskAssessment {
  const cutoff = now.getTime() - windowHours * HOUR;
  const recent = incidents.filter((i) => {
    const t = Date.parse(i.timestamp);
    return Number.isFinite(t) && t >= cutoff && t <= now.getTime();
  });

  let score = 0;
  const counts: Partial<Record<IncidentKind, number>> = {};
  for (const inc of recent) {
    score += SEVERITY_WEIGHTS[inc.kind] ?? 0;
    counts[inc.kind] = (counts[inc.kind] ?? 0) + 1;
  }

  const band = RISK_BANDS.find((b) => score >= b.min && score <= b.max) ?? RISK_BANDS[0];

  const parts: string[] = [];
  if (counts.attack) parts.push(`${counts.attack} attack${counts.attack > 1 ? "s" : ""}`);
  if (counts["missile-near-miss"])
    parts.push(`${counts["missile-near-miss"]} near-miss`);
  if (counts.advisory)
    parts.push(`${counts.advisory} advisor${counts.advisory > 1 ? "ies" : "y"}`);

  const summary = parts.length ? parts.join(", ") : "no weighted incidents";
  const rationale = `${summary} in last ${windowHours}h → weighted score ${score} (${band.level}).`;

  return {
    level: band.level,
    score,
    rationale,
    weightedCount: recent.length,
    windowHours,
  };
}

export function levelColor(level: RiskLevel): string {
  switch (level) {
    case "GREEN":
      return "#16a34a";
    case "AMBER":
      return "#d97706";
    case "RED":
      return "#dc2626";
    case "BLACK":
      return "#0a0a0a";
  }
}

export function levelLabel(level: RiskLevel): string {
  switch (level) {
    case "GREEN":
      return "Routine — no significant disruption";
    case "AMBER":
      return "Elevated — exercise caution";
    case "RED":
      return "High — active threats reported";
    case "BLACK":
      return "Severe — transit not advised";
  }
}
