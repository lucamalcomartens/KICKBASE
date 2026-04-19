from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

import requests

from kickbase_api.errors import KickbaseApiError, KickbaseConfigurationError


KICKBASE_BASE_URL = "https://api.kickbase.com/v4"
UNIX_EPOCH = date(1970, 1, 1)
MIN_MARKET_VALUE_WINDOW_DAYS = 92
MAX_MARKET_VALUE_WINDOW_DAYS = 365
TRANSFER_TYPES = {
    1: "buy",
    2: "sell",
}


@dataclass(frozen=True, slots=True)
class KickbaseLeague:
    id: str
    name: str
    competition_id: str | None = None


@dataclass(frozen=True, slots=True)
class KickbaseTeam:
    id: str
    name: str
    current_place: int | None = None
    previous_place: int | None = None
    points: int | None = None
    matches: int | None = None
    goal_difference: int | None = None
    badge_path: str | None = None
    raw: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class KickbaseCompetitionMatch:
    match_id: str
    season: str
    matchday: int
    date: str
    home_team_id: str | None
    away_team_id: str | None
    home_team_short_name: str | None
    away_team_short_name: str | None
    home_team_badge_path: str | None
    away_team_badge_path: str | None
    home_goals: int | None
    away_goals: int | None
    match_status: int | None
    is_live: bool | None
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class KickbaseCompetitionPlayer:
    player_id: str
    display_name: str
    first_name: str | None
    last_name: str | None
    team_id: str | None
    team_name: str | None
    position: int | None
    market_value: int | None
    average_points: int | None
    market_value_day_change: int | None
    market_value_total_change: int | None
    raw: dict[str, Any]

    def to_dict(self, *, include_raw: bool = False) -> dict[str, Any]:
        payload = {
            "player_id": self.player_id,
            "display_name": self.display_name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "team_id": self.team_id,
            "team_name": self.team_name,
            "position": self.position,
            "market_value": self.market_value,
            "average_points": self.average_points,
            "market_value_day_change": self.market_value_day_change,
            "market_value_total_change": self.market_value_total_change,
        }
        if include_raw:
            payload["raw"] = self.raw
        return payload


@dataclass(frozen=True, slots=True)
class KickbaseCompetitionPlayerDetail:
    player_id: str
    display_name: str
    first_name: str | None
    last_name: str | None
    shirt_number: int | None
    team_id: str | None
    team_name: str | None
    position: int | None
    market_value: int | None
    average_points: int | None
    total_points: int | None
    goals: int | None
    yellow_cards: int | None
    red_cards: int | None
    market_value_day_change: int | None
    projected_starting_lineup: bool | None
    provider_name: str | None
    provider_updated_at: str | None
    provider_status_raw: int | None
    status: int | None
    status_text: str | None
    status_list: list[Any]
    raw: dict[str, Any]

    def to_dict(self, *, include_raw: bool = False) -> dict[str, Any]:
        payload = {
            "player_id": self.player_id,
            "display_name": self.display_name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "shirt_number": self.shirt_number,
            "team_id": self.team_id,
            "team_name": self.team_name,
            "position": self.position,
            "market_value": self.market_value,
            "average_points": self.average_points,
            "total_points": self.total_points,
            "goals": self.goals,
            "yellow_cards": self.yellow_cards,
            "red_cards": self.red_cards,
            "market_value_day_change": self.market_value_day_change,
            "projected_starting_lineup": self.projected_starting_lineup,
            "provider_name": self.provider_name,
            "provider_updated_at": self.provider_updated_at,
            "provider_status_raw": self.provider_status_raw,
            "status": self.status,
            "status_text": self.status_text,
            "status_list": list(self.status_list),
        }
        if include_raw:
            payload["raw"] = self.raw
        return payload


@dataclass(frozen=True, slots=True)
class KickbasePlayerMarketValue:
    player_id: str
    date: str
    market_value: int


