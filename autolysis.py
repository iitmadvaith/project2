# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "matplotlib",
#     "pandas",
#     "python-dotenv",
#     "requests",
#     "scipy",
#     "seaborn",
#     "scikit-learn",
# ]
# ///

import os
import sys
import json
import dotenv
import pandas
import seaborn as sns
from scipy.stats import zscore
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


# load AIPROXY_TOKEN from environment
dotenv.load_dotenv()
AIPROXY_TOKEN = os.environ.get("AIPROXY_TOKEN")

# Ensure that the token is actually set
if not AIPROXY_TOKEN:
    print("env var AIPROXY_TOKEN not set bailing")
    exit(1)

# make sure we have one argument which is the csv file
if len(sys.argv) != 2:
    print("Too many arguments or too few")
    exit(1)

# load csv file for analyis
filename = sys.argv[1]
df = pandas.read_csv(filename)


def numerical_summary(df, column):
    if df[column].dtype in ["float64", "int64"]:
        summary = df[column].describe().to_dict()
        return json.dumps({"column": column, "summary": summary}, indent=4)
    return json.dumps({"error": f"{column} is not a numerical column."}, indent=4)


def detect_outliers(df, column):
    if df[column].dtype in ["float64", "int64"]:
        z_scores = zscore(df[column].dropna())
        outliers = df.loc[(z_scores > 3) | (z_scores < -3), column]
        return json.dumps({"column": column, "outliers": outliers.tolist()}, indent=4)
    return json.dumps({"error": f"{column} is not a numerical column."}, indent=4)


def extract_datetime_features(df, column):
    if df[column].dtype == "datetime64[ns]":
        features = {
            "year": df[column].dt.year.tolist(),
            "month": df[column].dt.month.tolist(),
            "day": df[column].dt.day.tolist(),
            "weekday": df[column].dt.weekday.tolist(),
        }
        return json.dumps({"column": column, "features": features}, indent=4)
    return json.dumps({"error": f"{column} is not a datetime column."}, indent=4)


# some basic info
info = df.info()
null_info = df.isnull().sum()

# generate heatmap
heatmap = sns.heatmap(df.isnull(), cbar=False, cmap="viridis")
fig = heatmap.get_figure()
fig.savefig("heatmap.png")
