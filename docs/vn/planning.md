# Vietnam Market Support — Plan

**Status:** Implemented 2026-09-09 — see §9 for what shipped and where this plan was wrong
**Date:** 2026-09-09
**Scope decision:** Additive. Vietnam (HOSE / HNX / UPCoM) is added as a third market
alongside the existing US and China coverage. No China or US behavior is removed,
renamed, or demoted.

---

## 1. Objective

Make Vietnamese equities first-class inputs to the existing Augur analysis pipeline:
a VN ticker MUST flow through `fetch_market_context` → persona scoring → consensus →
dashboard without special-casing at any call site, and MUST carry `currency="VND"`
so VND figures are never silently aggregated with USD or CNY.

---

## 2. Current architecture — verified findings

All line references verified against the working tree on 2026-09-09.

| Component | Location | Behavior |
|---|---|---|
| Provider interface | `src/augur/datasources/base.py:62` | `DataProvider` ABC — `name: str` class attr, `fetch(ticker) -> Dict[str, Any]`, raises `DataProviderError` to trigger fallback |
| Numeric hygiene | `src/augur/datasources/base.py:28` | `safe_num()` normalizes `None`/`NaN`/`inf`/non-numeric → default. Every provider MUST route raw values through it |
| Provider chain builder | `src/augur/datasources/__init__.py` — `default_providers()` | Flat, **market-agnostic** ordered list: yfinance → finnhub (if configured) → alphavantage (if configured) → stooq |
| Chain execution | `src/augur/data.py:237` `_build_context_from_providers` | First provider returning a non-empty dict wins and supplies the **entire** context. Unknown keys filtered against `MarketContext` fields. On total failure sets `data_source="none"` + `data_error` |
| Chain caching | `src/augur/data.py:214-229` | Module-level `_providers_cache` + lock; `_get_providers()` takes **no ticker argument**. Reset via `reset_providers_cache()` (`data.py:131`) |
| Ticker validation | `src/augur/data.py:166` `_normalize_ticker` | Uppercases; 1–15 chars; `^[A-Z0-9.\-]+$`; rejects `..`, leading/trailing `.`/`-` |
| Context model | `src/augur/personas/base.py:69` `MarketContext` | Dataclass. **Already has a `currency` field** |
| Non-chain overlay precedent | `src/augur/data.py:294` `_overlay_edgar_fundamentals` | Field-by-field merge onto an already-built context, deliberately *outside* the first-wins chain |
| Market overview | `src/augur/data.py:569` | Hardcoded instrument list (`^HSI`, `000300.SS`, `^FTSE`, `^N225`, `GC=F`, …). No VN index |
| Hot tickers | `src/augur/data.py:729` | Hardcoded `HOT_SYMBOLS` — US megacaps + crypto, with Chinese display names |
| i18n | `src/dashboard/i18n/{en,zh}.json`, `src/dashboard/static/js/i18n.js` | Two locales only |

### Three findings that shape the plan

1. **`_normalize_ticker` already accepts Yahoo-style VN symbols.** `VNM.VN` is 6 chars,
   alphanumeric + one interior dot, no leading/trailing punctuation. **No change required**
   to ticker validation.
2. **yfinance already covers HOSE prices via the `.VN` suffix.** The existing chain can
   serve VN price/history *today*. What it lacks is Vietnamese fundamentals coverage.
   This makes yfinance the natural VN *fallback*, not the thing to replace.
3. **The chain is first-wins and ticker-blind.** This is the one real architectural
   blocker: a VN-specific provider cannot simply be appended, because yfinance sits
   first and will win with thin data. `_get_providers()` must become market-aware.

---

## 3. Vietnam market reference

| Attribute | Value |
|---|---|
| Exchanges | HOSE (Ho Chi Minh), HNX (Hanoi), UPCoM (unlisted, operated by HNX) |
| Ticker format | 3 uppercase letters (`VNM`, `FPT`, `HPG`, `VCB`, `VIC`, `MSN`). UPCoM also 3 letters |
| Indices | VN-Index, VN30 (HOSE); HNX-Index, HNX30; UPCoM-Index |
| Currency | VND. Prices quoted in whole dong; market caps commonly reported in billions of VND |
| Timezone | ICT, UTC+7 (no DST) |
| Session | 09:00–11:30, 13:00–14:45, with ATO open auction and ATC close auction |
| Daily price band | HOSE ±7%, HNX ±10%, UPCoM ±15% |
| Lot size | 100 shares (HOSE and HNX) |
| Settlement | T+2 |
| Foreign ownership limit | Default 49%; banks 30%; some sectors 100%. Per-ticker "room" is a real signal |
| Fundamentals disclosure | Quarterly + annual, filed to HOSE/HNX portals. **No SEC EDGAR equivalent** |
| Sector taxonomy | ICB (HOSE). GICS is not the local standard |
| Index classification | FTSE Russell frontier→secondary-emerging upgrade `[verify current status before citing in user-facing copy]` |

