import { promises as fs } from "node:fs";
import path from "node:path";
import type { EscortWindowEntry, Incident, Operator } from "./types";

const DATA_DIR = path.join(process.cwd(), "data");
const INCIDENTS_PATH = path.join(DATA_DIR, "incidents.json");
const OPERATORS_PATH = path.join(DATA_DIR, "operators.json");
const ESCORTS_PATH = path.join(DATA_DIR, "escorts.json");
const SUBSCRIBERS_PATH = path.join(DATA_DIR, "subscribers.jsonl");

async function readJson<T>(p: string, fallback: T): Promise<T> {
  try {
    const raw = await fs.readFile(p, "utf8");
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

export async function loadIncidents(): Promise<Incident[]> {
  const items = await readJson<Incident[]>(INCIDENTS_PATH, []);
  return [...items].sort((a, b) => Date.parse(b.timestamp) - Date.parse(a.timestamp));
}

export async function saveIncidents(incidents: Incident[]): Promise<void> {
  await fs.mkdir(DATA_DIR, { recursive: true });
  await fs.writeFile(INCIDENTS_PATH, JSON.stringify(incidents, null, 2), "utf8");
}

export async function loadOperators(): Promise<Operator[]> {
  return readJson<Operator[]>(OPERATORS_PATH, []);
}

export async function loadEscorts(): Promise<EscortWindowEntry[]> {
  const items = await readJson<EscortWindowEntry[]>(ESCORTS_PATH, []);
  return items.sort((a, b) => Date.parse(a.start) - Date.parse(b.start));
}

export async function appendSubscriber(email: string): Promise<void> {
  await fs.mkdir(DATA_DIR, { recursive: true });
  const line = JSON.stringify({ email, ts: new Date().toISOString() }) + "\n";
  await fs.appendFile(SUBSCRIBERS_PATH, line, "utf8");
}
