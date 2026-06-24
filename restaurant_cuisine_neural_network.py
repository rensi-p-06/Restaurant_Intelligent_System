import argparse
from collections import Counter
from itertools import product
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    hamming_loss,
    precision_score,
    recall_score,
)
from sklearn.model_selection import KFold, train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MultiLabelBinarizer, OneHotEncoder, StandardScaler


TARGET_COLUMN = "Cuisines"
TEXT_FEATURE = "Restaurant Name"
REPORT_LINES = []

CATEGORICAL_FEATURES = [
    "Country Code",
    "City",
    "Locality",
    "Has Table booking",
    "Has Online delivery",
    "Is delivering now",
]

NUMERIC_FEATURES = [
    "Longitude",
    "Latitude",
    "Log Average Cost INR",
    "Price range",
    "Aggregate rating",
    "Log Votes",
]

FEATURE_COLUMNS = [TEXT_FEATURE] + CATEGORICAL_FEATURES + NUMERIC_FEATURES
LEAKAGE_COLUMNS = ["Cuisines", "Primary Cuisine", "Cuisine Count"]

BASE_MODEL_PARAMS = {
    "min_cuisine_samples": 20,
    "max_name_features": 3000,
    "ngram_max": 2,
    "tfidf_min_df": 1,
    "hidden_layer_sizes": (256,),
    "alpha": 0.0001,
    "learning_rate_init": 0.001,
}

TUNING_GRID = {
    "min_cuisine_samples": [10, 20, 30],
    "max_name_features": [2000, 3000],
    "ngram_max": [1, 2],
    "tfidf_min_df": [1, 2],
    "hidden_layer_sizes": [(128,), (256,), (128, 64)],
    "alpha": [0.0001, 0.001],
    "learning_rate_init": [0.001],
}


def report(message: str = "") -> None:
    print(message)
    REPORT_LINES.append(str(message))


def make_one_hot_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=True)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=True)


def format_params(params: dict) -> str:
    parts = []
    for key, value in params.items():
        parts.append(f"{key}={value}")
    return ", ".join(parts)


def build_preprocessor(max_name_features: int, ngram_max: int, tfidf_min_df: int) -> ColumnTransformer:
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="constant", fill_value="Unknown")),
            ("onehot", make_one_hot_encoder()),
        ]
    )

    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler(with_mean=False)),
        ]
    )

    return ColumnTransformer(
        transformers=[
            (
                "name",
                TfidfVectorizer(
                    lowercase=True,
                    strip_accents="unicode",
                    ngram_range=(1, ngram_max),
                    max_features=max_name_features,
                    min_df=tfidf_min_df,
                ),
                TEXT_FEATURE,
            ),
            ("cat", categorical_pipeline, CATEGORICAL_FEATURES),
            ("num", numeric_pipeline, NUMERIC_FEATURES),
        ]
    )


def load_dataset(csv_path: str) -> pd.DataFrame:
    data = pd.read_csv(csv_path)
    data.columns = data.columns.str.strip()

    if "Log votes" in data.columns and "Log Votes" not in data.columns:
        data["Log Votes"] = data["Log votes"]

    if "Votes" in data.columns and "Log Votes" not in data.columns:
        data["Log Votes"] = np.log1p(pd.to_numeric(data["Votes"], errors="coerce").fillna(0))

    if "Average Cost INR" in data.columns and "Log Average Cost INR" not in data.columns:
        cost = pd.to_numeric(data["Average Cost INR"], errors="coerce").fillna(0)
        data["Log Average Cost INR"] = np.log1p(cost.clip(lower=0))

    missing_features = [col for col in FEATURE_COLUMNS if col not in data.columns]
    if missing_features:
        raise ValueError(f"Missing required feature columns: {missing_features}")

    if TARGET_COLUMN not in data.columns:
        raise ValueError(f"Missing target column: {TARGET_COLUMN}")

    return data


def split_cuisines(value: str) -> list[str]:
    return [cuisine.strip() for cuisine in str(value).split(",") if cuisine.strip()]


