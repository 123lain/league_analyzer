from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ResponseBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PlayerResponse(BaseModel):
    puuid: str
    game_name: str
    tag_line: str


class PlayerMatchResponse(BaseModel):
    match_id: str
    champion_name: str
    kills: int
    deaths: int
    assists: int
    win: bool


class MatchResponse(BaseModel):
    match_id: str
    match_creation: datetime
    match_duration: int
    queue_id: int
    patch: str
