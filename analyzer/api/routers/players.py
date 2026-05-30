from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status

from analyzer.schemas.responses import PlayerResponse, ChampionStatsResponse, MatchHistoryResponse
from analyzer.api.dependencies import get_ingestion_service


router = APIRouter(prefix='/players', tags=['players'])


@router.get(
    '/{puuid}/matches',
    response_model=list[MatchHistoryResponse]
)
async def get_player_matches(
        puuid: str,
        limit: int = 10,
        service=Depends(get_ingestion_service)
):
    matches = await service.get_player_match_history(puuid, limit)
    if not matches:
        raise HTTPException(
            status_code=404,
            detail=f'No matches found for player {puuid}. Trigger sync.'
        )

    return matches


@router.get(
    '/{puuid}/champion-stats',
    response_model=list[ChampionStatsResponse]
)
async def get_player_champion_stats(
        puuid: str,
        limit: int = 5,
        service=Depends(get_ingestion_service)
):
    stats = await service.get_player_champion_stats(puuid, limit)
    return stats


@router.get(
    '/{game_name}/{tag_line}',
    response_model=PlayerResponse
)
async def get_player_by_riot_id(
        game_name: str,
        tag_line: str,
        background_tasks: BackgroundTasks,
        service = Depends(get_ingestion_service)
):
    player = await service.get_player_by_riot_id(game_name, tag_line, background_tasks)
    if not player:
        raise HTTPException(status_code=404, detail=f'Player {game_name}#{tag_line} not found')

    return player


@router.post(
    '/{game_name}/{tag_line}/sync',
    status_code=status.HTTP_202_ACCEPTED
)
async def sync_player_data(
        game_name: str,
        tag_line: str,
        background_tasks: BackgroundTasks,
        service = Depends(get_ingestion_service)
):
    background_tasks.add_task(
        service.sync_player_and_matches,
        game_name=game_name,
        tag_line=tag_line
    )

    return {
        'status': 'OK',
        'detail': f'Added update task for player {game_name}#{tag_line}'
    }
