from datetime import datetime
from typing import Any

from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase
from sqlalchemy.dialects.postgresql import JSONB


class Base(DeclarativeBase):
    pass


class Player(Base):
    __tablename__ = 'players'

    puuid: Mapped[str] = mapped_column(
        String(80),
        primary_key=True,
    )
    game_name: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False
    )
    tag_line: Mapped[str] = mapped_column(
        Text,
        index=True,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now()
    )
    ranked_data: Mapped[list[Any] | dict | None] = mapped_column(JSONB, nullable=True) # list if its empty

    matches: Mapped[list['PlayerMatch']] = relationship(back_populates='player')


class Match(Base):
    __tablename__ = 'matches'

    match_id: Mapped[str] = mapped_column(
        String(30),
        primary_key=True,
    )
    match_created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True)
    )
    match_duration_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    queue_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=420
    )
    patch: Mapped[str] = mapped_column(
        String(16),
        nullable=False
    )
    raw_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=True
    )

    participants: Mapped[list['PlayerMatch']] = relationship(back_populates='match')


class PlayerMatch(Base):
    __tablename__ = 'player_matches'

    puuid: Mapped[str] = mapped_column(
        ForeignKey('players.puuid', ondelete='CASCADE'),
        primary_key=True,
    )
    match_id: Mapped[str] = mapped_column(
        ForeignKey('matches.match_id', ondelete='CASCADE'),
        primary_key=True,
    )

    champion_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    champion_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    kills: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    deaths: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    assists: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    creep_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    damage_dealt: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    win: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False
    )
    team_position: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default='UNKNOWN'
    )

    player: Mapped["Player"] = relationship(back_populates="matches")
    match: Mapped["Match"] = relationship(back_populates="participants")