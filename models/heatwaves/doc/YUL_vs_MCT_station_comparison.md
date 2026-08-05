# Station Comparison — YUL vs McTavish

## Overview

| | **YUL — Montreal Airport** | **WTA — McTavish** |
|---|---|---|
| Stations | 5415 → 51157 | 10761 |
| Rows | 3,975 | 3,975 |
| Date range | 2000-05-01 → 2025-09-27 | 2000-05-01 → 2025-09-27 |
| Heatwave days | **45** (9 years) | **40** (7 years) |
| Target positive % | 1.74% | 1.41% |

## Heatwave Days — Years With Events

| Year | YUL | MCT | Diff | Agree? |
|------|-----|-----|------|--------|
| 2001 | 3 | 5 | +2 | ✓ |
| 2002 | 6 | 6 | 0 | ✓ |
| 2010 | 4 | 4 | 0 | ✓ |
| **2011** | **4** | **0** | **−4** | **✗** |
| 2018 | 6 | 6 | 0 | ✓ |
| 2020 | 8 | 6 | −2 | ✓ |
| 2021 | 3 | 7 | +4 | ✓ |
| **2024** | **3** | **0** | **−3** | **✗** |
| 2025 | 8 | 6 | −2 | ✓ |

## Heatwave Date Agreement

**31 shared** · 14 YUL-only · 9 MCT-only

### YUL-Only Heatwave Dates

| Date | YUL Tmax | MCT Tmax | Δ |
|------|----------|----------|---|
| 2011-07-20 | 31.5 | 30.8 | −0.7 |
| 2011-07-21 | 35.6 | 34.9 | −0.7 |
| 2011-07-22 | 31.9 | 31.3 | −0.6 |
| 2011-07-23 | 32.6 | 31.6 | −1.0 |
| 2020-07-08 | 31.0 | 29.7 | −1.3 |
| 2020-07-09 | 34.1 | 33.4 | −0.7 |
| 2020-07-10 | 36.1 | 35.0 | −1.1 |
| 2024-06-18 | 33.0 | 32.3 | −0.7 |
| 2024-06-19 | 33.7 | 33.1 | −0.6 |
| 2024-06-20 | 32.6 | 32.2 | −0.4 |
| 2025-06-22 | 30.2 | 29.4 | −0.8 |
| 2025-06-23 | 34.9 | 34.7 | −0.2 |
| 2025-06-24 | 35.6 | 34.7 | −0.9 |
| 2025-06-25 | 29.4 | 28.4 | −1.0 |

### MCT-Only Heatwave Dates

| Date | YUL Tmax | MCT Tmax | Δ |
|------|----------|----------|---|
| 2001-08-06 | 32.1 | 31.5 | −0.6 |
| 2001-08-10 | 30.9 | 30.0 | −0.9 |
| 2020-06-18 | 33.3 | 33.4 | +0.1 |
| 2021-08-20 | 32.1 | 33.6 | **+1.5** |
| 2021-08-21 | 34.0 | 35.0 | **+1.0** |
| 2021-08-22 | 32.4 | 33.5 | **+1.1** |
| 2021-08-23 | 31.1 | 31.8 | +0.7 |
| 2025-08-08 | 30.8 | N/A | — |
| 2025-08-13 | 28.5 | 29.4 | +0.9 |

## Temperature on Shared Heatwave Days

| Metric | MCT − YUL |
|--------|-----------|
| **Tmax** | **+0.06°C** (essentially equal) |
| **Tmin** | **+1.06°C** (urban heat island) |

> [!NOTE]
> **YUL Tmax runs ~0.7°C hotter** on disagreement days — the airport's flat, paved surface amplifies daytime highs past the threshold. **MCT Tmin runs ~1°C warmer** consistently — downtown urban heat island retains heat overnight.

## Data Completeness

| Column | YUL | MCT |
|--------|-----|-----|
| temp_max_c | 1.0% | 1.7% |
| temp_min_c | 0.9% | 1.3% |
| humidity_mean_pct | **0.0%** | 0.5% |
| wind_speed_mean_kmh | 0.0% | 2.5% |
| dew_point_mean_c | 0.0% | 0.5% |
| total_precip_mm | 0.5% | 3.8% |
| total_rain_mm | 0.5% | **100%** ⚠️ |
| visibility_mean_km | 0.0% | **100%** ⚠️ |

> [!WARNING]
> McTavish does not report `total_rain_mm` or `visibility_km`. Models using McTavish data should exclude these features.
