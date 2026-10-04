# ============================================================
# visualizer.py
# PURPOSE: Create charts and warehouse grid using Plotly
# WHAT YOU LEARN: data visualization, plotly, color mapping
# ============================================================

import plotly.graph_objects as go  # Low-level: build charts manually
import plotly.express as px         # High-level: quick charts from DataFrames
import pandas as pd


# Color palette for zones
ZONE_COLORS = {
    "A": "#22c55e",   # Green  - closest to exit
    "B": "#f59e0b",   # Amber  - medium distance
    "C": "#ef4444",   # Red    - furthest from exit
}

# Color palette for categories
CATEGORY_COLORS = {
    "Electronics": "#3b82f6",
    "Stationery":  "#8b5cf6",
    "Furniture":   "#f97316",
}


def plot_warehouse_grid(assignments_df, warehouse_df):
    """
    Draw the warehouse as a visual grid.
    Each cell = one slot, colored by zone.
    Hover over a cell to see what product is stored there.

    X axis = column, Y axis = row (row 1 at top)
    """

    # Merge warehouse slots with assignment results
    # how="left" keeps ALL warehouse slots even if empty (no assignment yet)
    if not assignments_df.empty:
        merged = warehouse_df.merge(
            assignments_df[["slot_id", "product_name", "pick_frequency", "category", "travel_score"]],
            on="slot_id",
            how="left"
        )
    else:
        merged = warehouse_df.copy()
        merged["product_name"] = None
        merged["pick_frequency"] = None
        merged["category"] = None
        merged["travel_score"] = None

    # Fill empty slots with placeholders
    merged["display_name"] = merged["product_name"].fillna("Empty")
    merged["display_freq"] = merged["pick_frequency"].fillna(0)
    merged["color"] = merged["zone"].map(ZONE_COLORS).fillna("#94a3b8")

    # Build hover tooltip text for each slot
    # apply(lambda row: ..., axis=1) runs a function on each row
    merged["hover_text"] = merged.apply(lambda row: (
        f"<b>Slot:</b> {row['slot_id']}<br>"
        f"<b>Zone:</b> {row['zone']}<br>"
        f"<b>Product:</b> {row['display_name']}<br>"
        f"<b>Pick Frequency:</b> {int(row['display_freq'])}/day<br>"
        f"<b>Distance:</b> {row['distance_from_exit']} units<br>"
        f"<b>Capacity:</b> {row['capacity_kg']} kg"
    ), axis=1)

    fig = go.Figure()

    # Add one scatter trace per zone (so each zone appears in the legend)
    for zone, color in ZONE_COLORS.items():
        zone_data = merged[merged["zone"] == zone]

        fig.add_trace(go.Scatter(
            x=zone_data["column"],
            y=zone_data["row"],
            mode="markers+text",
            marker=dict(
                size=55,
                color=color,
                symbol="square",
                line=dict(width=2, color="white")
            ),
            # Truncate long product names to fit inside cell
            text=zone_data["display_name"].apply(
                lambda x: x[:8] + ".." if len(str(x)) > 8 else x
            ),
            textfont=dict(size=8, color="white"),
            hovertext=zone_data["hover_text"],
            hoverinfo="text",
            name=f"Zone {zone}",
        ))

    # Add EXIT label at origin
    fig.add_annotation(
        x=0.5, y=0,
        text="🚪 EXIT",
        showarrow=False,
        font=dict(size=14, color="#1e293b"),
        bgcolor="#fef9c3",
        bordercolor="#ca8a04",
        borderwidth=2,
        borderpad=6
    )

    fig.update_layout(
        title=dict(text="Warehouse Slot Map", font=dict(size=18)),
        xaxis=dict(title="Column", dtick=1, gridcolor="#e2e8f0"),
        yaxis=dict(title="Row", dtick=1, autorange="reversed", gridcolor="#e2e8f0"),
        plot_bgcolor="#f8fafc",
        paper_bgcolor="white",
        height=500,
        showlegend=True,
        hovermode="closest"
    )

    return fig


def plot_frequency_vs_distance(assignments_df):
    """
    Scatter plot: frequency on Y, distance on X.
    Good optimization = downward trend (high frequency = low distance).
    """

    if assignments_df.empty:
        return go.Figure()

    fig = px.scatter(
        assignments_df,
        x="distance_from_exit",
        y="pick_frequency",
        color="category",
        size="weight_kg",
        hover_name="product_name",
        hover_data=["slot_id", "zone", "travel_score"],
        color_discrete_map=CATEGORY_COLORS,
        title="Pick Frequency vs Distance from Exit",
        labels={
            "distance_from_exit": "Distance from Exit (units)",
            "pick_frequency": "Daily Pick Frequency",
        }
    )

    fig.update_layout(plot_bgcolor="#f8fafc", paper_bgcolor="white", height=400)
    return fig


def plot_zone_distribution(zone_summary_df):
    """
    Bar chart: how many products are in each zone.
    """

    if zone_summary_df.empty:
        return go.Figure()

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=zone_summary_df["zone"],
        y=zone_summary_df["products_count"],
        marker_color=[ZONE_COLORS.get(z, "#94a3b8") for z in zone_summary_df["zone"]],
        text=zone_summary_df["products_count"],
        textposition="outside"
    ))

    fig.update_layout(
        title="Products per Zone",
        xaxis_title="Zone",
        yaxis_title="Number of Products",
        plot_bgcolor="#f8fafc",
        paper_bgcolor="white",
        height=350,
        showlegend=False
    )

    return fig


def plot_travel_score_breakdown(assignments_df):
    """
    Horizontal bar chart: each product's travel score.
    High score = product is frequent OR placed far away.
    Lower is better — this chart reveals any inefficiencies.
    """

    if assignments_df.empty:
        return go.Figure()

    sorted_df = assignments_df.sort_values("travel_score", ascending=True)
    bar_colors = [CATEGORY_COLORS.get(cat, "#94a3b8") for cat in sorted_df["category"]]

    fig = go.Figure(go.Bar(
        x=sorted_df["travel_score"],
        y=sorted_df["product_name"],
        orientation="h",   # "h" = horizontal bars
        marker_color=bar_colors,
        text=sorted_df["travel_score"].round(0),
        textposition="outside"
    ))

    fig.update_layout(
        title="Travel Score per Product (lower = better placement)",
        xaxis_title="Travel Score (frequency × distance)",
        yaxis_title="Product",
        plot_bgcolor="#f8fafc",
        paper_bgcolor="white",
        height=max(300, len(sorted_df) * 30),
        showlegend=False
    )

    return fig


def plot_category_pie(assignments_df):
    """
    Donut chart showing product count by category.
    hole=0.4 makes it a donut instead of a full pie.
    """

    if assignments_df.empty:
        return go.Figure()

    # value_counts() = count occurrences of each unique value
    category_counts = assignments_df["category"].value_counts().reset_index()
    category_counts.columns = ["category", "count"]

    fig = px.pie(
        category_counts,
        values="count",
        names="category",
        title="Product Distribution by Category",
        color="category",
        color_discrete_map=CATEGORY_COLORS,
        hole=0.4
    )

    fig.update_layout(paper_bgcolor="white", height=350)
    return fig