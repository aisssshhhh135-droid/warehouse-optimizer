# ============================================================
# data_manager.py
# PURPOSE: Load, validate, and manage product & warehouse data
# WHAT YOU LEARN: pandas DataFrames, CSV handling, data validation
# ============================================================

import pandas as pd  # pandas = powerful library to work with tabular data (like Excel in Python)
import os            # os = lets us check if files exist on the computer


def load_products(filepath="data/products.csv"):
    """
    Load product data from a CSV file into a pandas DataFrame.

    A DataFrame is like a spreadsheet table in Python.
    Each row = one product. Each column = a property (name, weight, etc.)
    """

    # Check if the file actually exists before trying to open it
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Products file not found at: {filepath}")

    # pd.read_csv() reads the CSV file and turns it into a DataFrame
    df = pd.read_csv(filepath)

    # Validate that all required columns exist
    required_columns = ["product_id", "product_name", "weight_kg", "pick_frequency", "category"]
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Missing required column in products.csv: {col}")

    # Sort products by pick_frequency (highest first)
    # WHY? High-frequency items should go near the exit = less travel time
    df = df.sort_values("pick_frequency", ascending=False).reset_index(drop=True)

    return df


def load_warehouse(filepath="data/warehouse.csv"):
    """
    Load warehouse slot data from a CSV file.

    Each slot is a physical location in the warehouse.
    Slots closer to the exit (lower distance_from_exit) are more valuable.
    """

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Warehouse file not found at: {filepath}")

    df = pd.read_csv(filepath)

    required_columns = ["slot_id", "zone", "row", "column", "capacity_kg", "distance_from_exit"]
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Missing required column in warehouse.csv: {col}")

    # Sort slots by distance_from_exit (closest first)
    # WHY? We assign best slots to most-picked products
    df = df.sort_values("distance_from_exit", ascending=True).reset_index(drop=True)

    return df


def get_summary_stats(products_df, warehouse_df):
    """
    Calculate summary statistics for the dashboard.
    Returns a dictionary with key numbers.
    """

    total_product_weight = products_df["weight_kg"].sum()
    total_capacity = warehouse_df["capacity_kg"].sum()
    avg_frequency = products_df["pick_frequency"].mean()
    num_zones = warehouse_df["zone"].nunique()  # nunique() = count of unique values

    return {
        "total_products": len(products_df),
        "total_slots": len(warehouse_df),
        "total_product_weight_kg": round(total_product_weight, 2),
        "total_capacity_kg": round(total_capacity, 2),
        "avg_pick_frequency": round(avg_frequency, 1),
        "num_zones": num_zones,
        "capacity_utilization_pct": round((total_product_weight / total_capacity) * 100, 1)
    }


def add_product(products_df, product_id, name, weight, frequency, category):
    """
    Add a new product row to the existing DataFrame and return the updated one.
    """

    # Create new row as a dictionary, wrap in list so pd.DataFrame makes 1 row
    new_row = pd.DataFrame([{
        "product_id": product_id,
        "product_name": name,
        "weight_kg": weight,
        "pick_frequency": frequency,
        "category": category
    }])

    # pd.concat() stacks two DataFrames together (like adding rows)
    # ignore_index=True resets row numbers cleanly
    updated_df = pd.concat([products_df, new_row], ignore_index=True)

    # Re-sort so high-frequency items stay at top
    updated_df = updated_df.sort_values("pick_frequency", ascending=False).reset_index(drop=True)

    return updated_df


def save_products(products_df, filepath="data/products.csv"):
    """Save the updated products DataFrame back to CSV."""
    # index=False prevents an extra index column being written to the file
    products_df.to_csv(filepath, index=False)
    return True