import numpy as np
import pandas as pd
import requests
import urllib.parse
import json
import os

from datetime import datetime
from google.oauth2.service_account import Credentials

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException

target_table = "real_estate.jakarta"
target_table_2 = "real_estate.most_recent"
project_id = "jakarta-housing-price"
credential_file = "jakarta-housing-price-595a9cff2797.json"
credential = Credentials.from_service_account_file(credential_file)
job_location = "asia-southeast2"

df = pd.read_csv("cleaned_data.csv")
most_recent = pd.read_csv("most_recent_data.csv")

numeric_columns = ["bedroom", "bathroom", "garage", "land_m2", "building_m2", "price_idr", "monthly_payment_idr"]
df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric)
most_recent[numeric_columns] = most_recent[numeric_columns].apply(pd.to_numeric)

df_without_timestamp = df.copy()
df_without_timestamp = df_without_timestamp.drop("scraped_timestamp", axis=1)

df_without_timestamp.to_gbq(
    destination_table=target_table,
    project_id=project_id,
    if_exists="append",
    location=job_location,
    chunksize=10_000,
    progress_bar=True,
    credentials=credential
)

most_recent_without_timestamp = most_recent.copy()
most_recent_without_timestamp = most_recent_without_timestamp.drop("scraped_timestamp", axis=1)

most_recent_without_timestamp.to_gbq(
    destination_table=target_table_2,
    project_id=project_id,
    if_exists="replace",
    location=job_location,
    progress_bar=True,
    credentials=credential
)