@dataclass(frozen=True, slots=True)
class KickbaseMatchdayStat:
    player_id: str
    match_id: str
    season: str
    matchday: int
    date: str
    points: int | None
    minutes: int | None
    average_points: int | None
    total_points: int | None
    appearance_status: int | None
    matchday_status: int | None
    is_current: bool | None
    player_team_id: str | None
    home_team_id: str | None
    away_team_id: str | None
    home_goals: int | None
    away_goals: int | None
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class KickbaseMarketPlayer:
    player_id: str
    first_name: str | None
    last_name: str | None
    team_id: str | None
    position: int | None
    market_value: int | None
    list_price: int | None
    expires_in_seconds: int | None
    expires_at: str | None
    raw: dict[str, Any]

    @property
    def full_name(self) -> str:
        full_name = " ".join(part for part in [self.first_name, self.last_name] if part)
        return full_name or self.player_id

    def to_dict(self, *, include_raw: bool = False) -> dict[str, Any]:
        payload = {
            "player_id": self.player_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "team_id": self.team_id,
            "position": self.position,
            "market_value": self.market_value,
            "list_price": self.list_price,
            "expires_in_seconds": self.expires_in_seconds,
            "expires_at": self.expires_at,
        }
        if include_raw:
            payload["raw"] = self.raw
        return payload


@dataclass(frozen=True, slots=True)
class KickbaseSquadPlayer:
    player_id: str
    first_name: str | None
    last_name: str | None
    team_id: str | None
    position: int | None
    market_value: int | None
    points: int | None
    average_points: int | None
    market_value_day_change: int | None
    market_value_total_change: int | None
    raw: dict[str, Any]

    @property
    def full_name(self) -> str:
        full_name = " ".join(part for part in [self.first_name, self.last_name] if part)
        return full_name or self.player_id

    def to_dict(self, *, include_raw: bool = False) -> dict[str, Any]:
        payload = {
            "player_id": self.player_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "team_id": self.team_id,
            "position": self.position,
            "market_value": self.market_value,
            "points": self.points,
            "average_points": self.average_points,
            "market_value_day_change": self.market_value_day_change,
            "market_value_total_change": self.market_value_total_change,
        }
        if include_raw:
            payload["raw"] = self.raw
        return payload


@dataclass(frozen=True, slots=True)
class KickbaseLeagueManager:
    manager_id: str
    display_name: str
    profile_image_path: str | None
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class KickbaseManagerTransfer:
    manager_id: str
    manager_name: str | None
    player_id: str
    player_name: str
    team_id: str | None
    transfer_type: int | None
    transfer_type_text: str | None
    price: int | None
    date: str
    counterparty_manager_name: str | None
    player_image_path: str | None
    raw: dict[str, Any]


