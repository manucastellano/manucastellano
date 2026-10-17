# Market research: regime and finalists, 2026-10-17

**Read this first.** The build container's network policy blocked every market-data host
(exchanges, CoinGecko, DefiLlama, Tokenomist, TypeSafe, AgenKit). Everything below comes from
web-search summaries of **secondary sources** (news sites and aggregators), not primary data.
Several sources disagree with each other, and the disagreements are noted. **No number here is
verified.** That's why every finalist ships `verified: false` in `schemas/jev_schema_v1.json`,
and the policy refuses to trade an unverified finalist.

Labels: **[R]** reported by a named secondary source · **[C]** sources conflict · **[E]** my estimate or inference · **[S]** speculation · **[?]** not found, must be pulled from a primary source.

## 1. Regime (as of 2026-10-16/17)

| Input | Reading | Label / source |
|---|---|---|
| BTC price | ~$81.6k–82.6k on Oct 16; briefly above $84k on Oct 14; fell 3.5% to ~$80.8k after a hot CPI print | [R][C] [Fortune](https://fortune.com/article/price-of-bitcoin-10-16-2026), [ad-hoc-news](https://www.ad-hoc-news.de/boerse/news/marktberichte/etf-inflow-of-5-06-million-usd-on-october-15-2026-bitcoin-price-implications/70345024), [Wealthier Today](https://www.wealthiertoday.com/news/bitcoin-etf-outflows-october-14-2026/) |
| Spot BTC ETF flows | ~$2.65B in for September; −$484.9M on Oct 7; −$261M on Oct 14; +$5M on Oct 15 | [R] [CoinCentral](https://coincentral.com/bitcoin-etf-statistics-2026-complete-data-on-inflows-aum-and-performance), ad-hoc-news |
| BTC dominance | ~59.4–59.9% | [R][C] [tv-hub](https://www.tv-hub.org/guide/bitcoin-dominance), [CoinDesk Oct 2](https://www.coindesk.com/markets/2026/10/02/crypto-traders-are-in-risk-on-mode-as-bitcoin-dominance-nears-return-to-60) |
| Total crypto market cap | ~$2.7–2.8T | [R][C] |
| Funding | Annualized perp funding fell from ~6.7% (Oct 5) toward neutral; one aggregator shows slightly negative | [R] Bitfinex via Wealthier Today; [CoinStats](https://coinstats.app/ai/a/latest-news-for-bitcoin) |
| Open interest | ~flat near $53B; OI fell during the bounce (read as spot-led) | [R] CoinStats, Bitfinex via Wealthier Today |
| Options | Continued demand for downside protection | [R] Bitfinex via Wealthier Today |
| Stablecoins | Often cited above $300B total; USDT share of total market cap ~6.3% in early Oct | [R][?] [CoinDesk](https://www.coindesk.com/markets/2026/10/02/crypto-traders-are-in-risk-on-mode-as-bitcoin-dominance-nears-return-to-60); the 30-day net issuance trend is **[?]** |
| ETH | ~$2,670–2,720 in early October; Ether ETF outflows ~−$118M over Oct 1–3 after +$832M in September | [R][C] [Yahoo](https://finance.yahoo.com/news/ethereum-etfs-hit-six-week-135007523.html), [Farside](https://www.farside.co.uk/eth/); mid-October price **[?]**; ETH/BTC **[?]** |
| Macro | Hot CPI revived rate-hike bets; FOMC Oct 27–28; higher Treasury yields; oil reportedly above $100 | [R] [Yahoo Finance](https://finance.yahoo.com/markets/crypto/articles/bitcoin-price-prediction-october-2026-141555670.html) (oil figure single-sourced); hike odds [C] |
| Sentiment | "Fear" | [R] CoinGecko via search |
| Narrative rotation | Protocol buybacks reportedly at a record ~$638M in 2026, concentrated in Hyperliquid and Pump.fun; one analysis found only 2 of 11 programs cut net supply | [R] [crypto.news](https://crypto.news/crypto-token-buybacks-hit-record-638m-in-2026/), [SpendNode](https://www.spendnode.io/blog/crypto-token-buybacks-record-638-million-hyperliquid-pumpfun-september-2026/) |

**Regime call [E]:** risk-off chop, with `mean_reverting` most likely and `high_vol` around
FOMC (Oct 27–28). It is not `trending`. Dominance near 60%, ETF outflows and fear sentiment are
a headwind for alt longs. Implication for the system: small sizes, a high bar for alt longs, and
standing aside through the FOMC window unless the reflex sees a clean setup.

## 2. Finalists

I'm presenting five, not the 5–10 requested, because I could not fill the required metrics
(TVL, active users, holder concentration) for more without inventing them. **The candidates are
mostly consensus "revenue + buyback" names, not hidden mispricings.** That's the honest output
of the data I could reach; see section 3.

### 2.1 BTC-PERP (regime anchor, not a valuation thesis)
- **Why it's here:** the deepest liquidity and lowest costs, and the only instrument where a
  per-candle reflex plausibly beats costs. FOMC Oct 27–28 is a **confirmed** scheduled event.
- **Bear case:** hawkish repricing; persistent ETF outflows; oil and yields up together.
- **Invalidation:** stand aside when realized vol is above 2x its 24h norm around FOMC.
- **Value accrual:** n/a (monetary asset).

### 2.2 HYPE-PERP (Hyperliquid)
- **Thesis [R]:** trading fees fund automated HYPE buybacks (one source says 99% of eligible
  fees); USDC reserve yield now also funds them (first payment ~14.58M USDC); the Assistance Fund
  bought ~144k HYPE in the 7 days to Oct 14. Reported cumulative buybacks are ~$1.26B (methodology
  differs by source; a trailing-year figure of ~$943M also circulates **[C]**). Price ~$80–82 on
  Oct 14–16. [24/7 Wall St](https://247wallst.com/investing/cryptocurrency/2026/10/14/hyperliquid-has-bought-back-1-26-billion-of-its-own-token-ethereum-burns-its-fees-instead-which-one-holds-its-price-better/), [CryptoTicker](https://cryptoticker.io/en/hyperliquid-buyback-usdc-earnings/), [Tokenomist](https://tokenomist.ai/hyperliquid)
- **Supply/unlocks [C]:** Oct 6 core-contributor unlock scheduled ~9.92M HYPE, but reportedly
  only 3.75M released and placed OTC with one buyer ([FinanceFeeds](https://financefeeds.com/hyperliquid-hype-unlock-october-otc-buyer/)). Next unlock reportedly Nov 6. One calendar shows a $1.3B event on Oct 29, which conflicts with the others.
- **Confirmed vs speculative:** buyback mechanism = confirmed by multiple sources; "OTC buyer absorbs unlocks" = **[S]** for future months.
- **Bear case:** buybacks are pro-cyclical (lower volume means smaller buybacks, exactly when price is weak); monthly team unlocks; perp-DEX competition; regulatory exposure; a planned funding-cap cut (4%/h → 0.5%/h) may change trader behavior; a very well-known thesis, so likely priced in.
- **Invalidation:** weekly fees down >40% vs the 4-week average, or buyback volume below unlocked supply hitting the market.
- **[?]** Fees and revenue from a primary dashboard, OI market share, holder concentration, active traders.

### 2.3 ENA-PERP (Ethena)
- **Thesis [R]:** the remaining ~1.4B ENA investor allocation unlocked in one event on Oct 5, 2026, ending the monthly overhang 17 months early. A fee switch (95% of net revenue to open-market ENA buybacks, no burn) passed governance. ENA incentives tied to USDe expansion ended at the end of September. [The Block](https://www.theblock.co/news/ecosystems/2026-08-27-ethena-foundation-proposes-fee-switch-ena-token-buybacks-other-updates-412951), [CryptoTicker](https://cryptoticker.io/en/ethena-fee-switch-ena-buyback/)
- **The catch:** buybacks only start when USDe supply reaches **$7.5B**. Reported supply is ~$4.3–5.0B **[C]**. USDe yield comes from funding rates, which are now near neutral or negative, so supply tends to shrink in exactly this regime.
- **Confirmed:** overhang removal (a dated event), fee-switch vote. **Speculative:** reaching the $7.5B trigger.
- **Bear case:** no buybacks for the foreseeable future; another unlock reportedly Nov 1 (~2.7% of market cap per Tokenomics.com); price reportedly $0.16–0.22 **[C]**; the vote date is reported inconsistently.
- **Invalidation:** USDe supply falls 3 weeks in a row, or funding stays negative for 2 weeks.

### 2.4 PUMP-PERP (Pump.fun)
- **Thesis [R]:** an April 29, 2026 burn of ~$370M (~36% of circulating supply) plus 50% of net revenue committed to buy-and-burn via contract through April 2027. Weekly revenue reportedly ~$18.6M in early October (an AI-generated aggregator page, **low reliability**). Price reportedly at or near all-time lows **[C]**. [CoinMarketCap Academy](https://coinmarketcap.com/academy/article/pumpfun-burns-dollar370m-in-pump-commits-50percent-of-revenue-to-buybacks), [FXStreet](https://www.fxstreet.com/cryptocurrencies/news/pumpfun-burns-36-of-circulating-pump-supply-unveils-50-revenue-buyback-program-202604290053)
- **Value accrual:** the strongest of the set on paper (burn, not just treasury buyback).
- **Bear case:** revenue depends on memecoin speculation, which is cyclical and fades in risk-off; launchpad competition; legal and reputational risk (**[?]**, not verified here); a falling price despite burns suggests revenue is decaying or supply pressure exists elsewhere.
- **Invalidation:** weekly revenue down >50% vs the 4-week average, or the buyback contract stops executing on-chain.

### 2.5 SOL-PERP (catalyst watch)
- **Catalysts [R]:** staking ETF filings (Morgan Stanley's final paperwork reported Jul 22, 2026; Grayscale's updated filing) and the Alpenglow consensus upgrade (finality reportedly ~12.8s → ~150ms). [Analytics Insight](https://www.analyticsinsight.net/news/solana-price-eyes-80-as-alpenglow-upgrade-and-etf-filing-draw-attention)
- **Not confirmed:** approval dates and Alpenglow mainnet timing (sources say Q3 or H2 2026 **[C]**). No October 2026 coverage found. Current price **[?]**.
- **Bear case:** catalysts may already be priced in; reported ETF inflows are small (+$5.83M best day in two weeks); alt beta under ~60% BTC dominance.
- **Invalidation:** catalyst dates slip past year-end, or SOL/BTC makes a new 90-day low.

### Considered and dropped
- **AAVE:** the most recent buyback data found was from 2025 ("Aavenomics", $1M/week); nothing on v4 or a 2026 fee switch was found. Too stale to underwrite.
- **Unlock shorts (ALLO, HUMA, RAIN, L1X in November):** single-source unlock data ([Bitbase](https://www.bitbase.com/news/325003), [Tokenomics.com](https://app.tokenomics.com/unlocks)); a crowded strategy where borrow and funding costs are often prohibitive. Revisit with Tokenomist data.

## 3. Asymmetry check: is anything here actually mispriced? [E]

- **Organic vs incentive-driven:** HYPE and PUMP revenue is organic trading and launch fees, but
  both are *activity-cyclical*. ENA's revenue is funding-rate carry, which is regime-dependent by
  construction.
- **Priced in?** All buyback stories are heavily covered in the press (a record-buybacks
  narrative). The one dated, non-consensus item is ENA's overhang removal, but it is offset by the
  fee switch being nowhere near its trigger.
- **Value accrual:** PUMP (burn) > HYPE (buyback into the Assistance Fund) > ENA (buyback, no burn,
  gated) > SOL/BTC (none in this sense).
- **Net:** I would not claim any of these is a strong asymmetric setup today. The system is
  designed so that this doesn't matter much: the reflex trades short-horizon structure on liquid
  perps, and the theses only inform Jev's context and the operator's universe choice.

## 4. Verification checklist (operator, before flipping `verified: true`)
For each finalist, pull from primary sources and record the date:
- Price, 30-day volume, perp OI and funding (venue API).
- Fees and revenue (protocol dashboard, DefiLlama "fees" and "revenue").
- Unlock calendar for the next 90 days (Tokenomist), with the % of circulating supply.
- Top-100 holder concentration excluding exchanges and contracts (block explorer).
- Buyback execution on-chain (contract or Assistance Fund address).
- Round-trip cost on your venue: measure fee tier + spread + slippage at your intended size.
