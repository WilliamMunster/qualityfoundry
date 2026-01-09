import sys
import os

# 将 backend 目录添加到 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))

from backend.app.qualityfoundry.database.config import SessionLocal, engine
from backend.app.qualityfoundry.services.auth_service import AuthService

def seed():
    print(f"DEBUG: Engine URL: {engine.url}")
    db = SessionLocal()
    try:
        print("Creating default admin...")
        admin = AuthService.create_default_admin(db)
        if admin:
            print(f"Admin created/verified: {admin.username}")
        else:
            print("Failed to create admin")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
