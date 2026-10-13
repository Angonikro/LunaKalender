# LunaKalender 1.3.9 – Release Notes

## Änderungen
- Toneinstellungen auf PulseAudio und ALSA reduziert.
- PulseAudio-Wiedergabe über `paplay`.
- ALSA-Geräteliste wird mit `aplay -L` und `aplay -l` ermittelt; USB-Soundkarten und HDMI erscheinen, sofern vom System erkannt.
- Treiber- und Geräteauswahl sowie die Aktivierung des Erinnerungstons werden gespeichert.
- Vollständige README und bereinigtes CHANGELOG.

## Installation
Debian/Raspberry Pi: `sudo apt install ./lunakalender_1.3.9_all.deb`

Die tatsächliche Audioausgabe sollte nach der Installation mit „Testton“ geprüft werden.
