from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
from typing import Dict, List

from dotenv import load_dotenv
import numpy as np
import pandas as pd
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS


# Load environment variables from a local .env file (if present)
# Create quant_finance/.env with a line like:
# TWELVE_DATA_API_KEY=your_real_key_here
load_dotenv()

app = Flask(__name__)
CORS(app)


API_BASE_URL = "https://api.twelvedata.com"
RISK_FREE_RATE = 0.02  # 2% annual, used for simple Sharpe ratio


@dataclass
class PriceSeries:
    dates: pd.DatetimeIndex
    prices: np.ndarray


def _get_api_key() -> str | None:
    """Read Twelve Data API key from environment, return None if missing."""
    return os.getenv("TWELVE_DATA_API_KEY")


def fetch_prices(symbol: str, outputsize: int = 90) -> PriceSeries:
    """
    Fetch daily close prices for a symbol.

    If an API key is not configured or the request fails, fall back to a simple
    mock random-walk series so the app still works in demos/classrooms.
    """
    api_key = _get_api_key()
    if not api_key:
        # Fail fast – this project is meant to use real data only.
        raise ValueError("TWELVE_DATA_API_KEY is not configured on the server")

    try:
        resp = requests.get(
            f"{API_BASE_URL}/time_series",
            params={
                "symbol": symbol,
                "interval": "1day",
                "outputsize": outputsize,
                "apikey": api_key,
            },
            timeout=8,
        )
        data = resp.json()
        if "values" not in data:
            # Propagate a clear error instead of silently faking data
            message = data.get("message") or f"No values returned for symbol {symbol}"
            raise ValueError(f"Twelve Data error for {symbol}: {message}")

        df = pd.DataFrame(data["values"])
        df["datetime"] = pd.to_datetime(df["datetime"])
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df = df.sort_values("datetime").dropna(subset=["close"])

        if len(df) < 30:
            raise ValueError(f"Not enough price history returned for symbol {symbol}")

        # Use a DatetimeIndex so we can safely call .intersection()
        dates_index = pd.DatetimeIndex(df["datetime"])
        return PriceSeries(dates=dates_index, prices=df["close"].to_numpy())
    except ValueError:
        # Re-raise our own explicit value errors unchanged
        raise
    except Exception as e:
        # Network or parsing issues – surface as a clear error
        raise ValueError(f"Failed to fetch data for {symbol}: {e}")


def compute_metrics(portfolio: List[Dict[str, float]]) -> Dict:
    """
    Compute basic portfolio metrics from a list of {symbol, allocation}.

    - Fetches per-symbol price history
    - Builds a normalized portfolio value curve
    - Computes expected annual return, volatility and Sharpe ratio
    """
    symbols = [item["symbol"].upper() for item in portfolio]
    weights = np.array([float(item["allocation"]) / 100.0 for item in portfolio])

    # Fetch all price series
    series_map: Dict[str, PriceSeries] = {s: fetch_prices(s) for s in symbols}

    # Align on common dates (inner join)
    all_dates = None
    for ps in series_map.values():
        all_dates = ps.dates if all_dates is None else all_dates.intersection(ps.dates)

    if all_dates is None or len(all_dates) < 30:
        raise ValueError("Not enough overlapping price data to analyze portfolio.")

    all_dates = all_dates.sort_values()

    # Build matrix of aligned prices
    price_matrix = []
    for s in symbols:
        ps = series_map[s]
        aligned = (
            pd.Series(ps.prices, index=ps.dates)
            .reindex(all_dates)
            .interpolate()
            .bfill()
            .ffill()
        )
        price_matrix.append(aligned.to_numpy())

    price_matrix = np.vstack(price_matrix).T  # shape (T, N)

    # Compute daily returns per symbol
    daily_returns = price_matrix[1:] / price_matrix[:-1] - 1.0  # (T-1, N)

    # Portfolio daily returns as weighted sum
    port_daily_returns = daily_returns @ weights  # (T-1,)

    # Annualised metrics (assuming 252 trading days)
    mean_daily = float(np.mean(port_daily_returns))
    std_daily = float(np.std(port_daily_returns))

    expected_return = mean_daily * 252
    volatility = std_daily * np.sqrt(252)
    sharpe = (
        (expected_return - RISK_FREE_RATE) / volatility if volatility > 0 else 0.0
    )

    # Build normalized portfolio value curve
    port_values = 100.0 * np.cumprod(1 + port_daily_returns)
    value_dates = all_dates[1:]

    history = [
        {
            "date": d.strftime("%Y-%m-%d"),
            "value": round(float(v), 2),
        }
        for d, v in zip(value_dates, port_values)
    ]

    return {
        "portfolio_metrics": {
            "expected_return": round(expected_return, 4),
            "volatility": round(volatility, 4),
            "sharpe_ratio": round(sharpe, 2),
        },
        "history": history,
    }


@app.route("/api/health", methods=["GET"])
def health() -> tuple[dict, int]:
    """Simple health check for the QuantWise backend."""
    return jsonify({"status": "ok"}), 200


@app.route("/api/analyze", methods=["POST"])
def analyze_portfolio() -> tuple[dict, int]:
    """
    Analyze a simple portfolio.

    Expects JSON:
    {
      "portfolio": [
        { "symbol": "AAPL", "allocation": 50 },
        { "symbol": "MSFT", "allocation": 50 }
      ]
    }
    """
    data = request.get_json(silent=True) or {}
    portfolio = data.get("portfolio") or []

    if not isinstance(portfolio, list) or not portfolio:
        return jsonify({"error": "Portfolio must be a non-empty list."}), 400

    try:
        total_alloc = sum(float(item.get("allocation", 0.0)) for item in portfolio)
    except (TypeError, ValueError):
        return jsonify({"error": "All allocations must be numeric."}), 400

    if abs(total_alloc - 100.0) > 1e-3:
        return (
            jsonify(
                {
                    "error": "Total allocation must sum to 100.",
                    "total_allocation": total_alloc,
                }
            ),
            400,
        )

    try:
        result = compute_metrics(portfolio)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        # For classroom use it's okay to expose a simple error string
        return jsonify({"error": f"Internal error: {e}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)

