from app.extensions import db
from flask_login import UserMixin
from werkzeug.security import check_password_hash
from datetime import datetime

# ==========================================
# MODEL USER
# ==========================================
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.BigInteger, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    google_id = db.Column(db.String(100), nullable=True)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(30), nullable=False)  # 'SUPER_GUDANG', 'KARYAWAN_GUDANG', 'SUPER_KASIR', 'KARYAWAN_KASIR', 'KUSTOMER'
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

# ==========================================
# MODEL CATEGORY
# ==========================================
class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.BigInteger, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    
    # Relasi
    products = db.relationship('Product', backref='category', lazy=True)

# ==========================================
# MODEL PRODUCT (Dengan image_blob)
# ==========================================
class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.BigInteger, primary_key=True)
    category_id = db.Column(db.BigInteger, db.ForeignKey('categories.id'))
    sku = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    price = db.Column(db.Numeric(15, 2), nullable=False)
    stock = db.Column(db.Integer, default=0)
    image_url = db.Column(db.String(255))  # Legacy field, bisa dikosongkan
    image_blob = db.Column(db.LargeBinary)  # Menyimpan gambar sebagai bytes (BLOB)
    is_active = db.Column(db.Boolean, default=True)
    updated_at = db.Column(db.TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    
    # Relasi
    mutations = db.relationship('StockMutation', backref='product', lazy=True, order_by='StockMutation.created_at.desc()')

# ==========================================
# MODEL STOCK MUTATION
# ==========================================
class StockMutation(db.Model):
    __tablename__ = 'stock_mutations'
    
    id = db.Column(db.BigInteger, primary_key=True)
    product_id = db.Column(db.BigInteger, db.ForeignKey('products.id'), nullable=False)
    mutation_type = db.Column(db.String(20), nullable=False)  # 'IN', 'OUT', 'ADJUSTMENT'
    quantity = db.Column(db.Integer, nullable=False)
    reference_id = db.Column(db.BigInteger)
    notes = db.Column(db.Text)
    created_by = db.Column(db.BigInteger, db.ForeignKey('users.id'))
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    
    # Relasi
    creator = db.relationship('User', backref='mutations_created')

# ==========================================
# MODEL ACTIVITY LOG
# ==========================================
class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    
    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'))
    action = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    
    # Relasi
    user = db.relationship('User', backref='activity_logs')

# ==========================================
# MODEL ORDER
# ==========================================
class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.BigInteger, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'))
    order_type = db.Column(db.String(20), nullable=False)  # 'POS', 'ONLINE'
    total_amount = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    payment_method = db.Column(db.String(30), nullable=False)
    payment_status = db.Column(db.String(20), default='PENDING')  # 'PENDING', 'SUCCESS', 'EXPIRE'
    midtrans_transaction_id = db.Column(db.String(100))
    midtrans_snap_token = db.Column(db.String(255))
    shipping_address = db.Column(db.Text)
    status = db.Column(db.String(20), default='PENDING')  # 'PENDING', 'COMPLETED', 'CANCELLED'
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)

    # Relasi
    user = db.relationship('User', backref='orders')
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Order {self.order_number}>'

# ==========================================
# MODEL ORDER ITEM
# ==========================================
class OrderItem(db.Model):
    __tablename__ = 'order_items'
    
    id = db.Column(db.BigInteger, primary_key=True)
    order_id = db.Column(db.BigInteger, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.BigInteger, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price_at_purchase = db.Column(db.Numeric(15, 2), nullable=False)
    
    # Subtotal dihitung otomatis oleh Database (TiDB/MySQL)
    subtotal = db.Column(db.Numeric(15, 2), db.Computed('quantity * price_at_purchase', persisted=True))

    # Relasi
    product = db.relationship('Product', backref='order_items')

    def __repr__(self):
        return f'<OrderItem {self.product.name if self.product else "Unknown"} x{self.quantity}>'