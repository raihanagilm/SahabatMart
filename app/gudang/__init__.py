from flask import Blueprint

gudang_bp = Blueprint('gudang', __name__, template_folder='../templates/gudang')

from app.gudang import routes