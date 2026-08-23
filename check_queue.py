import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY", os.environ.get("SUPABASE_KEY"))
supabase: Client = create_client(url, key)

res = supabase.table("photos").select("id", count="exact").eq("processed", False).execute()
print(f"Unprocessed photos count: {res.count}")
