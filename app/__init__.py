from flask import Flask, redirect, url_for
from werkzeug.middleware.proxy_fix import ProxyFix  # <-- TAMBAHKAN INI
from app.config import Config
from app.extensions import db, login_manager
from app.models import User

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # TAMBAHKAN INI: Beritahu Flask bahwa dia berada di belakang proxy Vercel (HTTPS)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # Nonaktifkan strict slashes untuk mencegah loop /route vs /route/
    app.url_map.strict_slashes = False

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

    # Register Blueprint Kasir
    from app.kasir import kasir_bp
    app.register_blueprint(kasir_bp, url_prefix='/kasir')

    return app