def prepare_features_and_labels(
    data: pd.DataFrame,
    min_cuisine_samples: int,
) -> tuple[pd.DataFrame, np.ndarray, MultiLabelBinarizer, pd.DataFrame, pd.DataFrame]:
    data = data.dropna(subset=[TARGET_COLUMN]).copy()
    cuisine_lists = data[TARGET_COLUMN].apply(split_cuisines)
    all_cuisine_counts = Counter(cuisine for row in cuisine_lists for cuisine in row)

    common_cuisines = {
        cuisine for cuisine, count in all_cuisine_counts.items() if count >= min_cuisine_samples
    }
    filtered_cuisine_lists = cuisine_lists.apply(
        lambda row: [cuisine for cuisine in row if cuisine in common_cuisines]
    )
    valid_rows = filtered_cuisine_lists.map(len) > 0

    X = data.loc[valid_rows, FEATURE_COLUMNS].copy()
    filtered_cuisine_lists = filtered_cuisine_lists.loc[valid_rows]

    X[TEXT_FEATURE] = X[TEXT_FEATURE].fillna("").astype(str).str.strip()
    for col in CATEGORICAL_FEATURES:
        X[col] = X[col].fillna("Unknown").astype(str).str.strip()
    for col in NUMERIC_FEATURES:
        X[col] = pd.to_numeric(X[col], errors="coerce")

    mlb = MultiLabelBinarizer()
    y = mlb.fit_transform(filtered_cuisine_lists)

    cuisine_frequency = (
        pd.DataFrame(
            [{"Cuisine": cuisine, "Count": count} for cuisine, count in all_cuisine_counts.items()]
        )
        .sort_values(["Count", "Cuisine"], ascending=[False, True])
        .reset_index(drop=True)
    )
    cuisine_frequency["Used In Model"] = cuisine_frequency["Count"] >= min_cuisine_samples

    dropped_cuisines = cuisine_frequency.loc[
        ~cuisine_frequency["Used In Model"], ["Cuisine", "Count"]
    ].reset_index(drop=True)

    return X, y, mlb, cuisine_frequency, dropped_cuisines


def split_dataset(
    X: pd.DataFrame,
    y: np.ndarray,
    test_size: float,
    val_size: float,
    random_state: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray, np.ndarray]:
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


def build_model(params: dict, random_state: int) -> Pipeline:
    neural_network = MLPClassifier(
        hidden_layer_sizes=params["hidden_layer_sizes"],
        activation="relu",
        solver="adam",
        alpha=params["alpha"],
        batch_size="auto",
        learning_rate="adaptive",
        learning_rate_init=params["learning_rate_init"],
        max_iter=250,
        early_stopping=True,
        validation_fraction=0.12,
        n_iter_no_change=12,
        random_state=random_state,
        verbose=False,
    )

    return Pipeline(
        steps=[
            (
                "preprocessor",
                build_preprocessor(
                    max_name_features=params["max_name_features"],
                    ngram_max=params["ngram_max"],
                    tfidf_min_df=params["tfidf_min_df"],
                ),
            ),
            ("classifier", neural_network),
        ]
    )


def positive_probabilities(model: Pipeline, X: pd.DataFrame) -> np.ndarray:
    probabilities = model.predict_proba(X)

    if isinstance(probabilities, list):
        positive_columns = []
        for output_probability in probabilities:
            if output_probability.shape[1] == 1:
                positive_columns.append(output_probability[:, 0])
            else:
                positive_columns.append(output_probability[:, 1])
        return np.column_stack(positive_columns)

    return np.asarray(probabilities)


def apply_threshold(probabilities: np.ndarray, threshold: float, ensure_one_label: bool = True) -> np.ndarray:
    predictions = (probabilities >= threshold).astype(int)

    if ensure_one_label:
        empty_rows = predictions.sum(axis=1) == 0
        if np.any(empty_rows):
            best_label_indexes = np.argmax(probabilities[empty_rows], axis=1)
            predictions[empty_rows, best_label_indexes] = 1

    return predictions


