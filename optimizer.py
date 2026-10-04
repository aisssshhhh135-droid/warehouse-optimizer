# ============================================================
# optimizer.py
# PURPOSE: Assign products to warehouse slots optimally
# WHAT YOU LEARN: algorithms, greedy approach, optimization logic
# ============================================================

import pandas as pd
import numpy as np


# ============================================================
# CORE CONCEPT:
#
# GOAL: Minimize total travel distance in the warehouse.
# RULE: Products picked MORE OFTEN → placed CLOSER to the exit.
#
# SCORE formula:
#   travel_score = pick_frequency × distance_from_exit
#
# We want TOTAL SCORE to be as LOW as possible.
# ============================================================


def greedy_optimize(products_df, warehouse_df):
    """
    Greedy Algorithm: Assign the most-picked product to the closest slot.

    Steps:
    1. Products sorted by pick_frequency (highest first)
    2. Slots sorted by distance_from_exit (closest first)
    3. Match them one by one — always take the best available slot

    Returns:
        assignments_df  - DataFrame of product-to-slot assignments
        total_score     - sum of (frequency × distance), lower = better
        unassigned      - list of products that didn't fit any slot
    """

    assignments = []          # Stores each assignment as a dict
    unassigned_products = []  # Products we couldn't place

    # .copy() prevents accidentally modifying the originals
    slots = warehouse_df.copy()
    slots["available_capacity"] = slots["capacity_kg"]  # Track remaining space
    slots["assigned_product"] = None                     # Track what's in each slot

    # Loop through each product (highest frequency first)
    for _, product in products_df.iterrows():
        # iterrows() gives one row at a time: (index, row_data)
        # _ = we don't need the index number

        product_weight = product["weight_kg"]
        assigned = False  # Will flip to True once we find a slot

        # Loop through slots (closest to exit first)
        for slot_idx, slot in slots.iterrows():

            # Can this slot hold the product's weight?
            if slot["available_capacity"] >= product_weight:

                # ✅ Assign this product to this slot
                assignments.append({
                    "product_id":        product["product_id"],
                    "product_name":      product["product_name"],
                    "weight_kg":         product_weight,
                    "pick_frequency":    product["pick_frequency"],
                    "category":          product["category"],
                    "slot_id":           slot["slot_id"],
                    "zone":              slot["zone"],
                    "row":               slot["row"],
                    "column":            slot["column"],
                    "distance_from_exit": slot["distance_from_exit"],
                    # How much daily travel this assignment causes
                    "travel_score": product["pick_frequency"] * slot["distance_from_exit"]
                })

                # Reduce slot's remaining capacity
                slots.at[slot_idx, "available_capacity"] -= product_weight
                slots.at[slot_idx, "assigned_product"] = product["product_id"]

                assigned = True
                break  # Product is placed — stop searching slots

        if not assigned:
            unassigned_products.append(product["product_name"])

    # Convert list of dicts → DataFrame
    if assignments:
        assignments_df = pd.DataFrame(assignments)
        total_score = assignments_df["travel_score"].sum()
    else:
        assignments_df = pd.DataFrame()
        total_score = 0

    return assignments_df, total_score, unassigned_products


def calculate_efficiency_gain(assignments_df, products_df, warehouse_df):
    """
    Compare our optimized score vs worst-case (reversed assignment).
    Shows HOW MUCH better our algorithm performs.

    Returns:
        efficiency_gain_pct - % improvement over worst case
        worst_score         - score if least-used items were placed closest
        best_score          - our optimized score
    """

    if assignments_df.empty:
        return 0, 0, 0

    best_score = assignments_df["travel_score"].sum()

    # Worst case: LEAST frequent items get CLOSEST slots (backwards!)
    products_reversed = products_df.sort_values("pick_frequency", ascending=True).reset_index(drop=True)
    slots_sorted = warehouse_df.sort_values("distance_from_exit", ascending=True).reset_index(drop=True)

    worst_score = 0
    # zip() pairs two lists element by element: [(product1, slot1), (product2, slot2)...]
    for i, (_, product) in enumerate(products_reversed.iterrows()):
        if i < len(slots_sorted):
            slot = slots_sorted.iloc[i]  # .iloc[i] = get row by position number
            worst_score += product["pick_frequency"] * slot["distance_from_exit"]

    if worst_score > 0:
        efficiency_gain_pct = round(((worst_score - best_score) / worst_score) * 100, 1)
    else:
        efficiency_gain_pct = 0

    return efficiency_gain_pct, worst_score, best_score


def get_zone_summary(assignments_df):
    """
    Group assignments by warehouse zone and compute per-zone stats.
    Uses pandas groupby() — like SQL GROUP BY.
    """

    if assignments_df.empty:
        return pd.DataFrame()

    zone_summary = assignments_df.groupby("zone").agg(
        products_count      = ("product_id",       "count"),
        avg_frequency       = ("pick_frequency",   "mean"),
        total_weight        = ("weight_kg",         "sum"),
        avg_distance        = ("distance_from_exit","mean"),
        total_travel_score  = ("travel_score",      "sum")
    ).reset_index()

    zone_summary["avg_frequency"]      = zone_summary["avg_frequency"].round(1)
    zone_summary["total_weight"]       = zone_summary["total_weight"].round(2)
    zone_summary["avg_distance"]       = zone_summary["avg_distance"].round(1)
    zone_summary["total_travel_score"] = zone_summary["total_travel_score"].round(1)

    return zone_summary.sort_values("avg_distance")


def get_category_summary(assignments_df):
    """
    Group assignments by product category.
    Useful to confirm Electronics are near exit, Furniture at the back.
    """

    if assignments_df.empty:
        return pd.DataFrame()

    category_summary = assignments_df.groupby("category").agg(
        products_count     = ("product_id",        "count"),
        avg_frequency      = ("pick_frequency",    "mean"),
        avg_distance       = ("distance_from_exit","mean"),
        total_travel_score = ("travel_score",       "sum")
    ).reset_index()

    category_summary["avg_frequency"]      = category_summary["avg_frequency"].round(1)
    category_summary["avg_distance"]       = category_summary["avg_distance"].round(1)
    category_summary["total_travel_score"] = category_summary["total_travel_score"].round(1)

    return category_summary.sort_values("avg_distance")