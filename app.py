
import os
import glob
import pandas as pd
import gradio as gr
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# 1. LOAD NETFLIX DATASET
# ==========================================

csv_files = glob.glob("/content/*.csv")

netflix_files = [
    f for f in csv_files
    if "netflix" in os.path.basename(f).lower()
]

if netflix_files:
    DATA_PATH = netflix_files[0]
elif len(csv_files) == 1:
    DATA_PATH = csv_files[0]
else:
    raise FileNotFoundError(
        "Netflix CSV not found. Upload your Netflix dataset to Colab."
    )

df = pd.read_csv(DATA_PATH)

print("Netflix Dataset Loaded Successfully!")
print("File:", DATA_PATH)
print("Dataset Shape:", df.shape)

# ==========================================
# 2. DATA CLEANING
# ==========================================

df.columns = df.columns.str.strip()

required_columns = [
    "show_id", "type", "title", "director",
    "cast", "country", "date_added",
    "release_year", "rating", "duration",
    "listed_in", "description"
]

for col in required_columns:
    if col not in df.columns:
        df[col] = "Unknown"

text_columns = [
    "type", "title", "director", "cast",
    "country", "rating", "duration",
    "listed_in", "description"
]

for col in text_columns:
    df[col] = df[col].fillna("Unknown").astype(str)

df["release_year"] = pd.to_numeric(
    df["release_year"], errors="coerce"
)

df["date_added"] = pd.to_datetime(
    df["date_added"], errors="coerce"
)

# ==========================================
# 3. FILTER OPTIONS
# ==========================================

content_types = ["All"] + sorted(
    df["type"].unique().tolist()
)

countries = sorted(set(
    country.strip()
    for value in df["country"]
    for country in value.split(",")
    if country.strip() and country.strip() != "Unknown"
))

genres = sorted(set(
    genre.strip()
    for value in df["listed_in"]
    for genre in value.split(",")
    if genre.strip() and genre.strip() != "Unknown"
))

country_options = ["All"] + countries
genre_options = ["All"] + genres

valid_years = df["release_year"].dropna()

if len(valid_years):
    MIN_YEAR = int(valid_years.min())
    MAX_YEAR = int(valid_years.max())
else:
    MIN_YEAR = 1900
    MAX_YEAR = 2026

if MIN_YEAR == MAX_YEAR:
    MAX_YEAR += 1

# ==========================================
# 4. EMPTY CHART FUNCTION
# ==========================================

def empty_chart(message):
    fig = go.Figure()

    fig.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False
    )

    fig.update_layout(
        template="plotly_dark",
        height=350
    )

    return fig

# ==========================================
# 5. DASHBOARD FUNCTION
# ==========================================

