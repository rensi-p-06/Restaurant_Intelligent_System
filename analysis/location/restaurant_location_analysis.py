import argparse
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_CSV_PATH = r"Dataset\cleaned_dataset.csv"
DEFAULT_OUTPUT_DIR = "location_analysis_results"

CORE_COLUMNS = [
    "Restaurant ID",
    "Restaurant Name",
    "City",
    "Locality",
    "Latitude",
    "Longitude",
    "Cuisines",
    "Average Cost INR",
    "Log Average Cost INR",
    "Price range",
    "Aggregate rating",
    "Votes",
    "Log Votes",
    "Has Table booking",
    "Has Online delivery",
    "Restaurant Cost Category",
    "Rating Category",
    "Popularity Category",
    "City Restaurant Count",
    "Is Expensive",
    "Location Cluster",
    "City Location Cluster",
]


def resolve_path(path: str) -> Path:
    candidate = Path(path)
    if candidate.exists() or candidate.is_absolute():
        return candidate
    return Path(__file__).resolve().parent / candidate


def split_cuisines(value: object) -> list[str]:
    return [item.strip() for item in str(value).split(",") if item.strip()]


def safe_mode(series: pd.Series) -> str:
    series = series.dropna().astype(str)
    if series.empty:
        return "Unknown"
    return series.mode().iloc[0]


def most_common_cuisine(series: pd.Series) -> str:
    cuisines = []
    for value in series.dropna():
        cuisines.extend(split_cuisines(value))
    if not cuisines:
        return "Unknown"
    return Counter(cuisines).most_common(1)[0][0]


def unique_cuisine_count(series: pd.Series) -> int:
    cuisines = set()
    for value in series.dropna():
        cuisines.update(split_cuisines(value))
    return len(cuisines)


