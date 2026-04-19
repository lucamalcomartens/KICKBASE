from __future__ import annotations

import argparse
import ctypes
import json
import math
import sys
from ctypes import wintypes
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from kickbase_api import (  # noqa: E402
    KickbaseApiError,
    KickbaseClient,
    KickbaseConfigurationError,
    KickbaseLeague,
    KickbaseManagerTransfer,
    KickbaseMarketPlayer,
    KickbasePlayerMarketValue,
)


DEFAULT_LOOKBACK_DAYS = 90
DEFAULT_VALUE_TOLERANCE = 0.2
DEFAULT_SAFE_PERCENTILE = 0.8
DEFAULT_GAMBLE_PERCENTILE = 0.5
DEFAULT_MIN_SAMPLES = 5
DEFAULT_MAX_PAGES_PER_MANAGER = 12
MIN_MARKET_VALUE_HISTORY_DAYS = 92
FORECAST_VERSION = 3
FORECAST_LOG_PATH = PROJECT_ROOT / "Anwendungsfälle" / "daten" / "gebot_vorhersage_log.jsonl"
MAX_CALIBRATION_WINDOW_DAYS = 90
MARKET_VALUE_DISTANCE_SCALE = 0.18
TREND_DISTANCE_SCALE = 3.0
ACCELERATION_DISTANCE_SCALE = 2.5
MANAGER_WEIGHT_FACTOR = 0.1
POSITION_MISMATCH_WEIGHT = 0.72
PRICE_CLASS_MATCH_WEIGHT = 1.08
PRICE_CLASS_NEAR_WEIGHT = 0.96
PRICE_CLASS_FAR_WEIGHT = 0.88
SAME_TEAM_WEIGHT = 1.05
POSITION_CALIBRATION_BLEND = 0.65
PRICE_CLASS_CALIBRATION_BLEND = 0.85
TEAM_CALIBRATION_BLEND = 0.35
POSITION_CALIBRATION_FULL_COUNT = 12
PRICE_CLASS_CALIBRATION_FULL_COUNT = 12
TEAM_CALIBRATION_FULL_COUNT = 6
WINDOWS_CREDENTIAL_ERROR_NOT_FOUND = 1168
WINDOWS_CREDENTIAL_TYPE_GENERIC = 1
WINDOWS_TOKEN_CREDENTIAL_TARGETS = (
    "KICKBASE_TOKEN",
    "kickbase:token",
    "KICKBASE_TOKEN@KickAdvisor",
    "KICK_TOKEN@KickAdvisor",
)
WINDOWS_LOGIN_CREDENTIAL_TARGETS = ("KICKBASE_LOGIN", "kickbase:login")
WINDOWS_SPLIT_LOGIN_CREDENTIAL_TARGETS = (
    ("KICK_USER@KickAdvisor", "KICK_PASS@KickAdvisor"),
    ("KICKBASE_USER@KickAdvisor", "KICKBASE_PASSWORD@KickAdvisor"),
    ("KICKBASE_EMAIL@KickAdvisor", "KICKBASE_PASSWORD@KickAdvisor"),
    ("EMAIL_USER@KickAdvisor", "EMAIL_PASS@KickAdvisor"),
    ("KICK_USER", "KICK_PASS"),
    ("KICKBASE_USER", "KICKBASE_PASSWORD"),
    ("KICKBASE_EMAIL", "KICKBASE_PASSWORD"),
)


class _WinCredential(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


@dataclass(frozen=True, slots=True)
class MarktwertTrend:
    market_value: int
    one_day_log_slope_pct: float | None
    three_day_log_slope_pct: float | None
    seven_day_log_slope_pct: float | None
    acceleration_pct: float | None
    distance_to_14d_high_pct: float | None
    distance_to_14d_low_pct: float | None
    momentum_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "market_value": self.market_value,
            "one_day_log_slope_pct": _round_or_none(self.one_day_log_slope_pct),
            "three_day_log_slope_pct": _round_or_none(self.three_day_log_slope_pct),
            "seven_day_log_slope_pct": _round_or_none(self.seven_day_log_slope_pct),
            "acceleration_pct": _round_or_none(self.acceleration_pct),
            "distance_to_14d_high_pct": _round_or_none(self.distance_to_14d_high_pct),
            "distance_to_14d_low_pct": _round_or_none(self.distance_to_14d_low_pct),
            "momentum_score": round(self.momentum_score, 4),
        }


@dataclass(frozen=True, slots=True)
class MarktKontext:
    captured_at: str
    expires_at: str | None
    hours_to_expiry: float | None
    projected_market_value_at_expiry: int
    bid_reference_market_value: int
    list_price: int | None
    bid_floor: int
    list_price_delta_pct: float | None
    current_position: int | None
    current_team_id: str | None
    current_team_name: str | None
    price_class: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "captured_at": self.captured_at,
            "expires_at": self.expires_at,
            "hours_to_expiry": _round_or_none(self.hours_to_expiry),
            "projected_market_value_at_expiry": self.projected_market_value_at_expiry,
            "bid_reference_market_value": self.bid_reference_market_value,
            "list_price": self.list_price,
            "bid_floor": self.bid_floor,
            "list_price_delta_pct": _round_or_none(self.list_price_delta_pct),
            "current_position": self.current_position,
            "current_team_id": self.current_team_id,
            "current_team_name": self.current_team_name,
            "price_class": self.price_class,
        }


@dataclass(frozen=True, slots=True)
class ManagerAggressionProfile:
    manager_id: str
    manager_name: str | None
    transfer_count: int
    mean_overpay_pct: float
    p80_overpay_pct: float
    aggression_score_pct: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "manager_id": self.manager_id,
            "manager_name": self.manager_name,
            "transfer_count": self.transfer_count,
            "mean_overpay_pct": round(self.mean_overpay_pct, 4),
            "p80_overpay_pct": round(self.p80_overpay_pct, 4),
            "aggression_score_pct": round(self.aggression_score_pct, 4),
        }


@dataclass(frozen=True, slots=True)
class CalibrationSummary:
    completed_sample_count: int
    safe_hit_rate: float | None
    gamble_hit_rate: float | None
    safe_adjustment_pct: float
    gamble_adjustment_pct: float
    position_sample_count: int = 0
    price_class_sample_count: int = 0
    team_sample_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "completed_sample_count": self.completed_sample_count,
            "safe_hit_rate": _round_or_none(self.safe_hit_rate),
            "gamble_hit_rate": _round_or_none(self.gamble_hit_rate),
            "safe_adjustment_pct": round(self.safe_adjustment_pct, 4),
            "gamble_adjustment_pct": round(self.gamble_adjustment_pct, 4),
            "position_sample_count": self.position_sample_count,
            "price_class_sample_count": self.price_class_sample_count,
            "team_sample_count": self.team_sample_count,
        }


@dataclass(frozen=True, slots=True)
class CalibrationCase:
    player_id: str
    position: int | None
    team_id: str | None
    price_class: str
    safe_hit: float
    gamble_hit: float
    safe_delta_pct: float
    gamble_delta_pct: float


