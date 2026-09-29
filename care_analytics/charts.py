"""Plotly charts for the synthetic log. Titles say SYNTHETIC."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

CHANNEL_ORDER = ["ussd", "app", "web", "social", "call"]
OUTCOMES = [
    "Resolved on first contact",
    "Resolved after another contact",
    "Abandoned",
]
CHANNEL_COLOURS = {
    "ussd": "#0B6E4F",
    "app": "#1B4F72",
    "web": "#2874A6",
    "social": "#6C3483",
    "call": "#922B21",
}
OUTCOME_COLOURS = {
    "Resolved on first contact": "#196F3D",
    "Resolved after another contact": "#B9770E",
    "Abandoned": "#7B241C",
}
SYNTHETIC_NOTE = "SYNTHETIC data. Not observed customer behaviour."


def friction_matrix(events: pd.DataFrame) -> pd.DataFrame:
    grouped = events.groupby(["category", "intent", "intent_group", "channel"], as_index=False).agg(
        contacts=("resolved", "size"),
        resolved_contacts=("resolved", "sum"),
    )
    grouped["contacts"] = grouped["contacts"].astype(int)
    grouped["resolved_contacts"] = grouped["resolved_contacts"].astype(int)
    grouped["friction"] = 1 - (grouped["resolved_contacts"] / grouped["contacts"])
    grouped["data_origin"] = "SYNTHETIC"
    return grouped.sort_values(["category", "intent", "channel"]).reset_index(drop=True)


def _write(fig: go.Figure, path: Path, div_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(
        path,
        include_plotlyjs="cdn",
        full_html=True,
        div_id=div_id,
        config={"displayModeBar": False, "responsive": True},
    )


def write_sankey(links: pd.DataFrame, path: Path) -> None:
    labels = CHANNEL_ORDER + OUTCOMES
    index = {label: position for position, label in enumerate(labels)}
    colours = [CHANNEL_COLOURS[label] for label in CHANNEL_ORDER] + [
        OUTCOME_COLOURS[label] for label in OUTCOMES
    ]
    present = links.loc[links["n"] > 0]
    figure = go.Figure(
        data=[
            go.Sankey(
                arrangement="snap",
                node={
                    "label": labels,
                    "color": colours,
                    "pad": 18,
                    "thickness": 18,
                    "line": {"width": 0},
                },
                link={
                    "source": [index[value] for value in present["first_channel"]],
                    "target": [index[value] for value in present["outcome"]],
                    "value": [int(value) for value in present["n"]],
                    "color": "rgba(80,80,80,0.25)",
                },
            )
        ]
    )
    figure.update_layout(
        title={
            "text": (
                "SYNTHETIC — first channel to journey outcome<br>"
                f"<sup>{SYNTHETIC_NOTE} Counts are simulated journeys.</sup>"
            ),
            "x": 0.02,
        },
        font={"size": 13, "family": "Arial"},
        paper_bgcolor="white",
        margin={"l": 20, "r": 20, "t": 80, "b": 20},
        height=520,
        width=860,
    )
    _write(figure, path, "synthetic-sankey")


def write_friction_heatmap(matrix: pd.DataFrame, path: Path) -> None:
    intents = (
        matrix[["category", "intent"]]
        .drop_duplicates()
        .sort_values(["category", "intent"])["intent"]
        .tolist()
    )
    friction = (
        matrix.pivot(index="intent", columns="channel", values="friction")
        .reindex(index=intents, columns=CHANNEL_ORDER)
    )
    counts = (
        matrix.pivot(index="intent", columns="channel", values="contacts")
        .reindex(index=intents, columns=CHANNEL_ORDER)
        .fillna(0)
    )
    text = []
    for intent in intents:
        row = []
        for channel in CHANNEL_ORDER:
            count = int(counts.loc[intent, channel])
            if count == 0 or pd.isna(friction.loc[intent, channel]):
                row.append("")
            else:
                row.append(f"{friction.loc[intent, channel] * 100:.0f}%<br>n={count}")
        text.append(row)
    figure = go.Figure(
        data=[
            go.Heatmap(
                z=friction.values,
                x=CHANNEL_ORDER,
                y=intents,
                colorscale="YlOrRd",
                zmin=0,
                zmax=1,
                colorbar={"title": "Friction"},
                customdata=counts.values,
                text=text,
                texttemplate="%{text}",
                hovertemplate=(
                    "intent %{y}<br>channel %{x}<br>friction %{z:.3f}"
                    "<br>contacts %{customdata}<extra></extra>"
                ),
            )
        ]
    )
    figure.update_layout(
        title={
            "text": (
                "SYNTHETIC — friction heatmap (1 − contact resolution rate)<br>"
                f"<sup>{SYNTHETIC_NOTE} Empty cells have no simulated contacts.</sup>"
            ),
            "x": 0.02,
        },
        font={"size": 11, "family": "Arial"},
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis={"title": "Channel", "side": "top"},
        yaxis={"title": "Intent", "autorange": "reversed"},
        margin={"l": 220, "r": 40, "t": 90, "b": 40},
        height=980,
        width=860,
    )
    _write(figure, path, "synthetic-friction-heatmap")
