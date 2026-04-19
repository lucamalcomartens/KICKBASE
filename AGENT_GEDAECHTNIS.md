# Agent Gedaechtnis

## Zweck

- Dieses Dokument haelt den aktuell verifizierten Projektstand fest.
- Es wird nach jeder relevanten Arbeitsphase aktualisiert.
- Wenn Code und Dokument nicht zusammenpassen, hat der verifizierte Codezustand Vorrang.

## Aktueller Stand

- Workspace-Root ist `C:\Projekte\KICKBASE`.
- Das operative Python-Projekt liegt im Unterordner `kickbase_api/`.
- Eine virtuelle Umgebung ist bereits als `.venv/` im Workspace vorhanden.
- Das Projekt ist bewusst leichtgewichtig gehalten und benoetigt keine Paketinstallation des eigenen Moduls.
- `kickbase_api/kickbase_api/` enthaelt den API-Client.
- `kickbase_api/Anwendungsfälle/` enthaelt konkrete Workflows und Auswertungen ueber dem API-Client.
- `kickbase_api/Anwendungsfälle/morgen_liste_gebote.py` steuert unter anderem die Marktlisten- und Auto-Bid-Logik bis zum naechsten Marktwert-Update.
- `.github/workflows/morgenliste-gebote.yml` fuehrt `morgen_liste_gebote.py` taeglich ueber GitHub Actions aus.

## Arbeitsprinzipien

- Local-first statt Infrastruktur-Ausbau ohne nachgewiesenen Engpass.
- Eine gemeinsame Entscheidungslogik fuer Simulation, Backtests und Live-Empfehlungen ist wichtiger als getrennte Heuristik-Pfade.
- Vor laengeren Retrainings, groesseren Vergleichslaeufen oder erweiterten Tests zuerst Rueckfrage stellen.

## Verifizierte Erkenntnisse

- Manager-eigene Marktlistings werden ueber `POST /v4/leagues/{leagueId}/market` mit `{"pi": playerId, "prc": price}` erstellt.
- Wiederholte Forecast-Logs fuer dieselbe Auktion muessen per Transfer-Schluessel dedupliziert werden, weil `expires_at` leicht driften kann.
- Ein exakt verifizierter 5-stufiger Mapping-Schluessel fuer Kickbase-Startelf-Wahrscheinlichkeiten ist derzeit noch nicht identifiziert.
- Die aktuelle Repo-Anforderung ist ein repo-lokaler Entwicklungsagent mit persistentem Markdown-Gedaechtnis und Fortschrittslog.
- Die Gebots-Workflows sind nicht auf Windows-Credentials festgelegt: `_build_client()` faellt nach Windows-Credential-Checks auf `KickbaseClient.from_env()` zurueck und kann damit auch headless auf einem externen Host laufen.
- Das eigentliche Problem fuer die taegliche Nutzung ist nicht die Skriptlogik, sondern die fehlende Always-on-Ausfuehrung und ein Push-Kanal fuer Ergebnisse oder Aktionen.
- Der taegliche GitHub-Action-Workflow laeuft mit `--auto-bid --bid-level 80` und einem Zufallsstart im Berlin-Fenster `22:10` bis `22:20`.
- Der Workflow unterstuetzt Login ueber `KICKBASE_EMAIL` und `KICKBASE_PASSWORD`; optional kann weiter `KICKBASE_TOKEN` genutzt werden.
- Der manuelle `workflow_dispatch`-Test fuer den GitHub-Action-Workflow wurde erfolgreich bestaetigt.

## Offene Punkte

- Falls gewuenscht, kann der Agent spaeter noch um spezialisierte Prompts oder weitere Teilagenten erweitert werden.
- Der naechste relevante Praxistest ist ein geplanter Nachtlauf des GitHub-Action-Workflows im echten 22:10-bis-22:20-Fenster.
- Fuer echte Abwesenheitstage braucht das Projekt entweder einen externen Scheduler mit Benachrichtigung oder eine klar begrenzte Vollautomatik fuer sichere Gebote.

## Letzte Aktualisierung

- 2026-04-19: Initialer Agent-Workflow fuer Repo-Gedaechtnis und Fortschrittslog angelegt.
- 2026-04-19: Automation-Anforderung fuer taegliche Marktpruefung verifiziert; headless Lauf ueber Env-Variablen statt nur Windows-Credentials moeglich.
- 2026-04-19: GitHub-Actions-Automation fuer `morgen_liste_gebote.py` mit erfolgreichem manuellem Test und Zufallsfenster 22:10 bis 22:20 Berlin-Zeit verifiziert.