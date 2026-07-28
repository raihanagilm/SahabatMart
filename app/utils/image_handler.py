import io
from PIL import Image

# Konfigurasi kompresi
MAX_SIZE = (800, 800)  # Resize ke max 800x800 pixels
QUALITY = 85  # Quality kompresi JPEG (1-100)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def compress_image_to_blob(file):
    """
    Compress gambar dan convert ke bytes (BLOB)
    Returns: bytes data untuk disimpan di database, atau None jika gagal
    """
    if not file or not allowed_file(file.filename):
        return None
    
    try:
        # Buka gambar dengan Pillow
        img = Image.open(file)
        
        # Convert RGBA ke RGB jika perlu (untuk JPEG)
        if img.mode in ('RGBA', 'P', 'LA'):
            img = img.convert('RGB')
        
        # Resize jika terlalu besar
        img.thumbnail(MAX_SIZE, Image.Resampling.LANCZOS)
        
        # Save ke bytes buffer dengan kompresi
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG', quality=QUALITY, optimize=True)
        img_byte_arr.seek(0)
        
        # Return bytes data
        return img_byte_arr.getvalue()
        
    except Exception as e:
        print(f"Error compressing image: {e}")
        return None