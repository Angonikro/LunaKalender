#!/usr/bin/env python3
"""LunaKalender – Monatskalender mit Terminen, Mondphasen und optionalem Tray."""
import calendar
import math
import shutil
import struct
import subprocess
import tempfile
import wave
import json
import os
import sys
import re
import threading
import tkinter as tk
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, time, timezone
from html.parser import HTMLParser
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk
from urllib.parse import urljoin

APP_NAME = "LunaKalender"
VERSION = "1.3.8"
DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "lunakalender"
EVENTS_FILE = DATA_DIR / "events.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
HOLIDAY_CACHE_FILE = DATA_DIR / "school_holidays.json"
PUBLIC_HOLIDAY_CACHE_FILE = DATA_DIR / "public_holidays.json"
HOLIDAY_API = "https://date.nager.at/api/v3/PublicHolidays/{year}/DE"
STATE_CODES = {"Baden-Württemberg":"DE-BW", "Bayern":"DE-BY", "Berlin":"DE-BE", "Brandenburg":"DE-BB", "Bremen":"DE-HB", "Hamburg":"DE-HH", "Hessen":"DE-HE", "Mecklenburg-Vorpommern":"DE-MV", "Niedersachsen":"DE-NI", "Nordrhein-Westfalen":"DE-NW", "Rheinland-Pfalz":"DE-RP", "Saarland":"DE-SL", "Sachsen":"DE-SN", "Sachsen-Anhalt":"DE-ST", "Schleswig-Holstein":"DE-SH", "Thüringen":"DE-TH"}
KMK_URL = "https://www.kmk.org/service/ferienregelung/ferienkalender.html"
STATES = ("Baden-Württemberg", "Bayern", "Berlin", "Brandenburg", "Bremen", "Hamburg", "Hessen", "Mecklenburg-Vorpommern", "Niedersachsen", "Nordrhein-Westfalen", "Rheinland-Pfalz", "Saarland", "Sachsen", "Sachsen-Anhalt", "Schleswig-Holstein", "Thüringen")
SYNODIC_MONTH = 29.530588853
REFERENCE_NEW_MOON = 2000.0
PHASES = ("🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘")
PHASE_NAMES = ("Neumond", "Zunehmende Sichel", "Erstes Viertel", "Zunehmender Mond", "Vollmond", "Abnehmender Mond", "Letztes Viertel", "Abnehmende Sichel")

class CalendarLinks(HTMLParser):
    """Liest Kalender-Links und deren Linktexte aus dem KMK-HTML."""
    def __init__(self):
        super().__init__(); self.links = []; self._href = None; self._text = []
    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a": self._href = dict(attrs).get("href"); self._text = []
    def handle_data(self, data):
        if self._href is not None: self._text.append(data)
    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            self.links.append((self._href, " ".join("".join(self._text).split()))); self._href = None; self._text = []

def moon_phase(day):
    ordinal = day.toordinal() + 1721424.5; age = (ordinal - REFERENCE_NEW_MOON) % SYNODIC_MONTH
    index = int((age / SYNODIC_MONTH * 8 + 0.5)) % 8
    return PHASES[index], PHASE_NAMES[index]

def parse_ical(text):
    """Liest ganztägige VEVENT-Termine aus iCalendar-Text (auch gefaltete Zeilen)."""
    lines = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if line.startswith((" ", "\t")) and lines: lines[-1] += line[1:]
        else: lines.append(line)
    events, event = [], None
    for line in lines:
        if line == "BEGIN:VEVENT": event = {}
        elif line == "END:VEVENT" and event is not None:
            try:
                start = datetime.strptime(event["DTSTART"], "%Y%m%d").date()
                raw_end = event.get("DTEND"); end = datetime.strptime(raw_end, "%Y%m%d").date() - timedelta(days=1) if raw_end else start
                if end >= start: events.append((start, end, event.get("SUMMARY", "Schulferien")))
            except (KeyError, ValueError): pass
            event = None
        elif event is not None and ":" in line:
            key, value = line.split(":", 1); key = key.split(";", 1)[0]
            if key in ("DTSTART", "DTEND", "SUMMARY"): event[key] = value.replace("\\,", ",").replace("\\;", ";").replace("\\n", " ")
    return events

def _state_match(label):
    normalized = re.sub(r"[^a-z]", "", label.casefold())
    return next((state for state in sorted(STATES, key=len, reverse=True) if re.sub(r"[^a-z]", "", state.casefold()) in normalized), None)