@dataclass(frozen=True, slots=True)
class TransferGebotsSample:
    manager_id: str
    manager_name: str | None
    player_id: str
    player_name: str
    transfer_date: str
    winning_bid: int
    reference_market_value: int
    overpay: int
    overpay_pct: float
    position: int | None
    team_id: str | None
    price_class: str
    recency_days: float
    manager_aggression_pct: float
    similarity_weight: float
    weight_market_value: float
    weight_recency: float
    weight_trend: float
    weight_position: float
    weight_price_class: float
    weight_team: float
    weight_manager: float
    trend: MarktwertTrend

    def to_dict(self) -> dict[str, Any]:
        return {
            "manager_id": self.manager_id,
            "manager_name": self.manager_name,
            "player_id": self.player_id,
            "player_name": self.player_name,
            "transfer_date": self.transfer_date,
            "winning_bid": self.winning_bid,
            "reference_market_value": self.reference_market_value,
            "overpay": self.overpay,
            "overpay_pct": round(self.overpay_pct, 2),
            "position": self.position,
            "team_id": self.team_id,
            "price_class": self.price_class,
            "recency_days": round(self.recency_days, 3),
            "manager_aggression_pct": round(self.manager_aggression_pct, 4),
            "similarity_weight": round(self.similarity_weight, 6),
            "weight_market_value": round(self.weight_market_value, 6),
            "weight_recency": round(self.weight_recency, 6),
            "weight_trend": round(self.weight_trend, 6),
            "weight_position": round(self.weight_position, 6),
            "weight_price_class": round(self.weight_price_class, 6),
            "weight_team": round(self.weight_team, 6),
            "weight_manager": round(self.weight_manager, 6),
            "trend": self.trend.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class GebotsVorhersage:
    league_id: str
    player_id: str
    player_name: str
    market_value: int
    projected_market_value_at_expiry: int
    bid_reference_market_value: int
    list_price: int | None
    bid_floor: int
    lookback_days: int
    value_tolerance: float
    target_trend: MarktwertTrend
    target_context: MarktKontext
    total_recent_buy_samples: int
    primary_sample_count: int
    sample_count: int
    min_samples_target: int
    selection_mode: str
    sample_weight_sum: float
    weighted_gamble_base_pct: float
    weighted_safe_base_pct: float
    calibration: CalibrationSummary
    gamble_percentile: float
    gamble_overpay_pct: float
    gamble_bid: int
    safe_percentile: float
    safe_overpay_pct: float
    safe_bid: int
    average_overpay_pct: float
    median_overpay_pct: float
    max_overpay_pct: float
    warning: str | None
    samples: tuple[TransferGebotsSample, ...]

    @property
    def gamble_overpay_absolute(self) -> int:
        return self.gamble_bid - self.bid_reference_market_value

    @property
    def safe_overpay_absolute(self) -> int:
        return self.safe_bid - self.bid_reference_market_value

    def to_dict(self, *, include_samples: bool = False) -> dict[str, Any]:
        payload = {
            "league_id": self.league_id,
            "player_id": self.player_id,
            "player_name": self.player_name,
            "market_value": self.market_value,
            "projected_market_value_at_expiry": self.projected_market_value_at_expiry,
            "bid_reference_market_value": self.bid_reference_market_value,
            "list_price": self.list_price,
            "bid_floor": self.bid_floor,
            "lookback_days": self.lookback_days,
            "value_tolerance": round(self.value_tolerance, 4),
            "target_trend": self.target_trend.to_dict(),
            "target_context": self.target_context.to_dict(),
            "total_recent_buy_samples": self.total_recent_buy_samples,
            "primary_sample_count": self.primary_sample_count,
            "sample_count": self.sample_count,
            "min_samples_target": self.min_samples_target,
            "selection_mode": self.selection_mode,
            "sample_weight_sum": round(self.sample_weight_sum, 4),
            "weighted_gamble_base_pct": round(self.weighted_gamble_base_pct, 2),
            "weighted_safe_base_pct": round(self.weighted_safe_base_pct, 2),
            "calibration": self.calibration.to_dict(),
            "gamble_percentile_rank": round(self.gamble_percentile * 100, 1),
            "gamble_overpay_pct": round(self.gamble_overpay_pct, 2),
            "gamble_overpay_absolute": self.gamble_overpay_absolute,
            "gamble_bid": self.gamble_bid,
            "safe_percentile_rank": round(self.safe_percentile * 100, 1),
            "safe_overpay_pct": round(self.safe_overpay_pct, 2),
            "safe_overpay_absolute": self.safe_overpay_absolute,
            "safe_bid": self.safe_bid,
            "average_overpay_pct": round(self.average_overpay_pct, 2),
            "median_overpay_pct": round(self.median_overpay_pct, 2),
            "max_overpay_pct": round(self.max_overpay_pct, 2),
            "warning": self.warning,
        }
        if include_samples:
            payload["samples"] = [sample.to_dict() for sample in self.samples]
        return payload


@dataclass(frozen=True, slots=True)
class _WindowsGenericCredential:
    target_name: str
    username: str | None
    secret: str


@dataclass(frozen=True, slots=True)
class ForecastEnvironment:
    league: KickbaseLeague
    captured_at: datetime
    market_players: tuple[KickbaseMarketPlayer, ...]
    player_metadata_by_id: dict[str, dict[str, Any]]
    samples: tuple[TransferGebotsSample, ...]
    manager_profiles_by_id: dict[str, ManagerAggressionProfile]
    calibration: CalibrationSummary
    calibration_cases: tuple[CalibrationCase, ...]


@dataclass(frozen=True, slots=True)
class InteractiveMarketSelectionItem:
    player: KickbaseMarketPlayer
    recent_market_value_changes: tuple[int | None, int | None, int | None]


def estimate_market_player_bid(
    client: KickbaseClient,
    league_id: str,
    *,
    player_id: str | None = None,
    player_name: str | None = None,
    days: int = DEFAULT_LOOKBACK_DAYS,
    value_tolerance: float = DEFAULT_VALUE_TOLERANCE,
    safe_percentile: float = DEFAULT_SAFE_PERCENTILE,
    gamble_percentile: float = DEFAULT_GAMBLE_PERCENTILE,
    min_samples: int = DEFAULT_MIN_SAMPLES,
    max_pages_per_manager: int = DEFAULT_MAX_PAGES_PER_MANAGER,
    forecast_environment: ForecastEnvironment | None = None,
) -> GebotsVorhersage:
    normalized_days = int(days)
    normalized_tolerance = float(value_tolerance)
    normalized_min_samples = int(min_samples)

    if normalized_days <= 0:
        raise ValueError("days must be greater than zero.")
    if normalized_tolerance < 0:
        raise ValueError("value_tolerance must be zero or greater.")
    if normalized_min_samples <= 0:
        raise ValueError("min_samples must be greater than zero.")
    _validate_percentile("safe_percentile", safe_percentile)
    _validate_percentile("gamble_percentile", gamble_percentile)
    if gamble_percentile > safe_percentile:
        raise ValueError("gamble_percentile must be less than or equal to safe_percentile.")

    environment = forecast_environment or prepare_forecast_environment(
        client,
        league_id,
        days=normalized_days,
        max_pages_per_manager=max_pages_per_manager,
    )
    captured_at = environment.captured_at
    league = environment.league
    if not league.competition_id:
        raise KickbaseApiError("The selected league does not expose a competition ID.")

    market_players = list(environment.market_players)
    target_player = _resolve_market_player(
        client,
        league.id,
        player_id=player_id,
        player_name=player_name,
        market_players=market_players,
    )
    if target_player.market_value is None or target_player.market_value <= 0:
        raise KickbaseApiError("The selected market player does not expose a usable market value.")

    player_metadata_by_id = environment.player_metadata_by_id
    target_position = target_player.position
    if target_position is None:
        target_position = _player_position_from_metadata(player_metadata_by_id, target_player.player_id)
    target_team_id = target_player.team_id or _player_team_id_from_metadata(player_metadata_by_id, target_player.player_id)
    target_team_name = _player_team_name_from_metadata(player_metadata_by_id, target_player.player_id)

    target_history = client.get_player_market_value_history(
        league.competition_id,
        target_player.player_id,
        days=max(normalized_days, MIN_MARKET_VALUE_HISTORY_DAYS),
    )
    target_index = len(target_history) - 1
    if target_index < 0:
        raise KickbaseApiError("No market value history was returned for the selected player.")
    target_trend = _trend_from_history(target_history, target_index)
    hours_to_expiry = _hours_to_expiry(_parse_iso_timestamp(target_player.expires_at), reference_time=captured_at)
    projected_market_value_at_expiry = _project_market_value_at_expiry(
        target_player.market_value,
        target_trend.momentum_score,
        hours_to_expiry,
    )
    bid_reference_market_value = max(1, projected_market_value_at_expiry)
    target_price_class = _price_class_key_from_market_value(bid_reference_market_value)
    list_price = target_player.list_price
    bid_floor = max(0, list_price or 0)

    samples = list(environment.samples)
    if not samples:
        raise KickbaseApiError("Recent buy transfers were found, but no comparable market value history was usable.")

    manager_profiles_by_id = environment.manager_profiles_by_id
    weighted_samples, selection_mode, primary_sample_count = _prepare_weighted_samples(
        samples,
        target_market_value=bid_reference_market_value,
        target_trend=target_trend,
        target_position=target_position,
        target_team_id=target_team_id,
        target_price_class=target_price_class,
        value_tolerance=normalized_tolerance,
        manager_profiles_by_id=manager_profiles_by_id,
        min_samples=normalized_min_samples,
    )
    if not weighted_samples:
        raise KickbaseApiError("No comparable transfers were available for the bid forecast.")

    sample_weights = [sample.similarity_weight for sample in weighted_samples]
    overpay_values = [sample.overpay_pct for sample in weighted_samples]
    weighted_average_overpay_pct = _weighted_average(overpay_values, sample_weights)
    weighted_median_overpay_pct = _weighted_quantile(overpay_values, sample_weights, 0.5)
    weighted_gamble_base_pct = _weighted_quantile(overpay_values, sample_weights, gamble_percentile)
    weighted_safe_base_pct = _weighted_quantile(overpay_values, sample_weights, safe_percentile)
    calibration = _build_calibration_summary(
        client,
        league_id=league.id,
        reference_time=captured_at,
        minimum_days=normalized_days,
        cached_summary=environment.calibration,
        target_position=target_position,
        target_team_id=target_team_id,
        target_price_class=target_price_class,
        player_metadata_by_id=player_metadata_by_id,
        cached_cases=environment.calibration_cases,
    )

    gamble_overpay_pct = max(
        0.0,
        weighted_gamble_base_pct
        + calibration.gamble_adjustment_pct,
    )
    safe_overpay_pct = max(
        0.0,
        weighted_safe_base_pct
        + calibration.safe_adjustment_pct,
    )
    gamble_bid = max(bid_floor, _apply_overpay(bid_reference_market_value, gamble_overpay_pct))
    safe_bid = max(bid_floor, _apply_overpay(bid_reference_market_value, safe_overpay_pct))

    target_context = MarktKontext(
        captured_at=captured_at.isoformat().replace("+00:00", "Z"),
        expires_at=target_player.expires_at,
        hours_to_expiry=hours_to_expiry,
        projected_market_value_at_expiry=projected_market_value_at_expiry,
        bid_reference_market_value=bid_reference_market_value,
        list_price=list_price,
        bid_floor=bid_floor,
        list_price_delta_pct=_list_price_delta_pct(list_price, projected_market_value_at_expiry),
        current_position=target_position,
        current_team_id=target_team_id,
        current_team_name=target_team_name,
        price_class=target_price_class,
    )
    warning = _build_sample_warning(
        total_samples=len(samples),
        primary_sample_count=primary_sample_count,
        selected_sample_count=len(weighted_samples),
        min_samples=normalized_min_samples,
        selection_mode=selection_mode,
        calibration=calibration,
        bid_floor=bid_floor,
        lowest_model_bid=min(gamble_bid, safe_bid),
    )
    forecast = GebotsVorhersage(
        league_id=league.id,
        player_id=target_player.player_id,
        player_name=target_player.full_name,
        market_value=target_player.market_value,
        projected_market_value_at_expiry=projected_market_value_at_expiry,
        bid_reference_market_value=bid_reference_market_value,
        list_price=list_price,
        bid_floor=bid_floor,
        lookback_days=normalized_days,
        value_tolerance=normalized_tolerance,
        target_trend=target_trend,
        target_context=target_context,
        total_recent_buy_samples=len(samples),
        primary_sample_count=primary_sample_count,
        sample_count=len(weighted_samples),
        min_samples_target=normalized_min_samples,
        selection_mode=selection_mode,
        sample_weight_sum=sum(sample_weights),
        weighted_gamble_base_pct=weighted_gamble_base_pct,
        weighted_safe_base_pct=weighted_safe_base_pct,
        calibration=calibration,
        gamble_percentile=gamble_percentile,
        gamble_overpay_pct=gamble_overpay_pct,
        gamble_bid=gamble_bid,
        safe_percentile=safe_percentile,
        safe_overpay_pct=safe_overpay_pct,
        safe_bid=safe_bid,
        average_overpay_pct=weighted_average_overpay_pct,
        median_overpay_pct=weighted_median_overpay_pct,
        max_overpay_pct=max(overpay_values),
        warning=warning,
        samples=tuple(sorted(weighted_samples, key=lambda item: item.transfer_date, reverse=True)),
    )
    _append_forecast_log(forecast, league_name=league.name)
    return forecast


def prepare_forecast_environment(
    client: KickbaseClient,
    league_id: str,
    *,
    days: int = DEFAULT_LOOKBACK_DAYS,
    max_pages_per_manager: int = DEFAULT_MAX_PAGES_PER_MANAGER,
    captured_at: datetime | None = None,
) -> ForecastEnvironment:
    normalized_days = int(days)
    normalized_max_pages = int(max_pages_per_manager)
    if normalized_days <= 0:
        raise ValueError("days must be greater than zero.")
    if normalized_max_pages <= 0:
        raise ValueError("max_pages_per_manager must be greater than zero.")

    runtime_captured_at = captured_at or datetime.now(timezone.utc)
    league = _resolve_league_by_id(client, league_id)
    if not league.competition_id:
        raise KickbaseApiError("The selected league does not expose a competition ID.")

    market_players = tuple(client.get_market_players(league.id))
    player_metadata_by_id = _load_competition_player_metadata(client, league.competition_id)
    transfers = collect_recent_buy_transfers(
        client,
        league.id,
        days=normalized_days,
        max_pages_per_manager=normalized_max_pages,
    )
    if not transfers:
        raise KickbaseApiError("No recent buy transfers were found for this league.")

    samples = tuple(
        _build_transfer_samples(
            client,
            competition_id=league.competition_id,
            transfers=transfers,
            market_value_history_days=max(normalized_days, MIN_MARKET_VALUE_HISTORY_DAYS),
            player_metadata_by_id=player_metadata_by_id,
            reference_time=runtime_captured_at,
        )
    )
    if not samples:
        raise KickbaseApiError("Recent buy transfers were found, but no comparable market value history was usable.")

    manager_profiles_by_id = _build_manager_profiles(list(samples))
    calibration_cases = _build_calibration_cases(
        client,
        league_id=league.id,
        reference_time=runtime_captured_at,
        minimum_days=normalized_days,
        player_metadata_by_id=player_metadata_by_id,
    )
    calibration = _build_calibration_summary(
        client,
        league_id=league.id,
        reference_time=runtime_captured_at,
        minimum_days=normalized_days,
        player_metadata_by_id=player_metadata_by_id,
        cached_cases=calibration_cases,
    )
    return ForecastEnvironment(
        league=league,
        captured_at=runtime_captured_at,
        market_players=market_players,
        player_metadata_by_id=player_metadata_by_id,
        samples=samples,
        manager_profiles_by_id=manager_profiles_by_id,
        calibration=calibration,
        calibration_cases=calibration_cases,
    )


def collect_recent_buy_transfers(
    client: KickbaseClient,
    league_id: str,
    *,
    days: int = DEFAULT_LOOKBACK_DAYS,
    max_pages_per_manager: int = DEFAULT_MAX_PAGES_PER_MANAGER,
) -> list[KickbaseManagerTransfer]:
    normalized_days = int(days)
    normalized_max_pages = int(max_pages_per_manager)
    if normalized_days <= 0:
        raise ValueError("days must be greater than zero.")
    if normalized_max_pages <= 0:
        raise ValueError("max_pages_per_manager must be greater than zero.")

    cutoff = datetime.now(timezone.utc) - timedelta(days=normalized_days)
    transfers: list[KickbaseManagerTransfer] = []
    seen_transfers: set[tuple[str, str, str, int | None, int | None]] = set()

    for manager in client.get_league_managers(league_id):
        start = 0
        seen_pages: set[tuple[tuple[str, str, int | None, int | None], ...]] = set()
        for _ in range(normalized_max_pages):
            page = client.get_manager_transfer_history(league_id, manager.manager_id, start=start)
            if not page:
                break

            page_signature = tuple(
                (item.player_id, item.date, item.transfer_type, item.price)
                for item in page
            )
            if page_signature in seen_pages:
                break
            seen_pages.add(page_signature)

            reached_cutoff = False
            for item in page:
                transfer_timestamp = _parse_iso_timestamp(item.date)
                if transfer_timestamp is None:
                    continue
                if transfer_timestamp < cutoff:
                    reached_cutoff = True
                    continue
                if item.transfer_type_text != "buy":
                    continue

                transfer_key = (
                    item.manager_id,
                    item.player_id,
                    item.date,
                    item.transfer_type,
                    item.price,
                )
                if transfer_key in seen_transfers:
                    continue
                seen_transfers.add(transfer_key)
                transfers.append(item)

            if reached_cutoff:
                break
            start += len(page)

    transfers.sort(key=lambda item: item.date, reverse=True)
    return transfers


def format_summary(forecast: GebotsVorhersage) -> str:
    lines = [
        f"Spieler: {forecast.player_name} ({forecast.player_id})",
        (
            f"Aktueller MW: {forecast.market_value} | Prognose bis Ablauf: "
            f"{forecast.projected_market_value_at_expiry} | Listenpreis: {forecast.list_price or 'n/a'} | "
            f"Mindestboden: {forecast.bid_floor}"
        ),
        (
            "Trend: "
            f"1D={_format_pct(forecast.target_trend.one_day_log_slope_pct)}, "
            f"3D/d={_format_pct(forecast.target_trend.three_day_log_slope_pct)}, "
            f"7D/d={_format_pct(forecast.target_trend.seven_day_log_slope_pct)}, "
            f"Beschleunigung={_format_pct(forecast.target_trend.acceleration_pct)}, "
            f"Momentum={forecast.target_trend.momentum_score:+.2f}%"
        ),
        (
            "Range 14T: "
            f"Distanz zum Hoch={_format_pct(forecast.target_trend.distance_to_14d_high_pct)}, "
            f"Distanz zum Tief={_format_pct(forecast.target_trend.distance_to_14d_low_pct)}"
        ),
        (
            "Kontext: "
            + ", ".join(
                part
                for part in [
                    f"Stunden bis Ablauf={_format_optional_number(forecast.target_context.hours_to_expiry, 1)}",
                    (
                        f"Position={_format_position_label(forecast.target_context.current_position)}"
                        if forecast.target_context.current_position is not None
                        else None
                    ),
                    f"Preisklasse={_price_class_label(forecast.target_context.price_class)}",
                    (
                        f"Verein={forecast.target_context.current_team_name}"
                        if forecast.target_context.current_team_name
                        else None
                    ),
                ]
                if part
            )
        ),
        (
            "Gewichtete Basis: "
            f"Zocken={forecast.weighted_gamble_base_pct:+.2f}%, "
            f"Sicher={forecast.weighted_safe_base_pct:+.2f}%, "
            f"Mittel={forecast.average_overpay_pct:+.2f}%, "
            f"Median={forecast.median_overpay_pct:+.2f}%"
        ),
        (
            "Praemien: "
            f"Kalibrierung Sicher={forecast.calibration.safe_adjustment_pct:+.2f}%, "
            f"Kalibrierung Zocken={forecast.calibration.gamble_adjustment_pct:+.2f}%"
        ),
        (
            f"Final: Zocken={forecast.gamble_bid} (Basis + {forecast.gamble_overpay_absolute}, "
            f"{forecast.gamble_overpay_pct:.2f}%), Sicher={forecast.safe_bid} "
            f"(Basis + {forecast.safe_overpay_absolute}, {forecast.safe_overpay_pct:.2f}%)"
        ),
        (
            f"Samples: {forecast.sample_count} genutzt, {forecast.primary_sample_count} direkt im +/-"
            f"{forecast.value_tolerance * 100:.0f}% Marktwertband, Gewichtssumme={forecast.sample_weight_sum:.2f}, "
            f"Modus={forecast.selection_mode}"
        ),
    ]
    if forecast.calibration.completed_sample_count:
        lines.append(
            "Kalibrierung: "
            f"{forecast.calibration.completed_sample_count} abgeschlossene Logs, "
            f"Position={forecast.calibration.position_sample_count}, "
            f"Preisklasse={forecast.calibration.price_class_sample_count}, "
            f"Verein={forecast.calibration.team_sample_count}, "
            f"Sicher-Trefferquote={_format_ratio_pct(forecast.calibration.safe_hit_rate)}, "
            f"Zocken-Trefferquote={_format_ratio_pct(forecast.calibration.gamble_hit_rate)}"
        )
    if forecast.warning:
        lines.append(f"Warnung: {forecast.warning}")
    return "\n".join(lines)


def format_buy_recommendation(forecast: GebotsVorhersage) -> str:
    return _format_buy_recommendation_block(forecast)


def format_buy_recommendations(forecasts: list[GebotsVorhersage]) -> str:
    if not forecasts:
        return ""
    if len(forecasts) == 1:
        return _format_buy_recommendation_block(forecasts[0])
    return "\n\n".join(
        _format_buy_recommendation_block(forecast, index=index)
        for index, forecast in enumerate(forecasts, start=1)
    )


def _format_buy_recommendation_block(
    forecast: GebotsVorhersage,
    *,
    index: int | None = None,
) -> str:
    header = forecast.player_name if index is None else f"{index}. {forecast.player_name}"
    lines = [
        header,
        f"   {_format_percentile_label(forecast.gamble_percentile)}: {_format_money(forecast.gamble_bid)}",
        f"   {_format_percentile_label(forecast.safe_percentile)}: {_format_money(forecast.safe_bid)}",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gebotsvorhersage fuer aktuelle Kickbase-Marktspieler")
    parser.add_argument("--league-id", help="Liga-ID. Falls leer, wird ueber --league-name oder den ersten Liga-Treffer aufgeloest.")
    parser.add_argument("--league-name", help="Exakter Ligename als Alternative zur Liga-ID.")
    parser.add_argument("--player-id", help="Spieler-ID des aktuellen Marktspielers.")
    parser.add_argument("--player-name", help="Exakter Name des aktuellen Marktspielers.")
    parser.add_argument("--token", help="Optionaler Kickbase-Token als direkter Override der Windows-Anmeldeinformationen.")
    parser.add_argument("--update-hour", type=int, default=22, help="Stunde des naechsten Marktwert-Updates in lokaler Zeit.")
    parser.add_argument("--days", type=int, default=DEFAULT_LOOKBACK_DAYS, help="Lookback-Fenster in Tagen.")
    parser.add_argument("--details", action="store_true", help="Zeigt den ausfuehrlichen Modell- und Kontextblock an.")
    parser.add_argument(
        "--value-tolerance",
        type=float,
        default=DEFAULT_VALUE_TOLERANCE,
        help="Marktwertband fuer Vergleichstransfers, z.B. 0.2 fuer +/-20%%.",
    )
    parser.add_argument("--safe-percentile", type=float, default=DEFAULT_SAFE_PERCENTILE)
    parser.add_argument("--gamble-percentile", type=float, default=DEFAULT_GAMBLE_PERCENTILE)
    parser.add_argument("--min-samples", type=int, default=DEFAULT_MIN_SAMPLES)
    args = parser.parse_args(argv)

    if args.update_hour < 0 or args.update_hour > 23:
        parser.error("--update-hour muss zwischen 0 und 23 liegen.")

    try:
        client = _build_client(args)
        league = _resolve_league(client, league_id=args.league_id, league_name=args.league_name)
        if not league.competition_id:
            raise KickbaseApiError("The selected league does not expose a competition ID.")

        forecasts: list[GebotsVorhersage]
        if not args.player_id and not args.player_name:
            selected_players = _select_market_players_interactively(
                client,
                league.id,
                competition_id=league.competition_id,
                update_hour=args.update_hour,
            )
            environment = prepare_forecast_environment(
                client,
                league.id,
                days=args.days,
            )
            forecasts = [
                estimate_market_player_bid(
                    client,
                    league.id,
                    player_id=selected_player.player_id,
                    days=args.days,
                    value_tolerance=args.value_tolerance,
                    safe_percentile=args.safe_percentile,
                    gamble_percentile=args.gamble_percentile,
                    min_samples=args.min_samples,
                    forecast_environment=environment,
                )
                for selected_player in selected_players
            ]
        else:
            forecasts = [
                estimate_market_player_bid(
                    client,
                    league.id,
                    player_id=args.player_id,
                    player_name=args.player_name,
                    days=args.days,
                    value_tolerance=args.value_tolerance,
                    safe_percentile=args.safe_percentile,
                    gamble_percentile=args.gamble_percentile,
                    min_samples=args.min_samples,
                )
            ]
    except (KickbaseApiError, KickbaseConfigurationError, ValueError) as error:
        print(f"Fehler: {error}")
        return 1

    print()
    print(f"Liga: {league.name} ({league.id})")
    print()
    print(format_buy_recommendations(forecasts))
    if args.details:
        for index, forecast in enumerate(forecasts, start=1):
            print()
            print(f"Details: {index}. {forecast.player_name}")
            print(format_summary(forecast))
    return 0


def _build_client(args: argparse.Namespace) -> KickbaseClient:
    token = str(args.token or "").strip()
    if token:
        return KickbaseClient(token)

    token_credential = _read_first_windows_generic_credential(WINDOWS_TOKEN_CREDENTIAL_TARGETS)
    if token_credential is not None:
        token_secret = token_credential.secret.strip()
        if not token_secret:
            raise KickbaseConfigurationError(
                f"Der Windows-Credential-Manager-Eintrag '{token_credential.target_name}' enthaelt keinen Token."
            )
        return KickbaseClient(token_secret)

    login_credential = _read_first_windows_generic_credential(WINDOWS_LOGIN_CREDENTIAL_TARGETS)
    if login_credential is not None:
        username = str(login_credential.username or "").strip()
        password = login_credential.secret.strip()
        if not username or not password:
            raise KickbaseConfigurationError(
                f"Der Windows-Credential-Manager-Eintrag '{login_credential.target_name}' braucht Benutzername und Passwort."
            )
        return KickbaseClient.login(username, password)

    split_login_client = _build_client_from_split_windows_credentials()
    if split_login_client is not None:
        return split_login_client

    try:
        return KickbaseClient.from_env()
    except KickbaseConfigurationError as error:
        raise KickbaseConfigurationError(_windows_credential_help_message()) from error


def _build_client_from_split_windows_credentials() -> KickbaseClient | None:
    last_error: KickbaseApiError | None = None
    for username_target, password_target in WINDOWS_SPLIT_LOGIN_CREDENTIAL_TARGETS:
        username_credential = _read_windows_generic_credential(username_target)
        password_credential = _read_windows_generic_credential(password_target)
        if username_credential is None or password_credential is None:
            continue

        username = username_credential.secret.strip()
        password = password_credential.secret.strip()
        if not username or not password:
            continue

        try:
            return KickbaseClient.login(username, password)
        except KickbaseApiError as error:
            last_error = error
            continue

    if last_error is not None:
        raise last_error
    return None


def _read_first_windows_generic_credential(
    target_names: tuple[str, ...],
) -> _WindowsGenericCredential | None:
    for target_name in target_names:
        credential = _read_windows_generic_credential(target_name)
        if credential is not None:
            return credential
    return None


def _read_windows_generic_credential(target_name: str) -> _WindowsGenericCredential | None:
    if sys.platform != "win32":
        return None

    advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
    credential_pointer = ctypes.POINTER(_WinCredential)()
    cred_read = advapi32.CredReadW
    cred_read.argtypes = [wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.POINTER(_WinCredential))]
    cred_read.restype = wintypes.BOOL

    cred_free = advapi32.CredFree
    cred_free.argtypes = [ctypes.c_void_p]
    cred_free.restype = None

    if not cred_read(target_name, WINDOWS_CREDENTIAL_TYPE_GENERIC, 0, ctypes.byref(credential_pointer)):
        error_code = ctypes.get_last_error()
        if error_code == WINDOWS_CREDENTIAL_ERROR_NOT_FOUND:
            return None
        raise OSError(f"CredReadW fehlgeschlagen fuer '{target_name}' (Win32-Fehler {error_code}).")

    try:
        credential = credential_pointer.contents
        blob_size = int(credential.CredentialBlobSize or 0)
        blob = b""
        if blob_size > 0 and credential.CredentialBlob:
            blob = ctypes.string_at(credential.CredentialBlob, blob_size)
        return _WindowsGenericCredential(
            target_name=target_name,
            username=str(credential.UserName or "").strip() or None,
            secret=_decode_windows_credential_blob(blob),
        )
    finally:
        cred_free(credential_pointer)


def _decode_windows_credential_blob(blob: bytes) -> str:
    if not blob:
        return ""
    for encoding in ("utf-16-le", "utf-8"):
        try:
            return blob.decode(encoding).rstrip("\x00")
        except UnicodeDecodeError:
            continue
    return blob.decode("latin-1").rstrip("\x00")


def _windows_credential_help_message() -> str:
    return (
        "Keine Kickbase-Credentials gefunden. Lege in der Windows-Anmeldeinformationsverwaltung ein generisches "
        "Credential 'KICKBASE_TOKEN' an (Kennwort = Token) oder 'KICKBASE_LOGIN' "
        "(Benutzername = Kickbase-Mail, Kennwort = Passwort). Vorhandene Legacy-Eintraege wie "
        "'KICK_USER@KickAdvisor' und 'KICK_PASS@KickAdvisor' werden ebenfalls unterstuetzt. Alternativ per cmdkey: "
        "cmdkey /generic:KICKBASE_TOKEN /user:token /pass:DEIN_TOKEN"
    )


def _resolve_league(client: KickbaseClient, *, league_id: str | None, league_name: str | None) -> KickbaseLeague:
    if league_id:
        return _resolve_league_by_id(client, league_id)
    return client.resolve_league(league_name)


def _resolve_league_by_id(client: KickbaseClient, league_id: str) -> KickbaseLeague:
    league_id_text = str(league_id or "").strip()
    if not league_id_text:
        raise ValueError("league_id is required.")

    for league in client.list_leagues():
        if league.id == league_id_text:
            return league
    raise ValueError(f"League '{league_id_text}' was not found for this account.")


def _resolve_market_player(
    client: KickbaseClient,
    league_id: str,
    *,
    player_id: str | None,
    player_name: str | None,
    market_players: list[KickbaseMarketPlayer] | None = None,
) -> KickbaseMarketPlayer:
    resolved_market_players = market_players or client.get_market_players(league_id)
    if player_id:
        player_id_text = str(player_id).strip()
        for player in resolved_market_players:
            if player.player_id == player_id_text:
                return player
        raise ValueError(f"Market player with id '{player_id_text}' was not found.")

    player_name_text = str(player_name or "").strip().casefold()
    for player in resolved_market_players:
        if player.full_name.casefold() == player_name_text:
            return player
    raise ValueError(f"Market player '{player_name}' was not found.")


def _select_market_players_interactively(
    client: KickbaseClient,
    league_id: str,
    *,
    competition_id: str,
    update_hour: int,
) -> list[KickbaseMarketPlayer]:
    selection_items, selection_header, selection_title = get_market_players_for_interactive_selection(
        client,
        league_id,
        competition_id=competition_id,
        update_hour=update_hour,
    )
    next_update = _next_market_update_local(update_hour=update_hour)

    if selection_header:
        print(selection_header)
        print()
    print(selection_title or f"Marktspieler bis zum naechsten Update um {next_update.strftime('%d.%m.%Y %H:%M')}:")
    print()
    for index, item in enumerate(selection_items, start=1):
        player = item.player
        expires_text = _format_local_expiry(player.expires_at)
        print(f"{index:>2}. {player.full_name}")
        print(
            f"    MW {_format_money_optional(player.market_value)} | "
            f"Preis {_format_money_optional(player.list_price)} | Ablauf {expires_text}"
        )
        print(
            "    Aend. 1T/2T/3T: "
            f"{_format_market_value_change_series(item.recent_market_value_changes)}"
        )
        if index != len(selection_items):
            print()

    selections = _prompt_selection(len(selection_items))
    return [selection_items[selection - 1].player for selection in selections]


def get_market_players_for_interactive_selection(
    client: KickbaseClient,
    league_id: str,
    *,
    competition_id: str,
    update_hour: int,
) -> tuple[list[InteractiveMarketSelectionItem], str | None, str | None]:
    market_players = _market_players_until_next_update(client, league_id, update_hour=update_hour)
    selection_header = None
    selection_title = None
    next_update = _next_market_update_local(update_hour=update_hour)
    if not market_players:
        market_players = get_market_players_for_next_day(client, league_id, update_hour=update_hour)
        if market_players:
            next_day = next_update.date() + timedelta(days=1)
            selection_header = (
                f"Keine Marktspieler laufen bis zum naechsten Marktwert-Update um {update_hour:02d}:00 aus. "
                f"Ich zeige dir stattdessen die Marktspieler vom Folgetag {next_day.strftime('%d.%m.%Y')}."
            )
            selection_title = f"Marktspieler mit Ablauf am {next_day.strftime('%d.%m.%Y')}:"
        else:
            market_players = _sorted_market_players(client.get_market_players(league_id))
            if not market_players:
                raise ValueError("Der Kickbase-Markt ist aktuell leer.")
            selection_header = (
                f"Keine Marktspieler laufen bis zum naechsten Marktwert-Update um {update_hour:02d}:00 aus und "
                "auch nicht am Folgetag. Ich zeige dir stattdessen alle aktuellen Marktspieler nach Ablauf sortiert."
            )
    return _build_interactive_selection_items(client, competition_id, market_players), selection_header, selection_title


def _market_players_until_next_update(
    client: KickbaseClient,
    league_id: str,
    *,
    update_hour: int,
) -> list[KickbaseMarketPlayer]:
    next_update = _next_market_update_local(update_hour=update_hour)
    players = []
    for player in client.get_market_players(league_id):
        expires_at = _parse_iso_timestamp(player.expires_at) if player.expires_at else None
        if expires_at is None:
            continue
        if expires_at.astimezone(_local_timezone()) <= next_update:
            players.append(player)

    return _sorted_market_players(players)


def get_market_players_for_next_day(
    client: KickbaseClient,
    league_id: str,
    *,
    update_hour: int,
) -> list[KickbaseMarketPlayer]:
    next_update = _next_market_update_local(update_hour=update_hour)
    target_day = next_update.date() + timedelta(days=1)
    players = []
    for player in client.get_market_players(league_id):
        expires_at = _parse_iso_timestamp(player.expires_at) if player.expires_at else None
        if expires_at is None:
            continue
        if expires_at.astimezone(_local_timezone()).date() == target_day:
            players.append(player)

    return _sorted_market_players(players)


def _sorted_market_players(players: list[KickbaseMarketPlayer]) -> list[KickbaseMarketPlayer]:
    def sort_key(item: KickbaseMarketPlayer) -> tuple[float, str]:
        expires_at = _parse_iso_timestamp(item.expires_at) if item.expires_at else None
        expires_timestamp = expires_at.timestamp() if expires_at is not None else float("inf")
        return (expires_timestamp, item.full_name.casefold())

    return sorted(players, key=sort_key)


def _next_market_update_local(*, update_hour: int, reference_time: datetime | None = None) -> datetime:
    now_local = (reference_time or datetime.now().astimezone()).astimezone(_local_timezone())
    candidate = now_local.replace(hour=update_hour, minute=0, second=0, microsecond=0)
    if now_local >= candidate:
        candidate += timedelta(days=1)
    return candidate


def _local_timezone() -> timezone:
    return datetime.now().astimezone().tzinfo or timezone.utc


def _format_local_expiry(value: str | None) -> str:
    expires_at = _parse_iso_timestamp(value) if value else None
    if expires_at is None:
        return "n/a"
    return expires_at.astimezone(_local_timezone()).strftime("%d.%m. %H:%M")


def _prompt_selection(max_index: int) -> list[int]:
    while True:
        raw_value = input("Welche Nummern willst du auswerten? (z.B. 1,3,5 oder 2-4) ").strip()
        try:
            selection = _parse_selection_input(raw_value, max_index)
        except ValueError as error:
            print(f"Bitte gueltig eingeben: {error}")
            continue
        return selection


def _parse_selection_input(raw_value: str, max_index: int) -> list[int]:
    normalized = raw_value.strip().casefold()
    if not normalized:
        raise ValueError("mindestens eine Nummer angeben")
    if normalized in {"alle", "all", "*"}:
        return list(range(1, max_index + 1))

    selections: list[int] = []
    seen: set[int] = set()
    for comma_part in normalized.replace(";", ",").split(","):
        for token in comma_part.split():
            if not token:
                continue
            if "-" in token:
                start_text, end_text = token.split("-", 1)
                if not start_text or not end_text:
                    raise ValueError("Bereiche bitte als start-ende angeben")
                try:
                    start = int(start_text)
                    end = int(end_text)
                except ValueError as error:
                    raise ValueError("Bereiche muessen nur Zahlen enthalten") from error
                step = 1 if end >= start else -1
                for item in range(start, end + step, step):
                    _append_selection_value(selections, seen, item, max_index)
                continue
            try:
                value = int(token)
            except ValueError as error:
                raise ValueError("nur Nummern, Kommas oder Bereiche wie 2-4 verwenden") from error
            _append_selection_value(selections, seen, value, max_index)

    if not selections:
        raise ValueError("mindestens eine Nummer angeben")
    return selections


def _append_selection_value(
    selections: list[int],
    seen: set[int],
    value: int,
    max_index: int,
) -> None:
    if value < 1 or value > max_index:
        raise ValueError(f"nur Nummern zwischen 1 und {max_index}")
    if value in seen:
        return
    seen.add(value)
    selections.append(value)


def _build_interactive_selection_items(
    client: KickbaseClient,
    competition_id: str,
    market_players: list[KickbaseMarketPlayer],
) -> list[InteractiveMarketSelectionItem]:
    items: list[InteractiveMarketSelectionItem] = []
    for player in market_players:
        items.append(
            InteractiveMarketSelectionItem(
                player=player,
                recent_market_value_changes=_load_recent_market_value_changes(
                    client,
                    competition_id=competition_id,
                    player_id=player.player_id,
                ),
            )
        )
    return items


def _load_recent_market_value_changes(
    client: KickbaseClient,
    *,
    competition_id: str,
    player_id: str,
) -> tuple[int | None, int | None, int | None]:
    try:
        history = client.get_player_market_value_history(
            competition_id,
            player_id,
            days=MIN_MARKET_VALUE_HISTORY_DAYS,
        )
    except KickbaseApiError:
        return (None, None, None)
    return _recent_market_value_changes_from_history(history)


def _recent_market_value_changes_from_history(
    history: list[KickbasePlayerMarketValue],
) -> tuple[int | None, int | None, int | None]:
    changes: list[int | None] = []
    for index in range(len(history) - 1, 0, -1):
        current_value = history[index].market_value
        previous_value = history[index - 1].market_value
        changes.append(current_value - previous_value)
        if len(changes) == 3:
            break
    while len(changes) < 3:
        changes.append(None)
    return (changes[0], changes[1], changes[2])


def _build_transfer_samples(
    client: KickbaseClient,
    *,
    competition_id: str,
    transfers: list[KickbaseManagerTransfer],
    market_value_history_days: int,
    player_metadata_by_id: dict[str, dict[str, Any]],
    reference_time: datetime,
) -> list[TransferGebotsSample]:
    history_cache: dict[str, list[KickbasePlayerMarketValue]] = {}
    samples: list[TransferGebotsSample] = []

    for transfer in transfers:
        if transfer.price is None or transfer.price <= 0:
            continue

        history = history_cache.get(transfer.player_id)
        if history is None:
            history = client.get_player_market_value_history(
                competition_id,
                transfer.player_id,
                days=market_value_history_days,
            )
            history_cache[transfer.player_id] = history
        if not history:
            continue

        history_index = _history_index_at_or_before(history, _parse_iso_date(transfer.date))
        if history_index is None:
            continue

        reference_market_value = history[history_index].market_value
        if reference_market_value <= 0:
            continue

        transfer_timestamp = _parse_iso_timestamp(transfer.date)
        if transfer_timestamp is None:
            continue

        trend = _trend_from_history(history, history_index)
        overpay = transfer.price - reference_market_value
        overpay_pct = (overpay / reference_market_value) * 100
        samples.append(
            TransferGebotsSample(
                manager_id=transfer.manager_id,
                manager_name=transfer.manager_name,
                player_id=transfer.player_id,
                player_name=transfer.player_name,
                transfer_date=transfer.date,
                winning_bid=transfer.price,
                reference_market_value=reference_market_value,
                overpay=overpay,
                overpay_pct=overpay_pct,
                position=_player_position_from_metadata(player_metadata_by_id, transfer.player_id),
                team_id=_player_team_id_from_metadata(player_metadata_by_id, transfer.player_id),
                price_class=_price_class_key_from_market_value(reference_market_value),
                recency_days=max(0.0, (reference_time - transfer_timestamp).total_seconds() / 86400),
                manager_aggression_pct=0.0,
                similarity_weight=1.0,
                weight_market_value=1.0,
                weight_recency=1.0,
                weight_trend=1.0,
                weight_position=1.0,
                weight_price_class=1.0,
                weight_team=1.0,
                weight_manager=1.0,
                trend=trend,
            )
        )

    return samples


def _history_index_at_or_before(
    history: list[KickbasePlayerMarketValue],
    target_day: date | None,
) -> int | None:
    history_index = None
    for index, item in enumerate(history):
        history_day = _parse_iso_date(item.date)
        if history_day is None:
            continue
        if target_day is None or history_day <= target_day:
            history_index = index
            continue
        break
    return history_index


def _trend_from_history(history: list[KickbasePlayerMarketValue], history_index: int) -> MarktwertTrend:
    current_value = history[history_index].market_value
    one_day_slope = _daily_log_return(history, history_index, lookback_steps=1)
    three_day_slope = _daily_log_return(history, history_index, lookback_steps=3)
    seven_day_slope = _daily_log_return(history, history_index, lookback_steps=7)
    acceleration_pct = None
    if one_day_slope is not None and three_day_slope is not None:
        acceleration_pct = one_day_slope - three_day_slope

    lookback_start = max(0, history_index - 13)
    recent_window = history[lookback_start : history_index + 1]
    recent_values = [item.market_value for item in recent_window if item.market_value > 0]
    distance_to_14d_high_pct = None
    distance_to_14d_low_pct = None
    range_position_bonus = 0.0
    if recent_values:
        recent_high = max(recent_values)
        recent_low = min(recent_values)
        distance_to_14d_high_pct = 100 * ((current_value / recent_high) - 1) if recent_high > 0 else None
        distance_to_14d_low_pct = 100 * ((current_value / recent_low) - 1) if recent_low > 0 else None
        if recent_high > recent_low:
            normalized_position = (current_value - recent_low) / (recent_high - recent_low)
            range_position_bonus = 0.4 * (normalized_position - 0.5)

    weighted_sum = 0.0
    weight_total = 0.0
    if one_day_slope is not None:
        weighted_sum += 0.55 * one_day_slope
        weight_total += 0.55
    if three_day_slope is not None:
        weighted_sum += 0.30 * three_day_slope
        weight_total += 0.30
    if seven_day_slope is not None:
        weighted_sum += 0.15 * seven_day_slope
        weight_total += 0.15

    base_trend = weighted_sum / weight_total if weight_total else 0.0
    momentum_score = base_trend + (0.25 * (acceleration_pct or 0.0)) + range_position_bonus
    return MarktwertTrend(
        market_value=current_value,
        one_day_log_slope_pct=one_day_slope,
        three_day_log_slope_pct=three_day_slope,
        seven_day_log_slope_pct=seven_day_slope,
        acceleration_pct=acceleration_pct,
        distance_to_14d_high_pct=distance_to_14d_high_pct,
        distance_to_14d_low_pct=distance_to_14d_low_pct,
        momentum_score=momentum_score,
    )


def _daily_log_return(
    history: list[KickbasePlayerMarketValue],
    current_index: int,
    *,
    lookback_steps: int,
) -> float | None:
    previous_index = current_index - lookback_steps
    if previous_index < 0:
        return None

    current_value = history[current_index].market_value
    previous_value = history[previous_index].market_value
    if current_value <= 0 or previous_value <= 0:
        return None
    return 100 * math.log(current_value / previous_value) / lookback_steps


def _prepare_weighted_samples(
    samples: list[TransferGebotsSample],
    *,
    target_market_value: int,
    target_trend: MarktwertTrend,
    target_position: int | None,
    target_team_id: str | None,
    target_price_class: str,
    value_tolerance: float,
    manager_profiles_by_id: dict[str, ManagerAggressionProfile],
    min_samples: int,
) -> tuple[list[TransferGebotsSample], str, int]:
    lower_bound = max(0, math.floor(target_market_value * (1 - value_tolerance)))
    upper_bound = math.ceil(target_market_value * (1 + value_tolerance))
    primary_sample_count = 0
    aggression_values = [profile.aggression_score_pct for profile in manager_profiles_by_id.values()]
    aggression_weights = [max(1.0, float(profile.transfer_count)) for profile in manager_profiles_by_id.values()]
    aggression_center = _weighted_quantile(aggression_values, aggression_weights, 0.5) if aggression_values else 0.0
    aggression_p25 = _weighted_quantile(aggression_values, aggression_weights, 0.25) if aggression_values else 0.0
    aggression_p75 = _weighted_quantile(aggression_values, aggression_weights, 0.75) if aggression_values else 1.0
    aggression_scale = max(1.0, aggression_p75 - aggression_p25)

    weighted_samples: list[TransferGebotsSample] = []
    for sample in samples:
        if lower_bound <= sample.reference_market_value <= upper_bound:
            primary_sample_count += 1

        weight_market_value = math.exp(
            -abs(math.log(max(sample.reference_market_value, 1) / max(target_market_value, 1)))
            / MARKET_VALUE_DISTANCE_SCALE
        )
        weight_recency = 1.0
        trend_distance = abs(sample.trend.momentum_score - target_trend.momentum_score)
        acceleration_distance = abs(
            (sample.trend.acceleration_pct or 0.0) - (target_trend.acceleration_pct or 0.0)
        )
        weight_trend = math.exp(
            -(trend_distance / TREND_DISTANCE_SCALE) - (acceleration_distance / ACCELERATION_DISTANCE_SCALE)
        )
        weight_position = 1.0
        if target_position is not None and sample.position is not None and sample.position != target_position:
            weight_position = POSITION_MISMATCH_WEIGHT
        weight_price_class = _price_class_similarity_weight(target_price_class, sample.price_class)
        weight_team = _team_similarity_weight(target_team_id, sample.team_id)

        profile = manager_profiles_by_id.get(sample.manager_id)
        manager_aggression_pct = profile.aggression_score_pct if profile is not None else sample.overpay_pct
        aggression_z = (manager_aggression_pct - aggression_center) / aggression_scale
        weight_manager = math.exp(MANAGER_WEIGHT_FACTOR * _clip(aggression_z, -2.0, 2.0))

        similarity_weight = max(
            1e-6,
            weight_market_value
            * weight_recency
            * weight_trend
            * weight_position
            * weight_price_class
            * weight_team
            * weight_manager,
        )
        weighted_samples.append(
            TransferGebotsSample(
                manager_id=sample.manager_id,
                manager_name=sample.manager_name,
                player_id=sample.player_id,
                player_name=sample.player_name,
                transfer_date=sample.transfer_date,
                winning_bid=sample.winning_bid,
                reference_market_value=sample.reference_market_value,
                overpay=sample.overpay,
                overpay_pct=sample.overpay_pct,
                position=sample.position,
                team_id=sample.team_id,
                price_class=sample.price_class,
                recency_days=sample.recency_days,
                manager_aggression_pct=manager_aggression_pct,
                similarity_weight=similarity_weight,
                weight_market_value=weight_market_value,
                weight_recency=weight_recency,
                weight_trend=weight_trend,
                weight_position=weight_position,
                weight_price_class=weight_price_class,
                weight_team=weight_team,
                weight_manager=weight_manager,
                trend=sample.trend,
            )
        )

    weighted_samples.sort(key=lambda item: item.similarity_weight, reverse=True)
    if primary_sample_count >= min_samples:
        return weighted_samples, "weighted_kernel", primary_sample_count
    return weighted_samples, "weighted_kernel_broad", primary_sample_count


def _build_manager_profiles(
    samples: list[TransferGebotsSample],
) -> dict[str, ManagerAggressionProfile]:
    grouped: dict[str, list[TransferGebotsSample]] = {}
    for sample in samples:
        grouped.setdefault(sample.manager_id, []).append(sample)

    profiles: dict[str, ManagerAggressionProfile] = {}
    for manager_id, manager_samples in grouped.items():
        weights = [1.0 for _ in manager_samples]
        overpays = [sample.overpay_pct for sample in manager_samples]
        mean_overpay_pct = _weighted_average(overpays, weights)
        p80_overpay_pct = _weighted_quantile(overpays, weights, 0.8)
        aggression_score_pct = (0.35 * mean_overpay_pct) + (0.65 * p80_overpay_pct)
        profiles[manager_id] = ManagerAggressionProfile(
            manager_id=manager_id,
            manager_name=manager_samples[0].manager_name,
            transfer_count=len(manager_samples),
            mean_overpay_pct=mean_overpay_pct,
            p80_overpay_pct=p80_overpay_pct,
            aggression_score_pct=aggression_score_pct,
        )

    return profiles


def _build_calibration_summary(
    client: KickbaseClient,
    *,
    league_id: str,
    reference_time: datetime,
    minimum_days: int,
    cached_summary: CalibrationSummary | None = None,
    target_position: int | None = None,
    target_team_id: str | None = None,
    target_price_class: str | None = None,
    player_metadata_by_id: dict[str, dict[str, Any]] | None = None,
    cached_cases: tuple[CalibrationCase, ...] | None = None,
) -> CalibrationSummary:
    if (
        cached_summary is not None
        and cached_cases is None
        and target_position is None
        and target_team_id is None
        and target_price_class is None
    ):
        return cached_summary

    calibration_cases = list(cached_cases or ())
    if not calibration_cases:
        calibration_cases = list(
            _build_calibration_cases(
                client,
                league_id=league_id,
                reference_time=reference_time,
                minimum_days=minimum_days,
                player_metadata_by_id=player_metadata_by_id or {},
            )
        )

    return _summarize_calibration_cases(
        calibration_cases,
        target_position=target_position,
        target_team_id=target_team_id,
        target_price_class=target_price_class,
    )


def _build_calibration_cases(
    client: KickbaseClient,
    *,
    league_id: str,
    reference_time: datetime,
    minimum_days: int,
    player_metadata_by_id: dict[str, dict[str, Any]],
) -> tuple[CalibrationCase, ...]:
    logs = _load_forecast_logs(league_id)
    if not logs:
        return ()

    completed_logs = _completed_forecast_logs(logs, reference_time=reference_time)
    if not completed_logs:
        return ()

    created_timestamps = [
        created_at
        for log in completed_logs
        if (created_at := _parse_iso_timestamp(str(log.get("created_at") or ""))) is not None
    ]
    if not created_timestamps:
        return ()

    oldest_created_at = min(created_timestamps)
    calibration_days = min(
        MAX_CALIBRATION_WINDOW_DAYS,
        max(
            minimum_days,
            int(math.ceil((reference_time - oldest_created_at).total_seconds() / 86400)) + 7,
        ),
    )
    transfers = collect_recent_buy_transfers(
        client,
        league_id,
        days=max(minimum_days, calibration_days),
        max_pages_per_manager=DEFAULT_MAX_PAGES_PER_MANAGER,
    )
    matched_logs = _match_forecast_logs_to_transfers(completed_logs, transfers)
    if not matched_logs:
        return ()

    calibration_cases: list[CalibrationCase] = []
    for log_entry, transfer in matched_logs:
        if transfer.price is None:
            continue
        player_id = str(log_entry.get("player_id") or "").strip()
        reference_market_value = max(1, int(log_entry.get("bid_reference_market_value") or 1))
        safe_bid = int(log_entry.get("safe_bid") or 0)
        gamble_bid = int(log_entry.get("gamble_bid") or 0)
        position = _log_position(log_entry)
        if position is None:
            position = _player_position_from_metadata(player_metadata_by_id, player_id)
        team_id = str(log_entry.get("current_team_id") or "").strip() or None
        if team_id is None:
            team_id = _player_team_id_from_metadata(player_metadata_by_id, player_id)
        price_class = str(log_entry.get("price_class") or "").strip() or _price_class_key_from_market_value(
            reference_market_value
        )
        calibration_cases.append(
            CalibrationCase(
                player_id=player_id,
                position=position,
                team_id=team_id,
                price_class=price_class,
                safe_hit=1.0 if safe_bid >= transfer.price else 0.0,
                gamble_hit=1.0 if gamble_bid >= transfer.price else 0.0,
                safe_delta_pct=100 * ((transfer.price - safe_bid) / reference_market_value),
                gamble_delta_pct=100 * ((transfer.price - gamble_bid) / reference_market_value),
            )
        )

    return tuple(calibration_cases)


def _summarize_calibration_cases(
    calibration_cases: list[CalibrationCase],
    *,
    target_position: int | None = None,
    target_team_id: str | None = None,
    target_price_class: str | None = None,
) -> CalibrationSummary:
    global_stats = _calibration_stats(calibration_cases)
    if global_stats[0] == 0:
        return CalibrationSummary(0, None, None, 0.0, 0.0)

    position_cases = [case for case in calibration_cases if target_position is not None and case.position == target_position]
    price_class_cases = [
        case for case in calibration_cases if target_price_class is not None and case.price_class == target_price_class
    ]
    team_cases = [case for case in calibration_cases if target_team_id is not None and case.team_id == target_team_id]

    safe_hit_values = [global_stats[1]] if global_stats[1] is not None else []
    gamble_hit_values = [global_stats[2]] if global_stats[2] is not None else []
    adjustment_safe_values = [global_stats[3]]
    adjustment_gamble_values = [global_stats[4]]
    hit_weights = [1.0] if safe_hit_values else []
    adjustment_weights = [1.0]

    for cases, blend_weight, full_count in (
        (position_cases, POSITION_CALIBRATION_BLEND, POSITION_CALIBRATION_FULL_COUNT),
        (price_class_cases, PRICE_CLASS_CALIBRATION_BLEND, PRICE_CLASS_CALIBRATION_FULL_COUNT),
        (team_cases, TEAM_CALIBRATION_BLEND, TEAM_CALIBRATION_FULL_COUNT),
    ):
        subset_stats = _calibration_stats(cases)
        subset_count = subset_stats[0]
        if subset_count == 0:
            continue
        subset_weight = blend_weight * _segment_reliability(subset_count, full_count)
        adjustment_safe_values.append(subset_stats[3])
        adjustment_gamble_values.append(subset_stats[4])
        adjustment_weights.append(subset_weight)
        if subset_stats[1] is not None and subset_stats[2] is not None:
            safe_hit_values.append(subset_stats[1])
            gamble_hit_values.append(subset_stats[2])
            hit_weights.append(subset_weight)

    completed_sample_count = global_stats[0]
    safe_hit_rate = _weighted_average(safe_hit_values, hit_weights) if safe_hit_values and hit_weights else None
    gamble_hit_rate = _weighted_average(gamble_hit_values, hit_weights) if gamble_hit_values and hit_weights else None
    if completed_sample_count < 5:
        return CalibrationSummary(
            completed_sample_count=completed_sample_count,
            safe_hit_rate=safe_hit_rate,
            gamble_hit_rate=gamble_hit_rate,
            safe_adjustment_pct=0.0,
            gamble_adjustment_pct=0.0,
            position_sample_count=len(position_cases),
            price_class_sample_count=len(price_class_cases),
            team_sample_count=len(team_cases),
        )

    safe_adjustment_pct = _clip(_weighted_average(adjustment_safe_values, adjustment_weights), -1.5, 2.5)
    gamble_adjustment_pct = _clip(_weighted_average(adjustment_gamble_values, adjustment_weights), -1.0, 2.0)
    return CalibrationSummary(
        completed_sample_count=completed_sample_count,
        safe_hit_rate=safe_hit_rate,
        gamble_hit_rate=gamble_hit_rate,
        safe_adjustment_pct=safe_adjustment_pct,
        gamble_adjustment_pct=gamble_adjustment_pct,
        position_sample_count=len(position_cases),
        price_class_sample_count=len(price_class_cases),
        team_sample_count=len(team_cases),
    )


def _calibration_stats(cases: list[CalibrationCase]) -> tuple[int, float | None, float | None, float, float]:
    if not cases:
        return 0, None, None, 0.0, 0.0
    weights = [1.0 for _ in cases]
    safe_hits = [case.safe_hit for case in cases]
    gamble_hits = [case.gamble_hit for case in cases]
    safe_deltas = [case.safe_delta_pct for case in cases]
    gamble_deltas = [case.gamble_delta_pct for case in cases]
    return (
        len(cases),
        _weighted_average(safe_hits, weights),
        _weighted_average(gamble_hits, weights),
        _clip(_weighted_average(safe_deltas, weights), -1.5, 2.5),
        _clip(_weighted_average(gamble_deltas, weights), -1.0, 2.0),
    )


def _segment_reliability(sample_count: int, full_count: int) -> float:
    if sample_count <= 0 or full_count <= 0:
        return 0.0
    return _clip(sample_count / full_count, 0.0, 1.0)

    logs = _load_forecast_logs(league_id)
    if not logs:
        return CalibrationSummary(0, None, None, 0.0, 0.0)

    completed_logs = _completed_forecast_logs(logs, reference_time=reference_time)
    if not completed_logs:
        return CalibrationSummary(0, None, None, 0.0, 0.0)

    created_timestamps = [
        created_at
        for log in completed_logs
        if (created_at := _parse_iso_timestamp(str(log.get("created_at") or ""))) is not None
    ]
    if not created_timestamps:
        return CalibrationSummary(0, None, None, 0.0, 0.0)

    oldest_created_at = min(created_timestamps)
    calibration_days = min(
        MAX_CALIBRATION_WINDOW_DAYS,
        max(
            minimum_days,
            int(math.ceil((reference_time - oldest_created_at).total_seconds() / 86400)) + 7,
        ),
    )
    transfers = collect_recent_buy_transfers(
        client,
        league_id,
        days=max(minimum_days, calibration_days),
        max_pages_per_manager=DEFAULT_MAX_PAGES_PER_MANAGER,
    )
    matched_logs = _match_forecast_logs_to_transfers(completed_logs, transfers)
    if not matched_logs:
        return CalibrationSummary(0, None, None, 0.0, 0.0)

    weights: list[float] = []
    safe_hits: list[float] = []
    gamble_hits: list[float] = []
    safe_deltas: list[float] = []
    gamble_deltas: list[float] = []
    for log_entry, transfer in matched_logs:
        transfer_timestamp = _parse_iso_timestamp(transfer.date)
        if transfer_timestamp is None or transfer.price is None:
            continue
        weight = 1.0
        reference_market_value = max(1, int(log_entry.get("bid_reference_market_value") or 1))
        safe_bid = int(log_entry.get("safe_bid") or 0)
        gamble_bid = int(log_entry.get("gamble_bid") or 0)
        weights.append(weight)
        safe_hits.append(1.0 if safe_bid >= transfer.price else 0.0)
        gamble_hits.append(1.0 if gamble_bid >= transfer.price else 0.0)
        safe_deltas.append(100 * ((transfer.price - safe_bid) / reference_market_value))
        gamble_deltas.append(100 * ((transfer.price - gamble_bid) / reference_market_value))

    completed_sample_count = len(weights)
    if completed_sample_count == 0:
        return CalibrationSummary(0, None, None, 0.0, 0.0)

    safe_hit_rate = _weighted_average(safe_hits, weights)
    gamble_hit_rate = _weighted_average(gamble_hits, weights)
    if completed_sample_count < 5:
        return CalibrationSummary(completed_sample_count, safe_hit_rate, gamble_hit_rate, 0.0, 0.0)

    safe_adjustment_pct = _clip(_weighted_average(safe_deltas, weights), -1.5, 2.5)
    gamble_adjustment_pct = _clip(_weighted_average(gamble_deltas, weights), -1.0, 2.0)
    return CalibrationSummary(
        completed_sample_count=completed_sample_count,
        safe_hit_rate=safe_hit_rate,
        gamble_hit_rate=gamble_hit_rate,
        safe_adjustment_pct=safe_adjustment_pct,
        gamble_adjustment_pct=gamble_adjustment_pct,
    )


def _load_forecast_logs(league_id: str) -> list[dict[str, Any]]:
    if not FORECAST_LOG_PATH.exists():
        return []

    logs: list[dict[str, Any]] = []
    for line in FORECAST_LOG_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except ValueError:
            continue
        if not isinstance(payload, dict):
            continue
        if str(payload.get("league_id") or "") != str(league_id):
            continue
        logs.append(payload)
    return logs


def _completed_forecast_logs(
    logs: list[dict[str, Any]],
    *,
    reference_time: datetime,
) -> list[dict[str, Any]]:
    latest_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for log_entry in logs:
        created_at = _parse_iso_timestamp(str(log_entry.get("created_at") or ""))
        expires_at = _parse_iso_timestamp(str(log_entry.get("expires_at") or ""))
        if created_at is None or expires_at is None or expires_at >= reference_time:
            continue
        player_id = str(log_entry.get("player_id") or "").strip()
        if not player_id:
            continue
        dedupe_key = (player_id, expires_at.isoformat())
        current = latest_by_key.get(dedupe_key)
        if current is None or str(current.get("created_at") or "") < str(log_entry.get("created_at") or ""):
            latest_by_key[dedupe_key] = log_entry
    return [latest_by_key[key] for key in sorted(latest_by_key)]


def _match_forecast_logs_to_transfers(
    logs: list[dict[str, Any]],
    transfers: list[KickbaseManagerTransfer],
) -> list[tuple[dict[str, Any], KickbaseManagerTransfer]]:
    transfers_by_player: dict[str, list[KickbaseManagerTransfer]] = {}
    for transfer in transfers:
        transfers_by_player.setdefault(transfer.player_id, []).append(transfer)

    latest_match_by_transfer: dict[tuple[str, str, int], tuple[datetime, dict[str, Any], KickbaseManagerTransfer]] = {}
    for log_entry in logs:
        player_id = str(log_entry.get("player_id") or "").strip()
        created_at = _parse_iso_timestamp(str(log_entry.get("created_at") or ""))
        expires_at = _parse_iso_timestamp(str(log_entry.get("expires_at") or ""))
        if not player_id or created_at is None:
            continue
        match_window_end = (expires_at or created_at) + timedelta(days=7)
        candidates = []
        for transfer in transfers_by_player.get(player_id, []):
            transfer_timestamp = _parse_iso_timestamp(transfer.date)
            if transfer_timestamp is None:
                continue
            if created_at <= transfer_timestamp <= match_window_end:
                candidates.append((transfer_timestamp, transfer))
        if not candidates:
            continue
        candidates.sort(key=lambda item: item[0])
        matched_transfer = candidates[0][1]
        transfer_key = (
            player_id,
            str(matched_transfer.date or ""),
            int(matched_transfer.price or 0),
        )
        current = latest_match_by_transfer.get(transfer_key)
        if current is None or current[0] < created_at:
            latest_match_by_transfer[transfer_key] = (created_at, log_entry, matched_transfer)

    return [
        (log_entry, transfer)
        for _, log_entry, transfer in sorted(
            latest_match_by_transfer.values(),
            key=lambda item: (
                _parse_iso_timestamp(item[2].date) or datetime.min.replace(tzinfo=timezone.utc),
                str(item[1].get("player_name") or "").casefold(),
            ),
        )
    ]


def _append_forecast_log(forecast: GebotsVorhersage, *, league_name: str) -> None:
    FORECAST_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "forecast_version": FORECAST_VERSION,
        "created_at": forecast.target_context.captured_at,
        "league_id": forecast.league_id,
        "league_name": league_name,
        "player_id": forecast.player_id,
        "player_name": forecast.player_name,
        "expires_at": forecast.target_context.expires_at,
        "market_value": forecast.market_value,
        "projected_market_value_at_expiry": forecast.projected_market_value_at_expiry,
        "bid_reference_market_value": forecast.bid_reference_market_value,
        "list_price": forecast.list_price,
        "bid_floor": forecast.bid_floor,
        "current_position": forecast.target_context.current_position,
        "current_team_id": forecast.target_context.current_team_id,
        "current_team_name": forecast.target_context.current_team_name,
        "price_class": forecast.target_context.price_class,
        "gamble_bid": forecast.gamble_bid,
        "safe_bid": forecast.safe_bid,
        "gamble_overpay_pct": forecast.gamble_overpay_pct,
        "safe_overpay_pct": forecast.safe_overpay_pct,
        "sample_count": forecast.sample_count,
        "selection_mode": forecast.selection_mode,
    }
    with FORECAST_LOG_PATH.open("a", encoding="utf-8") as file_handle:
        file_handle.write(json.dumps(payload, ensure_ascii=True) + "\n")


