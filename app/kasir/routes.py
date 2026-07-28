from flask import render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime
from sqlalchemy import or_
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from . import kasir_bp
from app.models import User, Product, Order, OrderItem, StockMutation, ActivityLog
from app.extensions import db

# Decorator untuk membatasi akses hanya untuk role Kasir
def kasir_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role not in ['SUPER_KASIR', 'KARYAWAN_KASIR']:
            flash('Akses ditolak. Halaman ini khusus untuk staf Kasir.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# Helper function untuk mencatat aktivitas (sama seperti di modul gudang)
def log_activity(action, description=None):
    log = ActivityLog(
        user_id=current_user.id if current_user.is_authenticated else None,
        action=action,
        description=description,
        ip_address=request.remote_addr
    )
    db.session.add(log)

# ==========================================
# DASHBOARD KASIR
# ==========================================
@kasir_bp.route('/dashboard')
@kasir_required
def dashboard():
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 1. Hitung total transaksi dan revenue langsung dari DB (1 Query)
    stats = db.session.query(
        func.count(Order.id).label('total_tx'),
        func.coalesce(func.sum(Order.total_amount), 0).label('total_rev')
    ).filter(
        Order.order_type == 'POS',
        Order.created_at >= today_start,
        Order.payment_status == 'SUCCESS'
    ).first()
    
    total_transactions_today = stats.total_tx or 0
    total_revenue_today = float(stats.total_rev or 0)
    
    # 2. Hitung total item terjual dengan JOIN (1 Query, bukan N+1)
    items_sold = db.session.query(func.coalesce(func.sum(OrderItem.quantity), 0)).join(Order).filter(
        Order.order_type == 'POS',
        Order.created_at >= today_start,
        Order.payment_status == 'SUCCESS'
    ).scalar()
    
    total_items_sold_today = items_sold or 0
    avg_transaction = total_revenue_today / total_transactions_today if total_transactions_today > 0 else 0

    return render_template('kasir/dashboard.html',
                           total_transactions=total_transactions_today,
                           total_revenue=total_revenue_today,
                           total_items_sold=total_items_sold_today,
                           avg_transaction=avg_transaction)
    
# ==========================================
# MANAJEMEN KARYAWAN KASIR (Khusus Super Kasir)
# ==========================================
@kasir_bp.route('/employees')
@kasir_required
def employees():
    if current_user.role != 'SUPER_KASIR':
        flash('Hanya Super Kasir yang bisa melihat daftar karyawan kasir.', 'warning')
        return redirect(url_for('kasir.dashboard'))
        
    staff = User.query.filter(User.role.in_(['SUPER_KASIR', 'KARYAWAN_KASIR'])).all()
    return render_template('employees.html', staff=staff)

@kasir_bp.route('/employees/add', methods=['GET', 'POST'])
@kasir_required
def add_employee():
    if current_user.role != 'SUPER_KASIR':
        flash('Akses ditolak.', 'danger')
        return redirect(url_for('kasir.dashboard'))

    if request.method == 'POST':
        from werkzeug.security import generate_password_hash
        if User.query.filter_by(email=request.form['email']).first():
            flash('Email sudah terdaftar!', 'danger')
            return redirect(url_for('kasir.add_employee'))

        new_staff = User(
            email=request.form['email'],
            password_hash=generate_password_hash(request.form['password']),
            full_name=request.form['full_name'],
            role='KARYAWAN_KASIR'
        )
        db.session.add(new_staff)
        db.session.commit()
        
        log_activity('ADD_KASIR_EMPLOYEE', f'Menambahkan karyawan kasir baru: {new_staff.full_name}')
        
        flash('Karyawan kasir berhasil ditambahkan!', 'success')
        return redirect(url_for('kasir.employees'))
        
    return render_template('employee_form.html')

@kasir_bp.route('/employees/<int:employee_id>/toggle-status', methods=['POST'])
@kasir_required
def toggle_employee_status(employee_id):
    if current_user.role != 'SUPER_KASIR':
        flash('Akses ditolak.', 'danger')
        return redirect(url_for('kasir.dashboard'))
    
    employee = User.query.get_or_404(employee_id)
    
    if employee.id == current_user.id:
        flash('Anda tidak bisa menonaktifkan akun Anda sendiri!', 'danger')
        return redirect(url_for('kasir.employees'))
    
    employee.is_active = not employee.is_active
    db.session.commit()
    
    status_text = 'diaktifkan' if employee.is_active else 'dinonaktifkan'
    log_activity('TOGGLE_KASIR_STATUS', f'{status_text.capitalize()} karyawan kasir: {employee.full_name}')
    
    flash(f'Karyawan {employee.full_name} berhasil {status_text}!', 'success')
    return redirect(url_for('kasir.employees'))

# ==========================================
# LOG AKTIVITAS KASIR (Khusus Super Kasir)
# ==========================================
@kasir_bp.route('/activity-logs')
@kasir_required
def activity_logs():
    if current_user.role != 'SUPER_KASIR':
        flash('Hanya Super Kasir yang bisa melihat log aktivitas.', 'warning')
        return redirect(url_for('kasir.dashboard'))
    
    page = request.args.get('page', 1, type=int)
    # Filter log hanya untuk aksi yang berhubungan dengan kasir
    kasir_actions = ['LOGIN', 'LOGOUT', 'POS_TRANSACTION', 'ADD_KASIR_EMPLOYEE', 'TOGGLE_KASIR_STATUS']
    logs = ActivityLog.query.filter(ActivityLog.action.in_(kasir_actions)).order_by(ActivityLog.created_at.desc()).paginate(page=page, per_page=20)
    
    return render_template('activity_logs.html', logs=logs)

# ==========================================
# HALAMAN TRANSAKSI (POS)
# ==========================================
@kasir_bp.route('/pos')
@kasir_required
def pos():
    return render_template('pos.html')

# API: Mencari Produk untuk POS (dengan Pagination)
@kasir_bp.route('/api/products')
@kasir_required
def api_products():
    q = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 24, type=int)  # Default 24 produk per halaman
    
    query = Product.query.filter_by(is_active=True)
    
    if q:
        query = query.filter(or_(Product.name.ilike(f'%{q}%'), Product.sku.ilike(f'%{q}%')))
    
    # Paginasi
    products_paginated = query.order_by(Product.name).paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'products': [{
            'id': p.id,
            'sku': p.sku,
            'name': p.name,
            'price': float(p.price),
            'stock': p.stock,
            'has_image': p.image_blob is not None
        } for p in products_paginated.items],
        'pagination': {
            'current_page': products_paginated.page,
            'total_pages': products_paginated.pages,
            'total_items': products_paginated.total,
            'has_next': products_paginated.has_next,
            'has_prev': products_paginated.has_prev
        }
    })
    
    
