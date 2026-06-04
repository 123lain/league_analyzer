from contextlib import asynccontextmanager

from fastapi import FastAPI

from analyzer.settings.logger import setup_logger
from analyzer.api.routers import players
from analyzer.core.riot_client import RiotAPIClient


logger = setup_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    riot_client = RiotAPIClient()
    await riot_client.start()

    app.state.riot_client = riot_client
    yield

    await riot_client.close()

app = FastAPI(title='League Analyzer', lifespan=lifespan)
app.include_router(players.router)

@app.get('/healthz')
async def health():
    return {'status': 'OK'}