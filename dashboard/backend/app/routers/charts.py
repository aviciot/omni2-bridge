from fastapi import APIRouter

router = APIRouter(prefix="/charts", tags=["charts"])

# All chart endpoints removed - they were calling non-existent OMNI2 endpoints
# Original endpoints:
# - /queries (called non-existent /api/v1/charts/queries on OMNI2)
# - /cost (called non-existent /api/v1/charts/cost on OMNI2) 
# - /response-times (called non-existent /api/v1/charts/response-times on OMNI2)
# - /errors (called non-existent /api/v1/charts/errors on OMNI2)