# [BARU] Endpoint untuk serve gambar produk dari BLOB (untuk kasir)
@kasir_bp.route('/products/<int:product_id>/image')
@kasir_required
def product_image(product_id):
    from flask import Response
    
    product = Product.query.get_or_404(product_id)
    
    if not product.image_blob:
        # Return placeholder atau 404 jika tidak ada gambar
        return Response(status=404)
    
    # Return gambar dengan cache headers yang agresif
    return Response(
        product.image_blob,
        mimetype='image/jpeg',
        headers={
            'Cache-Control': 'public, max-age=31536000, immutable',  # Cache 1 tahun
            'Expires': 'Thu, 31 Dec 2037 23:59:59 GMT',
            'Pragma': 'public',
            'Vary': 'Accept-Encoding'
        }
    )

# API: Proses Checkout Transaksi POS (AJAX)
@kasir_bp.route('/pos/checkout', methods=['POST'])
@kasir_required
def pos_checkout():
    data = request.get_json()
    cart_items = data.get('items', [])
    payment_method = data.get('payment_method', 'CASH')
    
    if not cart_items:
        return jsonify({'success': False, 'message': 'Keranjang kosong!'}), 400
        
    # Generate order number unik berdasarkan timestamp
    now = datetime.now()
    order_number = f"POS-{now.strftime('%Y%m%d%H%M%S')}"
    
    total_amount = 0
    order_items_data = []
    
    # 1. Validasi stok dan hitung total
    for item in cart_items:
        product = Product.query.get(item['product_id'])
        if not product:
            return jsonify({'success': False, 'message': f'Produk tidak ditemukan.'}), 400
        if product.stock < item['quantity']:
            return jsonify({'success': False, 'message': f'Stok {product.name} tidak mencukupi (Tersedia: {product.stock}).'}), 400
            
        subtotal = float(product.price) * item['quantity']
        total_amount += subtotal
        order_items_data.append({
            'product_id': product.id,
            'quantity': item['quantity'],
            'price_at_purchase': float(product.price)
        })
        
    # 2. Buat Order Utama
    new_order = Order(
        order_number=order_number,
        user_id=current_user.id,
        order_type='POS',
        total_amount=total_amount,
        payment_method=payment_method,
        payment_status='SUCCESS', # Langsung sukses untuk POS
        status='COMPLETED'
    )
    db.session.add(new_order)
    db.session.flush() # Flush untuk mendapatkan ID order sebelum commit
    
    # 3. Buat Order Items, Kurangi Stok, & Catat Mutasi
    for item_data in order_items_data:
        # Tambah ke detail order
        new_item = OrderItem(
            order_id=new_order.id,
            product_id=item_data['product_id'],
            quantity=item_data['quantity'],
            price_at_purchase=item_data['price_at_purchase']
        )
        db.session.add(new_item)
        
        # Kurangi stok produk
        product = Product.query.get(item_data['product_id'])
        product.stock -= item_data['quantity']
        
        # Catat mutasi stok (OUT)
        mutation = StockMutation(
            product_id=product.id,
            mutation_type='OUT',
            quantity=item_data['quantity'],
            reference_id=new_order.id,
            notes=f'Penjualan POS: {order_number}',
            created_by=current_user.id
        )
        db.session.add(mutation)
        
    db.session.commit()
    
    # 4. Log aktivitas
    log_activity('POS_TRANSACTION', f'Transaksi POS berhasil: {order_number} (Total: Rp {total_amount:,.0f})')
    
    return jsonify({
        'success': True, 
        'message': 'Transaksi berhasil!',
        'order_number': order_number,
        'total_amount': total_amount
    })
