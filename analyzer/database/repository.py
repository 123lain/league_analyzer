from sqlalchemy import select, desc, func, cast, Float, Integer
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

    async def get_player_match_history(
            self,
            puuid: str,
            limit: int = 10
    ):
        """
        JOIN Match and PlayerMatch to get needed data
        """
        stmt = (
            select(
                Match.match_id,
                Match.match_created,
                Match.match_duration_seconds,
                PlayerMatch.champion_name,
                PlayerMatch.kills,
                PlayerMatch.deaths,
                PlayerMatch.assists,
                PlayerMatch.creep_score,
                PlayerMatch.win,
                PlayerMatch.team_position
            )
            .join(PlayerMatch, Match.match_id == PlayerMatch.match_id)
            .where(PlayerMatch.puuid == puuid)
            .order_by(desc(Match.match_created))  # newest first
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        return result.mappings().all()

    async def get_player_champion_stats(
            self, puuid:
            str, limit:
            int = 5
    ):
        """
        Player's top champions, winrate and KDA
        """
        win_count = func.sum(PlayerMatch.win.cast(Integer))
        games_count = func.count(PlayerMatch.match_id)

        safe_deaths = func.greatest(func.sum(PlayerMatch.deaths), 1) # to not get division by zero errors

        stmt = (
            select(
                PlayerMatch.champion_name,
                games_count.label("games_played"),

                (cast(win_count, Float) / cast(games_count, Float) * 100).label("win_rate"),

                ((cast(func.sum(PlayerMatch.kills) + func.sum(PlayerMatch.assists), Float)) / cast(safe_deaths,
                                                                                                   Float)).label("kda"),

                func.round(func.avg(PlayerMatch.kills), 1).label("avg_kills"),
                func.round(func.avg(PlayerMatch.deaths), 1).label("avg_deaths"),
                func.round(func.avg(PlayerMatch.assists), 1).label("avg_assists"),
            )
            .where(PlayerMatch.puuid == puuid)
            .group_by(PlayerMatch.champion_name)
            .order_by(desc(games_count))  # sort by champion popularity for player
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        return result.mappings().all()