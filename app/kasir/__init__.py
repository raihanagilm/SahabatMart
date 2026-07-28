from flask import Blueprint

# PENTING: template_folder harus relatif ke file __init__.py ini
kasir_bp = Blueprint(
    'kasir', 
    __name__, 
    template_folder='../templates/kasir',
    static_folder='../static'
)

from app.kasir import routes