import random
from datetime import datetime
from app import create_app
from app.extensions import db
from app.models import Product, Category

def seed_products(num_products=10000):
    app = create_app()
    
    with app.app_context():
        # 1. Ambil kategori yang sudah ada
        categories = Category.query.all()
        if not categories:
            print("❌ Error: Tidak ada kategori di database. Jalankan query kategori terlebih dahulu!")
            return

        print(f"🚀 Memulai seeding {num_products} produk...")
        
        # Data acak untuk variasi nama produk
        adjectives = ["Premium", "Organik", "Segar", "Import", "Lokal", "Hemat", "Super", "Ekstra", "Spesial"]
        nouns = ["Beras", "Minyak", "Sabun", "Susu", "Kopi", "Teh", "Gula", "Garam", "Mie", "Snack", "Biskuit", "Sampo", "Pasta Gigi", "Deterjen", "Pewangi", "Tisu", "Popok"]
        variants = ["Pouch", "Botol", "Kaleng", "Kardus", "Sachet", "Refill", "Family Pack", "Eceran"]

        batch = []
        batch_size = 1000 # Commit setiap 1000 baris agar hemat memori
        
        for i in range(1, num_products + 1):
            cat = random.choice(categories)
            prefix = cat.name[:3].upper()
            
            # Generate SKU unik berdasarkan index loop (jamin tidak duplikat)
            sku = f"{prefix}-{str(i).zfill(5)}"
            
            # Generate nama produk acak yang realistis
            name = f"{random.choice(adjectives)} {random.choice(nouns)} {random.choice(variants)} {random.choice([50, 100, 250, 500, 1000])}g/ml"
            
            # Harga acak antara Rp 2.000 - Rp 150.000
            price = round(random.uniform(2000, 150000), 2)
            
            # Stok acak antara 0 - 500
            stock = random.randint(0, 500)
            
            product = Product(
                category_id=cat.id,
                sku=sku,
                name=name,
                price=price,
                stock=stock,
                is_active=True,
                created_at=datetime.utcnow()
            )
            batch.append(product)
            
            # Simpan ke database setiap 1000 produk (Mencegah Memory Leak & Timeout)
            if len(batch) >= batch_size:
                db.session.bulk_save_objects(batch)
                db.session.commit()
                print(f"✅ Berhasil menyimpan {len(batch)} produk... (Total: {i})")
                batch = [] # Reset batch
        
        # Simpan sisa data jika ada
        if batch:
            db.session.bulk_save_objects(batch)
            db.session.commit()
            print(f"✅ Berhasil menyimpan {len(batch)} produk terakhir.")
            
        print(f"🎉 Seeding selesai! Total {num_products} produk berhasil ditambahkan.")

if __name__ == "__main__":
    # Ubah angka ini jika ingin lebih banyak/sedikit (misal: 5000 atau 20000)
    seed_products(10000)