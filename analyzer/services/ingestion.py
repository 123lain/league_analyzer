from datetime import timezone, datetime

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from analyzer.config import settings
from analyzer.core.logger import setup_logger
from analyzer.core.riot_client import RiotAPIClient
from analyzer.database import Match, Player, PlayerMatch
from analyzer.database.repository import PlayerRepository, MatchRepository, PlayerMatchRepository


logger = setup_logger()


class IngestionService:
    def __init__(
            self,
            db: AsyncSession,
            riot_client: RiotAPIClient
    ):
        self.db = db
        self.riot_client = riot_client
        self.player_repository = PlayerRepository(db)
        self.match_repository = MatchRepository(db)
        self.player_match_repository = PlayerMatchRepository(db)

    async def get_player_by_riot_id(
            self,
            game_name: str,
            tag_line: str,
            background_tasks: BackgroundTasks
    ) -> Player | None:
        player_in_db = await self.player_repository.get_player_by_riot_id(game_name, tag_line)

        if player_in_db is None:
            player = await self.riot_client.get_player_by_riot_id(game_name, tag_line)
            if player:
                ranked_entries = await self.ensure_ranked_data(player)

                player = Player(
                    puuid=player['puuid'],
                    game_name=player['gameName'],
                    tag_line=player['tagLine'],
                    ranked_data=ranked_entries
                )

                async with self.db.begin():
                    await self.player_repository.add_player(player)

                logger.info(f'Added profile for {player.game_name}#{player.tag_line} has ranked entries')

                background_tasks.add_task(
                    self.ingest_player_matches,
                    puuid=player.puuid,
                    count=settings.MATCH_HISTORY_LIMIT
                )
                return player
            else:
                return None
        else:
            logger.info(f'Player {player_in_db.puuid} already exists in database')
            player_in_db.ranked_data = await self.ensure_ranked_data(player_in_db)

            return player_in_db

    async def ensure_ranked_data(
            self,
            player: Player
    ):
        if player.ranked_data:
            return player.ranked_data

        logger.info(f"Fetching missing ranked data for {player.puuid}")
        new_ranked = await self.riot_client.get_ranked_entries(player.puuid)

        player.ranked_data = new_ranked if new_ranked else []

        return player.ranked_data

    async def ingest_player_matches(
            self,
            puuid: str,
            count: int
    ):
        """
        Get last {count} matches for player
        """
        logger.info(f'Started service for parsing player {puuid} matches')
        try:
            match_ids = await self.riot_client.get_recent_match_ids(puuid, count)
        except Exception as e:
            logger.error(f'Failed to get matches list from Riot API: {e}')
            raise

        if not match_ids:
            logger.info(f'Player {puuid} has no matches or Riot returned an empty list')
            return

        existing_ids = await self.match_repository.get_existing_match_ids(match_ids)
        await self.db.rollback() # to stop session

        new_match_ids = [m_id for m_id in match_ids if m_id not in existing_ids]
        logger.info(f'Found {len(new_match_ids)} new matches')

        for m_id in new_match_ids:
            try:
                raw_match_data = await self.riot_client.get_match_details(m_id)
                if not raw_match_data:
                    continue

                async with self.db.begin():
                    info = raw_match_data['info']
                    match_obj = Match(
                        match_id=m_id,
                        match_created=datetime.fromtimestamp(info['gameCreation'] / 1000, tz=timezone.utc),
                        match_duration_seconds=info['gameDuration'],
                        queue_id=info['queueId'],
                        patch=".".join(info.get('gameVersion').split('.')[:2]), # get the main patch and one digit after .
                        raw_data=raw_match_data
                    )
                    await self.match_repository.add_new_match(match_obj)

                    participant_puuids = {  # do this to queue all participants at once
                        participant['puuid']
                        for participant in info['participants']
                    }

                    existing_puuids = await self.player_repository.get_existing_puuids(participant_puuids)

                    for participant in info['participants']:
                        p_puuid = participant['puuid']

                        if p_puuid not in existing_puuids:
                            p_placeholder = Player(
                                puuid=p_puuid,
                                game_name=participant.get('riotIdGameName'),
                                tag_line=participant.get('riotIdTagline'),
                            )
                            await self.player_repository.add_player(p_placeholder)

                        creep_score = participant.get('totalMinionsKilled', 0) + participant.get('neutralMinionsKilled',
                                                                                                 0)

                        player_match_stats = PlayerMatch(
                            puuid=p_puuid,
                            match_id=m_id,
                            champion_id=participant.get('championId'),
                            champion_name=participant.get('championName'),
                            kills=participant.get('kills'),
                            deaths=participant.get('deaths'),
                            assists=participant.get('assists'),
                            creep_score=creep_score,
                            damage_dealt=participant.get('totalDamageDealtToChampions'),
                            win=participant.get('win'),
                            team_position=participant.get('teamPosition')
                        )
                        await self.player_match_repository.add_player_match(player_match_stats)

                logger.info(f'Match {m_id} added to database')
            except Exception as e:
                logger.error(f'Failed to pase match {m_id}: {e}')
                continue

        logger.info(f'Finished service for parsing player {puuid} matches')

    async def sync_player_and_matches(
            self,
            game_name: str,
            tag_line: str
    ) -> None:
        logger.info(f"Started synchronization for {game_name}#{tag_line}")

        try:
            riot_player = await self.riot_client.get_player_by_riot_id(game_name, tag_line)
            if not riot_player:
                logger.error(f"Player {game_name}#{tag_line} not found")
                return

            puuid = riot_player["puuid"]

            ranked_entries = await self.riot_client.get_ranked_entries(puuid)
            async with self.db.begin():
                player_in_db = await self.player_repository.get_player_by_puuid(puuid)

                if not player_in_db:
                    player_obj = Player(
                        puuid=puuid,
                        game_name=riot_player["gameName"],
                        tag_line=riot_player["tagLine"],
                        ranked_data=ranked_entries if ranked_entries else []
                    )
                    await self.player_repository.add_player(player_obj)
                    logger.info(f"Added new player profile for puuid {puuid}")
                else:
                    player_in_db.game_name = riot_player["gameName"]
                    player_in_db.tag_line = riot_player["tagLine"]
                    logger.info(f"Updated profile for puuid {puuid}")

            await self.ingest_player_matches(puuid, count=settings.MATCH_HISTORY_LIMIT)

        except Exception as e:
            logger.critical(f"Error while synchronizing {game_name}: {e}")

    async def get_player_match_history(
            self,
            puuid: str,
            limit: int = 10
    ):
        return await self.player_match_repository.get_player_match_history(puuid, limit)

    async def get_player_champion_stats(
            self,
            puuid: str,
            limit: int = 5
    ):
        return await self.player_match_repository.get_player_champion_stats(puuid, limit)