class KickbaseClient:
    def __init__(
        self,
        token: str,
        *,
        session: requests.Session | None = None,
        base_url: str = KICKBASE_BASE_URL,
        request_timeout: int = 20,
    ):
        if not token:
            raise ValueError("Kickbase token is required.")
        self._token = token
        self._base_url = base_url.rstrip("/")
        self._request_timeout = request_timeout
        self._session = session or requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            }
        )

    @classmethod
    def login(
        cls,
        username: str,
        password: str,
        *,
        base_url: str = KICKBASE_BASE_URL,
        request_timeout: int = 20,
    ) -> "KickbaseClient":
        if not username or not password:
            raise KickbaseConfigurationError(
                "Kickbase credentials missing. Provide username and password or configure env vars."
            )

        session = requests.Session()
        try:
            response = session.post(
                f"{base_url.rstrip('/')}/user/login",
                json={"em": username, "pass": password, "loy": False, "rep": {}},
                timeout=request_timeout,
            )
        except requests.RequestException as error:
            raise KickbaseApiError(f"Kickbase login request failed: {error}") from error

        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            if response.status_code == 401:
                raise KickbaseApiError("Kickbase login failed with 401 Unauthorized.") from error
            raise KickbaseApiError(f"Kickbase login failed: {response.status_code} {response.text}") from error

        try:
            payload = response.json()
        except ValueError as error:
            raise KickbaseApiError("Kickbase login succeeded but returned invalid JSON.") from error

        token = payload.get("tkn") if isinstance(payload, dict) else None
        if not token:
            raise KickbaseApiError("Kickbase login succeeded but no token was returned.")

        return cls(token, session=session, base_url=base_url, request_timeout=request_timeout)

    @classmethod
    def from_env(
        cls,
        *,
        base_url: str = KICKBASE_BASE_URL,
        request_timeout: int = 20,
    ) -> "KickbaseClient":
        token = _first_env_value("KICKBASE_TOKEN", "KICK_TOKEN")
        if token:
            return cls(token, base_url=base_url, request_timeout=request_timeout)

        username = _first_env_value("KICK_USER", "KICKBASE_USER", "KICKBASE_EMAIL")
        password = _first_env_value("KICK_PASS", "KICKBASE_PASSWORD")
        if not username or not password:
            raise KickbaseConfigurationError(
                "Missing Kickbase credentials. Set KICKBASE_TOKEN or KICK_USER/KICK_PASS."
            )
        return cls.login(username, password, base_url=base_url, request_timeout=request_timeout)

    def get_profile_name(self) -> str:
        payload = self._get_json("/user/settings")
        return str(payload.get("u", {}).get("unm") or "unknown")

    def list_leagues(self) -> list[KickbaseLeague]:
        payload = self._get_json("/leagues/selection")
        leagues = []
        for item in payload.get("it", []):
            league_id = item.get("i")
            league_name = item.get("n")
            if league_id is None or not league_name:
                continue
            leagues.append(
                KickbaseLeague(
                    id=str(league_id),
                    name=str(league_name),
                    competition_id=_to_str(item.get("cpi")),
                )
            )
        return leagues

    def resolve_league(self, league_name: str | None = None) -> KickbaseLeague:
        leagues = self.list_leagues()
        if not leagues:
            raise KickbaseApiError("No Kickbase leagues were returned for this account.")

        if not league_name:
            return leagues[0]

        for league in leagues:
            if league.name == league_name:
                return league

        available_names = ", ".join(league.name for league in leagues)
        raise ValueError(f"League '{league_name}' was not found. Available leagues: {available_names}")

    def get_budget(self, league_id: str) -> int | None:
        payload = self._get_json(f"/leagues/{league_id}/me/budget")
        return _to_int(payload.get("b"))

    def get_league_managers(self, league_id: str) -> list[KickbaseLeagueManager]:
        payload = self._get_json(f"/leagues/{league_id}/ranking")
        managers = []
        for item in payload.get("us", []):
            if not isinstance(item, dict):
                continue
            manager_id = item.get("i")
            display_name = _to_str(item.get("unm")) or _to_str(item.get("n")) or _to_str(item.get("nm"))
            if manager_id is None or not display_name:
                continue
            managers.append(
                KickbaseLeagueManager(
                    manager_id=str(manager_id),
                    display_name=display_name,
                    profile_image_path=_to_str(item.get("uim")) or _to_str(item.get("im")),
                    raw=item,
                )
            )
        return managers

    def get_competition_teams(self, competition_id: str) -> list[KickbaseTeam]:
        payload = self._get_json(f"/competitions/{competition_id}/table")
        teams = []
        for item in payload.get("it", []):
            if not isinstance(item, dict):
                continue
            team_id = item.get("tid")
            team_name = item.get("tn")
            if team_id is None or not team_name:
                continue
            teams.append(
                KickbaseTeam(
                    id=str(team_id),
                    name=str(team_name),
                    current_place=_to_int(item.get("cpl")),
                    previous_place=_to_int(item.get("pcpl")),
                    points=_to_int(item.get("cp")),
                    matches=_to_int(item.get("mc")),
                    goal_difference=_to_int(item.get("gd")),
                    badge_path=_to_str(item.get("tim")),
                    raw=item,
                )
            )
        return teams

    def get_competition_matches(self, competition_id: str) -> list[KickbaseCompetitionMatch]:
        payload = self._get_json(f"/competitions/{competition_id}/matchdays")
        matches: list[KickbaseCompetitionMatch] = []
        for segment in payload.get("it", []):
            if not isinstance(segment, dict):
                continue
            segment_matchday = _to_int(segment.get("day"))
            for item in segment.get("it", []):
                if not isinstance(item, dict):
                    continue
                match_date = _parse_iso_timestamp(item.get("dt"))
                if match_date is None:
                    continue
                matchday = _to_int(item.get("day")) or segment_matchday or 0
                match_id = str(item.get("mi") or f"{competition_id}:{matchday}:{item.get('dt')}")
                matches.append(
                    KickbaseCompetitionMatch(
                        match_id=match_id,
                        season=_derive_season(match_date.date()),
                        matchday=matchday,
                        date=match_date.isoformat().replace("+00:00", "Z"),
                        home_team_id=_to_str(item.get("t1")),
                        away_team_id=_to_str(item.get("t2")),
                        home_team_short_name=_to_str(item.get("t1sy")),
                        away_team_short_name=_to_str(item.get("t2sy")),
                        home_team_badge_path=_to_str(item.get("t1im")),
                        away_team_badge_path=_to_str(item.get("t2im")),
                        home_goals=_to_int(item.get("t1g")),
                        away_goals=_to_int(item.get("t2g")),
                        match_status=_to_int(item.get("st")),
                        is_live=_to_bool(item.get("il")),
                        raw=item,
                    )
                )

        matches.sort(key=lambda item: (item.date, item.matchday, item.match_id))
        return matches

    def get_competition_players(self, competition_id: str) -> list[KickbaseCompetitionPlayer]:
        players_by_id: dict[str, KickbaseCompetitionPlayer] = {}
        for team in self.get_competition_teams(competition_id):
            payload = self._get_json(f"/competitions/{competition_id}/teams/{team.id}/teamprofile")
            for item in payload.get("it", []):
                if not isinstance(item, dict):
                    continue
                player = _map_competition_player(item, team_name=team.name)
                players_by_id[player.player_id] = player
        return list(players_by_id.values())

    def get_competition_player_detail(self, competition_id: str, player_id: str) -> KickbaseCompetitionPlayerDetail:
        competition_id_text = str(competition_id or "").strip()
        player_id_text = str(player_id or "").strip()
        if not competition_id_text:
            raise ValueError("Competition ID is required to fetch player details.")
        if not player_id_text:
            raise ValueError("Player ID is required to fetch player details.")
        payload = self._get_json(f"/competitions/{competition_id_text}/players/{player_id_text}")
        if not isinstance(payload, dict) or not payload:
            raise KickbaseApiError("Kickbase returned no player details.")
        return _map_competition_player_detail(payload)

    def get_competition_player_detail_raw(self, competition_id: str, player_id: str) -> dict[str, Any]:
        competition_id_text = str(competition_id or "").strip()
        player_id_text = str(player_id or "").strip()
        if not competition_id_text:
            raise ValueError("Competition ID is required to fetch raw player details.")
        if not player_id_text:
            raise ValueError("Player ID is required to fetch raw player details.")
        payload = self._get_json(f"/competitions/{competition_id_text}/players/{player_id_text}")
        if not isinstance(payload, dict):
            raise KickbaseApiError("Kickbase returned an unexpected player detail payload.")
        return payload

    def get_player_market_value_history(
        self,
        competition_id: str,
        player_id: str,
        *,
        days: int = MAX_MARKET_VALUE_WINDOW_DAYS,
    ) -> list[KickbasePlayerMarketValue]:
        requested_days = max(1, min(days, MAX_MARKET_VALUE_WINDOW_DAYS))
        request_window = (
            MIN_MARKET_VALUE_WINDOW_DAYS
            if requested_days <= MIN_MARKET_VALUE_WINDOW_DAYS
            else MAX_MARKET_VALUE_WINDOW_DAYS
        )
        payload = self._get_json(f"/competitions/{competition_id}/players/{player_id}/marketvalue/{request_window}")

        market_values = []
        for item in payload.get("it", []):
            if not isinstance(item, dict):
                continue
            day_offset = _to_int(item.get("dt"))
            market_value = _to_int(item.get("mv"))
            if day_offset is None or market_value is None:
                continue
            market_values.append(
                KickbasePlayerMarketValue(
                    player_id=str(player_id),
                    date=(UNIX_EPOCH + timedelta(days=day_offset)).isoformat(),
                    market_value=market_value,
                )
            )

        market_values.sort(key=lambda item: item.date)
        if len(market_values) > requested_days:
            return market_values[-requested_days:]
        return market_values

    def get_player_matchday_history(self, competition_id: str, player_id: str) -> list[KickbaseMatchdayStat]:
        payload = self._get_json(f"/competitions/{competition_id}/players/{player_id}/performance")
        history = []
        for segment in payload.get("it", []):
            if not isinstance(segment, dict):
                continue
            for item in segment.get("ph", []):
                if not isinstance(item, dict):
                    continue
                match_date = _parse_iso_timestamp(item.get("md"))
                if match_date is None:
                    continue
                history.append(
                    KickbaseMatchdayStat(
                        player_id=str(player_id),
                        match_id=str(item.get("mi") or f"{player_id}:{item.get('day')}:{item.get('md')}"),
                        season=_derive_season(match_date.date()),
                        matchday=_to_int(item.get("day")) or 0,
                        date=match_date.isoformat().replace("+00:00", "Z"),
                        points=_to_int(item.get("p")),
                        minutes=_parse_minutes(item.get("mp")),
                        average_points=_to_int(item.get("ap")),
                        total_points=_to_int(item.get("tp")),
                        appearance_status=_to_int(item.get("st")),
                        matchday_status=_to_int(item.get("mdst")),
                        is_current=_to_bool(item.get("cur")),
                        player_team_id=_to_str(item.get("pt")),
                        home_team_id=_to_str(item.get("t1")),
                        away_team_id=_to_str(item.get("t2")),
                        home_goals=_to_int(item.get("t1g")),
                        away_goals=_to_int(item.get("t2g")),
                        raw=item,
                    )
                )

        history.sort(key=lambda item: (item.date, item.match_id))
        return history

    def get_manager_transfer_history(
        self,
        league_id: str,
        manager_id: str,
        *,
        start: int = 0,
    ) -> list[KickbaseManagerTransfer]:
        payload = self._get_json(f"/leagues/{league_id}/managers/{manager_id}/transfer?start={max(0, start)}")
        manager_name = _to_str(payload.get("unm"))
        transfers = []
        for item in payload.get("it", []):
            if not isinstance(item, dict):
                continue
            transfer_date = _parse_iso_timestamp(item.get("dt"))
            player_id = item.get("pi")
            player_name = _to_str(item.get("pn"))
            if transfer_date is None or player_id is None or not player_name:
                continue
            transfer_type = _to_int(item.get("tty"))
            transfers.append(
                KickbaseManagerTransfer(
                    manager_id=str(manager_id),
                    manager_name=manager_name,
                    player_id=str(player_id),
                    player_name=player_name,
                    team_id=_to_str(item.get("tid")),
                    transfer_type=transfer_type,
                    transfer_type_text=TRANSFER_TYPES.get(transfer_type),
                    price=_to_int(item.get("trp")),
                    date=transfer_date.isoformat().replace("+00:00", "Z"),
                    counterparty_manager_name=_to_str(item.get("othnm")),
                    player_image_path=_to_str(item.get("pim")),
                    raw=item,
                )
            )

        transfers.sort(key=lambda item: item.date, reverse=True)
        return transfers

    def get_market_raw(self, league_id: str) -> list[dict[str, Any]]:
        payload = self._get_json(f"/leagues/{league_id}/market")
        return [item for item in payload.get("it", []) if isinstance(item, dict)]

    def get_squad_raw(self, league_id: str) -> list[dict[str, Any]]:
        payload = self._get_json(f"/leagues/{league_id}/squad")
        return [item for item in payload.get("it", []) if isinstance(item, dict)]

    def get_market_players(
        self,
        league_id: str,
        *,
        captured_at: datetime | None = None,
    ) -> list[KickbaseMarketPlayer]:
        reference_time = captured_at or datetime.now(timezone.utc)
        return [_map_market_player(item, captured_at=reference_time) for item in self.get_market_raw(league_id)]

    def get_squad_players(self, league_id: str) -> list[KickbaseSquadPlayer]:
        return [_map_squad_player(item) for item in self.get_squad_raw(league_id)]

    def get_manager_squad(self, league_id: str, *, manager_id: str) -> dict[str, Any]:
        payload = self._get_json(f"/leagues/{league_id}/managers/{manager_id}/squad")
        players: list[dict[str, Any]] = []
        for item in payload.get("it", []):
            if not isinstance(item, dict):
                continue
            player_id = _to_str(item.get("pi"))
            if not player_id:
                continue
            players.append(
                {
                    "player_id": player_id,
                    "player_name": _to_str(item.get("pn")) or "",
                    "team_id": _to_str(item.get("tid")),
                    "position": _to_int(item.get("pos")),
                    "market_value": _to_int(item.get("mv")),
                    "market_value_profit_loss": _to_int(item.get("mvgl")),
                    "average_points": _to_int(item.get("ap")),
                    "total_points": _to_int(item.get("p")),
                    "league_ownership": _to_int(item.get("lo")),
                    "status": _to_int(item.get("st")),
                    "status_list": list(item.get("stl") or []),
                    "market_value_trend": _to_int(item.get("mvt")),
                    "day_change_sdmvt": _to_int(item.get("sdmvt")),
                    "day_change_tfhmvt": _to_int(item.get("tfhmvt")),
                    "is_team_of_the_matchday": bool(item.get("iotm")),
                    "offer_count": _to_int(item.get("ofc")) or 0,
                }
            )
        return {
            "manager_id": str(payload.get("u") or manager_id),
            "manager_name": _to_str(payload.get("unm")),
            "squad_status": _to_int(payload.get("st")),
            "player_count": _to_int(payload.get("nps")),
            "players": players,
        }

    def set_lineup(
        self,
        league_id: str,
        *,
        formation_type: str,
        player_ids: list[str],
    ) -> dict[str, Any]:
        league_id_text = str(league_id or "").strip()
        formation_text = str(formation_type or "").strip()
        normalized_player_ids = [str(player_id).strip() for player_id in list(player_ids or []) if str(player_id).strip()]
        if not league_id_text:
            raise ValueError("League ID is required to set the lineup.")
        if not formation_text:
            raise ValueError("Formation type is required to set the lineup.")
        if not normalized_player_ids:
            raise ValueError("At least one player ID is required to set the lineup.")
        return self._post_json(
            f"/leagues/{league_id_text}/lineup",
            json_payload={"type": formation_text, "players": normalized_player_ids},
        )

    def place_offer(
        self,
        league_id: str,
        *,
        player_id: str,
        price: int,
    ) -> dict[str, Any]:
        league_id_text = str(league_id or "").strip()
        player_id_text = str(player_id or "").strip()
        normalized_price = int(price)
        if not league_id_text:
            raise ValueError("League ID is required to place an offer.")
        if not player_id_text:
            raise ValueError("Player ID is required to place an offer.")
        if normalized_price <= 0:
            raise ValueError("Offer price must be greater than zero.")
        return self._post_json(
            f"/leagues/{league_id_text}/market/{player_id_text}/offers",
            json_payload={"price": normalized_price},
        )

    def get_own_offer_state(
        self,
        league_id: str,
        *,
        player_id: str,
    ) -> dict[str, Any]:
        league_id_text = str(league_id or "").strip()
        player_id_text = str(player_id or "").strip()
        if not league_id_text:
            raise ValueError("League ID is required to inspect the own offer state.")
        if not player_id_text:
            raise ValueError("Player ID is required to inspect the own offer state.")

        market_entry = next(
            (item for item in self.get_market_raw(league_id_text) if str(item.get("i") or "").strip() == player_id_text),
            None,
        )
        offer_id = _to_str((market_entry or {}).get("uoid"))
        offer_price = _to_int((market_entry or {}).get("uop"))
        return {
            "player_id": player_id_text,
            "has_own_offer": bool(offer_id),
            "offer_id": offer_id,
            "offer_price": offer_price,
            "market_entry": market_entry,
        }

    def remove_offer(
        self,
        league_id: str,
        *,
        player_id: str,
        offer_id: str,
    ) -> dict[str, Any]:
        league_id_text = str(league_id or "").strip()
        player_id_text = str(player_id or "").strip()
        offer_id_text = str(offer_id or "").strip()
        if not league_id_text:
            raise ValueError("League ID is required to remove an offer.")
        if not player_id_text:
            raise ValueError("Player ID is required to remove an offer.")
        if not offer_id_text:
            raise ValueError("Offer ID is required to remove an offer.")
        return self._delete_json(f"/leagues/{league_id_text}/market/{player_id_text}/offers/{offer_id_text}")

    def cancel_own_offer(
        self,
        league_id: str,
        *,
        player_id: str,
    ) -> dict[str, Any]:
        own_offer_before = self.get_own_offer_state(league_id, player_id=player_id)
        if not own_offer_before["has_own_offer"]:
            return {
                "status": "completed",
                "offer_removed": True,
                "completion_method": "readback",
                "offer_id": None,
                "offer_price_before": None,
                "has_own_offer_after": False,
                "market_entry_after": own_offer_before["market_entry"],
            }

        self.remove_offer(
            league_id,
            player_id=player_id,
            offer_id=str(own_offer_before["offer_id"]),
        )
        own_offer_after = self.get_own_offer_state(league_id, player_id=player_id)
        if own_offer_after["has_own_offer"]:
            raise KickbaseApiError(
                "Kickbase offer DELETE was sent, but the own offer is still visible in the readback."
            )
        return {
            "status": "completed",
            "offer_removed": True,
            "completion_method": "DELETE",
            "offer_id": own_offer_before["offer_id"],
            "offer_price_before": own_offer_before["offer_price"],
            "has_own_offer_after": False,
            "market_entry_after": own_offer_after["market_entry"],
        }

    def list_player_for_sale(
        self,
        league_id: str,
        *,
        player_id: str,
    ) -> dict[str, Any]:
        league_id_text = str(league_id or "").strip()
        player_id_text = str(player_id or "").strip()
        if not league_id_text:
            raise ValueError("League ID is required to list a player for sale.")
        if not player_id_text:
            raise ValueError("Player ID is required to list a player for sale.")
        return self._post_json(f"/leagues/{league_id_text}/market/{player_id_text}/sell")

    def accept_kickbase_offer(
        self,
        league_id: str,
        *,
        player_id: str,
    ) -> dict[str, Any]:
        league_id_text = str(league_id or "").strip()
        player_id_text = str(player_id or "").strip()
        if not league_id_text:
            raise ValueError("League ID is required to accept the Kickbase offer.")
        if not player_id_text:
            raise ValueError("Player ID is required to accept the Kickbase offer.")
        return self._delete_json(f"/leagues/{league_id_text}/market/{player_id_text}/sell")

    def get_player_sale_state(
        self,
        league_id: str,
        *,
        player_id: str,
    ) -> dict[str, Any]:
        league_id_text = str(league_id or "").strip()
        player_id_text = str(player_id or "").strip()
        if not league_id_text:
            raise ValueError("League ID is required to inspect the sale state.")
        if not player_id_text:
            raise ValueError("Player ID is required to inspect the sale state.")

        squad_ids = {player.player_id for player in self.get_squad_players(league_id_text)}
        market_entry = next(
            (item for item in self.get_market_raw(league_id_text) if str(item.get("i") or "").strip() == player_id_text),
            None,
        )
        return {
            "player_id": player_id_text,
            "in_squad": player_id_text in squad_ids,
            "market_listed": market_entry is not None,
            "market_entry": market_entry,
        }

    def sell_player(
        self,
        league_id: str,
        *,
        player_id: str,
    ) -> dict[str, Any]:
        sale_state_before = self.get_player_sale_state(league_id, player_id=player_id)
        if not sale_state_before["in_squad"] and not sale_state_before["market_listed"]:
            return {
                "status": "completed",
                "sale_completed": True,
                "completion_method": "readback",
                "in_squad_after": False,
                "market_listed_after": False,
                "market_entry_after": None,
            }

        self.list_player_for_sale(league_id, player_id=player_id)
        sale_state_after = self.get_player_sale_state(league_id, player_id=player_id)
        if not sale_state_after["in_squad"]:
            return {
                "status": "completed",
                "sale_completed": True,
                "completion_method": "POST",
                "in_squad_after": False,
                "market_listed_after": bool(sale_state_after["market_listed"]),
                "market_entry_after": sale_state_after["market_entry"],
            }

        raise KickbaseApiError(
            "Kickbase sell POST was sent, but the player is still in the squad in the readback."
        )

    def build_league_snapshot(
        self,
        *,
        league_name: str | None = None,
        market_limit: int = 10,
        include_raw: bool = False,
    ) -> dict[str, Any]:
        league = self.resolve_league(league_name)
        captured_at = datetime.now(timezone.utc)
        market_players = self.get_market_players(league.id, captured_at=captured_at)

        return {
            "captured_at": captured_at.isoformat().replace("+00:00", "Z"),
            "username": self.get_profile_name(),
            "league": {"id": league.id, "name": league.name},
            "competition": {"id": league.competition_id},
            "budget": self.get_budget(league.id),
            "market_count": len(market_players),
            "market_preview": [
                player.to_dict(include_raw=include_raw) for player in market_players[: max(0, market_limit)]
            ],
        }

    def _get_json(self, path: str) -> dict[str, Any]:
        return self._request_json("GET", path)

    def _post_json(self, path: str, *, json_payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._request_json("POST", path, json_payload=json_payload)

    def _delete_json(self, path: str) -> dict[str, Any]:
        return self._request_json("DELETE", path)

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        json_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            response = self._session.request(
                method,
                f"{self._base_url}{path}",
                json=json_payload,
                timeout=self._request_timeout,
            )
        except requests.RequestException as error:
            raise KickbaseApiError(f"Kickbase request failed: {error}") from error
        return self._parse_json_response(response)

    def _parse_json_response(self, response: requests.Response) -> dict[str, Any]:
        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            if response.status_code == 401:
                raise KickbaseApiError("Kickbase request returned 401 Unauthorized. The login token may be invalid.") from error
            raise KickbaseApiError(f"Kickbase request failed: {response.status_code} {response.text}") from error
        if response.status_code == 204:
            return {}
        if not str(response.text or "").strip():
            return {}
        try:
            payload = response.json()
        except ValueError as error:
            raise KickbaseApiError("Kickbase returned invalid JSON.") from error
        if not isinstance(payload, dict):
            raise KickbaseApiError("Kickbase returned an unexpected payload type.")
        return payload


def _map_competition_player(item: dict[str, Any], *, team_name: str | None) -> KickbaseCompetitionPlayer:
    display_name = _to_str(item.get("n")) or str(item.get("i") or "unknown")
    return KickbaseCompetitionPlayer(
        player_id=str(item.get("i") or "unknown"),
        display_name=display_name,
        first_name=None,
        last_name=display_name,
        team_id=_to_str(item.get("tid")),
        team_name=team_name,
        position=_to_int(item.get("pos")),
        market_value=_to_int(item.get("mv")),
        average_points=_to_int(item.get("ap")),
        market_value_day_change=_to_int(item.get("sdmvt")),
        market_value_total_change=_to_int(item.get("mvgl")),
        raw=item,
    )


def _map_competition_player_detail(item: dict[str, Any]) -> KickbaseCompetitionPlayerDetail:
    first_name = _to_str(item.get("fn"))
    last_name = _to_str(item.get("ln"))
    display_name = " ".join(part for part in [first_name, last_name] if part) or _to_str(item.get("shn")) or str(item.get("i") or "unknown")
    return KickbaseCompetitionPlayerDetail(
        player_id=str(item.get("i") or "unknown"),
        display_name=display_name,
        first_name=first_name,
        last_name=last_name,
        shirt_number=_to_int(item.get("shn")),
        team_id=_to_str(item.get("tid")),
        team_name=_to_str(item.get("tn")),
        position=_to_int(item.get("pos")),
        market_value=_to_int(item.get("mv")),
        average_points=_to_int(item.get("ap")),
        total_points=_to_int(item.get("tp")),
        goals=_to_int(item.get("g")),
        yellow_cards=_to_int(item.get("y")),
        red_cards=_to_int(item.get("r")),
        market_value_day_change=_to_int(item.get("tfhmvt")),
        projected_starting_lineup=_to_bool(item.get("sl")),
        provider_name=_to_str(item.get("plpt")),
        provider_updated_at=_to_str(item.get("ts")),
        provider_status_raw=_to_int(item.get("stud")),
        status=_to_int(item.get("st")),
        status_text=_to_str(item.get("stxt")),
        status_list=list(item.get("stl") or []),
        raw=item,
    )


def _map_market_player(item: dict[str, Any], *, captured_at: datetime) -> KickbaseMarketPlayer:
    expires_in_seconds = _to_int(item.get("exs"))
    return KickbaseMarketPlayer(
        player_id=str(item.get("i") or "unknown"),
        first_name=_to_str(item.get("fn")),
        last_name=_to_str(item.get("n")),
        team_id=_to_str(item.get("tid")),
        position=_to_int(item.get("pos")),
        market_value=_to_int(item.get("mv")),
        list_price=_to_int(item.get("prc")),
        expires_in_seconds=expires_in_seconds,
        expires_at=_expires_at_from_seconds(expires_in_seconds, captured_at=captured_at),
        raw=item,
    )


def _map_squad_player(item: dict[str, Any]) -> KickbaseSquadPlayer:
    player_name = _to_str(item.get("n"))
    return KickbaseSquadPlayer(
        player_id=str(item.get("i") or "unknown"),
        first_name=None,
        last_name=player_name,
        team_id=_to_str(item.get("tid")),
        position=_to_int(item.get("pos")),
        market_value=_to_int(item.get("mv")),
        points=_to_int(item.get("p")),
        average_points=_to_int(item.get("ap")),
        market_value_day_change=_to_int(item.get("tfhmvt")),
        market_value_total_change=_to_int(item.get("tfhmvt")),
        raw=item,
    )


def _expires_at_from_seconds(expires_in_seconds: int | None, *, captured_at: datetime) -> str | None:
    if expires_in_seconds is None:
        return None
    expires_at = captured_at + timedelta(seconds=expires_in_seconds)
    return expires_at.isoformat().replace("+00:00", "Z")


def _derive_season(match_date: date) -> str:
    if match_date.month >= 7:
        return f"{match_date.year}/{match_date.year + 1}"
    return f"{match_date.year - 1}/{match_date.year}"


def _parse_iso_timestamp(value: object) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _parse_minutes(value: object) -> int | None:
    if value is None:
        return None
    text = str(value).strip().replace("'", "")
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _to_bool(value: object) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1"}:
        return True
    if text in {"false", "0"}:
        return False
    return None


def _to_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _first_env_value(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return None