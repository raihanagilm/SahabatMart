# app/auth/routes.py
from flask import render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user

# [PERBAIKAN] Gunakan relative import untuk auth_bp
from . import auth_bp 

from app.models import User
from app.extensions import db

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # Redirect sementara sampai dashboard dibuat
        return redirect(url_for('gudang.dashboard')) 

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            # [PERBAIKAN] Tambahkan role SUPER_GUDANG dan KARYAWAN_GUDANG
            allowed_roles = ['SUPER_GUDANG', 'KARYAWAN_GUDANG', 'GUDANG', 'KASIR']
            
            if user.role in allowed_roles:
                login_user(user)
                flash(f'Login berhasil! Selamat datang, {user.full_name}.', 'success')
                
                # Redirect berdasarkan role
                if user.role in ['SUPER_GUDANG', 'KARYAWAN_GUDANG', 'GUDANG']:
                    return redirect(url_for('gudang.dashboard'))
                elif user.role == 'KASIR':
                    # Nanti akan kita buat blueprint 'pos'
                    return redirect(url_for('pos.dashboard')) 
            else:
                flash('Akun ini bukan untuk staf operasional (Gudang/Kasir).', 'warning')
        else:
            flash('Email atau password salah.', 'danger')

    return render_template('login.html')

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        # TODO: Logika untuk mengirim email reset password akan ditambahkan di Epoch selanjutnya
        flash(f'Jika email {email} terdaftar, instruksi reset password telah dikirim.', 'info')
        return redirect(url_for('auth.login'))
        
    return render_template('forgot_password.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Anda telah logout.', 'info')
    return redirect(url_for('auth.login'))