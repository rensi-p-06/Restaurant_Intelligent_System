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
REPORT_LINES = []

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


def report(message: str = "") -> None:
    print(message)
    REPORT_LINES.append(str(message))


def format_params(params: dict) -> str:
    return ", ".join(f"{key}={value}" for key, value in params.items())


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
    candidate: int,
    cv_folds: int,
    tuning_iterations: int,
    random_state: int,
) -> tuple[dict, list[dict]]:
    kfold = KFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
    fold_metrics = []
    fold_records = []

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
        best_iteration = model.get_best_iteration()

        fold_metrics.append({"RMSE": rmse, "MAE": mae, "R2": r2})
        fold_records.append(
            {
                "Candidate": candidate,
                "Fold": fold,
                "RMSE": rmse,
                "MAE": mae,
                "R2": r2,
                "Best Iteration": best_iteration,
                **params,
            }
        )
        report(
            f"    Fold {fold}: "
            f"RMSE={rmse:.4f}, MAE={mae:.4f}, R2={r2:.4f}, "
            f"best_iteration={best_iteration}"
        )

    metrics = {
        "RMSE": np.mean([metric["RMSE"] for metric in fold_metrics]),
        "RMSE_STD": np.std([metric["RMSE"] for metric in fold_metrics]),
        "MAE": np.mean([metric["MAE"] for metric in fold_metrics]),
        "R2": np.mean([metric["R2"] for metric in fold_metrics]),
    }
    return metrics, fold_records


def tune_hyperparameters(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    cv_folds: int,
    tuning_trials: int,
    tuning_iterations: int,
    random_state: int,
) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    candidates = get_tuning_candidates(tuning_trials, random_state=random_state)
    tuning_results = []
    summary_records = []
    all_fold_records = []

    report("\nHyperparameter tuning with cross-validation")
    report(f"Candidates: {len(candidates)}")
    report(f"CV folds  : {cv_folds}")

    for index, params in enumerate(candidates, start=1):
        report(f"\nCandidate {index}/{len(candidates)}: {params}")
        metrics, fold_records = cross_validate_params(
            X_train,
            y_train,
            params,
            candidate=index,
            cv_folds=cv_folds,
            tuning_iterations=tuning_iterations,
            random_state=random_state,
        )
        tuning_results.append({"params": params, "metrics": metrics})
        all_fold_records.extend(fold_records)
        summary_records.append(
            {
                "Candidate": index,
                "Parameters": format_params(params),
                "Mean RMSE": metrics["RMSE"],
                "RMSE STD": metrics["RMSE_STD"],
                "Mean MAE": metrics["MAE"],
                "Mean R2": metrics["R2"],
                **params,
            }
        )
        report(
            f"  Mean CV: RMSE={metrics['RMSE']:.4f} "
            f"(+/- {metrics['RMSE_STD']:.4f}), "
            f"MAE={metrics['MAE']:.4f}, R2={metrics['R2']:.4f}"
        )

    best_result = min(tuning_results, key=lambda result: result["metrics"]["RMSE"])
    report("\nBest Parameters")
    report(str(best_result["params"]))
    report(
        f"Best CV RMSE={best_result['metrics']['RMSE']:.4f}, "
        f"MAE={best_result['metrics']['MAE']:.4f}, "
        f"R2={best_result['metrics']['R2']:.4f}"
    )

    return best_result["params"], pd.DataFrame(summary_records), pd.DataFrame(all_fold_records)


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

    report(f"\n{label} Results")
    report(f"MAE : {metrics['MAE']:.4f}")
    report(f"RMSE: {metrics['RMSE']:.4f}")
    report(f"R2  : {metrics['R2']:.4f}")

    return metrics


def show_feature_importance(model: CatBoostRegressor) -> pd.DataFrame:
    importance = pd.DataFrame(
        {
            "Feature": FEATURE_COLUMNS,
            "Importance": model.get_feature_importance(),
        }
    ).sort_values(by="Importance", ascending=False)

    report("\nFeature Importance")
    report(importance.to_string(index=False))
    return importance


