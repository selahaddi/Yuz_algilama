import sys
import os

from dotenv import load_dotenv
load_dotenv("../Yüz_Tanıma_&_Kategori/.env")

from supabase import create_client
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)
res = supabase.table("photos").select("*").limit(1).execute()
print(res.data[0].keys() if res.data else "No data")