def tune_threshold(model: Pipeline, X_val: pd.DataFrame, y_val: np.ndarray) -> tuple[float, pd.DataFrame]:
    probabilities = positive_probabilities(model, X_val)
    records = []

    for threshold in np.arange(0.10, 0.81, 0.05):
        y_pred = apply_threshold(probabilities, threshold)
        records.append(
            {
                "Threshold": round(float(threshold), 2),
                "Micro F1": f1_score(y_val, y_pred, average="micro", zero_division=0),
                "Macro F1": f1_score(y_val, y_pred, average="macro", zero_division=0),
                "Sample F1": f1_score(y_val, y_pred, average="samples", zero_division=0),
                "Hamming Loss": hamming_loss(y_val, y_pred),
                "Exact Match Accuracy": accuracy_score(y_val, y_pred),
            }
        )

    threshold_results = pd.DataFrame(records)
    best_row = threshold_results.sort_values(
        ["Micro F1", "Sample F1", "Macro F1"],
        ascending=[False, False, False],
    ).iloc[0]

    return float(best_row["Threshold"]), threshold_results


def get_tuning_candidates(max_trials: int, random_state: int) -> list[dict]:
    keys = list(TUNING_GRID.keys())
    candidates = [dict(zip(keys, values)) for values in product(*(TUNING_GRID[key] for key in keys))]

    base_candidate = BASE_MODEL_PARAMS.copy()
    rng = np.random.default_rng(random_state)
    rng.shuffle(candidates)
    candidates = [base_candidate] + [candidate for candidate in candidates if candidate != base_candidate]

    return candidates[:max_trials]


def cross_validate_params(
    X: pd.DataFrame,
    y: np.ndarray,
    params: dict,
    candidate: int,
    cv_folds: int,
    random_state: int,
) -> tuple[dict, list[dict]]:
    kfold = KFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
    fold_records = []

    for fold, (train_idx, val_idx) in enumerate(kfold.split(X), start=1):
        X_train_fold = X.iloc[train_idx]
        X_val_fold = X.iloc[val_idx]
        y_train_fold = y[train_idx]
        y_val_fold = y[val_idx]

        model = build_model(params, random_state=random_state + fold)
        model.fit(X_train_fold, y_train_fold)

        best_threshold, threshold_results = tune_threshold(model, X_val_fold, y_val_fold)
        best_threshold_row = threshold_results.loc[
            threshold_results["Threshold"].sub(best_threshold).abs().idxmin()
        ]

        fold_record = {
            "Candidate": candidate,
            "Fold": fold,
            "Best Threshold": best_threshold,
            "Micro F1": best_threshold_row["Micro F1"],
            "Macro F1": best_threshold_row["Macro F1"],
            "Sample F1": best_threshold_row["Sample F1"],
            "Hamming Loss": best_threshold_row["Hamming Loss"],
            "Exact Match Accuracy": best_threshold_row["Exact Match Accuracy"],
            **params,
        }
        fold_records.append(fold_record)

        report(
            f"    Fold {fold}: threshold={best_threshold:.2f}, "
            f"micro_f1={fold_record['Micro F1']:.4f}, "
            f"macro_f1={fold_record['Macro F1']:.4f}, "
            f"sample_f1={fold_record['Sample F1']:.4f}"
        )

    metrics = {
        "Mean Micro F1": float(np.mean([record["Micro F1"] for record in fold_records])),
        "Micro F1 STD": float(np.std([record["Micro F1"] for record in fold_records])),
        "Mean Macro F1": float(np.mean([record["Macro F1"] for record in fold_records])),
        "Mean Sample F1": float(np.mean([record["Sample F1"] for record in fold_records])),
        "Mean Hamming Loss": float(np.mean([record["Hamming Loss"] for record in fold_records])),
        "Mean Exact Match Accuracy": float(np.mean([record["Exact Match Accuracy"] for record in fold_records])),
        "Mean Best Threshold": float(np.mean([record["Best Threshold"] for record in fold_records])),
    }

    return metrics, fold_records


