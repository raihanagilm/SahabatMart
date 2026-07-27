# app/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-secret-key')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # [FIX] Memaksa koneksi menggunakan SSL untuk TiDB Cloud Serverless
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {
            'ssl': {
                # Mencari file cacert.pem di root folder (D:\Projek\SahabatMart\)
                'ca': os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'cacert.pem')
            }
        }
    }