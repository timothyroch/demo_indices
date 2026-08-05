import pandas as pd


def build_weather_dataframe(
    history: list[dict],
    temp: float | None,
    precip: float | None,
) -> pd.DataFrame:
    rows = [
        {
            "Date/Heure": record["date"],
            "Temp moy.(°C)": record["temperature"],
            "Précip. tot. (mm)": record["precipitation"],
        }
        for record in history
    ]

    rows.append(
        {
            "Date/Heure": pd.Timestamp.now(tz="UTC"),
            "Temp moy.(°C)": float(temp) if temp is not None else 0.0,
            "Précip. tot. (mm)": float(precip) if precip is not None else 0.0,
        }
    )

    df = pd.DataFrame(rows)
    df["Date/Heure"] = pd.to_datetime(df["Date/Heure"], utc=True)
    df["Month"] = df["Date/Heure"].dt.month
    df["Season"] = df["Month"].apply(_get_season)

    return df.sort_values("Date/Heure").reset_index(drop=True)


def _get_season(month: int) -> str:
    if month in [12, 1, 2]:
        return "winter"
    if month in [3, 4, 5]:
        return "spring"
    if month in [6, 7, 8]:
        return "summer"
    return "fall"
