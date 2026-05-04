import { NextResponse } from "next/server";
import { appendSubscriber } from "@/lib/dataStore";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

export async function POST(req: Request) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  const email = (body as { email?: unknown })?.email;
  if (typeof email !== "string" || !EMAIL_RE.test(email) || email.length > 254) {
    return NextResponse.json({ error: "Valid email required." }, { status: 400 });
  }

  try {
    await appendSubscriber(email.toLowerCase().trim());
  } catch (err) {
    return NextResponse.json(
      { error: `Failed to record subscription: ${(err as Error).message}` },
      { status: 500 },
    );
  }

  return NextResponse.json({ ok: true }, { status: 200 });
}
