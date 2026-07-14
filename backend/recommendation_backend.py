import argparse
import base64
import csv
import hashlib
import hmac
import json
import os
import secrets
import shutil
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
import pandas as pd
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
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
    inspect,
    text as sql_text,
)
from sqlalchemy.orm import Session, declarative_base, joinedload, relationship, sessionmaker


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/restaurant_recommendation",
)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = os.getenv("DATASET_PATH", str(PROJECT_ROOT / "Dataset" / "cleaned_dataset.csv"))
ADMIN_ADDED_RESTAURANTS_PATH = Path(
    os.getenv("ADMIN_ADDED_RESTAURANTS_PATH", str(PROJECT_ROOT / "Dataset" / "admin_added_restaurants.csv"))
)
ADMIN_ADDED_RESTAURANTS_XLSX_PATH = Path(
    os.getenv("ADMIN_ADDED_RESTAURANTS_XLSX_PATH", str(PROJECT_ROOT / "Dataset" / "admin_added_restaurants.xlsx"))
)
FIGMA_FRONTEND_DIR = PROJECT_ROOT / "Frontend"
DEFAULT_FRONTEND_DIR = FIGMA_FRONTEND_DIR
FRONTEND_DIR = Path(os.getenv("FRONTEND_DIR", str(DEFAULT_FRONTEND_DIR)))
FRONTEND_DIST_DIR = FRONTEND_DIR / "dist"
FRONTEND_ASSETS_DIR = FRONTEND_DIR / "assets"
FRONTEND_DIST_ASSETS_DIR = FRONTEND_DIST_DIR / "assets"
ML_DIR = PROJECT_ROOT / "ml"
ANALYSIS_DIR = PROJECT_ROOT / "analysis"
UPLOADS_DIR = PROJECT_ROOT / "uploads"
MENU_UPLOADS_DIR = UPLOADS_DIR / "menu_items"

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
    password_hash = Column(String(500), nullable=True)
    role = Column(String(30), nullable=False, default="user")
    managed_restaurant_id = Column(Integer, nullable=True)
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


class MenuItem(Base):
    __tablename__ = "menu_items"

    menu_item_id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.restaurant_id", ondelete="CASCADE"), nullable=False, index=True)
    item_name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100))
    price_inr = Column(Float)
    is_available = Column(Boolean, default=True)
    photo_url = Column(Text)
    created_by_user_id = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class UserCreate(BaseModel):
    name: str
    email: str
    password: str = Field(min_length=6)
    role: str = "user"
    managed_restaurant_id: int | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    user_id: int
    name: str
    email: str | None = None
    role: str
    managed_restaurant_id: int | None = None


class AssignManagerRequest(BaseModel):
    manager_user_id: int
    restaurant_id: int


class RestaurantMutationRequest(BaseModel):
    restaurant_id: int | None = None
    restaurant_name: str
    city: str | None = None
    address: str | None = None
    locality: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    cuisines: list[str] = Field(default_factory=list)
    average_cost_inr: float | None = None
    price_range: int | None = Field(default=None, ge=1, le=4)
    aggregate_rating: float | None = Field(default=None, ge=0, le=5)
    votes: int | None = Field(default=None, ge=0)
    has_table_booking: str | None = None
    has_online_delivery: str | None = None
    is_delivering_now: str | None = None
    restaurant_cost_category: str | None = None
    rating_category: str | None = None
    popularity_category: str | None = None
    is_expensive: bool | None = None
    location_cluster: int | None = None
    city_location_cluster: str | None = None


class RestaurantResponse(BaseModel):
    restaurant_id: int
    restaurant_name: str
    city: str | None = None
    cuisines: list[str] = Field(default_factory=list)
    message: str


class MenuItemResponse(BaseModel):
    menu_item_id: int
    restaurant_id: int
    item_name: str
    description: str | None = None
    category: str | None = None
    price_inr: float | None = None
    is_available: bool
    photo_url: str | None = None
    message: str


class RecommendationRequest(BaseModel):
    user_id: int | None = None
    cuisines: list[str] = Field(default_factory=list)
    city: str | None = None
    cities: list[str] = Field(default_factory=list)
    price_range: int | None = Field(default=None, ge=1, le=4)
    min_rating: float | None = Field(default=None, ge=0, le=5)
    max_cost: float | None = Field(default=None, ge=0)
    min_votes: int | None = Field(default=None, ge=0)
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