def _load_competition_player_metadata(
    client: KickbaseClient,
    competition_id: str,
) -> dict[str, dict[str, Any]]:
    try:
        competition_players = client.get_competition_players(competition_id)
    except KickbaseApiError:
        return {}
    return {
        player.player_id: {
            "position": player.position,
            "team_id": player.team_id,
            "team_name": player.team_name,
            "display_name": player.display_name,
        }
        for player in competition_players
    }


def _player_position_from_metadata(
    player_metadata_by_id: dict[str, dict[str, Any]],
    player_id: str,
) -> int | None:
    metadata = player_metadata_by_id.get(player_id)
    if not metadata:
        return None
    raw_position = metadata.get("position")
    return int(raw_position) if isinstance(raw_position, int) else None


def _player_team_id_from_metadata(
    player_metadata_by_id: dict[str, dict[str, Any]],
    player_id: str,
) -> str | None:
    metadata = player_metadata_by_id.get(player_id)
    if not metadata:
        return None
    raw_team_id = metadata.get("team_id")
    if not raw_team_id:
        return None
    return str(raw_team_id).strip() or None


def _player_team_name_from_metadata(
    player_metadata_by_id: dict[str, dict[str, Any]],
    player_id: str,
) -> str | None:
    metadata = player_metadata_by_id.get(player_id)
    if not metadata:
        return None
    raw_team_name = metadata.get("team_name")
    if not raw_team_name:
        return None
    return str(raw_team_name).strip() or None


