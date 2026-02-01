import argparse
import json
import math
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd
import requests
from tqdm import tqdm


MFAPI_SCHEME_URL = "https://api.mfapi.in/mf/{scheme_code}"


@dataclass(frozen=True)
class ReturnMetrics:
    latest_nav: Optional[float]
    latest_date: Optional[pd.Timestamp]
    abs_return_1y: Optional[float]
    cagr_3y: Optional[float]
    cagr_5y: Optional[float]
    vol_1y_annualized: Optional[float]
    sharpe_1y_annualized: Optional[float]


def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        if isinstance(x, str) and x.strip() in {"", "-", "NA", "N/A", "nan", "NaN"}:
            return None
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except Exception:
        return None


def _parse_mfapi_date(s: str) -> Optional[pd.Timestamp]:
    # mfapi date format: "30-01-2026"
    try:
        ts = pd.to_datetime(s, format="%d-%m-%Y", errors="coerce")
        if pd.isna(ts):
            return None
        return ts
    except Exception:
        return None


def _pick_nav_on_or_before(df: pd.DataFrame, target: pd.Timestamp) -> Optional[Tuple[pd.Timestamp, float]]:
    """
    df must have columns: date (datetime), nav (float), sorted ascending by date.
    Returns (date, nav) for the last available observation <= target.
    """
    if df.empty:
        return None
    sub = df[df["date"] <= target]
    if sub.empty:
        return None
    row = sub.iloc[-1]
    return row["date"], float(row["nav"])


def compute_return_metrics(nav_df: pd.DataFrame) -> ReturnMetrics:
    """
    Expects columns: date (datetime64), nav (float). Can be unsorted.
    """
    if nav_df is None or nav_df.empty:
        return ReturnMetrics(None, None, None, None, None, None, None)

    df = nav_df.copy()
    df = df.dropna(subset=["date", "nav"])
    df = df.sort_values("date")
    if df.empty:
        return ReturnMetrics(None, None, None, None, None, None, None)

    latest_date = df["date"].iloc[-1]
    latest_nav = float(df["nav"].iloc[-1])

    # Target dates (calendar years)
    one_year_ago = latest_date - pd.Timedelta(days=365)
    three_years_ago = latest_date - pd.Timedelta(days=365 * 3)
    five_years_ago = latest_date - pd.Timedelta(days=365 * 5)

    nav_1y = _pick_nav_on_or_before(df, one_year_ago)
    nav_3y = _pick_nav_on_or_before(df, three_years_ago)
    nav_5y = _pick_nav_on_or_before(df, five_years_ago)

    abs_return_1y = None
    if nav_1y is not None and nav_1y[1] > 0:
        abs_return_1y = (latest_nav / nav_1y[1]) - 1.0

    cagr_3y = None
    if nav_3y is not None and nav_3y[1] > 0:
        cagr_3y = (latest_nav / nav_3y[1]) ** (1.0 / 3.0) - 1.0

    cagr_5y = None
    if nav_5y is not None and nav_5y[1] > 0:
        cagr_5y = (latest_nav / nav_5y[1]) ** (1.0 / 5.0) - 1.0

    # Volatility / Sharpe over last ~252 observations (approx 1 trading year)
    df_ret = df.copy()
    df_ret["ret"] = df_ret["nav"].pct_change()
    df_ret = df_ret.dropna(subset=["ret"])
    df_ret = df_ret.tail(252)

    vol_1y_annualized = None
    sharpe_1y_annualized = None
    if not df_ret.empty:
        mu = float(df_ret["ret"].mean())
        sigma = float(df_ret["ret"].std(ddof=1))
        if sigma > 0:
            vol_1y_annualized = sigma * math.sqrt(252.0)
            sharpe_1y_annualized = (mu / sigma) * math.sqrt(252.0)

    return ReturnMetrics(
        latest_nav=latest_nav,
        latest_date=latest_date,
        abs_return_1y=abs_return_1y,
        cagr_3y=cagr_3y,
        cagr_5y=cagr_5y,
        vol_1y_annualized=vol_1y_annualized,
        sharpe_1y_annualized=sharpe_1y_annualized,
    )


def fetch_mfapi_scheme(scheme_code: int, timeout_s: int) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    url = MFAPI_SCHEME_URL.format(scheme_code=scheme_code)
    try:
        r = requests.get(url, timeout=timeout_s)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, f"{type(e).__name__}: {str(e)}"


def mfapi_nav_history_to_df(payload: Dict[str, Any]) -> pd.DataFrame:
    """
    mfapi payload keys: meta, data (list of dicts with date/nav).
    data is typically reverse-chronological.
    """
    rows = payload.get("data") or []
    out = []
    for row in rows:
        d = _parse_mfapi_date(str(row.get("date", "")))
        nav = _safe_float(row.get("nav"))
        if d is None or nav is None:
            continue
        out.append({"date": d, "nav": nav})
    return pd.DataFrame(out)


def _load_checkpoint(path: str) -> int:
    if not os.path.exists(path):
        return 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        return int(obj.get("next_index", 0))
    except Exception:
        return 0


def _save_checkpoint(path: str, next_index: int) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"next_index": int(next_index)}, f)
    os.replace(tmp, path)