class RecommendationMetadataResponse(BaseModel):
    cuisines: list[str]
    cities: list[str]
    cost_categories: list[str]
    restaurant_count: int
    cuisine_count: int
    city_count: int
    admin_added_count: int


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


def normalize_role(role: str) -> str:
    role = (role or "user").strip().lower()
    if role not in {"user", "admin", "manager"}:
        raise HTTPException(status_code=400, detail="role must be one of: user, admin, manager")
    return role


def normalize_email(email: str) -> str:
    email = (email or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    return email


def hash_password(password: str) -> str:
    if len(password or "") < 6:
        raise HTTPException(status_code=400, detail="Password must contain at least 6 characters")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    salt_text = base64.b64encode(salt).decode("ascii")
    digest_text = base64.b64encode(digest).decode("ascii")
    return f"pbkdf2_sha256$120000${salt_text}${digest_text}"


def verify_password(password: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False
    try:
        algorithm, iterations_text, salt_text, digest_text = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_text.encode("ascii"))
        expected = base64.b64decode(digest_text.encode("ascii"))
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations_text))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def ensure_admin_rule(db: Session, role: str, existing_user_id: int | None = None) -> None:
    if role != "admin":
        return
    query = db.query(User).filter(User.role == "admin")
    if existing_user_id is not None:
        query = query.filter(User.user_id != existing_user_id)
    if query.first() is not None:
        raise HTTPException(status_code=409, detail="Only one admin account is allowed")


