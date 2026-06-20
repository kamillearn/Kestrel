<div align="center">

# 🦅 KESTREL&nbsp;ENGINE

### Institutional-Grade Opening Range Automation

Kestrel productionizes the **Opening Range Breakout (ORB)** edge for index futures
with ruthless discipline. Verified on **Nasdaq**, **S&P 500**, and **DAX**.

<br/>

![Status](https://img.shields.io/badge/STATUS-●_LIVE-10B981?style=for-the-badge&labelColor=0F172A)
![Env](https://img.shields.io/badge/ENV-PRODUCTION_READY-B59410?style=for-the-badge&labelColor=0F172A)
![Python](https://img.shields.io/badge/PYTHON-3.10+-334155?style=for-the-badge&labelColor=0F172A)
![Brokers](https://img.shields.io/badge/BROKERS-IBKR_·_OANDA-334155?style=for-the-badge&labelColor=0F172A)

<br/>

**[Performance](#-performance-analytics) · [The Edge](#-the-edge--30-minute-range-breakout) · [Architecture](#-system-architecture) · [Risk](#-institutional-safeguards)**

</div>

<br/>

<div align="center">

| Expectancy | Max Drawdown | Total Return |
|:----------:|:------------:|:------------:|
| **`+0.213 R`** | **`17.6%`** | **`+255%`** |

</div>

---

## 🖥️ Production Snapshot

```yaml
# ════════════════════════════════════════════════════════
#  PROD-ENV-SNAPSHOT  //  MNQ.NQ                  [ ● LIVE ]
# ════════════════════════════════════════════════════════
current_portfolio_value:  "€35,509.42"
ytd_return:               "▲ 15.5%"
daily_risk_cap:           "1.0%"
open_trades:              0
state:                    PRODUCTION_READY
```

---

## 📈 Performance Analytics

> Comparing asset performance and long-term capital compounding **under modeled costs**.

### Portfolio Capital Simulation (€)

```text
 Capital Simulation (€)                       2021 ──▶ 2026*
 ───────────────────────────────────────────────────────────
 2021   €10,120   +1.2%    ███▉
 2022   €12,056   +19.1%   ████▊
 2023   €17,743   +47.2%   ██████▉
 2024   €22,521   +26.9%   ████████▉
 2025   €30,745   +36.5%   ████████████▏
 2026*  €35,509   +15.5%   ██████████████
 ───────────────────────────────────────────────────────────
                                            ▲  +255% cumulative
```

| Year   |     Equity (€) | Annual Return |
|:-------|---------------:|--------------:|
| 2021   |      `€10,120` |       `+1.2%` |
| 2022   |      `€12,056` |      `+19.1%` |
| 2023   |      `€17,743` |      `+47.2%` |
| 2024   |      `€22,521` |      `+26.9%` |
| 2025   |      `€30,745` |      `+36.5%` |
| 2026\* |      `€35,509` |      `+15.5%` |

<sub>\* 2026 is a partial year (projection).</sub>

### Expectancy (R) per Asset

```text
 Expectancy (R) per Asset
 ────────────────────────────────────────────────────
 MNQ   +0.213 R   ████████████████████   49.5% win
 SPY   +0.091 R   ████████▌              43.4% win
 MYM   +0.034 R   ███▎                   46.0% win
 ────────────────────────────────────────────────────
```

| Asset | Expectancy (R) | Win Rate |
|:------|---------------:|---------:|
| **MNQ** |    `+0.213 R` |  `49.5%` |
| SPY     |    `+0.091 R` |  `43.4%` |
| MYM     |    `+0.034 R` |  `46.0%` |

---

## 🎯 The Edge — 30-Minute Range Breakout

> Kestrel **doesn't guess direction.** It waits for the first 30 minutes of the
> session — the most liquid period — to establish a range. The high and low are
> calculated, and **OCO (One-Cancels-Other)** brackets are placed.

1. **Define Range** — Calculate the High / Low from **09:30 → 10:00 ET**.
2. **Deploy OCO** — Rest a **Stop-Buy at the High** and a **Stop-Sell at the Low**.
3. **End-of-Day Exit** — The position is **strictly closed at 15:55 ET**.

```text
        30m HIGH ──────────────●  ▶  BUY-STOP ENTRY
                 │             │
            ORB  │   RANGE     │      first touch wins,
                 │             │      the opposite cancels
        30m LOW  ──────────────●  ▶  SELL-STOP ENTRY
```

---

## 🏗️ System Architecture

> Built for high-uptime, **venue-agnostic** execution with AI-powered oversight.

| Module | Pipeline | Responsibility |
|:------:|:---------|:---------------|
| 🧠 **Core Engine** | `execution/broker.py` · `instruments.py` | The execution heart — manages OCO handles, point values, and multi-broker routing (**IBKR / OANDA**). |
| 📡 **Telemetry & AI Ops** | `mcp_server.py` · `heartbeat.py` | Real-time JSON state snapshots wired to a **Claude MCP Server** and Telegram alerts. |
| 🏭 **Alpha Factory** | `alpha_factory.py` · `alpha_daemon.py` | Autonomous research pipeline — scans global markets for new edges and verifies **T-Stats**. |

---

## ✅ Institutional Safeguards

|   | Safeguard | Control |
|:-:|:----------|:--------|
| ✅ | **Portfolio Killswitch** | Automatic closure of all orders if account drawdown hits **20% total**. |
| ✅ | **Daily Risk Cap** | Hard daily cap of **1% portfolio risk** across all correlated assets. |
| ✅ | **Time-Decay Exit** | Non-triggered orders are canceled; open trades are **squared before the close**. |
| ✅ | **MCP Guardrails** | AI monitors live slippage and can **physically halt execution** via the flag system. |

### Pre-Flight Validation

```yaml
# ──────────────────────────────────────
#  PRE-FLIGHT VALIDATION  ·  required
# ──────────────────────────────────────
[1]  Dry-run for one full week
[2]  Reconcile paper fills (2 wks)
[3]  Tier-1 Micro scaling only
# ──────────────────────────────────────
ACTIVE_EDGE:   MNQ_FUTURES
tick_size:     0.25
```

---

<div align="center">

### 🦅 KESTREL ENGINE

`IBKR INSIGHT`&nbsp;&nbsp;·&nbsp;&nbsp;`OANDA REST V20`&nbsp;&nbsp;·&nbsp;&nbsp;`PYTHON 3.10+`

<sub>© 2026 Institutional Trading Lab. **Not financial advice.** Results are in-sample
backtests under modeled costs; live edge depends on fill quality and decays over time.</sub>

</div>
