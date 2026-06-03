import os
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import folium
from folium.plugins import HeatMap, MarkerCluster
import streamlit as st
from streamlit_folium import st_folium

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Boston Crime Dashboard",
    page_icon=":police_car:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 1.6rem !important; }
</style>
""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SUPP_FILES = [
    "tmp6w6ts2d7.csv",
    "tmpkd_w64k_.csv",
    "tmpfap3hfze.csv",
    "tmpdfeo3qy2.csv",
    "tmpcyl1hw5w.csv",
]

MONTH_LABELS = ["Jan","Feb","Mar","Apr","May","Jun",
                "Jul","Aug","Sep","Oct","Nov","Dec"]
DAY_ORDER = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
BOSTON_CENTER = [42.318, -71.083]

# ── Data loading ───────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Loading crime data...")
def load_data():
    def _load(path):
        df = pd.read_csv(path, encoding="latin-1", low_memory=False)
        df["OCCURRED_ON_DATE"] = (
            pd.to_datetime(df["OCCURRED_ON_DATE"], errors="coerce", utc=True)
              .dt.tz_localize(None)
        )
        return df

    parts = [_load(os.path.join(BASE_DIR, "crime.csv"))]
    for f in SUPP_FILES:
        parts.append(_load(os.path.join(BASE_DIR, f)))

    df = pd.concat(parts, ignore_index=True)
    df["YEAR"]        = df["OCCURRED_ON_DATE"].dt.year
    df["MONTH"]       = df["OCCURRED_ON_DATE"].dt.month
    df["DAY_OF_WEEK"] = df["OCCURRED_ON_DATE"].dt.day_name()
    df["HOUR"]        = df["OCCURRED_ON_DATE"].dt.hour

    df.dropna(subset=["OCCURRED_ON_DATE"], inplace=True)
    df = df[df["YEAR"] >= 2015]
    df.drop_duplicates(
        subset=["INCIDENT_NUMBER", "OFFENSE_CODE", "OCCURRED_ON_DATE"],
        inplace=True
    )

    codes = pd.read_csv(
        os.path.join(BASE_DIR, "offense_codes.csv"), encoding="latin-1"
    )
    codes.columns = codes.columns.str.strip()
    codes["NAME"] = codes["NAME"].str.strip().str.title()
    codes.drop_duplicates(subset="CODE", keep="first", inplace=True)
    df = df.merge(
        codes.rename(columns={"CODE": "OFFENSE_CODE", "NAME": "OFFENSE_NAME"}),
        on="OFFENSE_CODE", how="left"
    )
    df["OFFENSE_CODE_GROUP"] = df["OFFENSE_CODE_GROUP"].fillna(df["OFFENSE_NAME"])
    df["SHOOTING"] = (
        df["SHOOTING"].fillna("N")
          .map(lambda x: 1 if str(x).upper() in ("Y", "1") else 0)
    )
    df["Lat"]  = pd.to_numeric(df["Lat"],  errors="coerce")
    df["Long"] = pd.to_numeric(df["Long"], errors="coerce")
    return df


df_all = load_data()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Boston Crime")
    st.divider()

    year_min = int(df_all["YEAR"].min())
    year_max = int(df_all["YEAR"].max())
    year_range = st.slider(
        "Year range", year_min, year_max, (2016, 2025), step=1
    )

    all_districts = sorted(df_all["DISTRICT"].dropna().unique().tolist())
    selected_districts = st.multiselect(
        "Districts", all_districts, default=all_districts
    )

    top_crime_list = (
        ["All"]
        + df_all["OFFENSE_CODE_GROUP"].value_counts().head(25).index.tolist()
    )
    selected_crime = st.selectbox("Crime type", top_crime_list)

    map_mode = st.radio(
        "Map layer",
        ["Crime Heatmap", "Shooting Markers", "Both"],
        index=2,
    )

    st.divider()
    st.caption("Boston Police Dept\nJune 2015 - April 2026")

# ── Filter ─────────────────────────────────────────────────────────────────────
active_districts = selected_districts if selected_districts else all_districts
df = df_all[
    df_all["YEAR"].between(*year_range)
    & df_all["DISTRICT"].isin(active_districts)
]
if selected_crime != "All":
    df = df[df["OFFENSE_CODE_GROUP"] == selected_crime]

# ── Helper ─────────────────────────────────────────────────────────────────────
def clean_ax(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"{x:,.0f}")
    )

# ══════════════════════════════════════════════════════════════════════════════
# KPI ROW
# ══════════════════════════════════════════════════════════════════════════════
st.title("Boston Crime Dashboard")
st.caption(
    f"Showing **{len(df):,}** records | "
    f"{year_range[0]}-{year_range[1]} | "
    + (
        "All districts"
        if len(selected_districts) == len(all_districts)
        else ", ".join(selected_districts)
    )
)

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Records", f"{len(df):,}")

