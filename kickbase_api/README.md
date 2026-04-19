# KICKBASE API

Dieser Ordner ist absichtlich eigenstaendig.

Du kannst das Projekt direkt aus diesem Ordner starten. Eine Paket-Installation ist dafuer nicht notwendig.

## Inhalt

- `kickbase_api`: das eigentliche Python-Modul
- `Anwendungsfälle`: konkrete Workflows und Auswertungen oberhalb des API-Clients
- `example_usage.py`: kleines Beispiel fuer Login, Liga-Auswahl und Markt-Vorschau
- `requirements.txt`: minimale Laufzeitabhaengigkeit

## Schnellstart

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python example_usage.py
```

## Benoetigte Umgebungsvariablen

Du kannst entweder mit Benutzername und Passwort oder direkt mit einem Token arbeiten.

Variante 1:

- `KICK_USER` oder `KICKBASE_USER` oder `KICKBASE_EMAIL`
- `KICK_PASS` oder `KICKBASE_PASSWORD`

Variante 2:

- `KICKBASE_TOKEN` oder `KICK_TOKEN`

Optional:

- `KICKBASE_LEAGUE_NAME` fuer eine konkrete Liga

## Beispiel

```python
from kickbase_api import KickbaseClient

client = KickbaseClient.from_env()
league = client.resolve_league("Meine Liga")
market_players = client.get_market_players(league.id)

for player in market_players[:5]:
    print(player.full_name, player.market_value, player.list_price)
```

## Verfuegbare Kernmethoden

- `get_profile_name()`
- `list_leagues()`
- `resolve_league()`
- `get_budget()`
- `get_market_players()`
- `get_squad_players()`
- `get_league_managers()`
- `get_competition_teams()`
- `get_competition_matches()`
- `get_competition_players()`
- `get_competition_player_detail()`
- `get_competition_player_detail_raw()`
- `get_player_market_value_history()`
- `get_player_matchday_history()`
- `get_manager_transfer_history()`
- `set_lineup()`
- `place_offer()`
- `cancel_own_offer()`
- `sell_player()`
- `build_league_snapshot()`

Konkrete Anwendungslogik wie Gebotsprognosen liegt bewusst ausserhalb des API-Pakets im Ordner `Anwendungsfälle`.
