"""Module to pull and parse SAME and FIPS data"""
import requests
from io import StringIO
import csv

document_id = "1msvlkDtCgO42IRoIxX9z5IIDQU0Ocq5eLvbW_E__awA"

SAME_sheet_id = "0"
FIPS_sheet_id = "532761371"

SAME_sheet = "https://docs.google.com/spreadsheets/d/" + document_id + "/export?format=csv&gid=" + SAME_sheet_id
FIPS_sheet = "https://docs.google.com/spreadsheets/d/" + document_id + "/export?format=csv&gid=" + FIPS_sheet_id

SAME_response = requests.get(SAME_sheet)
FIPS_response = requests.get(FIPS_sheet)

SAME = list(csv.DictReader(StringIO(SAME_response.text), delimiter=","))
FIPS = list(csv.DictReader(StringIO(FIPS_response.text), delimiter=","))
