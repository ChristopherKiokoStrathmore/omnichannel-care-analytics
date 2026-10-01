"""Charts for the synthetic log.

HTML files are Plotly. PNG files are a matplotlib rendering of the same frames,
with a visible SYNTHETIC DATA label. Titles say SYNTHETIC.
"""

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
                "SYNTHETIC - first channel to journey outcome<br>"
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
                "SYNTHETIC - friction heatmap (1 − contact resolution rate)<br>"
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


def _pyplot():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def _mark_synthetic(fig, ax, title: str) -> None:
    ax.set_title(title, loc="left", fontsize=13, color="#1C2833", pad=10)
    fig.text(
        0.995,
        0.005,
        "SYNTHETIC DATA",
        ha="right",
        va="bottom",
        fontsize=10,
        color="#7B241C",
        fontweight="bold",
    )


def _save_png(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        path,
        format="png",
        dpi=140,
        bbox_inches="tight",
        facecolor="white",
        metadata={"Title": "SYNTHETIC DATA"},
    )


def _stack_layout(
    order: list[str], totals: dict[str, int], gap: float = 0.028
) -> tuple[dict[str, tuple[float, float]], float]:
    total = sum(totals[name] for name in order) or 1
    usable = 1.0 - gap * (len(order) - 1)
    scale = usable / total
    cursor = 1.0
    layout: dict[str, tuple[float, float]] = {}
    for name in order:
        height = totals[name] * scale
        bottom = cursor - height
        layout[name] = (bottom, height)
        cursor = bottom - gap
    return layout, scale


def sankey_png_figure(links: pd.DataFrame):
    """Matplotlib Sankey of the same first-channel to outcome counts as the HTML."""

    plt = _pyplot()
    present = links.loc[links["n"] > 0].copy()
    counts = {
        (str(row["first_channel"]), str(row["outcome"])): int(row["n"])
        for _, row in present.iterrows()
    }
    left_totals = {
        channel: sum(counts.get((channel, outcome), 0) for outcome in OUTCOMES)
        for channel in CHANNEL_ORDER
    }
    right_totals = {
        outcome: sum(counts.get((channel, outcome), 0) for channel in CHANNEL_ORDER)
        for outcome in OUTCOMES
    }
    left_layout, left_scale = _stack_layout(CHANNEL_ORDER, left_totals)
    right_layout, right_scale = _stack_layout(OUTCOMES, right_totals)
    left_cursor = {name: bottom + height for name, (bottom, height) in left_layout.items()}
    right_cursor = {name: bottom + height for name, (bottom, height) in right_layout.items()}

    fig, ax = plt.subplots(figsize=(11.2, 6.4), dpi=140)
    fig.patch.set_facecolor("white")
    ax.set_xlim(0.0, 1.42)
    ax.set_ylim(-0.02, 1.04)
    ax.axis("off")

    left_x, right_x, bar_w = 0.24, 0.70, 0.028
    for channel in CHANNEL_ORDER:
        for outcome in OUTCOMES:
            count = counts.get((channel, outcome), 0)
            if count <= 0:
                continue
            left_h = count * left_scale
            right_h = count * right_scale
            y_left = left_cursor[channel] - left_h
            y_right = right_cursor[outcome] - right_h
            left_cursor[channel] = y_left
            right_cursor[outcome] = y_right
            x0 = left_x + bar_w
            x1 = right_x
            xs = [x0 + (x1 - x0) * i / 40 for i in range(41)]
            span = x1 - x0 if x1 != x0 else 1
            top = []
            bottom = []
            for x_pos in xs:
                smooth = (x_pos - xs[0]) / span
                smooth = smooth * smooth * (3 - 2 * smooth)
                top.append((y_left + left_h) + ((y_right + right_h) - (y_left + left_h)) * smooth)
                bottom.append(y_left + (y_right - y_left) * smooth)
            ax.fill_between(xs, bottom, top, color=CHANNEL_COLOURS[channel], alpha=0.35, linewidth=0)

    for channel in CHANNEL_ORDER:
        bottom, height = left_layout[channel]
        ax.add_patch(
            plt.Rectangle(
                (left_x, bottom),
                bar_w,
                height,
                facecolor=CHANNEL_COLOURS[channel],
                edgecolor="none",
            )
        )
        ax.text(
            left_x - 0.015,
            bottom + height / 2,
            f"{channel}\n{left_totals[channel]}",
            ha="right",
            va="center",
            fontsize=9,
            color="#1C2833",
        )
    for outcome in OUTCOMES:
        bottom, height = right_layout[outcome]
        ax.add_patch(
            plt.Rectangle(
                (right_x, bottom),
                bar_w,
                height,
                facecolor=OUTCOME_COLOURS[outcome],
                edgecolor="none",
            )
        )
        ax.text(
            right_x + bar_w + 0.015,
            bottom + height / 2,
            f"{outcome}\n{right_totals[outcome]}",
            ha="left",
            va="center",
            fontsize=9,
            color="#1C2833",
        )
    _mark_synthetic(fig, ax, "SYNTHETIC DATA - first channel to journey outcome")
    fig.tight_layout()
    return fig


def write_sankey_png(links: pd.DataFrame, path: Path) -> None:
    plt = _pyplot()
    figure = sankey_png_figure(links)
    _save_png(figure, path)
    plt.close(figure)


def friction_png_figure(matrix: pd.DataFrame):
    """Matplotlib heatmap of the same friction matrix the HTML chart uses."""

    plt = _pyplot()
    intents = (
        matrix[["category", "intent"]]
        .drop_duplicates()
        .sort_values(["category", "intent"])["intent"]
        .tolist()
    )
    friction = matrix.pivot(index="intent", columns="channel", values="friction").reindex(
        index=intents, columns=CHANNEL_ORDER
    )
    counts = (
        matrix.pivot(index="intent", columns="channel", values="contacts")
        .reindex(index=intents, columns=CHANNEL_ORDER)
        .fillna(0)
    )
    fig, ax = plt.subplots(figsize=(10.2, 12.6), dpi=140)
    fig.patch.set_facecolor("white")
    image = ax.imshow(friction.to_numpy(dtype=float), cmap="YlOrRd", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(CHANNEL_ORDER)), CHANNEL_ORDER)
    ax.set_yticks(range(len(intents)), intents)
    ax.tick_params(axis="x", top=True, bottom=False, labeltop=True, labelbottom=False)
    ax.tick_params(axis="y", labelsize=8)
    ax.set_xlabel("Channel")
    ax.xaxis.set_label_position("top")
    for row_index, intent in enumerate(intents):
        for col_index, channel in enumerate(CHANNEL_ORDER):
            count = int(counts.loc[intent, channel])
            value = friction.loc[intent, channel]
            if count == 0 or pd.isna(value):
                continue
            ax.text(
                col_index,
                row_index,
                f"{float(value) * 100:.0f}%\nn={count}",
                ha="center",
                va="center",
                fontsize=6.5,
                color="white" if float(value) >= 0.55 else "#1C2833",
            )
    colorbar = fig.colorbar(image, ax=ax, fraction=0.035, pad=0.02)
    colorbar.set_label("Friction")
    _mark_synthetic(
        fig,
        ax,
        "SYNTHETIC DATA - friction heatmap (1 - contact resolution rate)",
    )
    fig.tight_layout()
    return fig


def write_friction_heatmap_png(matrix: pd.DataFrame, path: Path) -> None:
    plt = _pyplot()
    figure = friction_png_figure(matrix)
    _save_png(figure, path)
    plt.close(figure)
