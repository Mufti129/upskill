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
    
    with st.expander("Data Preview - Before Cleaning"):
        tab1, tab2, tab3 = st.tabs(["orders", "customers", "catalog"])
        with tab1:
            st.subheader("orders - Raw")
            st.dataframe(orders.head(100))
            st.write("Shape:", orders.shape)
            st.write("Missing Values:")
            st.write(orders.isna().sum())
        
        with tab2:
            st.subheader("customers - Raw")
            st.dataframe(customers.head(100))
            st.write("Shape:", customers.shape)
            st.write("Missing Values:")
            st.write(customers.isna().sum())
        
        with tab3:
            st.subheader("catalog - Raw")
            st.dataframe(catalog.head(100))
            st.write("Shape:", catalog.shape)
            st.write("Missing Values:")
            st.write(catalog.isna().sum())
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
     # ========= FIX REVENUE =========
    orders["total_revenue"] = orders["qty"] * orders["price_per_pax"]
    # ========= REMOVE DUPLICATE =========
    orders = orders.dropna(subset=["order_date"])
    orders = orders.drop_duplicates(subset="order_id")
    catalog = catalog.drop_duplicates(subset="training_id")
    customers = customers.drop_duplicates(subset="customer_id")
    # ========= STANDARDIZE TEXT =========
    orders["training_name"] = (orders["training_name"].str.strip().str.lower().str.title())
    catalog["training_name"] = (catalog["training_name"].str.strip().str.lower().str.title())
    orders["status"] = orders["status"].str.lower()
    
    # ========= FIX REVENUE =========
    #orders["total_revenue"] = orders["qty"] * orders["price_per_pax"]
    # ========= PREVIEW AFTER CLEANING =========
    with st.expander("Data Preview - After Cleaning"):
        tab1c, tab2c, tab3c = st.tabs(["Orders Clean", "Customers Clean", "Catalog Clean"])
        with tab1c:
            st.subheader("Orders - Cleaned")
            st.dataframe(orders.head(100))
            st.write("Shape:", orders.shape)
            st.write("Missing Values:")
            st.write(orders.isna().sum())
        with tab2c:
            st.subheader("Customers - Cleaned")
            st.dataframe(customers.head(100))
            st.write("Shape:", customers.shape)
            st.write("Missing Values:")
            st.write(customers.isna().sum())
        with tab3c:
            st.subheader("Catalog - Cleaned")
            st.dataframe(catalog.head(100))
            st.write("Shape:", catalog.shape)
            st.write("Missing Values:")
            st.write(catalog.isna().sum())
   
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
#Priveiw after Merge#
with st.expander("Data Preview - After Merge"):
    st.subheader("Merged Dataset Preview")
    st.dataframe(df.head(100))
    st.write("Shape:", df.shape)
    st.write("Missing Values:")
    st.write(df.isna().sum())
    st.write("Columns:")
    st.write(list(df.columns))
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
#completed_only = st.sidebar.checkbox("Completed Only", value=True)

filtered_df = df[(df["year"] == selected_year) & (df["city"].isin(selected_city)) ]

#if completed_only:
 #   filtered_df = filtered_df[
  #      filtered_df["Status"].str.lower() == "completed"
   # ]
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
min_date = filtered_df["order_date"].min()
max_date = filtered_df["order_date"].max()

st.caption(f"Periode Analisis: {min_date.date()} sampai {max_date.date()}")
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
# CLIENT DEPENDENCY
# ======================================================
# ======================================================
# CLIENT DEPENDENCY & RISK ANALYSIS
# ======================================================

st.markdown('<div class="section-title">Client Dependency & Risk Analysis</div>', unsafe_allow_html=True)

# ======================
# AGGREGATION
# ======================
client_rev = (
    filtered_df.groupby("company_name")["total_revenue"]
    .sum()
    .sort_values(ascending=False)
)

total_revenue_all = client_rev.sum()

# ======================
# TOP 1 & TOP 3 SHARE
# ======================
top1_share = (client_rev.iloc[0] / total_revenue_all) * 100
top3_share = (client_rev.iloc[:3].sum() / total_revenue_all) * 100

col1, col2 = st.columns(2)
col1.metric("Top 1 Client Contribution %", f"{top1_share:.2f}%")
col2.metric("Top 3 Client Contribution %", f"{top3_share:.2f}%")

# ======================
# RISK CLASSIFICATION (RULE OF THUMB)
# ======================

if top1_share > 60:
    risk_level = "🔴 EXTREME RISK - Single Client Dependency"
elif top1_share > 40:
    risk_level = "🟠 HIGH RISK - Revenue Concentrated"