### Consequences for the analysis pipeline

- **No EDGAR path.** `_overlay_edgar_fundamentals` is US-only and MUST be skipped for VN
  tickers. Fundamentals have to come from the VN provider itself.
- **Price bands compress volatility.** A ±7% hard limit truncates the tails that
  `volatility_60d` and drawdown-based persona scores assume. Flag as a scoring caveat,
  do not silently rescale.
- **Magnitude mismatch.** A VND market cap is ~25,000× the USD figure for the same
  company. Any cross-market ranking, screening threshold, or chart axis that does not
  read `currency` will produce nonsense. This is the highest-severity risk in the port.

---

## 4. Data source evaluation

| Source | Auth | Cost | Price/History | Fundamentals | Maturity | Verdict |
|---|---|---|---|---|---|---|
| **vnstock** (Python lib, wraps VCI/TCBS) | None | Free | Good | **Best available free** — income statement, balance sheet, ratios | Active OSS, but unofficial and scrape-adjacent; breaks when upstream changes | **Primary** |
| **yfinance `.VN`** | None | Free | Good (HOSE) | Thin | Already a dependency, already in the chain | **Fallback** |
| TCBS public JSON (`apipubaws.tcbs.com.vn`) | None | Free | Good | Good | Undocumented public endpoints; no stability contract | Direct-call option if vnstock proves unstable |
| SSI FastConnect | Consumer ID + secret | Paid/broker acct | Real-time, production | Moderate | Official broker API | **Documented as the production upgrade path — not implemented now** |
| VNDIRECT dchart | None | Free | Good | Weak | Undocumented internal API | Rejected |
| Fireant | API key | Freemium | Good | Good | Reasonable | Rejected — key requirement without offsetting benefit over vnstock |

**Recommendation:** `vnstock` primary, existing yfinance `.VN` as fallback. This gives a
zero-credential, zero-config VN path that degrades gracefully to a source already in the
chain. SSI FastConnect is specified as a future provider behind the same `DataProvider`
interface, requiring no further architectural change.

**Dependency gate:** `vnstock` is a new runtime dependency. Per the stop conditions, this
requires explicit approval before `pyproject.toml` is touched. It MUST be an optional
extra (`augur-agents[vn]`) with a lazy import, matching the `yfinance` treatment at
`data.py:200`.

---

## 5. Gap analysis

20 files currently carry China/US market assumptions. Triaged by whether VN support
requires touching them.

### Must change (in scope)

| File | Assumption | Required change |
|---|---|---|
| `src/augur/datasources/__init__.py` | Flat market-agnostic chain | `default_providers()` gains an optional market argument; VN chain returns `[VNStockProvider, YFinanceProvider]` |
| `src/augur/data.py:218` `_get_providers` | No ticker argument, single cached chain | Accept optional market key; cache per-market |
| `src/augur/data.py:237` `_build_context_from_providers` | Market-blind | Resolve market from ticker, request the matching chain |
| `src/augur/data.py:294` EDGAR overlay | Applied unconditionally | Skip for non-US markets |
| `src/augur/data.py:569` market overview | No VN instrument | Add VN-Index entry |
| `src/dashboard/i18n/` | `en`, `zh` only | Add `vi.json` with the full `en.json` key set |
| `src/dashboard/static/js/i18n.js` | Two locales registered | Register Vietnamese |

### New files

| File | Purpose |
|---|---|
| `src/augur/markets.py` | Market registry: exchange metadata, ticker→market resolution, currency, timezone, price band, lot size. Single source of truth — no `if ticker in [...]` anywhere else |
| `src/augur/datasources/vnstock_provider.py` | `VNStockProvider(DataProvider)`, `name = "vnstock"`, lazy import, `is_configured()` |
| `tests/test_markets.py` | Market resolution unit tests |
| `tests/test_vnstock_provider.py` | Provider tests, HTTP fully mocked |

### Out of scope — documented, not touched

`soul.py`, `consensus/industry_matrix.py`, `cli_commands/{workflow,meta}.py`,
`personas/{zhang_lei,dan_bin}.py`, `dashboard/routes/{personas,analysis}.py`,
`dashboard/templates/{personas,committee,scanner}.html`,
`dashboard/static/js/factor-map.js`, `src/skills/augur-*`, `scripts/generate_skills.py`.

These carry China-specific *content* (persona biography, A-share industry taxonomy,
Chinese display strings) rather than market-*mechanism* assumptions. They continue to
work unchanged; VN localization of persona content is deferred to a follow-up. The one
item worth noting: `consensus/industry_matrix.py` uses a China/US industry taxonomy that
does not map cleanly to ICB, so VN tickers will fall into its default bucket. Acceptable
for phase 1, flagged for follow-up.

