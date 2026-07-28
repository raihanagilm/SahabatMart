# api/index.py
import sys
import os

# Tambahkan root directory ke path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

# Vercel handler
app = create_app()

# Vercel serverless handler
def handler(request):
    return app(request.environ, lambda *args: None)