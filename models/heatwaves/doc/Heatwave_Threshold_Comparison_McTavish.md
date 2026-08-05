# Heatwave Threshold Options — McTavish Station (Downtown Montreal)

> **Context:** The McTavish station is located downtown and reflects the **Urban Heat Island (UHI)** effect. Compared to the airport, it typically has **warmer nights** (higher Tmin) but sometimes slightly cooler daytime peaks depending on wind/shading.
> 
> *Note: ECCC has also utilized a two-day threshold of a maximum temperature ≥ 32°C and a minimum temperature ≥ 20°C (Option C below).*

## Options Summary & Interpretation

| Option | Thresholds | Days | Captures | FP Rate | Result Interpretation (Simple Terms) |
|--------|-----------|------|----------|---------|--------------------------------------|
| **A. INSPQ Strict** | 33/20, 3d | 40 | 6/16 | 37.5% | **Too strict:** Misses 10 out of 16 major events. Downtown rarely sustains 33°C for 3 full days despite dangerous heat. |
| **B. ECCC Warning** | 30/20, 2d | 264 | 14/16 | 78.4% | **Highly inclusive:** Captures almost everything (14/16), including 2006 and 2022. But flags nearly every warm summer period (264 days total). |
| **C. ECCC Extreme** | **32/20, 2d** | **93** | **11/16** | **59.1%** | **Best balance:** Captures the severe defining waves with half the noise of Option B. Only 93 total days. Missing the mildest events. |
| **D. Hybrid** | 31/20, 3d | 175 | 11/16 | 70.9% | **Noisy middle-ground:** Requiring 3 days makes it miss severe 2-day bursts, while 31°C Tmax lets in too much background summer heat. |
| **E. ECCC + Humidex**| 30/20 & H≥40 | 130 | 12/16 | 66.9% | **Humidity-focused:** Better than B, but humidex data can be patchy, and it still flags 130 days. |

---

## Event Capture Matrix (McTavish Data)

Each cell = days detected in your expected period. ❌ = missed.

| Event | A. INSPQ 33/20 3d | B. ECCC 30/20 2d | C. ECCCExtreme 32/20 2d | D. Hybrid 31/20 3d | E. ECCC+H40 30/20 2d |
|-------|:--:|:--:|:--:|:--:|:--:|
| 2001 Early Aug | 5d | 9d | 4d | 9d | 4d |
| 2002 Early Jul | 3d | 5d | 4d | 5d | 4d |
| 2005 Late Jul | ❌ | ❌ | ❌ | ❌ | ❌ |
| 2006 July | ❌ | 2d ✅ | ❌ | ❌ | 2d ✅ |
| 2010 Jul 4–9 | 4d | 6d | 4d | 6d | 5d |
| 2011 Jul 20–22 | ❌ | 3d | 3d | 3d | 3d |
| 2018 Jun 29–Jul 5| 6d | 7d | 6d | 7d | 6d |
| 2019 June | ❌ | ❌ | ❌ | ❌ | ❌ |
| 2020 May 26–28 | ❌ | 2d | 2d | 3d | ❌ |
| 2021 Aug 24–26 | 3d | 3d | 3d | 3d | 3d |
| 2022 Mid-June | ❌ | 1d ✅ | ❌ | ❌ | ❌ |
| 2023 Summer | ❌ | 3d | ❌ | ❌ | 2d |
| 2024 Jun 18–20 | ❌ | 3d | 3d | 3d | 3d |
| 2025 Jun 22–24 | ❌ | 3d | 3d | 3d | 3d |
| 2025 Jul 11–17 | ❌ | 6d | 2d | 4d | 5d |
| 2025 Aug 10–15 | 4d | 4d | 4d | 5d | 3d |
| **CAPTURED** | **6/16** | **14/16** | **11/16** | **11/16** | **12/16** |

### Key Differences vs. Airport (YUL)
Using the downtown McTavish station drastically altered what the thresholds catch:
1. **INSPQ (Option A) performs worse downtown (6/16 vs 9/16 at YUL).** Why? Daytime highs at McTavish often peak just under 33°C (e.g. 32.5°C), missing the strict daytime threshold, even though nights are warmer.
2. **ECCC 30/20 (Option B) performs better downtown (14/16 vs 12/16 at YUL).** It successfully catches **2006 July** and **2022 Mid-June** here, which were completely missed at the airport.
3. **2005 Late Jul and 2019 June** are *still* missed by all standard temperature filters, confirming they were either very humid but not remarkably hot, or very localized events.

---

## Conclusion & Recommendation

If you want the machine learning model to predict:
- **Major, deadly wave events only:** Use **Option C (ECCC 32/20 2d)**. It gives a clean, highly specific dataset (93 days).
- **Any period of elevated heat risk:** Use **Option B (ECCC 30/20 2d)**. It aligns best with public heat warnings and captures 14 of your 16 events, at the cost of including many lesser hot spells.
