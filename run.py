# run.py - Place this in E:\essl-attendance-system\
"""
Run script for ESSL Attendance System
Place this file in the project ROOT directory (E:\essl-attendance-system\)
"""
import sys
import os
from pathlib import Path

# Get the project root directory (where this file is located)
PROJECT_ROOT = Path(__file__).parent.absolute()

# Add project root to Python path
sys.path.insert(0, str(PROJECT_ROOT))

print(f"📁 Project Root: {PROJECT_ROOT}")
print(f"🐍 Python Path: {sys.path[0]}\n")


if __name__ == '__main__':
    # CRITICAL: This protects against Windows multiprocessing issues
    import multiprocessing
    multiprocessing.freeze_support()
    
    # Now we can import from app
    try:
        from app.config import get_settings
        settings = get_settings()
        
        import uvicorn
        
        print("="*80)
        print("🚀 Starting ESSL Fingerprint Attendance System")
        print("="*80)
        print(f"📡 Server: http://{settings.APP_HOST}:{settings.APP_PORT}")
        print(f"📝 API Docs: http://localhost:{settings.APP_PORT}/docs")
        print(f"🔌 Device Webhook: http://YOUR_LOCAL_IP:{settings.APP_PORT}/iclock/cdata")
        print("="*80 + "\n")
        
        uvicorn.run(
            "app.main:app",
            host=settings.APP_HOST,
            port=settings.APP_PORT,
            reload=True,
            log_level="info"
        )
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("\n🔍 Troubleshooting:")
        print(f"1. Make sure you're in the project root: {PROJECT_ROOT}")
        print("2. Check if 'app' directory exists")
        print("3. Verify all __init__.py files are present")
        print("4. Install dependencies: pip install -r requirements.txt")
        sys.exit(1)