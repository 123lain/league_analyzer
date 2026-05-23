from fastapi import Depends, Request

from analyzer.services.ingestion import IngestionService
from analyzer.database.session import get_db


def get_riot_client(request: Request):
    return request.app.state.riot_client


def get_ingestion_service(
        db=Depends(get_db),
        riot_client = Depends(get_riot_client)
):
    return IngestionService(db, riot_client)