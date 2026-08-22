import os
import asyncio
from supabase import create_client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
if not url or not key:
    from dotenv import load_dotenv
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

supabase = create_client(url, key)
try:
    res = supabase.table("orders").insert({
        "event_id": "test",
        "guest_name": "test",
        "guest_contact": "test",
        "photo_ids": ["test1"],
        "total_price": 10.0,
        "status": "pending"
    }).execute()
    print("Success:", res)
except Exception as e:
    print("Error:", str(e))
