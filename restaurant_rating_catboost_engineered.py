import argparse
from itertools import product
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from catboost import CatBoostRegressor, Pool
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, train_test_split


TARGET_COLUMN = "Aggregate rating"

# Do not include Rating Category or Restaurant Popularity Score here.
# They are created using Aggregate rating and would cause data leakage.
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
    "Log Votes",
    "Average Cost INR",
    "Log Average Cost INR",
    "Cost Relative To City",
    "City wise Cost Category",
    "Restaurant Cost Category",
    "Cuisine Count",
    "Popularity Category",
    "City Restaurant Count",
    "Is Expensive",
    "Location Cluster",
    "City Location Cluster",
]

CAT_FEATURES = [
    "Country Code",
    "City",
    "Cuisines",
    "Has Table booking",
    "Has Online delivery",
    "Is delivering now",
    "City wise Cost Category",
    "Restaurant Cost Category",
    "Popularity Category",
    "Location Cluster",
    "City Location Cluster",
]

LEAKAGE_COLUMNS = [
    "Rating color",
    "Rating text",
    "Rating Category",
    "Restaurant Popularity Score",
]

UNUSED_COLUMNS = [
    "Restaurant ID",
    "Restaurant Name",
    "Address",
    "Locality Verbose",
    "Currency",
    "Switch to order menu",
]

BASE_MODEL_PARAMS = {
    "loss_function": "RMSE",
    "eval_metric": "RMSE",
    "iterations": 3000,
    "learning_rate": 0.03,
    "depth": 8,
    "l2_leaf_reg": 5,
    "random_strength": 1,
    "bagging_temperature": 1,
    "random_seed": 42,
    "od_type": "Iter",
    "od_wait": 150,
}

TUNING_GRID = {
    "depth": [6, 8, 10],
    "learning_rate": [0.02, 0.03, 0.05],
    "l2_leaf_reg": [3, 5, 7, 9],
    "random_strength": [0.5, 1, 2],
    "bagging_temperature": [0, 1],
}


def load_dataset(csv_path: str) -> pd.DataFrame:
    data = pd.read_csv(csv_path)
    data.columns = data.columns.str.strip()

    if "Log votes" in data.columns and "Log Votes" not in data.columns:
        data["Log Votes"] = data["Log votes"]

    if "Votes" in data.columns and "Log Votes" not in data.columns:
        data["Log Votes"] = np.log1p(pd.to_numeric(data["Votes"], errors="coerce").fillna(0))

    missing_features = [col for col in FEATURE_COLUMNS if col not in data.columns]
    if missing_features:
        raise ValueError(f"Missing required feature columns: {missing_features}")

    if TARGET_COLUMN not in data.columns:
        raise ValueError(f"Missing target column: {TARGET_COLUMN}")

    return data


