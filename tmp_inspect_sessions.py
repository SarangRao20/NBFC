import asyncio
from db.database import sessions_collection

async def inspect():
    docs = await sessions_collection.find({}, {'session_id':1, 'customer_data.phone':1}).to_list(length=20)
    for d in docs:
        print(d)

asyncio.run(inspect())
