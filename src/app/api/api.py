from fastapi import APIRouter
from api.v1 import router as v1_router  # Import the v1 router

# Create a global router
router = APIRouter()

# Include versioned API (all routes inside v1)
router.include_router(v1_router, prefix="/api")