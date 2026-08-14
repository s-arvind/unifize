from fastapi import FastAPI

from routers import discounts_router
from seed import seed

app = FastAPI(title="Discount Service API")
app.include_router(discounts_router)
seed()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
