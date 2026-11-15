from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

from app.modules.chat.routes import router as chat_router
from app.modules.decision_lab.routes import router as decision_lab_router
from app.modules.stocks.routes import router as stocks_router

from app.modules.stocksfeed.routes import router as stocksfeed_router
from app.modules.riskripple.event_routes import router as event_router
from app.modules.riskripple.routes import router as riskripple_router

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

app = FastAPI(title="Stock Market API")
app.include_router(chat_router)
app.include_router(stocks_router)
app.include_router(stocksfeed_router)
app.include_router(riskripple_router)
app.include_router(event_router)
app.include_router(decision_lab_router)