def load_dataset(csv_path: str) -> pd.DataFrame:
    data_path = resolve_path(csv_path)
    df = pd.read_csv(data_path)
    df.columns = df.columns.str.strip()

    missing = [col for col in CORE_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df[CORE_COLUMNS].copy()

    text_columns = [
        "Restaurant Name",
        "City",
        "Locality",
        "Cuisines",
        "Has Table booking",
        "Has Online delivery",
        "Restaurant Cost Category",
        "Rating Category",
        "Popularity Category",
        "City Location Cluster",
    ]
    for col in text_columns:
        df[col] = df[col].fillna("Unknown").astype(str).str.strip()

    numeric_columns = [
        "Restaurant ID",
        "Latitude",
        "Longitude",
        "Average Cost INR",
        "Log Average Cost INR",
        "Price range",
        "Aggregate rating",
        "Votes",
        "Log Votes",
        "City Restaurant Count",
        "Is Expensive",
        "Location Cluster",
    ]
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["Average Cost INR"] = df["Average Cost INR"].fillna(df["Average Cost INR"].median())
    df["Log Average Cost INR"] = df["Log Average Cost INR"].fillna(
        np.log1p(df["Average Cost INR"].clip(lower=0))
    )
    df["Price range"] = df["Price range"].fillna(df["Price range"].median()).astype(int)
    df["Aggregate rating"] = df["Aggregate rating"].fillna(0)
    df["Votes"] = df["Votes"].fillna(0).astype(int)
    df["Log Votes"] = df["Log Votes"].fillna(np.log1p(df["Votes"].clip(lower=0)))
    df["City Restaurant Count"] = df["City Restaurant Count"].fillna(0).astype(int)
    df["Is Expensive"] = df["Is Expensive"].fillna(0).astype(int)
    df["Location Cluster"] = df["Location Cluster"].fillna(-1).astype(int)

    valid_coordinate_mask = (
        df["Latitude"].between(-90, 90)
        & df["Longitude"].between(-180, 180)
        & ~((df["Latitude"] == 0) & (df["Longitude"] == 0))
    )
    df["Has Valid Coordinates"] = valid_coordinate_mask

    return df


def build_city_stats(df: pd.DataFrame) -> pd.DataFrame:
    grouped = df.groupby("City")
    stats = grouped.agg(
        Restaurant_Count=("Restaurant ID", "count"),
        Avg_Rating=("Aggregate rating", "mean"),
        Median_Rating=("Aggregate rating", "median"),
        Avg_Cost_INR=("Average Cost INR", "mean"),
        Median_Cost_INR=("Average Cost INR", "median"),
        Avg_Price_Range=("Price range", "mean"),
        Total_Votes=("Votes", "sum"),
        Avg_Log_Votes=("Log Votes", "mean"),
        Delivery_Restaurants=("Has Online delivery", lambda x: (x.str.lower() == "yes").sum()),
        Booking_Restaurants=("Has Table booking", lambda x: (x.str.lower() == "yes").sum()),
        Expensive_Restaurants=("Is Expensive", "sum"),
        Valid_Coordinate_Count=("Has Valid Coordinates", "sum"),
        Dominant_Cost_Category=("Restaurant Cost Category", safe_mode),
        Dominant_Rating_Category=("Rating Category", safe_mode),
        Dominant_Popularity_Category=("Popularity Category", safe_mode),
        Most_Common_Cuisine=("Cuisines", most_common_cuisine),
        Unique_Cuisine_Count=("Cuisines", unique_cuisine_count),
    ).reset_index()

    stats["Delivery_Percentage"] = (
        stats["Delivery_Restaurants"] / stats["Restaurant_Count"] * 100
    ).round(2)
    stats["Booking_Percentage"] = (
        stats["Booking_Restaurants"] / stats["Restaurant_Count"] * 100
    ).round(2)
    stats["Expensive_Percentage"] = (
        stats["Expensive_Restaurants"] / stats["Restaurant_Count"] * 100
    ).round(2)

    return stats.sort_values("Restaurant_Count", ascending=False)


def build_locality_stats(df: pd.DataFrame, min_count: int) -> pd.DataFrame:
    grouped = df.groupby(["City", "Locality"])
    stats = grouped.agg(
        Restaurant_Count=("Restaurant ID", "count"),
        Avg_Rating=("Aggregate rating", "mean"),
        Avg_Cost_INR=("Average Cost INR", "mean"),
        Avg_Price_Range=("Price range", "mean"),
        Total_Votes=("Votes", "sum"),
        Most_Common_Cuisine=("Cuisines", most_common_cuisine),
    ).reset_index()
    stats = stats[stats["Restaurant_Count"] >= min_count]
    return stats.sort_values(["Restaurant_Count", "Avg_Rating"], ascending=[False, False])


def build_cluster_stats(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    location_cluster_stats = (
        df.groupby("Location Cluster")
        .agg(
            Restaurant_Count=("Restaurant ID", "count"),
            Avg_Rating=("Aggregate rating", "mean"),
            Avg_Cost_INR=("Average Cost INR", "mean"),
            Avg_Price_Range=("Price range", "mean"),
            Most_Common_Cuisine=("Cuisines", most_common_cuisine),
            Dominant_Cost_Category=("Restaurant Cost Category", safe_mode),
        )
        .reset_index()
        .sort_values("Restaurant_Count", ascending=False)
    )

    city_cluster_stats = (
        df.groupby("City Location Cluster")
        .agg(
            City=("City", safe_mode),
            Restaurant_Count=("Restaurant ID", "count"),
            Avg_Rating=("Aggregate rating", "mean"),
            Avg_Cost_INR=("Average Cost INR", "mean"),
            Avg_Price_Range=("Price range", "mean"),
            Most_Common_Cuisine=("Cuisines", most_common_cuisine),
            Dominant_Cost_Category=("Restaurant Cost Category", safe_mode),
        )
        .reset_index()
        .sort_values("Restaurant_Count", ascending=False)
    )

    return location_cluster_stats, city_cluster_stats


def build_cuisine_stats(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for row in df[["City", "Cuisines", "Aggregate rating", "Average Cost INR", "Price range"]].to_dict(orient="records"):
        for cuisine in split_cuisines(row["Cuisines"]):
            rows.append(
                {
                    "City": row["City"],
                    "Cuisine": cuisine,
                    "Aggregate rating": row["Aggregate rating"],
                    "Average Cost INR": row["Average Cost INR"],
                    "Price range": row["Price range"],
                }
            )

    cuisine_df = pd.DataFrame(rows)
    overall = (
        cuisine_df.groupby("Cuisine")
        .agg(
            Restaurant_Count=("Cuisine", "count"),
            Avg_Rating=("Aggregate rating", "mean"),
            Avg_Cost_INR=("Average Cost INR", "mean"),
            Avg_Price_Range=("Price range", "mean"),
        )
        .reset_index()
        .sort_values("Restaurant_Count", ascending=False)
    )

    by_city = (
        cuisine_df.groupby(["City", "Cuisine"])
        .agg(
            Restaurant_Count=("Cuisine", "count"),
            Avg_Rating=("Aggregate rating", "mean"),
            Avg_Cost_INR=("Average Cost INR", "mean"),
        )
        .reset_index()
        .sort_values(["City", "Restaurant_Count"], ascending=[True, False])
    )

    return overall, by_city


def save_csv_outputs(
    output_dir: Path,
    city_stats: pd.DataFrame,
    locality_stats: pd.DataFrame,
    location_cluster_stats: pd.DataFrame,
    city_cluster_stats: pd.DataFrame,
    cuisine_overall: pd.DataFrame,
    cuisine_by_city: pd.DataFrame,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    city_stats.to_csv(output_dir / "city_statistics.csv", index=False)
    locality_stats.to_csv(output_dir / "locality_statistics_min_count.csv", index=False)
    location_cluster_stats.to_csv(output_dir / "location_cluster_statistics.csv", index=False)
    city_cluster_stats.to_csv(output_dir / "city_location_cluster_statistics.csv", index=False)
    cuisine_overall.to_csv(output_dir / "overall_cuisine_statistics.csv", index=False)
    cuisine_by_city.to_csv(output_dir / "city_cuisine_statistics.csv", index=False)


def add_heatmap_legend(folium_map) -> None:
    from branca.element import Element

    legend_html = """
    <div style="
        position: fixed;
        bottom: 24px;
        left: 24px;
        z-index: 9999;
        background: white;
        padding: 12px 14px;
        border: 1px solid #9ca3af;
        border-radius: 6px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.25);
        font-family: Arial, sans-serif;
        font-size: 12px;
        color: #111827;
        max-width: 250px;
    ">
        <div style="font-weight:700;font-size:13px;margin-bottom:8px;">Restaurant Density Heatmap</div>
        <div style="height:12px;width:200px;background:linear-gradient(to right,#2563eb,#22c55e,#facc15,#ef4444);border:1px solid #111827;"></div>
        <div style="display:flex;justify-content:space-between;width:200px;margin-top:4px;">
            <span>Low density</span><span>High density</span>
        </div>
        <div style="font-size:11px;color:#4b5563;margin-top:6px;">
            Red/yellow areas show higher restaurant concentration. Blue/green areas show lower concentration.
        </div>
    </div>
    """
    folium_map.get_root().html.add_child(Element(legend_html))


def add_heatmap_title(folium_map, total_restaurants: int) -> None:
    from branca.element import Element

    title_html = f"""
    <div style="
        position: fixed;
        top: 18px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 9999;
        background: rgba(255,255,255,0.94);
        padding: 10px 16px;
        border: 1px solid #d1d5db;
        border-radius: 999px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.18);
        font-family: Arial, sans-serif;
        color: #111827;
        text-align: center;
    ">
        <div style="font-weight:700;font-size:14px;">Restaurant Density Heatmap</div>
        <div style="font-size:11px;color:#4b5563;">Based on {total_restaurants:,} restaurants with valid coordinates</div>
    </div>
    """
    folium_map.get_root().html.add_child(Element(title_html))


def add_heatmap_toggle_note(folium_map, city_count: int) -> None:
    from branca.element import Element

    note_html = f"""
    <div style="
        position: fixed;
        top: 86px;
        left: 18px;
        z-index: 9999;
        background: rgba(255,255,255,0.95);
        padding: 10px 12px;
        border: 1px solid #d1d5db;
        border-radius: 6px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.18);
        font-family: Arial, sans-serif;
        color: #111827;
        font-size: 11px;
        max-width: 245px;
        line-height: 1.4;
    ">
        <div style="font-weight:700;font-size:12px;margin-bottom:5px;">Heatmap Toggles</div>
        <div>Use the layer button in the top-right corner to compare:</div>
        <ul style="margin:6px 0 0 16px;padding:0;">
            <li>All restaurant density</li>
            <li>High-rated restaurant density</li>
            <li>Low-rated restaurant density</li>
            <li>Top {city_count} city-only heatmaps</li>
        </ul>
    </div>
    """
    folium_map.get_root().html.add_child(Element(note_html))


def add_heatmap_control_styles(folium_map) -> None:
    from branca.element import Element

    style_html = """
    <style>
        .leaflet-control-layers {
            border: 0 !important;
            border-radius: 14px !important;
            overflow: hidden;
            box-shadow: 0 12px 32px rgba(17, 24, 39, 0.22) !important;
            background: rgba(255, 255, 255, 0.94) !important;
            backdrop-filter: blur(10px);
            font-family: Arial, sans-serif;
        }
        .leaflet-control-layers-expanded {
            padding: 12px 14px !important;
            min-width: 310px;
            max-height: 74vh;
            overflow-y: auto;
        }
        .leaflet-control-layers::before {
            content: "Select Heatmap Layer";
            display: block;
            font-weight: 800;
            font-size: 13px;
            color: #111827;
            margin-bottom: 8px;
            padding-bottom: 8px;
            border-bottom: 1px solid #e5e7eb;
        }
        .leaflet-control-layers-overlays label {
            display: flex;
            align-items: center;
            gap: 8px;
            margin: 6px 0;
            padding: 7px 8px;
            border-radius: 10px;
            color: #374151;
            font-size: 12px;
            cursor: pointer;
            transition: background 140ms ease, color 140ms ease;
        }
        .leaflet-control-layers-overlays label:hover {
            background: #fff7ed;
            color: #c4621d;
        }
        .leaflet-control-layers-selector {
            width: 16px;
            height: 16px;
            accent-color: #c4621d;
            flex-shrink: 0;
        }
        .leaflet-control-layers-separator {
            display: none;
        }
    </style>
    """
    folium_map.get_root().html.add_child(Element(style_html))


def heat_points_from_frame(frame: pd.DataFrame) -> list[list[float]]:
    return frame[["Latitude", "Longitude"]].dropna().values.tolist()


def add_heat_layer(
    folium_module,
    heatmap_class,
    folium_map,
    frame: pd.DataFrame,
    name: str,
    show: bool,
    radius: int = 10,
    blur: int = 15,
) -> int:
    heat_points = heat_points_from_frame(frame)
    if not heat_points:
        return 0
    layer = folium_module.FeatureGroup(name=f"{name} ({len(heat_points):,})", show=show)
    heatmap_class(heat_points, radius=radius, blur=blur, min_opacity=0.25).add_to(layer)
    layer.add_to(folium_map)
    return len(heat_points)


def create_folium_maps(df: pd.DataFrame, output_dir: Path, max_map_points: int) -> None:
    try:
        import folium
        from folium.plugins import HeatMap, MarkerCluster
    except ImportError:
        print("Folium is not installed. Skipping interactive maps.")
        return

    map_df = df[df["Has Valid Coordinates"]].copy()
    if map_df.empty:
        print("No valid coordinates found. Skipping maps.")
        return

    center_lat = map_df["Latitude"].median()
    center_lon = map_df["Longitude"].median()

    sampled = map_df.sort_values(["Aggregate rating", "Votes"], ascending=[False, False]).head(max_map_points)

    restaurant_map = folium.Map(location=[center_lat, center_lon], zoom_start=3, tiles="OpenStreetMap")
    marker_cluster = MarkerCluster(name="Restaurants").add_to(restaurant_map)

    for row in sampled.to_dict(orient="records"):
        popup = folium.Popup(
            html=(
                f"<b>{row['Restaurant Name']}</b><br>"
                f"City: {row['City']}<br>"
                f"Cuisines: {row['Cuisines']}<br>"
                f"Rating: {row['Aggregate rating']}<br>"
                f"Cost INR: {row['Average Cost INR']}<br>"
                f"Price range: {row['Price range']}"
            ),
            max_width=350,
        )
        folium.CircleMarker(
            location=[row["Latitude"], row["Longitude"]],
            radius=4,
            popup=popup,
            color="#2563eb",
            fill=True,
            fill_opacity=0.7,
        ).add_to(marker_cluster)

    restaurant_map.save(output_dir / "restaurant_location_marker_map.html")

    heat_map = folium.Map(location=[center_lat, center_lon], zoom_start=3, tiles=None)
    folium.TileLayer("CartoDB positron", name="Base Map", control=False).add_to(heat_map)
    all_count = add_heat_layer(folium, HeatMap, heat_map, map_df, "All Restaurants Density", show=True)

    high_rated_df = map_df[map_df["Aggregate rating"] >= 4.0]
    add_heat_layer(folium, HeatMap, heat_map, high_rated_df, "High-Rated Restaurants Density (rating >= 4.0)", show=False)

    low_rated_df = map_df[(map_df["Aggregate rating"] > 0) & (map_df["Aggregate rating"] < 3.0)]
    add_heat_layer(folium, HeatMap, heat_map, low_rated_df, "Low-Rated Restaurants Density (0 < rating < 3.0)", show=False)

    top_city_names = (
        map_df["City"]
        .dropna()
        .astype(str)
        .value_counts()
        .head(10)
        .index
        .tolist()
    )
    for city in top_city_names:
        city_df = map_df[map_df["City"].astype(str) == city]
        add_heat_layer(folium, HeatMap, heat_map, city_df, f"City Filter: {city}", show=False, radius=12, blur=17)

    folium.LayerControl(collapsed=False, position="topright").add_to(heat_map)
    add_heatmap_title(heat_map, total_restaurants=all_count)
    add_heatmap_toggle_note(heat_map, city_count=len(top_city_names))
    add_heatmap_control_styles(heat_map)
    add_heatmap_legend(heat_map)
    heat_map.save(output_dir / "restaurant_density_heatmap.html")

    print("Saved Folium maps.")


def create_plotly_graphs(
    output_dir: Path,
    city_stats: pd.DataFrame,
    location_cluster_stats: pd.DataFrame,
    cuisine_overall: pd.DataFrame,
    top_n: int,
) -> None:
    try:
        import plotly.express as px
    except ImportError:
        print("Plotly is not installed. Skipping HTML graphs.")
        return

    template = "plotly_dark"

    top_cities = city_stats.head(top_n)
    fig = px.bar(
        top_cities.sort_values("Restaurant_Count"),
        x="Restaurant_Count",
        y="City",
        orientation="h",
        title=f"Top {top_n} Cities by Restaurant Count",
        template=template,
        text="Restaurant_Count",
    )
    fig.write_html(output_dir / "top_cities_by_restaurant_count.html", include_plotlyjs=True)

    rating_cities = city_stats[city_stats["Restaurant_Count"] >= 10].sort_values("Avg_Rating", ascending=False).head(top_n)
    fig = px.bar(
        rating_cities.sort_values("Avg_Rating"),
        x="Avg_Rating",
        y="City",
        orientation="h",
        title=f"Top {top_n} Cities by Average Rating",
        template=template,
        text=rating_cities["Avg_Rating"].round(2),
    )
    fig.write_html(output_dir / "top_cities_by_average_rating.html", include_plotlyjs=True)

    cost_cities = city_stats[city_stats["Restaurant_Count"] >= 10].sort_values("Avg_Cost_INR", ascending=False).head(top_n)
    fig = px.bar(
        cost_cities.sort_values("Avg_Cost_INR"),
        x="Avg_Cost_INR",
        y="City",
        orientation="h",
        title=f"Top {top_n} Cities by Average Cost INR",
        template=template,
        text=cost_cities["Avg_Cost_INR"].round(0),
    )
    fig.write_html(output_dir / "top_cities_by_average_cost.html", include_plotlyjs=True)

    fig = px.scatter(
        city_stats,
        x="Avg_Cost_INR",
        y="Avg_Rating",
        size="Restaurant_Count",
        color="Dominant_Cost_Category",
        hover_name="City",
        title="City-Level Rating vs Cost",
        template=template,
    )
    fig.write_html(output_dir / "city_rating_vs_cost.html", include_plotlyjs=True)

    top_cuisines = cuisine_overall.head(top_n)
    fig = px.bar(
        top_cuisines.sort_values("Restaurant_Count"),
        x="Restaurant_Count",
        y="Cuisine",
        orientation="h",
        title=f"Top {top_n} Cuisines Overall",
        template=template,
        text="Restaurant_Count",
    )
    fig.write_html(output_dir / "top_cuisines_overall.html", include_plotlyjs=True)

    top_clusters = location_cluster_stats.head(top_n)
    fig = px.bar(
        top_clusters.sort_values("Restaurant_Count"),
        x="Restaurant_Count",
        y="Location Cluster",
        orientation="h",
        title=f"Top {top_n} Location Clusters by Restaurant Count",
        template=template,
        text="Restaurant_Count",
    )
    fig.write_html(output_dir / "top_location_clusters.html", include_plotlyjs=True)

    print("Saved Plotly graphs.")


def create_insights_report(
    output_dir: Path,
    df: pd.DataFrame,
    city_stats: pd.DataFrame,
    location_cluster_stats: pd.DataFrame,
    city_cluster_stats: pd.DataFrame,
    cuisine_overall: pd.DataFrame,
    min_city_count: int,
) -> None:
    valid_coords = int(df["Has Valid Coordinates"].sum())
    total_rows = len(df)
    top_city = city_stats.iloc[0]

    eligible_cities = city_stats[city_stats["Restaurant_Count"] >= min_city_count]
    best_rating_city = eligible_cities.sort_values("Avg_Rating", ascending=False).iloc[0]
    highest_cost_city = eligible_cities.sort_values("Avg_Cost_INR", ascending=False).iloc[0]
    top_cluster = location_cluster_stats.iloc[0]
    top_city_cluster = city_cluster_stats.iloc[0]
    top_cuisine = cuisine_overall.iloc[0]

    lines = [
        "# Location-Based Restaurant Analysis",
        "",
        "## Dataset Summary",
        f"- Total restaurants analyzed: {total_rows:,}",
        f"- Restaurants with valid coordinates: {valid_coords:,} ({valid_coords / total_rows * 100:.2f}%)",
        f"- Number of cities: {df['City'].nunique():,}",
        f"- Number of location clusters: {df['Location Cluster'].nunique():,}",
        f"- Number of city-location clusters: {df['City Location Cluster'].nunique():,}",
        "",
        "## Key Insights",
        f"- Highest restaurant concentration is in **{top_city['City']}** with {int(top_city['Restaurant_Count']):,} restaurants.",
        f"- Among cities with at least {min_city_count} restaurants, the highest average rating is in **{best_rating_city['City']}** "
        f"with average rating {best_rating_city['Avg_Rating']:.2f}.",
        f"- Among cities with at least {min_city_count} restaurants, the highest average cost is in **{highest_cost_city['City']}** "
        f"with average cost INR {highest_cost_city['Avg_Cost_INR']:.2f}.",
        f"- The most common cuisine overall is **{top_cuisine['Cuisine']}** with {int(top_cuisine['Restaurant_Count']):,} restaurant appearances.",
        f"- The largest location cluster is **{int(top_cluster['Location Cluster'])}** with {int(top_cluster['Restaurant_Count']):,} restaurants.",
        f"- The largest city-location cluster is **{top_city_cluster['City Location Cluster']}** with "
        f"{int(top_city_cluster['Restaurant_Count']):,} restaurants.",
        "",
        "## Notes",
        "- Locality-level output is generated, but locality should be interpreted carefully because some locality values may be noisy.",
        "- City and cluster-level analysis is more reliable for this dataset.",
        "- Interactive HTML maps and charts are saved in the output folder.",
    ]

    (output_dir / "location_analysis_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Perform location-based restaurant analysis.")
    parser.add_argument("--csv", default=DEFAULT_CSV_PATH, help="Path to cleaned_dataset.csv")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Folder for CSVs, maps, graphs, and report")
    parser.add_argument("--top-n", type=int, default=20, help="Number of top cities/cuisines/clusters in charts")
    parser.add_argument("--min-city-count", type=int, default=10, help="Minimum restaurants required for rating/cost city insights")
    parser.add_argument("--min-locality-count", type=int, default=10, help="Minimum restaurants required in locality output")
    parser.add_argument("--max-map-points", type=int, default=2500, help="Maximum points shown on marker map")
    args = parser.parse_args()

    output_dir = resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = load_dataset(args.csv)
    city_stats = build_city_stats(df)
    locality_stats = build_locality_stats(df, min_count=args.min_locality_count)
    location_cluster_stats, city_cluster_stats = build_cluster_stats(df)
    cuisine_overall, cuisine_by_city = build_cuisine_stats(df)

    save_csv_outputs(
        output_dir=output_dir,
        city_stats=city_stats,
        locality_stats=locality_stats,
        location_cluster_stats=location_cluster_stats,
        city_cluster_stats=city_cluster_stats,
        cuisine_overall=cuisine_overall,
        cuisine_by_city=cuisine_by_city,
    )

    create_folium_maps(df, output_dir=output_dir, max_map_points=args.max_map_points)
    create_plotly_graphs(
        output_dir=output_dir,
        city_stats=city_stats,
        location_cluster_stats=location_cluster_stats,
        cuisine_overall=cuisine_overall,
        top_n=args.top_n,
    )
    create_insights_report(
        output_dir=output_dir,
        df=df,
        city_stats=city_stats,
        location_cluster_stats=location_cluster_stats,
        city_cluster_stats=city_cluster_stats,
        cuisine_overall=cuisine_overall,
        min_city_count=args.min_city_count,
    )

    print(f"Location analysis complete. Outputs saved to: {output_dir.resolve()}")
    print("Main report: location_analysis_report.md")


if __name__ == "__main__":
    main()
