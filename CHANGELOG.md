# LunaKalender – Änderungsprotokoll

## 1.3.9 – Toneinstellungen und Dokumentation
- Sound-Treiber-Auswahl auf PulseAudio und ALSA beschränkt.
- PulseAudio-Wiedergabe über `paplay`.
- ALSA-Geräteerkennung über `aplay -L` und `aplay -l`; verfügbare USB-Soundkarten und HDMI-Ausgänge werden angeboten, sofern Linux sie meldet.
- Auswahl des Sound-Treibers, ALSA-Ausgabegeräts und Ton-Aktivierung werden gespeichert.
- README vollständig wiederhergestellt und auf Version 1.3.9 aktualisiert.
- Debian-Paket und GitHub-Quellarchiv bleiben bei Version 1.3.9.

## 1.3.8
- Checkbox „Im Tray starten“: bei aktivierter Option startet LunaKalender bei der nächsten Benutzeranmeldung verborgen im Tray; das Hauptfenster bleibt geschlossen.
- Manueller Start über Desktop- oder Menüeintrag öffnet weiterhin das Hauptfenster normal sichtbar.

## 1.3.7 – Autostart im Tray
- Autostart im Tray: startet LunaKalender bei der Benutzeranmeldung direkt im Infobereich.
- Aktivierung schaltet das Tray-Symbol ein; Deaktivierung entfernt den benutzerspezifischen Autostart-Eintrag.
- Manueller Start öffnet weiterhin das Kalenderfenster.

## Version 1.3.6
- README vollständig neu strukturiert und Installationsanleitung aktualisiert.
- Funktionsübersicht, Tray-Popup, Sonnen-/Mondzeiten, Erinnerungen, Datenschutz und Paketbau klar dokumentiert.
- Programmversion und Debian-Paketversion auf 1.3.6 angeglichen; bestehende Funktionen unverändert.

## Version 1.3.5
- Tray-Popup um ca. 2 cm nach unten verschoben; Inhalt und Höhe unverändert.
- Sonnen-/Mondzeiten, Monatsnavigation und Tray-Bedienung unverändert.

## 1.3.4
- Tray-Popup wird weiter oberhalb der unteren Bildschirmkante platziert, damit Mondphase und vollständige Mondzeiten samt Schaltfläche nicht abgeschnitten werden.
- Popup-Höhe leicht vergrößert; Linksklick-Toggle und Rechtsklick-Kontextmenü bleiben unverändert.

## 1.3.3
- Tray-Popup vergrößert, damit Sonnen- und Mondaufgang sowie Sonnen- und Monduntergang vollständig sichtbar sind.
- Kompakte Monatsübersicht und bestehende Links-/Rechtsklick-Bedienung beibehalten.

## 1.3.2
- Linux-Tray von pystray auf GTK-StatusIcon umgestellt: Linksklick toggelt direkt das Sonnen-/Mond-Popup; Rechtsklick öffnet ausschließlich das Kontextmenü.
- GTK 3 Tray-Abhängigkeiten ergänzt.

# LunaKalender – Änderungsprotokoll

## Version 1.3.1
- Linksklick auf das Tray-Symbol öffnet direkt ein kompaktes Kalender-Popup; erneuter Linksklick schließt es wieder.
- Rechtsklick-Menü mit „Kalender anzeigen“ und „Beenden“ bleibt erhalten.
- Popup zeigt Monatsübersicht, Mondphasen und Sonnen-/Mondaufgang sowie -untergang für den gewählten Tag.
- Farbige Darstellung mit Sonnengelb, Mondblau und dunklem Nachtblau.

## 1.2.13
- Ferien- und Feiertagsdetails werden im rechten Infobereich umgebrochen. Lange Namen können die Kalender-Spalten nicht mehr horizontal zusammendrücken.
- Mindestbreite und Kalender-/Sonnen-Mond-Berechnungen unverändert.

# Änderungsprotokoll LunaKalender

