
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.database import engine
from app.models import coupon as coupon_model
from app.routers import coupons as coupons_router

# Create database tables
coupon_model.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Coupons Management API",
    description="RESTful API to manage and apply different types of discount coupons for an e-commerce platform",
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS - keep permissive for demo; restrict in prod
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(coupons_router.router)


@app.get("/health")
def health():
    return {"status": "healthy"}


# Proper JSON error with correct status code
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"status_code": exc.status_code, "detail": exc.detail}},
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