def save_results(
    results_dir: Path,
    final_metrics: list[dict],
    feature_importance: pd.DataFrame,
    cv_summary: pd.DataFrame | None = None,
    cv_folds: pd.DataFrame | None = None,
) -> None:
    results_dir.mkdir(parents=True, exist_ok=True)

    (results_dir / "training_report.txt").write_text("\n".join(REPORT_LINES), encoding="utf-8")
    pd.DataFrame(final_metrics).to_csv(results_dir / "final_metrics.csv", index=False)
    feature_importance.to_csv(results_dir / "feature_importance.csv", index=False)

    if cv_summary is not None and not cv_summary.empty:
        cv_summary.to_csv(results_dir / "cv_hyperparameter_summary.csv", index=False)

    if cv_folds is not None and not cv_folds.empty:
        cv_folds.to_csv(results_dir / "cv_fold_metrics.csv", index=False)


def save_plots(
    results_dir: Path,
    final_metrics: list[dict],
    feature_importance: pd.DataFrame,
    cv_summary: pd.DataFrame | None = None,
    cv_folds: pd.DataFrame | None = None,
) -> None:
    try:
        import plotly.graph_objects as go
    except ImportError:
        report("\nPlotly is not installed. Skipping interactive graph creation.")
        return

    results_dir.mkdir(parents=True, exist_ok=True)

    template = "plotly_dark"
    metrics_df = pd.DataFrame(final_metrics)
    metric_names = ["MAE", "RMSE", "R2"]

    fig = go.Figure()
    colors = {"MAE": "#00cc96", "RMSE": "#ef553b", "R2": "#636efa"}
    for index, metric in enumerate(metric_names):
        fig.add_trace(
            go.Bar(
                x=metrics_df["Dataset"],
                y=metrics_df[metric],
                name=metric,
                marker_color=colors[metric],
                text=metrics_df[metric].round(4),
                textposition="auto",
                visible=index == 0,
            )
        )
    fig.update_layout(
        template=template,
        title="Final Model Metrics by Dataset Split",
        xaxis_title="Dataset Split",
        yaxis_title="Metric Value",
        updatemenus=[
            {
                "buttons": [
                    {
                        "label": metric,
                        "method": "update",
                        "args": [
                            {"visible": [name == metric for name in metric_names]},
                            {"yaxis": {"title": metric}},
                        ],
                    }
                    for metric in metric_names
                ],
                "direction": "down",
                "x": 1.12,
                "y": 1.15,
                "showactive": True,
            }
        ],
    )
    fig.write_html(results_dir / "final_metrics_toggle.html", include_plotlyjs="cdn")

    if cv_summary is not None and not cv_summary.empty:
        cv_metric_map = {
            "Mean R2": "#636efa",
            "Mean RMSE": "#ef553b",
            "Mean MAE": "#00cc96",
        }

        fig = go.Figure()
        for index, (metric, color) in enumerate(cv_metric_map.items()):
            fig.add_trace(
                go.Scatter(
                    x=cv_summary["Candidate"],
                    y=cv_summary[metric],
                    mode="lines+markers",
                    name=metric,
                    marker={"size": 10, "color": color},
                    line={"color": color},
                    text=cv_summary["Parameters"],
                    hovertemplate=(
                        "Candidate=%{x}<br>"
                        f"{metric}=%{{y:.4f}}<br>"
                        "Params=%{text}<extra></extra>"
                    ),
                    visible=index == 0,
                )
            )
        fig.update_layout(
            template=template,
            title="Cross-Validation Metric by Hyperparameter Candidate",
            xaxis_title="Candidate",
            yaxis_title="Mean R2",
            updatemenus=[
                {
                    "buttons": [
                        {
                            "label": metric,
                            "method": "update",
                            "args": [
                                {"visible": [name == metric for name in cv_metric_map]},
                                {"yaxis": {"title": metric}},
                            ],
                        }
                        for metric in cv_metric_map
                    ],
                    "direction": "down",
                    "x": 1.12,
                    "y": 1.15,
                    "showactive": True,
                }
            ],
        )
        fig.write_html(results_dir / "cv_candidate_metrics_toggle.html", include_plotlyjs="cdn")

        params = ["depth", "learning_rate", "l2_leaf_reg", "random_strength", "bagging_temperature"]
        fig = go.Figure()
        for index, param in enumerate(params):
            fig.add_trace(
                go.Scatter(
                    x=cv_summary[param],
                    y=cv_summary["Mean R2"],
                    mode="markers",
                    name=param,
                    marker={"size": 12, "color": "#ab63fa"},
                    text=cv_summary["Parameters"],
                    hovertemplate=(
                        f"{param}=%{{x}}<br>"
                        "Mean R2=%{y:.4f}<br>"
                        "Params=%{text}<extra></extra>"
                    ),
                    visible=index == 0,
                )
            )
        fig.update_layout(
            template=template,
            title="Mean CV R2 vs Hyperparameter Values",
            xaxis_title=params[0],
            yaxis_title="Mean CV R2",
            updatemenus=[
                {
                    "buttons": [
                        {
                            "label": param,
                            "method": "update",
                            "args": [
                                {"visible": [name == param for name in params]},
                                {"xaxis": {"title": param}},
                            ],
                        }
                        for param in params
                    ],
                    "direction": "down",
                    "x": 1.12,
                    "y": 1.15,
                    "showactive": True,
                }
            ],
        )
        fig.write_html(results_dir / "cv_r2_vs_hyperparameters_toggle.html", include_plotlyjs="cdn")

    if cv_folds is not None and not cv_folds.empty:
        fold_metric_names = ["R2", "RMSE", "MAE"]
        fig = go.Figure()
        trace_metric_names = []
        for metric in fold_metric_names:
            for candidate, group in cv_folds.groupby("Candidate"):
                trace_metric_names.append(metric)
                fig.add_trace(
                    go.Scatter(
                        x=group["Fold"],
                        y=group[metric],
                        mode="lines+markers",
                        name=f"Candidate {candidate}",
                        legendgroup=f"Candidate {candidate}",
                        text=group.apply(
                            lambda row: format_params(
                                {
                                    "depth": row["depth"],
                                    "learning_rate": row["learning_rate"],
                                    "l2_leaf_reg": row["l2_leaf_reg"],
                                    "random_strength": row["random_strength"],
                                    "bagging_temperature": row["bagging_temperature"],
                                }
                            ),
                            axis=1,
                        ),
                        hovertemplate=(
                            "Fold=%{x}<br>"
                            f"{metric}=%{{y:.4f}}<br>"
                            "Params=%{text}<extra></extra>"
                        ),
                        visible=metric == "R2",
                    )
                )
        fig.update_layout(
            template=template,
            title="Cross-Validation Fold Metrics by Candidate",
            xaxis_title="Fold",
            yaxis_title="R2",
            updatemenus=[
                {
                    "buttons": [
                        {
                            "label": metric,
                            "method": "update",
                            "args": [
                                {"visible": [name == metric for name in trace_metric_names]},
                                {"yaxis": {"title": metric}},
                            ],
                        }
                        for metric in fold_metric_names
                    ],
                    "direction": "down",
                    "x": 1.12,
                    "y": 1.15,
                    "showactive": True,
                }
            ],
        )
        fig.write_html(results_dir / "cv_fold_metrics_toggle.html", include_plotlyjs="cdn")

    top_counts = [10, 15, min(25, len(feature_importance)), len(feature_importance)]
    top_counts = list(dict.fromkeys(top_counts))

    fig = go.Figure()
    for index, top_n in enumerate(top_counts):
        top_features = feature_importance.head(top_n).sort_values("Importance")
        fig.add_trace(
            go.Bar(
                x=top_features["Importance"],
                y=top_features["Feature"],
                orientation="h",
                name=f"Top {top_n}",
                marker_color="#ffa15a",
                text=top_features["Importance"].round(4),
                textposition="auto",
                visible=index == 1 if len(top_counts) > 1 else True,
            )
        )
    fig.update_layout(
        template=template,
        title="Feature Importance",
        xaxis_title="Importance",
        yaxis_title="Feature",
        height=700,
        updatemenus=[
            {
                "buttons": [
                    {
                        "label": f"Top {top_n}",
                        "method": "update",
                        "args": [
                            {"visible": [count == top_n for count in top_counts]},
                            {"title": f"Top {top_n} Feature Importances"},
                        ],
                    }
                    for top_n in top_counts
                ],
                "direction": "down",
                "x": 1.12,
                "y": 1.15,
                "showactive": True,
            }
        ],
    )
    fig.write_html(results_dir / "feature_importance_toggle.html", include_plotlyjs="cdn")

    cumulative = feature_importance.copy()
    cumulative["Cumulative Importance"] = cumulative["Importance"].cumsum()

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=cumulative["Feature"],
            y=cumulative["Cumulative Importance"],
            mode="lines+markers",
            name="Cumulative Importance",
            marker={"size": 8, "color": "#19d3f3"},
            line={"color": "#19d3f3"},
            hovertemplate="Feature=%{x}<br>Cumulative=%{y:.4f}<extra></extra>",
        )
    )
    fig.update_layout(
        template=template,
        title="Cumulative Feature Importance",
        xaxis_title="Feature",
        yaxis_title="Cumulative Importance",
        xaxis_tickangle=-45,
    )
    fig.write_html(results_dir / "feature_importance_cumulative.html", include_plotlyjs="cdn")

    report("\nSaved interactive Plotly dark-theme graphs.")


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
        "--results-dir",
        default="rating_model_results",
        help="Directory where reports, CSV files, and graphs will be saved",
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

    report("Dataset split")
    report(f"Train     : {X_train.shape[0]} rows")
    report(f"Validation: {X_val.shape[0]} rows")
    report(f"Test      : {X_test.shape[0]} rows")

    if args.skip_tuning:
        best_params = None
        cv_summary = pd.DataFrame()
        cv_folds = pd.DataFrame()
        report("\nSkipping hyperparameter tuning. Training with default parameters.")
    else:
        best_params, cv_summary, cv_folds = tune_hyperparameters(
            X_train,
            y_train,
            cv_folds=args.cv_folds,
            tuning_trials=args.tuning_trials,
            tuning_iterations=args.tuning_iterations,
            random_state=42,
        )

    model = train_catboost(X_train, y_train, X_val, y_val, best_params=best_params)

    final_metrics = []
    for label, features, target in [
        ("Train", X_train, y_train),
        ("Validation", X_val, y_val),
        ("Test", X_test, y_test),
    ]:
        metrics = evaluate_model(model, features, target, label)
        final_metrics.append({"Dataset": label, **metrics})

    feature_importance = show_feature_importance(model)

    output_path = Path(args.model_output)
    joblib.dump(model, output_path)
    report(f"\nSaved model to: {output_path.resolve()}")

    results_dir = Path(args.results_dir)
    save_results(
        results_dir=results_dir,
        final_metrics=final_metrics,
        feature_importance=feature_importance,
        cv_summary=cv_summary,
        cv_folds=cv_folds,
    )
    save_plots(
        results_dir=results_dir,
        final_metrics=final_metrics,
        feature_importance=feature_importance,
        cv_summary=cv_summary,
        cv_folds=cv_folds,
    )
    report(f"Saved reports and graphs to: {results_dir.resolve()}")
    (results_dir / "training_report.txt").write_text("\n".join(REPORT_LINES), encoding="utf-8")


if __name__ == "__main__":
    main()
