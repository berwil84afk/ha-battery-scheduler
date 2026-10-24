# Battery Scheduler für Home Assistant

Steuert einen Batteriespeicher (z. B. Balkonspeicher mit 800-W-Grenze):

- **Laden** im einstellbaren Zeitfenster mit fester Leistung, bis die *Maximalladung* erreicht ist.
- **Entladen** im einstellbaren Zeitfenster, geregelt auf den aktuellen Netzbezug
  (Nulleinspeisung), bis die *Mindestladung* erreicht ist.
- Lade- und Entladeleistung sind einzeln einstellbar und hart auf **800 W** begrenzt.

## Installation

1. Ordner `custom_components/battery_scheduler` nach `<config>/custom_components/` kopieren
   (oder das Repository als benutzerdefiniertes HACS-Repository hinzufügen).
2. Home Assistant neu starten.
3. *Einstellungen → Geräte & Dienste → Integration hinzufügen → „Battery Scheduler“*.

## Einrichtung

| Feld | Bedeutung |
|---|---|
| Ladezustand | Sensor mit dem SoC des Speichers in % |
| Netzleistung | Sensor mit dem aktuellen Stromimport (W oder kW). **Bezug positiv, Einspeisung negativ** – sonst „Netzsensor invertieren“ aktivieren |
| Ladeleistung-Entität | `number`/`input_number`, die die Ladeleistung in W setzt |
| Entladeleistung-Entität | `number`/`input_number`, die die Entladeleistung in W setzt. Kann dieselbe Entität wie oben sein: dann wird *Entladen positiv, Laden negativ* geschrieben (mit „Gemeinsamen Sollwert invertieren“ umgekehrt) |
| Ziel-Netzbezug | Restbezug, auf den geregelt wird (Standard 10 W, verhindert Einspeisung) |
| Regelintervall | Sekunden zwischen zwei Regelschritten (Standard 10 s) |

Alles lässt sich später über *Konfigurieren* ändern.

## Entitäten

| Entität | Typ |
|---|---|
| Automatik | Schalter – aus = Integration greift nicht ein (setzt beim Ausschalten einmal 0 W) |
| Mindestladung / Maximalladung | Zahl, % (Mindestabstand 5 %) |
| Maximale Lade- / Entladeleistung | Zahl, 0–800 W |
| Laden Start / Ende, Entladen Start / Ende | Uhrzeit (Fenster über Mitternacht möglich) |
| Betriebsmodus | Sensor: Bereit, Lädt, Voll, Entlädt, Mindestladung erreicht, Deaktiviert, Fehler |
| Lade- / Entladesollwert | Sensor, W |

Die Einstellungen bleiben über Neustarts erhalten.

## Regelverhalten

- Überschneiden sich die Fenster, hat **Laden Vorrang**.
- Außerhalb beider Fenster werden Lade- und Entladeleistung auf 0 gesetzt.
- Entladen: `neuer Sollwert = alter Sollwert + Netzbezug − Ziel-Netzbezug`,
  begrenzt auf 0 … maximale Entladeleistung. Änderungen unter 10 W werden nicht geschrieben.
- SoC-Hysterese 2 %: Nach „Voll“ wird erst unter Max − 2 % wieder geladen, nach
  „Mindestladung erreicht“ erst über Min + 2 % wieder entladen.
- Ist der SoC- oder Netzsensor nicht verfügbar, geht die Steuerung in „Fehler“ und setzt 0 W.
- Die Sollwerte werden zusätzlich auf `min`/`max` der Ziel-Entität begrenzt.