elif top1_share > 20:
    risk_level = "🟡 MODERATE - Monitor Diversification"
else:
    risk_level = "🟢 HEALTHY - Diversified Revenue"

st.caption(f"Risk Assessment: {risk_level}")

# ======================
# TOP 5 CLIENT TABLE
# ======================
top_clients = client_rev.head(5).reset_index()
top_clients.columns = ["Company Name", "Total Revenue"]
top_clients["Contribution %"] = (
    top_clients["Total Revenue"] / total_revenue_all
) * 100

st.subheader("Top 5 Clients by Revenue")
st.dataframe(top_clients)

# ======================
# CLIENT TIER SEGMENTATION
# ======================
client_df = client_rev.reset_index()
client_df.columns = ["Company Name", "Total Revenue"]

client_df["Contribution %"] = (
    client_df["Total Revenue"] / total_revenue_all
) * 100

client_df["Cumulative %"] = client_df["Contribution %"].cumsum()

def assign_tier(cum_pct):
    if cum_pct <= 70:
        return "Tier A"
    elif cum_pct <= 90:
        return "Tier B"
    else:
        return "Tier C"

client_df["Tier"] = client_df["Cumulative %"].apply(assign_tier)

st.subheader("Client Tier Distribution")
st.dataframe(client_df.head(10))

# ======================
# UPSell SIGNAL (Mid Tier Candidates)
# ======================
upsell_candidates = client_df[
    client_df["Tier"] == "Tier B"
].head(5)

st.subheader("Upsell Potential Clients (Tier B)")
st.dataframe(upsell_candidates)

# ======================
# STRATEGIC NOTE
# ======================
if top3_share > 75:
    st.warning("Revenue terlalu terpusat pada 3 klien teratas. Perlu strategi diversifikasi.")
elif top3_share > 60:
    st.info("Konsentrasi cukup tinggi. Fokus akuisisi klien baru.")
else:
    st.success("Struktur revenue relatif stabil dan terdiversifikasi.")

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

# ======================================================
# AUTO EXECUTIVE INSIGHT ENGINE
# ======================================================

# ======================================================
# AUTO EXECUTIVE INSIGHT ENGINE
# ======================================================

st.markdown('<div class="section-title">📌 Automated Executive Insights</div>', unsafe_allow_html=True)

# ======================================================
# 1️⃣ TOP TRAINING 2024
# ======================================================

top_training = (
    filtered_df.groupby("training_name")["total_revenue"]
    .sum()
    .sort_values(ascending=False)
)

if not top_training.empty:
    best_training_name = top_training.index[0]
    best_training_value = top_training.iloc[0]

    st.markdown("### 1️⃣ Training dengan Revenue Terbesar")
    st.write(
        f"Training dengan revenue terbesar sepanjang {selected_year} adalah "
        f"**{best_training_name}** dengan total revenue sebesar "
        f"Rp {best_training_value:,.0f}. "
        "Training ini menjadi kontributor utama dalam struktur pendapatan tahunan."
    )

# ======================================================
# 2️⃣ KATEGORI PALING DIMINATI
# ======================================================

if "category" in filtered_df.columns:

    top_category = (
        filtered_df.groupby("category")["qty"]
        .sum()
        .sort_values(ascending=False)
    )

    if not top_category.empty:
        best_category = top_category.index[0]
        best_category_value = top_category.iloc[0]

        st.markdown("### 2️⃣ Kategori Paling Diminati")
        st.write(
            f"Kategori training yang paling diminati adalah **{best_category}**, "
            f"dengan total peserta sebanyak {int(best_category_value)} orang. "
            "Hal ini menunjukkan demand pasar yang kuat pada kategori tersebut."
        )

# ======================================================
# 3️⃣ TREN REVENUE BULANAN
# ======================================================

st.markdown("### 3️⃣ Pola Tren Revenue Bulanan")

if len(monthly) > 1:
    if latest_growth > 10:
        trend_comment = "mengalami akselerasi pertumbuhan yang kuat."
    elif latest_growth > 0:
        trend_comment = "mengalami pertumbuhan moderat."
    else:
        trend_comment = "mengalami penurunan dan perlu evaluasi strategi penjualan."

    st.write(
        f"Secara tren, revenue bulanan {trend_comment} "
        f"Pertumbuhan bulan terakhir tercatat sebesar {latest_growth:.2f}% dibanding bulan sebelumnya."
    )

# ======================================================
# 4️⃣ KOTA KONTRIBUTOR TERBESAR
# ======================================================

city_contribution = (
    filtered_df.groupby("city")["total_revenue"]
    .sum()
    .sort_values(ascending=False)
)

