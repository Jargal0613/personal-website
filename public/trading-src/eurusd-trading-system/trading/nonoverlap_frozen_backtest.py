"""Reproduces data/reference/nonoverlap_frozen_results.csv (frozen reference).

Not used by the live trader. Needs pandas + numpy (not in requirements.txt)
and the input dataset, which lives in the research archive:
  tar -xzf /workspace/projects/ai-trading-archive-20261006.tar.gz \
      --strip-components=1 -C /workspace/projects/ai-trading \
      ai-trading-archive-20261006/data/market_structure_features.csv
Writes a *.reproduced.csv next to the frozen file so the reference is never
overwritten. Run from the project root.
"""

import pandas as pd
import numpy as np


INPUT_FILE = "data/market_structure_features.csv"

# Frozen from candidate confirmation.
STRATEGIES = [
    {
        "name": "ATR expansion",
        "feature": "atr_change_15m",
        "threshold": 0.18870875,
        "hold_minutes": 60,
    },
    {
        "name": "Large 5m range",
        "feature": "range_5m",
        "threshold": 0.00032600,
        "hold_minutes": 120,
    },
]

# Assumed ROUND-TRIP cost.
# These are model assumptions because historical bid/ask
# spreads are not available in the M1 dataset.
COSTS = [
    0.000,
    0.005,
    0.010,
    0.015,
    0.020,
]


def backtest(df, strategy, cost_percent):

    feature = strategy["feature"]
    threshold = strategy["threshold"]
    hold = strategy["hold_minutes"]

    trades = []

    i = 0
    last_entry = len(df) - hold - 1

    while i <= last_entry:

        # Signal is evaluated using the completed candle at i.
        signal = (
            df.iloc[i][feature] > threshold
        )

        if not signal:
            i += 1
            continue

        # Enter at the NEXT candle's open.
        entry_index = i + 1
        exit_index = entry_index + hold

        if exit_index >= len(df):
            break

        entry_price = df.iloc[
            entry_index
        ]["open"]

        exit_price = df.iloc[
            exit_index
        ]["open"]

        # SHORT return.
        gross_return = (
            (entry_price - exit_price)
            / entry_price
        ) * 100

        net_return = (
            gross_return - cost_percent
        )

        trades.append({
            "signal_index": i,
            "entry_index": entry_index,
            "exit_index": exit_index,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "gross_return": gross_return,
            "net_return": net_return,
        })

        # One position at a time.
        # Do not accept another signal until
        # this position has closed.
        i = exit_index + 1

    if not trades:
        return pd.DataFrame()

    return pd.DataFrame(trades)


def statistics(trades):

    if trades.empty:
        return None

    returns = trades[
        "net_return"
    ].to_numpy()

    wins = returns > 0
    losses = returns < 0

    gross_profit = returns[
        wins
    ].sum()

    gross_loss = -returns[
        losses
    ].sum()

    if gross_loss > 0:
        profit_factor = (
            gross_profit / gross_loss
        )
    else:
        profit_factor = np.inf

    equity = np.cumsum(returns)

    running_max = np.maximum.accumulate(
        equity
    )

    drawdown = (
        equity - running_max
    )

    max_drawdown = drawdown.min()

    return {
        "trades": len(trades),
        "win_rate": wins.mean() * 100,
        "avg_return": returns.mean(),
        "median_return": np.median(returns),
        "total_return": returns.sum(),
        "profit_factor": profit_factor,
        "max_drawdown": max_drawdown,
    }


def main():

    print()
    print("=" * 75)
    print("NON-OVERLAPPING FROZEN STRATEGY BACKTEST")
    print("=" * 75)
    print()

    df = pd.read_csv(
        INPUT_FILE
    )

    print(
        f"Input rows: {len(df)}"
    )

    print()

    all_results = []

    for strategy in STRATEGIES:

        print()
        print("=" * 75)
        print(
            f"STRATEGY: {strategy['name']}"
        )
        print("=" * 75)

        print(
            f"Feature: {strategy['feature']}"
        )

        print(
            f"Threshold: "
            f"{strategy['threshold']}"
        )

        print(
            f"Direction: SHORT"
        )

        print(
            f"Holding period: "
            f"{strategy['hold_minutes']} minutes"
        )

        print(
            "Entry: next candle OPEN"
        )

        print(
            "Execution: one position at a time"
        )

        print()

        for cost in COSTS:

            trades = backtest(
                df,
                strategy,
                cost,
            )

            result = statistics(
                trades
            )

            if result is None:
                print(
                    f"Cost {cost:.3f}% | "
                    "No trades"
                )
                continue

            pf = result[
                "profit_factor"
            ]

            if np.isinf(pf):
                pf_text = "inf"
            else:
                pf_text = f"{pf:.3f}"

            print(
                f"Cost {cost:.3f}% | "
                f"Trades={result['trades']:>4} | "
                f"Win={result['win_rate']:>6.2f}% | "
                f"Avg={result['avg_return']:+.6f}% | "
                f"Total={result['total_return']:+.4f}% | "
                f"PF={pf_text:>6} | "
                f"MaxDD={result['max_drawdown']:+.4f}%"
            )

            all_results.append({
                "strategy": strategy["name"],
                "cost_percent": cost,
                **result,
            })

        # ----------------------------------------------------
        # Show zero-cost trade distribution
        # ----------------------------------------------------

        trades = backtest(
            df,
            strategy,
            0.0,
        )

        if not trades.empty:

            print()
            print("Zero-cost trade distribution:")

            print(
                f"  Best trade:  "
                f"{trades['gross_return'].max():+.5f}%"
            )

            print(
                f"  Worst trade: "
                f"{trades['gross_return'].min():+.5f}%"
            )

            print(
                f"  Median:      "
                f"{trades['gross_return'].median():+.5f}%"
            )

            print(
                f"  25th pct:    "
                f"{trades['gross_return'].quantile(.25):+.5f}%"
            )

            print(
                f"  75th pct:    "
                f"{trades['gross_return'].quantile(.75):+.5f}%"
            )

    # --------------------------------------------------------
    # Save results
    # --------------------------------------------------------

    if all_results:

        results_df = pd.DataFrame(
            all_results
        )

        output_file = (
            "data/reference/"
            "nonoverlap_frozen_results.reproduced.csv"
        )

        results_df.to_csv(
            output_file,
            index=False,
        )

        print()
        print(
            f"Results saved to: "
            f"{output_file}"
        )

    print()
    print("=" * 75)
    print("BACKTEST COMPLETE")
    print("=" * 75)
    print()


if __name__ == "__main__":
    main()
