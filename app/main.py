# app/main.py
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from app.config import get_settings
from app.core.database import init_db
from app.core.response import error_response
from app.background.tasks import sync_manager

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# Import routers
from app.api.routes import users, attendance, device, iclock, payroll, auth, lop

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Handles startup and shutdown events
    """
    # Startup
    print("\n" + "="*80)
    print("🚀 ESSL Fingerprint Attendance System Starting...")
    print("="*80)
    
    # Initialize database
    print("📊 Initializing database...")
    init_db()
    print("✅ Database initialized")
    
    # Start background sync
    print("🔄 Starting background synchronization...")
    sync_manager.start()
    
    print("\n✅ Application started successfully!")
    print(f"📡 API Server: http://{settings.APP_HOST}:{settings.APP_PORT}")
    print(f"📚 API Docs: http://{settings.APP_HOST}:{settings.APP_PORT}/docs")
    
    # Get local IP for network access instructions
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        print(f"🌐 Network Access: http://{local_ip}:{settings.APP_PORT}")
        print(f"🔌 Device Webhook: http://{local_ip}:{settings.APP_PORT}/iclock/cdata")
    except:
        print(f"🔌 Device Webhook: http://YOUR_LOCAL_IP:{settings.APP_PORT}/iclock/cdata")
    
    print("="*80 + "\n")
    
    yield
    
    # Shutdown
    print("\n" + "="*80)
    print("🛑 Shutting down application...")
    sync_manager.stop()
    print("✅ Application shutdown complete")
    print("="*80 + "\n")


# Create FastAPI app
app = FastAPI(
    title="ESSL Fingerprint Attendance System",
    description="REST API for managing ESSL F22 fingerprint attendance device with LOP tracking",
    version="1.0.0",
    lifespan=lifespan
)


# CORS configuration - Allow all origins for local network
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for local network
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all uncaught exceptions"""
    print(f"❌ Unhandled exception: {exc}")
    
    return JSONResponse(
        status_code=500,
        content=error_response(
            message="Internal server error",
            error_details={
                "type": type(exc).__name__,
                "details": str(exc)
            }
        )
    )


# Serve static files (React build)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
    
    @app.get("/")
    async def serve_frontend():
        """Serve the React frontend"""
        return FileResponse("static/index.html")
    
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Handle SPA routing - serve index.html for all non-API routes"""
        # Don't interfere with API routes
        if full_path.startswith("api/") or full_path.startswith("iclock/"):
            raise HTTPException(status_code=404)
        
        # Check if file exists in static directory
        file_path = f"static/{full_path}"
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        
        # Otherwise serve index.html for SPA routing
        return FileResponse("static/index.html")
else:
    # If static directory doesn't exist, show API info
    @app.get("/")
    async def root():
        """Root endpoint - API health check"""
        return {
            "status": "success",
            "message": "ESSL Fingerprint Attendance System API",
            "version": "1.0.0",
            "note": "Frontend not built. Run 'python deploy.py' to build frontend.",
            "endpoints": {
                "docs": "/docs",
                "users": "/api/v1/users",
                "attendance": "/api/v1/attendance",
                "payroll": "/api/v1/payroll",
                "device": "/api/v1/device",
                "lop": "/api/v1/lop",
                "iclock_webhook": "/iclock/cdata"
            }
        }

# Include routers
app.include_router(users.router, prefix="/api/v1")
app.include_router(attendance.router, prefix="/api/v1")
app.include_router(device.router, prefix="/api/v1")
app.include_router(payroll.router, prefix="/api/v1")
app.include_router(lop.router, prefix="/api/v1")  # NEW: LOP routes
app.include_router(iclock.router)  # No prefix for iClock protocol
app.include_router(auth.router, prefix="/api/v1")


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    from app.core.database import engine
    
    try:
        # Test database connection
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        
        return {
            "status": "success",
            "message": "System is healthy",
            "data": {
                "database": "connected",
                "background_sync": "running",
                "lop_check": "scheduled at 7 AM daily"
            },
            "error": None
        }
    except Exception as e:
        return {
            "status": "error",
            "message": "System health check failed",
            "data": None,
            "error": {"database": str(e)}
        }


# Run application
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=False,  # Disable reload in production
        log_level="info"
    )