def netflix_dashboard(
    content_type,
    country,
    genre,
    start_year,
    end_year,
    search_title
):

    data = df.copy()

    # Filter content type
    if content_type != "All":
        data = data[data["type"] == content_type]

    # Filter country
    if country != "All":
        data = data[
            data["country"].apply(
                lambda x: country in [
                    c.strip() for c in x.split(",")
                ]
            )
        ]

    # Filter genre
    if genre != "All":
        data = data[
            data["listed_in"].apply(
                lambda x: genre in [
                    g.strip() for g in x.split(",")
                ]
            )
        ]

    # Filter release year
    if start_year > end_year:
        start_year, end_year = end_year, start_year

    data = data[
        data["release_year"].between(
            start_year, end_year
        )
    ]

    # Search title
    if search_title and search_title.strip():
        data = data[
            data["title"].str.contains(
                search_title.strip(),
                case=False,
                na=False,
                regex=False
            )
        ]

    # ======================================
    # 6. CALCULATE DASHBOARD STATISTICS
    # ======================================

    total_titles = len(data)

    total_movies = int(
        (data["type"] == "Movie").sum()
    )

    total_shows = int(
        (data["type"] == "TV Show").sum()
    )

    total_countries = len(set(
        c.strip()
        for value in data["country"]
        for c in value.split(",")
        if c.strip() and c.strip() != "Unknown"
    ))

    total_genres = len(set(
        g.strip()
        for value in data["listed_in"]
        for g in value.split(",")
        if g.strip() and g.strip() != "Unknown"
    ))

    movie_percent = (
        total_movies / total_titles * 100
        if total_titles else 0
    )

    show_percent = (
        total_shows / total_titles * 100
        if total_titles else 0
    )

    summary = f"""
# 🎬 NETFLIX ANALYTICS DASHBOARD

## Dashboard Overview

| KPI | Value |
|---|---:|
| Total Netflix Titles | {total_titles:,} |
| Total Movies | {total_movies:,} |
| Total TV Shows | {total_shows:,} |
| Countries Represented | {total_countries:,} |
| Genre Categories | {total_genres:,} |

**Movies Percentage:** {movie_percent:.2f}%

**TV Shows Percentage:** {show_percent:.2f}%
"""

    # ======================================
    # 7. MOVIES VS TV SHOWS
    # ======================================

    type_counts = (
        data["type"].value_counts()
        .reset_index()
    )

    type_counts.columns = ["Type", "Count"]

    if not type_counts.empty:
        fig_type = px.pie(
            type_counts,
            names="Type",
            values="Count",
            hole=0.5,
            title="Movies vs TV Shows",
            color_discrete_sequence=[
                "#E50914", "#6254A5"
            ]
        )
    else:
        fig_type = empty_chart("No content available")

    fig_type.update_layout(
        template="plotly_dark",
        height=350
    )

    # ======================================
    # 8. CONTENT BY RELEASE YEAR
    # ======================================

    year_data = (
        data.dropna(subset=["release_year"])
        .groupby("release_year")
        .size()
        .reset_index(name="Titles")
    )

    if not year_data.empty:
        fig_year = px.line(
            year_data,
            x="release_year",
            y="Titles",
            markers=True,
            title="Content by Release Year"
        )

        fig_year.update_traces(
            line_color="#E50914"
        )
    else:
        fig_year = empty_chart("No release year data")

    fig_year.update_layout(
        template="plotly_dark",
        height=350
    )

    # ======================================
    # 9. TOP 10 COUNTRIES
    # ======================================

    country_data = data.assign(
        country=data["country"].str.split(",")
    ).explode("country")

    country_data["country"] = (
        country_data["country"].str.strip()
    )

    country_counts = (
        country_data[
            (country_data["country"] != "Unknown") &
            (country_data["country"] != "")
        ]
        .groupby("country")
        .size()
        .sort_values(ascending=False)
        .head(10)
        .reset_index(name="Titles")
    )

    if not country_counts.empty:
        fig_country = px.bar(
            country_counts.sort_values("Titles"),
            x="Titles",
            y="country",
            orientation="h",
            title="Top 10 Countries",
            color="Titles",
            color_continuous_scale="Reds"
        )
    else:
        fig_country = empty_chart("No country data available")

    fig_country.update_layout(
        template="plotly_dark",
        height=400
    )

    # ======================================
    # 10. TOP 10 GENRES
    # ======================================

    genre_data = data.assign(
        genre=data["listed_in"].str.split(",")
    ).explode("genre")

    genre_data["genre"] = (
        genre_data["genre"].str.strip()
    )

    genre_counts = (
        genre_data[
            (genre_data["genre"] != "Unknown") &
            (genre_data["genre"] != "")
        ]
        .groupby("genre")
        .size()
        .sort_values(ascending=False)
        .head(10)
        .reset_index(name="Titles")
    )

    if not genre_counts.empty:
        fig_genre = px.bar(
            genre_counts.sort_values("Titles"),
            x="Titles",
            y="genre",
            orientation="h",
            title="Top 10 Netflix Genres",
            color="Titles",
            color_continuous_scale="Reds"
        )
    else:
        fig_genre = empty_chart("No genre data available")

    fig_genre.update_layout(
        template="plotly_dark",
        height=400
    )

    # ======================================
    # 11. CONTENT RATINGS
    # ======================================

    rating_counts = (
        data["rating"].value_counts()
        .reset_index()
    )

    rating_counts.columns = ["Rating", "Count"]

    if not rating_counts.empty:
        fig_rating = px.bar(
            rating_counts,
            x="Rating",
            y="Count",
            title="Content Rating Distribution",
            color="Count",
            color_continuous_scale="Reds"
        )
    else:
        fig_rating = empty_chart("No rating data available")

    fig_rating.update_layout(
        template="plotly_dark",
        height=350
    )

    # ======================================
    # 12. DATASET TABLE
    # ======================================

    table = data[
        [
            "show_id", "type", "title",
            "director", "country",
            "release_year", "rating",
            "duration", "listed_in"
        ]
    ].head(100)

    return (
        summary,
        fig_type,
        fig_year,
        fig_country,
        fig_genre,
        fig_rating,
        table
    )

# ==========================================
# 13. BUILD GRADIO INTERFACE
# ==========================================

demo = gr.Interface(

    fn=netflix_dashboard,

    inputs=[

        gr.Dropdown(
            choices=content_types,
            value="All",
            label="Content Type"
        ),

        gr.Dropdown(
            choices=country_options,
            value="All",
            label="Country"
        ),

        gr.Dropdown(
            choices=genre_options,
            value="All",
            label="Genre"
        ),

        gr.Slider(
            minimum=MIN_YEAR,
            maximum=MAX_YEAR,
            value=MIN_YEAR,
            step=1,
            label="Starting Release Year"
        ),

        gr.Slider(
            minimum=MIN_YEAR,
            maximum=MAX_YEAR,
            value=MAX_YEAR,
            step=1,
            label="Ending Release Year"
        ),

        gr.Textbox(
            label="Search Netflix Title",
            placeholder="Search a Movie or TV Show"
        )
    ],

    outputs=[

        gr.Markdown(label="Dashboard Statistics"),

        gr.Plot(label="Movies vs TV Shows"),

        gr.Plot(label="Release Year Analysis"),

        gr.Plot(label="Top Countries"),

        gr.Plot(label="Top Genres"),

        gr.Plot(label="Content Ratings"),

        gr.Dataframe(label="Netflix Dataset Explorer")
    ],

    title="🎬 Netflix Data Analytics Dashboard",

    description=(
        "Explore Netflix data through interactive "
        "charts, filters and statistics."
    ),

    theme=gr.themes.Soft(
        primary_hue="red",
        secondary_hue="slate"
    ),

)

# ==========================================
# 14. LAUNCH DASHBOARD
# ==========================================

if __name__ == "__main__":

    demo.launch(
        share=True,
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", 7860))
    )
