# run.py
"""
Run script for ESSL Attendance System.
Place this file in the project ROOT directory.

Fix: reload=True has been removed.
With reload=True, uvicorn spawns a watcher process AND a worker process.
APScheduler starts in BOTH, causing background sync and LOP jobs to run
twice simultaneously, producing duplicate records and concurrent ZK connections.
"""
import sys
import os
import multiprocessing
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

print(f"📁 Project Root: {PROJECT_ROOT}")
print(f"🐍 Python Path:  {sys.path[0]}\n")

if __name__ == "__main__":
    multiprocessing.freeze_support()

    try:
        from app.config import get_settings
        settings = get_settings()

        import uvicorn

        print("=" * 80)
        print("🚀 Starting ESSL Fingerprint Attendance System")
        print("=" * 80)
        print(f"📡 Server:          http://{settings.APP_HOST}:{settings.APP_PORT}")
        print(f"📝 API Docs:        http://localhost:{settings.APP_PORT}/docs")
        print(f"🔌 Device Webhook:  http://YOUR_LOCAL_IP:{settings.APP_PORT}/iclock/cdata")
        print(f"⏰ DAY_START_TIME:  {settings.DAY_START_TIME}  (logical day boundary)")
        print("=" * 80 + "\n")

        uvicorn.run(
            "app.main:app",
            host=settings.APP_HOST,
            port=settings.APP_PORT,
            reload=False,       # MUST be False — reload causes double background jobs
            log_level="info",
        )

    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("\n🔍 Troubleshooting:")
        print(f"   1. Make sure you are in the project root: {PROJECT_ROOT}")
        print("   2. Activate your virtual environment")
        print("   3. Run: pip install -r requirements.txt")
        sys.exit(1)