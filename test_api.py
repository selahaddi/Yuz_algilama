import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

res = supabase.table("events").select("*, studios(name, primary_color, logo_url, watermark_text)").execute()
print(res.data)