def tune_hyperparameters(
    data: pd.DataFrame,
    cv_folds: int,
    tuning_trials: int,
    random_state: int,
) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    candidates = get_tuning_candidates(tuning_trials, random_state=random_state)
    tuning_results = []
    summary_records = []
    all_fold_records = []

    report("\nNeural network hyperparameter tuning with K-fold cross-validation")
    report(f"Candidates: {len(candidates)}")
    report(f"CV folds  : {cv_folds}")
    report("Selection metric: Mean Micro F1")

    for index, params in enumerate(candidates, start=1):
        report(f"\nCandidate {index}/{len(candidates)}: {params}")
        X_candidate, y_candidate, candidate_mlb, _, _ = prepare_features_and_labels(
            data,
            min_cuisine_samples=params["min_cuisine_samples"],
        )
        report(
            f"  Candidate data: rows={X_candidate.shape[0]}, "
            f"cuisine_labels={len(candidate_mlb.classes_)}"
        )

        metrics, fold_records = cross_validate_params(
            X_candidate,
            y_candidate,
            params=params,
            candidate=index,
            cv_folds=cv_folds,
            random_state=random_state,
        )

        tuning_results.append({"params": params, "metrics": metrics})
        all_fold_records.extend(fold_records)
        summary_records.append(
            {
                "Candidate": index,
                "Parameters": format_params(params),
                **metrics,
                **params,
            }
        )

        report(
            f"  Mean CV: micro_f1={metrics['Mean Micro F1']:.4f} "
            f"(+/- {metrics['Micro F1 STD']:.4f}), "
            f"macro_f1={metrics['Mean Macro F1']:.4f}, "
            f"sample_f1={metrics['Mean Sample F1']:.4f}, "
            f"threshold={metrics['Mean Best Threshold']:.2f}"
        )

    best_result = max(
        tuning_results,
        key=lambda result: (
            result["metrics"]["Mean Micro F1"],
            result["metrics"]["Mean Sample F1"],
            result["metrics"]["Mean Macro F1"],
        ),
    )

    report("\nBest Neural Network Hyperparameters")
    report(str(best_result["params"]))
    report(
        f"Best CV micro_f1={best_result['metrics']['Mean Micro F1']:.4f}, "
        f"macro_f1={best_result['metrics']['Mean Macro F1']:.4f}, "
        f"sample_f1={best_result['metrics']['Mean Sample F1']:.4f}"
    )

    return best_result["params"], pd.DataFrame(summary_records), pd.DataFrame(all_fold_records)


def evaluate_model(
    model: Pipeline,
    X: pd.DataFrame,
    y: np.ndarray,
    label: str,
    threshold: float,
) -> tuple[dict, np.ndarray]:
    probabilities = positive_probabilities(model, X)
    predictions = apply_threshold(probabilities, threshold)

    metrics = {
        "Exact Match Accuracy": accuracy_score(y, predictions),
        "Hamming Loss": hamming_loss(y, predictions),
        "Micro Precision": precision_score(y, predictions, average="micro", zero_division=0),
        "Micro Recall": recall_score(y, predictions, average="micro", zero_division=0),
        "Micro F1": f1_score(y, predictions, average="micro", zero_division=0),
        "Macro Precision": precision_score(y, predictions, average="macro", zero_division=0),
        "Macro Recall": recall_score(y, predictions, average="macro", zero_division=0),
        "Macro F1": f1_score(y, predictions, average="macro", zero_division=0),
        "Weighted F1": f1_score(y, predictions, average="weighted", zero_division=0),
        "Sample F1": f1_score(y, predictions, average="samples", zero_division=0),
        "Average True Labels": float(y.sum(axis=1).mean()),
        "Average Predicted Labels": float(predictions.sum(axis=1).mean()),
    }

    report(f"\n{label} Results")
    for metric, value in metrics.items():
        report(f"{metric}: {value:.4f}")

    return metrics, predictions


def build_label_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    cuisine_names: np.ndarray,
) -> pd.DataFrame:
    report_dict = classification_report(
        y_true,
        y_pred,
        target_names=cuisine_names,
        output_dict=True,
        zero_division=0,
    )

    rows = []
    for cuisine in cuisine_names:
        metric = report_dict[cuisine]
        rows.append(
            {
                "Cuisine": cuisine,
                "Precision": metric["precision"],
                "Recall": metric["recall"],
                "F1-score": metric["f1-score"],
                "Support": metric["support"],
            }
        )

    return pd.DataFrame(rows).sort_values(
        ["F1-score", "Support", "Cuisine"],
        ascending=[False, False, True],
    )


