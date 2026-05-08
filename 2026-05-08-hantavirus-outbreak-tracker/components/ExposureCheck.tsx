'use client';

import { useState } from 'react';
import ships from '../data/ships.json';

type Ship = (typeof ships)[number];

function parseDate(s: string): number | null {
  if (!s) return null;
  const t = Date.parse(s);
  return Number.isFinite(t) ? t : null;
}

function overlaps(userStart: number, userEnd: number, s: Ship): boolean {
  const sStart = parseDate(s.dates.start);
  const sEnd = parseDate(s.dates.end);
  if (sStart == null || sEnd == null) return false;
  return userStart <= sEnd && userEnd >= sStart;
}

export default function ExposureCheck() {
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [shipName, setShipName] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const userStart = parseDate(start);
  const userEnd = parseDate(end || start);
  const valid = userStart != null && userEnd != null && userStart <= userEnd;

  const matches = valid
    ? ships.filter((s) => {
        const nameOk = !shipName || s.name.toLowerCase().includes(shipName.toLowerCase());
        return nameOk && overlaps(userStart!, userEnd!, s);
      })
    : [];

  return (
    <div>
      <div className="grid sm:grid-cols-2 gap-4">
        <label className="block">
          <span className="text-sm font-medium">Travel start</span>
          <input
            type="date"
            value={start}
            onChange={(e) => setStart(e.target.value)}
            className="mt-1 w-full px-3 py-2 border border-ink/20 rounded-md bg-white"
          />
        </label>
        <label className="block">
          <span className="text-sm font-medium">Travel end</span>
          <input
            type="date"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
            className="mt-1 w-full px-3 py-2 border border-ink/20 rounded-md bg-white"
          />
        </label>
      </div>
      <label className="block mt-4">
        <span className="text-sm font-medium">Ship name (optional)</span>
        <input
          type="text"
          value={shipName}
          onChange={(e) => setShipName(e.target.value)}
          placeholder="e.g. Atlantic Voyager"
          className="mt-1 w-full px-3 py-2 border border-ink/20 rounded-md bg-white"
        />
      </label>

      <button
        onClick={() => setSubmitted(true)}
        disabled={!valid}
        className="mt-4 px-5 py-2 bg-ink text-bone rounded-md hover:bg-rust disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Check
      </button>

      {submitted && valid && (
        <div className="mt-6" aria-live="polite">
          {matches.length === 0 ? (
            <div className="border border-moss/40 bg-moss/10 rounded p-4">
              <strong>No flagged voyage matches your dates.</strong> If you traveled by air or
              other ship in the affected region, still monitor for symptoms for 6 weeks.
            </div>
          ) : (
            <div className="space-y-3">
              {matches.map((s) => (
                <div key={s.name} className="border border-rust/40 bg-rust/5 rounded p-4">
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <h3 className="font-serif text-lg font-bold">{s.name}</h3>
                    <span className="text-xs uppercase font-semibold tracking-wider bg-rust text-bone px-2 py-1 rounded">
                      Possible exposure
                    </span>
                  </div>
                  <p className="text-sm text-ink/70 mt-1">
                    {s.operator} · {s.route}
                  </p>
                  <p className="text-sm mt-1">
                    Voyage: {s.dates.start} → {s.dates.end}
                  </p>
                  <ul className="mt-2 text-sm list-disc list-inside text-ink/80">
                    {s.ports.map((p) => (
                      <li key={p.name}>
                        {p.name} ({p.date})
                      </li>
                    ))}
                  </ul>
                  <p className="mt-3 text-sm">{s.advisory}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
