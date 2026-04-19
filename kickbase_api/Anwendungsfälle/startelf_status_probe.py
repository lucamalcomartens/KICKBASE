from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from kickbase_api import KickbaseApiError, KickbaseConfigurationError  # noqa: E402
import gebot_vorhersage as forecast_app  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Zeigt lineup-nahe Rohfelder aus dem Kickbase-Player-Detail-Endpoint")
    parser.add_argument("--league-id", help="Liga-ID. Falls leer, wird ueber --league-name oder die erste Liga aufgeloest.")
    parser.add_argument("--league-name", help="Exakter Ligename als Alternative zur Liga-ID.")
    parser.add_argument("--token", help="Optionaler Kickbase-Token als direkter Override der Windows-Anmeldeinformationen.")
    parser.add_argument("--update-hour", type=int, default=22, help="Stunde des naechsten Marktwert-Updates in lokaler Zeit.")
    parser.add_argument("--player-id", action="append", default=[], help="Spieler-ID. Kann mehrfach angegeben werden.")
    parser.add_argument("--player-name", action="append", default=[], help="Exakter Spielername. Kann mehrfach angegeben werden.")
    parser.add_argument("--all-market", action="store_true", help="Nimmt alle aktuellen Marktspieler statt nur bis zum naechsten Update.")
    parser.add_argument("--details", action="store_true", help="Zeigt zusaetzlich ein kleines Rohfeld-Subset je Spieler.")
    args = parser.parse_args(argv)

    if args.update_hour < 0 or args.update_hour > 23:
        parser.error("--update-hour muss zwischen 0 und 23 liegen.")

    try:
        client = forecast_app._build_client(args)
        league = forecast_app._resolve_league(client, league_id=args.league_id, league_name=args.league_name)
        if not league.competition_id:
            raise KickbaseApiError("The selected league does not expose a competition ID.")
        if args.player_id or args.player_name:
            selected_players = _select_competition_players(
                client,
                competition_id=league.competition_id,
                player_ids=args.player_id,
                player_names=args.player_name,
            )
        else:
            market_players = (
                client.get_market_players(league.id)
                if args.all_market
                else forecast_app._market_players_until_next_update(client, league.id, update_hour=args.update_hour)
            )
            selected_players = _select_market_players(market_players)
        if not selected_players:
            print("Keine passenden Spieler gefunden.")
            return 0
    except (KickbaseApiError, KickbaseConfigurationError, ValueError) as error:
        print(f"Fehler: {error}")
        return 1

    print(f"Liga: {league.name} ({league.id})")
    print()
    for index, player in enumerate(selected_players, start=1):
        detail = client.get_competition_player_detail(league.competition_id, player.player_id)
        print(_format_detail(index, player.display_name, detail, show_details=args.details))
        if index != len(selected_players):
            print()

    return 0


def _select_market_players(market_players):
    return [
        _ProbePlayer(player_id=player.player_id, display_name=player.full_name)
        for player in market_players
    ]


def _select_competition_players(client, *, competition_id: str, player_ids: list[str], player_names: list[str]):
    selected = []
    selected_ids = {str(player_id).strip() for player_id in player_ids if str(player_id).strip()}
    selected_names = {str(player_name).strip().casefold() for player_name in player_names if str(player_name).strip()}
    for player in client.get_competition_players(competition_id):
        candidate_names = {player.display_name.casefold()}
        if player.first_name or player.last_name:
            candidate_names.add(" ".join(part for part in [player.first_name, player.last_name] if part).casefold())
        if player.player_id in selected_ids or candidate_names & selected_names:
            selected.append(_ProbePlayer(player_id=player.player_id, display_name=_competition_player_display_name(player)))
    return selected


class _ProbePlayer:
    def __init__(self, *, player_id: str, display_name: str):
        self.player_id = player_id
        self.display_name = display_name


def _competition_player_display_name(player) -> str:
    if player.first_name or player.last_name:
        return " ".join(part for part in [player.first_name, player.last_name] if part)
    return player.display_name


def _format_detail(index: int, player_name: str, detail, *, show_details: bool) -> str:
    lines = [
        f"{index}. {player_name}",
        (
            f"   Startelf-Flag: {_format_bool(detail.projected_starting_lineup)} | "
            f"Provider: {detail.provider_name or '-'} | "
            f"Provider-Status roh: {detail.provider_status_raw if detail.provider_status_raw is not None else '-'}"
        ),
        (
            f"   Status: {detail.status if detail.status is not None else '-'} | "
            f"Status-Text: {detail.status_text or '-'} | "
            f"Update: {detail.provider_updated_at or '-'}"
        ),
    ]
    if show_details:
        raw = detail.raw
        lines.append(
            "   Rohfelder: "
            f"sl={raw.get('sl')} | stud={raw.get('stud')} | st={raw.get('st')} | "
            f"stxt={raw.get('stxt')} | ts={raw.get('ts')} | shn={raw.get('shn')}"
        )
    return "\n".join(lines)


def _format_bool(value: bool | None) -> str:
    if value is True:
        return "ja"
    if value is False:
        return "nein"
    return "-"


if __name__ == "__main__":
    raise SystemExit(main())