## 1.2.12 – Kalenderoberfläche farblich verfeinert
- Gesamtes Kalenderfenster mit harmonisierter Farbpalette überarbeitet.
- Dunkelmodus mit tiefem Nachtblau, klaren Kontrasten und goldenen Akzenten.
- Hellmodus mit sanften Blau-/Weißtönen und warmen Akzenten.
- Kalenderfelder, Wochenenden, Buttons, Auswahlfelder und Terminliste optisch vereinheitlicht.
- Größere, klarere Tageszahlen und dezente Rahmen für bessere Lesbarkeit.
- Kalenderfunktionen und astronomische Berechnungen unverändert.


## 1.2.11 – Farbige Sonnen- und Mondanzeige
- Sonnenzeiten in warmem Sonnengelb hervorgehoben.
- Mondzeiten in hellem Silberblau dargestellt.
- Aufgangs- und Untergangszeilen farblich unterschieden; Berechnungslogik unverändert.

## 1.2.10 – Korrektur der Sonnen- und Mondzeiten
- Atmosphärische Refraktion bei der Berechnung berücksichtigt (Standard-Luftdruck 1010 hPa).
- Auf- und Untergangszeiten dadurch näher an üblichen veröffentlichten Ortszeiten.
- README und Paketversion aktualisiert.


## 1.2.9 – Sonnen- und Mondzeiten
- Neue Anzeige für Sonnenaufgang und Sonnenuntergang sowie Mondaufgang und Monduntergang.
- Koordinaten frei eingebbar; Standard: 51.7383, 9.0196.
- Berechnung mit PyEphem, Anzeige in lokaler Zeitzone und Sekundenauflösung.
- Dekorative Symbole für Sonne, Mond, Auf- und Untergang.

- Behoben: Erinnerungston läuft asynchron und blockiert die Oberfläche nicht.
- Behoben: Erinnerungs-Popup ist nicht mehr transient zum im Tray versteckten Hauptfenster und soll daher auch bei verborgenem Kalender sichtbar erscheinen.

# LunaKalender 1.2.8

## Neu in 1.2.8
- Terminerinnerung wird zur eingestellten Uhrzeit geprüft (Sekundenintervall).
- Popup zeigt Datum, Uhrzeit, Titel und Notiz des Termins.
- Erinnerungston wird bei aktivierter Tonoption zusammen mit dem Popup abgespielt.


- Erinnerungston für Termine mit Uhrzeit ergänzt; einmalige Auslösung pro Termin und Tag.
- Ton kann in „Ton-Einstellungen“ aktiviert/deaktiviert werden.
- Testton und Auswahl des ALSA-Ausgabegeräts/Soundkarten-Backends ergänzt.
- Einstellungen für Ton und Ausgabegerät werden gespeichert.
- Debian-Paket installiert `alsa-utils` für `aplay`.

# Changelog

## 1.2.5
- README: Installation des Debian-Pakets und Start aus dem Quellcode ohne `venv` ausführlich dokumentiert.
- `requirements.txt` für pip-basierte Installationen ergänzt; Debian-Systempakete bleiben der empfohlene Weg ohne virtuelle Umgebung.

## 1.2.4
- Feiertagsnamen und Schulferien werden beim Auswählen eines Tages im Detailbereich angezeigt.
- Bundesweite Feiertage haben Offline-Fallbacks.

# Änderungsprotokoll

## 1.2.3
- Neue Option „Jährlich wiederholen“ beim Anlegen und Bearbeiten von Terminen.
- Jährliche Termine erscheinen automatisch am gleichen Monatstag in künftigen Jahren.
- Der 29. Februar wird in Nicht-Schaltjahren am 28. Februar angezeigt.
- Tagesliste, Monatszähler und Infobereich berücksichtigen jährliche Wiederholungen.
- ICS-Export schreibt jährliche Wiederholungen als `RRULE:FREQ=YEARLY`.


## 1.2.2
- Terminbearbeitung in einem gemeinsamen Dialog zusammengefasst: Datum, Titel, Uhrzeit und mehrzeilige Notiz sind gleichzeitig sichtbar.
- Bestehende Termine können beim Bearbeiten auf ein anderes Datum verschoben werden.
- Datum und Uhrzeit werden vor dem Speichern validiert; Abbrechen lässt die ursprünglichen Daten unverändert.
- Tastaturbedienung ergänzt: Strg+Enter speichert, Esc bricht ab.
- Neue Termine verwenden denselben komfortablen Dialog wie die Bearbeitung.