---

## 6. Implementation plan

### Phase 1 — Market registry (no behavior change)
- Create `src/augur/markets.py`: `Market` dataclass (`code`, `name`, `currency`,
  `timezone`, `price_band_pct`, `lot_size`, `settlement`, `yf_suffix`), a `MARKETS`
  table for `US` / `CN` / `VN`, and `resolve_market(ticker) -> Market`.
- Resolution rules, in order: explicit suffix (`.VN`, `.SS`, `.SZ`, `.HK`) → known VN
  symbol set → default `US`. Bare 3-letter symbols are ambiguous with US tickers, so a
  bare symbol resolves to VN **only** when it is in the curated VN symbol set; otherwise
  callers use the explicit `.VN` form.
- Nothing else imports it yet. Full suite MUST stay green.

### Phase 2 — VN provider
- `VNStockProvider` implementing `DataProvider`. Lazy-imports `vnstock`, strips the
  `.VN` suffix before querying, routes every numeric through `safe_num`, returns
  `currency="VND"` and `data_source="vnstock"`. Raises `DataProviderError` on any
  failure so the chain falls through to yfinance.
- Tests with the network fully mocked.

### Phase 3 — Market-aware chain
- `default_providers(market="US")`; VN returns `[VNStockProvider, YFinanceProvider]`
  when vnstock is installed, `[YFinanceProvider]` otherwise.
- `_get_providers(market)` caches per market; `reset_providers_cache()` clears all.
- `_build_context_from_providers` resolves the market and passes it through.
- `_overlay_edgar_fundamentals` short-circuits for non-US.
- Existing US/CN tests MUST pass untouched — the default argument preserves today's path.

### Phase 4 — Currency and surface integration
- Verify `currency` propagates from provider → `MarketContext` → dashboard.
- Add VN-Index to the market overview instrument list.
- Add `src/dashboard/i18n/vi.json` with parity against `en.json`; register in `i18n.js`.

### Phase 5 — Verification
- Full suite; confirm zero regressions against the pre-change baseline.
- End-to-end run of a VN ticker through the standard analysis entrypoint.

---

## 7. Acceptance criteria

- [ ] `python -m pytest` passes with no fewer passing tests than the pre-change baseline
- [ ] `resolve_market("VNM.VN").currency == "VND"`; `resolve_market("AAPL").code == "US"`
- [ ] VN provider tests pass with zero live network calls
- [ ] A VN ticker returns a populated `MarketContext` with `currency == "VND"`
- [ ] With `vnstock` absent, VN tickers still resolve via yfinance `.VN` — no crash
- [ ] EDGAR overlay does not run for VN tickers
- [ ] `src/dashboard/i18n/vi.json` key set matches `en.json` exactly
- [ ] No file outside the declared scope is modified

---

## 8. Risks and open questions

| Risk | Severity | Mitigation |
|---|---|---|
| Cross-market aggregation mixes VND and USD magnitudes | **High** | `currency` is mandatory on every VN context; audit ranking/screening call sites in phase 4 |
| `vnstock` upstream breakage | Medium | Optional dependency + yfinance fallback; failure degrades, never crashes |
| Bare 3-letter VN symbols collide with US tickers | Medium | Curated symbol set; explicit `.VN` is the documented canonical form |
| ±7% price band distorts volatility-based persona scores | Medium | Documented caveat; no silent rescaling |
| Persona logic tuned on US/CN fundamentals may misjudge VN names | Medium | Out of scope for phase 1; flagged for follow-up |

**Open questions requiring a decision:**
1. Approve `vnstock` as an optional dependency? (blocks phase 2)
2. Canonical ticker form — `VNM.VN` (Yahoo-compatible) or bare `VNM`? Plan assumes `.VN`.
3. Is Vietnamese UI localization wanted now, or English-only VN data first?

---

## 9. Implementation record

Shipped 2026-09-09. Full suite: **2607 passed, 0 failed** (pre-change baseline 2480;
+127 new tests). Three places where this plan turned out to be wrong or too risky are
corrected below — the sections above are left as originally written so the reasoning
that led to the change stays readable.

### 9.1 Correction — the i18n section named the wrong system

§5 said to add `src/dashboard/i18n/vi.json` and "register it in `i18n.js`". That
conflates two independent systems:

| System | Source of strings | Locales | Selected by |
|---|---|---|---|
| Client-side | `window.I18N` inline dicts in `static/js/i18n.js` | zh, en, ja, ko, **vi** | Settings selector (`setAppLang`) → `localStorage` |
| Server-side | `src/dashboard/i18n/{lang}.json` via `GET /api/i18n/{lang}` | en, zh only | `augur_lang` cookie, allowlisted in `routes/optimizer.py:128,146` |

