# Restaurant Intelligence System

An end-to-end restaurant analytics and recommendation project built with machine learning, FastAPI, PostgreSQL, and a React frontend.

## Main Features

- Rating prediction model outputs and reports
- Cuisine classification experiments and saved metrics
- Content-based restaurant recommendation system
- Location-based analysis with maps, city statistics, and cuisine insights
- Role-based workflows for users, admins, and restaurant managers
- Manager menu item creation with dish photo upload
- React dashboard generated from the Figma frontend and connected to the FastAPI backend

## Folder Structure

```text
backend/
  recommendation_backend.py
  requirements.txt

Frontend/
  src/
  dist/
  package.json
  package-lock.json
  index.html

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

uploads/
  menu_items/
```

## Backend Setup

Open PowerShell in the project root:

```powershell
cd D:\Git\Restaurant_Intelligent_System
pip install -r backend\requirements.txt
```

If your PostgreSQL password is not `postgres`, set your database URL first:

```powershell
$env:DATABASE_URL="postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/restaurant_recommendation"
```

Create or update database tables:

```powershell
python backend\recommendation_backend.py create-tables
```

Run the FastAPI backend:

```powershell
python -m uvicorn backend.recommendation_backend:app --reload
```

API docs:

```text
http://127.0.0.1:8000/docs
```

## Frontend Setup

Development mode:

```powershell
cd D:\Git\Restaurant_Intelligent_System\Frontend
npm install
npm run dev
```

Frontend development URL:

```text
http://localhost:5173
```

The login page asks for the FastAPI base URL. Use:

```text
http://127.0.0.1:8000
```

## Build Frontend for Backend Serving

```powershell
cd D:\Git\Restaurant_Intelligent_System\Frontend
npm run build
cd D:\Git\Restaurant_Intelligent_System
python -m uvicorn backend.recommendation_backend:app --reload
```

Then open:

```text
http://127.0.0.1:8000
```

## First-Time App Flow

1. Start PostgreSQL and create the `restaurant_recommendation` database if it does not exist.
2. Run `create-tables`.
3. Start the backend.
4. Open the frontend.
5. Register the first `admin` account.
6. Login as admin and import the dataset.
7. Create users/managers and assign managers to restaurants.

## Role-Based Access

```text
user    - recommendations, analytics, reports
admin   - import dataset, create users, add restaurants, assign managers
manager - edit assigned restaurant and add menu items/photos
```

The backend uses the logged-in user's `user_id` as the `X-User-Id` request header.

## Useful Backend Endpoints

```text
POST /auth/register
POST /auth/login
GET  /users
POST /users
POST /restaurants/import
POST /admin/restaurants
POST /admin/assign-manager
PATCH /manager/restaurants/{restaurant_id}
POST /manager/restaurants/{restaurant_id}/menu-items
POST /recommendations
```

## Location Analysis

```powershell
pip install -r analysis\location\requirements.txt
python analysis\location\restaurant_location_analysis.py --csv "Dataset\cleaned_dataset.csv" --output-dir "analysis\location_results"
```

Generated reports and maps are saved in:

```text
analysis/location_results/
```