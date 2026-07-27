# app/auth/__init__.py
from flask import Blueprint

# Inisialisasi Blueprint
auth_bp = Blueprint('auth', __name__, template_folder='../templates/auth')

# [PERBAIKAN] Gunakan relative import (titik) untuk mengimpor routes
from . import routes 