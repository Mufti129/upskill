import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide", page_title="Executive Training Dashboard")
st.markdown("""
<style>
.big-font {
    font-size:18px !important;
    font-weight:600;
}
.section-title {
    font-size:24px;
    font-weight:700;
    margin-top:30px;
    margin-bottom:10px;
}
.card {
    padding:15px;
    border-radius:12px;
    background-color:#f9fafc;
    box-shadow:0 2px 6px rgba(0,0,0,0.05);
}
hr {
    margin-top:25px;
    margin-bottom:25px;
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


def load_data():
    # Sheet 1 - Training Catalog
    catalog = load_sheet(
        "1Xddtt7aue58VnVyw6RFiw4yh8G4zvvbb2dCh_SEPTJU",
        "2047167713"
    )

    # Sheet 2 - Training Orders
    orders = load_sheet(
        "17HuwXzIDKs1mmLWebunXKXMf2_P1qqxbJEYGpiCMMiE",
        "1355483010"
    )

    # Sheet 3 - Customer
    customers = load_sheet(
        "10KMQRXGMNN4rUYZOydFEfj-DYcTbcBC-4ZVSIQfxsic",
        "1545802490"
    )

    # =========================
    # BASIC CLEANING
    # =========================
def clean_columns(df):
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )
    return df
    orders = clean_columns(orders)
    catalog = clean_columns(catalog)
    customers = clean_columns(customers)
def clean_strings(df):
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str).str.strip()
    return df
    orders = clean_strings(orders)
    catalog = clean_strings(catalog)
    customers = clean_strings(customers)
    #orders['order_date'] = pd.to_datetime(orders['order_date'], errors='coerce')
    #orders['qty'] = pd.to_numeric(orders['qty'], errors='coerce')
    #orders['total_revenue'] = pd.to_numeric(orders['total_revenue'], errors='coerce')

    # Convert numeric columns
    orders["qty"] = pd.to_numeric(orders["qty"], errors="coerce")
    orders["price_per_pax"] = pd.to_numeric(orders["price_per_pax"], errors="coerce")
    orders["total_revenue"] = pd.to_numeric(orders["total_revenue"], errors="coerce")
    
    catalog["price_per_pax"] = pd.to_numeric(catalog["price_per_pax"], errors="coerce")
    catalog["max_pax"] = pd.to_numeric(catalog["max_pax"], errors="coerce")
    catalog["duration_days"] = pd.to_numeric(catalog["duration_days"], errors="coerce")
    
    # Convert date columns samakan format tampilan (YYYY-MM-DD)
    # Convert ke datetime
    customers["contract_start"] = pd.to_datetime(customers["contract_start"],errors="coerce",dayfirst=True)
    customers["contract_start"] = customers["contract_start"].dt.date
    orders["order_date"] = pd.to_datetime(orders["order_date"],errors="coerce",dayfirst=True)
    orders["order_date"] = orders["order_date"].dt.date
    
    #orders = orders.dropna(subset=['order_date'])
    #takeout duplikat
    orders = orders.drop_duplicates(subset="order_id")
    catalog = catalog.drop_duplicates(subset="training_id")
    customers = customers.drop_duplicates(subset="company_name")
    orders["recalculated_revenue"] = orders["qty"] * orders["price_per_pax"]
    
    # Replace incorrect revenue
    orders["total_revenue"] = orders["recalculated_revenue"]

    # =========================
    # MERGE DATA
    # =========================

    df = orders.merge(
        catalog[['training_name','trainer','duration_days','max_pax']],
        on='training_name',
        how='left'
    )

    df = df.merge(
        customers[['customer_id','company_name','industry','city']],
        on='customer_id',
        how='left'
    )

    df['month'] = df['order_date'].dt.to_period('M').astype(str)
    df['year'] = df['order_date'].dt.year

    return df


df = load_data()

# ======================================================
# SIDEBAR FILTER
# ======================================================

st.sidebar.header("Filter")

#selected_year = st.sidebar.selectbox(
 #   "Year",
  #  sorted(df['year'].dropna().unique())
#)

selected_city = st.sidebar.multiselect(
    "City",
    df['city'].dropna().unique(),
    default=df['city'].dropna().unique()
)

filtered_df = df[
    (df['year'] == selected_year) &
    (df['city'].isin(selected_city))
]

# ======================================================
# EXECUTIVE KPI
# ======================================================

#st.title("Executive Training Dashboard")
st.markdown('<div class="section-title">Executive Training Performance Dashboard</div>', unsafe_allow_html=True)
st.markdown("Ringkasan performa revenue, konsentrasi bisnis, dan peluang ekspansi klien.")
col1, col2, col3, col4 = st.columns(4)

total_revenue = filtered_df['total_revenue'].sum()
total_orders = filtered_df['order_id'].nunique()
total_participants = filtered_df['qty'].sum()
avg_order_value = total_revenue / total_orders if total_orders > 0 else 0

col1.metric("Total Revenue", f"Rp {total_revenue:,.0f}")
col2.metric("Total Orders", total_orders)
col3.metric("Total Participants", int(total_participants))
col4.metric("Avg Order Value", f"Rp {avg_order_value:,.0f}")

st.markdown("---")
#st.markdown("## 📈 Strategic Insight")
st.markdown('<div class="section-title">📈 Strategic Insights</div>', unsafe_allow_html=True)
# =============================
# MOM GROWTH
# =============================

monthly = (
    filtered_df.groupby('month')['total_revenue']
    .sum()
    .sort_index()
)
monthly_growth = monthly.pct_change() * 100
latest_growth = monthly_growth.iloc[-1] if len(monthly_growth) > 1 else 0
colA, colB, colC = st.columns(3)
colA.metric(
    "Latest MoM Growth",
    f"{latest_growth:.2f}%",
)
colB.metric(
    "Best Month Revenue",
    f"Rp {monthly.max():,.0f}"
)
colC.metric(
    "Worst Month Revenue",
    f"Rp {monthly.min():,.0f}"
)
if latest_growth > 10:
    st.success(f"Revenue menunjukkan akselerasi kuat dengan pertumbuhan {latest_growth:.2f}% dibanding bulan sebelumnya. Momentum bisnis sedang ekspansif.")
elif latest_growth > 0:
    st.info(f"Revenue tumbuh {latest_growth:.2f}% dari bulan sebelumnya. Pertumbuhan ada, namun belum agresif.")
else:
    st.error(f"Revenue turun {abs(latest_growth):.2f}% dibanding bulan sebelumnya. Perlu investigasi penyebab penurunan.")

st.markdown("### Revenue Concentration (Pareto 80/20)")
training_rev = (
    filtered_df.groupby('training_name')['total_revenue']
    .sum()
    .sort_values(ascending=False)
)

pareto_df = training_rev.reset_index()
pareto_df['cumulative_%'] = (
    pareto_df['total_revenue'].cumsum() /
    pareto_df['total_revenue'].sum()
) * 100

top_80 = pareto_df[pareto_df['cumulative_%'] <= 80]

st.write(f"⚠ {len(top_80)} training menyumbang 80% revenue")
st.dataframe(top_80)
total_training = len(training_rev)
dominant_count = len(top_80)

concentration_ratio = dominant_count / total_training * 100

if concentration_ratio < 30:
    st.warning("Revenue sangat terkonsentrasi pada sedikit training. Risiko bisnis tinggi jika demand training utama turun.")
elif concentration_ratio < 50:
    st.info("Revenue cukup terdistribusi, namun masih ada ketergantungan pada beberapa training utama.")
else:
    st.success("Revenue relatif terdiversifikasi antar training. Risiko konsentrasi rendah.")

st.markdown("### Client Revenue Dependency")

client_rev = (
    filtered_df.groupby('company_name')['total_revenue']
    .sum()
    .sort_values(ascending=False)
)

top_client_share = (client_rev.iloc[0] / client_rev.sum()) * 100

st.metric("Top Client Contribution %", f"{top_client_share:.2f}%")
if top_client_share > 40:
    st.error("Bisnis sangat tergantung pada satu klien utama. Risiko kehilangan revenue besar jika klien tersebut churn.")
elif top_client_share > 25:
    st.warning("Terdapat ketergantungan cukup signifikan pada klien utama.")
else:
    st.success("Revenue relatif terdiversifikasi antar klien.")

st.markdown("### Pricing Power Insight")
avg_price = filtered_df.groupby('training_name')['price_per_pax'].mean()

highest_price_training = avg_price.idxmax()
lowest_price_training = avg_price.idxmin()

colX, colY = st.columns(2)

colX.metric("Highest Avg Price Training", highest_price_training)
colY.metric("Lowest Avg Price Training", lowest_price_training)
price_gap = avg_price.max() - avg_price.min()
if price_gap > 5_000_000:
    st.info("Terdapat gap harga signifikan antar training. Ada peluang repositioning atau bundling.")
else:
    st.write("Struktur harga relatif homogen antar training.")
st.markdown("### Advanced Upsell Scoring")

client_analysis = (
    filtered_df.groupby('company_name')
    .agg(
        total_revenue=('total_revenue','sum'),
        total_orders=('order_id','nunique'),
        total_participants=('qty','sum')
    )
    .reset_index()
)

client_analysis['upsell_score'] = (
    client_analysis['total_revenue'].rank(pct=True) * 0.5 +
    client_analysis['total_participants'].rank(pct=True) * 0.5
)

upsell_candidates = client_analysis.sort_values(
    by='upsell_score',
    ascending=False
).head(5)

st.dataframe(upsell_candidates)
st.markdown(
    "Klien dengan skor upsell tertinggi memiliki kombinasi revenue dan partisipasi besar. "
    "Strategi cross-sell atau kontrak jangka panjang dapat meningkatkan lifetime value."
)
# ======================================================
# 1️⃣ TRAINING REVENUE RANKING
# ======================================================

st.subheader("Revenue by Training")

training_rev = (
    filtered_df.groupby('training_name')['total_revenue']
    .sum()
    .reset_index()
    .sort_values(by='total_revenue', ascending=False)
)

fig1 = px.bar(
    training_rev,
    x='total_revenue',
    y='training_name',
    orientation='h',
    text_auto=True
)

st.plotly_chart(fig1, use_container_width=True)

# ======================================================
# 2️⃣ CATEGORY DEMAND
# ======================================================

st.subheader("Category Demand (Based on Participants)")

category_demand = (
    filtered_df.groupby('category')['qty']
    .sum()
    .reset_index()
    .sort_values(by='qty', ascending=False)
)

fig2 = px.bar(
    category_demand,
    x='category',
    y='qty',
    text_auto=True
)

st.plotly_chart(fig2, use_container_width=True)

# ======================================================
# 3️⃣ MONTHLY TREND
# ======================================================

st.subheader("Monthly Revenue Trend")

monthly_trend = (
    filtered_df.groupby('month')['total_revenue']
    .sum()
    .reset_index()
)

fig3 = px.line(
    monthly_trend,
    x='month',
    y='total_revenue',
    markers=True
)

st.plotly_chart(fig3, use_container_width=True)

# ======================================================
# 4️⃣ CITY CONTRIBUTION
# ======================================================

st.subheader("Revenue by City")

city_rev = (
    filtered_df.groupby('city')['total_revenue']
    .sum()
    .reset_index()
    .sort_values(by='total_revenue', ascending=False)
)

fig4 = px.bar(
    city_rev,
    x='city',
    y='total_revenue',
    text_auto=True
)

st.plotly_chart(fig4, use_container_width=True)

# ======================================================
# 5️⃣ CLIENT ANALYSIS
# ======================================================

st.subheader("Top Clients")

client_analysis = (
    filtered_df.groupby('company_name')
    .agg(
        total_revenue=('total_revenue','sum'),
        total_orders=('order_id','nunique')
    )
    .reset_index()
    .sort_values(by='total_revenue', ascending=False)
)

#st.dataframe(client_analysis.head(10))
st.dataframe(
    client_analysis.head(10),
    use_container_width=True
)
# Upsell Logic
st.subheader("Upsell Candidates")

median_revenue = client_analysis['total_revenue'].median()

upsell = client_analysis[
    (client_analysis['total_revenue'] > median_revenue) &
    (client_analysis['total_orders'] <= 2)
]

st.dataframe(upsell)

st.markdown("---")
st.markdown(
    "<center><small>Executive Dashboard by Mukhammad Rekza Mufti • Auto Updated from Google Sheets • Powered by Streamlit</small></center>",
    unsafe_allow_html=True
)
