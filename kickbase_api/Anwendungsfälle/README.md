# Anwendungsfälle

Dieser Ordner enthaelt konkrete Workflows oberhalb des reinen API-Clients.

## Gebotsvorhersage

Die Datei `gebot_vorhersage.py` schaetzt fuer einen aktuellen Marktspieler zwei Schwellen:

- `zocken`: das 50. Perzentil
- `sicher`: das 80. Perzentil

Grundlage sind die Gewinnerpreise der letzten Liga-Kaeufe. Historische Zweitgebote sind ueber die bekannte API derzeit nicht stabil verfuegbar.

### Modelllogik

Die aktuelle Version arbeitet nicht mehr mit einem einfachen Mittelwertmodell, sondern mit einer gewichteten Quantilschaetzung:

- der Marktwert wird bis zum Ablaufzeitpunkt des Angebots fortgeschrieben
- historische Kauf-Faelle werden nicht hart ein- oder ausgeschlossen, sondern weich gewichtet
- standardmaessig werden die letzten 90 Tage betrachtet
- innerhalb dieses Fensters werden alte und neue Kaufdaten gleich behandelt; es gibt keine Zeitgewichtung
- die Gebotsschwellen werden direkt als gewichtete Quantile der historischen Overpays geschaetzt
- das Modell gewichtet Vergleichsfaelle zusaetzlich nach Position, Preisklasse und leicht nach gleichem Verein
- die finalen Zielwerte bleiben nah an diesen Perzentilen; nur spaetere Kalibrierung kann noch leicht justieren
- jede Empfehlung wird lokal protokolliert, damit spaeter eine automatische Kalibrierung moeglich ist

Die Kalibrierung bleibt global robust, blendet aber passende Teilmengen nach Position, Preisklasse und Verein nur dann
staerker ein, wenn dort genug abgeschlossene Faelle vorhanden sind. Dadurch helfen Segmente, ohne duenne Teilmengen zu
ueberbewerten.

### Trend-Signal

Der Trend des Zielspielers und der Vergleichstransfers nutzt jetzt mehrere Fenster:

- 1-Tages-Steigung als taegliche Log-Rendite
- 3-Tages-Steigung als geglaettete taegliche Log-Rendite
- 7-Tages-Steigung als langsamerer Grundtrend
- Beschleunigung = `1D - 3D/d`
- Distanz zum 14-Tages-Hoch und 14-Tages-Tief
- Momentum-Score als Mischung aus Trend, Beschleunigung und Range-Position

### Kalibrierung und Logging

Jeder Lauf schreibt einen Forecast in `Anwendungsfälle\daten\gebot_vorhersage_log.jsonl`.

Sobald genug abgeschlossene historische Empfehlungen vorliegen, nutzt das Skript diese Logs zur Rueckkalibrierung:

- Trefferquote von `zocken`
- Trefferquote von `sicher`
- kleiner Auf- oder Abschlag, wenn die Empfehlung historisch systematisch zu hoch oder zu niedrig lag

### Interaktiver Aufruf

Ohne Spielerparameter startet das Skript interaktiv:

- es laedt aktuelle Marktspieler
- filtert auf Spieler, die bis zum naechsten Marktwert-Update um 22:00 auslaufen
- wenn dort niemand liegt, zeigt es stattdessen die Spieler mit Ablauf am Folgetag
- zeigt diese nummeriert und uebersichtlich an, inklusive der letzten drei Marktwertaenderungen je Spieler
- erlaubt eine Mehrfachauswahl per Nummern wie `1,3,5` oder `2-4`
- gibt danach standardmaessig nur den Wert fuer das 50. und 80. Perzentil aus
- die Anmeldung kommt aus der Windows-Anmeldeinformationsverwaltung

```powershell
python Anwendungsfälle\gebot_vorhersage.py --league-name "Meine Liga"
```

Mit technischem Detailblock:

```powershell
python Anwendungsfälle\gebot_vorhersage.py --league-name "Meine Liga" --details
```

### Windows-Anmeldeinformationsverwaltung

Lege eines dieser generischen Credentials in Windows an:

- `KICKBASE_TOKEN`: Kennwort = Kickbase-Token, Benutzername beliebig
- `KICKBASE_LOGIN`: Benutzername = Kickbase-E-Mail oder Benutzername, Kennwort = Kickbase-Passwort

Per PowerShell oder Terminal geht das z.B. so:

```powershell
cmdkey /generic:KICKBASE_TOKEN /user:token /pass:DEIN_TOKEN
```

oder fuer Benutzername/Passwort:

```powershell
cmdkey /generic:KICKBASE_LOGIN /user:mail@example.com /pass:DEIN_PASSWORT
```

Optional kannst du weiterhin direkt einen Token uebergeben. Das ueberschreibt den Credential-Manager-Eintrag:

```powershell
python Anwendungsfälle\gebot_vorhersage.py --league-name "Meine Liga" --token "..."
```

Optional kannst du die Update-Stunde anpassen:

```powershell
python Anwendungsfälle\gebot_vorhersage.py --league-name "Meine Liga" --update-hour 22
```

### Direkter Aufruf

```powershell
python Anwendungsfälle\gebot_vorhersage.py --league-name "Meine Liga" --player-name "Thomas Muller"
```

Alternativ mit Spieler-ID:

```powershell
python Anwendungsfälle\gebot_vorhersage.py --league-id "123456" --player-id "78910"
```

## Startelf-Status Probe

Die Datei `startelf_status_probe.py` zeigt die derzeit lesbaren lineup-nahen Felder aus dem Player-Detail-Endpoint.

