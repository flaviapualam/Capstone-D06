import os
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=True)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME   = os.getenv("MONGO_DB", "capstone_d06")
COLL_NAME = os.getenv("MONGO_COLL", "readings")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

if COLL_NAME not in db.list_collection_names():
    db.create_collection(
        COLL_NAME,
        timeseries={"timeField": "ts", "granularity": "seconds"},
        expireAfterSeconds=14*24*3600
    )
    db[COLL_NAME].create_index([("uuid", 1), ("ts", -1)])
print("Time-series collection ready.")
