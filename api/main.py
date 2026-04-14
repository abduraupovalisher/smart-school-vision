from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes.isapi import router as isapi_router

# Initialize FastAPI application
app = FastAPI(title="Smart School Vision API")

# Configure CORS to allow the desktop app or web dashboard to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register ISAPI webhook routes
app.include_router(isapi_router, prefix="/api")


@app.get("/health")
def health_check():
    """Simple health check endpoint"""
    return {"status": "ok"}
