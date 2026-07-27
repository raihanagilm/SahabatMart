from flask import render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from functools import wraps
from . import gudang_bp
from app.models import User, Product, Category # Pastikan Product & Category ada di models.py
from app.extensions import db

# Decorator custom untuk membatasi akses hanya untuk role Gudang
def gudang_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role not in ['SUPER_GUDANG', 'KARYAWAN_GUDANG']:
            flash('Akses ditolak. Halaman ini khusus untuk staf Gudang.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# --- DASHBOARD ---
@gudang_bp.route('/dashboard')
@gudang_required
def dashboard():
    total_products = Product.query.count()
    low_stock_products = Product.query.filter(Product.stock < 10).count() # Threshold stok menipis
    total_categories = Category.query.count()
    
    return render_template('dashboard.html', 
                           total_products=total_products, 
                           low_stock=low_stock_products,
                           total_categories=total_categories)

# --- CRUD PRODUK ---
@gudang_bp.route('/products')
@gudang_required
def products():
    page = request.args.get('page', 1, type=int)
    products = Product.query.paginate(page=page, per_page=10)
    return render_template('products.html', products=products)

@gudang_bp.route('/products/add', methods=['GET', 'POST'])
@gudang_required
def add_product():
    if request.method == 'POST':
        # Logic untuk menambah produk (singkat untuk contoh)
        new_product = Product(
            sku=request.form['sku'],
            name=request.form['name'],
            price=float(request.form['price']),
            stock=int(request.form['stock']),
            category_id=request.form.get('category_id') or None
        )
        db.session.add(new_product)
        db.session.commit()
        flash('Produk berhasil ditambahkan!', 'success')
        return redirect(url_for('gudang.products'))
        
    categories = Category.query.all()
    return render_template('product_form.html', categories=categories, product=None)

# --- MANAJEMEN KARYAWAN (Khusus Super Admin) ---
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
        flash('Hanya Super Admin yang bisa menambahkan karyawan.', 'danger')
        return redirect(url_for('gudang.dashboard'))

    if request.method == 'POST':
        from werkzeug.security import generate_password_hash
        new_staff = User(
            email=request.form['email'],
            password_hash=generate_password_hash(request.form['password']),
            full_name=request.form['full_name'],
            role='KARYAWAN_GUDANG'
        )
        db.session.add(new_staff)
        db.session.commit()
        flash('Karyawan berhasil ditambahkan!', 'success')
        return redirect(url_for('gudang.employees'))
        
    return render_template('employee_form.html')

# --- EDIT PRODUK ---
@gudang_bp.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
@gudang_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        product.sku = request.form['sku']
        product.name = request.form['name']
        product.price = float(request.form['price'])
        product.category_id = request.form.get('category_id') or None
        
        db.session.commit()
        flash('Produk berhasil diupdate!', 'success')
        return redirect(url_for('gudang.products'))
        
    categories = Category.query.all()
    return render_template('product_form.html', categories=categories, product=product)

# --- DELETE PRODUK ---
@gudang_bp.route('/products/<int:product_id>/delete', methods=['POST'])
@gudang_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    # Cek apakah produk sudah pernah memiliki riwayat mutasi (terjual/dipakai)
    if product.mutations:
        flash('Produk tidak bisa dihapus karena sudah memiliki riwayat transaksi/mutasi. Silakan nonaktifkan saja.', 'danger')
        return redirect(url_for('gudang.products'))
        
    db.session.delete(product)
    db.session.commit()
    flash('Produk berhasil dihapus!', 'success')
    return redirect(url_for('gudang.products'))

# --- RIWAYAT MUTASI STOK ---
@gudang_bp.route('/products/<int:product_id>/mutations')
@gudang_required
def product_mutations(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product_mutations.html', product=product)

# --- TAMBAH MUTASI STOK MANUAL (IN/OUT/ADJUSTMENT) ---
@gudang_bp.route('/products/<int:product_id>/mutations/add', methods=['POST'])
@gudang_required
def add_mutation(product_id):
    product = Product.query.get_or_404(product_id)
    
    mutation_type = request.form['mutation_type'] # 'IN', 'OUT', 'ADJUSTMENT'
    quantity = int(request.form['quantity'])
    notes = request.form.get('notes', '')

    if quantity <= 0:
        flash('Jumlah mutasi harus lebih dari 0.', 'danger')
        return redirect(url_for('gudang.product_mutations', product_id=product_id))

    # Logika Update Stok di Tabel Products
    if mutation_type == 'IN':
        product.stock += quantity
    elif mutation_type == 'OUT':
        if product.stock < quantity:
            flash('Stok tidak mencukupi untuk pengeluaran.', 'danger')
            return redirect(url_for('gudang.product_mutations', product_id=product_id))
        product.stock -= quantity
    elif mutation_type == 'ADJUSTMENT':
        # Adjustment langsung mengubah stok ke angka yang diinput (bisa + atau -)
        # Atau bisa juga diartikan sebagai stok akhir yang diinginkan. 
        # Di sini kita asumsikan quantity adalah selisih (bisa minus)
        product.stock += quantity 

    # Catat ke Tabel Mutasi
    new_mutation = StockMutation(
        product_id=product.id,
        mutation_type=mutation_type,
        quantity=quantity,
        notes=notes,
        created_by=current_user.id
    )
    
    db.session.add(new_mutation)
    db.session.commit()
    
    flash(f'Mutasi stok ({mutation_type}) sebanyak {quantity} berhasil dicatat!', 'success')
    return redirect(url_for('gudang.product_mutations', product_id=product_id))