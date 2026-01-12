
import sys
from pathlib import Path

# Add backend/app to path
backend_path = Path(__file__).resolve().parents[2] / "backend" / "app"
sys.path.insert(0, str(backend_path))

from qualityfoundry.database.config import Base, engine
from qualityfoundry.database import (
    models,
    user_models,
    ai_config_models,
    system_config_models
)

def init_db():
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")

if __name__ == "__main__":
    init_db()
