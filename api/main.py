from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.analytics import router as analytics_router

app = FastAPI(title="Parkee POS Analytics API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analytics_router)


@app.get("/health")
def health():
    return {"status": "ok"}
