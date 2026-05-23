from fastapi import APIRouter, Depends, HTTPException

from analyzer.schemas.responses import PlayerResponse
from analyzer.api.dependencies import get_ingestion_service

router = APIRouter(prefix="/players", tags=["players"])


@router.get('/{game_name}/{tag_line}', response_model=PlayerResponse)
async def get_player_by_riot_id(
        game_name: str,
        tag_line: str,
        service = Depends(get_ingestion_service)
):
    player = await service.get_player_by_riot_id(game_name, tag_line)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    return player
