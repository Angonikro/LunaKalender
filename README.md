# LunaKalender 1.3.8

Ein grafischer Monatskalender für Linux mit lokaler Terminverwaltung, Erinnerungen, Schulferien, Feiertagen sowie Sonnen- und Mondinformationen. Für Debian und Raspberry Pi ist die Installation über das Debian-Paket der einfachste Weg.

## Funktionen

- Monatsansicht mit Navigation und Hervorhebung des ausgewählten Tages
- Lokale Termine, Notizen und Terminerinnerungen mit optionalem Erinnerungston
- Wiederkehrende jährliche Termine
- Schulferien und gesetzliche Feiertage für das ausgewählte Bundesland
- Dunkel- und Hellmodus
- Infobereichssymbol (Tray): Linksklick öffnet das kompakte Sonnen-/Mond-Popup; ein weiterer Linksklick schließt es. Rechtsklick öffnet das Kontextmenü.
- Popup mit Monatsübersicht, Mondphasen sowie Sonnenaufgang, Sonnenuntergang, Mondaufgang und Monduntergang für den ausgewählten Tag
- Einstellbare Koordinaten; Standard: Breitengrad `51.7383`, Längengrad `9.0196`
- Import und Export von Terminen als iCalendar-Dateien (`.ics`) und Kontakten als vCard (`.vcf`)
- Lokale Speicherung von Einstellungen, Terminen und Kontakten



### Im Tray starten (ab 1.3.8)

Aktiviere oben „Im Tray starten“, damit LunaKalender bei der nächsten Linux-Anmeldung automatisch **nur im Tray** startet; das Hauptfenster bleibt dabei verborgen. Ein normaler Start über den Desktop- oder Menüeintrag öffnet das Kalenderfenster weiterhin ganz normal. Zum Abschalten des automatischen Starts das Häkchen wieder entfernen.

## Sonnen- und Mondzeiten

Im Hauptkalender über **„☀ Sonne & 🌙 Mond“** oder im Tray-Popup werden die Auf- und Untergangszeiten für den ausgewählten Tag angezeigt. Breitengrad und Längengrad sind änderbar; die Standardkoordinaten sind `51.7383, 9.0196`. Die Berechnung verwendet PyEphem und zeigt die Zeiten in der lokalen Zeitzone an. Atmosphärische Refraktion wird mit einem Standard-Luftdruck von 1010 hPa berücksichtigt. Tatsächliche Zeiten können durch Wetter, Höhenlage und den örtlichen Horizont leicht abweichen. Wenn ein Himmelskörper am gewählten Ort nicht auf- oder untergeht, wird dies entsprechend angezeigt.

## Erinnerungen und Ton

Termine mit Uhrzeit können zur eingestellten Zeit eine Erinnerung mit Titel und Notiz anzeigen. Der Erinnerungston lässt sich in **„Ton-Einstellungen“** aktivieren oder deaktivieren; **„Testton“** prüft die Ausgabe. Wenn `alsa-utils` installiert ist, kann ein Ausgabegerät aus der von `aplay -L` gelieferten Liste gewählt werden. `default` verwendet die Linux-Standardausgabe. Termine ohne Uhrzeit lösen keinen Erinnerungston aus. Damit Erinnerungen im Tray-Betrieb ausgeführt werden, muss LunaKalender weiterlaufen.



Das Paket wird im Unterordner `dist` erstellt. Zum Bauen wird `dpkg-deb` benötigt.

## Datenspeicherung und Datenschutz

Termine, Einstellungen und Kontakte werden lokal gespeichert. Für Ferien- und Feiertagsdaten kann LunaKalender bei Bedarf HTTPS-Anfragen an die KMK-Seite und deren Kalender sowie an `date.nager.at` senden. Mondphasen und Sonnen-/Mondzeiten werden lokal berechnet.

## Dateien

- `main.py` – Kalenderoberfläche und Hauptfunktionen
- `exchange.py` – Import-/Exportfunktionen
- `requirements.txt` – Python-Abhängigkeiten für eine pip-Installation in einer virtuellen Umgebung
- `build_deb.sh` – Skript zum Erstellen des Debian-Pakets
- `debian/` – Desktop-Datei und Programmsymbol

## Hinweise

## Installation auf Debian / Raspberry Pi (empfohlen)

Lade `lunakalender_1.3.8_all.deb` herunter und installiere es im Download-Ordner:

```bash
sudo apt install ./lunakalender_1.3.8_all.deb
```

Das Paket installiert die benötigten Systemabhängigkeiten. Eine virtuelle Umgebung (`venv`) ist nicht erforderlich.

## Aus dem GitHub-Quellcode starten

Wer das Repository klont oder das GitHub-ZIP herunterlädt, hat **kein Debian-Paket**. Die benötigten Abhängigkeiten müssen deshalb selbst installiert werden. Unter Debian und Raspberry Pi OS ist die Installation über `apt` der einfachste Weg.

### Variante A: Systempakete verwenden (empfohlen für Debian/Raspberry Pi)

```bash
sudo apt update
sudo apt install python3 python3-tk python3-gi gir1.2-gtk-3.0 python3-pil python3-ephem alsa-utils
```

Repository klonen und starten:

```bash
git clone <REPOSITORY-URL>
cd LunaKalender
python3 main.py
```

Alternativ das GitHub-ZIP entpacken und im entpackten Ordner `LunaKalender` starten:

```bash
python3 main.py
```
## Debian-Paket selbst bauen

Im Projektordner:

```bash
./build_deb.sh
```

Bei dieser Variante ist **kein `pip install -r requirements.txt` nötig**, weil Pillow und PyEphem über die Debian-Systempakete installiert werden. `tkinter` und die GTK-Bindings (`python3-gi`) müssen ebenfalls über `apt` installiert werden; sie lassen sich nicht zuverlässig durch `requirements.txt` ersetzen.

### Warum kein virtuelles Python-Environment?

Die folgenden Schritte verwenden die von Debian bereitgestellten Systempakete. Eine virtuelle Umgebung (`venv`) und `pip install` sind dafür nicht nötig. So werden Tkinter, GTK und die Python-Bibliotheken passend zum installierten Debian-/Raspberry-Pi-OS-System eingerichtet.

Für Debian und Raspberry Pi wird die Paketinstallation mit Systemabhängigkeiten empfohlen. Wenn du bewusst `pip` verwenden möchtest, nutze dafür eine virtuelle Umgebung, um die systemweite Python-Installation nicht zu verändern.

73 de DO2QG Andreas
