# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "charset-normalizer",
#     "matplotlib",
#     "pandas",
#     "python-dotenv",
#     "requests",
#     "scikit-learn",
#     "scipy",
#     "seaborn",
# ]
# ///

import os
import sys
import json
import dotenv
import pandas as pd
import seaborn as sns
from scipy.stats import zscore
from requests import Session
from typing import Dict, Any
from charset_normalizer import detect

# Constants
BASE_URL = "https://aiproxy.sanand.workers.dev/openai"
ENV_TOKEN_KEY = "AIPROXY_TOKEN"
HEATMAP_FILE = "heatmap.png"


# Load environment variables
def load_env() -> str:
    dotenv.load_dotenv()
    token = os.environ.get(ENV_TOKEN_KEY)
    if not token:
        print(f"Environment variable {ENV_TOKEN_KEY} not set. Exiting.")
        sys.exit(1)
    return token


# Load CSV file
def load_csv(filename: str) -> pd.DataFrame:
    with open(filename, "rb") as f:
        result = detect(f.read())
        print(f"Detected encoding: {result['encoding']}")

    try:
        return pd.read_csv(filename, encoding=result["encoding"])
    except Exception as e:
        print(f"Error loading CSV file: {e}")
        sys.exit(1)


# Generate dataset summary
def generate_summary(df: pd.DataFrame) -> Dict[str, Any]:
    return {
        "total_columns": len(df.columns),
        "data_types": {
            str(dtype): sum(df.dtypes == dtype) for dtype in df.dtypes.unique()
        },
        "columns_with_nulls": [col for col in df.columns if df[col].isnull().any()],
    }


# Save heatmap of missing data
def save_heatmap(df: pd.DataFrame) -> None:
    heatmap = sns.heatmap(df.isnull(), cbar=False, cmap="viridis")
    fig = heatmap.get_figure()
    fig.savefig(HEATMAP_FILE)
    print(f"Heatmap saved as {HEATMAP_FILE}")


# Define AI functions
def numerical_summary(column: str, df: pd.DataFrame) -> Dict[str, Any]:
    if df[column].dtype in ["float64", "int64"]:
        return {"column": column, "summary": df[column].describe().to_dict()}
    return {"error": f"{column} is not a numerical column."}


def detect_outliers(column: str, df: pd.DataFrame) -> Dict[str, Any]:
    if df[column].dtype in ["float64", "int64"]:
        # Drop NaN values before calculating z-scores
        valid_values = df[column].dropna()
        z_scores = zscore(valid_values)
        # Create a mask aligned with the original DataFrame
        mask = (z_scores > 3) | (z_scores < -3)
        outliers = valid_values[mask]  # Select outliers
        return {"column": column, "outliers": outliers.tolist()}
    return {"error": f"{column} is not a numerical column."}


# Prepare HTTP session
def initialize_session(token: str) -> Session:
    session = Session()
    session.headers.update({"Authorization": f"Bearer {token}"})
    return session


# Make chat request
def chat_request(session: Session, payload: Dict[str, Any]) -> Any:
    try:
        response = session.post(f"{BASE_URL}/v1/chat/completions", json=payload)
        if response.ok:
            return response.json()
        print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")
    return None


# Main function
def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: script.py <csv_file>")
        sys.exit(1)

    # Load environment and CSV
    token = load_env()
    filename = sys.argv[1]
    df = load_csv(filename)

    # Generate summary and save heatmap
    info_summary = generate_summary(df)
    save_heatmap(df)

    # Prepare payload for AI interaction
    session = initialize_session(token)

    stat_data = {}

    for col in df.columns:
        if df[col].dtype in ["float64", "int64"]:
            numercial_data = {
                "summary": numerical_summary(col, df),
                "outliers": detect_outliers(col, df),
            }

            stat_data[col] = numercial_data

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "user",
                "content": f"Find evidence of fraud using numerical analysis and present a story-based report. \
CSV columns: {df.columns.tolist()}. First 2 rows: {df.head(2).to_json()}. this is the basic analysis of the data. Summary: {info_summary}. \
{json.dumps(stat_data)} any columns not included are not numerical values. For your report start with a summary before presenting your findings DO NOT HALUCINATE",
            }
        ],
    }
    # print(json.dumps(payload))
    # perform chat interaction
    result = chat_request(session, payload)
    if result:
        content = result["choices"][0]["message"]["content"]

        with open("README.md", "w+") as f:
            f.write(content)


if __name__ == "__main__":
    main()
