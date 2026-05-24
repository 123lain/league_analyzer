from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ResponseBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RankedEntry(BaseModel):
    queue_type: str = Field(..., description='Ranked queue type', alias='queueType')
    tier: str
    rank: str
    league_points: int = Field(..., description='Player LP', alias='leaguePoints')
    wins: int
    losses: int


class PlayerResponse(ResponseBaseModel):
    puuid: str = Field(..., description='Unique player ID from Riot API')
    game_name: str
    tag_line: str
    ranked_data: list[RankedEntry] | None


class MatchHistoryResponse(ResponseBaseModel):
    match_id: str = Field(..., description='Unique match id from Riot API')
    match_created: datetime
    match_duration_seconds: int
    champion_name: str = Field(..., description='Player\'s champion name in match')
    kills: int
    deaths: int
    assists: int
    creep_score: int
    win: bool = Field(..., description='Game result for player')
    team_position: str = Field(..., description='Player role in match')


class ChampionStatsResponse(BaseModel):
    champion_name: str
    games_played: int = Field(..., description='Player\'s total game player on champion')
    win_rate: float = Field(..., description='Player\'s winrate (%) on champion')
    kda: float = Field(..., description='Player\'s KDA on champion')
    avg_kills: float = Field(..., description='Player\'s average kills on champion')
    avg_deaths: float = Field(..., description='Player\'s average deaths on champion')
    avg_assists: float = Field(..., description='Player\'s average assists on champion')