def save_prediction_sample(
    results_dir: Path,
    X_test: pd.DataFrame,
    y_test: np.ndarray,
    y_pred: np.ndarray,
    mlb: MultiLabelBinarizer,
    max_rows: int = 100,
) -> None:
    actual = mlb.inverse_transform(y_test)
    predicted = mlb.inverse_transform(y_pred)

    sample = X_test.head(max_rows).copy()
    sample["Actual Cuisines"] = [", ".join(labels) for labels in actual[:max_rows]]
    sample["Predicted Cuisines"] = [", ".join(labels) for labels in predicted[:max_rows]]
    sample.to_csv(results_dir / "prediction_sample.csv", index=False)


def save_results(
    results_dir: Path,
    final_metrics: list[dict],
    label_metrics: pd.DataFrame,
    cuisine_frequency: pd.DataFrame,
    dropped_cuisines: pd.DataFrame,
    threshold_results: pd.DataFrame,
    cv_summary: pd.DataFrame | None = None,
    cv_folds: pd.DataFrame | None = None,
) -> None:
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "training_report.txt").write_text("\n".join(REPORT_LINES), encoding="utf-8")
    pd.DataFrame(final_metrics).to_csv(results_dir / "final_metrics.csv", index=False)
    label_metrics.to_csv(results_dir / "per_cuisine_metrics.csv", index=False)
    cuisine_frequency.to_csv(results_dir / "cuisine_frequency.csv", index=False)
    dropped_cuisines.to_csv(results_dir / "dropped_rare_cuisines.csv", index=False)
    threshold_results.to_csv(results_dir / "threshold_tuning.csv", index=False)

    if cv_summary is not None and not cv_summary.empty:
        cv_summary.to_csv(results_dir / "cv_hyperparameter_summary.csv", index=False)

    if cv_folds is not None and not cv_folds.empty:
        cv_folds.to_csv(results_dir / "cv_fold_metrics.csv", index=False)


