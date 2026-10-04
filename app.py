# ============================================================
# app.py
# PURPOSE: Main Streamlit web app — ties all modules together
# WHAT YOU LEARN: Streamlit UI, session_state, modular code
# ============================================================

import streamlit as st
import pandas as pd
import os

# Import our own modules
from data_manager import load_products, load_warehouse, get_summary_stats, add_product, save_products
from optimizer import greedy_optimize, calculate_efficiency_gain, get_zone_summary, get_category_summary
from visualizer import (
    plot_warehouse_grid,
    plot_frequency_vs_distance,
    plot_zone_distribution,
    plot_travel_score_breakdown,
    plot_category_pie
)

# st.set_page_config() MUST be the very first Streamlit call
st.set_page_config(
    page_title="Warehouse Slot Optimizer",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject custom CSS for a polished look
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    [data-testid="metric-container"] {
        background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
        border: 1px solid #bae6fd;
        border-radius: 12px;
        padding: 16px;
    }

    .main-header {
        background: linear-gradient(135deg, #1e3a5f, #2563eb);
        color: white;
        padding: 24px 32px;
        border-radius: 16px;
        margin-bottom: 24px;
    }
    .main-header h1 { margin: 0; font-size: 28px; }
    .main-header p  { margin: 6px 0 0 0; opacity: 0.85; font-size: 14px; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# SESSION STATE
# Streamlit reruns the entire script on every interaction.
# session_state lets us persist data across those reruns.
# Think of it as a global variable store for the app session.
# ============================================================
def initialize_session_state():
    if "products_df" not in st.session_state:
        st.session_state.products_df = load_products()

    if "warehouse_df" not in st.session_state:
        st.session_state.warehouse_df = load_warehouse()

    if "assignments_df" not in st.session_state:
        st.session_state.assignments_df = pd.DataFrame()

    if "optimization_run" not in st.session_state:
        st.session_state.optimization_run = False


# ============================================================
# SIDEBAR — Left panel for navigation
# ============================================================
def render_sidebar():
    with st.sidebar:
        st.markdown("## 🏭 Warehouse Optimizer")
        st.markdown("---")

        page = st.radio(
            "Navigate",
            ["📊 Dashboard", "🗺️ Slot Map", "📦 Products", "⚙️ Settings"],
            label_visibility="collapsed"
        )

        st.markdown("---")

        if st.session_state.optimization_run:
            st.success(f"{len(st.session_state.assignments_df)} products assigned")
        else:
            st.info("Run optimizer to see results")

        st.markdown("---")
        st.caption("Built with Python + Streamlit")

    return page


# ============================================================
# PAGE: DASHBOARD
# ============================================================
def page_dashboard():
    st.markdown("""
    <div class="main-header">
        <h1>🏭 Warehouse Slot Optimizer</h1>
        <p>Assign products to warehouse slots to minimize picker travel distance</p>
    </div>
    """, unsafe_allow_html=True)

    col_btn, col_info = st.columns([1, 3])

    with col_btn:
        if st.button("🚀 Run Optimization", type="primary", use_container_width=True):
            with st.spinner("Optimizing slot assignments..."):
                assignments, score, unassigned = greedy_optimize(
                    st.session_state.products_df,
                    st.session_state.warehouse_df
                )
            st.session_state.assignments_df = assignments
            st.session_state.total_score = score
            st.session_state.unassigned = unassigned
            st.session_state.optimization_run = True
            st.success("✅ Optimization complete!")

    with col_info:
        if st.session_state.optimization_run and st.session_state.unassigned:
            st.warning(f"⚠️ {len(st.session_state.unassigned)} products couldn't be assigned: "
                      f"{', '.join(st.session_state.unassigned)}")

    # ── KPI Metrics ──────────────────────────────────────
    st.markdown("### 📈 Key Metrics")
    stats = get_summary_stats(st.session_state.products_df, st.session_state.warehouse_df)

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Total Products",     stats["total_products"])
    with col2: st.metric("Warehouse Slots",    stats["total_slots"])
    with col3: st.metric("Capacity Used",      f"{stats['capacity_utilization_pct']}%")
    with col4: st.metric("Avg Pick Frequency", f"{stats['avg_pick_frequency']}/day")

    if st.session_state.optimization_run and not st.session_state.assignments_df.empty:
        efficiency, worst, best = calculate_efficiency_gain(
            st.session_state.assignments_df,
            st.session_state.products_df,
            st.session_state.warehouse_df
        )

        col5, col6, col7, col8 = st.columns(4)
        with col5: st.metric("Travel Score (Optimized)",  f"{round(best, 0):.0f}")
        with col6: st.metric("Travel Score (Worst Case)", f"{round(worst, 0):.0f}")
        with col7: st.metric("Efficiency Gain",           f"{efficiency}%", delta=f"+{efficiency}%")
        with col8: st.metric("Products Assigned",         len(st.session_state.assignments_df))

    # ── Charts ───────────────────────────────────────────
    if st.session_state.optimization_run and not st.session_state.assignments_df.empty:
        st.markdown("### 📊 Analysis Charts")

        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            st.plotly_chart(plot_frequency_vs_distance(st.session_state.assignments_df), use_container_width=True)
        with chart_col2:
            st.plotly_chart(plot_zone_distribution(get_zone_summary(st.session_state.assignments_df)), use_container_width=True)

        chart_col3, chart_col4 = st.columns(2)
        with chart_col3:
            st.plotly_chart(plot_travel_score_breakdown(st.session_state.assignments_df), use_container_width=True)
        with chart_col4:
            st.plotly_chart(plot_category_pie(st.session_state.assignments_df), use_container_width=True)

        # ── Summary Tables ────────────────────────────────
        st.markdown("### 📋 Summary Tables")
        tab1, tab2 = st.tabs(["By Zone", "By Category"])

        with tab1:
            st.dataframe(get_zone_summary(st.session_state.assignments_df), use_container_width=True, hide_index=True)
        with tab2:
            st.dataframe(get_category_summary(st.session_state.assignments_df), use_container_width=True, hide_index=True)

    else:
        st.info("👆 Click **Run Optimization** to assign products to slots and see analysis.")


# ============================================================
# PAGE: SLOT MAP
# ============================================================
def page_slot_map():
    st.markdown("## 🗺️ Warehouse Slot Map")

    if not st.session_state.optimization_run:
        st.warning("Please run the optimizer first from the Dashboard.")
        return

    st.plotly_chart(
        plot_warehouse_grid(st.session_state.assignments_df, st.session_state.warehouse_df),
        use_container_width=True
    )

    col1, col2, col3 = st.columns(3)
    with col1: st.markdown("🟢 **Zone A** — Closest to exit")
    with col2: st.markdown("🟡 **Zone B** — Medium distance")
    with col3: st.markdown("🔴 **Zone C** — Furthest from exit")

    st.markdown("#### All Assignments")
    if not st.session_state.assignments_df.empty:
        display_cols = ["product_name", "slot_id", "zone", "row", "column",
                       "pick_frequency", "distance_from_exit", "travel_score"]
        st.dataframe(st.session_state.assignments_df[display_cols], use_container_width=True, hide_index=True)


# ============================================================
# PAGE: PRODUCTS
# ============================================================
def page_products():
    st.markdown("## 📦 Product Management")

    st.markdown("### Current Products")
    st.dataframe(st.session_state.products_df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### ➕ Add New Product")

    # st.form groups inputs and only submits when the button is clicked
    # Without a form, Streamlit reruns on every keystroke
    with st.form("add_product_form"):
        form_col1, form_col2 = st.columns(2)

        with form_col1:
            existing_ids = st.session_state.products_df["product_id"].tolist()
            max_id = max([int(pid[1:]) for pid in existing_ids if pid[1:].isdigit()], default=0)
            new_id = f"P{str(max_id + 1).zfill(3)}"  # zfill pads with zeros: P001, P012

            st.text_input("Product ID (auto)", value=new_id, disabled=True)
            product_name = st.text_input("Product Name *", placeholder="e.g. Wireless Speaker")
            category = st.selectbox("Category", ["Electronics", "Stationery", "Furniture", "Other"])

        with form_col2:
            weight = st.number_input("Weight (kg) *", min_value=0.1, max_value=100.0, value=1.0, step=0.1)
            frequency = st.slider("Daily Pick Frequency *", min_value=1, max_value=100, value=50)

        submitted = st.form_submit_button("Add Product", type="primary")

        if submitted:
            if not product_name:
                st.error("Product name is required!")
            else:
                updated_df = add_product(
                    st.session_state.products_df,
                    new_id, product_name, weight, frequency, category
                )
                st.session_state.products_df = updated_df
                save_products(updated_df)

                # Reset optimization since data changed
                st.session_state.optimization_run = False
                st.session_state.assignments_df = pd.DataFrame()

                st.success(f"✅ Added {product_name}. Re-run optimizer to update assignments.")
                st.rerun()  # Refresh the page to show updated table


# ============================================================
# PAGE: SETTINGS
# ============================================================
def page_settings():
    st.markdown("## ⚙️ Settings & Raw Data")

    tab1, tab2 = st.tabs(["📄 Products CSV", "🏗️ Warehouse CSV"])

    with tab1:
        st.dataframe(st.session_state.products_df, use_container_width=True)
        st.download_button(
            "⬇️ Download Products CSV",
            data=st.session_state.products_df.to_csv(index=False),
            file_name="products.csv",
            mime="text/csv"
        )

    with tab2:
        st.dataframe(st.session_state.warehouse_df, use_container_width=True)
        st.download_button(
            "⬇️ Download Warehouse CSV",
            data=st.session_state.warehouse_df.to_csv(index=False),
            file_name="warehouse.csv",
            mime="text/csv"
        )

    st.markdown("---")
    if st.button("🔄 Reset All Data to Defaults"):
        for key in ["products_df", "warehouse_df", "assignments_df", "optimization_run"]:
            if key in st.session_state:
                del st.session_state[key]
        st.success("Reset complete.")
        st.rerun()


# ============================================================
# MAIN ENTRY POINT
# This runs when you execute: streamlit run app.py
# ============================================================
def main():
    initialize_session_state()
    page = render_sidebar()

    if   page == "📊 Dashboard": page_dashboard()
    elif page == "🗺️ Slot Map":  page_slot_map()
    elif page == "📦 Products":  page_products()
    elif page == "⚙️ Settings":  page_settings()


# Only run main() when this file is executed directly
if __name__ == "__main__":
    main()