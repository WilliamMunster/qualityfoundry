
import sys
import os

# Add parent directory to path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    print("Attempting to import AIService...")
    from qualityfoundry.services.ai_service import AIService
    print("Successfully imported AIService")
except Exception as e:
    import traceback
    print(f"Import failed: {e}")
    traceback.print_exc()
