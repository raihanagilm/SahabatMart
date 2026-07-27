from flask import render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from functools import wraps
from sqlalchemy import or_
from werkzeug.security import generate_password_hash

from . import gudang_bp
from app.models import User, Product, Category, StockMutation
from app.extensions import db

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
        # Cek duplikasi SKU
        if Product.query.filter_by(sku=request.form['sku']).first():
            flash('SKU sudah terdaftar!', 'danger')
            return redirect(url_for('gudang.add_product'))

        new_product = Product(
            sku=request.form['sku'],
            name=request.form['name'],
            price=float(request.form['price']),
            stock=int(request.form.get('stock', 0)),
            category_id=request.form.get('category_id') or None
        )
        db.session.add(new_product)
        db.session.commit()
        flash('Produk berhasil ditambahkan!', 'success')
        return redirect(url_for('gudang.products'))
        
    categories = Category.query.all()
    return render_template('product_form.html', categories=categories, product=None)

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

@gudang_bp.route('/products/<int:product_id>/delete', methods=['POST'])
@gudang_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    if product.mutations:
        flash('Produk tidak bisa dihapus karena sudah memiliki riwayat transaksi/mutasi. Silakan nonaktifkan saja.', 'danger')
        return redirect(url_for('gudang.products'))
        
    db.session.delete(product)
    db.session.commit()
    flash('Produk berhasil dihapus!', 'success')
    return redirect(url_for('gudang.products'))

# ==========================================
# MUTASI STOK
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
    
    flash(f'Mutasi stok ({mutation_type}) sebanyak {quantity} berhasil dicatat!', 'success')
    return redirect(url_for('gudang.product_mutations', product_id=product_id))

# ==========================================
# MANAJEMEN KARYAWAN (Khusus Super Admin)
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
        flash('Karyawan berhasil ditambahkan!', 'success')
        return redirect(url_for('gudang.employees'))
        
    return render_template('employee_form.html')