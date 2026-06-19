import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from catboost import CatBoostRegressor, Pool
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


TARGET_COLUMN = "Aggregate rating"

FEATURE_COLUMNS = [
    "Country Code",
    "City",
    "Longitude",
    "Latitude",
    "Cuisines",
    "Average Cost for two",
    "Has Table booking",
    "Has Online delivery",
    "Is delivering now",
    "Price range",
    "Average Cost INR",
    "Log Average Cost INR",
    "Cost Relative To City",
    "Cuisine Count",
]

CAT_FEATURES = [
    "Country Code",
    "City",
    "Cuisines",
    "Has Table booking",
    "Has Online delivery",
    "Is delivering now",
]

DROP_COLUMNS = [
    "Restaurant ID",
    "Restaurant Name",
    "Address",
    "Locality",
    "Locality Verbose",
    "Currency",
    "Rating color",
    "Rating text",
    "Switch to order menu",
    "Votes",
    "Log Votes",
]


def load_dataset(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()

    missing_features = [col for col in FEATURE_COLUMNS if col not in df.columns]
    if missing_features:
        raise ValueError(f"Missing required feature columns: {missing_features}")

    if TARGET_COLUMN not in df.columns:
        raise ValueError(f"Missing target column: {TARGET_COLUMN}")

    return df


def prepare_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    df = df.drop(columns=[col for col in DROP_COLUMNS if col in df.columns])
    df = df.dropna(subset=[TARGET_COLUMN])

    X = df[FEATURE_COLUMNS].copy()
    y = df[TARGET_COLUMN].copy()

    for col in CAT_FEATURES:
        X[col] = X[col].fillna("Unknown").astype(str)

    numeric_cols = [col for col in FEATURE_COLUMNS if col not in CAT_FEATURES]
    for col in numeric_cols:
        X[col] = pd.to_numeric(X[col], errors="coerce")
        X[col] = X[col].fillna(X[col].median())

    return X, y


def split_dataset(
    X: pd.DataFrame,
    y: pd.Series,
    test_size: float = 0.15,
    val_size: float = 0.15,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.Series]:
    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
    )

    val_ratio_from_train_val = val_size / (1 - test_size)

    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val,
        y_train_val,
        test_size=val_ratio_from_train_val,
        random_state=random_state,
    )

    return X_train, X_val, X_test, y_train, y_val, y_test


def evaluate_model(model: CatBoostRegressor, X: pd.DataFrame, y: pd.Series, label: str) -> dict:
    predictions = model.predict(X)
    rmse = np.sqrt(mean_squared_error(y, predictions))

    metrics = {
        "MAE": mean_absolute_error(y, predictions),
        "RMSE": rmse,
        "R2": r2_score(y, predictions),
    }

    print(f"\n{label} Results")
    print(f"MAE : {metrics['MAE']:.4f}")
    print(f"RMSE: {metrics['RMSE']:.4f}")
    print(f"R2  : {metrics['R2']:.4f}")

    return metrics


def show_feature_importance(model: CatBoostRegressor) -> None:
    importance = pd.DataFrame(
        {
            "Feature": FEATURE_COLUMNS,
            "Importance": model.get_feature_importance(),
        }
    ).sort_values(by="Importance", ascending=False)

    print("\nFeature Importance")
    print(importance.to_string(index=False))


def train_catboost(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
) -> CatBoostRegressor:
    train_pool = Pool(X_train, y_train, cat_features=CAT_FEATURES)
    val_pool = Pool(X_val, y_val, cat_features=CAT_FEATURES)

    model = CatBoostRegressor(
        loss_function="RMSE",
        eval_metric="RMSE",
        iterations=3000,
        learning_rate=0.03,
        depth=8,
        l2_leaf_reg=7,
        random_seed=42,
        od_type="Iter",
        od_wait=150,
        verbose=100,
    )

    model.fit(
        train_pool,
        eval_set=val_pool,
        use_best_model=True,
    )

    return model


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train a CatBoost model for restaurant rating prediction without vote features."
    )
    parser.add_argument(
        "--csv",
        default=r"D:\Internship\cleaned_dataset.csv",
        help="Path to cleaned_dataset.csv",
    )
    parser.add_argument(
        "--model-output",
        default="catboost_restaurant_rating_model_without_votes.pkl",
        help="Output path for the trained model",
    )
    args = parser.parse_args()

    df = load_dataset(args.csv)
    X, y = prepare_features(df)

    X_train, X_val, X_test, y_train, y_val, y_test = split_dataset(X, y)

    print("Dataset split")
    print(f"Train     : {X_train.shape[0]} rows")
    print(f"Validation: {X_val.shape[0]} rows")
    print(f"Test      : {X_test.shape[0]} rows")

    model = train_catboost(X_train, y_train, X_val, y_val)

    evaluate_model(model, X_train, y_train, "Train")
    evaluate_model(model, X_val, y_val, "Validation")
    evaluate_model(model, X_test, y_test, "Test")

    show_feature_importance(model)

    output_path = Path(args.model_output)
    joblib.dump(model, output_path)
    print(f"\nSaved model to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
