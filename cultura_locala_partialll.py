import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
from pathlib import Path
from datetime import datetime, date
import math


DB_PATH = Path.home() / ".cultura_locala" / "events.db"


def get_connection():
    DB_PATH.parent.mkdir(exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    with get_connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS categories (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS events (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            title         TEXT NOT NULL,
            category_id   INTEGER REFERENCES categories(id),
            description   TEXT,
            location      TEXT,
            date          TEXT NOT NULL,
            time          TEXT,
            total_seats   INTEGER DEFAULT 0,
            public_target TEXT,
            organizer     TEXT,
            created_at    TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS registrations (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id   INTEGER REFERENCES events(id) ON DELETE CASCADE,
            name       TEXT NOT NULL,
            email      TEXT,
            phone      TEXT,
            registered_at TEXT DEFAULT (datetime('now'))
        );

        INSERT OR IGNORE INTO categories (name) VALUES
            ('Muzică'), ('Teatru'), ('Film'), ('Expoziție'),
            ('Atelier'), ('Conferință'), ('Festival'), ('Dans'), ('Altele');
        """)


BG       = "#F8F6F2"
SIDEBAR  = "#2C2C54"
ACCENT   = "#E94560"
CARD_BG  = "#FFFFFF"
TEXT     = "#2C2C54"
MUTED    = "#888888"
SUCCESS  = "#27AE60"
WARNING  = "#F39C12"

FONT_TITLE  = ("Helvetica", 22, "bold")
FONT_HEADER = ("Helvetica", 13, "bold")
FONT_BODY   = ("Helvetica", 11)
FONT_SMALL  = ("Helvetica", 9)

CAT_COLORS = {
    "Muzică": "#E91E63", "Teatru": "#9C27B0", "Film": "#3F51B5",
    "Expoziție": "#009688", "Atelier": "#FF5722", "Conferință": "#607D8B",
    "Festival": "#F44336", "Dans": "#E91E63", "Altele": "#795548",
}


class App:
    def __init__(self):
        init_db()

        self.root = tk.Tk()
        self.root.title("Cultură Locală")
        self.root.geometry("1100x700")
        self.root.minsize(900, 600)
        self.root.configure(bg=BG)

        self.current_page = tk.StringVar(value="events")
        self._build_layout()
        self._show_page("events")
        self.root.mainloop()

    def _build_layout(self):

        self.sidebar = tk.Frame(self.root, bg=SIDEBAR, width=200)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)


        tk.Label(self.sidebar, text="🎭", font=("Helvetica", 32),
                 bg=SIDEBAR, fg=ACCENT).pack(pady=(24, 4))
        tk.Label(self.sidebar, text="Cultură\nLocală",
                 font=("Helvetica", 13, "bold"),
                 bg=SIDEBAR, fg="white", justify="center").pack(pady=(0, 32))


        self.nav_buttons = {}
        nav_items = [
            ("events",     "📋  Evenimente"),
            ("add_event",  "➕  Adaugă eveniment"),
            ("registrations", "👥  Înscrieri"),
            ("stats",      "📊  Statistici"),
        ]
        for page, label in nav_items:
            btn = tk.Button(
                self.sidebar, text=label, anchor="w",
                font=FONT_BODY, relief="flat", cursor="hand2",
                bg=SIDEBAR, fg="white", padx=20, pady=10,
                activebackground=ACCENT, activeforeground="white",
                command=lambda p=page: self._show_page(p),
            )
            btn.pack(fill="x")
            self.nav_buttons[page] = btn


        self.main = tk.Frame(self.root, bg=BG)
        self.main.pack(side="left", fill="both", expand=True)

    def _show_page(self, page: str):

        for p, btn in self.nav_buttons.items():
            btn.configure(bg=ACCENT if p == page else SIDEBAR)


        for w in self.main.winfo_children():
            w.destroy()

        self.current_page.set(page)

        if page == "events":       self._page_events()
        elif page == "add_event":  self._page_add_event()
        elif page == "registrations": self._page_registrations()
        elif page == "stats":      self._page_stats()



    def _page_events(self):
         # Header
        hdr = tk.Frame(self.main, bg=BG)
        hdr.pack(fill="x", padx=24, pady=(20, 0))

        tk.Label(hdr, text="Evenimente", font=FONT_TITLE,
                 bg=BG, fg=TEXT).pack(side="left")
        tk.Button(hdr, text="+ Eveniment nou", command=lambda: self._show_page("add_event"),
                  bg=ACCENT, fg="white", relief="flat", cursor="hand2",
                  font=FONT_BODY, padx=14, pady=6).pack(side="right")

# Filtre
        filter_frame = tk.Frame(self.main, bg=BG)
        filter_frame.pack(fill="x", padx=24, pady=12)

        tk.Label(filter_frame, text="🔍", bg=BG, font=("Helvetica", 14)).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._refresh_events())
        tk.Entry(filter_frame, textvariable=self.search_var, font=FONT_BODY,
                 width=28, relief="solid", bd=1).pack(side="left", padx=6)

        tk.Label(filter_frame, text="Categorie:", bg=BG, font=FONT_BODY).pack(side="left", padx=(16, 4))
        self.cat_filter = ttk.Combobox(filter_frame, state="readonly", width=14, font=FONT_BODY)
        cats = ["Toate"] + self._get_categories()
        self.cat_filter["values"] = cats
        self.cat_filter.set("Toate")
        self.cat_filter.bind("<<ComboboxSelected>>", lambda e: self._refresh_events())
        self.cat_filter.pack(side="left")

        tk.Label(filter_frame, text="Dată:", bg=BG, font=FONT_BODY).pack(side="left", padx=(16, 4))
        self.date_filter = ttk.Combobox(filter_frame, state="readonly", width=14, font=FONT_BODY)
        self.date_filter["values"] = ["Toate", "Azi", "Această săptămână", "Această lună", "Viitoare"]
        self.date_filter.set("Toate")
        self.date_filter.bind("<<ComboboxSelected>>", lambda e: self._refresh_events())
        self.date_filter.pack(side="left")

# Tabel
        table_frame = tk.Frame(self.main, bg=BG)
        table_frame.pack(fill="both", expand=True, padx=24, pady=(0, 16))

        cols = ("ID", "Titlu", "Categorie", "Data", "Ora", "Locație", "Locuri", "Înscriși", "Public țintă")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings",
                                  selectmode="browse", height=18)

        widths = [40, 220, 100, 90, 60, 140, 60, 70, 110]
        for col, w in zip(cols, widths):
            self.tree.heading(col, text=col, command=lambda c=col: self._sort_tree(c))
            self.tree.column(col, width=w, anchor="center" if col not in ("Titlu", "Locație", "Public țintă") else "w")

        sb_y = ttk.Scrollbar(table_frame, orient="vertical",   command=self.tree.yview)
        sb_x = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        sb_y.grid(row=0, column=1, sticky="ns")
        sb_x.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        # button acțiune
        act = tk.Frame(self.main, bg=BG)
        act.pack(fill="x", padx=24, pady=(0, 16))

        for label, cmd, color in [
            ("Editează",    self._edit_event,    "#1976D2"),
            ("Înscriere",   self._quick_register, SUCCESS),
            ("Șterge",      self._delete_event,  "#E53935"),
        ]:
            tk.Button(act, text=label, command=cmd, relief="flat", cursor="hand2",
                      bg=color, fg="white", font=FONT_BODY,
                      padx=14, pady=6).pack(side="left", padx=4)

        self._sort_col = None
        self._sort_asc = True
        self._refresh_events()

    def _refresh_events(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        query   = self.search_var.get().lower() if hasattr(self, "search_var") else ""
        cat_sel = self.cat_filter.get()         if hasattr(self, "cat_filter")  else "Toate"
        date_sel= self.date_filter.get()        if hasattr(self, "date_filter") else "Toate"
        today   = date.today().isoformat()
        week_end= date.fromordinal(date.today().toordinal() + (6 - date.today().weekday())).isoformat()
        month_end = f"{date.today().year}-{date.today().month:02d}-31"


