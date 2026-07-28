# app/__init__.py
from flask import Flask, redirect, url_for, request
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
    # Di dalam fungsi create_app(), setelah app = Flask(__name__)

    @app.after_request
    def add_cache_headers(response):
        """Tambahkan cache headers untuk static files"""
        
        # Cache untuk gambar dan static assets (1 tahun)
        if request.path.startswith('/static/'):
            if any(request.path.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.ico', '.svg', '.webp']):
                response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
                response.headers['Expires'] = 'Thu, 31 Dec 2037 23:59:59 GMT'
            
            # Cache untuk CSS dan JS (1 minggu)
            elif any(request.path.endswith(ext) for ext in ['.css', '.js']):
                response.headers['Cache-Control'] = 'public, max-age=604800'  # 7 hari
        
        return response

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

