
# =============================================================================
# setup.py - Setup script
# =============================================================================
"""
Setup and verification script
Run this first to check your environment
"""
import os
import sys

def check_environment():
    """Check if environment is properly configured"""
    print("\n" + "="*80)
    print("🔍 ESSL Attendance System - Environment Check")
    print("="*80 + "\n")
    
    issues = []
    
    # Check Python version
    print("1. Checking Python version...")
    if sys.version_info < (3, 8):
        issues.append("❌ Python 3.8+ required")
        print(f"   ❌ Current: {sys.version}")
    else:
        print(f"   ✅ Python {sys.version.split()[0]}")
    
    # Check .env file
    print("\n2. Checking .env file...")
    if not os.path.exists(".env"):
        issues.append("❌ .env file not found")
        print("   ❌ .env file not found")
        print("   Create .env file with required configuration")
    else:
        print("   ✅ .env file exists")
        
        # Check required variables
        required_vars = [
            "DB_HOST", "DB_NAME", "DB_USER", "DB_PASS", "DEVICE_IP"
        ]
        
        with open(".env", "r") as f:
            env_content = f.read()
        
        missing_vars = []
        for var in required_vars:
            if var not in env_content:
                missing_vars.append(var)
        
        if missing_vars:
            issues.append(f"❌ Missing variables in .env: {', '.join(missing_vars)}")
            print(f"   ⚠️  Missing variables: {', '.join(missing_vars)}")
        else:
            print("   ✅ All required variables present")
    
    # Check app directory structure
    print("\n3. Checking directory structure...")
    required_dirs = [
        "app",
        "app/core",
        "app/models",
        "app/services",
        "app/api",
        "app/api/routes",
        "app/background",
        "app/schemas"
    ]
    
    for directory in required_dirs:
        if not os.path.exists(directory):
            issues.append(f"❌ Missing directory: {directory}")
            print(f"   ❌ {directory}")
            os.makedirs(directory, exist_ok=True)
            print(f"      → Created {directory}")
        else:
            print(f"   ✅ {directory}")
    
    # Check __init__.py files
    print("\n4. Checking __init__.py files...")
    init_files = [
        "app/__init__.py",
        "app/core/__init__.py",
        "app/models/__init__.py",
        "app/services/__init__.py",
        "app/api/__init__.py",
        "app/api/routes/__init__.py",
        "app/background/__init__.py",
        "app/schemas/__init__.py"
    ]
    
    for init_file in init_files:
        if not os.path.exists(init_file):
            print(f"   ⚠️  Creating {init_file}")
            with open(init_file, "w") as f:
                f.write("")
        else:
            print(f"   ✅ {init_file}")
    
    # Check dependencies
    print("\n5. Checking dependencies...")
    try:
        import fastapi
        print("   ✅ fastapi")
    except ImportError:
        issues.append("❌ fastapi not installed")
        print("   ❌ fastapi not installed")
    
    try:
        import sqlalchemy
        print("   ✅ sqlalchemy")
    except ImportError:
        issues.append("❌ sqlalchemy not installed")
        print("   ❌ sqlalchemy not installed")
    
    try:
        import psycopg2
        print("   ✅ psycopg2")
    except ImportError:
        issues.append("❌ psycopg2 not installed")
        print("   ❌ psycopg2 not installed")
    
    try:
        from zk import ZK
        print("   ✅ pykzk")
    except ImportError:
        issues.append("❌ pykzk not installed")
        print("   ❌ pykzk not installed")
    
    # Summary
    print("\n" + "="*80)
    if issues:
        print("⚠️  Issues found:")
        for issue in issues:
            print(f"   {issue}")
        print("\n💡 Fix these issues before running the application")
        print("\nTo install dependencies:")
        print("   pip install -r requirements.txt")
    else:
        print("✅ All checks passed! You're ready to go!")
        print("\nTo start the application:")
        print("   python run.py")
    print("="*80 + "\n")

if __name__ == "__main__":
    check_environment()