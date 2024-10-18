import asyncio

from pymongo import AsyncMongoClient

from deposit.config import MONGO_URI

client = AsyncMongoClient(MONGO_URI)
db = client["transaction_database"]
transfer_collection = db["transfer"]
address_collection = db["user_addresses"]
asyncio.run(address_collection.create_index("address", unique=True))
asyncio.run(address_collection.create_index("user_id", unique=True))
