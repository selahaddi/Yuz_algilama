import sys
import os

# Yüz_Tanıma_&_Kategori/venv/bin/activate
sys.path.append(os.path.join(os.getcwd(), '..', 'Yüz_Tanıma_&_Kategori'))

import urllib.request
import json

try:
    req = urllib.request.Request("http://127.0.0.1:8503/api/clusters/042f7b85-67f5-4fc8-880c-67604469ba18")
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read().decode())
        print(json.dumps(data, indent=2))
except Exception as e:
    print(e)
