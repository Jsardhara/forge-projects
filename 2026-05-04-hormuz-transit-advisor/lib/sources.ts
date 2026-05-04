export interface FeedSource {
  id: string;
  name: string;
  url: string;
  defaultKind: "advisory" | "attack" | "missile-near-miss" | "escort";
}

export const FEED_SOURCES: ReadonlyArray<FeedSource> = [
  {
    id: "ukmto",
    name: "UKMTO",
    url: "https://www.ukmto.org/feed",
    defaultKind: "advisory",
  },
  {
    id: "reuters-energy",
    name: "Reuters Energy",
    url: "https://www.reutersagency.com/feed/?best-topics=energy&post_type=best",
    defaultKind: "advisory",
  },
  {
    id: "npr-world",
    name: "NPR World",
    url: "https://feeds.npr.org/1004/rss.xml",
    defaultKind: "advisory",
  },
];

const HORMUZ_KEYWORDS = [
  "hormuz",
  "strait",
  "iran",
  "tanker",
  "houthi",
  "gulf of oman",
  "persian gulf",
  "ukmto",
  "imscc",
  "centcom",
  "escort",
  "convoy",
];

export function isHormuzRelated(text: string): boolean {
  const lower = text.toLowerCase();
  return HORMUZ_KEYWORDS.some((k) => lower.includes(k));
}

export function classifyKind(text: string): FeedSource["defaultKind"] {
  const lower = text.toLowerCase();
  if (/(struck|hit|attack|drone strike|seized|boarded|fired on)/.test(lower)) {
    return "attack";
  }
  if (/(missile|near.?miss|projectile|warning shot|ballistic)/.test(lower)) {
    return "missile-near-miss";
  }
  if (/(escort|convoy|imscc|centcom|task force)/.test(lower)) {
    return "escort";
  }
  return "advisory";
}