# ==========================================
# RIWAYAT TRANSAKSI
# ==========================================
@kasir_bp.route('/transactions')
@kasir_required
def transactions():
    page = request.args.get('page', 1, type=int)
    date_filter = request.args.get('date', '', type=str)
    search = request.args.get('search', '', type=str)

    # TAMBAHKAN joinedload untuk User agar nama kasir dimuat sekaligus
    query = Order.query.options(joinedload(Order.user)).filter_by(order_type='POS')

    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(db.func.date(Order.created_at) == filter_date)
        except ValueError:
            pass

    if search:
        query = query.filter(Order.order_number.ilike(f'%{search}%'))

    orders = query.order_by(Order.created_at.desc()).paginate(page=page, per_page=15)

    return render_template('transactions.html', orders=orders, 
                           current_date=date_filter, current_search=search)
# API: Detail Transaksi (untuk modal)
@kasir_bp.route('/api/transactions/<int:order_id>')
@kasir_required
def api_transaction_detail(order_id):
    order = Order.query.get_or_404(order_id)
    
    # Pastikan ini adalah transaksi POS dan milik kasir ini (atau super kasir)
    if order.order_type != 'POS':
        return jsonify({'success': False, 'message': 'Transaksi tidak ditemukan'}), 404
        
    items = [{
        'name': item.product.name,
        'sku': item.product.sku,
        'quantity': item.quantity,
        'price': float(item.price_at_purchase),
        'subtotal': float(item.subtotal)
    } for item in order.items]
    
    return jsonify({
        'success': True,
        'order_number': order.order_number,
        'date': order.created_at.strftime('%d-%m-%Y %H:%M:%S'),
        'cashier': order.user.full_name if order.user else 'Unknown',
        'payment_method': order.payment_method,
        'total_amount': float(order.total_amount),
        'items': items
    })