def save_plots(
    results_dir: Path,
    final_metrics: list[dict],
    label_metrics: pd.DataFrame,
    cuisine_frequency: pd.DataFrame,
    threshold_results: pd.DataFrame,
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
    metric_names = [
        "Exact Match Accuracy",
        "Hamming Loss",
        "Micro Precision",
        "Micro Recall",
        "Micro F1",
        "Macro F1",
        "Weighted F1",
        "Sample F1",
        "Average Predicted Labels",
    ]

    fig = go.Figure()
    for index, metric in enumerate(metric_names):
        fig.add_trace(
            go.Bar(
                x=metrics_df["Dataset"],
                y=metrics_df[metric],
                name=metric,
                text=metrics_df[metric].round(4),
                textposition="auto",
                visible=index == 0,
            )
        )
    fig.update_layout(
        template=template,
        title="Neural Network Cuisine Metrics by Dataset Split",
        xaxis_title="Dataset Split",
        yaxis_title=metric_names[0],
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

    threshold_metric_names = ["Micro F1", "Macro F1", "Sample F1", "Exact Match Accuracy", "Hamming Loss"]
    fig = go.Figure()
    for index, metric in enumerate(threshold_metric_names):
        fig.add_trace(
            go.Scatter(
                x=threshold_results["Threshold"],
                y=threshold_results[metric],
                mode="lines+markers",
                name=metric,
                visible=index == 0,
            )
        )
    fig.update_layout(
        template=template,
        title="Validation Metrics by Prediction Threshold",
        xaxis_title="Threshold",
        yaxis_title=threshold_metric_names[0],
        updatemenus=[
            {
                "buttons": [
                    {
                        "label": metric,
                        "method": "update",
                        "args": [
                            {"visible": [name == metric for name in threshold_metric_names]},
                            {"yaxis": {"title": metric}},
                        ],
                    }
                    for metric in threshold_metric_names
                ],
                "direction": "down",
                "x": 1.12,
                "y": 1.15,
                "showactive": True,
            }
        ],
    )
    fig.write_html(results_dir / "threshold_tuning_toggle.html", include_plotlyjs=True)

    top_counts = [20, 40, min(75, len(cuisine_frequency))]
    top_counts = list(dict.fromkeys(count for count in top_counts if count > 0))
    fig = go.Figure()
    for index, top_n in enumerate(top_counts):
        top_cuisines = cuisine_frequency.head(top_n).sort_values("Count")
        fig.add_trace(
            go.Bar(
                x=top_cuisines["Count"],
                y=top_cuisines["Cuisine"],
                orientation="h",
                name=f"Top {top_n}",
                text=top_cuisines["Count"],
                textposition="auto",
                visible=index == 0,
            )
        )
    fig.update_layout(
        template=template,
        title="Cuisine Frequency",
        xaxis_title="Restaurant Count",
        yaxis_title="Cuisine",
        height=800,
        updatemenus=[
            {
                "buttons": [
                    {
                        "label": f"Top {top_n}",
                        "method": "update",
                        "args": [
                            {"visible": [count == top_n for count in top_counts]},
                            {"title": f"Top {top_n} Cuisine Frequencies"},
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
    fig.write_html(results_dir / "cuisine_frequency_toggle.html", include_plotlyjs=True)

    sorted_label_metrics = label_metrics.sort_values("F1-score")
    per_label_metric_names = ["F1-score", "Precision", "Recall", "Support"]
    fig = go.Figure()
    for index, metric in enumerate(per_label_metric_names):
        plot_data = sorted_label_metrics.tail(30) if metric == "Support" else sorted_label_metrics.head(30)
        fig.add_trace(
            go.Bar(
                x=plot_data[metric],
                y=plot_data["Cuisine"],
                orientation="h",
                name=metric,
                text=plot_data[metric].round(4),
                textposition="auto",
                visible=index == 0,
            )
        )
    fig.update_layout(
        template=template,
        title="Per-Cuisine Neural Network Performance",
        xaxis_title=per_label_metric_names[0],
        yaxis_title="Cuisine",
        height=800,
        updatemenus=[
            {
                "buttons": [
                    {
                        "label": metric,
                        "method": "update",
                        "args": [
                            {"visible": [name == metric for name in per_label_metric_names]},
                            {"xaxis": {"title": metric}},
                        ],
                    }
                    for metric in per_label_metric_names
                ],
                "direction": "down",
                "x": 1.12,
                "y": 1.15,
                "showactive": True,
            }
        ],
    )
    fig.write_html(results_dir / "per_cuisine_metrics_toggle.html", include_plotlyjs=True)

    if cv_summary is not None and not cv_summary.empty:
        cv_metric_names = [
            "Mean Micro F1",
            "Mean Macro F1",
            "Mean Sample F1",
            "Mean Hamming Loss",
            "Mean Exact Match Accuracy",
        ]
        fig = go.Figure()
        for index, metric in enumerate(cv_metric_names):
            fig.add_trace(
                go.Scatter(
                    x=cv_summary["Candidate"],
                    y=cv_summary[metric],
                    mode="lines+markers",
                    name=metric,
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
            title="Neural Network CV Metrics by Hyperparameter Candidate",
            xaxis_title="Candidate",
            yaxis_title=cv_metric_names[0],
            updatemenus=[
                {
                    "buttons": [
                        {
                            "label": metric,
                            "method": "update",
                            "args": [
                                {"visible": [name == metric for name in cv_metric_names]},
                                {"yaxis": {"title": metric}},
                            ],
                        }
                        for metric in cv_metric_names
                    ],
                    "direction": "down",
                    "x": 1.12,
                    "y": 1.15,
                    "showactive": True,
                }
            ],
        )
        fig.write_html(results_dir / "cv_candidate_metrics_toggle.html", include_plotlyjs=True)

    if cv_folds is not None and not cv_folds.empty:
        fold_metric_names = ["Micro F1", "Macro F1", "Sample F1", "Hamming Loss"]
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
                        text=group["Candidate"],
                        hovertemplate=f"Fold=%{{x}}<br>{metric}=%{{y:.4f}}<extra></extra>",
                        visible=metric == "Micro F1",
                    )
                )
        fig.update_layout(
            template=template,
            title="Neural Network CV Fold Metrics by Candidate",
            xaxis_title="Fold",
            yaxis_title="Micro F1",
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
        fig.write_html(results_dir / "cv_fold_metrics_toggle.html", include_plotlyjs=True)

    report("\nSaved interactive Plotly dark-theme graphs.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train a neural network for multi-label restaurant cuisine classification."
    )
    parser.add_argument(
        "--csv",
        default="cleaned_dataset.csv",
        help="Path to cleaned_dataset.csv. Default expects the CSV in the current workspace.",
    )
    parser.add_argument(
        "--model-output",
        default="cuisine_neural_network_model.pkl",
        help="Output path for the trained neural network pipeline",
    )
    parser.add_argument(
        "--label-binarizer-output",
        default="cuisine_neural_network_label_binarizer.pkl",
        help="Output path for the fitted MultiLabelBinarizer",
    )
    parser.add_argument(
        "--results-dir",
        default="cuisine_model_neural_network_results",
        help="Directory where reports, CSV files, and graphs will be saved",
    )
    parser.add_argument("--min-cuisine-samples", type=int, default=20)
    parser.add_argument("--test-size", type=float, default=0.15)
    parser.add_argument("--val-size", type=float, default=0.15)
    parser.add_argument("--threshold", type=float, default=None)
    parser.add_argument("--max-name-features", type=int, default=3000)
    parser.add_argument("--ngram-max", type=int, default=2)
    parser.add_argument("--tfidf-min-df", type=int, default=1)
    parser.add_argument("--hidden-layer-sizes", default="256", help="Comma-separated layer sizes, e.g. 256 or 256,128")
    parser.add_argument("--alpha", type=float, default=0.0001)
    parser.add_argument("--learning-rate-init", type=float, default=0.001)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--cv-folds", type=int, default=3)
    parser.add_argument("--tuning-trials", type=int, default=6)
    parser.add_argument("--skip-tuning", action="store_true")
    args = parser.parse_args()

    report("Cuisine Classification: TF-IDF + Neural Network")
    report(f"Dataset path: {args.csv}")
    report(f"Target column: {TARGET_COLUMN}")
    report(f"Text feature: {TEXT_FEATURE}")
    report(f"Categorical features: {CATEGORICAL_FEATURES}")
    report(f"Numeric features: {NUMERIC_FEATURES}")
    report(f"Leakage columns excluded: {LEAKAGE_COLUMNS}")
    report(f"Tuning trials: {args.tuning_trials}")
    report(f"Cross-validation folds: {args.cv_folds}")

    data = load_dataset(args.csv)

    if args.skip_tuning:
        hidden_layer_sizes = tuple(
            int(size.strip()) for size in args.hidden_layer_sizes.split(",") if size.strip()
        )
        best_params = {
            "min_cuisine_samples": args.min_cuisine_samples,
            "max_name_features": args.max_name_features,
            "ngram_max": args.ngram_max,
            "tfidf_min_df": args.tfidf_min_df,
            "hidden_layer_sizes": hidden_layer_sizes,
            "alpha": args.alpha,
            "learning_rate_init": args.learning_rate_init,
        }
        cv_summary = pd.DataFrame()
        cv_folds = pd.DataFrame()
        report("\nSkipping hyperparameter tuning. Training with provided/default parameters.")
    else:
        best_params, cv_summary, cv_folds = tune_hyperparameters(
            data,
            cv_folds=args.cv_folds,
            tuning_trials=args.tuning_trials,
            random_state=args.random_state,
        )

    report("\nFinal neural network parameters")
    report(str(best_params))

    X, y, mlb, cuisine_frequency, dropped_cuisines = prepare_features_and_labels(
        data,
        min_cuisine_samples=best_params["min_cuisine_samples"],
    )

    report("\nDataset Summary")
    report(f"Original rows: {data.shape[0]}")
    report(f"Rows used after rare-cuisine filtering: {X.shape[0]}")
    report(f"Original individual cuisines: {len(cuisine_frequency)}")
    report(f"Cuisine labels used in model: {len(mlb.classes_)}")
    report(f"Rare cuisine labels dropped: {len(dropped_cuisines)}")
    report(f"Average labels per used restaurant: {y.sum(axis=1).mean():.4f}")

    X_train, X_val, X_test, y_train, y_val, y_test = split_dataset(
        X,
        y,
        test_size=args.test_size,
        val_size=args.val_size,
        random_state=args.random_state,
    )

    report("\nDataset Split")
    report(f"Train     : {X_train.shape[0]} rows")
    report(f"Validation: {X_val.shape[0]} rows")
    report(f"Test      : {X_test.shape[0]} rows")

    model = build_model(best_params, random_state=args.random_state)

    report("\nTraining final neural network...")
    model.fit(X_train, y_train)
    report("Training complete.")

    if args.threshold is None:
        best_threshold, threshold_results = tune_threshold(model, X_val, y_val)
        report(f"\nBest validation threshold: {best_threshold:.2f}")
    else:
        best_threshold = args.threshold
        probabilities = positive_probabilities(model, X_val)
        y_val_pred = apply_threshold(probabilities, best_threshold)
        threshold_results = pd.DataFrame(
            [
                {
                    "Threshold": best_threshold,
                    "Micro F1": f1_score(y_val, y_val_pred, average="micro", zero_division=0),
                    "Macro F1": f1_score(y_val, y_val_pred, average="macro", zero_division=0),
                    "Sample F1": f1_score(y_val, y_val_pred, average="samples", zero_division=0),
                    "Hamming Loss": hamming_loss(y_val, y_val_pred),
                    "Exact Match Accuracy": accuracy_score(y_val, y_val_pred),
                }
            ]
        )
        report(f"\nUsing provided threshold: {best_threshold:.2f}")

    final_metrics = []
    predictions_by_split = {}
    for label, features, target in [
        ("Train", X_train, y_train),
        ("Validation", X_val, y_val),
        ("Test", X_test, y_test),
    ]:
        metrics, predictions = evaluate_model(model, features, target, label, best_threshold)
        final_metrics.append({"Dataset": label, **metrics})
        predictions_by_split[label] = predictions

    label_metrics = build_label_metrics(y_test, predictions_by_split["Test"], mlb.classes_)

    report("\nLowest Test F1 Cuisines")
    report(label_metrics.sort_values(["F1-score", "Support"]).head(15).to_string(index=False))

    report("\nHighest Test F1 Cuisines")
    report(label_metrics.sort_values(["F1-score", "Support"], ascending=[False, False]).head(15).to_string(index=False))

    model_output = Path(args.model_output)
    label_binarizer_output = Path(args.label_binarizer_output)
    joblib.dump(model, model_output)
    joblib.dump(mlb, label_binarizer_output)
    report(f"\nSaved model to: {model_output.resolve()}")
    report(f"Saved label binarizer to: {label_binarizer_output.resolve()}")

    results_dir = Path(args.results_dir)
    save_results(
        results_dir=results_dir,
        final_metrics=final_metrics,
        label_metrics=label_metrics,
        cuisine_frequency=cuisine_frequency,
        dropped_cuisines=dropped_cuisines,
        threshold_results=threshold_results,
        cv_summary=cv_summary,
        cv_folds=cv_folds,
    )
    save_prediction_sample(
        results_dir=results_dir,
        X_test=X_test,
        y_test=y_test,
        y_pred=predictions_by_split["Test"],
        mlb=mlb,
    )
    save_plots(
        results_dir=results_dir,
        final_metrics=final_metrics,
        label_metrics=label_metrics,
        cuisine_frequency=cuisine_frequency,
        threshold_results=threshold_results,
        cv_summary=cv_summary,
        cv_folds=cv_folds,
    )
    report(f"Saved reports and graphs to: {results_dir.resolve()}")
    (results_dir / "training_report.txt").write_text("\n".join(REPORT_LINES), encoding="utf-8")


if __name__ == "__main__":
    main()
