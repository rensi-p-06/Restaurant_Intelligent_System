import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_DB_PATH = "restaurant_recommendation.db"
DEFAULT_CSV_PATH = r"Dataset\cleaned_dataset.csv"

RESTAURANT_COLUMNS = [
    "Restaurant ID",
    "Restaurant Name",
    "Country Code",
    "City",
    "Address",
    "Locality",
    "Longitude",
    "Latitude",
    "Cuisines",
    "Average Cost INR",
    "Log Average Cost INR",
    "Cost Relative To City",
    "City wise Cost Category",
    "Restaurant Cost Category",
    "Price range",
    "Aggregate rating",
    "Rating Category",
    "Votes",
    "Log Votes",
    "Popularity Category",
    "Restaurant Popularity Score",
    "City Restaurant Count",
    "Has Table booking",
    "Has Online delivery",
    "Is delivering now",
    "Is Expensive",
    "Has Delivery Or Booking",
    "Location Cluster",
    "City Location Cluster",
]

OPTIONAL_RESTAURANT_DEFAULTS = {
    "Cost Relative To City": 1.0,
    "City wise Cost Category": "Unknown",
    "Restaurant Cost Category": "Unknown",
    "Rating Category": "Unknown",
    "Popularity Category": "Unknown",
    "Restaurant Popularity Score": 0.0,
    "City Restaurant Count": 0,
    "Is delivering now": "No",
    "Is Expensive": 0,
    "Has Delivery Or Booking": 0,
    "Location Cluster": -1,
    "City Location Cluster": "Unknown",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def resolve_path(path: str) -> Path:
    candidate = Path(path)
    if candidate.exists() or candidate.is_absolute():
        return candidate
    return Path(__file__).resolve().parent / candidate


def connect(db_path: str) -> sqlite3.Connection:
    resolved = resolve_path(db_path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(resolved)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS restaurants (
            restaurant_id INTEGER PRIMARY KEY,
            restaurant_name TEXT NOT NULL,
            country_code INTEGER,
            city TEXT,
            address TEXT,
            locality TEXT,
            longitude REAL,
            latitude REAL,
            average_cost_inr REAL,
            log_average_cost_inr REAL,
            cost_relative_to_city REAL,
            city_wise_cost_category TEXT,
            restaurant_cost_category TEXT,
            price_range INTEGER,
            aggregate_rating REAL,
            rating_category TEXT,
            votes INTEGER,
            log_votes REAL,
            popularity_category TEXT,
            restaurant_popularity_score REAL,
            city_restaurant_count INTEGER,
            has_table_booking TEXT,
            has_online_delivery TEXT,
            is_delivering_now TEXT,
            is_expensive INTEGER,
            has_delivery_or_booking INTEGER,
            location_cluster INTEGER,
            city_location_cluster TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS cuisines (
            cuisine_id INTEGER PRIMARY KEY AUTOINCREMENT,
            cuisine_name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS restaurant_cuisines (
            restaurant_id INTEGER NOT NULL,
            cuisine_id INTEGER NOT NULL,
            PRIMARY KEY (restaurant_id, cuisine_id),
            FOREIGN KEY (restaurant_id) REFERENCES restaurants (restaurant_id) ON DELETE CASCADE,
            FOREIGN KEY (cuisine_id) REFERENCES cuisines (cuisine_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS user_preferences (
            preference_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            preferred_cuisines TEXT,
            preferred_city TEXT,
            preferred_locality TEXT,
            preferred_price_range INTEGER,
            max_average_cost_inr REAL,
            min_rating REAL,
            preferred_cost_category TEXT,
            preferred_rating_category TEXT,
            preferred_popularity_category TEXT,
            wants_expensive INTEGER,
            preferred_location_cluster INTEGER,
            preferred_city_location_cluster TEXT,
            wants_online_delivery TEXT,
            wants_table_booking TEXT,
            wants_delivering_now TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS recommendation_history (
            history_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            preferences_json TEXT NOT NULL,
            restaurant_id INTEGER NOT NULL,
            recommendation_score REAL NOT NULL,
            rank INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE SET NULL,
            FOREIGN KEY (restaurant_id) REFERENCES restaurants (restaurant_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_restaurants_city ON restaurants (city);
        CREATE INDEX IF NOT EXISTS idx_restaurants_locality ON restaurants (locality);
        CREATE INDEX IF NOT EXISTS idx_restaurants_price ON restaurants (price_range);
        CREATE INDEX IF NOT EXISTS idx_restaurants_rating ON restaurants (aggregate_rating);
        CREATE INDEX IF NOT EXISTS idx_restaurants_cost_category ON restaurants (restaurant_cost_category);
        CREATE INDEX IF NOT EXISTS idx_restaurants_popularity ON restaurants (popularity_category);
        CREATE INDEX IF NOT EXISTS idx_restaurants_location_cluster ON restaurants (location_cluster);
        CREATE INDEX IF NOT EXISTS idx_restaurants_city_location_cluster ON restaurants (city_location_cluster);
        CREATE INDEX IF NOT EXISTS idx_cuisines_name ON cuisines (cuisine_name);
        """
    )
    add_missing_columns(conn)
    conn.commit()


def add_missing_columns(conn: sqlite3.Connection) -> None:
    restaurant_columns = {row["name"] for row in conn.execute("PRAGMA table_info(restaurants)")}
    restaurant_migrations = {
        "cost_relative_to_city": "ALTER TABLE restaurants ADD COLUMN cost_relative_to_city REAL",
        "city_wise_cost_category": "ALTER TABLE restaurants ADD COLUMN city_wise_cost_category TEXT",
        "restaurant_cost_category": "ALTER TABLE restaurants ADD COLUMN restaurant_cost_category TEXT",
        "rating_category": "ALTER TABLE restaurants ADD COLUMN rating_category TEXT",
        "popularity_category": "ALTER TABLE restaurants ADD COLUMN popularity_category TEXT",
        "restaurant_popularity_score": "ALTER TABLE restaurants ADD COLUMN restaurant_popularity_score REAL",
        "city_restaurant_count": "ALTER TABLE restaurants ADD COLUMN city_restaurant_count INTEGER",
        "is_delivering_now": "ALTER TABLE restaurants ADD COLUMN is_delivering_now TEXT",
        "is_expensive": "ALTER TABLE restaurants ADD COLUMN is_expensive INTEGER",
        "has_delivery_or_booking": "ALTER TABLE restaurants ADD COLUMN has_delivery_or_booking INTEGER",
        "location_cluster": "ALTER TABLE restaurants ADD COLUMN location_cluster INTEGER",
        "city_location_cluster": "ALTER TABLE restaurants ADD COLUMN city_location_cluster TEXT",
    }
    for column, statement in restaurant_migrations.items():
        if column not in restaurant_columns:
            conn.execute(statement)

    preference_columns = {row["name"] for row in conn.execute("PRAGMA table_info(user_preferences)")}
    preference_migrations = {
        "preferred_cost_category": "ALTER TABLE user_preferences ADD COLUMN preferred_cost_category TEXT",
        "preferred_rating_category": "ALTER TABLE user_preferences ADD COLUMN preferred_rating_category TEXT",
        "preferred_popularity_category": "ALTER TABLE user_preferences ADD COLUMN preferred_popularity_category TEXT",
        "wants_expensive": "ALTER TABLE user_preferences ADD COLUMN wants_expensive INTEGER",
        "preferred_location_cluster": "ALTER TABLE user_preferences ADD COLUMN preferred_location_cluster INTEGER",
        "preferred_city_location_cluster": "ALTER TABLE user_preferences ADD COLUMN preferred_city_location_cluster TEXT",
        "wants_delivering_now": "ALTER TABLE user_preferences ADD COLUMN wants_delivering_now TEXT",
    }
    for column, statement in preference_migrations.items():
        if column not in preference_columns:
            conn.execute(statement)


def split_cuisines(value: str) -> list[str]:
    return [cuisine.strip() for cuisine in str(value).split(",") if cuisine.strip()]


def normalize_yes_no(value: object) -> str:
    text = str(value).strip().title()
    return "Yes" if text == "Yes" else "No"


def load_dataset(csv_path: str) -> pd.DataFrame:
    path = resolve_path(csv_path)
    data = pd.read_csv(path)
    data.columns = data.columns.str.strip()

    for col, default in OPTIONAL_RESTAURANT_DEFAULTS.items():
        if col not in data.columns:
            data[col] = default

    missing = [col for col in RESTAURANT_COLUMNS if col not in data.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    data = data[RESTAURANT_COLUMNS].copy()
    data = data.dropna(subset=["Restaurant ID", "Restaurant Name", "Cuisines"])

    text_columns = [
        "Restaurant Name",
        "City",
        "Address",
        "Locality",
        "Cuisines",
        "City wise Cost Category",
        "Restaurant Cost Category",
        "Rating Category",
        "Popularity Category",
        "City Location Cluster",
    ]
    for col in text_columns:
        data[col] = data[col].fillna("Unknown").astype(str).str.strip()

    numeric_columns = [
        "Restaurant ID",
        "Country Code",
        "Longitude",
        "Latitude",
        "Average Cost INR",
        "Log Average Cost INR",
        "Cost Relative To City",
        "Price range",
        "Aggregate rating",
        "Votes",
        "Log Votes",
        "Restaurant Popularity Score",
        "City Restaurant Count",
        "Is Expensive",
        "Has Delivery Or Booking",
        "Location Cluster",
    ]
    for col in numeric_columns:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    data["Average Cost INR"] = data["Average Cost INR"].fillna(data["Average Cost INR"].median())
    data["Log Average Cost INR"] = data["Log Average Cost INR"].fillna(
        np.log1p(data["Average Cost INR"].clip(lower=0))
    )
    data["Cost Relative To City"] = data["Cost Relative To City"].fillna(1.0)
    data["Price range"] = data["Price range"].fillna(data["Price range"].median()).astype(int)
    data["Aggregate rating"] = data["Aggregate rating"].fillna(0)
    data["Votes"] = data["Votes"].fillna(0).astype(int)
    data["Log Votes"] = data["Log Votes"].fillna(np.log1p(data["Votes"].clip(lower=0)))
    data["Restaurant Popularity Score"] = data["Restaurant Popularity Score"].fillna(0)
    data["City Restaurant Count"] = data["City Restaurant Count"].fillna(0).astype(int)
    data["Is Expensive"] = data["Is Expensive"].fillna(0).astype(int)
    data["Has Delivery Or Booking"] = data["Has Delivery Or Booking"].fillna(0).astype(int)
    data["Location Cluster"] = data["Location Cluster"].fillna(-1).astype(int)
    data["Country Code"] = data["Country Code"].fillna(0).astype(int)
    data["Restaurant ID"] = data["Restaurant ID"].astype(int)

    data["Has Table booking"] = data["Has Table booking"].apply(normalize_yes_no)
    data["Has Online delivery"] = data["Has Online delivery"].apply(normalize_yes_no)
    data["Is delivering now"] = data["Is delivering now"].apply(normalize_yes_no)

    return data


def import_restaurants(conn: sqlite3.Connection, csv_path: str) -> None:
    create_tables(conn)
    data = load_dataset(csv_path)
    timestamp = now_utc()

    restaurant_rows = []
    cuisine_names = set()
    restaurant_cuisine_pairs = []

    for row in data.to_dict(orient="records"):
        restaurant_id = int(row["Restaurant ID"])
        cuisines = split_cuisines(row["Cuisines"])

        restaurant_rows.append(
            (
                restaurant_id,
                row["Restaurant Name"],
                int(row["Country Code"]),
                row["City"],
                row["Address"],
                row["Locality"],
                float(row["Longitude"]) if pd.notna(row["Longitude"]) else None,
                float(row["Latitude"]) if pd.notna(row["Latitude"]) else None,
                float(row["Average Cost INR"]),
                float(row["Log Average Cost INR"]),
                float(row["Cost Relative To City"]),
                row["City wise Cost Category"],
                row["Restaurant Cost Category"],
                int(row["Price range"]),
                float(row["Aggregate rating"]),
                row["Rating Category"],
                int(row["Votes"]),
                float(row["Log Votes"]),
                row["Popularity Category"],
                float(row["Restaurant Popularity Score"]),
                int(row["City Restaurant Count"]),
                row["Has Table booking"],
                row["Has Online delivery"],
                row["Is delivering now"],
                int(row["Is Expensive"]),
                int(row["Has Delivery Or Booking"]),
                int(row["Location Cluster"]),
                row["City Location Cluster"],
                timestamp,
                timestamp,
            )
        )

        for cuisine in cuisines:
            cuisine_names.add(cuisine)
            restaurant_cuisine_pairs.append((restaurant_id, cuisine))

    conn.executemany(
        """
        INSERT INTO restaurants (
            restaurant_id, restaurant_name, country_code, city, address, locality,
            longitude, latitude, average_cost_inr, log_average_cost_inr,
            cost_relative_to_city, city_wise_cost_category, restaurant_cost_category,
            price_range, aggregate_rating, rating_category, votes, log_votes,
            popularity_category, restaurant_popularity_score, city_restaurant_count,
            has_table_booking, has_online_delivery, is_delivering_now,
            is_expensive, has_delivery_or_booking, location_cluster, city_location_cluster,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(restaurant_id) DO UPDATE SET
            restaurant_name=excluded.restaurant_name,
            country_code=excluded.country_code,
            city=excluded.city,
            address=excluded.address,
            locality=excluded.locality,
            longitude=excluded.longitude,
            latitude=excluded.latitude,
            average_cost_inr=excluded.average_cost_inr,
            log_average_cost_inr=excluded.log_average_cost_inr,
            cost_relative_to_city=excluded.cost_relative_to_city,
            city_wise_cost_category=excluded.city_wise_cost_category,
            restaurant_cost_category=excluded.restaurant_cost_category,
            price_range=excluded.price_range,
            aggregate_rating=excluded.aggregate_rating,
            rating_category=excluded.rating_category,
            votes=excluded.votes,
            log_votes=excluded.log_votes,
            popularity_category=excluded.popularity_category,
            restaurant_popularity_score=excluded.restaurant_popularity_score,
            city_restaurant_count=excluded.city_restaurant_count,
            has_table_booking=excluded.has_table_booking,
            has_online_delivery=excluded.has_online_delivery,
            is_delivering_now=excluded.is_delivering_now,
            is_expensive=excluded.is_expensive,
            has_delivery_or_booking=excluded.has_delivery_or_booking,
            location_cluster=excluded.location_cluster,
            city_location_cluster=excluded.city_location_cluster,
            updated_at=excluded.updated_at
        """,
        restaurant_rows,
    )

    conn.executemany(
        "INSERT OR IGNORE INTO cuisines (cuisine_name) VALUES (?)",
        [(name,) for name in sorted(cuisine_names)],
    )

    cuisine_id_lookup = {
        row["cuisine_name"]: row["cuisine_id"]
        for row in conn.execute("SELECT cuisine_id, cuisine_name FROM cuisines")
    }

    conn.executemany(
        "INSERT OR IGNORE INTO restaurant_cuisines (restaurant_id, cuisine_id) VALUES (?, ?)",
        [(restaurant_id, cuisine_id_lookup[cuisine]) for restaurant_id, cuisine in restaurant_cuisine_pairs],
    )

    conn.commit()
    print(f"Imported {len(restaurant_rows)} restaurants and {len(cuisine_names)} cuisines.")


def add_user(conn: sqlite3.Connection, name: str, email: str | None = None) -> int:
    create_tables(conn)
    conn.execute(
        "INSERT INTO users (name, email, created_at) VALUES (?, ?, ?)",
        (name, email, now_utc()),
    )
    conn.commit()
    user_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
    print(f"Created user_id={user_id}")
    return user_id


def save_user_preference(conn: sqlite3.Connection, user_id: int, preferences: dict) -> int:
    create_tables(conn)
    conn.execute(
        """
        INSERT INTO user_preferences (
            user_id, preferred_cuisines, preferred_city, preferred_locality,
            preferred_price_range, max_average_cost_inr, min_rating,
            preferred_cost_category, preferred_rating_category, preferred_popularity_category,
            wants_expensive, preferred_location_cluster, preferred_city_location_cluster,
            wants_online_delivery, wants_table_booking, wants_delivering_now, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            ", ".join(preferences.get("cuisines", [])),
            preferences.get("city"),
            preferences.get("locality"),
            preferences.get("price_range"),
            preferences.get("max_cost"),
            preferences.get("min_rating"),
            preferences.get("cost_category"),
            preferences.get("rating_category"),
            preferences.get("popularity_category"),
            preferences.get("is_expensive"),
            preferences.get("location_cluster"),
            preferences.get("city_location_cluster"),
            preferences.get("online_delivery"),
            preferences.get("table_booking"),
            preferences.get("delivering_now"),
            now_utc(),
        ),
    )
    conn.commit()
    preference_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
    print(f"Saved preference_id={preference_id}")
    return preference_id


def load_restaurant_frame(conn: sqlite3.Connection) -> pd.DataFrame:
    query = """
        SELECT
            r.restaurant_id,
            r.restaurant_name,
            r.country_code,
            r.city,
            r.address,
            r.locality,
            r.longitude,
            r.latitude,
            r.average_cost_inr,
            r.log_average_cost_inr,
            r.cost_relative_to_city,
            r.city_wise_cost_category,
            r.restaurant_cost_category,
            r.price_range,
            r.aggregate_rating,
            r.rating_category,
            r.votes,
            r.log_votes,
            r.popularity_category,
            r.restaurant_popularity_score,
            r.city_restaurant_count,
            r.has_table_booking,
            r.has_online_delivery,
            r.is_delivering_now,
            r.is_expensive,
            r.has_delivery_or_booking,
            r.location_cluster,
            r.city_location_cluster,
            GROUP_CONCAT(c.cuisine_name, ', ') AS cuisines
        FROM restaurants r
        LEFT JOIN restaurant_cuisines rc ON r.restaurant_id = rc.restaurant_id
        LEFT JOIN cuisines c ON rc.cuisine_id = c.cuisine_id
        GROUP BY r.restaurant_id
    """
    return pd.read_sql_query(query, conn)


def parse_cuisine_argument(cuisine_text: str | None) -> list[str]:
    if not cuisine_text:
        return []
    return [item.strip() for item in cuisine_text.split(",") if item.strip()]


def score_recommendations(data: pd.DataFrame, preferences: dict) -> pd.DataFrame:
    scored = data.copy()
    scored["score"] = 0.0
    scored["match_reasons"] = ""

    preferred_cuisines = [c.lower() for c in preferences.get("cuisines", [])]
    city = preferences.get("city")
    locality = preferences.get("locality")
    price_range = preferences.get("price_range")
    min_rating = preferences.get("min_rating")
    max_cost = preferences.get("max_cost")
    cost_category = preferences.get("cost_category")
    rating_category = preferences.get("rating_category")
    popularity_category = preferences.get("popularity_category")
    is_expensive = preferences.get("is_expensive")
    location_cluster = preferences.get("location_cluster")
    city_location_cluster = preferences.get("city_location_cluster")
    online_delivery = preferences.get("online_delivery")
    table_booking = preferences.get("table_booking")
    delivering_now = preferences.get("delivering_now")

    if preferred_cuisines:
        cuisine_sets = scored["cuisines"].fillna("").apply(
            lambda value: {cuisine.strip().lower() for cuisine in str(value).split(",") if cuisine.strip()}
        )
        cuisine_match_ratio = cuisine_sets.apply(
            lambda cuisines: len(cuisines.intersection(preferred_cuisines)) / len(preferred_cuisines)
        )
        scored["score"] += cuisine_match_ratio * 40
        scored.loc[cuisine_match_ratio > 0, "match_reasons"] += "cuisine match; "

    if city:
        city_match = scored["city"].fillna("").str.lower() == city.lower()
        scored["score"] += city_match.astype(float) * 20
        scored.loc[city_match, "match_reasons"] += "city match; "

    if locality:
        locality_match = scored["locality"].fillna("").str.lower().str.contains(locality.lower(), regex=False)
        scored["score"] += locality_match.astype(float) * 3
        scored.loc[locality_match, "match_reasons"] += "weak locality match; "

    if price_range is not None:
        price_distance = (scored["price_range"].fillna(price_range) - price_range).abs()
        price_score = (1 - (price_distance / 3).clip(0, 1)) * 12
        scored["score"] += price_score
        scored.loc[price_distance == 0, "match_reasons"] += "price match; "

    if min_rating is not None:
        rating_filter = scored["aggregate_rating"].fillna(0) >= min_rating
        scored = scored.loc[rating_filter].copy()
        scored["match_reasons"] += f"rating >= {min_rating}; "

    rating_score = (scored["aggregate_rating"].fillna(0).clip(0, 5) / 5) * 12
    scored["score"] += rating_score

    if rating_category:
        rating_category_match = scored["rating_category"].fillna("").str.lower() == rating_category.lower()
        scored["score"] += rating_category_match.astype(float) * 6
        scored.loc[rating_category_match, "match_reasons"] += "rating category match; "

    if max_cost is not None:
        cost = scored["average_cost_inr"].fillna(max_cost)
        cost_score = (1 - ((cost - max_cost).clip(lower=0) / max(max_cost, 1)).clip(0, 1)) * 8
        scored["score"] += cost_score
        scored.loc[cost <= max_cost, "match_reasons"] += "within budget; "

    if cost_category:
        cost_category_match = scored["restaurant_cost_category"].fillna("").str.lower() == cost_category.lower()
        scored["score"] += cost_category_match.astype(float) * 8
        scored.loc[cost_category_match, "match_reasons"] += "cost category match; "

    if popularity_category:
        popularity_match = scored["popularity_category"].fillna("").str.lower() == popularity_category.lower()
        scored["score"] += popularity_match.astype(float) * 6
        scored.loc[popularity_match, "match_reasons"] += "popularity category match; "

    if is_expensive is not None:
        expensive_match = scored["is_expensive"].fillna(0).astype(int) == int(is_expensive)
        scored["score"] += expensive_match.astype(float) * 4
        scored.loc[expensive_match, "match_reasons"] += "expensive preference match; "

    if location_cluster is not None:
        cluster_match = scored["location_cluster"].fillna(-1).astype(int) == int(location_cluster)
        scored["score"] += cluster_match.astype(float) * 8
        scored.loc[cluster_match, "match_reasons"] += "location cluster match; "

    if city_location_cluster:
        city_cluster_match = (
            scored["city_location_cluster"].fillna("").str.lower() == city_location_cluster.lower()
        )
        scored["score"] += city_cluster_match.astype(float) * 8
        scored.loc[city_cluster_match, "match_reasons"] += "city-location cluster match; "

    if online_delivery:
        delivery_match = scored["has_online_delivery"].fillna("").str.lower() == online_delivery.lower()
        scored["score"] += delivery_match.astype(float) * 5
        scored.loc[delivery_match, "match_reasons"] += "delivery match; "

    if table_booking:
        booking_match = scored["has_table_booking"].fillna("").str.lower() == table_booking.lower()
        scored["score"] += booking_match.astype(float) * 5
        scored.loc[booking_match, "match_reasons"] += "booking match; "

    if delivering_now:
        delivering_match = scored["is_delivering_now"].fillna("").str.lower() == delivering_now.lower()
        scored["score"] += delivering_match.astype(float) * 3
        scored.loc[delivering_match, "match_reasons"] += "currently delivering match; "

    popularity_score = scored["log_votes"].fillna(0)
    if popularity_score.max() > 0:
        scored["score"] += (popularity_score / popularity_score.max()) * 6

    engineered_popularity = scored["restaurant_popularity_score"].fillna(0)
    if engineered_popularity.max() > 0:
        scored["score"] += (engineered_popularity / engineered_popularity.max()) * 6

    cost_relative = scored["cost_relative_to_city"].fillna(1.0)
    scored["score"] += (1 - (cost_relative - 1).abs().clip(0, 1)) * 2

    scored = scored.sort_values(
        ["score", "aggregate_rating", "votes"],
        ascending=[False, False, False],
    ).reset_index(drop=True)
    scored["rank"] = scored.index + 1
    return scored


def save_recommendation_history(
    conn: sqlite3.Connection,
    user_id: int | None,
    preferences: dict,
    recommendations: pd.DataFrame,
) -> None:
    timestamp = now_utc()
    preferences_json = json.dumps(preferences, ensure_ascii=True)

    rows = [
        (
            user_id,
            preferences_json,
            int(row.restaurant_id),
            float(row.score),
            int(row.rank),
            timestamp,
        )
        for row in recommendations.itertuples(index=False)
    ]

    conn.executemany(
        """
        INSERT INTO recommendation_history (
            user_id, preferences_json, restaurant_id, recommendation_score, rank, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()


def recommend_restaurants(
    conn: sqlite3.Connection,
    preferences: dict,
    top_n: int,
    user_id: int | None = None,
    save_history: bool = True,
) -> pd.DataFrame:
    data = load_restaurant_frame(conn)
    if data.empty:
        raise ValueError("No restaurants found. Run the import-csv command first.")

    recommendations = score_recommendations(data, preferences).head(top_n).copy()

    if save_history and not recommendations.empty:
        save_recommendation_history(conn, user_id, preferences, recommendations)

    return recommendations[
        [
            "rank",
            "restaurant_id",
            "restaurant_name",
            "city",
            "locality",
            "cuisines",
            "price_range",
            "average_cost_inr",
            "restaurant_cost_category",
            "aggregate_rating",
            "rating_category",
            "votes",
            "popularity_category",
            "restaurant_popularity_score",
            "has_online_delivery",
            "has_table_booking",
            "is_delivering_now",
            "is_expensive",
            "location_cluster",
            "city_location_cluster",
            "score",
            "match_reasons",
        ]
    ]


def print_recommendations(recommendations: pd.DataFrame) -> None:
    if recommendations.empty:
        print("No recommendations found for these preferences.")
        return

    display = recommendations.copy()
    display["score"] = display["score"].round(2)
    print(display.to_string(index=False))


def run_sample_tests(conn: sqlite3.Connection) -> None:
    samples = [
        {
            "name": "North Indian delivery in New Delhi",
            "preferences": {
                "cuisines": ["North Indian"],
                "city": "New Delhi",
                "price_range": 2,
                "min_rating": 3.8,
                "cost_category": "Budget",
                "popularity_category": "High",
                "online_delivery": "Yes",
            },
        },
        {
            "name": "Pizza under mid budget",
            "preferences": {
                "cuisines": ["Pizza", "Italian"],
                "price_range": 2,
                "min_rating": 3.5,
                "max_cost": 1200,
                "is_expensive": 0,
            },
        },
        {
            "name": "Cafe with table booking",
            "preferences": {
                "cuisines": ["Cafe"],
                "price_range": 3,
                "min_rating": 4.0,
                "rating_category": "Excellent",
                "table_booking": "Yes",
            },
        },
    ]

    for sample in samples:
        print("\n" + "=" * 90)
        print(sample["name"])
        print("=" * 90)
        recommendations = recommend_restaurants(
            conn,
            preferences=sample["preferences"],
            top_n=10,
            user_id=None,
            save_history=False,
        )
        print_recommendations(recommendations)
        evaluate_recommendations(recommendations, sample["preferences"])


def evaluate_recommendations(recommendations: pd.DataFrame, preferences: dict) -> None:
    if recommendations.empty:
        return

    preferred_cuisines = [c.lower() for c in preferences.get("cuisines", [])]
    if preferred_cuisines:
        cuisine_matches = recommendations["cuisines"].fillna("").apply(
            lambda value: any(cuisine in value.lower() for cuisine in preferred_cuisines)
        )
        print(f"Cuisine match rate: {cuisine_matches.mean() * 100:.2f}%")

    if preferences.get("city"):
        city_matches = recommendations["city"].fillna("").str.lower() == preferences["city"].lower()
        print(f"City match rate: {city_matches.mean() * 100:.2f}%")

    print(f"Average rating: {recommendations['aggregate_rating'].mean():.2f}")
    print(f"Average score : {recommendations['score'].mean():.2f}")


def build_preferences_from_args(args: argparse.Namespace) -> dict:
    return {
        "cuisines": parse_cuisine_argument(args.cuisines),
        "city": args.city,
        "locality": args.locality,
        "price_range": args.price_range,
        "min_rating": args.min_rating,
        "max_cost": args.max_cost,
        "cost_category": args.cost_category,
        "rating_category": args.rating_category,
        "popularity_category": args.popularity_category,
        "is_expensive": args.is_expensive,
        "location_cluster": args.location_cluster,
        "city_location_cluster": args.city_location_cluster,
        "online_delivery": args.online_delivery,
        "table_booking": args.table_booking,
        "delivering_now": args.delivering_now,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Database-backed content-based restaurant recommendation system."
    )
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="SQLite database path")

    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init-db", help="Create database tables")
    init_parser.set_defaults(handler=lambda conn, args: create_tables(conn))

    import_parser = subparsers.add_parser("import-csv", help="Import restaurants from cleaned CSV")
    import_parser.add_argument("--csv", default=DEFAULT_CSV_PATH, help="Path to cleaned_dataset.csv")
    import_parser.set_defaults(handler=lambda conn, args: import_restaurants(conn, args.csv))

    user_parser = subparsers.add_parser("add-user", help="Create a user")
    user_parser.add_argument("--name", required=True)
    user_parser.add_argument("--email")
    user_parser.set_defaults(handler=lambda conn, args: add_user(conn, args.name, args.email))

    recommend_parser = subparsers.add_parser("recommend", help="Recommend restaurants")
    recommend_parser.add_argument("--user-id", type=int)
    recommend_parser.add_argument("--cuisines", help="Comma-separated cuisines, e.g. North Indian,Chinese")
    recommend_parser.add_argument("--city")
    recommend_parser.add_argument("--locality")
    recommend_parser.add_argument("--price-range", type=int, choices=[1, 2, 3, 4])
    recommend_parser.add_argument("--min-rating", type=float)
    recommend_parser.add_argument("--max-cost", type=float)
    recommend_parser.add_argument("--cost-category", help="Restaurant Cost Category, e.g. Budget, Mid-range, Luxury")
    recommend_parser.add_argument("--rating-category", help="Rating Category, e.g. Good, Excellent")
    recommend_parser.add_argument("--popularity-category", help="Popularity Category, e.g. High, Very High")
    recommend_parser.add_argument("--is-expensive", type=int, choices=[0, 1])
    recommend_parser.add_argument("--location-cluster", type=int)
    recommend_parser.add_argument("--city-location-cluster")
    recommend_parser.add_argument("--online-delivery", choices=["Yes", "No"])
    recommend_parser.add_argument("--table-booking", choices=["Yes", "No"])
    recommend_parser.add_argument("--delivering-now", choices=["Yes", "No"])
    recommend_parser.add_argument("--top-n", type=int, default=10)

    def handle_recommend(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
        preferences = build_preferences_from_args(args)
        if args.user_id:
            save_user_preference(conn, args.user_id, preferences)
        recommendations = recommend_restaurants(
            conn,
            preferences=preferences,
            top_n=args.top_n,
            user_id=args.user_id,
            save_history=True,
        )
        print_recommendations(recommendations)
        evaluate_recommendations(recommendations, preferences)

    recommend_parser.set_defaults(handler=handle_recommend)

    sample_parser = subparsers.add_parser("sample-tests", help="Run sample recommendation tests")
    sample_parser.set_defaults(handler=lambda conn, args: run_sample_tests(conn))

    args = parser.parse_args()
    with connect(args.db) as conn:
        args.handler(conn, args)


if __name__ == "__main__":
    main()
