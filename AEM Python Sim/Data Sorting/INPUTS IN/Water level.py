from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


CSV_PATH = Path("/workspaces/BAT/AEM Python Sim/Data Sorting/DATA/REAL 2024 data.csv")
HTML_PATH = Path("/workspaces/BAT/AEM Python Sim/Data Sorting/Plots/water_level_plot.html")


def main() -> None:
    df = pd.read_csv(CSV_PATH, sep=";")

    df["DateTime"] = pd.to_datetime(df["DateTime"], format="%d.%m.%Y %H:%M")
    df = df.sort_values("DateTime").reset_index(drop=True)

    numeric_columns = [
        "Production MI",
        "Production MII",
        "MI Wstd [%]",
        "MII Wstd [%]",
    ]
    df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric, errors="coerce")

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig.add_trace(
        go.Scatter(
            x=df["DateTime"],
            y=df["Production MII"],
            mode="lines",
            name="Production MII",
            line=dict(width=1, color="#f4a259"),
            stackgroup="production",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df["DateTime"],
            y=df["Production MI"],
            mode="lines",
            name="Production MI",
            line=dict(width=1, color="#0b6e4f"),
            stackgroup="production",
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=df["DateTime"],
            y=df["MII Wstd [%]"],
            mode="lines",
            name="MII Wstd [%]",
            line=dict(width=2, color="#bc4749"),
            stackgroup="water",
            fillcolor="rgba(0, 0, 0, 0)",
        ),
        secondary_y=True,
    )

    fig.add_trace(
        go.Scatter(
            x=df["DateTime"],
            y=df["MI Wstd [%]"],
            mode="lines",
            name="MI Wstd [%]",
            line=dict(width=2, color="#33658a"),
            stackgroup="water",
            fillcolor="rgba(0, 0, 0, 0)",
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title="Production and Water Level Over Time",
        xaxis_title="DateTime",
        yaxis_title="Production",
        legend_title="Series",
        template="plotly_white",
        hovermode="x unified",
    )
    fig.update_yaxes(title_text="Production", secondary_y=False)
    fig.update_yaxes(title_text="Water Level [%]", range=[0, 200], secondary_y=True)

    fig.write_html(HTML_PATH, include_plotlyjs=True)
    print(f"HTML graph written to: {HTML_PATH}")


if __name__ == "__main__":
    main()
