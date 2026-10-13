# LunaKalender – Änderungsprotokoll

## 1.4.0 – Mondphasen und Tray-Popup
- Verständlichere Mondphasen-Namen: „Halbmond (zunehmend)“ und „Halbmond (abnehmend)“.
- Mondphasen als eigene monochrome Grafiken gezeichnet, unabhängig von Emoji-Schriftarten.
- Beleuchtungsrichtung korrigiert: zunehmende Phasen rechts hell, abnehmende links hell.
- Phasenzuordnung anhand astronomischer Referenzdaten geprüft: 13.10.2026 zunehmende Sichel, 26.10.2026 Vollmond.
- Tray-Popup auf 420 Pixel verbreitert.
- Kalender im Tray-Popup in einem gleichmäßigen Sieben-Spalten-Raster ausgerichtet.
- Versionsnummer bleibt 1.4.0.

## 1.3.9 – Toneinstellungen und Dokumentation
- Sound-Treiber-Auswahl auf PulseAudio und ALSA beschränkt.
- PulseAudio-Wiedergabe über `paplay`.
- ALSA-Geräteerkennung über `aplay -L` und `aplay -l`.
- Sound-Treiber, ALSA-Ausgabegerät und Ton-Aktivierung werden gespeichert.

## 1.3.8 – Autostart im Tray
- Option „Im Tray starten“ startet die Anwendung bei der nächsten Anmeldung verborgen im Tray.
- Manueller Start öffnet weiterhin das Hauptfenster.

## 1.3.7 – Autostart im Tray
- Autostart bei Benutzeranmeldung und Verwaltung des benutzerspezifischen Autostart-Eintrags.

## 1.3.6 – Dokumentation
- README und Installationsanleitung überarbeitet.

## 1.3.5 – Tray-Popup
- Position des Tray-Popups angepasst.

## 1.3.4 – Tray-Popup
- Popup-Position und -Höhe angepasst, damit Inhalte sichtbar bleiben.

## 1.3.3 – Tray-Popup
- Popup vergrößert, um Monatsübersicht und Sonnen-/Mondzeiten sichtbar zu halten.

## 1.3.2 – Tray-Integration
- Linksklick öffnet bzw. schließt das Popup; Rechtsklick öffnet das Kontextmenü.

## 1.3.1 – Tray-Kalender
- Kalender-Popup mit Monatsnavigation, Mondphasen und Sonnen-/Mondzeiten.

## 1.2.13 – Termin- und Feiertagsanzeige
- Lange Ferien- und Feiertagsnamen werden umgebrochen, ohne Kalender-Spalten zusammenzudrücken.
