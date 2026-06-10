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

        sql = """
            SELECT e.id, e.title, c.name, e.date, e.time, e.location,
                   e.total_seats, e.public_target,
                   (SELECT COUNT(*) FROM registrations r WHERE r.event_id = e.id) AS registered
            FROM events e
            LEFT JOIN categories c ON e.category_id = c.id
            ORDER BY e.date ASC
        """
        with get_connection() as conn:
            rows = conn.execute(sql).fetchall()

        for row in rows:
            eid, title, cat, edate, etime, loc, seats, public, reg = row

            if query and query not in title.lower() and query not in (loc or "").lower() and query not in (cat or "").lower():
                continue
            if cat_sel != "Toate" and cat != cat_sel:
                continue
            if date_sel == "Azi" and edate != today:
                continue
            if date_sel == "Această săptămână" and not (today <= edate <= week_end):
                continue
            if date_sel == "Această lună" and not edate.startswith(today[:7]):
                continue
            if date_sel == "Viitoare" and edate < today:
                continue

            locuri_info = f"{reg}/{seats}" if seats else f"{reg}/∞"
            tag = "full" if seats and reg >= seats else "ok"
            self.tree.insert("", "end", iid=str(eid), tags=(tag,),
                             values=(eid, title, cat or "—", edate,
                                     etime or "—", loc or "—",
                                     seats or "∞", reg, public or "—"))

        self.tree.tag_configure("full", foreground="#E53935")
        self.tree.tag_configure("ok",   foreground=TEXT)

    def _sort_tree(self, col):
        items = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        rev = self._sort_asc if self._sort_col == col else True
        try:
            items.sort(key=lambda t: (float(t[0]) if t[0].replace(".","").isdigit() else t[0].lower()), reverse=not rev)
        except Exception:
            items.sort(reverse=not rev)
        for idx, (_, k) in enumerate(items):
            self.tree.move(k, "", idx)
        self._sort_col = col
        self._sort_asc = not rev

    def _get_selected_id(self):
        sel = self.tree.focus()
        if not sel:
            messagebox.showinfo("Info", "Selectează un eveniment.")
            return None
        return int(sel)

    def _delete_event(self):
        eid = self._get_selected_id()
        if eid is None: return
        title = self.tree.set(str(eid), "Titlu")
        if messagebox.askyesno("Confirmare", f"Ștergi evenimentul '{title}'?\nToate înscrierile vor fi șterse."):
            with get_connection() as conn:
                conn.execute("DELETE FROM events WHERE id=?", (eid,))
            self._refresh_events()

    def _edit_event(self):
        eid = self._get_selected_id()
        if eid is None: return
        with get_connection() as conn:
            row = conn.execute("""
                SELECT e.title, c.name, e.description, e.location, e.date,
                       e.time, e.total_seats, e.public_target, e.organizer
                FROM events e LEFT JOIN categories c ON e.category_id=c.id
                WHERE e.id=?""", (eid,)).fetchone()
        if row:
            EventDialog(self.root, self, edit_id=eid, initial=row)

    def _quick_register(self):
        eid = self._get_selected_id()
        if eid is None: return
        title = self.tree.set(str(eid), "Titlu")
        RegisterDialog(self.root, eid, title, self._refresh_events)



    def _page_add_event(self, edit_id=None, initial=None):
        canvas = tk.Canvas(self.main, bg=BG, highlightthickness=0)
        scroll = ttk.Scrollbar(self.main, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

        inner = tk.Frame(canvas, bg=BG)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        title_text = "Editează eveniment" if edit_id else "Eveniment nou"
        tk.Label(inner, text=title_text, font=FONT_TITLE, bg=BG, fg=TEXT).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=32, pady=(24, 16))

        fields = {}

        def row(r, label, widget_factory, col=0):
            tk.Label(inner, text=label, font=FONT_BODY, bg=BG, fg=TEXT, anchor="e", width=18
                     ).grid(row=r, column=col, sticky="e", padx=(32, 8), pady=6)
            w = widget_factory()
            w.grid(row=r, column=col+1, sticky="w", padx=(0, 32), pady=6)
            return w