class LunaKalender:
    def __init__(self, root):
        self.root = root; self.root.title(f"{APP_NAME} {VERSION}"); self.root.geometry("1100x700"); self.root.minsize(900, 560)
        self.today = date.today(); self.year, self.month = self.today.year, self.today.month; self.selected = self.today
        self.events = self._load_json(EVENTS_FILE, {})
        settings = self._load_json(SETTINGS_FILE, {"dark": False, "tray": False, "state": "", "sound_enabled": False, "sound_device": "default"})
        self.autostart_enabled = (Path.home() / ".config/autostart/lunakalender.desktop").exists()
        self.dark = bool(settings.get("dark", False)); self.tray_enabled = bool(settings.get("tray", False)); self.state = settings.get("state", "")
        self.sound_enabled = bool(settings.get("sound_enabled", False)); self.sound_device = str(settings.get("sound_device", "default")); self._alerted_events = set()
        self.latitude = str(settings.get("latitude", "51.7383")); self.longitude = str(settings.get("longitude", "9.0196"))
        if self.state not in STATES: self.state = ""
        self.holiday_cache = self._load_json(HOLIDAY_CACHE_FILE, {}); self.holidays = self.holiday_cache.get(self.state, []) if self.state else []
        self.public_holiday_cache = self._load_json(PUBLIC_HOLIDAY_CACHE_FILE, {}); self.public_holidays = self.public_holiday_cache.get(self.state, []) if self.state else []
        self.tray_icon = None; self._tray_popup = None; self._visible_event_refs = []; self._build(); self.root.bind("<Configure>", self._on_root_configure, add="+"); self.root.protocol("WM_DELETE_WINDOW", self._on_close); self._apply_theme(); self._draw_month(); self._show_events()
        if self.state: self._refresh_holidays(); self._refresh_public_holidays(self.state)
        if self.tray_enabled:
            self._start_tray(); self._update_tray_today()
        if "--tray" in sys.argv and self.tray_icon:
            self.root.withdraw()
        self._schedule_tray_refresh(); self._schedule_reminder_check()

    @staticmethod
    def _load_json(path, default):
        try:
            with path.open(encoding="utf-8") as f: value = json.load(f)
            return value if isinstance(value, type(default)) else default
        except (OSError, ValueError): return default
    def _save_settings(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True); SETTINGS_FILE.write_text(json.dumps({"dark": self.dark, "tray": self.tray_enabled, "state": self.state, "sound_enabled": self.sound_enabled, "sound_device": self.sound_device, "latitude": self.latitude, "longitude": self.longitude}), encoding="utf-8")
    def _save_holiday_cache(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True); tmp = HOLIDAY_CACHE_FILE.with_suffix(".tmp"); tmp.write_text(json.dumps(self.holiday_cache, ensure_ascii=False), encoding="utf-8"); tmp.replace(HOLIDAY_CACHE_FILE)
    def _fetch_kmk_ics(self, state):
        req = urllib.request.Request(KMK_URL, headers={"User-Agent": f"{APP_NAME}/{VERSION}", "Accept": "text/html"})
        with urllib.request.urlopen(req, timeout=25) as response: page = response.read(2_000_000).decode("utf-8", "replace")
        parser = CalendarLinks(); parser.feed(page); matches = [(href, label) for href, label in parser.links if href and _state_match(label) == state]
        if not matches: raise ValueError(f"Auf der KMK-Seite wurde kein Kalender-Link für {state} gefunden.")
        req = urllib.request.Request(urljoin(KMK_URL, matches[0][0]), headers={"User-Agent": f"{APP_NAME}/{VERSION}", "Accept": "text/calendar, text/plain, */*"})
        with urllib.request.urlopen(req, timeout=25) as response: raw = response.read(2_000_000)
        content = raw.decode("utf-8-sig", "replace")
        if "BEGIN:VCALENDAR" not in content.upper(): raise ValueError("Die KMK-Antwort ist kein gültiger iCalendar-Kalender.")
        entries = [[a.isoformat(), b.isoformat(), title] for a, b, title in parse_ical(content)]
        if not entries: raise ValueError("Der KMK-Kalender enthält keine lesbaren ganztägigen Ferien.")
        return entries
    def _fetch_public_holidays(self, state):
        code = STATE_CODES[state]; results = []
        for year in range(self.year - 1, self.year + 2):
            req = urllib.request.Request(HOLIDAY_API.format(year=year), headers={"User-Agent": f"{APP_NAME}/{VERSION}", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=20) as response: data = json.loads(response.read(1_000_000).decode("utf-8"))
            for item in data:
                subdivisions = item.get("counties")
                if subdivisions is None or code in subdivisions: results.append([item["date"], item.get("localName") or item.get("name", "Feiertag")])
        return results
    def _refresh_public_holidays(self, state):
        if not state: self.public_holidays = []; return
        def worker():
            try: entries = self._fetch_public_holidays(state); self.root.after(0, lambda: self._public_holidays_loaded(state, entries, None))
            except Exception as exc: self.root.after(0, lambda err=str(exc): self._public_holidays_loaded(state, None, err))
        threading.Thread(target=worker, daemon=True).start()
    def _public_holidays_loaded(self, state, entries, error):
        if self.state != state: return
        if entries is not None:
            self.public_holiday_cache[state] = entries; self.public_holidays = entries; DATA_DIR.mkdir(parents=True, exist_ok=True); tmp = PUBLIC_HOLIDAY_CACHE_FILE.with_suffix(".tmp"); tmp.write_text(json.dumps(self.public_holiday_cache, ensure_ascii=False), encoding="utf-8"); tmp.replace(PUBLIC_HOLIDAY_CACHE_FILE); self.holiday_status.configure(text=f"Ferien und Feiertage: {state} · aktualisiert")
        else:
            self.public_holidays = self.public_holiday_cache.get(state, [])
            if not self.public_holidays: self.holiday_status.configure(text=f"Feiertage offline nicht verfügbar: {error}")
        self._draw_month(); self._show_events()
    def _refresh_holidays(self):
        state = self.state
        if not state: return
        self.holiday_status.configure(text=f"Ferien: lade KMK-Daten für {state} …")
        def worker():
            try: entries = self._fetch_kmk_ics(state); self.root.after(0, lambda: self._holidays_loaded(state, entries, None))
            except Exception as exc: self.root.after(0, lambda err=str(exc): self._holidays_loaded(state, None, err))
        threading.Thread(target=worker, daemon=True).start()
    def _holidays_loaded(self, state, entries, error):
        if self.state != state: return
        if entries is not None: self.holiday_cache[state] = entries; self.holidays = entries; self._save_holiday_cache(); self.holiday_status.configure(text=f"Ferien: {state} · KMK-Daten aktualisiert")
        else: self.holidays = self.holiday_cache.get(state, []); self.holiday_status.configure(text=(f"Ferien: {state} · Offline-Cache" if self.holidays else f"Ferien nicht verfügbar: {error}"))
        self._draw_month(); self._show_events()
    def _build(self):
        top = ttk.Frame(self.root, padding=10); top.pack(fill="x")
        ttk.Button(top, text="‹", width=4, command=lambda: self._shift(-1)).pack(side="left"); ttk.Button(top, text="Heute", command=self._go_today).pack(side="left", padx=5); ttk.Button(top, text="›", width=4, command=lambda: self._shift(1)).pack(side="left")
        self.title_label = ttk.Label(top, text="", font=("TkDefaultFont", 16, "bold")); self.title_label.pack(side="left", padx=14); self.state_var = tk.StringVar(value=self.state)
        self.state_box = ttk.Combobox(top, textvariable=self.state_var, values=STATES, state="readonly", width=19); self.state_box.pack(side="right", padx=(8, 0)); self.state_box.bind("<<ComboboxSelected>>", self._state_changed)
        self.tray_var = tk.BooleanVar(value=self.tray_enabled); ttk.Checkbutton(top, text="Infobereichssymbol", variable=self.tray_var, command=self._toggle_tray).pack(side="right", padx=(8, 0)); self.autostart_var = tk.BooleanVar(value=self.autostart_enabled); ttk.Checkbutton(top, text="Im Tray starten", variable=self.autostart_var, command=self._toggle_autostart).pack(side="right", padx=(8, 0)); self.dark_button = ttk.Button(top, text="Dark Mode", command=self._toggle_dark); self.dark_button.pack(side="right"); ttk.Button(top, text="Ton-Einstellungen", command=self._sound_settings).pack(side="right", padx=6)
        body = ttk.Frame(self.root, padding=(10, 0, 10, 10)); body.pack(fill="both", expand=True)
        # Weighted grid keeps both calendar and detail panel visible when maximized.
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=5, minsize=560)
        body.grid_columnconfigure(1, weight=2, minsize=300)
        self.calendar_frame = ttk.Frame(body); self.day_buttons = []
        for col, name in enumerate(("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")):
            ttk.Label(self.calendar_frame, text=name, anchor="center", font=("TkDefaultFont", 10, "bold")).grid(row=0, column=col, sticky="nsew", padx=2, pady=4); self.calendar_frame.columnconfigure(col, weight=1, uniform="days")
        for row in range(1, 7):
            self.calendar_frame.rowconfigure(row, weight=1, uniform="weeks")
            for col in range(7):
                btn = tk.Button(self.calendar_frame, text="", relief="flat", command=lambda r=row, c=col: self._select_cell(r, c)); btn.grid(row=row, column=col, sticky="nsew", padx=2, pady=2); self.day_buttons.append(btn)
        side = ttk.Frame(body, padding=(14, 0, 0, 0)); side.grid(row=0, column=1, sticky="nsew")
        self.calendar_frame.grid(row=0, column=0, sticky="nsew")
        self.selected_label = ttk.Label(side, text="", font=("TkDefaultFont", 13, "bold")); self.phase_label = ttk.Label(side, text="", font=("TkDefaultFont", 11), wraplength=270, justify="left"); self.holiday_status = ttk.Label(side, text="Ferien: Bundesland auswählen", wraplength=260, justify="left")
        self.event_list = tk.Listbox(side, height=8, activestyle="none", exportselection=False); side.grid_columnconfigure(0, weight=1); side.grid_rowconfigure(3, weight=1)
        self.selected_label.grid(row=0, column=0, sticky="ew", pady=(4, 8)); self.phase_label.grid(row=1, column=0, sticky="ew", pady=(0, 8)); self.holiday_status.grid(row=2, column=0, sticky="ew", pady=(0, 6)); self.event_list.grid(row=3, column=0, sticky="nsew")
        actions = ttk.Frame(side); actions.grid(row=4, column=0, sticky="sew", pady=(8, 4)); actions.columnconfigure(0, weight=1, uniform="actions"); actions.columnconfigure(1, weight=1, uniform="actions")
        ttk.Button(actions, text="Neu", command=self._add_event).grid(row=0, column=0, sticky="ew", padx=(0, 3), pady=(0, 4)); ttk.Button(actions, text="Bearbeiten", command=self._edit_event).grid(row=0, column=1, sticky="ew", padx=(3, 0), pady=(0, 4)); ttk.Button(actions, text="Löschen", command=self._delete_event).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        ttk.Button(actions, text="☀️ Sonne & 🌙 Mond", command=self._sun_moon_dialog).grid(row=2, column=0, columnspan=2, sticky="ew")
        side.grid_rowconfigure(0, weight=0); side.grid_rowconfigure(1, weight=0); side.grid_rowconfigure(2, weight=0); side.grid_rowconfigure(3, weight=1, minsize=80); side.grid_rowconfigure(4, weight=0, minsize=88)
        self.event_list.configure(height=4)
        ttk.Label(self.root, text="Mondphasen sind Näherungswerte. Termine und Feriencache lokal gespeichert.", padding=(10, 4)).pack(fill="x", side="bottom")
    def _on_root_configure(self, event):
        if event.widget is self.root:
            self.root.after_idle(self._refresh_layout)
    def _refresh_layout(self):
        if not self.root.winfo_exists():
            return
        self.root.update_idletasks()
    def _state_changed(self, _event=None):
        self.state = self.state_var.get(); self._save_settings(); self.holidays = self.holiday_cache.get(self.state, []); self.holiday_status.configure(text=f"Ferien: {self.state} · Cache" if self.holidays else f"Ferien: lade {self.state} …"); self._draw_month(); self._show_events(); self._refresh_holidays(); self._refresh_public_holidays(self.state)
    def _holiday_for(self, day):
        found = []
        for start, end, title in self.holidays:
            try:
                if date.fromisoformat(start) <= day <= date.fromisoformat(end): found.append(title)
            except (ValueError, TypeError): continue
        return ", ".join(dict.fromkeys(found))
    def _public_holiday_for(self, day):
        """Liefert Feiertagsnamen aus dem Cache/API und sichere bundesweite Fallbacks."""
        names = [name for when, name in self.public_holidays if when == day.isoformat()]
        # Bundesweite Feiertage auch anzeigen, wenn die Online-Abfrage noch läuft
        # oder offline nicht verfügbar ist.
        national = {
            (1, 1): "Neujahr", (5, 1): "Tag der Arbeit",
            (10, 3): "Tag der Deutschen Einheit",
            (12, 25): "1. Weihnachtstag", (12, 26): "2. Weihnachtstag",
        }
        fallback = national.get((day.month, day.day))
        if fallback and not names:
            names.append(fallback)
        return ", ".join(dict.fromkeys(names))
    def _apply_theme(self):
        # Warm, colorful calendar palette; keep all calendar logic untouched.
        if self.dark:
            bg, fg, cell, selected, today = ("#171923", "#edf0f7", "#242938", "#344e78", "#59451f")
            panel, muted, accent, border = "#1d2230", "#aeb8cb", "#ffd54f", "#343b4d"
        else:
            bg, fg, cell, selected, today = ("#f3f6fc", "#20283a", "#ffffff", "#cfe3ff", "#fff0bd")
            panel, muted, accent, border = "#e9eff9", "#5f6b80", "#e5a900", "#d7dfed"
        self.root.configure(bg=bg)
        style = ttk.Style(self.root)
        try: style.theme_use("clam")
        except tk.TclError: pass
        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=fg)
        style.configure("TButton", background=panel, foreground=fg, padding=(10, 7), borderwidth=1, relief="flat")
        style.map("TButton", background=[("active", accent), ("pressed", selected)], foreground=[("active", "#202124")])
        style.configure("TCheckbutton", background=bg, foreground=fg, padding=4)
        style.map("TCheckbutton", background=[("active", bg)])
        style.configure("TCombobox", fieldbackground=cell, background=panel, foreground=fg, arrowcolor=accent, padding=5)
        style.map("TCombobox", fieldbackground=[("readonly", cell)], foreground=[("readonly", fg)])
        style.configure("TEntry", fieldbackground=cell, foreground=fg, padding=5)
        style.configure("TSeparator", background=border)
        self.event_list.configure(bg=cell, fg=fg, selectbackground=selected, selectforeground=fg,
                                  highlightthickness=1, highlightbackground=border, relief="flat",
                                  activestyle="none", font=("TkDefaultFont", 10), selectborderwidth=0)
        for i, btn in enumerate(self.day_buttons):
            btn.configure(bg=cell, fg=fg, activebackground=selected, activeforeground=fg,
                          font=("TkDefaultFont", 11), cursor="hand2", bd=0,
                          highlightthickness=1, highlightbackground=border,
                          padx=4, pady=5)
        self._colors = (bg, fg, cell, selected, today)
        self.dark_button.configure(text="☀️ Hellmodus" if self.dark else "🌙 Dark Mode")
    def _draw_month(self):
        bg, fg, cell, selected, today_color = self._colors; self.title_label.configure(text=f"{calendar.month_name[self.month]} {self.year}"); weeks = calendar.monthcalendar(self.year, self.month); weeks += [[0] * 7] * (6 - len(weeks))
        for i, (row, col) in enumerate((r, c) for r in range(1, 7) for c in range(7)):
            day = weeks[row - 1][col]; btn = self.day_buttons[i]
            if not day: btn.configure(text="", state="disabled", bg=bg); continue
            current = date(self.year, self.month, day); count = len(self._events_for_day(current)); holiday = self._holiday_for(current); public_holiday = self._public_holiday_for(current); color = selected if current == self.selected else (today_color if current == self.today else ("#352b35" if self.dark and col in (5, 6) else ("#fff5f3" if (not self.dark and col in (5, 6)) else cell))); symbol, _ = moon_phase(current)
            btn.configure(text=f"{day} {symbol}" + ("\n🏖" if holiday else "") + ("\n★" if public_holiday else "") + (f"\n• {count}" if count else ""), state="normal", bg=color, fg=fg, relief="solid" if current == self.selected else "flat", bd=1 if current == self.selected else 0)
    def _select_cell(self, row, col):
        weeks = calendar.monthcalendar(self.year, self.month); weeks += [[0] * 7] * (6 - len(weeks)); day = weeks[row - 1][col]
        if day: self.selected = date(self.year, self.month, day); self._draw_month(); self._show_events()
    def _show_events(self):
        self.selected_label.configure(text="Termine am ausgewählten Tag")
        symbol, name = moon_phase(self.selected)
        holiday_name = self._public_holiday_for(self.selected)
        school_holiday = self._holiday_for(self.selected)
        details = [f"{self.selected.strftime('%d.%m.%Y')} · {symbol} {name}"]
        if holiday_name:
            details.append(f"Feiertag: {holiday_name}")
        if school_holiday:
            details.append(f"Schulferien: {school_holiday}")
        self.phase_label.configure(text="\n".join(details))
        self.event_list.delete(0, tk.END)
        self._visible_event_refs = self._events_for_day(self.selected)
        self._visible_event_refs.sort(key=lambda ref: ref[1].get("time", ""))
        for source_day, event in self._visible_event_refs:
            marker = " 🔁" if event.get("annual", False) else ""
            self.event_list.insert(tk.END, f"{event.get('time', '')}  {event.get('title', 'Termin')}{marker}")

    def _sun_moon_dialog(self):
        dialog = tk.Toplevel(self.root); dialog.title("☀️ Sonne & 🌙 Mond"); dialog.transient(self.root); dialog.grab_set(); dialog.resizable(False, False)
        frame = ttk.Frame(dialog, padding=16); frame.pack(fill="both", expand=True)
        tk.Label(frame, text="☀️  Sonnen- und Mondzeiten", font=("TkDefaultFont", 15, "bold"), fg="#FFD54F", bg=dialog.cget("bg")).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 10))
        ttk.Label(frame, text="Breitengrad").grid(row=1, column=0, sticky="w")
        lat_var = tk.StringVar(value=self.latitude); ttk.Entry(frame, textvariable=lat_var, width=13).grid(row=1, column=1, padx=(6, 14))
        ttk.Label(frame, text="Längengrad").grid(row=1, column=2, sticky="w")
        lon_var = tk.StringVar(value=self.longitude); ttk.Entry(frame, textvariable=lon_var, width=13).grid(row=1, column=3, padx=(6, 0))
        result = tk.Text(frame, height=13, width=48, wrap="word", relief="flat", borderwidth=0, font=("TkDefaultFont", 11), bg=dialog.cget("bg"), fg="#E8EAF6", padx=0, pady=10, state="disabled"); result.grid(row=2, column=0, columnspan=4, sticky="ew")
        result.tag_configure("sun", foreground="#FFD54F", font=("TkDefaultFont", 11, "bold"))
        result.tag_configure("moon", foreground="#90CAF9", font=("TkDefaultFont", 11, "bold"))
        result.tag_configure("sun_event", foreground="#FFCA28")
        result.tag_configure("moon_event", foreground="#B0C4DE")
        result.tag_configure("meta", foreground="#B0BEC5")
        def calculate():
            try:
                lat, lon = float(lat_var.get().replace(",", ".")), float(lon_var.get().replace(",", "."))
                if not -90 <= lat <= 90 or not -180 <= lon <= 180: raise ValueError("Koordinaten außerhalb des gültigen Bereichs.")
                import ephem
                from zoneinfo import ZoneInfo
                from datetime import datetime as dt
                local_zone = datetime.now().astimezone().tzinfo
                local_start = dt.combine(self.selected, time.min).astimezone()
                utc_start = local_start.astimezone(timezone.utc).replace(tzinfo=None)
                observer = ephem.Observer(); observer.lat = str(lat); observer.lon = str(lon); observer.elevation = 0; observer.pressure = 1010
                observer.date = ephem.Date(utc_start)
                lines = [f"📅 {self.selected.strftime('%A, %d.%m.%Y')}", f"📍 {lat:.4f}°, {lon:.4f}°", ""]
                for body, label, rise_name, set_name in ((ephem.Sun, "☀️ Sonne", "Sonnenaufgang", "Sonnenuntergang"), (ephem.Moon, "🌙 Mond", "Mondaufgang", "Monduntergang")):
                    events = []
                    for kind, title in (("rise", rise_name), ("set", set_name)):
                        try:
                            observer.date = ephem.Date(utc_start)
                            moment = observer.next_rising(body()) if kind == "rise" else observer.next_setting(body())
                            utc_dt = moment.datetime().replace(tzinfo=timezone.utc)
                            local_dt = utc_dt.astimezone()
                            if local_dt.date() == self.selected: events.append((local_dt, title))
                            else: events.append((None, title))
                        except (ephem.AlwaysUpError, ephem.NeverUpError): events.append((None, title))
                    lines.append(body.__name__ if False else label)
                    for moment, title in events: lines.append(f"   {'🌅' if 'aufgang' in title else '🌇'} {title}: {moment.strftime('%H:%M:%S') if moment else 'Kein Ereignis an diesem Tag'}")
                    lines.append("")
                self.latitude, self.longitude = f"{lat:.4f}", f"{lon:.4f}"; self._save_settings()
                result.configure(state="normal")
                result.delete("1.0", "end")
                for line in lines:
                    if line.startswith("☀️"):
                        result.insert("end", line + "\n", "sun")
                    elif line.startswith("🌙"):
                        result.insert("end", line + "\n", "moon")
                    elif "Sonnenaufgang" in line or "Sonnenuntergang" in line:
                        result.insert("end", line + "\n", "sun_event")
                    elif "Mondaufgang" in line or "Monduntergang" in line:
                        result.insert("end", line + "\n", "moon_event")
                    elif line.startswith("📅") or line.startswith("📍"):
                        result.insert("end", line + "\n", "meta")
                    else:
                        result.insert("end", line + "\n")
                result.configure(state="disabled")
            except ImportError:
                messagebox.showerror("Modul fehlt", "Für genaue Sonnen- und Mondzeiten wird python3-ephem benötigt. Bitte installieren: sudo apt install python3-ephem", parent=dialog)
            except ValueError as exc: messagebox.showerror("Koordinaten prüfen", str(exc) or "Bitte gültige Koordinaten eingeben.", parent=dialog)
            except Exception as exc: messagebox.showerror("Berechnung fehlgeschlagen", str(exc), parent=dialog)
        ttk.Button(frame, text="🔭 Zeiten berechnen", command=calculate).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        ttk.Button(frame, text="Schließen", command=dialog.destroy).grid(row=3, column=2, columnspan=2, sticky="ew", padx=(8, 0), pady=(4, 0))
        calculate()

    def _events_for_day(self, day):
        """Gibt einmalige Termine und jährliche Wiederholungen für einen Tag zurück."""
        result = [(day.isoformat(), event) for event in self.events.get(day.isoformat(), [])]
        for source_day, items in self.events.items():
            try:
                anchor = date.fromisoformat(source_day)
            except (TypeError, ValueError):
                continue
            for event in items:
                if not event.get("annual", False) or source_day == day.isoformat():
                    continue
                matches = (anchor.month == day.month and anchor.day == day.day)
                # Ein jährlicher Termin am 29. Februar wird in Nicht-Schaltjahren am 28. Februar gezeigt.
                if anchor.month == 2 and anchor.day == 29 and day.month == 2 and day.day == 28 and not calendar.isleap(day.year):
                    matches = True
                if matches:
                    result.append((source_day, event))
        return result
    def _shift(self, amount):
        n = self.year * 12 + self.month - 1 + amount; self.year, m = divmod(n, 12); self.month = m + 1; self.selected = date(self.year, self.month, 1); self._draw_month(); self._show_events()
    def _go_today(self): self.today = date.today(); self.year, self.month, self.selected = self.today.year, self.today.month, self.today; self._draw_month(); self._show_events()
    def _available_sound_devices(self):
        devices = ["default"]
        if shutil.which("aplay"):
            try:
                output = subprocess.run(["aplay", "-L"], capture_output=True, text=True, timeout=3).stdout
                for line in output.splitlines():
                    if line and not line[0].isspace() and line not in devices and not line.startswith(("null", "pulse", "sysdefault:CARD=")):
                        devices.append(line)
            except (OSError, subprocess.SubprocessError):
                pass
        return devices

    def _sound_settings(self):
        dialog = tk.Toplevel(self.root); dialog.title("Ton-Einstellungen"); dialog.transient(self.root); dialog.resizable(False, False)
        frame = ttk.Frame(dialog, padding=16); frame.pack(fill="both", expand=True)
        enabled = tk.BooleanVar(value=self.sound_enabled); device = tk.StringVar(value=self.sound_device)
        ttk.Checkbutton(frame, text="Erinnerungston aktivieren", variable=enabled).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))
        ttk.Label(frame, text="Soundkarte / ALSA-Ausgabegerät:").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=5)
        choices = self._available_sound_devices()
        if device.get() not in choices: choices.append(device.get())
        combo = ttk.Combobox(frame, textvariable=device, values=choices, state="readonly", width=32); combo.grid(row=1, column=1, sticky="ew", pady=5)
        ttk.Label(frame, text="Standard verwendet die Linux-Standardausgabe.\nWenn aplay fehlt, wird der Systemton versucht.", wraplength=390).grid(row=2, column=0, columnspan=2, sticky="w", pady=8)
        def test():
            old_enabled, old_device = self.sound_enabled, self.sound_device
            self.sound_enabled, self.sound_device = True, device.get()
            self._play_reminder_sound()
            self.sound_enabled, self.sound_device = old_enabled, old_device
        def save():
            self.sound_enabled, self.sound_device = enabled.get(), device.get(); self._save_settings(); dialog.destroy()
        buttons = ttk.Frame(frame); buttons.grid(row=3, column=0, columnspan=2, sticky="e", pady=(8, 0))
        ttk.Button(buttons, text="Testton", command=test).pack(side="left", padx=(0, 8)); ttk.Button(buttons, text="Abbrechen", command=dialog.destroy).pack(side="left", padx=(0, 8)); ttk.Button(buttons, text="Speichern", command=save).pack(side="left")
        dialog.grab_set(); dialog.wait_window()

    def _play_reminder_sound(self):
        """Spielt den Erinnerungston außerhalb der Tk-Ereignisschleife ab."""
        if not self.sound_enabled:
            return
        if shutil.which("aplay"):
            device = self.sound_device or "default"
            def worker():
                try:
                    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
                        rate, duration = 22050, 0.45
                        with wave.open(tmp.name, "wb") as wav:
                            wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(rate)
                            samples = bytearray()
                            for i in range(int(rate * duration)):
                                envelope = min(1.0, i / 400, (rate * duration - i) / 1000)
                                samples.extend(struct.pack("<h", int(9000 * envelope * math.sin(2 * math.pi * 880 * i / rate))))
                            wav.writeframes(samples)
                        subprocess.run(["aplay", "-q", "-D", device, tmp.name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5, check=False)
                except (OSError, subprocess.SubprocessError, wave.Error):
                    try: self.root.after(0, self.root.bell)
                    except tk.TclError: pass
            threading.Thread(target=worker, daemon=True).start()
        else:
            try: self.root.bell()
            except tk.TclError: pass

    def _schedule_reminder_check(self):
        # Einmal pro Sekunde prüfen, damit Erinnerungen möglichst genau zur
        # eingestellten Uhrzeit ausgelöst werden.
        self.root.after(1000, self._check_due_reminders)

    def _show_reminder_popup(self, event, when):
        """Zeigt den Termintext in einem eigenen, gut sichtbaren Popup."""
        title = str(event.get("title", "Termin")).strip() or "Termin"
        note = str(event.get("note", "")).strip()
        popup = tk.Toplevel(self.root)
        popup.title("LunaKalender – Terminerinnerung")
        # Kein transient(root): Das Hauptfenster kann im Tray withdrawn sein.
        # Ein transientes Popup würde dann oft ebenfalls verborgen bleiben.
        popup.resizable(False, False)
        popup.attributes("-topmost", True)
        frame = ttk.Frame(popup, padding=18)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="🔔 Termin steht an", font=("TkDefaultFont", 13, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Label(frame, text=f"{when.strftime('%d.%m.%Y')} · {when.strftime('%H:%M')} Uhr", font=("TkDefaultFont", 10)).pack(anchor="w", pady=(0, 8))
        ttk.Label(frame, text=title, font=("TkDefaultFont", 12, "bold"), wraplength=420, justify="left").pack(anchor="w", fill="x")
        if note:
            ttk.Label(frame, text=note, wraplength=420, justify="left").pack(anchor="w", fill="x", pady=(8, 0))
        ttk.Button(frame, text="OK", command=popup.destroy).pack(anchor="e", pady=(14, 0))
        popup.bind("<Return>", lambda _event: popup.destroy())
        popup.bind("<Escape>", lambda _event: popup.destroy())
        popup.update_idletasks()
        x = max(0, (popup.winfo_screenwidth() - popup.winfo_reqwidth()) // 2)
        y = max(0, (popup.winfo_screenheight() - popup.winfo_reqheight()) // 2)
        popup.geometry(f"+{x}+{y}")
        popup.lift()
        popup.attributes("-topmost", True)
        popup.focus_force()
        popup.after(1500, lambda: popup.attributes("-topmost", False) if popup.winfo_exists() else None)

    def _check_due_reminders(self):
        now = datetime.now(); today = now.date(); minute = now.strftime("%H:%M")
        for source_day, event in self._events_for_day(today):
            if event.get("time") != minute: continue
            key = (today.isoformat(), source_day, event.get("title", ""), minute)
            if key not in self._alerted_events:
                self._alerted_events.add(key)
                # Popup immer anzeigen; Ton nur, wenn er in den Ton-Einstellungen aktiv ist.
                if self.sound_enabled: self._play_reminder_sound()
                self._show_reminder_popup(event, now)
        self._schedule_reminder_check()

    def _toggle_dark(self): self.dark = not self.dark; self._save_settings(); self._apply_theme(); self._draw_month()
    def _toggle_autostart(self):
        path = Path.home() / ".config/autostart/lunakalender.desktop"
        enabled = self.autostart_var.get()
        try:
            if enabled:
                if not self.tray_enabled:
                    self.tray_var.set(True)
                    self._toggle_tray()
                    if not self.tray_enabled:
                        self.autostart_var.set(False)
                        return
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("[Desktop Entry]\nType=Application\nName=LunaKalender (Tray)\nExec=/usr/bin/lunakalender --tray\nIcon=lunakalender\nTerminal=false\nX-GNOME-Autostart-enabled=true\n", encoding="utf-8")
            else:
                path.unlink(missing_ok=True)
            self.autostart_enabled = enabled
        except OSError as exc:
            self.autostart_var.set(not enabled)
            messagebox.showerror("Autostart", f"Autostart konnte nicht geändert werden:\n{exc}", parent=self.root)

    def _toggle_tray(self):
        self.tray_enabled = self.tray_var.get(); self._save_settings()
        if self.tray_enabled:
            if not self._start_tray(): self.tray_enabled = False; self.tray_var.set(False); self._save_settings()
        elif self.tray_icon: self._stop_tray(); self.root.deiconify()
    def _start_tray(self):
        if self.tray_icon: return True
        try:
            # pystray/AppIndicator zeigt unter Linux bei Linksklick häufig immer
            # das Menü. Gtk.StatusIcon liefert getrennte activate- (links) und
            # popup-menu- (rechts) Signale und ermöglicht damit das gewünschte Verhalten.
            import gi
            gi.require_version("Gtk", "3.0")
            from gi.repository import Gtk, GLib, GdkPixbuf
            self._gtk = Gtk; self._glib = GLib; self._gdkpixbuf = GdkPixbuf
            self._tray_ready = threading.Event()
            def run_gtk_tray():
                try:
                    icon = Gtk.StatusIcon()
                    icon.set_title(APP_NAME)
                    icon.set_tooltip_text(APP_NAME)
                    icon.set_from_pixbuf(self._tray_pixbuf(date.today().day, 0))
                    icon.connect("activate", lambda *_args: self.root.after(0, self._toggle_tray_popup))
                    menu = Gtk.Menu()
                    show_item = Gtk.MenuItem(label="Kalender anzeigen")
                    show_item.connect("activate", lambda *_args: self.root.after(0, self._show_window))
                    menu.append(show_item)
                    quit_item = Gtk.MenuItem(label="Beenden")
                    quit_item.connect("activate", lambda *_args: self.root.after(0, self._quit))
                    menu.append(quit_item); menu.show_all()
                    icon.connect("popup-menu", lambda _icon, button, activate_time: menu.popup(None, None, Gtk.StatusIcon.position_menu, icon, button, activate_time))
                    self.tray_icon = icon
                    self._tray_menu = menu
                    self._tray_ready.set()
                    Gtk.main()
                except Exception as exc:
                    self._tray_error = str(exc)
                    self._tray_ready.set()
            self._tray_error = None
            threading.Thread(target=run_gtk_tray, daemon=True, name="LunaKalender-GTK-Tray").start()
            self._tray_ready.wait(timeout=3)
            if self._tray_error: raise RuntimeError(self._tray_error)
            if not self.tray_icon: raise RuntimeError("GTK-Tray konnte nicht initialisiert werden")
            self.root.after(300, self._update_tray_today)
            return True
        except (ImportError, RuntimeError) as exc:
            messagebox.showerror("Tray nicht verfügbar", f"Das Infobereichssymbol benötigt GTK 3 mit Python-Bindings (python3-gi und gir1.2-gtk-3.0).\n\n{exc}", parent=self.root)
            return False
    def _tray_pixbuf(self, day, event_count):
        image = self._make_tray_image(day, event_count)
        handle, filename = tempfile.mkstemp(suffix=".png", prefix="lunakalender-tray-")
        os.close(handle)
        try:
            image.save(filename, format="PNG")
            return self._gdkpixbuf.Pixbuf.new_from_file(filename)
        finally:
            try: os.unlink(filename)
            except OSError: pass
    def _stop_tray(self):
        icon = self.tray_icon
        self.tray_icon = None
        if icon is not None:
            try: self._glib.idle_add(icon.set_visible, False)
            except Exception: pass
        try: self._glib.idle_add(self._gtk.main_quit)
        except Exception: pass
    def _today_event_summary(self):
        today = date.today(); events = [event for _source, event in self._events_for_day(today)]
        return today, [f"{event.get('time', '').strip()} {event.get('title', 'Termin')}".strip() for event in events]
    def _update_tray_today(self):
        if not self.tray_icon: return
        today, events = self._today_event_summary()
        tooltip = ((f"{APP_NAME} – {today.strftime('%d.%m.%Y')}: " + "; ".join(events)) if events else f"{APP_NAME} – heute keine Termine ({today.strftime('%d.%m.%Y')})")[:120]
        try:
            pixbuf = self._tray_pixbuf(today.day, len(events))
            self._glib.idle_add(self.tray_icon.set_tooltip_text, tooltip)
            self._glib.idle_add(self.tray_icon.set_from_pixbuf, pixbuf)
        except Exception: pass
    def _make_tray_image(self, day, event_count):
        from PIL import Image, ImageDraw, ImageFont
        image = Image.new("RGB", (64, 64), "#5069a8"); draw = ImageDraw.Draw(image); draw.rounded_rectangle((5, 5, 59, 59), radius=8, fill="#ffffff"); draw.rectangle((5, 5, 59, 19), fill="#d9534f"); font = ImageFont.load_default(); day_text = str(day); box = draw.textbbox((0, 0), day_text, font=font); draw.text(((64 - (box[2] - box[0])) / 2, 28), day_text, fill="#26334d", font=font)
        if event_count:
            badge = str(event_count) if event_count < 100 else "99+"; draw.ellipse((38, 36, 63, 61), fill="#d92332", outline="#ffffff", width=2); badge_box = draw.textbbox((0, 0), badge, font=font); draw.text((50 - (badge_box[2] - badge_box[0]) / 2, 43), badge, fill="#ffffff", font=font)
        return image
    def _schedule_tray_refresh(self): self.root.after(60_000, self._tray_periodic_refresh)
    def _tray_periodic_refresh(self):
        if self.tray_icon: self._update_tray_today()
        self._schedule_tray_refresh()
    def _tray_show(self, icon=None, item=None):
        # Der Standard-Menüpunkt von pystray wird beim Linksklick ausgelöst.
        # Direkt das kleine Popup umschalten, ohne ein Auswahlmenü zu zeigen.
        self.root.after(0, self._toggle_tray_popup)
    def _toggle_tray_popup(self):
        popup = self._tray_popup
        if popup is not None:
            try:
                if popup.winfo_exists():
                    popup.destroy()
                    self._tray_popup = None
                    return
            except tk.TclError:
                pass
        self._tray_popup = None
        self._show_tray_popup()
    def _show_tray_popup(self):
        popup = tk.Toplevel(self.root)
        self._tray_popup = popup
        popup.title("LunaKalender – Sonne & Mond")
        popup.resizable(False, False)
        popup.configure(bg="#101a2c")
        popup.overrideredirect(True)
        width, height = 370, 560
        popup.update_idletasks()
        x = max(6, popup.winfo_screenwidth() - width - 16)
        y = max(6, popup.winfo_screenheight() - height - 70)
        popup.geometry(f"{width}x{height}+{x}+{y}")
        popup.attributes("-topmost", True)
        popup.bind("<Escape>", lambda _e: self._close_tray_popup())
        popup.bind("<FocusOut>", lambda _e: popup.after(180, self._popup_focus_check))

        header = tk.Frame(popup, bg="#10284b", padx=12, pady=10)
        header.pack(fill="x")
        tk.Label(header, text="🌙  LunaKalender", bg="#10284b", fg="#ffffff", font=("TkDefaultFont", 13, "bold")).pack(side="left")
        tk.Button(header, text="×", command=self._close_tray_popup, bg="#10284b", fg="#ffffff", relief="flat", font=("TkDefaultFont", 15, "bold")).pack(side="right")
        nav = tk.Frame(popup, bg="#101a2c", padx=8, pady=8); nav.pack(fill="x")
        state = {"year": date.today().year, "month": date.today().month, "day": date.today()}
        month_label = tk.Label(nav, text="", bg="#101a2c", fg="#f3f5ff", font=("TkDefaultFont", 12, "bold")); month_label.pack(side="left", expand=True)
        tk.Button(nav, text="‹", width=3, command=lambda: shift_month(-1), bg="#23314b", fg="white", relief="flat").pack(side="left", padx=2)
        tk.Button(nav, text="Heute", command=lambda: choose_day(date.today()), bg="#23314b", fg="white", relief="flat").pack(side="left", padx=2)
        tk.Button(nav, text="›", width=3, command=lambda: shift_month(1), bg="#23314b", fg="white", relief="flat").pack(side="left", padx=2)
        grid = tk.Frame(popup, bg="#101a2c", padx=8); grid.pack(fill="x")
        weekdays = tk.Frame(grid, bg="#101a2c"); weekdays.pack(fill="x")
        for wd in ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"):
            tk.Label(weekdays, text=wd, width=4, bg="#101a2c", fg="#b8c8e8", font=("TkDefaultFont", 9, "bold")).pack(side="left", expand=True)
        daygrid = tk.Frame(grid, bg="#101a2c"); daygrid.pack(fill="x")
        detail = tk.Frame(popup, bg="#17243a", padx=12, pady=10); detail.pack(fill="both", expand=True, padx=9, pady=(8, 9))
        day_label = tk.Label(detail, text="", bg="#17243a", fg="white", anchor="w", font=("TkDefaultFont", 10, "bold")); day_label.pack(fill="x", pady=(0, 7))
        sun1 = tk.Label(detail, text="", bg="#17243a", fg="#ffd54f", anchor="w", font=("TkDefaultFont", 10, "bold")); sun1.pack(fill="x", pady=2)
        sun2 = tk.Label(detail, text="", bg="#17243a", fg="#ffca28", anchor="w", font=("TkDefaultFont", 10, "bold")); sun2.pack(fill="x", pady=2)
        moon1 = tk.Label(detail, text="", bg="#17243a", fg="#9ed5ff", anchor="w", font=("TkDefaultFont", 10, "bold")); moon1.pack(fill="x", pady=2)
        moon2 = tk.Label(detail, text="", bg="#17243a", fg="#c5d7f0", anchor="w", font=("TkDefaultFont", 10, "bold")); moon2.pack(fill="x", pady=2)
        phase_label = tk.Label(detail, text="", bg="#17243a", fg="#dce6fa", anchor="w"); phase_label.pack(fill="x", pady=(7, 0))
        tk.Button(detail, text="📅 Vollständigen Kalender öffnen", command=self._open_main_from_popup, bg="#174d86", fg="white", relief="flat", pady=5).pack(fill="x", pady=(9, 0))

        def draw_month():
            for child in daygrid.winfo_children(): child.destroy()
            names = ("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember")
            month_label.configure(text=f"{names[state['month']-1]} {state['year']}")
            for week in calendar.monthcalendar(state['year'], state['month']):
                row = tk.Frame(daygrid, bg="#101a2c"); row.pack(fill="x")
                for col, number in enumerate(week):
                    if not number:
                        tk.Label(row, text="", width=4, height=2, bg="#101a2c").pack(side="left", expand=True, fill="x", padx=1, pady=1); continue
                    d = date(state['year'], state['month'], number); symbol, _phase = moon_phase(d)
                    bg = "#1765ad" if d == state['day'] else ("#422d42" if col >= 5 else "#202b40")
                    tk.Button(row, text=f"{number} {symbol}", width=4, height=1, bg=bg, fg="white", activebackground="#2d72b9", activeforeground="white", relief="flat", font=("TkDefaultFont", 8), command=lambda chosen=d: choose_day(chosen)).pack(side="left", expand=True, fill="x", padx=1, pady=1)
        def shift_month(offset):
            month, year = state['month'] + offset, state['year']
            if month < 1: month, year = 12, year - 1
            elif month > 12: month, year = 1, year + 1
            state['month'], state['year'] = month, year
            state['day'] = date(year, month, min(state['day'].day, calendar.monthrange(year, month)[1]))
            choose_day(state['day'])
        def choose_day(day):
            state['day'], state['year'], state['month'] = day, day.year, day.month
            draw_month()
            day_label.configure(text=f"📅 {day.strftime('%d.%m.%Y')}  ·  {moon_phase(day)[1]}")
            try:
                import ephem
                observer = ephem.Observer(); observer.lat = str(float(self.latitude)); observer.lon = str(float(self.longitude)); observer.elevation = 0; observer.pressure = 1010
                local_start = datetime.combine(day, time.min).astimezone()
                utc_start = local_start.astimezone(timezone.utc).replace(tzinfo=None)
                times = {}
                for key, body in (("sun", ephem.Sun), ("moon", ephem.Moon)):
                    for kind, fn in (("rise", observer.next_rising), ("set", observer.next_setting)):
                        try:
                            observer.date = ephem.Date(utc_start); moment = fn(body())
                            local = moment.datetime().replace(tzinfo=timezone.utc).astimezone()
                            times[(key, kind)] = local.strftime("%H:%M:%S") if local.date() == day else "Kein Ereignis"
                        except (ephem.AlwaysUpError, ephem.NeverUpError): times[(key, kind)] = "Kein Ereignis"
                sun1.configure(text=f"☀️ Sonnenaufgang     {times[('sun','rise')]}")
                sun2.configure(text=f"🌇 Sonnenuntergang   {times[('sun','set')]}")
                moon1.configure(text=f"🌙 Mondaufgang        {times[('moon','rise')]}")
                moon2.configure(text=f"🌌 Monduntergang      {times[('moon','set')]}")
                phase_label.configure(text=f"📍 {self.latitude}, {self.longitude}  ·  {moon_phase(day)[0]}")
            except Exception:
                sun1.configure(text="☀️ Sonnenzeiten: python3-ephem benötigt")
                sun2.configure(text="")
                moon1.configure(text="🌙 Mondzeiten: nicht verfügbar")
                moon2.configure(text="")
                phase_label.configure(text=f"📍 {self.latitude}, {self.longitude}")
        draw_month(); choose_day(date.today()); popup.focus_force()
    def _popup_focus_check(self):
        popup = self._tray_popup
        if popup is not None:
            try:
                if popup.winfo_exists() and not popup.focus_displayof():
                    self._close_tray_popup()
            except tk.TclError: pass
    def _close_tray_popup(self):
        popup = self._tray_popup; self._tray_popup = None
        if popup is not None:
            try: popup.destroy()
            except tk.TclError: pass
    def _open_main_from_popup(self):
        self._close_tray_popup(); self._show_window()
    def _show_window(self): self.root.deiconify(); self.root.lift(); self.root.focus_force()
    def _tray_quit(self, icon=None, item=None): self.root.after(0, self._quit)
    def _on_close(self): self.root.withdraw() if self.tray_enabled and self.tray_icon else self._quit()
    def _quit(self):
        if self.tray_icon: self._stop_tray()
        self.root.destroy()
    @staticmethod
    def _valid_time(value): return not value or (len(value) == 5 and value[2] == ":" and value[:2].isdigit() and value[3:].isdigit() and int(value[:2]) <= 23 and int(value[3:]) <= 59)
    def _event_editor(self, title_text, initial_date, old=None):
        """Ein gemeinsamer, komfortabler Dialog für neue und bestehende Termine."""
        dialog = tk.Toplevel(self.root)
        dialog.title(title_text)
        dialog.transient(self.root)
        dialog.resizable(True, True)
        dialog.geometry("520x430")
        dialog.minsize(420, 360)
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(4, weight=1)
        outer = ttk.Frame(dialog, padding=14)
        outer.grid(row=0, column=0, sticky="nsew")
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(3, weight=1)

        date_var = tk.StringVar(value=initial_date.strftime("%d.%m.%Y"))
        title_var = tk.StringVar(value=(old or {}).get("title", ""))
        time_var = tk.StringVar(value=(old or {}).get("time", ""))
        annual_var = tk.BooleanVar(value=bool((old or {}).get("annual", False)))
        ttk.Label(outer, text="Datum (TT.MM.JJJJ)").grid(row=0, column=0, sticky="w", padx=(0, 12), pady=5)
        date_entry = ttk.Entry(outer, textvariable=date_var)
        date_entry.grid(row=0, column=1, sticky="ew", pady=5)
        ttk.Label(outer, text="Titel *").grid(row=1, column=0, sticky="w", padx=(0, 12), pady=5)
        title_entry = ttk.Entry(outer, textvariable=title_var)
        title_entry.grid(row=1, column=1, sticky="ew", pady=5)
        ttk.Label(outer, text="Uhrzeit").grid(row=2, column=0, sticky="w", padx=(0, 12), pady=5)
        time_entry = ttk.Entry(outer, textvariable=time_var, width=12)
        time_entry.grid(row=2, column=1, sticky="w", pady=5)
        ttk.Label(outer, text="Notiz").grid(row=3, column=0, sticky="nw", padx=(0, 12), pady=5)
        note_box = tk.Text(outer, height=8, wrap="word", undo=True)
        note_box.grid(row=3, column=1, sticky="nsew", pady=5)
        note_box.insert("1.0", (old or {}).get("note", ""))
        annual_check = ttk.Checkbutton(outer, text="Jährlich wiederholen (z. B. Geburtstag oder Jahrestag)", variable=annual_var)
        annual_check.grid(row=4, column=0, columnspan=2, sticky="w", pady=(5, 2))
        ttk.Label(outer, text="* Pflichtfeld · Uhrzeit optional, Format HH:MM").grid(row=5, column=0, columnspan=2, sticky="w", pady=(6, 10))
        buttons = ttk.Frame(outer)
        buttons.grid(row=6, column=0, columnspan=2, sticky="e")
        result = {"value": None}

        def save():
            title = title_var.get().strip()
            raw_date = date_var.get().strip()
            time_value = time_var.get().strip()
            try:
                target_date = datetime.strptime(raw_date, "%d.%m.%Y").date()
            except ValueError:
                messagebox.showwarning("Ungültiges Datum", "Bitte ein gültiges Datum im Format TT.MM.JJJJ eingeben.", parent=dialog)
                date_entry.focus_set()
                return
            if not title:
                messagebox.showwarning("Eingabe fehlt", "Bitte einen Titel eingeben.", parent=dialog)
                title_entry.focus_set()
                return
            if not self._valid_time(time_value):
                messagebox.showwarning("Ungültige Uhrzeit", "Bitte HH:MM eingeben oder das Feld leer lassen.", parent=dialog)
                time_entry.focus_set()
                return
            result["value"] = (target_date, {"title": title, "time": time_value, "note": note_box.get("1.0", "end-1c").strip(), "annual": annual_var.get()})
            dialog.destroy()

        ttk.Button(buttons, text="Abbrechen", command=dialog.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text="Speichern", command=save).pack(side="right")
        dialog.bind("<Control-Return>", lambda _event: save())
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        dialog.grab_set()
        title_entry.focus_set()
        self.root.wait_window(dialog)
        return result["value"]

    def _add_event(self):
        edited = self._event_editor("Neuen Termin anlegen", self.selected)
        if not edited:
            return
        target_date, event = edited
        self.events.setdefault(target_date.isoformat(), []).append(event)
        self.events[target_date.isoformat()].sort(key=lambda item: item.get("time", ""))
        self.selected = target_date
        self.year, self.month = target_date.year, target_date.month
        self._save(); self._draw_month(); self._show_events(); self._update_tray_today()

    def _selected_event_ref(self):
        selection = self.event_list.curselection()
        if not selection: return None
        index = selection[0]
        if 0 <= index < len(self._visible_event_refs):
            return self._visible_event_refs[index]
        return None
    def _edit_event(self):
        ref = self._selected_event_ref()
        if not ref:
            messagebox.showinfo("Termin bearbeiten", "Bitte zuerst einen Termin in der Liste auswählen.", parent=self.root)
            return
        old_day, old = ref
        events = self.events.get(old_day, [])
        actual_index = next((i for i, event in enumerate(events) if event is old), None)
        if actual_index is None:
            return
        initial_date = self.selected if old.get("annual", False) else datetime.strptime(old_day, "%Y-%m-%d").date()
        edited = self._event_editor("Termin bearbeiten", initial_date, old)
        if not edited:
            return
        target_date, event = edited
        # Erst nach erfolgreicher Validierung ändern, damit Abbrechen nie Daten verändert.
        events.pop(actual_index)
        if not events:
            self.events.pop(old_day, None)
        target_key = target_date.isoformat()
        self.events.setdefault(target_key, []).append(event)
        self.events[target_key].sort(key=lambda item: item.get("time", ""))
        self.selected = target_date
        self.year, self.month = target_date.year, target_date.month
        self._save(); self._draw_month(); self._show_events(); self._update_tray_today()

    def _save(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True); tmp = EVENTS_FILE.with_suffix(".tmp"); tmp.write_text(json.dumps(self.events, ensure_ascii=False, indent=2), encoding="utf-8"); tmp.replace(EVENTS_FILE)
    def _delete_event(self):
        ref = self._selected_event_ref()
        if not ref: return
        key, event = ref
        if messagebox.askyesno("Termin löschen", f"„{event.get('title', 'Termin')}“ am {key} wirklich löschen?", parent=self.root):
            self.events[key].remove(event)
            if not self.events[key]: self.events.pop(key)
            self._save(); self._draw_month(); self._show_events(); self._update_tray_today()

def main():
    root = tk.Tk(); app = LunaKalender(root)
    from exchange import install_exchange
    install_exchange(app); root.mainloop()
if __name__ == "__main__": main()
