# Restaurant Intelligent System

This project contains restaurant analytics, rating model outputs, a recommendation backend, and a static frontend dashboard.

## Folder Structure

```text
backend/
  recommendation_backend.py
  requirements.txt
  .env.example

frontend/
  index.html
  assets/

Dataset/
  cleaned_dataset.csv

analysis/
  location/
  location_results/

ml/
  rating/
  cuisine/
  recommendation/

notebooks/
  Data_Preprocessing.ipynb
```

## Run Backend

```powershell
cd "D:\Git\Restaurant_Intelligent_System"
pip install -r backend\requirements.txt
$env:DATABASE_URL="postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/restaurant_recommendation"
python backend\recommendation_backend.py create-tables
python -m uvicorn backend.recommendation_backend:app --reload
```

Backend API docs:

```text
http://127.0.0.1:8000/docs
```

## Run Frontend

Open another PowerShell window:

```powershell
cd "D:\Git\Restaurant_Intelligent_System"
python -m http.server 5500
```

Frontend URL:

```text
http://127.0.0.1:5500/frontend/index.html
```

## Run Location Analysis

```powershell
pip install -r analysis\location\requirements.txt
python analysis\location\restaurant_location_analysis.py --csv "Dataset\cleaned_dataset.csv" --output-dir "analysis\location_results"
```

## Role-Based Access

The backend uses a simple `X-User-Id` request header.

Roles:

```text
user    - can get recommendations
admin   - can import dataset, add restaurants, assign managers
manager - can edit only the assigned restaurant
```

Create the first admin from `/docs` using `POST /users`:

```json
{
  "name": "Admin",
  "email": "admin@example.com",
  "role": "admin"
}
```

Use the returned `user_id` as `X-User-Id` for admin-only endpoints.

Admin-only:

```text
POST /restaurants/import
POST /admin/restaurants
POST /admin/assign-manager
```

Manager/admin:

```text
PATCH /manager/restaurants/{restaurant_id}
```

In the frontend, enter the logged-in user's ID in the sidebar field named `Logged in user ID`.
