from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

from app.modules.stocks.routes import router as stocks_router

from app.modules.stocksfeed.routes import router as stocksfeed_router

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

app = FastAPI(title="Stock Market API")
app.include_router(stocks_router)
app.include_router(stocksfeed_router)
