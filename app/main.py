from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from app.config import get_settings
from app.core.database import init_db
from app.core.response import error_response
from app.background.tasks import sync_manager

# Import routers
from app.api.routes import users, attendance, device, iclock, payroll

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
    print(f"📝 API Docs: http://{settings.APP_HOST}:{settings.APP_PORT}/docs")
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
    description="REST API for managing ESSL F22 fingerprint attendance device",
    version="1.0.0",
    lifespan=lifespan
)


# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
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


# Include routers
app.include_router(users.router, prefix="/api/v1")
app.include_router(attendance.router, prefix="/api/v1")
app.include_router(device.router, prefix="/api/v1")
app.include_router(payroll.router, prefix="/api/v1")
app.include_router(iclock.router)  # No prefix for iClock protocol


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint - API health check"""
    return {
        "status": "success",
        "message": "ESSL Fingerprint Attendance System API",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "users": "/api/v1/users",
            "attendance": "/api/v1/attendance",
            "payroll": "/api/v1/payroll",
            "device": "/api/v1/device",
            "iclock_webhook": "/iclock/cdata"
        }
    }


@app.get("/health")
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
                "background_sync": "running"
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
        reload=True,  # Enable auto-reload in development
        log_level="info"
    )