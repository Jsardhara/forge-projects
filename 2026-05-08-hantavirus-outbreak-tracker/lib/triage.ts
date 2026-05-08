import { z } from 'zod';

export const AnswerSchema = z.object({
  core_symptoms: z.enum(['yes', 'one', 'no']).optional(),
  respiratory: z.enum(['severe', 'mild', 'no']).optional(),
  exposure: z.enum(['ship', 'contact', 'rodent', 'no']).optional(),
  other: z.enum(['many', 'few', 'none']).optional(),
});

export type Answers = z.infer<typeof AnswerSchema>;

export type Tier = 'emergency' | 'urgent' | 'monitor' | 'reassure';

export type Advice = {
  tier: Tier;
  headline: string;
  action: string;
  details: string[];
  clinician_script: string;
};

const WEIGHTS: Record<string, Record<string, number>> = {
  core_symptoms: { yes: 2, one: 1, no: 0 },
  respiratory: { severe: 3, mild: 1, no: 0 },
  exposure: { ship: 2, contact: 1, rodent: 1, no: 0 },
  other: { many: 2, few: 1, none: 0 },
};

export function scoreAnswers(a: Answers): number {
  let total = 0;
  for (const k of Object.keys(WEIGHTS) as (keyof Answers)[]) {
    const v = a[k];
    if (v) total += WEIGHTS[k][v] ?? 0;
  }
  return total;
}

export function triage(a: Answers): Advice {
  const score = scoreAnswers(a);
  const respSevere = a.respiratory === 'severe';
  const shipExposure = a.exposure === 'ship';

  if (respSevere) {
    return {
      tier: 'emergency',
      headline: 'Seek emergency care now.',
      action: 'Call emergency services (999/112/911) or go to the nearest A&E.',
      details: [
        'Severe shortness of breath with fever can indicate Hantavirus Pulmonary Syndrome (HPS), which deteriorates within hours.',
        'Tell the dispatcher about possible hantavirus exposure so the receiving team can prepare.',
        'Do not drive yourself if you are gasping for air.',
      ],
      clinician_script:
        'I have fever, myalgia, and acute dyspnoea. I have possible hantavirus exposure. Please consider HPS and order CBC, CMP, LDH, lactate, chest X-ray, and contact public health for hantavirus PCR/serology.',
    };
  }

  if (score >= 5 || (shipExposure && score >= 3)) {
    return {
      tier: 'urgent',
      headline: 'See a clinician within 24 hours.',
      action: 'Call your GP, NHS 111, or an urgent care clinic today. Mention the hantavirus outbreak.',
      details: [
        'Your combination of symptoms and exposure is consistent with early hantavirus illness.',
        'Early bloodwork (CBC showing thrombocytopenia, hemoconcentration, left shift) supports diagnosis before lung involvement.',
        'Avoid close contact with vulnerable people until evaluated.',
        'Stay hydrated; do not take NSAIDs until evaluated (kidney involvement possible in HFRS strains).',
      ],
      clinician_script:
        'I may have been exposed to hantavirus on the MV Atlantic Voyager voyage (28 Apr–12 May 2026) or via a contact. I have fever, myalgia, and other prodromal symptoms. Please consider hantavirus serology/PCR and notify public health.',
    };
  }

  if (score >= 2) {
    return {
      tier: 'monitor',
      headline: 'Monitor closely. Get tested if symptoms worsen.',
      action: 'Self-isolate where reasonable. Re-check this tool daily for the next 6 weeks.',
      details: [
        'You have some symptoms or exposure but not the full picture. Most flu-like illnesses are not hantavirus.',
        'Red flags that should escalate you to urgent care: shortness of breath, chest tightness, dropping urine output, dizziness on standing.',
        'Keep a symptom diary with dates and temperatures.',
        'If you were on the MV Atlantic Voyager, register with UKHSA or your national authority.',
      ],
      clinician_script:
        'I have some symptoms compatible with hantavirus prodrome and a possible exposure. I am tracking symptoms daily and will return immediately if I develop respiratory or kidney symptoms.',
    };
  }

  return {
    tier: 'reassure',
    headline: 'Low likelihood based on what you reported.',
    action: 'No urgent action. Use standard rodent-avoidance hygiene and watch for symptoms.',
    details: [
      'You reported few or no symptoms and no clear exposure.',
      'If symptoms develop in the next 6 weeks, return to this tool or contact a clinician.',
      'Hantavirus is not transmitted by casual contact in most strains; airborne transmission requires close-quarters exposure to rodent excreta or, rarely, infected respiratory droplets.',
    ],
    clinician_script:
      'I am asymptomatic but wanted to ask about hantavirus screening because of recent travel/news. Please advise if any precautions apply to me.',
  };
}

export const TIER_COLOR: Record<Tier, string> = {
  emergency: 'bg-rust text-bone',
  urgent: 'bg-amber text-ink',
  monitor: 'bg-moss text-bone',
  reassure: 'bg-ink/10 text-ink',
};