def _write_csv_best_effort(df: pd.DataFrame, path: str) -> str:
    """
    On Windows, writing to/overwriting a CSV that is open in Excel/IDE can raise PermissionError.
    If that happens, write to a sidecar file and return the actual path used.
    """
    try:
        df.to_csv(path, index=False)
        return path
    except PermissionError:
        alt = path + ".partial.csv"
        df.to_csv(alt, index=False)
        return alt


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a full mutual fund dataset with real returns/volatility from mfapi.in NAV history."
    )
    parser.add_argument("--scheme_list_csv", default="data/list1.csv", help="CSV containing Scheme Code and Scheme NAV Name.")
    parser.add_argument("--output_csv", default="data/mf_full_dataset.csv", help="Output CSV path.")
    parser.add_argument("--checkpoint_json", default="data/mf_full_dataset.checkpoint.json", help="Checkpoint file for resume.")
    parser.add_argument("--max_schemes", type=int, default=0, help="If >0, only process first N schemes (useful for testing).")
    parser.add_argument("--save_every", type=int, default=50, help="Flush partial results every N schemes.")
    parser.add_argument("--sleep_s", type=float, default=0.25, help="Sleep between API calls to be polite.")
    parser.add_argument("--timeout_s", type=int, default=30, help="HTTP timeout seconds.")
    args = parser.parse_args()

    df_list = pd.read_csv(args.scheme_list_csv)
    if "Scheme Code" not in df_list.columns:
        raise ValueError(f"Expected 'Scheme Code' in {args.scheme_list_csv}")
    if "Scheme NAV Name" not in df_list.columns:
        raise ValueError(f"Expected 'Scheme NAV Name' in {args.scheme_list_csv}")

    df_list = df_list[["Scheme Code", "Scheme NAV Name"]].dropna()
    df_list["Scheme Code"] = df_list["Scheme Code"].astype(int)
    df_list["Scheme NAV Name"] = df_list["Scheme NAV Name"].astype(str)

    if args.max_schemes and args.max_schemes > 0:
        df_list = df_list.head(args.max_schemes).copy()

    start_idx = _load_checkpoint(args.checkpoint_json)
    rows_out = []

    # Resume support: if output exists, load it and continue (dedupe by scheme_code).
    if os.path.exists(args.output_csv):
        try:
            existing = pd.read_csv(args.output_csv)
            if "scheme_code" in existing.columns:
                existing_codes = set(existing["scheme_code"].dropna().astype(int).tolist())
            else:
                existing_codes = set()
            rows_out.extend(existing.to_dict(orient="records"))
        except Exception:
            existing_codes = set()
    else:
        existing_codes = set()

    it = range(start_idx, len(df_list))
    for i in tqdm(it, desc="Building dataset"):
        scheme_code = int(df_list.iloc[i]["Scheme Code"])
        scheme_name_list = str(df_list.iloc[i]["Scheme NAV Name"])

        if scheme_code in existing_codes:
            _save_checkpoint(args.checkpoint_json, i + 1)
            continue

        payload, err = fetch_mfapi_scheme(scheme_code, timeout_s=args.timeout_s)
        meta = (payload or {}).get("meta") if payload else {}

        nav_df = mfapi_nav_history_to_df(payload) if payload else pd.DataFrame(columns=["date", "nav"])
        metrics = compute_return_metrics(nav_df)

        out_row = {
            "scheme_code": scheme_code,
            "scheme_name": meta.get("scheme_name") or scheme_name_list,
            "fund_house": meta.get("fund_house"),
            "scheme_type": meta.get("scheme_type"),
            "scheme_category": meta.get("scheme_category"),
            "isin_growth": meta.get("isin_growth"),
            "isin_div_reinvestment": meta.get("isin_div_reinvestment"),
            "plan": "Direct" if "direct" in scheme_name_list.lower() else "Regular",
            "latest_nav": metrics.latest_nav,
            "latest_nav_date": metrics.latest_date.strftime("%Y-%m-%d") if metrics.latest_date is not None else None,
            "abs_return_1y": metrics.abs_return_1y,
            "cagr_3y": metrics.cagr_3y,
            "cagr_5y": metrics.cagr_5y,
            "vol_1y_annualized": metrics.vol_1y_annualized,
            "sharpe_1y_annualized": metrics.sharpe_1y_annualized,
            # Not available from mfapi.in directly (and AMFI is returning 504 currently)
            "aum_cr": None,
            "expense_ratio": None,
            "status": "success" if payload else "failed",
            "error": err,
        }

        rows_out.append(out_row)
        existing_codes.add(scheme_code)

        if (len(existing_codes) % args.save_every) == 0:
            _write_csv_best_effort(pd.DataFrame(rows_out).drop_duplicates(subset=["scheme_code"]), args.output_csv)
            _save_checkpoint(args.checkpoint_json, i + 1)

        time.sleep(max(0.0, float(args.sleep_s)))

    _write_csv_best_effort(pd.DataFrame(rows_out).drop_duplicates(subset=["scheme_code"]), args.output_csv)
    _save_checkpoint(args.checkpoint_json, len(df_list))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