shoot_n = int(df["SHOOTING"].sum())
shoot_pct = df["SHOOTING"].mean() * 100 if len(df) > 0 else 0.0
k2.metric("Shootings", f"{shoot_n:,}", f"{shoot_pct:.2f}%")

top_crime = (
    df["OFFENSE_CODE_GROUP"].value_counts().idxmax() if len(df) > 0 else "--"
)
k3.metric("Top Offense", top_crime)

busiest_d = (
    df.groupby("DISTRICT").size().idxmax() if len(df) > 0 else "--"
)
k4.metric("Busiest District", busiest_d)

peak_hr = int(df.groupby("HOUR").size().idxmax()) if len(df) > 0 else 0
k5.metric("Peak Hour", f"{peak_hr:02d}:00")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# ROW 1 -- Folium map  +  Top-15 crimes
# ══════════════════════════════════════════════════════════════════════════════
map_col, bar_col = st.columns([3, 2], gap="large")

with map_col:
    st.subheader("Geographic Distribution")

    geo = df.dropna(subset=["Lat", "Long"])
    geo = geo[
        geo["Lat"].between(42.2, 42.4)
        & geo["Long"].between(-71.2, -70.9)
    ]

    m = folium.Map(
        location=BOSTON_CENTER,
        zoom_start=12,
        tiles="CartoDB positron",
        prefer_canvas=True,
    )

    if map_mode in ("Crime Heatmap", "Both") and len(geo) > 0:
        sample_n = min(40_000, len(geo))
        heat_data = (
            geo.sample(sample_n, random_state=42)[["Lat", "Long"]]
               .values.tolist()
        )
        HeatMap(
            heat_data,
            name="Crime density",
            radius=10,
            blur=12,
            min_opacity=0.25,
            max_zoom=15,
        ).add_to(m)

    if map_mode in ("Shooting Markers", "Both"):
        shootings_geo = geo[geo["SHOOTING"] == 1]
        if len(shootings_geo) > 0:
            shoot_layer = folium.FeatureGroup(
                name="Shooting incidents", show=True
            )
            cluster = MarkerCluster(
                options={"maxClusterRadius": 30, "disableClusteringAtZoom": 15}
            ).add_to(shoot_layer)
            for _, row in shootings_geo.head(1500).iterrows():
                date_str = (
                    row["OCCURRED_ON_DATE"].strftime("%Y-%m-%d %H:%M")
                    if pd.notna(row["OCCURRED_ON_DATE"]) else "unknown"
                )
                folium.CircleMarker(
                    location=[row["Lat"], row["Long"]],
                    radius=5,
                    color="#c0392b",
                    fill=True,
                    fill_color="#e74c3c",
                    fill_opacity=0.75,
                    popup=folium.Popup(
                        f"<b>{row['OFFENSE_CODE_GROUP']}</b><br>"
                        f"District: {row['DISTRICT']}<br>"
                        f"Date: {date_str}",
                        max_width=220,
                    ),
                    tooltip=str(row["DISTRICT"]),
                ).add_to(cluster)
            shoot_layer.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    st_folium(m, width="100%", height=480, returned_objects=[])

with bar_col:
    st.subheader("Top 15 Offense Groups")
    if len(df) > 0:
        top15 = df["OFFENSE_CODE_GROUP"].value_counts().head(15)
        fig, ax = plt.subplots(figsize=(5, 6.2))
        palette = plt.cm.Blues_r(np.linspace(0.25, 0.85, 15))
        ax.barh(
            top15.index[::-1], top15.values[::-1],
            color=palette, height=0.7
        )
        for i, v in enumerate(top15.values[::-1]):
            ax.text(
                v + top15.values.max() * 0.01, i,
                f"{v:,}", va="center", fontsize=7.5
            )
        ax.set_xlabel("Records")
        clean_ax(ax)
        ax.set_xlim(0, top15.values.max() * 1.18)
        plt.tight_layout()
        st.pyplot(fig, use_container_width=True)
        plt.close()

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# ROW 2 -- Hour / Day / Month
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("Temporal Patterns")
c1, c2, c3 = st.columns(3, gap="medium")

with c1:
    st.caption("**By Hour of Day**")
    hourly = df.groupby("HOUR").size().reset_index(name="Count")
    fig, ax = plt.subplots(figsize=(4.5, 3))
    ax.plot(hourly["HOUR"], hourly["Count"],
            marker="o", ms=4, color="#2980b9", linewidth=2)
    ax.fill_between(hourly["HOUR"], hourly["Count"],
                    alpha=0.12, color="#2980b9")
    ax.set_xticks(range(0, 24, 3))
    ax.set_xlabel("Hour"); ax.set_ylabel("Records")
    clean_ax(ax)
    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close()

