import numpy as np
import pandas as pd
import requests
import urllib.parse
import json
import os
import re

from datetime import datetime
from google.oauth2.service_account import Credentials
from geopy.geocoders import Nominatim

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException

df = pd.read_csv("scraped_data.csv")

target_table = "real_estate.jakarta"
target_table_2 = "real_estate.most_recent"
project_id = "jakarta-housing-price"
credential_file = "jakarta-housing-price-595a9cff2797.json"
credential = Credentials.from_service_account_file(credential_file)
job_location = "asia-southeast2"

query_most_recent = pd.read_gbq(f"SELECT * FROM `{project_id}.{target_table_2}`", project_id=project_id, credentials=credential)
query_most_recent["date"] = query_most_recent["date"].dt.tz_localize(None)

month_mapping = {
    "(?i)Januari": "January",
    "(?i)Februari": "February",
    "(?i)Maret": "March",
    "(?i)April": "April",
    "(?i)Mei": "May",
    "(?i)Juni": "June",
    "(?i)Juli": "July",
    "(?i)Agustus": "August",
    "(?i)September": "September",
    "(?i)Oktober": "October",
    "(?i)November": "November",
    "(?i)Desember": "December"
}

def convert_price(price):
    number_split = price.split(" ")

    numeric = float(number_split[0].replace(",", "."))
    suffix = number_split[1]

    if "triliun" in suffix.lower():
        multiplier = 10**12
    elif "miliar" in suffix.lower():
        multiplier = 10**9
    elif "juta" in suffix.lower():
        multiplier = 10**6
    else:
        multiplier = 1

    numeric *= multiplier
    return numeric

geolocator = Nominatim(user_agent="my_user_agent")

def get_district(text):
    if "Kav" in text:
        text = text.replace("Kav", "Kavling")

    cities = ["Jakarta Utara", "Jakarta Timur", "Jakarta Selatan", "Jakarta Barat", "Jakarta Pusat"]

    if "bintaro" in text.lower():
        result = "Pesanggrahan, Jakarta Selatan"
    elif "daan mogot" in text.lower():
        result = "Grogol Petamburan, Jakarta Barat"
    else:
        try:
            location = geolocator.geocode(text)
            if location is not None:
                address = location.raw["display_name"]
                for city in cities:
                    if city in address:
                        district = address.split(city)[0].strip()
                        district = district.split(",")
                        district = district[-2].strip()
                        break
                result = f"{district}, {city}"
            else:
                result = np.nan
        except:
            result = np.nan

    return result

df["Date"] = df["Date"].str.replace("Diperbarui sejak ", "").str.replace(",", "")
df["Date"] = df["Date"].replace(month_mapping, regex=True)
df["Date"] = pd.to_datetime(df["Date"])

df["Price IDR"] = df["Price"].str.split("\n").str[0].str.replace("Rp ", "")
df["Price IDR"] = df["Price IDR"].apply(convert_price)

df["Monthly Payment IDR"] = df["Price"].str.split("\n").str[1].str.replace("Cicilan : ", "").str.replace(" per bulan", "")
df["Monthly Payment IDR"] = df["Monthly Payment IDR"].apply(convert_price)

df["Scraped Timestamp"] = pd.to_datetime(df["Scraped Timestamp"])

df = df.drop("Price", axis=1)
df = df[["Date", "Title", "Link", "Location", "Bedroom", "Bathroom", "Garage", "Land m2", "Building m2", "Price IDR", "Monthly Payment IDR", "Agent", "Scraped Timestamp"]]
df.columns = df.columns.str.lower().str.replace(" ", "_")

for col in ["bedroom", "bathroom", "garage", "land_m2", "building_m2", "price_idr", "monthly_payment_idr"]:
    df[col] = df[col].astype(float)

df = df.drop_duplicates(subset=["title", "location", "bedroom", "bathroom", "garage", "land_m2", "building_m2"]).reset_index(drop=True)

condition = (
    (df["title"] == query_most_recent["title"][0]) &
    (df["link"] == query_most_recent["link"][0]) &
    (df["location"] == query_most_recent["address"][0]) &
    (df["agent"] == query_most_recent["agent"][0])
)

df = df[~condition]
df = df.rename(columns={"location": "address"})

jkt_districts = pd.read_excel("jakarta_districts.xlsx")

unique_locations = pd.DataFrame({"address": df["address"].unique()})
unique_locations["district"] = unique_locations["address"].apply(get_district)
unique_locations["district"] = unique_locations["district"].str.replace(r"(?i)\b(kec(?:amatan)?|kec)\b\.?|^\.|\.$", "", regex=True).str.strip()

updated_unique_locations = unique_locations.merge(jkt_districts, left_on="district", right_on="district_city", how="inner")
updated_unique_locations = updated_unique_locations[["address", "district_x", "kemendagri_code", "latitude_longitude"]]
updated_unique_locations = updated_unique_locations.rename(columns={"district_x": "district"})

merged_df = df.merge(updated_unique_locations, on="address", how="inner").reset_index(drop=True)
merged_df = merged_df[["date", "title", "link", "address", "district", "kemendagri_code", "latitude_longitude", "bedroom", "bathroom", "garage", "land_m2", "building_m2", "price_idr", "monthly_payment_idr", "agent", "scraped_timestamp"]]

merged_df.to_csv("cleaned_data.csv", index=False)

most_recent = merged_df[merged_df["scraped_timestamp"] == merged_df["scraped_timestamp"].min()]
most_recent.to_csv("most_recent_data.csv", index=False)