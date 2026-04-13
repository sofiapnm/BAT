from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


CSV_PATH = Path("/workspaces/BAT/AEM Python Sim/Data Sorting/DATA/REAL 2024 data.csv")
HTML_PATH = Path("/workspaces/BAT/AEM Python Sim/Data Sorting/Plots/waterlevel_2_plot.html")


def main() -> None:
    df = pd.read_csv(CSV_PATH, sep=";")

    df["DateTime"] = pd.to_datetime(df["DateTime"], format="%d.%m.%Y %H:%M")
    df = df.sort_values("DateTime").reset_index(drop=True)

    numeric_columns = [
        "Absatz (Verkauf)",
        "Production MI",
        "Production MII",
        "MI Wstd [%]",
        "MII Wstd [%]",
    ]
    df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric, errors="coerce")

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        subplot_titles=(
            "Production MI/MII with Absatz (Verkauf)",
            "MI/MII Wstd with Absatz (Verkauf)",
        ),
        specs=[
            [{"secondary_y": True}],
            [{"secondary_y": True}],
        ],
    )

    fig.add_trace(
        go.Scatter(
            x=df["DateTime"],
            y=df["Production MI"],
            mode="lines",
            name="Production MI",
            line=dict(width=2, color="#0b6e4f"),
        ),
        row=1,
        col=1,
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df["DateTime"],
            y=df["Production MII"],
            mode="lines",
            name="Production MII",
            line=dict(width=2, color="#f4a259"),
        ),
        row=1,
        col=1,
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df["DateTime"],
            y=df["Absatz (Verkauf)"],
            mode="lines",
            name="Absatz (Verkauf) - Production plot",
            line=dict(width=2, color="#1d3557", dash="dash"),
        ),
        row=1,
        col=1,
        secondary_y=True,
    )
    fig.add_trace(
        go.Scatter(
            x=df["DateTime"],
            y=df["MI Wstd [%]"],
            mode="lines",
            name="MI Wstd [%]",
            line=dict(width=2, color="#33658a"),
        ),
        row=2,
        col=1,
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df["DateTime"],
            y=df["MII Wstd [%]"],
            mode="lines",
            name="MII Wstd [%]",
            line=dict(width=2, color="#bc4749"),
        ),
        row=2,
        col=1,
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df["DateTime"],
            y=df["Absatz (Verkauf)"],
            mode="lines",
            name="Absatz (Verkauf) - Water plot",
            line=dict(width=2, color="#1d3557", dash="dash"),
        ),
        row=2,
        col=1,
        secondary_y=True,
    )

    fig.update_layout(
        title="Production, Water Level, and Absatz (Verkauf) Over Time",
        legend_title="Series",
        template="plotly_white",
        hovermode="x unified",
        height=900,
    )
    fig.update_xaxes(title_text="DateTime", row=2, col=1)
    fig.update_yaxes(title_text="Production", row=1, col=1, secondary_y=False)
    fig.update_yaxes(title_text="Absatz (Verkauf)", row=1, col=1, secondary_y=True)
    fig.update_yaxes(title_text="Water Level [%]", range=[0, 200], row=2, col=1, secondary_y=False)
    fig.update_yaxes(title_text="Absatz (Verkauf)", row=2, col=1, secondary_y=True)

    fig.write_html(HTML_PATH, include_plotlyjs=True)
    print(f"HTML graph written to: {HTML_PATH}")


if __name__ == "__main__":
    main()
