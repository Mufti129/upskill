import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(layout="wide", page_title="Executive Training Dashboard")

# ======================================================
# STYLE
# ======================================================
st.markdown("""
<style>
.section-title {
    font-size:24px;
    font-weight:700;
    margin-top:30px;
    margin-bottom:10px;
}
</style>
""", unsafe_allow_html=True)

# ======================================================
# LOAD GOOGLE SHEETS
# ======================================================

@st.cache_data(ttl=300)
def load_sheet(sheet_id, gid):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip().str.lower()
    return df


@st.cache_data(ttl=300)
def load_data():

    catalog = load_sheet(
        "1Xddtt7aue58VnVyw6RFiw4yh8G4zvvbb2dCh_SEPTJU",
        "2047167713"
    )

    orders = load_sheet(
        "17HuwXzIDKs1mmLWebunXKXMf2_P1qqxbJEYGpiCMMiE",
        "1355483010"
    )

    customers = load_sheet(
        "10KMQRXGMNN4rUYZOydFEfj-DYcTbcBC-4ZVSIQfxsic",
        "1545802490"
    )

    # ========= NUMERIC CLEANING =========
    for col in ["qty","price_per_pax","total_revenue"]:
        if col in orders.columns:
            orders[col] = pd.to_numeric(orders[col], errors="coerce")

    for col in ["price_per_pax","max_pax","duration_days"]:
        if col in catalog.columns:
            catalog[col] = pd.to_numeric(catalog[col], errors="coerce")

    # ========= DATE NORMALIZATION =========
    orders["order_date"] = pd.to_datetime(
        orders["order_date"],
        errors="coerce",
        dayfirst=True
    )

    orders = orders.dropna(subset=["order_date"])

    # ========= REMOVE DUPLICATE =========
    orders = orders.drop_duplicates(subset="order_id")
    catalog = catalog.drop_duplicates(subset="training_id")
    customers = customers.drop_duplicates(subset="customer_id")

    # ========= FIX REVENUE =========
    orders["total_revenue"] = orders["qty"] * orders["price_per_pax"]

    # ========= MERGE =========
    df = orders.merge(
        catalog,
        on="training_name",
        how="left"
    )

    df = df.merge(
        customers,
        on="customer_id",
        how="left"
    )

    # ========= TIME FEATURES =========
    df["month"] = df["order_date"].dt.to_period("M").astype(str)
    df["year"] = df["order_date"].dt.year
    df["quarter"] = df["order_date"].dt.to_period("Q").astype(str)

    return df


df = load_data()

# ======================================================
# DEFENSIVE CHECK
# ======================================================

if df.empty:
    st.error("Data kosong setelah cleaning.")
    st.stop()

df["year"] = pd.to_numeric(df["year"], errors="coerce")
year_list = sorted(df["year"].dropna().astype(int).unique())

st.sidebar.header("Filter")

selected_year = st.sidebar.selectbox("Year", year_list)

selected_city = st.sidebar.multiselect(
    "City",
    df["city"].dropna().unique(),
    default=df["city"].dropna().unique()
)

filtered_df = df[
    (df["year"] == selected_year) &
    (df["city"].isin(selected_city))
]

if filtered_df.empty:
    st.warning("Tidak ada data untuk filter yang dipilih.")
    st.stop()

# ======================================================
# EXECUTIVE KPI
# ======================================================

st.markdown('<div class="section-title">Executive Training Performance Dashboard</div>', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

total_revenue = filtered_df["total_revenue"].sum()
total_orders = filtered_df["order_id"].nunique()
total_participants = filtered_df["qty"].sum()
avg_order_value = total_revenue / total_orders if total_orders > 0 else 0

col1.metric("Total Revenue", f"Rp {total_revenue:,.0f}")
col2.metric("Total Orders", total_orders)
col3.metric("Total Participants", int(total_participants))
col4.metric("Avg Order Value", f"Rp {avg_order_value:,.0f}")

# Extra KPI
col5, col6 = st.columns(2)

revenue_per_participant = (
    total_revenue / total_participants
    if total_participants > 0 else 0
)

yearly = df.groupby("year")["total_revenue"].sum().sort_index()
yoy_growth = yearly.pct_change() * 100
current_yoy = yoy_growth.loc[selected_year] if selected_year in yoy_growth.index else 0

col5.metric("Revenue per Participant", f"Rp {revenue_per_participant:,.0f}")
col6.metric("YoY Growth", f"{current_yoy:.2f}%")

st.markdown("---")

# ======================================================
# STRATEGIC INSIGHT
# ======================================================

st.markdown('<div class="section-title">Strategic Insights</div>', unsafe_allow_html=True)

monthly = (
    filtered_df.groupby("month")["total_revenue"]
    .sum()
    .sort_index()
)

monthly_growth = monthly.pct_change() * 100
latest_growth = monthly_growth.iloc[-1] if len(monthly_growth) > 1 else 0

st.metric("Latest MoM Growth", f"{latest_growth:.2f}%")

# ======================================================
# PARETO ANALYSIS
# ======================================================

training_rev = (
    filtered_df.groupby("training_name")["total_revenue"]
    .sum()
    .sort_values(ascending=False)
)

pareto_df = training_rev.reset_index()
pareto_df["cumulative_%"] = (
    pareto_df["total_revenue"].cumsum() /
    pareto_df["total_revenue"].sum()
) * 100

top_80 = pareto_df[pareto_df["cumulative_%"] <= 80]

st.write(f"{len(top_80)} training menyumbang 80% revenue")
st.dataframe(top_80)

# ======================================================
# CLIENT DEPENDENCY
# ======================================================

client_rev = (
    filtered_df.groupby("company_name")["total_revenue"]
    .sum()
    .sort_values(ascending=False)
)

top_client_share = (client_rev.iloc[0] / client_rev.sum()) * 100
st.metric("Top Client Contribution %", f"{top_client_share:.2f}%")

# ======================================================
# BUSINESS RISK SCORE
# ======================================================

risk_score = 0

if latest_growth < 0:
    risk_score += 1
if top_client_share > 40:
    risk_score += 1
if len(top_80) / len(training_rev) < 0.3:
    risk_score += 1

st.markdown('<div class="section-title">Business Risk Level</div>', unsafe_allow_html=True)

if risk_score == 0:
    st.success("LOW RISK")
elif risk_score == 1:
    st.warning("MODERATE RISK")
else:
    st.error("HIGH RISK")

# ======================================================
# VISUALIZATION
# ======================================================

st.subheader("Revenue by Training")

training_plot = training_rev.reset_index()
fig1 = px.bar(
    training_plot,
    x="total_revenue",
    y="training_name",
    orientation="h"
)

st.plotly_chart(fig1, use_container_width=True)

st.subheader("Monthly Revenue Trend")

monthly_plot = monthly.reset_index()
fig2 = px.line(
    monthly_plot,
    x="month",
    y="total_revenue",
    markers=True
)

st.plotly_chart(fig2, use_container_width=True)

st.subheader("Revenue by City")

city_rev = (
    filtered_df.groupby("city")["total_revenue"]
    .sum()
    .reset_index()
    .sort_values(by="total_revenue", ascending=False)
)

fig3 = px.bar(
    city_rev,
    x="city",
    y="total_revenue"
)

st.plotly_chart(fig3, use_container_width=True)

st.markdown("---")
st.markdown(
    "<center><small>Executive Dashboard by Mukhammad Rekza Mufti• Auto Updated from Google Sheets • Powered by Streamlit</small></center>",
    unsafe_allow_html=True
)