if not city_contribution.empty:
    top_city = city_contribution.index[0]
    top_city_value = city_contribution.iloc[0]

    st.markdown("### 4️⃣ Kota dengan Kontribusi Revenue Tertinggi")
    st.write(
        f"Kota dengan kontribusi revenue terbesar adalah **{top_city}**, "
        f"dengan total revenue sebesar Rp {top_city_value:,.0f}. "
        "Wilayah ini berperan signifikan terhadap performa bisnis keseluruhan."
    )

# ======================================================
# 5️⃣ CLIENT UPSELL ANALYSIS
# ======================================================

st.markdown("### 5️⃣ Analisis Potensi Upsell Klien")

client_analysis = (
    filtered_df.groupby("company_name")
    .agg(
        total_revenue=("total_revenue","sum"),
        total_orders=("order_id","nunique"),
        total_participants=("qty","sum")
    )
    .reset_index()
)

median_revenue = client_analysis["total_revenue"].median()

upsell_clients = client_analysis[
    (client_analysis["total_revenue"] > median_revenue) &
    (client_analysis["total_orders"] <= 2)
].sort_values(by="total_revenue", ascending=False)

if not upsell_clients.empty:

    st.write(
        "Berikut adalah klien dengan potensi upsell tinggi, "
        "ditinjau dari revenue besar namun frekuensi transaksi masih rendah:"
    )

    st.dataframe(upsell_clients.head(5), use_container_width=True)

else:
    st.write("Tidak ditemukan klien dengan pola revenue tinggi namun frekuensi rendah.")

# ======================================================
# 6️⃣ PRODUCT / TRAINING UPSELL POTENTIAL
# ======================================================

#st.markdown("### 6️⃣ Training dengan Potensi Upsell")

# ======================================================
# CLIENT UPSELL POTENTIAL (IMPROVED LOGIC)
# ======================================================

st.markdown("### 6️⃣ Klien Berpotensi Upsell")

client_analysis = (
    filtered_df.groupby("company_name")
    .agg(
        total_revenue=("total_revenue","sum"),
        total_orders=("order_id","nunique"),
        total_participants=("qty","sum"),
        training_variety=("training_name","nunique")
    )
    .reset_index()
)

# Threshold logic
revenue_threshold = client_analysis["total_revenue"].quantile(0.6)
order_threshold = client_analysis["total_orders"].median()

upsell_clients = client_analysis[
    (client_analysis["total_revenue"] >= revenue_threshold) &
    (
        (client_analysis["total_orders"] <= order_threshold) |
        (client_analysis["training_variety"] <= 2)
    )
].sort_values(by="total_revenue", ascending=False)

if not upsell_clients.empty:

    st.write(
        "Klien berikut memiliki revenue kuat namun penetrasi produk masih terbatas. "
        "Strategi upsell dapat difokuskan pada penawaran paket lanjutan, kontrak tahunan, "
        "atau ekspansi ke kategori training lain."
    )

    st.dataframe(upsell_clients.head(5), use_container_width=True)

else:
    st.write("Tidak ditemukan klien dengan karakteristik upsell yang signifikan.")

# ======================================================
# TRAINING UPSELL POTENTIAL
# ======================================================

st.markdown("### 🎯 Training Berpotensi Upsell")

training_analysis = (
    filtered_df.groupby("training_name")
    .agg(
        total_revenue=("total_revenue","sum"),
        total_orders=("order_id","nunique"),
        total_participants=("qty","sum")
    )
    .reset_index()
)

rev_threshold = training_analysis["total_revenue"].quantile(0.6)
participant_threshold = training_analysis["total_participants"].median()

upsell_training = training_analysis[
    (training_analysis["total_revenue"] >= rev_threshold) &
    (training_analysis["total_orders"] <= training_analysis["total_orders"].median()) &
    (training_analysis["total_participants"] >= participant_threshold)
].sort_values(by="total_revenue", ascending=False)

if not upsell_training.empty:

    st.write(
        "Training berikut memiliki demand dan revenue kuat namun frekuensi transaksi relatif rendah. "
        "Potensi upsell dapat dilakukan melalui paket corporate, bundling lanjutan, atau retargeting klien existing."
    )

    st.dataframe(upsell_training.head(5), use_container_width=True)

else:
    st.write("Tidak ditemukan training dengan peluang upsell signifikan.")

st.markdown("---")
st.markdown(
    "<center><small>Executive Dashboard by Mukhammad Rekza Mufti• Auto Updated from Google Sheets • Powered by Streamlit</small></center>",
    unsafe_allow_html=True
)
