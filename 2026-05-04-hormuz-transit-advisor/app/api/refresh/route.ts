import { NextResponse } from "next/server";
import { fetchAllFeeds, mergeIncidents } from "@/lib/fetchFeeds";
import { loadIncidents, saveIncidents } from "@/lib/dataStore";

export async function POST() {
  const existing = await loadIncidents();
  const { fetched, perSource, errors } = await fetchAllFeeds();
  const { merged, added } = mergeIncidents(existing, fetched);
  await saveIncidents(merged);
  return NextResponse.json({
    ok: true,
    added,
    total: merged.length,
    perSource,
    errors,
  });
}

export async function GET() {
  return POST();
}
