interface IcsInput {
  uid: string;
  title: string;
  description: string;
  location: string;
  startLocal: string; // YYYYMMDDTHHMMSS local America/New_York
  durationMinutes: number;
}

const pad = (n: number) => String(n).padStart(2, "0");

const fmtUtc = (d: Date): string =>
  `${d.getUTCFullYear()}${pad(d.getUTCMonth() + 1)}${pad(d.getUTCDate())}T${pad(
    d.getUTCHours(),
  )}${pad(d.getUTCMinutes())}${pad(d.getUTCSeconds())}Z`;

const escapeText = (s: string): string =>
  s.replace(/\\/g, "\\\\").replace(/\n/g, "\\n").replace(/,/g, "\\,").replace(/;/g, "\\;");

/**
 * Build a minimal RFC 5545 VCALENDAR string.
 * Times are written as floating local time tagged with TZID=America/New_York.
 */
export function buildIcs(input: IcsInput): string {
  const dtStamp = fmtUtc(new Date());
  const dtEndLocal = addMinutes(input.startLocal, input.durationMinutes);

  const lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//WC26 Fare Finder//EN",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    "BEGIN:VEVENT",
    `UID:${input.uid}`,
    `DTSTAMP:${dtStamp}`,
    `DTSTART;TZID=America/New_York:${input.startLocal}`,
    `DTEND;TZID=America/New_York:${dtEndLocal}`,
    `SUMMARY:${escapeText(input.title)}`,
    `DESCRIPTION:${escapeText(input.description)}`,
    `LOCATION:${escapeText(input.location)}`,
    "END:VEVENT",
    "END:VCALENDAR",
    "",
  ];
  return lines.join("\r\n");
}

function addMinutes(localStamp: string, minutes: number): string {
  // localStamp = YYYYMMDDTHHMMSS
  const y = Number(localStamp.slice(0, 4));
  const mo = Number(localStamp.slice(4, 6)) - 1;
  const d = Number(localStamp.slice(6, 8));
  const h = Number(localStamp.slice(9, 11));
  const mi = Number(localStamp.slice(11, 13));
  const s = Number(localStamp.slice(13, 15));
  const dt = new Date(Date.UTC(y, mo, d, h, mi, s));
  dt.setUTCMinutes(dt.getUTCMinutes() + minutes);
  return `${dt.getUTCFullYear()}${pad(dt.getUTCMonth() + 1)}${pad(dt.getUTCDate())}T${pad(
    dt.getUTCHours(),
  )}${pad(dt.getUTCMinutes())}${pad(dt.getUTCSeconds())}`;
}

/** Convert "2026-06-13" + "15:00" + leadMinutes -> local stamp for departure. */
export function buildDepartureStamp(
  matchDate: string,
  kickoff: string,
  doorMinutes: number,
): { stamp: string; readable: string } {
  const [y, m, d] = matchDate.split("-").map(Number);
  const [hh, mm] = kickoff.split(":").map(Number);
  // Suggested departure = kickoff - doorMinutes - 30 min buffer for entry
  const total = hh * 60 + mm - doorMinutes - 30;
  const safeTotal = total < 0 ? 0 : total;
  const depH = Math.floor(safeTotal / 60);
  const depM = safeTotal % 60;
  const stamp = `${y}${pad(m)}${pad(d)}T${pad(depH)}${pad(depM)}00`;
  const readable = `${y}-${pad(m)}-${pad(d)} ${pad(depH)}:${pad(depM)}`;
  return { stamp, readable };
}
