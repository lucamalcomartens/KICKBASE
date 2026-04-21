# Agent Log

## Zweck

- Dieses Dokument ist die fortlaufende Historie der Agent-Arbeit im Repository.
- Neue Eintraege werden unten ergaenzt und enthalten Datum, Ergebnis und relevante Pruefungen.

## Historie

### 2026-04-19

- Repository-Kontext geprueft: keine vorhandenen Copilot-Workspace-Instruktionen und kein bestehender Custom Agent gefunden.
- Projektbasis bestaetigt: Python-Projekt im Ordner `kickbase_api/`, virtuelle Umgebung `.venv/`, Quickstart in `kickbase_api/README.md`.
- OpenClawd-inspirierter Repo-Agent vorbereitet mit zwei festen Wissensquellen:
  - `AGENT_GEDAECHTNIS.md` fuer den aktuellen verifizierten Stand.
  - `AGENT_LOG.md` fuer die Historie und den Fortschritt.
- Geplante Repo-Dateien fuer den Agent-Workflow angelegt:
  - `.github/copilot-instructions.md`
  - `.github/agents/kickbase-builder.agent.md`
  - `AGENT_GEDAECHTNIS.md`
  - `AGENT_LOG.md`
- Noch keine Laufzeit- oder Build-Pruefung ausgefuehrt, weil nur die Agent-Konfiguration und Projekt-Dokumentation angelegt wurden.
- Automationsfrage geprueft: `kickbase_api/Anwendungsfälle/gebot_vorhersage.py` unterstuetzt neben Windows-Credentials auch Token/Env-basierten Headless-Betrieb ueber `KickbaseClient.from_env()`.
- Daraus folgt: lokaler Task Scheduler loest das Erinnerungsproblem nur bei eingeschaltetem Rechner; fuer echte Abwesenheitstage ist ein externer Always-on-Runner mit Push-Benachrichtigung oder eng begrenzter Auto-Bid-Logik der richtige Hebel.
- Noch keine Codeaenderung fuer Scheduler oder Notification-Kanal umgesetzt; zunaechst Architektur-Optionen fuer GitHub Actions, kleinen Server oder Bot-Notification bewertet.
- GitHub-Action-Workflow `.github/workflows/morgenliste-gebote.yml` fuer `kickbase_api/Anwendungsfälle/morgen_liste_gebote.py` angelegt.
- Workflow auf taeglichen geplanten Lauf mit Zufallsstart zwischen 22:10 und 22:20 Berlin-Zeit umgestellt; Sommer- und Winterzeit werden ueber zwei UTC-Cron-Slots abgefangen.
- Workflow auf `--auto-bid --bid-level 80` festgelegt und gegen parallele Laeufe abgesichert.
- Login fuer GitHub Actions auf `KICKBASE_EMAIL` und `KICKBASE_PASSWORD` ausgerichtet; `KICKBASE_TOKEN` bleibt optional unterstuetzt.
- Dokumentation in `kickbase_api/Anwendungsfälle/README.md` fuer Workflow, Secrets und Zeitfenster aktualisiert.
- Geprueft: CLI-Einstieg von `morgen_liste_gebote.py` ueber `--help` erfolgreich; YAML- und Markdown-Dateien ohne gemeldete Fehler.
- Vom Nutzer bestaetigt: manueller `workflow_dispatch`-Test des GitHub-Action-Workflows hat funktioniert.

### 2026-04-21

- Auto-Bid-Logik in `kickbase_api/Anwendungsfälle/morgen_liste_gebote.py` um fuenf weitere Marktwert-Regeln erweitert: Summenregel, Treppenregel, bestaetigte Erholung, Billigspieler-Prozentregel und Re-Acceleration.
- Neue CLI-Schwellwerte fuer alle zusaetzlichen Regeln in `morgen_liste_gebote.py` ergaenzt, damit die Trigger weiter lokal und im Workflow justierbar bleiben.
- Ausgabe im Auto-Bid-Lauf auf eine gemeinsame Regelliste umgestellt, damit Review-Text und No-Match-Text nicht auseinanderlaufen.
- Dokumentation in `kickbase_api/Anwendungsfälle/README.md` an die neue Triggerlogik angepasst und den bisherigen Widerspruch zum verifizierten Workflow-Modus behoben: README zeigt jetzt wie der Code `--auto-bid --bid-level 50` statt `80`.
- Geprueft: `python -m py_compile Anwendungsfälle/morgen_liste_gebote.py` erfolgreich.
- Geprueft: `python Anwendungsfälle/morgen_liste_gebote.py --help` zeigt alle neuen CLI-Parameter fuer die zusaetzlichen Regeln an.
- Geprueft: Dry-Run `python Anwendungsfälle/morgen_liste_gebote.py --auto-bid --dry-run --bid-level 50` in Liga `Spitz (3594592)` liefert genau einen Treffer, Lucas Hoeler.
- Dry-Run-Detail: Lucas Hoeler triggert ueber strengen 3-Tages-Anstieg, Summenregel und Billigspielerregel; ein bestehendes eigenes Gebot wurde korrekt nur gemeldet und nicht veraendert.
- Kein echter Gebotsversand erfolgt, weil der Validierungslauf explizit als Dry-Run ausgefuehrt wurde.