with c2:
    st.caption("**By Day of Week**")
    weekly = df.groupby("DAY_OF_WEEK").size().reindex(DAY_ORDER).fillna(0)
    fig, ax = plt.subplots(figsize=(4.5, 3))
    colors = [
        "#e74c3c" if d in ("Saturday", "Sunday") else "#2980b9"
        for d in DAY_ORDER
    ]
    ax.bar(range(7), weekly.values, color=colors, width=0.6)
    ax.set_xticks(range(7))
    ax.set_xticklabels(
        ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"], fontsize=8
    )
    ax.set_ylabel("Records")
    clean_ax(ax)
    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close()

with c3:
    st.caption("**By Month of Year**")
    monthly = df.groupby("MONTH").size().reset_index(name="Count")
    fig, ax = plt.subplots(figsize=(4.5, 3))
    ax.bar(
        monthly["MONTH"], monthly["Count"],
        color=sns.color_palette("RdYlGn_r", 12), width=0.7
    )
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(MONTH_LABELS, fontsize=7.5, rotation=30)
    ax.set_ylabel("Records")
    clean_ax(ax)
    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close()

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# ROW 3 -- Annual trend  +  Hour x Day heatmap
# ══════════════════════════════════════════════════════════════════════════════
a1, a2 = st.columns([1, 2], gap="large")

with a1:
    st.subheader("Annual Trend")
    yearly = df.groupby("YEAR").size().reset_index(name="Count")
    partial_years = {int(df_all["YEAR"].min()), int(df_all["YEAR"].max())}
    bar_colors = [
        "#95a5a6" if int(y) in partial_years else "#2980b9"
        for y in yearly["YEAR"]
    ]
    fig, ax = plt.subplots(figsize=(4.5, 3.8))
    ax.bar(
        yearly["YEAR"], yearly["Count"],
        color=bar_colors, edgecolor="white", width=0.65
    )
    ax.bar_label(
        ax.containers[0],
        labels=[f"{v:,}" for v in yearly["Count"]],
        padding=3, fontsize=6.5
    )
    ax.set_xticks(yearly["YEAR"])
    plt.xticks(rotation=45, fontsize=7.5)
    ax.set_ylabel("Records")
    ax.set_title("(grey = partial year)", fontsize=8, color="grey")
    clean_ax(ax)
    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close()

with a2:
    st.subheader("Crime Intensity: Hour x Day")
    hour_day = (
        df.groupby(["DAY_OF_WEEK", "HOUR"])
          .size()
          .unstack(fill_value=0)
          .reindex(DAY_ORDER)
    )
    fig, ax = plt.subplots(figsize=(9.5, 3.5))
    sns.heatmap(
        hour_day, cmap="YlOrRd", ax=ax,
        linewidths=0.3, linecolor="#cccccc",
        cbar_kws={"label": "Records", "shrink": 0.8},
    )
    ax.set_xlabel("Hour of Day"); ax.set_ylabel("")
    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close()

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# ROW 4 -- Month x Year heatmap  +  District bar
# ══════════════════════════════════════════════════════════════════════════════
h1, h2 = st.columns([3, 2], gap="large")

with h1:
    st.subheader("Monthly Counts per Year (2016-2025)")
    df_full = df[df["YEAR"].between(2016, 2025)]
    if len(df_full) > 0:
        pivot = (
            df_full.pivot_table(
                index="MONTH", columns="YEAR",
                values="INCIDENT_NUMBER", aggfunc="count"
            )
            .fillna(0)
            .astype(int)
        )
        pivot.index = MONTH_LABELS
        fig, ax = plt.subplots(figsize=(9, 4))
        sns.heatmap(
            pivot, cmap="YlOrRd", annot=True, fmt="d",
            linewidths=0.3, ax=ax,
            cbar_kws={"label": "Records", "shrink": 0.6},
            annot_kws={"size": 7},
        )
        ax.set_xlabel("Year"); ax.set_ylabel("")
        plt.tight_layout()
        st.pyplot(fig, use_container_width=True)
        plt.close()

with h2:
    st.subheader("Crimes by District")
    dist_counts = (
        df.groupby("DISTRICT").size()
          .sort_values(ascending=True)
          .dropna()
    )
    if len(dist_counts) > 0:
        fig, ax = plt.subplots(
            figsize=(5, max(3, len(dist_counts) * 0.4))
        )
        palette = plt.cm.coolwarm_r(
            np.linspace(0.1, 0.9, len(dist_counts))
        )
        ax.barh(
            dist_counts.index, dist_counts.values,
            color=palette, height=0.65
        )
        for i, v in enumerate(dist_counts.values):
            ax.text(
                v + dist_counts.values.max() * 0.01, i,
                f"{v:,}", va="center", fontsize=7.5
            )
        ax.set_xlabel("Records")
        ax.set_xlim(0, dist_counts.values.max() * 1.18)
        clean_ax(ax)
        plt.tight_layout()
        st.pyplot(fig, use_container_width=True)
        plt.close()

st.caption(
    "Data: Boston Police Department | "
    "Crime Incident Reports | Source: Analyze Boston"
)
