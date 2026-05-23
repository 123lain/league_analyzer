from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RiotBaseModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class RankedEntry(RiotBaseModel):
    queue_type: str
    tier: str
    rank: str
    league_points: int
    wins: int
    losses: int


class RiotPlayer(RiotBaseModel):
    puuid: str
    gameName: str
    tagLine: str


class RiotPlayerMatch(RiotBaseModel):
    match_id: str
    champion_name: str
    kills: int
    deaths: int
    assists: int
    win: bool


class RiotMatch(RiotBaseModel):
    match_id: str
    match_creation: datetime
    match_duration: int
    queue_id: int
    patch: str