def _log_position(log_entry: dict[str, Any]) -> int | None:
    raw_position = log_entry.get("current_position")
    return int(raw_position) if isinstance(raw_position, int) else None


def _price_class_key_from_market_value(market_value: int) -> str:
    if market_value < 1_000_000:
        return "under_1m"
    if market_value < 5_000_000:
        return "1m_to_5m"
    if market_value < 10_000_000:
        return "5m_to_10m"
    if market_value < 20_000_000:
        return "10m_to_20m"
    return "20m_plus"


def _price_class_label(price_class: str) -> str:
    labels = {
        "under_1m": "<1 Mio",
        "1m_to_5m": "1-5 Mio",
        "5m_to_10m": "5-10 Mio",
        "10m_to_20m": "10-20 Mio",
        "20m_plus": ">=20 Mio",
    }
    return labels.get(price_class, price_class)


def _price_class_rank(price_class: str) -> int:
    ranks = {
        "under_1m": 0,
        "1m_to_5m": 1,
        "5m_to_10m": 2,
        "10m_to_20m": 3,
        "20m_plus": 4,
    }
    return ranks.get(price_class, 99)


def _price_class_similarity_weight(target_price_class: str, sample_price_class: str) -> float:
    distance = abs(_price_class_rank(target_price_class) - _price_class_rank(sample_price_class))
    if distance == 0:
        return PRICE_CLASS_MATCH_WEIGHT
    if distance == 1:
        return PRICE_CLASS_NEAR_WEIGHT
    return PRICE_CLASS_FAR_WEIGHT


