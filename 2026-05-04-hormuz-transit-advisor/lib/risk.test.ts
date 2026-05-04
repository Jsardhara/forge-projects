import { describe, it, expect } from "vitest";
import { assessRisk } from "./risk";
import type { Incident } from "./types";

const NOW = new Date("2026-05-04T12:00:00Z");

function inc(kind: Incident["kind"], hoursAgo: number, id = String(Math.random())): Incident {
  return {
    id,
    kind,
    title: kind,
    summary: "",
    source: "test",
    sourceUrl: "https://example.com",
    timestamp: new Date(NOW.getTime() - hoursAgo * 3600_000).toISOString(),
  };
}

describe("assessRisk", () => {
  it("returns GREEN for empty input", () => {
    const r = assessRisk([], NOW);
    expect(r.level).toBe("GREEN");
    expect(r.score).toBe(0);
  });

  it("returns GREEN with one advisory (score 1)", () => {
    const r = assessRisk([inc("advisory", 2)], NOW);
    expect(r.level).toBe("GREEN");
    expect(r.score).toBe(1);
  });

  it("returns AMBER at score 2 (one near-miss)", () => {
    const r = assessRisk([inc("missile-near-miss", 3)], NOW);
    expect(r.level).toBe("AMBER");
    expect(r.score).toBe(2);
  });

  it("returns AMBER at score 4 (one attack + one advisory)", () => {
    const r = assessRisk([inc("attack", 1), inc("advisory", 5)], NOW);
    expect(r.level).toBe("AMBER");
    expect(r.score).toBe(4);
  });

  it("returns RED at score 5 (one attack + one near-miss)", () => {
    const r = assessRisk([inc("attack", 1), inc("missile-near-miss", 2)], NOW);
    expect(r.level).toBe("RED");
  });

  it("returns RED at score 8", () => {
    const r = assessRisk(
      [inc("attack", 1), inc("attack", 2), inc("missile-near-miss", 3)],
      NOW,
    );
    expect(r.score).toBe(8);
    expect(r.level).toBe("RED");
  });

  it("returns BLACK at score 9", () => {
    const r = assessRisk(
      [inc("attack", 1), inc("attack", 2), inc("attack", 3)],
      NOW,
    );
    expect(r.score).toBe(9);
    expect(r.level).toBe("BLACK");
  });

  it("ignores incidents older than the window", () => {
    const r = assessRisk([inc("attack", 36), inc("advisory", 50)], NOW);
    expect(r.score).toBe(0);
    expect(r.level).toBe("GREEN");
  });

  it("ignores escort entries (weight 0)", () => {
    const r = assessRisk([inc("escort", 1), inc("escort", 2)], NOW);
    expect(r.score).toBe(0);
    expect(r.level).toBe("GREEN");
  });

  it("rationale mentions counts and score", () => {
    const r = assessRisk([inc("attack", 1), inc("advisory", 2)], NOW);
    expect(r.rationale).toContain("1 attack");
    expect(r.rationale).toContain("1 advisory");
    expect(r.rationale).toContain("score 4");
  });
});
