
import sys
from pathlib import Path

# Add backend/app to path
backend_path = Path(__file__).resolve().parents[2] / "backend" / "app"
sys.path.insert(0, str(backend_path))

from qualityfoundry.database.config import Base, engine  # noqa: E402
from qualityfoundry.database import (  # noqa: E402
    models,  # noqa: F401
    user_models,  # noqa: F401
    ai_config_models,  # noqa: F401
    system_config_models  # noqa: F401
)

def init_db():
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")

if __name__ == "__main__":
    init_db()