def _team_similarity_weight(target_team_id: str | None, sample_team_id: str | None) -> float:
    if target_team_id and sample_team_id and target_team_id == sample_team_id:
        return SAME_TEAM_WEIGHT
    return 1.0


def _hours_to_expiry(expires_at: datetime | None, *, reference_time: datetime) -> float | None:
    if expires_at is None:
        return None
    return max(0.0, (expires_at - reference_time).total_seconds() / 3600)


def _project_market_value_at_expiry(
    current_market_value: int,
    momentum_score_pct: float,
    hours_to_expiry: float | None,
) -> int:
    if current_market_value <= 0:
        return current_market_value
    if hours_to_expiry is None:
        return current_market_value
    projected_days = max(0.0, hours_to_expiry / 24.0)
    projected_value = current_market_value * math.exp((momentum_score_pct / 100) * projected_days)
    return max(1, math.ceil(projected_value))


def _list_price_delta_pct(list_price: int | None, projected_market_value: int) -> float | None:
    if list_price is None or projected_market_value <= 0:
        return None
    return 100 * ((list_price / projected_market_value) - 1)


def _build_sample_warning(
    *,
    total_samples: int,
    primary_sample_count: int,
    selected_sample_count: int,
    min_samples: int,
    selection_mode: str,
    calibration: CalibrationSummary,
    bid_floor: int,
    lowest_model_bid: int,
) -> str | None:
    warnings: list[str] = []
    if selected_sample_count < min_samples:
        warnings.append(
            f"Nur {selected_sample_count} Kauf-Samples verfuegbar; die Prognose basiert auf einem duennen Fenster."
        )
    elif primary_sample_count < min_samples:
        warnings.append(
            f"Nur {primary_sample_count} Samples lagen direkt im Preisband; das Modell gewichtet deshalb breiter ({selection_mode})."
        )
    if calibration.completed_sample_count < 5:
        warnings.append("Die automatische Kalibrierung ist noch duenn und wird erst ab 5 abgeschlossenen Logs aktiv.")
    if bid_floor > lowest_model_bid:
        warnings.append("Der Listenpreis setzt aktuell die operative Untergrenze fuer das Gebot.")
    if total_samples < min_samples:
        warnings.append(f"Im Lookback-Fenster lagen insgesamt nur {total_samples} Kauf-Samples.")
    if not warnings:
        return None
    return " ".join(warnings)