Damit kann man fuer konkrete Spieler das Ligainsider-Flag `sl`, den rohen Provider-Status `stud`, den Kickbase-Status und den Update-Zeitpunkt gegen die Premium-App vergleichen.

Ohne Spielerfilter werden standardmaessig die Marktspieler bis zum naechsten Marktwert-Update ausgegeben:

```powershell
python Anwendungsfälle\startelf_status_probe.py --league-name "Meine Liga"
```

Gezielt fuer einzelne Spieler:

```powershell
python Anwendungsfälle\startelf_status_probe.py --league-name "Meine Liga" --player-name "Mathias Honsak" --player-name "Andrej Kramarić" --details
```

## Liste bis zum naechsten Update

Die Datei `morgen_liste_gebote.py` berechnet fuer alle Spieler mit Ablauf bis zum naechsten Marktwert-Update direkt `zocken` und `sicher`.

Die Ausgaben zeigen sowohl den absoluten Zielwert als auch den absoluten Aufschlag auf die berechnete Basis bis zum Ablauf.

```powershell
python Anwendungsfälle\morgen_liste_gebote.py --league-name "Meine Liga"
```

Optional mit Detailblock je Spieler:

```powershell
python Anwendungsfälle\morgen_liste_gebote.py --league-name "Meine Liga" --details
```

### Auto-Gebote bis zum naechsten Update

Die gleiche Datei kann auch automatisch Gebote fuer die Marktliste bis zum naechsten Marktwert-Update setzen:

- es werden nur Spieler betrachtet, die bis zum naechsten Marktwert-Update auslaufen und deren letzte 3 Marktwertaenderungen jeweils mindestens `80000` betragen
- alternativ werden auch Spieler betrachtet, bei denen der letzte 1T-Anstieg mindestens `80000` ueber dem 2T-Anstieg liegt, auch wenn die 3-Tages-Regel nicht komplett erfuellt ist
- zusaetzlich werden Trendwenden mitgenommen: `2T` negativ und `1T` mindestens `80000` positiv
- fuer die Kalibrierung werden im Auto-Bid-Lauf trotzdem Prognosen fuer alle Marktspieler bis zum naechsten Marktwert-Update geloggt, auch wenn am Ende kein Gebot gesetzt wird
- vor dem Auto-Bid-Start waehlt man `50` oder `80` als Gebotsniveau, sofern `--bid-level` nicht direkt gesetzt wurde
- beim direkten Start der Datei, z.B. ueber den Play-Button in VS Code, startet dieser Auto-Bid-Modus automatisch
- nach jedem Lauf erscheint eine Review-Liste mit allen betroffenen Spielern, den 1T/2T/3T-Aenderungen, P50/P80 und dem Gebotsstatus
- die Review-Liste zeigt jetzt auch den konkreten Trigger je Spieler
- bestehende eigene Gebote werden standardmaessig nicht veraendert, sondern nur gemeldet

Wenn du trotz Direktstart nur die reine Liste sehen willst:

```powershell
python Anwendungsfälle\morgen_liste_gebote.py --list-only
```

Sicherer Testlauf ohne echte Gebote:

```powershell
python Anwendungsfälle\morgen_liste_gebote.py --league-name "Meine Liga" --auto-bid --dry-run
```

Echte Auto-Gebote:

```powershell
python Anwendungsfälle\morgen_liste_gebote.py --league-name "Meine Liga" --auto-bid
```

Fester Lauf mit dem sicheren 80. Perzentil:

```powershell
python Anwendungsfälle\morgen_liste_gebote.py --league-name "Meine Liga" --auto-bid --bid-level 80
```

Optional kannst du den 3-Tages-Filter oder das Gebotsniveau anpassen:

```powershell
python Anwendungsfälle\morgen_liste_gebote.py --league-name "Meine Liga" --auto-bid --min-three-day-rise 150000 --bid-level 50
```

Wenn vorhandene eigene Gebote automatisch auf den Zielwert angehoben werden sollen:

```powershell
python Anwendungsfälle\morgen_liste_gebote.py --league-name "Meine Liga" --auto-bid --update-existing
```

### GitHub Actions fuer taeglichen Lauf

Unter `.github/workflows/morgenliste-gebote.yml` liegt ein taeglicher GitHub-Action-Job fuer `morgen_liste_gebote.py`.

- Zeitplan: taeglich im Berlin-Fenster `22:10` bis `22:20`; dafuer gibt es zwei UTC-Cron-Slots fuer Sommer- und Winterzeit, von denen jeweils nur der lokal passende weiterlaeuft
- Zufallsstart: bei geplanten Laeufen wartet der Job nach dem Trigger auf einen zufaelligen Zeitpunkt im noch verbleibenden Fenster bis `22:20:59` Berlin-Zeit; wenn GitHub den Scheduler selbst spaet liefert, startet der Lauf sofort
- Modus: `--auto-bid --bid-level 80`
- Python: `3.11`
- Arbeitsverzeichnis: `kickbase_api/`

`workflow_dispatch` bleibt fuer manuelle Tests ohne zusaetzliche Zufallswartezeit direkt startbar.

Noetige Repository-Secrets in GitHub:

- `KICKBASE_LEAGUE_NAME`: exakter Name deiner Liga

Fuer den Login hast du zwei Optionen:

- bevorzugt ohne Token: `KICKBASE_EMAIL` und `KICKBASE_PASSWORD`
- alternativ: `KICKBASE_TOKEN`

Zum manuellen Testen kannst du den Workflow auch ueber `workflow_dispatch` direkt in GitHub starten.