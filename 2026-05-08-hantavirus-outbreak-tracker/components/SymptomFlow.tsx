'use client';

import { useMemo, useState } from 'react';
import symptoms from '../data/symptoms.json';
import { Answers, triage, TIER_COLOR } from '../lib/triage';

type Q = {
  id: string;
  prompt: string;
  help: string;
  options: { value: string; label: string; weight: number }[];
};

const QS = symptoms.questions as Q[];

export default function SymptomFlow() {
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Answers>({});
  const done = step >= QS.length;
  const advice = useMemo(() => (done ? triage(answers) : null), [done, answers]);

  function pick(qid: string, value: string) {
    const next: Answers = { ...answers, [qid]: value as never };
    setAnswers(next);
    setStep(step + 1);
  }

  function reset() {
    setStep(0);
    setAnswers({});
  }

  if (done && advice) {
    return (
      <div>
        <div
          role="status"
          aria-live="polite"
          className={`rounded-lg p-6 ${TIER_COLOR[advice.tier]}`}
        >
          <p className="text-xs uppercase tracking-widest opacity-80">{advice.tier}</p>
          <h2 className="font-serif text-2xl md:text-3xl font-bold mt-1">{advice.headline}</h2>
          <p className="mt-3 text-base md:text-lg">{advice.action}</p>
        </div>

        <div className="mt-6 space-y-4 text-ink">
          <h3 className="font-serif text-xl font-bold">What to know</h3>
          <ul className="list-disc list-inside space-y-2">
            {advice.details.map((d, i) => (
              <li key={i}>{d}</li>
            ))}
          </ul>

          <h3 className="font-serif text-xl font-bold pt-2">Tell your clinician</h3>
          <blockquote className="border-l-4 border-rust pl-4 italic text-ink/80">
            {advice.clinician_script}
          </blockquote>

          <div className="flex flex-wrap gap-3 pt-4">
            <button
              onClick={reset}
              className="px-4 py-2 border border-ink/30 rounded-md hover:bg-ink hover:text-bone"
            >
              Start over
            </button>
            <a
              href="/guide/"
              className="px-4 py-2 bg-ink text-bone rounded-md hover:bg-rust"
            >
              Read full guide →
            </a>
            <button
              onClick={() => {
                if (typeof navigator !== 'undefined' && navigator.share) {
                  navigator.share({ title: 'Hantavirus tracker', url: location.href }).catch(() => {});
                } else if (typeof navigator !== 'undefined') {
                  navigator.clipboard?.writeText(location.href);
                }
              }}
              className="px-4 py-2 border border-ink/30 rounded-md hover:bg-ink hover:text-bone"
            >
              Share this page
            </button>
          </div>
        </div>
      </div>
    );
  }

  const q = QS[step];
  const pct = Math.round((step / QS.length) * 100);

  return (
    <div>
      <div className="mb-6">
        <div className="flex justify-between text-xs text-ink/60 mb-2">
          <span>Question {step + 1} of {QS.length}</span>
          <span>{pct}%</span>
        </div>
        <div className="h-1 bg-ink/10 rounded">
          <div className="h-full bg-rust rounded transition-all" style={{ width: `${pct}%` }} />
        </div>
      </div>

      <h2 className="font-serif text-2xl md:text-3xl font-bold leading-snug">{q.prompt}</h2>
      <p className="text-sm text-ink/70 mt-2">{q.help}</p>

      <div className="mt-6 space-y-2" role="radiogroup" aria-label={q.prompt}>
        {q.options.map((opt) => (
          <button
            key={opt.value}
            onClick={() => pick(q.id, opt.value)}
            className="w-full text-left px-4 py-3 border border-ink/20 rounded-md hover:border-ink hover:bg-ink hover:text-bone transition-colors"
          >
            {opt.label}
          </button>
        ))}
      </div>

      {step > 0 && (
        <button
          onClick={() => setStep(step - 1)}
          className="mt-6 text-sm text-ink/60 underline"
        >
          ← Back
        </button>
      )}
    </div>
  );
}