The Settings **Interface Language** selector reads `window.I18N` and never touches the
cookie or the JSON files. `ja` and `ko` — the established partial locales — have no JSON
file and no allowlist entry either.

Vietnamese therefore shipped in `i18n.js` (212 keys, byte-identical key set to `ja`,
falling back current → en → zh) plus a `Tiếng Việt` button in `settings.html`.
Committed separately in `5e3c26a`.

**`vi.json` was deliberately not added.** On its own it is unreachable — no code path
selects it without also widening the `("en","zh")` allowlist and the cookie logic, which
would be new behavior for `ja`/`ko` too and is outside this plan's scope. The acceptance
criterion "`vi.json` key set matches `en.json`" is therefore **dropped, not missed**.
Server-rendered strings remain en/zh for every locale, exactly as they already were for
Japanese and Korean.

### 9.2 Deviation — bare symbols never resolve to Vietnam

§6 Phase 1 had a bare symbol resolve to VN when present in a curated set. That is unsafe:
several liquid VN symbols are live US listings. `VNM` is both Vinamilk on HOSE **and the
Vanguard FTSE Vietnam ETF on NYSE Arca**; `PLX` is also a US listing. Inferring VN from a
bare symbol would silently reroute tickers users analyze today — a regression, and the
opposite of this plan's additive premise.

Implemented rule: **only an explicit suffix resolves to a non-US market.** A bare symbol
always resolves to US, exactly as before `augur/markets.py` existed. `VN_SYMBOLS` still
ships and now backs `suggest_vn_ticker()`, which `search_ticker` calls so that typing
`VNM` also surfaces `VNM.VN` — discoverability without ambiguity. This strictly improves
the "bare 3-letter symbols collide with US tickers" risk in §8 rather than mitigating it.

### 9.3 Addition — Hong Kong split out of the CN entry

§6 folded `.HK` into the CN market. Encoding HK issuers as CNY would have been new bad
data, so `HK` is its own `Market` (HKD, `Asia/Hong_Kong`, T+2, no price band). Nothing
consumes it beyond the EDGAR skip, so this changes no existing behavior.

### 9.4 What shipped

| File | Change |
|---|---|
| `src/augur/markets.py` | **New.** `Market` dataclass, `MARKETS` table (US/CN/HK/VN), `resolve_market`, `strip_market_suffix`, `suggest_vn_ticker`, `VN_SYMBOLS` |
| `src/augur/datasources/vnstock_provider.py` | **New.** `VNStockProvider`, lazy import, `is_configured()`, defensive multi-candidate field extraction |
| `src/augur/datasources/__init__.py` | `default_providers(market="US")`; VN prepends vnstock when installed; `available_sources()` reports it |
| `src/augur/data.py` | `_get_providers(market)` with a separate per-market cache; `_build_context_from_providers` resolves market and backfills `currency`; EDGAR overlay skipped for non-EDGAR markets; VN-Index in `fetch_market_overview`; `search_ticker` suggests `.VN` |
| `pyproject.toml` | New optional extra `vn = ["vnstock>=3.2"]` |
| `tests/test_markets.py` | **New**, 83 tests |
| `tests/test_vnstock_provider.py` | **New**, 27 tests, network fully mocked |
| `tests/test_vn_market_integration.py` | **New**, 17 tests, chain/currency/EDGAR wiring |

### 9.5 Known limits

- **The vnstock field mapping is unverified against a live response.** `vnstock` is not
  installed in this environment and probing the VN endpoints is one of this plan's stop
  conditions, so column names were taken from its documented v3 API, not observed. This
  is deliberately not load-bearing: every access goes through `_pick()` multi-candidate
  matching, and any mismatch raises `DataProviderError` and falls through to yfinance
  `.VN`. **First run against real vnstock should diff the returned dict against
  `MarketContext` and correct the candidate name lists.**
- **`^VNINDEX` is the assumed Yahoo symbol for VN-Index**, also unverified. A wrong symbol
  degrades to that one row being absent from the market overview — per-instrument failure
  is already isolated.
- **`vn` is not part of the `all` extra.** vnstock is unofficial with heavy pins;
  `pip install augur-agents[all]` should not inherit that. Install it explicitly:
  `pip install -e ".[vn]"`.
- **Magnitudes for VN are billions of VND, not USD.** No FX conversion is performed —
  that needs a live rate source. `currency` is the discriminator and is now always
  populated. Cross-market ranking and screening call sites still have to read it; that
  audit is not done.
- **Persona scoring is unchanged.** ICB sector strings fall into
  `consensus/industry_matrix.py`'s default bucket, and the ±7% HOSE band compresses the
  volatility tails that drawdown-based scores assume. Both are documented caveats, not
  silently rescaled. Follow-up work.
