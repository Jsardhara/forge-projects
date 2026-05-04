import { XMLParser } from "fast-xml-parser";
import { classifyKind, FEED_SOURCES, isHormuzRelated, type FeedSource } from "./sources";
import type { Incident } from "./types";

interface RssItem {
  title?: string;
  link?: string;
  description?: string;
  pubDate?: string;
  guid?: string | { "#text"?: string };
}

const parser = new XMLParser({
  ignoreAttributes: false,
  attributeNamePrefix: "@_",
});

function extractItems(xml: string): RssItem[] {
  try {
    const parsed = parser.parse(xml);
    const channel = parsed?.rss?.channel;
    if (!channel) return [];
    const item = channel.item;
    if (!item) return [];
    return Array.isArray(item) ? item : [item];
  } catch {
    return [];
  }
}

function toIncident(source: FeedSource, item: RssItem): Incident | null {
  const title = (item.title ?? "").toString().trim();
  const link = (item.link ?? "").toString().trim();
  if (!title || !link) return null;

  const description = (item.description ?? "").toString().replace(/<[^>]+>/g, "").trim();
  const haystack = `${title} ${description}`;
  if (!isHormuzRelated(haystack)) return null;

  const kind = classifyKind(haystack);
  const rawDate = (item.pubDate ?? "").toString();
  const ts = Date.parse(rawDate);
  const timestamp = Number.isFinite(ts) ? new Date(ts).toISOString() : new Date().toISOString();

  const guidRaw =
    typeof item.guid === "object" ? item.guid?.["#text"] ?? "" : item.guid ?? "";
  const id = (guidRaw || link).toString();

  return {
    id,
    kind,
    title,
    summary: description.slice(0, 280),
    source: source.name,
    sourceUrl: link,
    timestamp,
  };
}

export async function fetchFeed(source: FeedSource): Promise<Incident[]> {
  const res = await fetch(source.url, {
    headers: { "user-agent": "HormuzTransitAdvisor/0.1 (+https://example.local)" },
    cache: "no-store",
  });
  if (!res.ok) return [];
  const xml = await res.text();
  return extractItems(xml)
    .map((item) => toIncident(source, item))
    .filter((x): x is Incident => x !== null);
}

export async function fetchAllFeeds(): Promise<{
  fetched: Incident[];
  perSource: Record<string, number>;
  errors: string[];
}> {
  const errors: string[] = [];
  const perSource: Record<string, number> = {};
  const results = await Promise.all(
    FEED_SOURCES.map(async (s) => {
      try {
        const items = await fetchFeed(s);
        perSource[s.id] = items.length;
        return items;
      } catch (err) {
        errors.push(`${s.id}: ${(err as Error).message}`);
        perSource[s.id] = 0;
        return [];
      }
    }),
  );
  return { fetched: results.flat(), perSource, errors };
}

export function mergeIncidents(
  existing: ReadonlyArray<Incident>,
  incoming: ReadonlyArray<Incident>,
): { merged: Incident[]; added: number } {
  const seen = new Set(existing.map((i) => i.sourceUrl));
  let added = 0;
  const next = [...existing];
  for (const item of incoming) {
    if (seen.has(item.sourceUrl)) continue;
    seen.add(item.sourceUrl);
    next.push(item);
    added += 1;
  }
  next.sort((a, b) => Date.parse(b.timestamp) - Date.parse(a.timestamp));
  return { merged: next, added };
}