def get_current_user(
    x_user_id: int | None = Header(default=None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> User:
    if x_user_id is None:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")
    user = db.get(User, x_user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid X-User-Id")
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def require_admin_or_assigned_manager(
    restaurant_id: int,
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role == "admin":
        return current_user
    if current_user.role == "manager" and current_user.managed_restaurant_id == restaurant_id:
        return current_user
    raise HTTPException(status_code=403, detail="You can only edit your assigned restaurant")


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    with engine.begin() as conn:
        if "password_hash" not in user_columns:
            conn.execute(sql_text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(500)"))
        if "role" not in user_columns:
            conn.execute(sql_text("ALTER TABLE users ADD COLUMN role VARCHAR(30) NOT NULL DEFAULT 'user'"))
        if "managed_restaurant_id" not in user_columns:
            conn.execute(sql_text("ALTER TABLE users ADD COLUMN managed_restaurant_id INTEGER"))


def delete_all_users() -> int:
    create_tables()
    with SessionLocal() as db:
        count = db.query(User).count()
        db.query(UserPreference).delete(synchronize_session=False)
        db.query(RecommendationHistory).update({RecommendationHistory.user_id: None}, synchronize_session=False)
        db.query(User).delete(synchronize_session=False)
        db.commit()
    return count


def split_cuisines(value: str) -> list[str]:
    return [item.strip() for item in str(value).split(",") if item.strip()]


def normalize_yes_no(value: object) -> str:
    return "Yes" if str(value).strip().title() == "Yes" else "No"


def resolve_dataset_path(csv_path: str | None = None) -> Path:
    path = Path(csv_path or DATASET_PATH)
    if path.exists() or path.is_absolute():
        return path
    return PROJECT_ROOT / path


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


def apply_restaurant_payload(db: Session, restaurant: Restaurant, payload: RestaurantMutationRequest) -> Restaurant:
    restaurant.restaurant_name = payload.restaurant_name
    restaurant.city = payload.city
    restaurant.address = payload.address
    restaurant.locality = payload.locality
    restaurant.latitude = payload.latitude
    restaurant.longitude = payload.longitude
    restaurant.average_cost_inr = payload.average_cost_inr
    restaurant.log_average_cost_inr = np.log1p(payload.average_cost_inr or 0)
    restaurant.price_range = payload.price_range
    restaurant.aggregate_rating = payload.aggregate_rating or 0
    restaurant.votes = payload.votes or 0
    restaurant.log_votes = np.log1p(payload.votes or 0)
    restaurant.has_table_booking = normalize_yes_no(payload.has_table_booking or "No")
    restaurant.has_online_delivery = normalize_yes_no(payload.has_online_delivery or "No")
    restaurant.is_delivering_now = normalize_yes_no(payload.is_delivering_now or "No")
    restaurant.restaurant_cost_category = payload.restaurant_cost_category or "Unknown"
    restaurant.rating_category = payload.rating_category or "Unknown"
    restaurant.popularity_category = payload.popularity_category or "Unknown"
    restaurant.restaurant_popularity_score = float(payload.votes or 0)
    restaurant.city_restaurant_count = 0
    restaurant.is_expensive = bool(payload.is_expensive)
    restaurant.has_delivery_or_booking = restaurant.has_online_delivery == "Yes" or restaurant.has_table_booking == "Yes"
    restaurant.location_cluster = payload.location_cluster if payload.location_cluster is not None else -1
    restaurant.city_location_cluster = payload.city_location_cluster or "Unknown"
    restaurant.cost_relative_to_city = 1.0
    restaurant.city_wise_cost_category = payload.restaurant_cost_category or "Unknown"

    if payload.cuisines:
        restaurant.cuisines = [get_or_create_cuisine(db, cuisine.strip()) for cuisine in payload.cuisines if cuisine.strip()]

    return restaurant


def append_admin_added_restaurant_export(restaurant: Restaurant) -> None:
    ADMIN_ADDED_RESTAURANTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    file_exists = ADMIN_ADDED_RESTAURANTS_PATH.exists()
    fieldnames = [
        "Restaurant ID",
        "Restaurant Name",
        "City",
        "Locality",
        "Address",
        "Cuisines",
        "Average Cost INR",
        "Price range",
        "Aggregate rating",
        "Votes",
        "Has Online delivery",
        "Has Table booking",
        "Created At",
    ]
    row = {
        "Restaurant ID": restaurant.restaurant_id,
        "Restaurant Name": restaurant.restaurant_name,
        "City": restaurant.city or "",
        "Locality": restaurant.locality or "",
        "Address": restaurant.address or "",
        "Cuisines": ", ".join(cuisine.cuisine_name for cuisine in restaurant.cuisines),
        "Average Cost INR": restaurant.average_cost_inr if restaurant.average_cost_inr is not None else "",
        "Price range": restaurant.price_range if restaurant.price_range is not None else "",
        "Aggregate rating": restaurant.aggregate_rating if restaurant.aggregate_rating is not None else "",
        "Votes": restaurant.votes if restaurant.votes is not None else "",
        "Has Online delivery": restaurant.has_online_delivery or "",
        "Has Table booking": restaurant.has_table_booking or "",
        "Created At": restaurant.created_at.isoformat() if restaurant.created_at else utc_now().isoformat(),
    }
    with ADMIN_ADDED_RESTAURANTS_PATH.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
    write_admin_added_restaurants_workbook(fieldnames)


def write_admin_added_restaurants_workbook(fieldnames: list[str]) -> None:
    if not ADMIN_ADDED_RESTAURANTS_PATH.exists():
        return
    with ADMIN_ADDED_RESTAURANTS_PATH.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    def cell(value: object) -> str:
        return f'<c t="inlineStr"><is><t>{escape(str(value or ""))}</t></is></c>'

    sheet_rows = [
        f'<row r="1">{"".join(cell(name) for name in fieldnames)}</row>'
    ]
    for row_index, row in enumerate(rows, start=2):
        sheet_rows.append(f'<row r="{row_index}">{"".join(cell(row.get(name, "")) for name in fieldnames)}</row>')

    worksheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(sheet_rows)}</sheetData>'
        '</worksheet>'
    )
    ADMIN_ADDED_RESTAURANTS_XLSX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ADMIN_ADDED_RESTAURANTS_XLSX_PATH, "w", zipfile.ZIP_DEFLATED) as workbook:
        workbook.writestr("[Content_Types].xml", (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '</Types>'
        ))
        workbook.writestr("_rels/.rels", (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>'
        ))
        workbook.writestr("xl/workbook.xml", (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Admin Added Restaurants" sheetId="1" r:id="rId1"/></sheets>'
            '</workbook>'
        ))
        workbook.writestr("xl/_rels/workbook.xml.rels", (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '</Relationships>'
        ))
        workbook.writestr("xl/worksheets/sheet1.xml", worksheet)


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
    cuisine_sets = scored["cuisines"].fillna("").apply(
        lambda value: {c.strip().lower() for c in str(value).split(",") if c.strip()}
    )

    if preferred_cuisines:
        cuisine_match = cuisine_sets.apply(lambda cuisines: bool(cuisines.intersection(preferred_cuisines)))
        scored = scored.loc[cuisine_match].copy()
        cuisine_sets = cuisine_sets.loc[scored.index]
        if scored.empty:
            return scored

        cuisine_ratio = cuisine_sets.apply(
            lambda cuisines: len(cuisines.intersection(preferred_cuisines)) / len(preferred_cuisines)
        )
        scored["score"] += cuisine_ratio * 40
        scored.loc[cuisine_ratio > 0, "match_reasons"] += "cuisine match; "

    preferred_cities = [city.lower() for city in request.cities if city.strip()]
    if request.city and not preferred_cities:
        preferred_cities = [request.city.lower()]

    if preferred_cities:
        match = scored["city"].fillna("").str.lower().isin(preferred_cities)
        scored = scored.loc[match].copy()
        if scored.empty:
            return scored
        scored["score"] += 20
        scored["match_reasons"] += "city match; "

    if request.price_range is not None:
        distance = (scored["price_range"].fillna(request.price_range) - request.price_range).abs()
        scored = scored.loc[distance == 0].copy()
        if scored.empty:
            return scored
        scored["score"] += 12
        scored["match_reasons"] += "price match; "

    if request.min_rating is not None:
        scored = scored.loc[scored["aggregate_rating"].fillna(0) >= request.min_rating].copy()
        scored["match_reasons"] += f"rating >= {request.min_rating}; "

    if scored.empty:
        return scored

    scored["score"] += (scored["aggregate_rating"].fillna(0).clip(0, 5) / 5) * 12

    if request.max_cost is not None:
        cost = scored["average_cost_inr"].fillna(request.max_cost)
        scored = scored.loc[cost <= request.max_cost].copy()
        if scored.empty:
            return scored
        cost = scored["average_cost_inr"].fillna(request.max_cost)
        scored["score"] += (1 - ((cost - request.max_cost).clip(lower=0) / max(request.max_cost, 1)).clip(0, 1)) * 8
        scored["match_reasons"] += "within budget; "

    if request.min_votes is not None:
        scored = scored.loc[scored["votes"].fillna(0) >= request.min_votes].copy()
        if scored.empty:
            return scored
        scored["match_reasons"] += f"votes >= {request.min_votes}; "

    category_matches = [
        ("restaurant_cost_category", request.cost_category, 8, "cost category match; "),
        ("rating_category", request.rating_category, 6, "rating category match; "),
        ("popularity_category", request.popularity_category, 6, "popularity category match; "),
        ("city_location_cluster", request.city_location_cluster, 8, "city-location cluster match; "),
    ]
    for column, value, weight, reason in category_matches:
        if value:
            match = scored[column].fillna("").str.lower() == value.lower()
            scored = scored.loc[match].copy()
            if scored.empty:
                return scored
            scored["score"] += weight
            scored["match_reasons"] += reason

    if request.is_expensive is not None:
        match = scored["is_expensive"].fillna(False).astype(bool) == request.is_expensive
        scored = scored.loc[match].copy()
        if scored.empty:
            return scored
        scored["score"] += 4
        scored["match_reasons"] += "expensive preference match; "

    if request.location_cluster is not None:
        match = scored["location_cluster"].fillna(-1).astype(int) == request.location_cluster
        scored = scored.loc[match].copy()
        if scored.empty:
            return scored
        scored["score"] += 8
        scored["match_reasons"] += "location cluster match; "

    yes_no_matches = [
        ("has_online_delivery", request.online_delivery, 5, "delivery match; "),
        ("has_table_booking", request.table_booking, 5, "booking match; "),
        ("is_delivering_now", request.delivering_now, 3, "currently delivering match; "),
    ]
    for column, value, weight, reason in yes_no_matches:
        if value:
            match = scored[column].fillna("").str.lower() == value.lower()
            scored = scored.loc[match].copy()
            if scored.empty:
                return scored
            scored["score"] += weight
            scored["match_reasons"] += reason

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
                preferred_city=", ".join(request.cities) if request.cities else request.city,
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

if FRONTEND_DIST_ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST_ASSETS_DIR)), name="assets")
elif FRONTEND_ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_ASSETS_DIR)), name="assets")
if ML_DIR.exists():
    app.mount("/ml", StaticFiles(directory=str(ML_DIR)), name="ml")
