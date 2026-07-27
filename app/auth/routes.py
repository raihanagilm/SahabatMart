from flask import render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.auth import auth_bp
from app.models import User
from app.extensions import db

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Jika sudah login, redirect sesuai role
    if current_user.is_authenticated:
        if current_user.role == 'GUDANG':
            return redirect(url_for('inventory.dashboard')) # Nanti kita buat
        elif current_user.role == 'KASIR':
            return redirect(url_for('pos.dashboard'))       # Nanti kita buat
        return redirect(url_for('main.home'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            # Cek apakah user adalah Gudang atau Kasir
            if user.role in ['GUDANG', 'KASIR']:
                login_user(user)
                flash(f'Login berhasil! Selamat datang, {user.full_name}.', 'success')
                
                # Redirect berdasarkan role
                if user.role == 'GUDANG':
                    return redirect(url_for('inventory.dashboard'))
                else:
                    return redirect(url_for('pos.dashboard'))
            else:
                flash('Akun ini bukan untuk Gudang atau Kasir.', 'warning')
        else:
            flash('Email atau password salah.', 'danger')

    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Anda telah logout.', 'info')
    return redirect(url_for('auth.login'))