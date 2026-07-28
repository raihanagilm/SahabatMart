# api/index.py
import sys
import os

# Tambahkan root directory ke path agar import 'app' berhasil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

# Vercel membutuhkan instance Flask bernama 'app' di level module
app = create_app()