# Boston Crime Analysis (2015 – 2025)

> End-to-end analysis of Boston Police Department crime incident reports, covering
> **884,901 records** across 11 years.  Includes an exploratory Jupyter notebook
> and an interactive Streamlit dashboard with a live Folium heat map.

---

## Dataset

| File | Source | Period | Records |
|------|--------|--------|---------|
| `crime.csv` | [Kaggle – Boston Crime](https://www.kaggle.com/datasets/AnalyzeBoston/crimes-in-boston) | Jun 2015 – Sep 2018 | 319,073 |
| Annual supplements | [Analyze Boston](https://data.boston.gov/dataset/crime-incident-reports-august-2015-to-date-source-new-system) | 2019 – Apr 2026 | 565,864 |
| `offense_codes.csv` | Same Kaggle package | — | 576 codes |

> **Note:** Data files are not committed to this repo due to size.
> Download them from the links above and place all CSVs in the project root
> before running anything.

---

## Key Findings

### 1. What types of crimes are most common?
| Rank | Offense Group | Records |
|------|--------------|---------|
| 1 | Investigate Person | 44,512 |
| 2 | Vandalism | 40,618 |
| 3 | Motor Vehicle Accident Response | 39,657 |

- **UCR Part III** (minor offences) accounts for the largest share of all records.
- Shooting incidents: **6,358** total — just **0.72 %** of all records, but
  concentrated in districts **B2** (Roxbury) and **B3** (Mattapan).

### 2. Where do crimes occur?
- **Busiest district:** B2 (Roxbury) — consistently leads across all years.
- **Busiest street:** Washington St — appears most frequently across all crime types.
- Larceny and drug violations cluster in the downtown / Back Bay corridor;
  violent crimes concentrate in the southern districts (B2, B3, C11).

### 3. How does frequency change over time?

| Pattern | Observation |
|---------|-------------|
| **Hour of day** | Peak at **17:00 (5 PM)**; lowest around 4–5 AM |
| **Day of week** | **Friday** is busiest; Sunday is quietest |
| **Month of year** | July–August peak; February–March trough |
| **COVID-19 (2020)** | Clear dip in March–May 2020 during lockdown; full recovery by 2021 |
| **Long-run trend** | Volume stable 2016–2019; 2020 dip; 2021–2025 rebound to pre-COVID levels |

---

## Project Structure

```
.
+-- boston_crime_analysis.ipynb   # EDA notebook (11 sections)
+-- ml_forecasting.ipynb          # ML notebook: SARIMA vs LightGBM + SHAP
+-- dashboard.py                  # Streamlit + Folium interactive dashboard
+-- requirements.txt              # Python dependencies
+-- README.md
+-- .gitignore
```

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/e1ec/Boston-Crime.git
cd Boston-Crime

# 2. Place all CSV files in this directory (see Dataset section above)

# 3. Create virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt
```

### Run the EDA Notebook

```bash
jupyter lab boston_crime_analysis.ipynb
```

### Run the ML Forecasting Notebook

```bash
jupyter lab ml_forecasting.ipynb
```

Both notebooks are self-contained and produce all charts inline.

### Run the Streamlit Dashboard

```bash
streamlit run dashboard.py
```

Open `http://localhost:8501` in your browser.

---

## Dashboard Features

| Section | Description |
|---------|-------------|
| **KPI row** | Total records, shooting count/%, top offense, busiest district, peak hour — all update with filters |
| **Folium map** | Crime heat map (up to 40 k sampled points) + shooting marker cluster; toggle layers independently |
| **Top 15 offenses** | Horizontal bar chart |
| **Temporal panels** | Hour-of-day, day-of-week, month-of-year |
| **Annual trend** | Year-by-year bar chart (partial years greyed out) |
| **Hour x Day heatmap** | Seaborn heatmap showing joint time patterns |
| **Month x Year heatmap** | 2016–2025 grid, annotated with counts |
| **District comparison** | Horizontal bar sorted by volume |

**Sidebar filters** (all visuals update instantly):
- Year range slider
- District multi-select
- Crime type dropdown (top 25 groups)
- Map layer toggle: Crime Heatmap / Shooting Markers / Both

---

## Tech Stack

| Library | Version | Use |
|---------|---------|-----|
| pandas | >= 3.0 | Data loading, cleaning, aggregation |
| numpy | >= 2.4 | Numerical operations |
| matplotlib | >= 3.10 | Static charts |
| seaborn | >= 0.13 | Heatmaps, colour palettes |
| folium | >= 0.18 | Interactive Leaflet map |
| streamlit | >= 1.35 | Dashboard web framework |
| streamlit-folium | >= 0.22 | Embed Folium map in Streamlit |
| jupyterlab | >= 4.0 | Notebook runtime |
| scikit-learn | >= 1.4 | Metrics, preprocessing |
| lightgbm | >= 4.0 | Gradient boosting forecasting model |
| statsmodels | >= 0.14 | SARIMA time series baseline |
| shap | >= 0.45 | Model explainability |

---

## Data Notes

- Records from the 2023-2026 supplement use UTC-aware timestamps (`+00`); the
  code normalises these to tz-naive at load time so all files concatenate cleanly.
- ~36 rows (< 0.01 %) are dropped for missing `OCCURRED_ON_DATE`.
- Duplicate rows (same incident + offense code + timestamp) are removed;
  **884,901** unique records remain after deduplication.

---

## License

Data is published by the City of Boston under the
[Open Data Commons Attribution License](https://opendatacommons.org/licenses/by/1-0/).
Code in this repository is MIT licensed.