## 1.2.1
- Fensterlayout auf ein gewichtetes Grid umgestellt: Kalender und Detailbereich teilen den verfügbaren Platz zuverlässig.
- Detailbereich wächst beim Maximieren mit; Terminliste und Aktionsbuttons bleiben im rechten Bereich sichtbar.
- Start- und Mindestgröße angepasst, damit die Bedienelemente nicht zusammengedrückt werden.


## 1.2.0
- ICS-Importmeldung unterscheidet importierte VEVENT-Einträge von materialisierten Einzelterminen.
- Mindestplatz für Terminliste und Aktionsbuttons im rechten Bereich erhöht; Beschriftungen erhalten die volle verfügbare Breite.


## 1.1.9
- Unbegrenzte ICS-Wiederholungen werden nur für ein rollierendes Jahr materialisiert statt für Jahrzehnte.
- Kalender und Terminbereich passen sich beim Ändern der Fenstergröße besser an; unnötige doppelte Resize-Callbacks entfernt.


## 1.1.8
- Unbegrenzte ICS-Wiederholungen werden bis zu einem definierten Zukunftshorizont als Kalendertermine importiert; COUNT/UNTIL bleiben berücksichtigt.
- Der Kalender bleibt nach dem Import beim zuvor ausgewählten Datum.


## 1.1.7
- ICS-Import springt nach dem Import zum ersten importierten Termin und zeigt ihn im Kalender samt Tagesliste an.
- Aktionsbereich erhält im Seitenpanel reservierten Platz; doppelte Resize-Callbacks entfernt.


## 1.1.6
- Unbegrenzte ICS-Wiederholungsregeln importieren nur ihren Starttermin statt einer erfundenen großen Anzahl.
- Tk-Neuzeichnung wird nach Größenänderungen angestoßen.


## 1.1.5
- Aktionsschaltflächen bleiben bei geringer Fensterhöhe erreichbar.
- ICS-Import begrenzt unbefristete Wiederholungsregeln und übernimmt Termine erst nach erfolgreicher Verarbeitung.


## 1.1.4
- Terminliste und Aktionsschaltflächen bleiben beim Maximieren sichtbar; die Liste gibt bei wenig Höhe Platz frei.


## 1.1.3
- Kalenderbereich behält beim Vergrößern den Platz für Terminliste und Aktionen.
- Bearbeiten und Löschen verwenden den ausgewählten Termin des angezeigten Tages.

## 1.1.2
- Terminliste zeigt nur Termine des ausgewählten Tages.
- Wiederkehrende iCalendar-Termine werden beim Import aufgelöst.


## 1.1.1
- Terminliste zeigt alle gespeicherten Termine chronologisch statt nur Termine des ausgewählten Tages.
- Bearbeiten und Löschen funktionieren für den in der Gesamtliste ausgewählten Termin.

## 1.1.0
- Import und Export von Terminen im iCalendar-Format (.ics).
- Import und Export von Kontakten im vCard-Format (.vcf); Kontakte lokal gespeichert.

## 1.0.10
- Infobereichssymbol zeigt das Tagesdatum und bei heutigen Terminen einen roten Zähler direkt im Symbol.

## 1.0.9
- Infobereichssymbol zeigt heutige Termine samt Uhrzeit im Tooltip und aktualisiert sich regelmäßig.

## 1.0.8
- Gesetzliche Feiertage mit Bundesland-Zuordnung und lokalem Offline-Cache.
- KMK-Schulferien werden im Monatsraster markiert.

## 1.0.7
- Verbesserte Erkennung und Verarbeitung der KMK-Ferienkalender.

## 1.0.6
- Ferienabruf lädt offizielle KMK-Ferienkalenderseite und verwendet dort verlinkte Kalender.

## 1.0.5
- Bundesland-Auswahl, automatischer Ferienabruf und Cache.

## 1.0.4
- Mondphasen-Symbole in Monatsansicht.

## 1.0.3
- Optionales Infobereichssymbol.

## 1.0.2
- Aktionsleiste neu angeordnet.

## 1.0.1
- Desktop-Eintrag, Dark Mode und lokale Terminverwaltung.