def prepare_features(data: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    data = data.copy()
    data = data.drop(columns=[col for col in UNUSED_COLUMNS + LEAKAGE_COLUMNS if col in data.columns])
    data = data.dropna(subset=[TARGET_COLUMN])

    X = data[FEATURE_COLUMNS].copy()
    y = pd.to_numeric(data[TARGET_COLUMN], errors="coerce")

    valid_target = y.notna()
    X = X.loc[valid_target].copy()
    y = y.loc[valid_target].copy()

    for col in CAT_FEATURES:
        X[col] = X[col].fillna("Unknown").astype(str).str.strip()

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


def build_model(params: dict | None = None, verbose: int | bool = 100) -> CatBoostRegressor:
    model_params = BASE_MODEL_PARAMS.copy()
    if params:
        model_params.update(params)
    model_params["verbose"] = verbose
    return CatBoostRegressor(**model_params)


def get_tuning_candidates(max_trials: int, random_state: int = 42) -> list[dict]:
    keys = list(TUNING_GRID.keys())
    candidates = [dict(zip(keys, values)) for values in product(*(TUNING_GRID[key] for key in keys))]

    base_candidate = {
        "depth": BASE_MODEL_PARAMS["depth"],
        "learning_rate": BASE_MODEL_PARAMS["learning_rate"],
        "l2_leaf_reg": BASE_MODEL_PARAMS["l2_leaf_reg"],
        "random_strength": BASE_MODEL_PARAMS["random_strength"],
        "bagging_temperature": BASE_MODEL_PARAMS["bagging_temperature"],
    }

    rng = np.random.default_rng(random_state)
    rng.shuffle(candidates)
    candidates = [base_candidate] + [candidate for candidate in candidates if candidate != base_candidate]

    return candidates[:max_trials]


def cross_validate_params(
    X: pd.DataFrame,
    y: pd.Series,
    params: dict,
    cv_folds: int,
    tuning_iterations: int,
    random_state: int,
) -> dict:
    kfold = KFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
    fold_metrics = []

    for fold, (train_idx, val_idx) in enumerate(kfold.split(X), start=1):
        X_train_fold = X.iloc[train_idx]
        X_val_fold = X.iloc[val_idx]
        y_train_fold = y.iloc[train_idx]
        y_val_fold = y.iloc[val_idx]

        train_pool = Pool(X_train_fold, y_train_fold, cat_features=CAT_FEATURES)
        val_pool = Pool(X_val_fold, y_val_fold, cat_features=CAT_FEATURES)

        fold_params = params.copy()
        fold_params["iterations"] = tuning_iterations

        model = build_model(fold_params, verbose=False)
        model.fit(train_pool, eval_set=val_pool, use_best_model=True)

        predictions = model.predict(X_val_fold)
        rmse = np.sqrt(mean_squared_error(y_val_fold, predictions))
        mae = mean_absolute_error(y_val_fold, predictions)
        r2 = r2_score(y_val_fold, predictions)

        fold_metrics.append({"RMSE": rmse, "MAE": mae, "R2": r2})
        print(
            f"    Fold {fold}: "
            f"RMSE={rmse:.4f}, MAE={mae:.4f}, R2={r2:.4f}, "
            f"best_iteration={model.get_best_iteration()}"
        )

    return {
        "RMSE": np.mean([metric["RMSE"] for metric in fold_metrics]),
        "RMSE_STD": np.std([metric["RMSE"] for metric in fold_metrics]),
        "MAE": np.mean([metric["MAE"] for metric in fold_metrics]),
        "R2": np.mean([metric["R2"] for metric in fold_metrics]),
    }


def tune_hyperparameters(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    cv_folds: int,
    tuning_trials: int,
    tuning_iterations: int,
    random_state: int,
) -> dict:
    candidates = get_tuning_candidates(tuning_trials, random_state=random_state)
    tuning_results = []

    print("\nHyperparameter tuning with cross-validation")
    print(f"Candidates: {len(candidates)}")
    print(f"CV folds  : {cv_folds}")

    for index, params in enumerate(candidates, start=1):
        print(f"\nCandidate {index}/{len(candidates)}: {params}")
        metrics = cross_validate_params(
            X_train,
            y_train,
            params,
            cv_folds=cv_folds,
            tuning_iterations=tuning_iterations,
            random_state=random_state,
        )
        tuning_results.append({"params": params, "metrics": metrics})
        print(
            f"  Mean CV: RMSE={metrics['RMSE']:.4f} "
            f"(+/- {metrics['RMSE_STD']:.4f}), "
            f"MAE={metrics['MAE']:.4f}, R2={metrics['R2']:.4f}"
        )

    best_result = min(tuning_results, key=lambda result: result["metrics"]["RMSE"])
    print("\nBest Parameters")
    print(best_result["params"])
    print(
        f"Best CV RMSE={best_result['metrics']['RMSE']:.4f}, "
        f"MAE={best_result['metrics']['MAE']:.4f}, "
        f"R2={best_result['metrics']['R2']:.4f}"
    )

    return best_result["params"]


def train_catboost(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    best_params: dict | None = None,
) -> CatBoostRegressor:
    train_pool = Pool(X_train, y_train, cat_features=CAT_FEATURES)
    val_pool = Pool(X_val, y_val, cat_features=CAT_FEATURES)

    model = build_model(best_params, verbose=100)
    model.fit(train_pool, eval_set=val_pool, use_best_model=True)

    return model


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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train tuned CatBoost model with engineered restaurant rating features."
    )
    parser.add_argument(
        "--csv",
        default=r"D:\Git\Restaurant_Intelligent_System\Dataset\cleaned_dataset.csv",
        help="Path to cleaned_dataset.csv",
    )
    parser.add_argument(
        "--model-output",
        default="catboost_restaurant_rating_engineered_model.pkl",
        help="Output path for the trained model",
    )
    parser.add_argument(
        "--cv-folds",
        type=int,
        default=3,
        help="Number of cross-validation folds used during hyperparameter tuning",
    )
    parser.add_argument(
        "--tuning-trials",
        type=int,
        default=8,
        help="Number of hyperparameter combinations to test",
    )
    parser.add_argument(
        "--tuning-iterations",
        type=int,
        default=800,
        help="Maximum CatBoost iterations used for each tuning fold",
    )
    parser.add_argument(
        "--skip-tuning",
        action="store_true",
        help="Train with default parameters without cross-validation tuning",
    )
    args = parser.parse_args()

    data = load_dataset(args.csv)
    X, y = prepare_features(data)

    X_train, X_val, X_test, y_train, y_val, y_test = split_dataset(X, y)

    print("Dataset split")
    print(f"Train     : {X_train.shape[0]} rows")
    print(f"Validation: {X_val.shape[0]} rows")
    print(f"Test      : {X_test.shape[0]} rows")

    if args.skip_tuning:
        best_params = None
        print("\nSkipping hyperparameter tuning. Training with default parameters.")
    else:
        best_params = tune_hyperparameters(
            X_train,
            y_train,
            cv_folds=args.cv_folds,
            tuning_trials=args.tuning_trials,
            tuning_iterations=args.tuning_iterations,
            random_state=42,
        )

    model = train_catboost(X_train, y_train, X_val, y_val, best_params=best_params)

    evaluate_model(model, X_train, y_train, "Train")
    evaluate_model(model, X_val, y_val, "Validation")
    evaluate_model(model, X_test, y_test, "Test")

    show_feature_importance(model)

    output_path = Path(args.model_output)
    joblib.dump(model, output_path)
    print(f"\nSaved model to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
