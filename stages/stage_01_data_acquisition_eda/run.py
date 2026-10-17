import io
import json
import zipfile
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import requests
import seaborn as sns

plt.switch_backend("Agg")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "processed"
ARTIFACT_DIR = PROJECT_ROOT / "artifacts" / "stage_01"
UCI_URL = "https://archive.ics.uci.edu/static/public/45/heart+disease.zip"
COLUMNS = [
    "age", "sex", "cp", "trestbps", "chol", "fbs", "restecg",
    "thalach", "exang", "oldpeak", "slope", "ca", "thal", "num",
]
NUMERIC_FEATURES = ["age", "trestbps", "chol", "thalach", "oldpeak"]
CATEGORICAL_FEATURES = ["sex", "cp", "fbs", "restecg", "exang", "slope", "ca", "thal"]


def acquire_data() -> tuple[pd.DataFrame, str]:
    response = requests.get(UCI_URL, timeout=30)
    response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        member = next(
            name for name in archive.namelist() if name.endswith("processed.cleveland.data")
        )
        with archive.open(member) as source:
            return pd.read_csv(source, header=None, names=COLUMNS, na_values="?"), member


def clean_data(raw: pd.DataFrame) -> pd.DataFrame:
    clean = raw.apply(pd.to_numeric, errors="coerce").dropna(subset=["num"]).copy()
    for column in NUMERIC_FEATURES:
        clean[column] = clean[column].fillna(clean[column].median())
    for column in CATEGORICAL_FEATURES:
        clean[column] = clean[column].fillna(clean[column].mode().iloc[0])
    clean["target"] = (clean.pop("num") > 0).astype(int)
    return clean


def write_eda(clean: pd.DataFrame) -> None:
    sns.set_theme(style="whitegrid", context="notebook")
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    figure, axes = plt.subplots(2, 3, figsize=(14, 8))
    for axis, column in zip(axes.flat, NUMERIC_FEATURES, strict=False):
        sns.histplot(
            data=clean, x=column, hue="target", kde=True, element="step",
            stat="density", common_norm=False, ax=axis,
        )
        axis.set_title(column.replace("_", " ").title())
    axes.flat[-1].axis("off")
    figure.suptitle("Continuous feature distributions by target", y=1.02, fontsize=15)
    figure.tight_layout()
    figure.savefig(ARTIFACT_DIR / "feature_distributions.png", dpi=160, bbox_inches="tight")
    plt.close(figure)

    figure, axis = plt.subplots()
    class_counts = clean["target"].value_counts().sort_index()
    sns.barplot(x=class_counts.index.astype(str), y=class_counts.values, color="#277da1", ax=axis)
    axis.set(
        title="Heart disease target balance",
        xlabel="Target (0 = absent, 1 = present)",
        ylabel="Patients",
    )
    figure.tight_layout()
    figure.savefig(ARTIFACT_DIR / "class_balance.png", dpi=160, bbox_inches="tight")
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(12, 9))
    sns.heatmap(
        clean.corr(numeric_only=True), cmap="vlag", center=0, annot=True,
        fmt=".2f", linewidths=0.4, square=True, ax=axis,
    )
    axis.set_title("Feature correlation matrix (coded categories treated numerically)")
    figure.tight_layout()
    figure.savefig(ARTIFACT_DIR / "correlation_heatmap.png", dpi=160, bbox_inches="tight")
    plt.close(figure)

    summary = {
        "rows": len(clean),
        "columns": clean.columns.tolist(),
        "missing_values": int(clean.isna().sum().sum()),
        "class_counts": {str(key): int(value) for key, value in class_counts.items()},
    }
    (ARTIFACT_DIR / "eda_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    raw, member = acquire_data()
    clean = clean_data(raw)
    output_path = DATA_DIR / "heart_disease.csv"
    clean.to_csv(output_path, index=False)
    write_eda(clean)
    print(f"Source: {member}")
    print(f"Saved {len(clean)} rows to {output_path}")
    print(f"EDA artifacts: {ARTIFACT_DIR}")


if __name__ == "__main__":
    main()