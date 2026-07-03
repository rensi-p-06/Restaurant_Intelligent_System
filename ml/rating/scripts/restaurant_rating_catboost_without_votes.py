import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from catboost import CatBoostRegressor, Pool
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


TARGET_COLUMN = "Aggregate rating"
REPORT_LINES = []

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


def report(message: str = "") -> None:
    print(message)
    REPORT_LINES.append(str(message))


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
    errors = np.abs(y - predictions)
    rmse = np.sqrt(mean_squared_error(y, predictions))
    mae = mean_absolute_error(y, predictions)

    metrics = {
        "MAE": mae,
        "RMSE": rmse,
        "R2": r2_score(y, predictions),
        "Within 0.25 Accuracy": np.mean(errors <= 0.25) * 100,
        "Within 0.50 Accuracy": np.mean(errors <= 0.50) * 100,
        "Rating Scale Accuracy": max(0, (1 - mae / 5.0) * 100),
    }

    report(f"\n{label} Results")
    report(f"MAE : {metrics['MAE']:.4f}")
    report(f"RMSE: {metrics['RMSE']:.4f}")
    report(f"R2  : {metrics['R2']:.4f}")
    report(f"Within 0.25 Accuracy: {metrics['Within 0.25 Accuracy']:.2f}%")
    report(f"Within 0.50 Accuracy: {metrics['Within 0.50 Accuracy']:.2f}%")
    report(f"Rating Scale Accuracy: {metrics['Rating Scale Accuracy']:.2f}%")

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
) -> None:
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "training_report.txt").write_text("\n".join(REPORT_LINES), encoding="utf-8")
    pd.DataFrame(final_metrics).to_csv(results_dir / "final_metrics.csv", index=False)
    feature_importance.to_csv(results_dir / "feature_importance.csv", index=False)


def save_plots(
    results_dir: Path,
    final_metrics: list[dict],
    feature_importance: pd.DataFrame,
) -> None:
    try:
        import plotly.graph_objects as go
    except ImportError:
        report("\nPlotly is not installed. Skipping interactive graph creation.")
        return

    results_dir.mkdir(parents=True, exist_ok=True)
    template = "plotly_dark"
    metrics_df = pd.DataFrame(final_metrics)
    metric_names = ["MAE", "RMSE", "R2", "Within 0.25 Accuracy", "Within 0.50 Accuracy", "Rating Scale Accuracy"]
    colors = {
        "MAE": "#00cc96",
        "RMSE": "#ef553b",
        "R2": "#636efa",
        "Within 0.25 Accuracy": "#ab63fa",
        "Within 0.50 Accuracy": "#ffa15a",
        "Rating Scale Accuracy": "#19d3f3",
    }

    fig = go.Figure()
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
    fig.write_html(results_dir / "final_metrics_toggle.html", include_plotlyjs=True)

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
                visible=(index == 1 if len(top_counts) > 1 else True),
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
    fig.write_html(results_dir / "feature_importance_toggle.html", include_plotlyjs=True)

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
    fig.write_html(results_dir / "feature_importance_cumulative.html", include_plotlyjs=True)
    report("\nSaved interactive Plotly dark-theme graphs.")


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
        default=r"D:\Git\Restaurant_Intelligent_System\Dataset\cleaned_dataset.csv",
        help="Path to cleaned_dataset.csv",
    )
    parser.add_argument(
        "--model-output",
        default="catboost_restaurant_rating_model_without_votes.pkl",
        help="Output path for the trained model",
    )
    parser.add_argument(
        "--results-dir",
        default="rating_model_without_votes_results",
        help="Directory where reports, CSV files, and graphs will be saved",
    )
    args = parser.parse_args()

    df = load_dataset(args.csv)
    X, y = prepare_features(df)

    X_train, X_val, X_test, y_train, y_val, y_test = split_dataset(X, y)

    report("Dataset split")
    report(f"Train     : {X_train.shape[0]} rows")
    report(f"Validation: {X_val.shape[0]} rows")
    report(f"Test      : {X_test.shape[0]} rows")

    model = train_catboost(X_train, y_train, X_val, y_val)

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
    )
    save_plots(
        results_dir=results_dir,
        final_metrics=final_metrics,
        feature_importance=feature_importance,
    )
    report(f"Saved reports and graphs to: {results_dir.resolve()}")
    (results_dir / "training_report.txt").write_text("\n".join(REPORT_LINES), encoding="utf-8")


if __name__ == "__main__":
    main()
