# app/auth/routes.py
from flask import render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user

# [PERBAIKAN] Gunakan relative import untuk auth_bp
from . import auth_bp 

from app.models import User, ActivityLog
from app.extensions import db

# Helper function untuk logging aktivitas
def log_activity(action, description=None):
    log = ActivityLog(
        user_id=current_user.id if current_user.is_authenticated else None,
        action=action,
        description=description,
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('gudang.dashboard')) 

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            # [PERBAIKAN] Tambahkan SUPER_KASIR dan KARYAWAN_KASIR
            allowed_roles = [
                'SUPER_GUDANG', 'KARYAWAN_GUDANG', 'GUDANG', 
                'SUPER_KASIR', 'KARYAWAN_KASIR', 'KASIR'
            ]
            
            if user.role in allowed_roles:
                # Cek apakah akun aktif
                if not user.is_active:
                    flash('Akun Anda telah dinonaktifkan. Hubungi Super Admin.', 'danger')
                    return redirect(url_for('auth.login'))
                
                login_user(user)
                
                # Log aktivitas login
                log = ActivityLog(
                    user_id=user.id,
                    action='LOGIN',
                    description=f'Login berhasil: {user.email}',
                    ip_address=request.remote_addr
                )
                db.session.add(log)
                db.session.commit()
                
                flash(f'Login berhasil! Selamat datang, {user.full_name}.', 'success')
                
                # [PERBAIKAN] Redirect berdasarkan role yang lebih spesifik
                if user.role in ['SUPER_GUDANG', 'KARYAWAN_GUDANG', 'GUDANG']:
                    return redirect(url_for('gudang.dashboard'))
                elif user.role in ['SUPER_KASIR', 'KARYAWAN_KASIR', 'KASIR']:
                    return redirect(url_for('kasir.dashboard')) # Arahkan ke kasir
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
    # [BARU] Log aktivitas logout
    log = ActivityLog(
        user_id=current_user.id,
        action='LOGOUT',
        description=f'Logout: {current_user.email}',
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    logout_user()
    flash('Anda telah logout.', 'info')
    return redirect(url_for('auth.login'))