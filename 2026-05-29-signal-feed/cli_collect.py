#!/usr/bin/env python3
"""One-shot CLI to run a collection and print results."""

import asyncio
import json
import sys

# Ensure the project root is on sys.path
sys.path.insert(0, __file__.rsplit("/", 1)[0])

from signal_feed.collectors import collect_all


async def main():
    print("📡 Signal Feed — Collecting signals...")
    print("=" * 60)

    signals = await collect_all()

    if not signals:
        print("No signals collected. Check network connection.")
        return

    bullish = [s for s in signals if s["sentiment_label"] == "bullish"]
    bearish = [s for s in signals if s["sentiment_label"] == "bearish"]
    neutral = [s for s in signals if s["sentiment_label"] == "neutral"]

    print(f"\n📊 Total signals: {len(signals)}")
    print(f"  🟢 Bullish: {len(bullish)}")
    print(f"  🔴 Bearish: {len(bearish)}")
    print(f"  ⚪ Neutral: {len(neutral)}")

    print("\n🔝 Top 5 Bullish Signals:")
    for s in sorted(bullish, key=lambda x: x["signal_score"], reverse=True)[:5]:
        print(f"  [{s['score']:.2f}] {s['title'][:80]}")
        print(f"       Source: {s['source']} | {s.get('url', '')[:60]}")

    print("\n🔻 Top 5 Bearish Signals:")
    for s in sorted(bearish, key=lambda x: x["signal_score"])[:5]:
        print(f"  [{s['signal_score']:.2f}] {s['title'][:80]}")
        print(f"       Source: {s['source']} | {s.get('url', '')[:60]}")

    # Save raw to file
    output_path = "last_collection.json"
    # Remove non-serializable datetime
    for s in signals:
        if "created_at" in s:
            s["created_at"] = str(s["created_at"])
    with open(output_path, "w") as f:
        json.dump(signals, f, indent=2)
    print(f"\n💾 Saved {len(signals)} signals to {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
