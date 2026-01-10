
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qualityfoundry.database.config import SessionLocal
from qualityfoundry.database.models import Requirement
from qualityfoundry.services.file_upload import file_upload_service

import uuid

def test_file_extraction():
    db = SessionLocal()
    try:
        req_id = uuid.UUID("e43f57bb-c0ef-4b3a-aa05-acd121cfba47")
        req = db.query(Requirement).filter(Requirement.id == req_id).first()
        
        if not req:
            print("Requirement not found")
            return
            
        print(f"Requirement: {req.title}")
        print(f"Current Content Preview: {req.content[:100]}")
        print(f"File Path: {req.file_path}")
        
        if req.file_path and os.path.exists(req.file_path):
            print("File exists, attempting extraction...")
            content = file_upload_service.extract_text(req.file_path)
            print("Extraction Result:")
            print(content[:500])  # Print first 500 chars
            
            if "需要安装 python-docx 库" not in content and len(content) > 50:
                 print("SUCCESS: Extraction working correctly!")
            else:
                 print("FAILURE: Still getting placeholder or empty content.")
        else:
            print("File does not exist on disk!")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_file_extraction()
