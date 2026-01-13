
import sys
from pathlib import Path

# Add backend/app to path
backend_path = Path("d:/PycharmProjects/qualityfoundry/backend/app")
sys.path.insert(0, str(backend_path))

from qualityfoundry.database.config import Base, engine, SessionLocal  # noqa: E402
from qualityfoundry.database import models  # noqa: E402, F401
from qualityfoundry.database import user_models  # noqa: E402, F401
from qualityfoundry.database import ai_config_models  # noqa: E402, F401
from qualityfoundry.database import system_config_models  # noqa: E402, F401

def diagnostic():
    print("--- Diagnostic Start ---")
    print(f"DATABASE_URL: {engine.url}")
    
    print("\nAttempting to create tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully (or already exist).")
    except Exception as e:
        print(f"Error creating tables: {e}")
        return

    db = SessionLocal()
    try:
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"\nTables in database: {tables}")
        
        expected_tables = ["requirements", "scenarios", "testcases", "environments", "executions", "users", "ai_configs"]
        for table in expected_tables:
            if table in tables:
                print(f"  [OK] Table '{table}' found.")
            else:
                print(f"  [MISSING] Table '{table}' NOT found.")
                
    except Exception as e:
        print(f"Error inspecting database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    diagnostic()
