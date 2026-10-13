"""Import und Export für iCalendar-Termine und vCard-Kontakte."""
import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog


def _unfold(text):
    lines = []
    for line in text.replace('\r\n', '\n').replace('\r', '\n').split('\n'):
        if line.startswith((' ', '\t')) and lines:
            lines[-1] += line[1:]
        else:
            lines.append(line)
    return lines


def _unescape(value):
    return value.replace('\\n', '\n').replace('\\N', '\n').replace('\\,', ',').replace('\\;', ';').replace('\\\\', '\\')


def _escape(value):
    return str(value).replace('\\', '\\\\').replace('\n', '\\n').replace(';', '\\;').replace(',', '\\,')


def _recurrence_dates(start, rule):
    """Expand common RFC5545 recurrence rules into occurrence dates."""
    parts = dict(item.split("=", 1) for item in rule.split(";") if "=" in item)
    freq = parts.get("FREQ", "").upper()
    interval = max(1, int(parts.get("INTERVAL", "1")))
    count_raw = parts.get("COUNT", "")
    count = int(count_raw) if count_raw.isdigit() else None
    until_raw = parts.get("UNTIL", "")
    until = None
    if until_raw:
        try:
            until = datetime.strptime(until_raw[:8], "%Y%m%d").date()
        except ValueError:
            pass
    # Occurrences are stored as individual dates, so materialize open-ended
    # rules through a practical horizon instead of discarding future instances.
    if until is None and count is None:
        # The app stores each occurrence as a separate event. A rolling
        # one-year window avoids importing decades of artificial duplicates.
        until = date.today() + timedelta(days=366)
    weekdays = {"MO":0,"TU":1,"WE":2,"TH":3,"FR":4,"SA":5,"SU":6}
    dates=[]; candidate=start; scanned=0
    scan_limit = max(36600, (until - start).days + 1) if until else 36600
    while (count is None or len(dates)<count) and scanned<scan_limit:
        scanned+=1
        if until and candidate>until: break
        delta=(candidate-start).days
        match = ((freq=="DAILY" and delta%interval==0) or
                 (freq=="WEEKLY" and (delta//7)%interval==0 and candidate.weekday() in [weekdays[x] for x in parts.get("BYDAY", start.strftime("%a").upper()[:2]).split(",") if x in weekdays]) or
                 (freq=="MONTHLY" and ((candidate.year-start.year)*12+candidate.month-start.month)%interval==0 and candidate.day==start.day) or
                 (freq=="YEARLY" and (candidate.year-start.year)%interval==0 and candidate.month==start.month and candidate.day==start.day))
        if match: dates.append(candidate)
        candidate += timedelta(days=1)
    return dates

def _ics_import(app):
    path = filedialog.askopenfilename(parent=app.root, title='iCalendar-Datei importieren', filetypes=[('iCalendar', '*.ics'), ('Alle Dateien', '*')])
    if not path:
        return
    try:
        lines = _unfold(Path(path).read_text(encoding='utf-8-sig'))
        staged = {}
        added = 0
        imported_events = 0
        current = None
        for line in lines:
            if line == 'BEGIN:VEVENT':
                current = {}
            elif line == 'END:VEVENT' and current is not None:
                raw = current.get('DTSTART', '')
                start = re.sub(r'^.*:', '', raw)
                if len(start) >= 8 and start[:8].isdigit():
                    day = datetime.strptime(start[:8], '%Y%m%d').date()
                    title = _unescape(current.get('SUMMARY', 'Termin')) or 'Termin'
                    note = _unescape(current.get('DESCRIPTION', ''))
                    time = ''
                    if 'T' in start and len(start) >= 15:
                        time = start[9:11] + ':' + start[11:13]
                    imported_events += 1
                    dates = _recurrence_dates(day, current.get('RRULE', '')) if current.get('RRULE') else [day]
                    exdates = set()
                    for excluded in current.get('EXDATE', '').split(','):
                        try: exdates.add(datetime.strptime(re.sub(r'^.*:', '', excluded)[:8], '%Y%m%d').date())
                        except ValueError: pass
                    for occurrence in dates:
                        if occurrence in exdates: continue
                        staged.setdefault(occurrence.isoformat(), []).append({'title': title, 'time': time, 'note': note})
                        added += 1
                current = None
            elif current is not None and ':' in line:
                key, value = line.split(':', 1)
                key = key.split(';', 1)[0].upper()
                if key in ('DTSTART', 'SUMMARY', 'DESCRIPTION', 'RRULE', 'EXDATE'):
                    current[key] = value
        if added:
            for day, imported in staged.items():
                app.events.setdefault(day, []).extend(imported)
            for items in app.events.values():
                items.sort(key=lambda event: event.get('time', ''))
            app._save(); app._draw_month(); app._show_events(); app._update_tray_today()
        messagebox.showinfo('Import abgeschlossen', f'{imported_events} ICS-Termineinträge importiert; {added} einzelne Termine im Kalender angelegt.', parent=app.root)
    except (OSError, UnicodeError, ValueError) as exc:
        messagebox.showerror('Import fehlgeschlagen', str(exc), parent=app.root)


def _ics_export(app):
    path = filedialog.asksaveasfilename(parent=app.root, title='iCalendar-Datei exportieren', defaultextension='.ics', filetypes=[('iCalendar', '*.ics')])
    if not path:
        return
    rows = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//LunaKalender//1.1.0//DE']
    for day, events in sorted(app.events.items()):
        try:
            d = date.fromisoformat(day)
        except ValueError:
            continue
        for i, event in enumerate(events):
            stamp = d.strftime('%Y%m%d')
            time = event.get('time', '')
            start = stamp + ('T' + time.replace(':', '') + '00' if time else '')
            rows += ['BEGIN:VEVENT', f'UID:{stamp}-{i}@lunakalender', f'DTSTAMP:{datetime.utcnow():%Y%m%dT%H%M%SZ}', f'DTSTART:{start}', f'SUMMARY:{_escape(event.get("title", "Termin"))}']
            if event.get('annual', False):
                rows.append('RRULE:FREQ=YEARLY')
            if event.get('note'):
                rows.append('DESCRIPTION:' + _escape(event['note']))
            if not time:
                rows.append('END:VEVENT')
            else:
                rows[-2:-2] = ['END:VEVENT'] if False else []
                rows.append('END:VEVENT')
    rows.append('END:VCALENDAR')
    try:
        Path(path).write_text('\r\n'.join(rows) + '\r\n', encoding='utf-8')
        messagebox.showinfo('Export abgeschlossen', 'Termine wurden als iCalendar-Datei exportiert.', parent=app.root)
    except OSError as exc:
        messagebox.showerror('Export fehlgeschlagen', str(exc), parent=app.root)


def _contacts_file(app):
    return Path(app.DATA_DIR if hasattr(app, 'DATA_DIR') else Path.home() / '.local/share/lunakalender') / 'contacts.json'


def _read_contacts(app):
    try:
        data = json.loads(_contacts_file(app).read_text(encoding='utf-8'))
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _vcf_import(app):
    path = filedialog.askopenfilename(parent=app.root, title='vCard-Kontakte importieren', filetypes=[('vCard', '*.vcf'), ('Alle Dateien', '*')])
    if not path:
        return
    try:
        lines = _unfold(Path(path).read_text(encoding='utf-8-sig'))
        contacts, current = [], None
        for line in lines:
            if line.upper() == 'BEGIN:VCARD':
                current = {}
            elif line.upper() == 'END:VCARD' and current is not None:
                if current.get('FN') or current.get('N'):
                    contacts.append(current)
                current = None
            elif current is not None and ':' in line:
                key, value = line.split(':', 1)
                key = key.split(';', 1)[0].upper()
                if key in ('FN', 'N', 'TEL', 'EMAIL', 'ORG', 'NOTE', 'ADR'):
                    current.setdefault(key, []).append(_unescape(value))
        existing = _read_contacts(app)
        existing.extend(contacts)
        target = _contacts_file(app)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding='utf-8')
        messagebox.showinfo('Import abgeschlossen', f'{len(contacts)} Kontakt(e) importiert. Kontakte sind lokal gespeichert.', parent=app.root)
    except (OSError, UnicodeError, ValueError) as exc:
        messagebox.showerror('Import fehlgeschlagen', str(exc), parent=app.root)


def _vcf_export(app):
    contacts = _read_contacts(app)
    if not contacts:
        messagebox.showinfo('Keine Kontakte', 'Es sind noch keine importierten Kontakte vorhanden.', parent=app.root)
        return
    path = filedialog.asksaveasfilename(parent=app.root, title='vCard-Kontakte exportieren', defaultextension='.vcf', filetypes=[('vCard', '*.vcf')])
    if not path:
        return
    rows = []
    for contact in contacts:
        rows += ['BEGIN:VCARD', 'VERSION:3.0']
        for key in ('FN', 'N', 'ORG', 'TEL', 'EMAIL', 'ADR', 'NOTE'):
            for value in contact.get(key, []):
                rows.append(f'{key}:{_escape(value)}')
        rows.append('END:VCARD')
    try:
        Path(path).write_text('\r\n'.join(rows) + '\r\n', encoding='utf-8')
        messagebox.showinfo('Export abgeschlossen', f'{len(contacts)} Kontakt(e) exportiert.', parent=app.root)
    except OSError as exc:
        messagebox.showerror('Export fehlgeschlagen', str(exc), parent=app.root)


def install_exchange(app):
    import tkinter as tk
    from tkinter import ttk
    menu = tk.Menu(app.root)
    transfer = tk.Menu(menu, tearoff=False)
    transfer.add_command(label='Termine aus ICS importieren…', command=lambda: _ics_import(app))
    transfer.add_command(label='Termine als ICS exportieren…', command=lambda: _ics_export(app))
    transfer.add_separator()
    transfer.add_command(label='Kontakte aus VCF importieren…', command=lambda: _vcf_import(app))
    transfer.add_command(label='Kontakte als VCF exportieren…', command=lambda: _vcf_export(app))
    menu.add_cascade(label='Import/Export', menu=transfer)
    app.root.configure(menu=menu)