if ANALYSIS_DIR.exists():
    app.mount("/analysis", StaticFiles(directory=str(ANALYSIS_DIR)), name="analysis")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
MENU_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")


@app.on_event("startup")
def on_startup() -> None:
    create_tables()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def frontend_index() -> FileResponse:
    index_path = FRONTEND_DIST_DIR / "index.html"
    if not index_path.exists():
        index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend index.html not found")
    response = FileResponse(index_path)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


def to_user_response(user: User) -> UserResponse:
    return UserResponse(
        user_id=user.user_id,
        name=user.name,
        email=user.email,
        role=user.role,
        managed_restaurant_id=user.managed_restaurant_id,
    )


def create_user_record(db: Session, payload: UserCreate) -> User:
    role = normalize_role(payload.role)
    email = normalize_email(payload.email)
    ensure_admin_rule(db, role)
    if db.query(User).filter(User.email == email).first() is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        name=payload.name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
        role=role,
        managed_restaurant_id=payload.managed_restaurant_id if role == "manager" else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/register", response_model=UserResponse)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> UserResponse:
    user = create_user_record(db, payload)
    return to_user_response(user)


@app.post("/auth/login", response_model=UserResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> UserResponse:
    email = normalize_email(payload.email)
    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return to_user_response(user)


@app.post("/users", response_model=UserResponse)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> UserResponse:
    user = create_user_record(db, payload)
    return to_user_response(user)


@app.get("/users", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[UserResponse]:
    users = db.query(User).order_by(User.user_id.asc()).all()
    return [to_user_response(user) for user in users]


@app.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return to_user_response(current_user)


@app.get("/metadata/recommendations", response_model=RecommendationMetadataResponse)
def recommendation_metadata(db: Session = Depends(get_db)) -> RecommendationMetadataResponse:
    cuisines = [
        row[0]
        for row in db.query(Cuisine.cuisine_name)
        .order_by(Cuisine.cuisine_name.asc())
        .all()
        if row[0] and row[0].strip()
    ]
    cities = [
        row[0]
        for row in db.query(Restaurant.city)
        .filter(Restaurant.city.isnot(None))
        .distinct()
        .order_by(Restaurant.city.asc())
        .all()
        if row[0] and row[0].strip()
    ]
    cost_categories = [
        row[0]
        for row in db.query(Restaurant.restaurant_cost_category)
        .filter(Restaurant.restaurant_cost_category.isnot(None))
        .distinct()
        .order_by(Restaurant.restaurant_cost_category.asc())
        .all()
        if row[0] and row[0].strip() and row[0].strip().lower() != "unknown"
    ]
    admin_added_count = 0
    if ADMIN_ADDED_RESTAURANTS_PATH.exists():
        try:
            with ADMIN_ADDED_RESTAURANTS_PATH.open("r", newline="", encoding="utf-8") as handle:
                admin_added_count = max(sum(1 for _ in handle) - 1, 0)
        except OSError:
            admin_added_count = 0
    return RecommendationMetadataResponse(
        cuisines=cuisines,
        cities=cities,
        cost_categories=cost_categories,
        restaurant_count=db.query(Restaurant).count(),
        cuisine_count=len(cuisines),
        city_count=len(cities),
        admin_added_count=admin_added_count,
    )


@app.post("/restaurants/import", response_model=ImportResponse)
def import_restaurants(
    csv_path: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> ImportResponse:
    restaurants_imported, cuisines_imported = import_restaurants_from_csv(db, csv_path)
    return ImportResponse(restaurants_imported=restaurants_imported, cuisines_imported=cuisines_imported)


@app.post("/admin/assign-manager", response_model=UserResponse)
def assign_restaurant_manager(
    payload: AssignManagerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> UserResponse:
    manager = db.get(User, payload.manager_user_id)
    if manager is None:
        raise HTTPException(status_code=404, detail="Manager user not found")

    restaurant = db.get(Restaurant, payload.restaurant_id)
    if restaurant is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    manager.role = "manager"
    manager.managed_restaurant_id = payload.restaurant_id
    db.commit()
    db.refresh(manager)

    return to_user_response(manager)


@app.post("/admin/restaurants", response_model=RestaurantResponse)
def create_restaurant(
    payload: RestaurantMutationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> RestaurantResponse:
    restaurant_id = payload.restaurant_id
    if restaurant_id is None:
        max_restaurant = db.query(Restaurant).order_by(Restaurant.restaurant_id.desc()).first()
        restaurant_id = (max_restaurant.restaurant_id + 1) if max_restaurant else 1

    if db.get(Restaurant, restaurant_id) is not None:
        raise HTTPException(status_code=409, detail="Restaurant ID already exists")

    restaurant = Restaurant(restaurant_id=restaurant_id)
    apply_restaurant_payload(db, restaurant, payload)
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)
    try:
        append_admin_added_restaurant_export(restaurant)
    except OSError as exc:
        print(f"Admin restaurant export failed for restaurant {restaurant.restaurant_id}: {exc}")

    return RestaurantResponse(
        restaurant_id=restaurant.restaurant_id,
        restaurant_name=restaurant.restaurant_name,
        city=restaurant.city,
        cuisines=[cuisine.cuisine_name for cuisine in restaurant.cuisines],
        message="Restaurant created by admin",
    )


@app.patch("/manager/restaurants/{restaurant_id}", response_model=RestaurantResponse)
def update_assigned_restaurant(
    restaurant_id: int,
    payload: RestaurantMutationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_assigned_manager),
) -> RestaurantResponse:
    restaurant = db.get(Restaurant, restaurant_id)
    if restaurant is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    apply_restaurant_payload(db, restaurant, payload)
    db.commit()
    db.refresh(restaurant)

    return RestaurantResponse(
        restaurant_id=restaurant.restaurant_id,
        restaurant_name=restaurant.restaurant_name,
        city=restaurant.city,
        cuisines=[cuisine.cuisine_name for cuisine in restaurant.cuisines],
        message="Restaurant updated",
    )


def save_menu_photo(photo: UploadFile | None) -> str | None:
    if photo is None or not photo.filename:
        return None
    content_type = (photo.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Menu photo must be an image")
    suffix = Path(photo.filename).suffix.lower() or ".jpg"
    filename = f"{uuid.uuid4().hex}{suffix}"
    destination = MENU_UPLOADS_DIR / filename
    with destination.open("wb") as buffer:
        shutil.copyfileobj(photo.file, buffer)
    return f"/uploads/menu_items/{filename}"


@app.post("/manager/restaurants/{restaurant_id}/menu-items", response_model=MenuItemResponse)
def create_menu_item(
    restaurant_id: int,
    item_name: str = Form(...),
    description: str | None = Form(default=None),
    category: str | None = Form(default=None),
    price_inr: float | None = Form(default=None),
    is_available: bool = Form(default=True),
    photo: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_assigned_manager),
) -> MenuItemResponse:
    restaurant = db.get(Restaurant, restaurant_id)
    if restaurant is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    menu_item = MenuItem(
        restaurant_id=restaurant_id,
        item_name=item_name.strip(),
        description=description,
        category=category,
        price_inr=price_inr,
        is_available=is_available,
        photo_url=save_menu_photo(photo),
        created_by_user_id=current_user.user_id,
    )
    db.add(menu_item)
    db.commit()
    db.refresh(menu_item)

    return MenuItemResponse(
        menu_item_id=menu_item.menu_item_id,
        restaurant_id=menu_item.restaurant_id,
        item_name=menu_item.item_name,
        description=menu_item.description,
        category=menu_item.category,
        price_inr=menu_item.price_inr,
        is_available=menu_item.is_available,
        photo_url=menu_item.photo_url,
        message="Menu item created",
    )


@app.post("/recommendations", response_model=RecommendationResponse)
def create_recommendations(
    payload: RecommendationRequest,
    db: Session = Depends(get_db),
) -> RecommendationResponse:
    items = recommend(db, payload)
    return RecommendationResponse(count=len(items), recommendations=items)


def cli() -> None:
    parser = argparse.ArgumentParser(description="Restaurant recommendation backend utilities.")
    parser.add_argument("command", choices=["create-tables", "import-csv", "clear-users"])
    parser.add_argument("--csv", default=None, help="Path to cleaned_dataset.csv")
    args = parser.parse_args()

    create_tables()
    if args.command == "import-csv":
        with SessionLocal() as db:
            restaurants_imported, cuisines_imported = import_restaurants_from_csv(db, args.csv)
        print(f"Imported {restaurants_imported} restaurants and {cuisines_imported} cuisines.")
    elif args.command == "clear-users":
        deleted_count = delete_all_users()
        print(f"Deleted {deleted_count} users.")
    else:
        print("Database tables created.")


if __name__ == "__main__":
    cli()
