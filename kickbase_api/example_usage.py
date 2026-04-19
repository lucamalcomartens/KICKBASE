from __future__ import annotations

import os

from kickbase_api import KickbaseApiError, KickbaseClient, KickbaseConfigurationError


def main() -> int:
    try:
        client = KickbaseClient.from_env()
        league = client.resolve_league(os.getenv("KICKBASE_LEAGUE_NAME"))
        budget = client.get_budget(league.id)
        market_players = client.get_market_players(league.id)

        print(f"Profil: {client.get_profile_name()}")
        print(f"Liga: {league.name} ({league.id})")
        print(f"Budget: {budget}")
        print(f"Marktgroesse: {len(market_players)}")
        print()
        print("Top 5 Marktspieler:")

        for player in market_players[:5]:
            print(
                f"- {player.full_name} | Team={player.team_id} | "
                f"Marktwert={player.market_value} | Preis={player.list_price}"
            )
        return 0
    except KickbaseConfigurationError as error:
        print(f"Konfigurationsfehler: {error}")
        return 1
    except KickbaseApiError as error:
        print(f"API-Fehler: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())