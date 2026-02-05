from app.core.mongodb import mongo_db


async def find_one_by_display_name(collection_name: str, display_name: str):
    collection = mongo_db[collection_name]

    doc = await collection.find_one({"displayName": display_name})

    if doc:
        doc["_id"] = str(doc["_id"])

    return doc

async def find_records_by_display_name(collection_name: str, display_name: str):
    collection = mongo_db[collection_name]

    cursor = collection.find({"displayName": display_name})
    docs = await cursor.to_list(length=None)   # length=None = no limit
# now docs is a list; use it
    if docs:
        for doc in docs:
            doc["_id"] = str(doc["_id"])

    return docs