def _sample_key(sample: TransferGebotsSample) -> tuple[str, str, str, int]:
    return (
        sample.manager_id,
        sample.player_id,
        sample.transfer_date,
        sample.winning_bid,
    )


def _weighted_average(values: list[float], weights: list[float]) -> float:
    if not values or not weights or len(values) != len(weights):
        raise ValueError("Values and weights must have the same non-zero length.")
    total_weight = sum(max(0.0, weight) for weight in weights)
    if total_weight <= 0:
        return sum(values) / len(values)
    return sum(value * max(0.0, weight) for value, weight in zip(values, weights)) / total_weight


def _weighted_quantile(values: list[float], weights: list[float], percentile: float) -> float:
    if not values or not weights or len(values) != len(weights):
        raise ValueError("Values and weights must have the same non-zero length.")
    _validate_percentile("percentile", percentile)
    ordered = sorted(zip(values, weights), key=lambda item: item[0])
    if percentile <= 0:
        return ordered[0][0]
    if percentile >= 1:
        return ordered[-1][0]

    total_weight = sum(max(0.0, weight) for _, weight in ordered)
    if total_weight <= 0:
        rank = max(1, math.ceil(percentile * len(ordered)))
        return ordered[rank - 1][0]

    threshold = percentile * total_weight
    cumulative_weight = 0.0
    for value, weight in ordered:
        cumulative_weight += max(0.0, weight)
        if cumulative_weight >= threshold:
            return value
    return ordered[-1][0]


