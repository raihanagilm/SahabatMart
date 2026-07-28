from flask import render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from functools import wraps
from app.utils.image_handler import compress_image_to_blob
from sqlalchemy import or_
from werkzeug.security import generate_password_hash

from . import gudang_bp
from app.models import User, Product, Category, StockMutation, ActivityLog
from app.extensions import db

# Helper function untuk mencatat aktivitas
def log_activity(action, description=None):
    log = ActivityLog(
        user_id=current_user.id if current_user.is_authenticated else None,
        action=action,
        description=description,
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
# Decorator untuk membatasi akses hanya untuk role Gudang
def gudang_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role not in ['SUPER_GUDANG', 'KARYAWAN_GUDANG', 'GUDANG']:
            flash('Akses ditolak. Halaman ini khusus untuk staf Gudang.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# ==========================================
# DASHBOARD
# ==========================================
@gudang_bp.route('/dashboard')
@gudang_required
def dashboard():
    total_products = Product.query.count()
    low_stock_products = Product.query.filter(Product.stock < 10).count()
    total_categories = Category.query.count()
    recent_mutations = StockMutation.query.order_by(StockMutation.created_at.desc()).limit(5).all()
    
    return render_template('dashboard.html', 
                           total_products=total_products, 
                           low_stock=low_stock_products,
                           total_categories=total_categories,
                           recent_mutations=recent_mutations)
# ==========================================
# CRUD PRODUK (Dengan Search & Filter)
# ==========================================

# Fungsi untuk generate SKU otomatis
def generate_sku(category_id):
    if not category_id:
        # Jika tidak ada kategori, gunakan prefix 'GEN' (General)
        prefix = 'GEN'
    else:
        category = Category.query.get(category_id)
        # Ambil 3 huruf pertama dari nama kategori, uppercase
        prefix = category.name[:3].upper() if category else 'GEN'
    
    # Cari produk terakhir dengan prefix yang sama
    # Contoh: cari semua produk dengan SKU dimulai dengan 'MNM-'
    last_product = Product.query.filter(Product.sku.like(f'{prefix}-%')).order_by(Product.sku.desc()).first()
    
    if last_product:
        # Extract nomor urut dari SKU terakhir
        # Contoh: 'MNM-015' -> extract '015' -> convert ke int 15 -> tambah 1 -> 16
        last_sku = last_product.sku
        last_number = int(last_sku.split('-')[1])
        new_number = last_number + 1
    else:
        # Jika belum ada produk dengan prefix ini, mulai dari 1
        new_number = 1
    
    # Format nomor urut menjadi 3 digit (001, 002, 015, 123)
    return f"{prefix}-{new_number:03d}"

@gudang_bp.route('/products')
@gudang_required
def products():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    category_id = request.args.get('category_id', '', type=str)
    
    query = Product.query
    
    if search:
        query = query.filter(or_(Product.name.ilike(f'%{search}%'), Product.sku.ilike(f'%{search}%')))
        
    if category_id:
        query = query.filter_by(category_id=int(category_id))
        
    products = query.order_by(Product.name.asc()).paginate(page=page, per_page=10)
    categories = Category.query.all()
    
    return render_template('products.html', products=products, categories=categories, 
                           current_search=search, current_category=category_id)

@gudang_bp.route('/products/add', methods=['GET', 'POST'])
@gudang_required
def add_product():
    if request.method == 'POST':
        category_id = request.form.get('category_id') or None
        product_name = request.form['name'].strip()
        price = float(request.form['price'])
        
        # Validasi harga
        if price <= 0:
            flash('Harga produk harus lebih dari 0!', 'danger')
            categories = Category.query.all()
            return render_template('gudang/product_form.html', categories=categories, product=None)
        
        # Validasi nama duplikat
        existing_product = Product.query.filter(
            db.func.lower(Product.name) == db.func.lower(product_name)
        ).first()
        
        if existing_product:
            flash(f'Nama produk "{product_name}" sudah ada!', 'danger')
            categories = Category.query.all()
            return render_template('gudang/product_form.html', categories=categories, product=None)
        
        sku = generate_sku(category_id)
        
        if Product.query.filter_by(sku=sku).first():
            flash('Error: SKU yang di-generate sudah ada.', 'danger')
            return redirect(url_for('gudang.add_product'))

        # [BARU] Handle upload gambar sebagai BLOB
        image_blob = None
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file and image_file.filename != '':
                image_blob = compress_image_to_blob(image_file)

        new_product = Product(
            sku=sku,
            name=product_name,
            price=price,
            stock=int(request.form.get('stock', 0)),
            category_id=category_id,
            image_blob=image_blob  # [BARU] Simpan bytes ke database
        )
        db.session.add(new_product)
        db.session.commit()
        
        log_activity('ADD_PRODUCT', f'Menambahkan produk baru: {product_name} (SKU: {sku})')
        
        flash(f'Produk berhasil ditambahkan dengan SKU: {sku}', 'success')
        return redirect(url_for('gudang.products'))
        
    categories = Category.query.all()
    return render_template('gudang/product_form.html', categories=categories, product=None)

@gudang_bp.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
@gudang_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        product_name = request.form['name'].strip()
        price = float(request.form['price'])
        
        # Validasi harga
        if price <= 0:
            flash('Harga produk harus lebih dari 0!', 'danger')
            categories = Category.query.all()
            return render_template('gudang/product_form.html', categories=categories, product=product)
        
        # Validasi nama duplikat
        existing_product = Product.query.filter(
            Product.id != product_id,
            db.func.lower(Product.name) == db.func.lower(product_name)
        ).first()
        
        if existing_product:
            flash(f'Nama produk "{product_name}" sudah digunakan oleh produk lain!', 'danger')
            categories = Category.query.all()
            return render_template('gudang/product_form.html', categories=categories, product=product)
        
        product.name = product_name
        product.price = price
        product.category_id = request.form.get('category_id') or None
        
        # [BARU] Handle upload gambar baru sebagai BLOB
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file and image_file.filename != '':
                # Compress dan simpan sebagai bytes
                image_blob = compress_image_to_blob(image_file)
                if image_blob:
                    product.image_blob = image_blob
        
        db.session.commit()
        
        log_activity('EDIT_PRODUCT', f'Mengedit produk: {product_name} (SKU: {product.sku})')
        
        flash('Produk berhasil diupdate!', 'success')
        return redirect(url_for('gudang.products'))
        
    categories = Category.query.all()
    return render_template('gudang/product_form.html', categories=categories, product=product)

# [BARU] Route untuk serve gambar dari BLOB
@gudang_bp.route('/products/<int:product_id>/image')
@gudang_required
def product_image(product_id):
    from flask import Response
    
    product = Product.query.get_or_404(product_id)
    
    if not product.image_blob:
        # Return placeholder image jika tidak ada gambar
        return Response(status=404)
    
    return Response(
        product.image_blob,
        mimetype='image/jpeg',
        headers={'Cache-Control': 'max-age=86400'}  # Cache 1 hari
    )

@gudang_bp.route('/products/<int:product_id>/delete', methods=['POST'])
@gudang_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    if product.mutations:
        flash('Produk tidak bisa dihapus karena sudah memiliki riwayat transaksi/mutasi.', 'danger')
        return redirect(url_for('gudang.products'))
    
    product_name = product.name
    db.session.delete(product)
    db.session.commit()
    
    # [BARU] Log aktivitas
    log_activity('DELETE_PRODUCT', f'Menghapus produk: {product_name}')
    
    flash('Produk berhasil dihapus!', 'success')
    return redirect(url_for('gudang.products'))

# ==========================================
# MUTASI STOK (Dengan Logging)
# ==========================================
@gudang_bp.route('/products/<int:product_id>/mutations')
@gudang_required
def product_mutations(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product_mutations.html', product=product)

@gudang_bp.route('/products/<int:product_id>/mutations/add', methods=['POST'])
@gudang_required
def add_mutation(product_id):
    product = Product.query.get_or_404(product_id)
    
    mutation_type = request.form['mutation_type']
    quantity = int(request.form['quantity'])
    notes = request.form.get('notes', '')

    if quantity <= 0:
        flash('Jumlah mutasi harus lebih dari 0.', 'danger')
        return redirect(url_for('gudang.product_mutations', product_id=product_id))

    if mutation_type == 'IN':
        product.stock += quantity
    elif mutation_type == 'OUT':
        if product.stock < quantity:
            flash('Stok tidak mencukupi untuk pengeluaran.', 'danger')
            return redirect(url_for('gudang.product_mutations', product_id=product_id))
        product.stock -= quantity
    elif mutation_type == 'ADJUSTMENT':
        product.stock += quantity 

    new_mutation = StockMutation(
        product_id=product.id,
        mutation_type=mutation_type,
        quantity=quantity,
        notes=notes,
        created_by=current_user.id
    )
    
    db.session.add(new_mutation)
    db.session.commit()
    
    # [BARU] Log aktivitas
    log_activity('MUTATION_STOCK', f'Mutasi stok {mutation_type} sebanyak {quantity} untuk produk: {product.name}')
    
    flash(f'Mutasi stok ({mutation_type}) sebanyak {quantity} berhasil dicatat!', 'success')
    return redirect(url_for('gudang.product_mutations', product_id=product_id))

# ==========================================
# MANAJEMEN KARYAWAN (Dengan Nonaktifkan & Logging)
# ==========================================
@gudang_bp.route('/employees')
@gudang_required
def employees():
    if current_user.role != 'SUPER_GUDANG':
        flash('Hanya Super Admin yang bisa melihat daftar karyawan.', 'warning')
        return redirect(url_for('gudang.dashboard'))
        
    staff = User.query.filter(User.role.in_(['SUPER_GUDANG', 'KARYAWAN_GUDANG'])).all()
    return render_template('employees.html', staff=staff)

@gudang_bp.route('/employees/add', methods=['GET', 'POST'])
@gudang_required
def add_employee():
    if current_user.role != 'SUPER_GUDANG':
        flash('Akses ditolak.', 'danger')
        return redirect(url_for('gudang.dashboard'))

    if request.method == 'POST':
        if User.query.filter_by(email=request.form['email']).first():
            flash('Email sudah terdaftar!', 'danger')
            return redirect(url_for('gudang.add_employee'))

        new_staff = User(
            email=request.form['email'],
            password_hash=generate_password_hash(request.form['password']),
            full_name=request.form['full_name'],
            role='KARYAWAN_GUDANG'
        )
        db.session.add(new_staff)
        db.session.commit()
        
        # [BARU] Log aktivitas
        log_activity('ADD_EMPLOYEE', f'Menambahkan karyawan baru: {new_staff.full_name} ({new_staff.email})')
        
        flash('Karyawan berhasil ditambahkan!', 'success')
        return redirect(url_for('gudang.employees'))
        
    return render_template('employee_form.html')

# [BARU] Route untuk toggle status aktif/nonaktif pegawai
@gudang_bp.route('/employees/<int:employee_id>/toggle-status', methods=['POST'])
@gudang_required
def toggle_employee_status(employee_id):
    if current_user.role != 'SUPER_GUDANG':
        flash('Akses ditolak.', 'danger')
        return redirect(url_for('gudang.dashboard'))
    
    employee = User.query.get_or_404(employee_id)
    
    # Jangan izinkan nonaktifkan diri sendiri
    if employee.id == current_user.id:
        flash('Anda tidak bisa menonaktifkan akun Anda sendiri!', 'danger')
        return redirect(url_for('gudang.employees'))
    
    employee.is_active = not employee.is_active
    db.session.commit()
    
    status_text = 'diaktifkan' if employee.is_active else 'dinonaktifkan'
    
    # Log aktivitas
    log_activity('TOGGLE_EMPLOYEE_STATUS', f'{status_text.capitalize()} karyawan: {employee.full_name}')
    
    flash(f'Karyawan {employee.full_name} berhasil {status_text}!', 'success')
    return redirect(url_for('gudang.employees'))

# [BARU] Route untuk melihat log aktivitas (khusus Super Admin)
@gudang_bp.route('/activity-logs')
@gudang_required
def activity_logs():
    if current_user.role != 'SUPER_GUDANG':
        flash('Hanya Super Admin yang bisa melihat log aktivitas.', 'warning')
        return redirect(url_for('gudang.dashboard'))
    
    page = request.args.get('page', 1, type=int)
    logs = ActivityLog.query.order_by(ActivityLog.created_at.desc()).paginate(page=page, per_page=20)
    
    return render_template('activity_logs.html', logs=logs)
