from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from analyzer.database import Match, Player, PlayerMatch


class MatchRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_existing_match_ids(
            self,
            match_ids: list[str],
    ) -> set[str]:
        result = await self.db.scalars(
            select(Match.match_id).where(Match.match_id.in_(match_ids))
        )
        return set(result.all())

    async def add_new_match(
            self,
            match: Match
    ) -> None:
         self.db.add(match)

class PlayerRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_existing_puuids(
            self,
            puuids: set[str],
    ) -> set[str]:
        result = await self.db.scalars(
            select(Player.puuid).where(Player.puuid.in_(puuids))
        )
        return set(result.all())

    async def get_player_by_puuid(
            self,
            puuid: str
    ) -> Player | None:
        return await self.db.scalar(
            select(Player).where(Player.puuid == puuid)
        )

    async def get_player_by_riot_id(
            self,
            game_name: str,
            tag_line: str
    ) -> Player | None:
        result = await self.db.scalar(
            select(Player).where(
                Player.game_name == game_name,
                Player.tag_line == tag_line)
        )

        return result if result else None

    async def add_player(
            self,
            player: Player
    ) -> None:
        self.db.add(player)

class PlayerMatchRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_player_match(
            self,
            player_match: PlayerMatch
    ) -> None:
        self.db.add(player_match)
