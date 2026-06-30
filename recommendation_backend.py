import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import Depends, FastAPI, Query
from pydantic import BaseModel, Field
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    create_engine,
)
from sqlalchemy.orm import Session, declarative_base, joinedload, relationship, sessionmaker


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/restaurant_recommendation",
)
DATASET_PATH = os.getenv("DATASET_PATH", r"Dataset\cleaned_dataset.csv")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


restaurant_cuisines = Table(
    "restaurant_cuisines",
    Base.metadata,
    Column("restaurant_id", Integer, ForeignKey("restaurants.restaurant_id", ondelete="CASCADE"), primary_key=True),
    Column("cuisine_id", Integer, ForeignKey("cuisines.cuisine_id", ondelete="CASCADE"), primary_key=True),
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class Restaurant(Base):
    __tablename__ = "restaurants"

    restaurant_id = Column(Integer, primary_key=True, index=True)
    restaurant_name = Column(String(500), nullable=False, index=True)
    country_code = Column(Integer)
    city = Column(String(255), index=True)
    address = Column(Text)
    locality = Column(Text)
    longitude = Column(Float)
    latitude = Column(Float)
    average_cost_inr = Column(Float)
    log_average_cost_inr = Column(Float)
    cost_relative_to_city = Column(Float)
    city_wise_cost_category = Column(String(100))
    restaurant_cost_category = Column(String(100), index=True)
    price_range = Column(Integer, index=True)
    aggregate_rating = Column(Float, index=True)
    rating_category = Column(String(100))
    votes = Column(Integer)
    log_votes = Column(Float)
    popularity_category = Column(String(100), index=True)
    restaurant_popularity_score = Column(Float)
    city_restaurant_count = Column(Integer)
    has_table_booking = Column(String(10))
    has_online_delivery = Column(String(10))
    is_delivering_now = Column(String(10))
    is_expensive = Column(Boolean, default=False)
    has_delivery_or_booking = Column(Boolean, default=False)
    location_cluster = Column(Integer, index=True)
    city_location_cluster = Column(String(255), index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    cuisines = relationship("Cuisine", secondary=restaurant_cuisines, back_populates="restaurants")


class Cuisine(Base):
    __tablename__ = "cuisines"

    cuisine_id = Column(Integer, primary_key=True, index=True)
    cuisine_name = Column(String(255), unique=True, nullable=False, index=True)

    restaurants = relationship("Restaurant", secondary=restaurant_cuisines, back_populates="cuisines")


class UserPreference(Base):
    __tablename__ = "user_preferences"

    preference_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    preferred_cuisines = Column(Text)
    preferred_city = Column(String(255))
    preferred_price_range = Column(Integer)
    max_average_cost_inr = Column(Float)
    min_rating = Column(Float)
    preferred_cost_category = Column(String(100))
    preferred_rating_category = Column(String(100))
    preferred_popularity_category = Column(String(100))
    wants_expensive = Column(Boolean)
    preferred_location_cluster = Column(Integer)
    preferred_city_location_cluster = Column(String(255))
    wants_online_delivery = Column(String(10))
    wants_table_booking = Column(String(10))
    wants_delivering_now = Column(String(10))
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class RecommendationHistory(Base):
    __tablename__ = "recommendation_history"

    history_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"))
    restaurant_id = Column(Integer, ForeignKey("restaurants.restaurant_id", ondelete="CASCADE"), nullable=False)
    preferences_json = Column(Text, nullable=False)
    recommendation_score = Column(Float, nullable=False)
    rank = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class UserCreate(BaseModel):
    name: str
    email: str | None = None


class UserResponse(BaseModel):
    user_id: int
    name: str
    email: str | None = None


class RecommendationRequest(BaseModel):
    user_id: int | None = None
    cuisines: list[str] = Field(default_factory=list)
    city: str | None = None
    price_range: int | None = Field(default=None, ge=1, le=4)
    min_rating: float | None = Field(default=None, ge=0, le=5)
    max_cost: float | None = Field(default=None, ge=0)
    cost_category: str | None = None
    rating_category: str | None = None
    popularity_category: str | None = None
    is_expensive: bool | None = None
    location_cluster: int | None = None
    city_location_cluster: str | None = None
    online_delivery: str | None = None
    table_booking: str | None = None
    delivering_now: str | None = None
    top_n: int = Field(default=10, ge=1, le=50)
    save_history: bool = True


class RecommendationItem(BaseModel):
    rank: int
    restaurant_id: int
    restaurant_name: str
    city: str | None
    cuisines: str
    price_range: int | None
    average_cost_inr: float | None
    restaurant_cost_category: str | None
    aggregate_rating: float | None
    rating_category: str | None
    votes: int | None
    popularity_category: str | None
    has_online_delivery: str | None
    has_table_booking: str | None
    is_delivering_now: str | None
    is_expensive: bool | None
    location_cluster: int | None
    city_location_cluster: str | None
    score: float
    match_reasons: str


class RecommendationResponse(BaseModel):
    count: int
    recommendations: list[RecommendationItem]


class ImportResponse(BaseModel):
    restaurants_imported: int
    cuisines_imported: int


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

OPTIONAL_DEFAULTS = {
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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


def split_cuisines(value: str) -> list[str]:
    return [item.strip() for item in str(value).split(",") if item.strip()]


def normalize_yes_no(value: object) -> str:
    return "Yes" if str(value).strip().title() == "Yes" else "No"


def resolve_dataset_path(csv_path: str | None = None) -> Path:
    path = Path(csv_path or DATASET_PATH)
    if path.exists() or path.is_absolute():
        return path
    return Path(__file__).resolve().parent / path


def load_dataset(csv_path: str | None = None) -> pd.DataFrame:
    data = pd.read_csv(resolve_dataset_path(csv_path))
    data.columns = data.columns.str.strip()

    for col, default in OPTIONAL_DEFAULTS.items():
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


def get_or_create_cuisine(db: Session, cuisine_name: str) -> Cuisine:
    cuisine = db.query(Cuisine).filter(Cuisine.cuisine_name == cuisine_name).one_or_none()
    if cuisine is None:
        cuisine = Cuisine(cuisine_name=cuisine_name)
        db.add(cuisine)
        db.flush()
    return cuisine


def import_restaurants_from_csv(db: Session, csv_path: str | None = None) -> tuple[int, int]:
    data = load_dataset(csv_path)
    cuisine_names = set()

    for row in data.to_dict(orient="records"):
        cuisines = split_cuisines(row["Cuisines"])
        cuisine_names.update(cuisines)

        restaurant = db.get(Restaurant, int(row["Restaurant ID"]))
        if restaurant is None:
            restaurant = Restaurant(restaurant_id=int(row["Restaurant ID"]))
            db.add(restaurant)

        restaurant.restaurant_name = row["Restaurant Name"]
        restaurant.country_code = int(row["Country Code"])
        restaurant.city = row["City"]
        restaurant.address = row["Address"]
        restaurant.locality = row["Locality"]
        restaurant.longitude = float(row["Longitude"]) if pd.notna(row["Longitude"]) else None
        restaurant.latitude = float(row["Latitude"]) if pd.notna(row["Latitude"]) else None
        restaurant.average_cost_inr = float(row["Average Cost INR"])
        restaurant.log_average_cost_inr = float(row["Log Average Cost INR"])
        restaurant.cost_relative_to_city = float(row["Cost Relative To City"])
        restaurant.city_wise_cost_category = row["City wise Cost Category"]
        restaurant.restaurant_cost_category = row["Restaurant Cost Category"]
        restaurant.price_range = int(row["Price range"])
        restaurant.aggregate_rating = float(row["Aggregate rating"])
        restaurant.rating_category = row["Rating Category"]
        restaurant.votes = int(row["Votes"])
        restaurant.log_votes = float(row["Log Votes"])
        restaurant.popularity_category = row["Popularity Category"]
        restaurant.restaurant_popularity_score = float(row["Restaurant Popularity Score"])
        restaurant.city_restaurant_count = int(row["City Restaurant Count"])
        restaurant.has_table_booking = row["Has Table booking"]
        restaurant.has_online_delivery = row["Has Online delivery"]
        restaurant.is_delivering_now = row["Is delivering now"]
        restaurant.is_expensive = bool(int(row["Is Expensive"]))
        restaurant.has_delivery_or_booking = bool(int(row["Has Delivery Or Booking"]))
        restaurant.location_cluster = int(row["Location Cluster"])
        restaurant.city_location_cluster = row["City Location Cluster"]
        restaurant.cuisines = [get_or_create_cuisine(db, cuisine) for cuisine in cuisines]

    db.commit()
    return len(data), len(cuisine_names)


def restaurants_to_frame(restaurants: list[Restaurant]) -> pd.DataFrame:
    rows = []
    for restaurant in restaurants:
        rows.append(
            {
                "restaurant_id": restaurant.restaurant_id,
                "restaurant_name": restaurant.restaurant_name,
                "city": restaurant.city,
                "cuisines": ", ".join(sorted(c.cuisine_name for c in restaurant.cuisines)),
                "price_range": restaurant.price_range,
                "average_cost_inr": restaurant.average_cost_inr,
                "restaurant_cost_category": restaurant.restaurant_cost_category,
                "aggregate_rating": restaurant.aggregate_rating,
                "rating_category": restaurant.rating_category,
                "votes": restaurant.votes,
                "log_votes": restaurant.log_votes,
                "popularity_category": restaurant.popularity_category,
                "restaurant_popularity_score": restaurant.restaurant_popularity_score,
                "has_online_delivery": restaurant.has_online_delivery,
                "has_table_booking": restaurant.has_table_booking,
                "is_delivering_now": restaurant.is_delivering_now,
                "is_expensive": restaurant.is_expensive,
                "location_cluster": restaurant.location_cluster,
                "city_location_cluster": restaurant.city_location_cluster,
                "cost_relative_to_city": restaurant.cost_relative_to_city,
            }
        )
    return pd.DataFrame(rows)


def score_recommendations(data: pd.DataFrame, request: RecommendationRequest) -> pd.DataFrame:
    scored = data.copy()
    scored["score"] = 0.0
    scored["match_reasons"] = ""

    preferred_cuisines = [c.lower() for c in request.cuisines]
    if preferred_cuisines:
        cuisine_sets = scored["cuisines"].fillna("").apply(
            lambda value: {c.strip().lower() for c in str(value).split(",") if c.strip()}
        )
        cuisine_ratio = cuisine_sets.apply(
            lambda cuisines: len(cuisines.intersection(preferred_cuisines)) / len(preferred_cuisines)
        )
        scored["score"] += cuisine_ratio * 40
        scored.loc[cuisine_ratio > 0, "match_reasons"] += "cuisine match; "

    if request.city:
        match = scored["city"].fillna("").str.lower() == request.city.lower()
        scored["score"] += match.astype(float) * 20
        scored.loc[match, "match_reasons"] += "city match; "

    if request.price_range is not None:
        distance = (scored["price_range"].fillna(request.price_range) - request.price_range).abs()
        scored["score"] += (1 - (distance / 3).clip(0, 1)) * 12
        scored.loc[distance == 0, "match_reasons"] += "price match; "

    if request.min_rating is not None:
        scored = scored.loc[scored["aggregate_rating"].fillna(0) >= request.min_rating].copy()
        scored["match_reasons"] += f"rating >= {request.min_rating}; "

    if scored.empty:
        return scored

    scored["score"] += (scored["aggregate_rating"].fillna(0).clip(0, 5) / 5) * 12

    if request.max_cost is not None:
        cost = scored["average_cost_inr"].fillna(request.max_cost)
        scored["score"] += (1 - ((cost - request.max_cost).clip(lower=0) / max(request.max_cost, 1)).clip(0, 1)) * 8
        scored.loc[cost <= request.max_cost, "match_reasons"] += "within budget; "

    category_matches = [
        ("restaurant_cost_category", request.cost_category, 8, "cost category match; "),
        ("rating_category", request.rating_category, 6, "rating category match; "),
        ("popularity_category", request.popularity_category, 6, "popularity category match; "),
        ("city_location_cluster", request.city_location_cluster, 8, "city-location cluster match; "),
    ]
    for column, value, weight, reason in category_matches:
        if value:
            match = scored[column].fillna("").str.lower() == value.lower()
            scored["score"] += match.astype(float) * weight
            scored.loc[match, "match_reasons"] += reason

    if request.is_expensive is not None:
        match = scored["is_expensive"].fillna(False).astype(bool) == request.is_expensive
        scored["score"] += match.astype(float) * 4
        scored.loc[match, "match_reasons"] += "expensive preference match; "

    if request.location_cluster is not None:
        match = scored["location_cluster"].fillna(-1).astype(int) == request.location_cluster
        scored["score"] += match.astype(float) * 8
        scored.loc[match, "match_reasons"] += "location cluster match; "

    yes_no_matches = [
        ("has_online_delivery", request.online_delivery, 5, "delivery match; "),
        ("has_table_booking", request.table_booking, 5, "booking match; "),
        ("is_delivering_now", request.delivering_now, 3, "currently delivering match; "),
    ]
    for column, value, weight, reason in yes_no_matches:
        if value:
            match = scored[column].fillna("").str.lower() == value.lower()
            scored["score"] += match.astype(float) * weight
            scored.loc[match, "match_reasons"] += reason

    if scored["log_votes"].fillna(0).max() > 0:
        scored["score"] += (scored["log_votes"].fillna(0) / scored["log_votes"].fillna(0).max()) * 6

    if scored["restaurant_popularity_score"].fillna(0).max() > 0:
        scored["score"] += (
            scored["restaurant_popularity_score"].fillna(0)
            / scored["restaurant_popularity_score"].fillna(0).max()
        ) * 6

    cost_relative = scored["cost_relative_to_city"].fillna(1.0)
    scored["score"] += (1 - (cost_relative - 1).abs().clip(0, 1)) * 2

    scored = scored.sort_values(["score", "aggregate_rating", "votes"], ascending=[False, False, False])
    scored = scored.reset_index(drop=True)
    scored["rank"] = scored.index + 1
    return scored


def save_request_data(db: Session, request: RecommendationRequest, items: list[RecommendationItem]) -> None:
    if request.user_id is not None:
        db.add(
            UserPreference(
                user_id=request.user_id,
                preferred_cuisines=", ".join(request.cuisines),
                preferred_city=request.city,
                preferred_price_range=request.price_range,
                max_average_cost_inr=request.max_cost,
                min_rating=request.min_rating,
                preferred_cost_category=request.cost_category,
                preferred_rating_category=request.rating_category,
                preferred_popularity_category=request.popularity_category,
                wants_expensive=request.is_expensive,
                preferred_location_cluster=request.location_cluster,
                preferred_city_location_cluster=request.city_location_cluster,
                wants_online_delivery=request.online_delivery,
                wants_table_booking=request.table_booking,
                wants_delivering_now=request.delivering_now,
            )
        )

    if request.save_history:
        preferences_json = json.dumps(request.dict(), ensure_ascii=True)
        for item in items:
            db.add(
                RecommendationHistory(
                    user_id=request.user_id,
                    restaurant_id=item.restaurant_id,
                    preferences_json=preferences_json,
                    recommendation_score=item.score,
                    rank=item.rank,
                )
            )
    db.commit()


def recommend(db: Session, request: RecommendationRequest) -> list[RecommendationItem]:
    restaurants = db.query(Restaurant).options(joinedload(Restaurant.cuisines)).all()
    data = restaurants_to_frame(restaurants)
    if data.empty:
        return []

    scored = score_recommendations(data, request).head(request.top_n)
    items = [
        RecommendationItem(
            rank=int(row["rank"]),
            restaurant_id=int(row["restaurant_id"]),
            restaurant_name=row["restaurant_name"],
            city=row["city"],
            cuisines=row["cuisines"],
            price_range=None if pd.isna(row["price_range"]) else int(row["price_range"]),
            average_cost_inr=None if pd.isna(row["average_cost_inr"]) else float(row["average_cost_inr"]),
            restaurant_cost_category=row["restaurant_cost_category"],
            aggregate_rating=None if pd.isna(row["aggregate_rating"]) else float(row["aggregate_rating"]),
            rating_category=row["rating_category"],
            votes=None if pd.isna(row["votes"]) else int(row["votes"]),
            popularity_category=row["popularity_category"],
            has_online_delivery=row["has_online_delivery"],
            has_table_booking=row["has_table_booking"],
            is_delivering_now=row["is_delivering_now"],
            is_expensive=bool(row["is_expensive"]),
            location_cluster=None if pd.isna(row["location_cluster"]) else int(row["location_cluster"]),
            city_location_cluster=row["city_location_cluster"],
            score=round(float(row["score"]), 4),
            match_reasons=row["match_reasons"],
        )
        for _, row in scored.iterrows()
    ]
    save_request_data(db, request, items)
    return items


app = FastAPI(title="Restaurant Recommendation API")


@app.on_event("startup")
def on_startup() -> None:
    create_tables()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/users", response_model=UserResponse)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> UserResponse:
    user = User(name=payload.name, email=payload.email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse(user_id=user.user_id, name=user.name, email=user.email)


@app.post("/restaurants/import", response_model=ImportResponse)
def import_restaurants(
    csv_path: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> ImportResponse:
    restaurants_imported, cuisines_imported = import_restaurants_from_csv(db, csv_path)
    return ImportResponse(restaurants_imported=restaurants_imported, cuisines_imported=cuisines_imported)


@app.post("/recommendations", response_model=RecommendationResponse)
def create_recommendations(
    payload: RecommendationRequest,
    db: Session = Depends(get_db),
) -> RecommendationResponse:
    items = recommend(db, payload)
    return RecommendationResponse(count=len(items), recommendations=items)


def cli() -> None:
    parser = argparse.ArgumentParser(description="Restaurant recommendation backend utilities.")
    parser.add_argument("command", choices=["create-tables", "import-csv"])
    parser.add_argument("--csv", default=None, help="Path to cleaned_dataset.csv")
    args = parser.parse_args()

    create_tables()
    if args.command == "import-csv":
        with SessionLocal() as db:
            restaurants_imported, cuisines_imported = import_restaurants_from_csv(db, args.csv)
        print(f"Imported {restaurants_imported} restaurants and {cuisines_imported} cuisines.")
    else:
        print("Database tables created.")


if __name__ == "__main__":
    cli()