#titlu
        fields["title"] = row(1, "Titlu *", lambda: tk.Entry(inner, width=40, font=FONT_BODY, relief="solid", bd=1))

                 #categorie
        cats = self._get_categories()
        cat_var = tk.StringVar()
        fields["category"] = row(2, "Categorie", lambda: ttk.Combobox(inner, textvariable=cat_var,
                                  values=cats, state="readonly", width=20, font=FONT_BODY))

           #data
        fields["date"] = row(3, "Data * (YYYY-MM-DD)", lambda: tk.Entry(inner, width=16, font=FONT_BODY, relief="solid", bd=1))

          #ora
        fields["time"] = row(4, "Ora (HH:MM)", lambda: tk.Entry(inner, width=10, font=FONT_BODY, relief="solid", bd=1))

         #locație
        fields["location"] = row(5, "Locație", lambda: tk.Entry(inner, width=40, font=FONT_BODY, relief="solid", bd=1))

        #locuri_totale
        fields["seats"] = row(6, "Locuri totale (0=∞)", lambda: tk.Entry(inner, width=10, font=FONT_BODY, relief="solid", bd=1))
        fields["seats"].insert(0, "0")

         #public_tinta
        pub_var = tk.StringVar()
        fields["public"] = row(7, "Public țintă", lambda: ttk.Combobox(inner, textvariable=pub_var, width=24,
                                values=["Toți", "Copii", "Tineri", "Adulți", "Seniori",
                                        "Familii", "Profesioniști"], font=FONT_BODY))

        #organizator
        fields["organizer"] = row(8, "Organizator", lambda: tk.Entry(inner, width=40, font=FONT_BODY, relief="solid", bd=1))

        #descriere
        tk.Label(inner, text="Descriere", font=FONT_BODY, bg=BG, fg=TEXT, anchor="e", width=18
                 ).grid(row=9, column=0, sticky="ne", padx=(32, 8), pady=6)
        desc_text = tk.Text(inner, width=40, height=5, font=FONT_BODY, relief="solid", bd=1, wrap="word")
        desc_text.grid(row=9, column=1, sticky="w", padx=(0, 32), pady=6)
        fields["desc"] = desc_text

        #editare
        if initial:
            t, cat, desc, loc, dt, tm, seats, pub, org = initial
            fields["title"].insert(0, t or "")
            cat_var.set(cat or "")
            fields["date"].insert(0, dt or "")
            fields["time"].insert(0, tm or "")
            fields["location"].insert(0, loc or "")
            fields["seats"].delete(0, tk.END)
            fields["seats"].insert(0, str(seats or 0))
            pub_var.set(pub or "")
            fields["organizer"].insert(0, org or "")
            if desc:
                desc_text.insert("1.0", desc)

        #butoane
        btn_frame = tk.Frame(inner, bg=BG)
        btn_frame.grid(row=10, column=0, columnspan=2, pady=20)

        def save():
            title_val = fields["title"].get().strip()
            if not title_val:
                messagebox.showerror("Eroare", "Titlul este obligatoriu.")
                return
            date_val = fields["date"].get().strip()
            if not date_val:
                messagebox.showerror("Eroare", "Data este obligatorie.")
                return
            try:
                datetime.strptime(date_val, "%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Eroare", "Formatul datei: YYYY-MM-DD (ex: 2024-06-15)")
                return

            cat_name = cat_var.get()
            with get_connection() as conn:
                cat_row = conn.execute("SELECT id FROM categories WHERE name=?", (cat_name,)).fetchone()
                cat_id  = cat_row[0] if cat_row else None

                try:
                    seats_val = int(fields["seats"].get() or 0)
                except ValueError:
                    seats_val = 0

                data = (
                    title_val, cat_id,
                    desc_text.get("1.0", tk.END).strip(),
                    fields["location"].get().strip(),
                    date_val,
                    fields["time"].get().strip() or None,
                    seats_val,
                    pub_var.get() or None,
                    fields["organizer"].get().strip() or None,
                )

                if edit_id:
                    conn.execute("""
                        UPDATE events SET title=?,category_id=?,description=?,location=?,
                        date=?,time=?,total_seats=?,public_target=?,organizer=? WHERE id=?
                    """, data + (edit_id,))
                    messagebox.showinfo("Salvat", "Eveniment actualizat!")
                else:
                    conn.execute("""
                        INSERT INTO events (title,category_id,description,location,date,time,
                        total_seats,public_target,organizer) VALUES (?,?,?,?,?,?,?,?,?)
                    """, data)
                    messagebox.showinfo("Salvat", f"Evenimentul '{title_val}' a fost adăugat!")

            self._show_page("events")

        tk.Button(btn_frame, text="💾  Salvează", command=save,
                  bg=ACCENT, fg="white", relief="flat", cursor="hand2",
                  font=FONT_BODY, padx=18, pady=8).pack(side="left", padx=8)
        tk.Button(btn_frame, text="Anulează", command=lambda: self._show_page("events"),
                  relief="flat", cursor="hand2", font=FONT_BODY,
                  padx=14, pady=8).pack(side="left")

    #inscrtiere

    def _page_registrations(self):
        tk.Label(self.main, text="Înscrieri participanți", font=FONT_TITLE,
                 bg=BG, fg=TEXT).pack(anchor="w", padx=24, pady=(20, 12))

        #selectevent
        top = tk.Frame(self.main, bg=BG)
        top.pack(fill="x", padx=24, pady=(0, 12))

        tk.Label(top, text="Eveniment:", font=FONT_BODY, bg=BG).pack(side="left")
        self.reg_event_var = tk.StringVar()
        events = self._get_event_list()
        self.reg_event_combo = ttk.Combobox(top, textvariable=self.reg_event_var,
                                             values=[e[1] for e in events],
                                             state="readonly", width=36, font=FONT_BODY)
        self.reg_event_combo.pack(side="left", padx=8)
        self.reg_event_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_registrations())
        self._events_for_reg = events

        tk.Button(top, text="+ Înscrie participant",
                  command=self._add_registration_from_page,
                  bg=SUCCESS, fg="white", relief="flat", cursor="hand2",
                  font=FONT_BODY, padx=12, pady=5).pack(side="left", padx=8)

        #tabel
        table_frame = tk.Frame(self.main, bg=BG)
        table_frame.pack(fill="both", expand=True, padx=24)

        cols = ("ID", "Nume", "Email", "Telefon", "Data înscrierii")
        self.reg_tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=16)
        widths = [40, 200, 220, 130, 160]
        for col, w in zip(cols, widths):
            self.reg_tree.heading(col, text=col)
            self.reg_tree.column(col, width=w)

        sb = ttk.Scrollbar(table_frame, orient="vertical", command=self.reg_tree.yview)
        self.reg_tree.configure(yscrollcommand=sb.set)
        self.reg_tree.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        #footer
        foot = tk.Frame(self.main, bg=BG)
        foot.pack(fill="x", padx=24, pady=8)
        self.reg_count_label = tk.Label(foot, text="", font=FONT_BODY, bg=BG, fg=MUTED)
        self.reg_count_label.pack(side="left")
        tk.Button(foot, text="🗑️  Șterge înscrierea selectată",
                  command=self._delete_registration,
                  relief="flat", cursor="hand2",
                  bg="#E53935", fg="white", font=FONT_BODY,
                  padx=12, pady=5).pack(side="right")

    def _refresh_registrations(self):
        for row in self.reg_tree.get_children():
            self.reg_tree.delete(row)
        title = self.reg_event_var.get()
        eid = next((e[0] for e in self._events_for_reg if e[1] == title), None)
        if eid is None: return
        with get_connection() as conn:
            rows = conn.execute("""
                SELECT id, name, email, phone, registered_at
                FROM registrations WHERE event_id=? ORDER BY registered_at
            """, (eid,)).fetchall()
        for row in rows:
            self.reg_tree.insert("", "end", iid=str(row[0]), values=row)
        self.reg_count_label.config(text=f"{len(rows)} participanți înscriși")

    def _add_registration_from_page(self):
        title = self.reg_event_var.get()
        eid   = next((e[0] for e in self._events_for_reg if e[1] == title), None)
        if eid is None:
            messagebox.showinfo("Info", "Selectează mai întâi un eveniment.")
            return
        RegisterDialog(self.root, eid, title, self._refresh_registrations)

    def _delete_registration(self):
        sel = self.reg_tree.focus()
        if not sel:
            messagebox.showinfo("Info", "Selectează o înregistrare.")
            return
        if messagebox.askyesno("Confirmare", "Ștergi înscrierea selectată?"):
            with get_connection() as conn:
                conn.execute("DELETE FROM registrations WHERE id=?", (int(sel),))
            self._refresh_registrations()

    #statistici

    def _page_stats(self):
        tk.Label(self.main, text="Statistici participare", font=FONT_TITLE,
                 bg=BG, fg=TEXT).pack(anchor="w", padx=24, pady=(20, 16))

        with get_connection() as conn:
            total_events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            total_reg    = conn.execute("SELECT COUNT(*) FROM registrations").fetchone()[0]
            total_cats   = conn.execute("SELECT COUNT(DISTINCT category_id) FROM events").fetchone()[0]
            upcoming     = conn.execute("SELECT COUNT(*) FROM events WHERE date >= ?",
                                         (date.today().isoformat(),)).fetchone()[0]

            by_cat = conn.execute("""
                SELECT c.name, COUNT(e.id) as cnt
                FROM events e JOIN categories c ON e.category_id=c.id
                GROUP BY c.name ORDER BY cnt DESC
            """).fetchall()

            top_events = conn.execute("""
                SELECT e.title, COUNT(r.id) as cnt
                FROM events e JOIN registrations r ON r.event_id=e.id
                GROUP BY e.id ORDER BY cnt DESC LIMIT 6
            """).fetchall()

            by_month = conn.execute("""
                SELECT substr(date,1,7) as m, COUNT(*) as cnt
                FROM events GROUP BY m ORDER BY m DESC LIMIT 6
            """).fetchall()

        #cards_rezumat
        card_frame = tk.Frame(self.main, bg=BG)
        card_frame.pack(fill="x", padx=24, pady=(0, 20))

        for label, value, color in [
            ("Total evenimente", total_events, ACCENT),
            ("Înscrieri totale",  total_reg,   "#1976D2"),
            ("Categorii active",  total_cats,  SUCCESS),
            ("Evenimente viitoare", upcoming,  WARNING),
        ]:
            card = tk.Frame(card_frame, bg=color, padx=20, pady=14)
            card.pack(side="left", padx=6, fill="y")
            tk.Label(card, text=str(value), font=("Helvetica", 28, "bold"),
                     bg=color, fg="white").pack()
            tk.Label(card, text=label, font=FONT_SMALL,
                     bg=color, fg="white").pack()


        charts = tk.Frame(self.main, bg=BG)
        charts.pack(fill="both", expand=True, padx=24)
        charts.columnconfigure((0, 1), weight=1)

          #evenimente_categorii
        self._draw_bar_chart(charts, "Evenimente pe categorii", by_cat, 0, 0)
        self._draw_bar_chart(charts, "Top înscrieri per eveniment", top_events, 0, 1)

    def _draw_bar_chart(self, parent, title, data, row, col):
        frame = tk.Frame(parent, bg=CARD_BG, relief="flat", bd=0)
        frame.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
        parent.rowconfigure(row, weight=1)

        tk.Label(frame, text=title, font=FONT_HEADER, bg=CARD_BG, fg=TEXT).pack(pady=(12, 4))

        canvas = tk.Canvas(frame, bg=CARD_BG, highlightthickness=0, height=220)
        canvas.pack(fill="x", padx=16, pady=(0, 12))

        if not data:
            canvas.create_text(200, 110, text="Nu există date", fill=MUTED, font=FONT_BODY)
            return

        canvas.update_idletasks()
        W = canvas.winfo_width() or 400
        H = 200
        margin_l, margin_r, margin_t, margin_b = 40, 16, 10, 50
        chart_w = W - margin_l - margin_r
        chart_h = H - margin_t - margin_b

        max_val = max(v for _, v in data) or 1
        n = len(data)
        bar_w = max(8, chart_w // n - 8)

        palette = [ACCENT, "#1976D2", SUCCESS, WARNING, "#9C27B0", "#00BCD4",
                   "#FF5722", "#607D8B", "#795548", "#E91E63"]

        for i, (label, val) in enumerate(data):
            x0 = margin_l + i * (chart_w // n) + (chart_w // n - bar_w) // 2
            x1 = x0 + bar_w
            bar_h = int((val / max_val) * chart_h)
            y0 = margin_t + chart_h - bar_h
            y1 = margin_t + chart_h

            color = palette[i % len(palette)]
            canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="")
            canvas.create_text((x0 + x1) // 2, y0 - 4, text=str(val),
                                font=FONT_SMALL, fill=TEXT)


            short = label[:8] + "…" if len(label) > 8 else label
            canvas.create_text((x0 + x1) // 2, y1 + 8, text=short,
                                font=FONT_SMALL, fill=MUTED, angle=0)


        canvas.create_line(margin_l, margin_t, margin_l, margin_t + chart_h,
                           fill="#DDDDDD", width=1)
        canvas.create_line(margin_l, margin_t + chart_h,
                           margin_l + chart_w, margin_t + chart_h,
                           fill="#DDDDDD", width=1)




    def _get_categories(self):
        with get_connection() as conn:
            return [r[0] for r in conn.execute("SELECT name FROM categories ORDER BY name")]

    def _get_event_list(self):
        with get_connection() as conn:
            return conn.execute(
                "SELECT id, title FROM events ORDER BY date DESC"
            ).fetchall()



#inregistrare participant

class RegisterDialog(tk.Toplevel):
    def __init__(self, parent, event_id, event_title, on_save):
        super().__init__(parent)
        self.title("Înscrie participant")
        self.geometry("380x280")
        self.resizable(False, False)
        self.grab_set()
        self.configure(bg=BG)

        self.event_id = event_id
        self.on_save  = on_save

        tk.Label(self, text=f"Eveniment: {event_title[:40]}",
                 font=FONT_SMALL, bg=BG, fg=MUTED).pack(anchor="w", padx=24, pady=(12, 0))
        tk.Label(self, text="Înscrie participant", font=FONT_HEADER, bg=BG, fg=TEXT).pack(
            anchor="w", padx=24, pady=(4, 12))

        frame = tk.Frame(self, bg=BG)
        frame.pack(padx=24, fill="x")

        for i, (lbl, attr) in enumerate([("Nume *", "name"), ("Email", "email"), ("Telefon", "phone")]):
            tk.Label(frame, text=lbl, font=FONT_BODY, bg=BG, width=10, anchor="e").grid(
                row=i, column=0, sticky="e", pady=5)
            e = tk.Entry(frame, font=FONT_BODY, relief="solid", bd=1, width=26)
            e.grid(row=i, column=1, sticky="w", padx=8, pady=5)
            setattr(self, attr, e)

        #veriflocuri
        with get_connection() as conn:
            row = conn.execute(
                "SELECT total_seats, (SELECT COUNT(*) FROM registrations WHERE event_id=?) FROM events WHERE id=?",
                (event_id, event_id)
            ).fetchone()
        if row:
            seats, reg = row
            if seats and reg >= seats:
                tk.Label(self, text="⚠️ Evenimentul este complet!", fg=ACCENT,
                         bg=BG, font=FONT_BODY).pack(pady=4)

        tk.Button(self, text="✅  Înscrie", command=self._save,
                  bg=SUCCESS, fg="white", relief="flat", cursor="hand2",
                  font=FONT_BODY, padx=16, pady=7).pack(pady=12)

        self.wait_window()

    def _save(self):
        name = self.name.get().strip()
        if not name:
            messagebox.showerror("Eroare", "Numele este obligatoriu.", parent=self)
            return
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO registrations (event_id, name, email, phone) VALUES (?,?,?,?)",
                (self.event_id, name, self.email.get().strip() or None,
                 self.phone.get().strip() or None)
            )
        messagebox.showinfo("Succes", f"'{name}' a fost înscris!", parent=self)
        self.on_save()
        self.destroy()


class EventDialog:
    def __init__(self, parent, app, edit_id, initial):
        app._page_add_event(edit_id=edit_id, initial=initial)


if __name__ == "__main__":
    App()
