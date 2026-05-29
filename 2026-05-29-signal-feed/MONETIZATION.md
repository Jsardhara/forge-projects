# Monetization Plan — Signal Feed API

## Product Positioning

**The "Bloomberg Terminal Lite" for retail traders and algo-devs.**
Most traders check 5+ tabs (Reddit, Twitter, CoinDesk, TradingView…).
Signal Feed aggregates, scores, and delivers structured signals via one API.

## Tiers

| Feature | Free | Pro ($19/mo) | Enterprise ($99/mo) |
|---|---|---|---|
| Requests/min | 5 | 100 | Unlimited |
| API Key | 1 | 5 | Unlimited |
| REST API | ✅ | ✅ | ✅ |
| WebSocket | ❌ | ✅ | ✅ |
| Historical data | 24h | 30d | Unlimited |
| Custom sources | ❌ | ❌ | ✅ |
| Webhooks | ❌ | 10 | Unlimited |
| Priority support | ❌ | ❌ | ✅ |

## Revenue Streams

### 1. API Subscription ($19/mo Pro, $99/mo Enterprise)
**Target:** Retail algo-traders, Discord/Telegram bot operators, fintech devs.
Even 50 Pro subscribers = $950/mo. 200 = $3,800/mo.

### 2. White-Label Bot Templates ($49–$199 one-time)
Pre-built Discord bot and Telegram bot that consume Signal Feed API.
Sell on Gumroad/CodeCanyon. Low effort (thin wrapper around API).

### 3. Slack Integration App (Slack marketplace)
Package the webhook delivery as a Slack app. Charge $9/user/month.
Great for crypto/stock trading groups.

### 4. Zapier/Make.com Integration (future)
No-code automation. Triggers: "When bearish signal > -0.7 on crypto → send SMS".

## Go-to-Market Strategy

1. **Launch on Product Hunt** with free tier (no credit card)
2. **Post on r/CryptoCurrency, r/algotrading** showing live signal screenshots
3. **Offer free API keys** to Twitter/X influencers in exchange for mentions
4. **Write SEO content**: "free crypto sentiment API", "market sentiment data python"
5. **Add to RapidAPI hub** — passive discovery

## Competitive Advantage

- **Structured sentiment scores** (not just "positive/negative"): numeric -1 to +1
- **Multi-source correlation**: same signal from Reddit + news = higher conviction
- **Dead simple API**: one header, JSON response, no OAuth gymnastics
- **Self-hostable**: enterprises can run internally (sell Docker image)

## Unit Economics

| Item | Cost |
|---|---|
| Hosting (Railway/Render free tier) | $0 |
| Reddit API (public JSON) | $0 |
| RSS feeds | $0 |
| CoinGecko API (free tier) | $0 |
| **Monthly cost** | **$0–$10** |
| **Break-even** | **1 Pro subscriber** |

## Milestones

- [ ] MVP built (today) — REST API + Reddit + RSS + keyword scoring
- [ ] Deploy on Railway, get public URL
- [ ] Launch Product Hunt (week 1)
- [ ] Build Discord bot template, list on Gumroad (week 2)
- [ ] Add CoinGecko price correlation (week 3)
- [ ] Add webhook delivery (week 4)

## Risks & Mitigation

| Risk | Mitigation |
|---|---|
| Reddit API rate limits | Rotate User-Agent, cache aggressively |
| Low signal accuracy (keyword scoring) | Upgrade to FinBERT in Pro tier, ML pipeline |
| Competition (free alternatives) | Bundle + correlation + UX > raw data alone |
| No domain expertise signal | Partner with actual traders for validation |