def _apply_overpay(market_value: int, overpay_pct: float) -> int:
    return math.ceil(market_value * (1 + (overpay_pct / 100)))


def _validate_percentile(name: str, percentile: float) -> None:
    if percentile < 0 or percentile > 1:
        raise ValueError(f"{name} must be between 0 and 1.")


def _parse_iso_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _parse_iso_date(value: str | None) -> date | None:
    timestamp = _parse_iso_timestamp(value)
    return None if timestamp is None else timestamp.date()


def _round_or_none(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 4)


def _format_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:+.2f}%"


def _format_ratio_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%"


def _format_optional_number(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def _format_position_label(position: int | None) -> str:
    labels = {
        1: "Tor",
        2: "Abwehr",
        3: "Mittelfeld",
        4: "Sturm",
    }
    return labels.get(position, str(position) if position is not None else "n/a")


def _format_money(value: int) -> str:
    return f"{int(value):,}".replace(",", ".")


def _format_money_optional(value: int | None) -> str:
    if value is None:
        return "n/a"
    return _format_money(value)


def _format_signed_money(value: int | None) -> str:
    if value is None:
        return "n/a"
    prefix = "+" if value >= 0 else "-"
    return f"{prefix}{_format_money(abs(value))}"


def _format_market_value_change_series(changes: tuple[int | None, int | None, int | None]) -> str:
    labels = ("1T", "2T", "3T")
    return " | ".join(
        f"{label} {_format_signed_money(change)}"
        for label, change in zip(labels, changes)
    )


def _format_percentile_label(percentile: float) -> str:
    return f"{percentile * 100:.0f}. Perzentil"


def _describe_trend_label(trend: MarktwertTrend) -> str:
    momentum = trend.momentum_score
    if momentum >= 1.5:
        return f"heiss steigend ({momentum:+.2f}%)"
    if momentum >= 0.4:
        return f"steigend ({momentum:+.2f}%)"
    if momentum <= -1.5:
        return f"stark fallend ({momentum:+.2f}%)"
    if momentum <= -0.4:
        return f"fallend ({momentum:+.2f}%)"
    return f"relativ neutral ({momentum:+.2f}%)"


def _clip(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


if __name__ == "__main__":
    raise SystemExit(main())