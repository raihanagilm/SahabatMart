# app/__init__.py
from flask import Flask, redirect, url_for
from app.config import Config
from app.extensions import db, login_manager
from app.models import User

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    # Register Blueprint Auth
    from app.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # Register Blueprint Gudang
    from app.gudang import gudang_bp
    app.register_blueprint(gudang_bp, url_prefix='/gudang')
    
    # [BARU] Register Blueprint Kasir
    from app.kasir import kasir_bp
    app.register_blueprint(kasir_bp, url_prefix='/kasir')

    return app

