export type IncidentKind = "attack" | "missile-near-miss" | "advisory" | "escort";

export interface Incident {
  id: string;
  kind: IncidentKind;
  title: string;
  summary: string;
  source: string;
  sourceUrl: string;
  timestamp: string; // ISO 8601
  location?: string;
  vessel?: string;
}

export interface EscortWindowEntry {
  id: string;
  authority: string;
  start: string;
  end: string;
  notes: string;
  sourceUrl?: string;
}

export interface Operator {
  name: string;
  status: "suspended" | "rerouted" | "monitoring";
  since: string;
  sourceUrl?: string;
}

export type RiskLevel = "GREEN" | "AMBER" | "RED" | "BLACK";

export interface RiskAssessment {
  level: RiskLevel;
  score: number;
  rationale: string;
  weightedCount: number;
  windowHours: number;
}
