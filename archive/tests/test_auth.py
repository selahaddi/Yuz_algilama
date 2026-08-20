import os
from supabase import create_client, Client
from dotenv import load_dotenv
import uuid

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", os.environ.get("SUPABASE_KEY", ""))

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

test_email = f"test_{uuid.uuid4()}@example.com"
test_password = "TestPassword123!"

print(f"Kayıt olunuyor: {test_email}")
try:
    res = supabase.auth.sign_up({"email": test_email, "password": test_password})
    print("Kayıt başarılı!", res)
except Exception as e:
    print(f"Kayıt Hatası: {e}")

print("Giriş yapılıyor...")
try:
    res = supabase.auth.sign_in_with_password({"email": test_email, "password": test_password})
    print("Giriş başarılı!")
except Exception as e:
    print(f"Giriş Hatası: {e}")
