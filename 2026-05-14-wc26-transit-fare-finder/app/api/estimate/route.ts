import { NextRequest, NextResponse } from "next/server";
import { rankOptions, OriginId, endsLate } from "@/lib/routes";
import matches from "@/data/matches.json";

export const dynamic = "force-static";

interface MatchEntry {
  id: string;
  label: string;
  teams: string;
  date: string;
  kickoff: string;
  endsApprox: string;
  venue: string;
}

const MATCHES = matches as MatchEntry[];

export async function POST(req: NextRequest) {
  let body: { origin?: OriginId; date?: string } = {};
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const origin = body.origin;
  const date = body.date;

  if (!origin || !date) {
    return NextResponse.json(
      { error: "origin and date are required" },
      { status: 400 },
    );
  }

  const match = MATCHES.find((m) => m.date === date) ?? null;
  const options = rankOptions(origin).map((o) => ({
    ...o,
    lastReturnWarn: match ? endsLate(match.endsApprox) : false,
  }));

  if (options.length === 0) {
    return NextResponse.json(
      { error: `No routes for origin ${origin}` },
      { status: 404 },
    );
  }

  return NextResponse.json({
    origin,
    date,
    match,
    options,
    generatedAt: new Date().toISOString(),
  });
}
