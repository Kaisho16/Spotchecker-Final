import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import database as db
import qrcode
from PIL import Image, ImageTk
from tkcalendar import DateEntry
import os
import requests
import base64
from dotenv import load_dotenv

load_dotenv()
XENDIT_API_KEY = os.environ.get("XENDIT_SECRET_KEY", "")

def print_receipt_raw(text_content: str, barcode_data: str = None):
    try:
        import win32print
        printer_name = win32print.GetDefaultPrinter()
        hPrinter = win32print.OpenPrinter(printer_name)
        try:
            hJob = win32print.StartDocPrinter(hPrinter, 1, ("SpotCheck Receipt", None, "RAW"))
            win32print.StartPagePrinter(hPrinter)
            
            raw_data = text_content.encode("utf-8")
            
            # Print barcode if provided
            if barcode_data:
                raw_data += (
                    b"\n" +
                    b"\x1B\x61\x01" + # Align Center
                    b"\x1D\x48\x02" + # Text position: below
                    b"\x1D\x68\x50" + # Barcode height: 80
                    b"\x1D\x77\x03" + # Barcode width: 3
                    b"\x1D\x6B\x04" + str(barcode_data).encode("ascii") + b"\x00" + # CODE39
                    b"\n" +
                    b"\x1B\x61\x00"   # Align Left
                )
                
            # Add padding and basic cut command
            raw_data += b"\n\n\n\n\n\x1d\x56\x00"
            win32print.WritePrinter(hPrinter, raw_data)
            win32print.EndPagePrinter(hPrinter)
            win32print.EndDocPrinter(hPrinter)
        finally:
            win32print.ClosePrinter(hPrinter)
        return True
    except Exception as e:
        messagebox.showerror("Printer Error", f"Failed to print receipt: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════
# Color palette & style constants
# ═══════════════════════════════════════════════════════════════════════════

COLORS = {
    "header_bg": "#1B2A4A",
    "header_fg": "#FFFFFF",
    "sidebar_bg": "#162037",
    "sidebar_fg": "#B0BEC5",
    "sidebar_active_bg": "#1E3A5F",
    "sidebar_active_fg": "#FFFFFF",
    "body_bg": "#F0F2F5",
    "card_bg": "#FFFFFF",
    "card_border": "#E0E4EA",
    "text_primary": "#1B2A4A",
    "text_secondary": "#5A6A7A",
    "accent_blue": "#3B82F6",
    "accent_green": "#22C55E",
    "accent_green_hover": "#16A34A",
    "accent_red": "#EF4444",
    "accent_red_hover": "#DC2626",
    "accent_orange": "#F59E0B",
    "accent_orange_hover": "#D97706",
    "counter_bg": "#EFF6FF",
    "counter_border": "#BFDBFE",
    "full_bg": "#FEE2E2",
    "full_border": "#FECACA",
    "full_fg": "#DC2626",
    "table_header_bg": "#F8FAFC",
    "table_row_alt": "#F8FAFC",
    "table_row_hover": "#2563EB",
    "btn_primary": "#3B82F6",
    "btn_primary_hover": "#2563EB",
    "btn_confirm": "#22C55E",
    "btn_confirm_hover": "#16A34A",
    "btn_danger": "#EF4444",
    "btn_danger_hover": "#DC2626",
    "btn_gray": "#94A3B8",
    "btn_gray_hover": "#64748B",
    "input_border": "#CBD5E1",
    "input_focus": "#3B82F6",
    "divider": "#E2E8F0",
}

FONT_FAMILY = "Segoe UI"
FONTS = {
    "header_title": (FONT_FAMILY, 20, "bold"),
    "header_clock": (FONT_FAMILY, 12),
    "sidebar": (FONT_FAMILY, 13),
    "sidebar_bold": (FONT_FAMILY, 13, "bold"),
    "counter_number": (FONT_FAMILY, 48, "bold"),
    "counter_label": (FONT_FAMILY, 13),
    "card_title": (FONT_FAMILY, 15, "bold"),
    "table_header": (FONT_FAMILY, 11, "bold"),
    "table_body": (FONT_FAMILY, 13),
    "body": (FONT_FAMILY, 13),
    "body_bold": (FONT_FAMILY, 13, "bold"),
    "label": (FONT_FAMILY, 12),
    "button": (FONT_FAMILY, 13, "bold"),
    "small": (FONT_FAMILY, 11),
    "receipt_title": (FONT_FAMILY, 16, "bold"),
    "receipt_body": (FONT_FAMILY, 12),
    "receipt_total": (FONT_FAMILY, 18, "bold"),
}

# Minimum window size
MIN_WIDTH = 1080
MIN_HEIGHT = 700


# ═══════════════════════════════════════════════════════════════════════════
# Reusable widget helpers
# ═══════════════════════════════════════════════════════════════════════════

class RoundedFrame(tk.Frame):
    """A frame that simulates a card with shadow by using border and padding."""
    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            bg=COLORS["card_bg"],
            highlightbackground=COLORS["card_border"],
            highlightthickness=1,
            bd=0,
            **kwargs,
        )


class StyledButton(tk.Button):
    """A flat-styled button with hover effects."""

    def __init__(self, parent, text, color_key="btn_primary", hover_key="btn_primary_hover",
                 fg="white", command=None, width=None, **kwargs):
        self._color = COLORS[color_key]
        self._hover = COLORS[hover_key]
        super().__init__(
            parent,
            text=text,
            font=FONTS["button"],
            bg=self._color,
            fg=fg,
            activebackground=self._hover,
            activeforeground=fg,
            relief="flat",
            cursor="hand2",
            bd=0,
            padx=24,
            pady=10,
            command=command,
            **kwargs,
        )
        if width:
            self.configure(width=width)
        self.bind("<Enter>", lambda e: self._on_enter())
        self.bind("<Leave>", lambda e: self._on_leave())

    def _on_enter(self):
        if str(self.cget("state")) != "disabled":
            self.configure(bg=self._hover)

    def _on_leave(self):
        if str(self.cget("state")) != "disabled":
            self.configure(bg=self._color)


class StyledEntry(tk.Entry):
    """Entry widget with consistent styling."""

    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            font=FONTS["body"],
            bg="white",
            fg=COLORS["text_primary"],
            insertbackground=COLORS["text_primary"],
            relief="solid",
            bd=1,
            highlightthickness=2,
            highlightcolor=COLORS["input_focus"],
            highlightbackground=COLORS["input_border"],
            **kwargs,
        )


def format_elapsed(hours):
    """Convert decimal hours to 'Xh Ym' string."""
    if hours is None or hours < 0:
        return "0h 00m"
    total_min = int(hours * 60)
    h = total_min // 60
    m = total_min % 60
    return f"{h}h {m:02d}m"


def format_currency(value):
    """Format value as Philippine peso string."""
    return f"₱{value:,.2f}"


def export_to_excel(data: list[dict], default_filename: str) -> None:
    """
    Open a Save As dialog and write data to an Excel file.
    Uses pandas and openpyxl to format the output nicely.
    """
    from tkinter import filedialog
    import pandas as pd
    import datetime

    if not data:
        messagebox.showwarning("No Data", "There is no data to export.")
        return

    # Automatically replace .csv with .xlsx in default filename if present
    if default_filename.endswith(".csv"):
        default_filename = default_filename[:-4] + ".xlsx"

    filepath = filedialog.asksaveasfilename(
        defaultextension=".xlsx",
        filetypes=[("Excel files", "*.xlsx")],
        initialfile=default_filename,
    )
    if not filepath:
        return  # User cancelled

    try:
        df = pd.DataFrame(data)
        
        # Write to excel with column auto-sizing
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Report')
            worksheet = writer.sheets['Report']
            for column_cells in worksheet.columns:
                length = max(len(str(cell.value)) for cell in column_cells)
                worksheet.column_dimensions[column_cells[0].column_letter].width = length + 2

        messagebox.showinfo("Exported", f"File saved:\n{filepath}")
    except Exception as e:
        messagebox.showerror("Export Failed", str(e))

# ═══════════════════════════════════════════════════════════════════════════
# Main Application
# ═══════════════════════════════════════════════════════════════════════════

class SpotCheckApp:
    """Root application class managing all screens."""

    def __init__(self, root):
        self.root = root
        self.root.title("SpotCheck — Parking Management")
        self.root.configure(bg=COLORS["body_bg"])
        self.root.minsize(MIN_WIDTH, MIN_HEIGHT)

        # Try to start maximized
        try:
            self.root.state("zoomed")
        except tk.TclError:
            self.root.geometry(f"{MIN_WIDTH}x{MIN_HEIGHT}")

        # Cache vehicle types
        self.vehicle_types = db.get_vehicle_types()

        # Pending after() IDs and global bindings
        self._dashboard_refresh_id = None
        self._mousewheel_binding_id = None
        self.logged_in_user = None

        self._configure_treeview_style()
        self._show_login_screen()

    # ─── Treeview style (set once) ────────────────────────────────────────
    def _configure_treeview_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            font=FONTS["table_body"],
            rowheight=36,
            background=COLORS["card_bg"],
            fieldbackground=COLORS["card_bg"],
            foreground=COLORS["text_primary"],
            borderwidth=0,
        )
        style.configure(
            "Treeview.Heading",
            font=FONTS["table_header"],
            background=COLORS["table_header_bg"],
            foreground=COLORS["text_secondary"],
            borderwidth=0,
            relief="flat",
        )
        style.map("Treeview", 
                  background=[("selected", COLORS["table_row_hover"])],
                  foreground=[("selected", "#FFFFFF")])
        style.map("Treeview.Heading", background=[("active", COLORS["table_header_bg"])])

    # ─── Layout ───────────────────────────────────────────────────────────
    def _build_layout(self):
        # ── Header ──
        self.header = tk.Frame(self.root, bg=COLORS["header_bg"], height=60)
        self.header.pack(fill="x", side="top")
        self.header.pack_propagate(False)

        # Logo / title area
        title_frame = tk.Frame(self.header, bg=COLORS["header_bg"])
        title_frame.pack(side="left", padx=20)

        tk.Label(
            title_frame, text="🅿", font=(FONT_FAMILY, 24),
            bg=COLORS["header_bg"], fg=COLORS["accent_blue"],
        ).pack(side="left", padx=(0, 8))
        tk.Label(
            title_frame, text=db.get_settings().get("parking_name", "SpotCheck"), font=FONTS["header_title"],
            bg=COLORS["header_bg"], fg=COLORS["header_fg"],
        ).pack(side="left")

        # Clock
        self.clock_label = tk.Label(
            self.header, text="", font=FONTS["header_clock"],
            bg=COLORS["header_bg"], fg="#93C5FD",
        )
        self.clock_label.pack(side="right", padx=20)

        # ── Body wrapper (sidebar + content) ──
        self.body = tk.Frame(self.root, bg=COLORS["body_bg"])
        self.body.pack(fill="both", expand=True)

        # ── Sidebar ──
        self.sidebar = tk.Frame(self.body, bg=COLORS["sidebar_bg"], width=220)
        self.sidebar.pack(fill="y", side="left")
        self.sidebar.pack_propagate(False)

        tk.Label(
            self.sidebar, text="MENU", font=FONTS["small"],
            bg=COLORS["sidebar_bg"], fg=COLORS["sidebar_fg"], anchor="w",
        ).pack(fill="x", padx=20, pady=(24, 8))

        self.nav_buttons = {}
        nav_items = [
            ("dashboard", "📊  Dashboard"),
            ("entry",     "🚗  Log Entry"),
            ("exit",      "🚪  Log Exit"),
            ("void",      "🚫  Void Ticket"),
        ]
        
        # Only show Reports, History, and Admin Panel for Super Admin
        if self.logged_in_user and self.logged_in_user["role"] == "Admin":
            nav_items.append(("reports", "📈  Reports"))
            nav_items.append(("history", "📅  History"))
            nav_items.append(("admin", "⚙️  Admin Panel"))
            
        self._active_nav = None
        for key, label in nav_items:
            btn = tk.Label(
                self.sidebar, text=label, font=FONTS["sidebar"],
                bg=COLORS["sidebar_bg"], fg=COLORS["sidebar_fg"],
                anchor="w", padx=20, pady=12, cursor="hand2",
            )
            btn.pack(fill="x")
            btn.bind("<Button-1>", lambda e, k=key: self._navigate(k))
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=COLORS["sidebar_active_bg"]) if b != self._active_nav else None)
            btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=COLORS["sidebar_bg"]) if b != self._active_nav else None)
            self.nav_buttons[key] = btn

        # Spacer
        tk.Frame(self.sidebar, bg=COLORS["sidebar_bg"]).pack(fill="both", expand=True)

        # User Profile & Logout
        if self.logged_in_user:
            tk.Frame(self.sidebar, bg="#1E2A44", height=1).pack(fill="x", pady=(0, 16))
            tk.Label(
                self.sidebar, text=self.logged_in_user["display_name"], font=FONTS["sidebar_bold"],
                bg=COLORS["sidebar_bg"], fg=COLORS["header_fg"], anchor="w"
            ).pack(fill="x", padx=20)
            tk.Label(
                self.sidebar, text=self.logged_in_user["role"], font=FONTS["small"],
                bg=COLORS["sidebar_bg"], fg=COLORS["sidebar_fg"], anchor="w"
            ).pack(fill="x", padx=20, pady=(0, 12))
            
            logout_btn = tk.Label(
                self.sidebar, text="🚪  Logout", font=FONTS["sidebar"],
                bg=COLORS["sidebar_bg"], fg=COLORS["accent_red"], anchor="w",
                padx=20, pady=12, cursor="hand2"
            )
            logout_btn.pack(fill="x", pady=(0, 16))
            logout_btn.bind("<Button-1>", lambda e: self._logout())
            logout_btn.bind("<Enter>", lambda e, b=logout_btn: b.configure(bg=COLORS["sidebar_active_bg"]))
            logout_btn.bind("<Leave>", lambda e, b=logout_btn: b.configure(bg=COLORS["sidebar_bg"]))

        # ── Content area ──
        self.content = tk.Frame(self.body, bg=COLORS["body_bg"])
        self.content.pack(fill="both", expand=True, padx=0, pady=0)

    def _logout(self):
        self.logged_in_user = None
        self._clear_content()
        self._show_login_screen()

    def _show_login_screen(self):
        # clear everything if any
        for w in self.root.winfo_children():
            w.destroy()
            
        # build login layout
        self.root.configure(bg=COLORS["header_bg"])
        
        login_frame = RoundedFrame(self.root)
        login_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        inner = tk.Frame(login_frame, bg=COLORS["card_bg"])
        inner.pack(padx=48, pady=40)
        
        tk.Label(inner, text="🅿 SpotCheck", font=FONTS["header_title"], bg=COLORS["card_bg"], fg=COLORS["accent_blue"]).pack(pady=(0, 24))
        
        tk.Label(inner, text="Username", font=FONTS["label"], bg=COLORS["card_bg"], fg=COLORS["text_primary"]).pack(anchor="w")
        user_var = tk.StringVar()
        user_entry = StyledEntry(inner, textvariable=user_var, width=30)
        user_entry.pack(pady=(0, 16))
        
        tk.Label(inner, text="Password", font=FONTS["label"], bg=COLORS["card_bg"], fg=COLORS["text_primary"]).pack(anchor="w")
        pass_var = tk.StringVar()
        pass_entry = StyledEntry(inner, textvariable=pass_var, width=30, show="*")
        pass_entry.pack(pady=(0, 24))
        
        def _on_login(event=None):
            user = db.verify_login(user_var.get().strip(), pass_var.get())
            if user:
                self.logged_in_user = user
                self.root.configure(bg=COLORS["body_bg"])
                for w in self.root.winfo_children():
                    w.destroy()
                self._build_layout()
                self._show_dashboard()
                self._tick_clock()
            else:
                messagebox.showerror("Login Failed", "Invalid username or password.", parent=self.root)
                
        pass_entry.bind("<Return>", _on_login)
        user_entry.bind("<Return>", _on_login)
        user_entry.focus_set()
        
        StyledButton(inner, text="Login", color_key="btn_primary", hover_key="btn_primary_hover", command=_on_login, width=26).pack()

    def _navigate(self, key):
        screens = {
            "dashboard": self._show_dashboard,
            "entry": self._show_entry,
            "exit": self._show_exit,
            "void": self._show_void,
            "reports": self._show_reports,
            "history": self._show_history,
            "admin": self._show_admin_panel,
        }
        screens.get(key, self._show_dashboard)()

    def _set_active_nav(self, key):
        for k, btn in self.nav_buttons.items():
            btn.configure(bg=COLORS["sidebar_bg"], fg=COLORS["sidebar_fg"], font=FONTS["sidebar"])
        active = self.nav_buttons.get(key)
        if active:
            active.configure(bg=COLORS["sidebar_active_bg"], fg=COLORS["sidebar_active_fg"], font=FONTS["sidebar_bold"])
            self._active_nav = active

    def _clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()
        if self._dashboard_refresh_id:
            self.root.after_cancel(self._dashboard_refresh_id)
            self._dashboard_refresh_id = None
        if self._mousewheel_binding_id:
            self.root.unbind_all("<MouseWheel>")
            self._mousewheel_binding_id = None

    def _tick_clock(self):
        now = datetime.now().strftime("%A, %B %d, %Y  •  %I:%M:%S %p")
        self.clock_label.configure(text=now)
        self.root.after(1000, self._tick_clock)

    # ═══════════════════════════════════════════════════════════════════════
    # 1. DASHBOARD
    # ═══════════════════════════════════════════════════════════════════════

    def _show_dashboard(self):
        self._clear_content()
        self._set_active_nav("dashboard")

        wrapper = tk.Frame(self.content, bg=COLORS["body_bg"])
        wrapper.pack(fill="both", expand=True, padx=28, pady=20)

        # ── Overstay Alert Banner ──
        self.alert_banner = tk.Frame(wrapper, bg=COLORS["accent_red"])
        # Initially hidden, will be packed in _refresh_dashboard if needed
        self.alert_label = tk.Label(
            self.alert_banner, text="", font=FONTS["body_bold"],
            bg=COLORS["accent_red"], fg="white", pady=10
        )
        self.alert_label.pack()

        # ── Top row: two stat cards + action buttons ──
        top_row = tk.Frame(wrapper, bg=COLORS["body_bg"])
        top_row.pack(fill="x", pady=(0, 18))

        # --- Stat card: Vehicles Inside ---
        vehicles_card = RoundedFrame(top_row)
        vehicles_card.pack(side="left", fill="both", expand=True, padx=(0, 10))

        vehicles_inner = tk.Frame(vehicles_card, bg=COLORS["card_bg"])
        vehicles_inner.pack(padx=24, pady=18, fill="both", expand=True)

        tk.Label(
            vehicles_inner, text="VEHICLES INSIDE",
            font=FONTS["counter_label"], bg=COLORS["card_bg"],
            fg=COLORS["text_secondary"],
        ).pack(anchor="w")

        self.vehicles_count_label = tk.Label(
            vehicles_inner, text="0", font=FONTS["counter_number"],
            bg=COLORS["card_bg"], fg=COLORS["accent_blue"],
        )
        self.vehicles_count_label.pack(anchor="w", pady=(4, 0))

        # --- Stat card: Available Slots ---
        self.slots_card = RoundedFrame(top_row)
        self.slots_card.pack(side="left", fill="both", expand=True, padx=(10, 10))

        self.slots_inner = tk.Frame(self.slots_card, bg=COLORS["card_bg"])
        self.slots_inner.pack(padx=24, pady=18, fill="both", expand=True)

        self.slots_title_label = tk.Label(
            self.slots_inner, text="AVAILABLE SLOTS",
            font=FONTS["counter_label"], bg=COLORS["card_bg"],
            fg=COLORS["text_secondary"],
        )
        self.slots_title_label.pack(anchor="w")

        self.floor_labels = []

        # --- Action buttons card ---
        btn_card = RoundedFrame(top_row)
        btn_card.pack(side="right", fill="y", padx=(10, 0))

        btn_inner = tk.Frame(btn_card, bg=COLORS["card_bg"])
        btn_inner.pack(padx=24, pady=18)

        tk.Label(
            btn_inner, text="QUICK ACTIONS", font=FONTS["counter_label"],
            bg=COLORS["card_bg"], fg=COLORS["text_secondary"],
        ).pack(anchor="w", pady=(0, 12))

        self.entry_btn = StyledButton(
            btn_inner, text="  🚗  Log Entry  ",
            color_key="accent_green", hover_key="accent_green_hover",
            command=self._show_entry, width=20,
        )
        self.entry_btn.pack(fill="x", pady=(0, 8))

        StyledButton(
            btn_inner, text="  🚪  Log Exit  ",
            color_key="btn_primary", hover_key="btn_primary_hover",
            command=self._show_exit, width=20,
        ).pack(fill="x", pady=(0, 8))

        StyledButton(
            btn_inner, text="  🚫  Void Ticket  ",
            color_key="btn_danger", hover_key="btn_danger_hover",
            command=self._show_void, width=20,
        ).pack(fill="x", pady=(0, 8))

        if self.logged_in_user and self.logged_in_user["role"] == "Admin":
            StyledButton(
                btn_inner, text="  📈  Reports  ",
                color_key="btn_gray", hover_key="btn_gray_hover",
                command=self._show_reports, width=20,
            ).pack(fill="x")

        # ── Active tickets table ──
        table_card = RoundedFrame(wrapper)
        table_card.pack(fill="both", expand=True)

        table_header = tk.Frame(table_card, bg=COLORS["card_bg"])
        table_header.pack(fill="x", padx=20, pady=(16, 8))

        tk.Label(
            table_header, text="Active Tickets", font=FONTS["card_title"],
            bg=COLORS["card_bg"], fg=COLORS["text_primary"],
        ).pack(side="left")

        self.ticket_count_label = tk.Label(
            table_header, text="", font=FONTS["small"],
            bg=COLORS["card_bg"], fg=COLORS["text_secondary"],
        )
        self.ticket_count_label.pack(side="right")

        tk.Frame(table_card, bg=COLORS["divider"], height=1).pack(fill="x", padx=20)

        tree_frame = tk.Frame(table_card, bg=COLORS["card_bg"])
        tree_frame.pack(fill="both", expand=True, padx=20, pady=(8, 16))

        columns = ("ticket_id", "plate_no", "type_name", "entry_time", "elapsed")
        self.dashboard_tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings", selectmode="browse",
        )

        headings = {
            "ticket_id": ("Ticket ID", 130),
            "plate_no": ("Plate No.", 150),
            "type_name": ("Vehicle Type", 140),
            "entry_time": ("Entry Time", 200),
            "elapsed": ("Time Parked", 140),
        }
        for col, (text, width) in headings.items():
            self.dashboard_tree.heading(col, text=text, anchor="w")
            self.dashboard_tree.column(col, width=width, minwidth=80, anchor="w")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.dashboard_tree.yview)
        self.dashboard_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.dashboard_tree.pack(fill="both", expand=True)

        self.dashboard_tree.tag_configure("odd", background=COLORS["card_bg"])
        self.dashboard_tree.tag_configure("even", background=COLORS["table_row_alt"])

        self._refresh_dashboard()

    def _refresh_dashboard(self):
        """Reload ticket data and schedule next refresh."""
        try:
            count = db.get_active_ticket_count()
            available = db.get_available_slots()

            self.vehicles_count_label.configure(text=str(count))
            self.ticket_count_label.configure(
                text=f"{count} active ticket{'s' if count != 1 else ''}"
            )

            # Update available slots card (Multi-floor)
            floor_spots = db.get_available_spots_by_floor()
            if not hasattr(self, 'floor_labels'):
                self.floor_labels = []
            
            while len(self.floor_labels) < len(floor_spots):
                lbl = tk.Label(self.slots_inner, font=FONTS["body_bold"], anchor="w")
                lbl.pack(fill="x", anchor="w")
                self.floor_labels.append(lbl)
            while len(self.floor_labels) > len(floor_spots):
                lbl = self.floor_labels.pop()
                lbl.destroy()

            for i, f in enumerate(floor_spots):
                lbl_text = f"{f['name']}: {f['available']}/{f['capacity']}"
                if f['available'] <= 0:
                    lbl_text += " (FULL)"
                bg_col = COLORS["card_bg"] if available > 0 else COLORS["full_bg"]
                fg_col = COLORS["accent_blue"] if f['available'] > 0 else COLORS["accent_red"]
                if available <= 0: fg_col = COLORS["full_fg"]
                self.floor_labels[i].configure(text=lbl_text, bg=bg_col, fg=fg_col)

            if available <= 0:
                self.slots_card.configure(
                    bg=COLORS["full_bg"],
                    highlightbackground=COLORS["full_border"],
                )
                self.slots_inner.configure(bg=COLORS["full_bg"])
                self.slots_title_label.configure(bg=COLORS["full_bg"], fg=COLORS["full_fg"])
                # Disable Log Entry button
                self.entry_btn.configure(
                    state="disabled", text="  🚗  FULL  ",
                    bg="#D1D5DB", cursor="arrow",
                )
            else:
                self.slots_card.configure(
                    bg=COLORS["card_bg"],
                    highlightbackground=COLORS["card_border"],
                )
                self.slots_inner.configure(bg=COLORS["card_bg"])
                self.slots_title_label.configure(bg=COLORS["card_bg"], fg=COLORS["text_secondary"])
                self.entry_btn.configure(
                    state="normal", text="  🚗  Log Entry  ",
                    bg=COLORS["accent_green"], cursor="hand2",
                )

            overstaying = db.get_overstaying_tickets()
            if overstaying:
                count = len(overstaying)
                text = f"⚠️ ALERT: {count} vehicle{'s' if count != 1 else ''} parked for over 24 hours!"
                self.alert_label.configure(text=text)
                self.alert_banner.pack(fill="x", pady=(0, 18), before=self.alert_banner.master.winfo_children()[1]) # pack before top_row
            else:
                self.alert_banner.pack_forget()

            tickets = db.get_active_tickets()
            for item in self.dashboard_tree.get_children():
                self.dashboard_tree.delete(item)
            for i, t in enumerate(tickets):
                tag = "even" if i % 2 == 0 else "odd"
                self.dashboard_tree.insert(
                    "", "end",
                    values=(
                        t["ticket_id"],
                        t["plate_no"],
                        t["type_name"],
                        t["entry_time"],
                        format_elapsed(t["hours_elapsed"]),
                    ),
                    tags=(tag,),
                )
        except Exception:
            pass  # widget may have been destroyed during navigation

        self._dashboard_refresh_id = self.root.after(10000, self._refresh_dashboard)

    # ═══════════════════════════════════════════════════════════════════════
    # 2. LOG ENTRY
    # ═══════════════════════════════════════════════════════════════════════

    def _show_entry(self):
        self._clear_content()
        self._set_active_nav("entry")

        wrapper = tk.Frame(self.content, bg=COLORS["body_bg"])
        wrapper.pack(expand=True)

        card = RoundedFrame(wrapper)
        card.pack(padx=40, pady=30)

        inner = tk.Frame(card, bg=COLORS["card_bg"])
        inner.pack(padx=48, pady=40)

        # Title
        tk.Label(
            inner, text="Log New Entry", font=FONTS["card_title"],
            bg=COLORS["card_bg"], fg=COLORS["text_primary"],
        ).pack(anchor="w", pady=(0, 4))
        tk.Label(
            inner, text="Register a vehicle entering the parking facility",
            font=FONTS["small"], bg=COLORS["card_bg"], fg=COLORS["text_secondary"],
        ).pack(anchor="w", pady=(0, 24))

        tk.Frame(inner, bg=COLORS["divider"], height=1).pack(fill="x", pady=(0, 24))

        # Plate number
        tk.Label(
            inner, text="License Plate Number", font=FONTS["label"],
            bg=COLORS["card_bg"], fg=COLORS["text_primary"],
        ).pack(anchor="w", pady=(0, 6))

        plate_var = tk.StringVar()
        plate_entry = StyledEntry(inner, textvariable=plate_var, width=36)
        plate_entry.pack(anchor="w", ipady=6, pady=(0, 20))
        plate_entry.focus_set()

        def _upper(*_):
            val = plate_var.get()
            upper_val = val.upper()
            if val != upper_val:
                plate_var.set(upper_val)
                plate_entry.icursor(len(upper_val))
        plate_var.trace_add("write", _upper)

        # Vehicle type
        tk.Label(
            inner, text="Vehicle Type", font=FONTS["label"],
            bg=COLORS["card_bg"], fg=COLORS["text_primary"],
        ).pack(anchor="w", pady=(0, 6))

        self.vehicle_types = db.get_vehicle_types()
        type_names = [vt["type_name"] for vt in self.vehicle_types]
        type_var = tk.StringVar(value=type_names[0] if type_names else "")
        type_combo = ttk.Combobox(
            inner, textvariable=type_var, values=type_names,
            state="readonly", font=FONTS["body"], width=34,
        )
        type_combo.pack(anchor="w", ipady=4, pady=(0, 10))

        # Floor
        tk.Label(
            inner, text="Floor", font=FONTS["label"],
            bg=COLORS["card_bg"], fg=COLORS["text_primary"],
        ).pack(anchor="w", pady=(0, 6))

        floors = db.get_floors()
        floor_names = [f["name"] for f in floors]
        floor_var = tk.StringVar(value=floor_names[0] if floor_names else "")
        floor_combo = ttk.Combobox(
            inner, textvariable=floor_var, values=floor_names,
            state="readonly", font=FONTS["body"], width=34,
        )
        floor_combo.pack(anchor="w", ipady=4, pady=(0, 28))

        # Confirm button
        confirm_btn = StyledButton(
            inner, text="  ✓  Confirm Entry  ",
            color_key="accent_green", hover_key="accent_green_hover",
        )
        confirm_btn.pack(anchor="w")

        def _on_confirm():
            plate = plate_var.get().strip().upper()
            if not plate:
                messagebox.showwarning("Missing Information", "Plate number cannot be empty.", parent=self.root)
                return

            selected_type = type_var.get()
            type_id = None
            for vt in self.vehicle_types:
                if vt["type_name"] == selected_type:
                    type_id = vt["type_id"]
                    break
            if type_id is None:
                messagebox.showwarning("Missing Information", "Please select a vehicle type.", parent=self.root)
                return

            selected_floor = floor_var.get()
            floor_id = None
            for f in floors:
                if f["name"] == selected_floor:
                    floor_id = f["floor_id"]
                    break
            if floor_id is None:
                messagebox.showwarning("Missing Information", "Please select a floor.", parent=self.root)
                return

            confirm_btn.configure(state="disabled")
            try:
                ticket_id = db.log_entry(plate, type_id, floor_id)
                # Show receipt popup
                self._show_entry_receipt(ticket_id, plate, selected_type)
                self._show_dashboard()
            except ValueError as e:
                messagebox.showerror("Error", str(e), parent=self.root)
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self.root)
            finally:
                try:
                    confirm_btn.configure(state="normal")
                except tk.TclError:
                    pass

        confirm_btn.configure(command=_on_confirm)

        # Back link
        tk.Label(inner, text="", bg=COLORS["card_bg"]).pack(pady=4)
        back_btn = tk.Label(
            inner, text="← Back to Dashboard", font=FONTS["small"],
            bg=COLORS["card_bg"], fg=COLORS["accent_blue"], cursor="hand2",
        )
        back_btn.pack(anchor="w")
        back_btn.bind("<Button-1>", lambda e: self._show_dashboard())

    def _show_entry_receipt(self, ticket_id, plate, vehicle_type):
        """Show entry receipt popup."""
        popup = tk.Toplevel(self.root)
        popup.title("Entry Receipt")
        popup.configure(bg=COLORS["card_bg"])
        popup.resizable(False, False)
        popup.grab_set()

        popup.update_idletasks()
        w, h = 400, 520
        x = (popup.winfo_screenwidth() // 2) - (w // 2)
        y = (popup.winfo_screenheight() // 2) - (h // 2)
        popup.geometry(f"{w}x{h}+{x}+{y}")

        inner = tk.Frame(popup, bg=COLORS["card_bg"])
        inner.pack(expand=True, padx=32, pady=28)
        
        try:
            qr = qrcode.QRCode(version=1, box_size=4, border=1)
            qr.add_data(ticket_id)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            self._current_qr_img = ImageTk.PhotoImage(img) # Keep reference
            tk.Label(inner, image=self._current_qr_img, bg=COLORS["card_bg"]).pack(pady=(0, 16))
        except Exception:
            pass

        tk.Label(
            inner, text="✅", font=(FONT_FAMILY, 36),
            bg=COLORS["card_bg"],
        ).pack(pady=(0, 8))

        tk.Label(
            inner, text="Vehicle Registered", font=FONTS["receipt_title"],
            bg=COLORS["card_bg"], fg=COLORS["accent_green"],
        ).pack(pady=(0, 20))

        tk.Frame(inner, bg=COLORS["divider"], height=1).pack(fill="x", pady=(0, 16))

        details = [
            ("Ticket ID", ticket_id),
            ("Plate No.", plate),
            ("Vehicle Type", vehicle_type),
            ("Entry Time", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ]
        for label, value in details:
            row = tk.Frame(inner, bg=COLORS["card_bg"])
            row.pack(fill="x", pady=4)
            tk.Label(row, text=label, font=FONTS["small"], bg=COLORS["card_bg"],
                     fg=COLORS["text_secondary"], width=14, anchor="w").pack(side="left")
            tk.Label(row, text=value, font=FONTS["body_bold"], bg=COLORS["card_bg"],
                     fg=COLORS["text_primary"], anchor="w").pack(side="left")

        tk.Frame(inner, bg=COLORS["divider"], height=1).pack(fill="x", pady=(16, 16))

        btn_row = tk.Frame(inner, bg=COLORS["card_bg"])
        btn_row.pack()

        def _do_print():
            text = (
                "SpotCheck Parking\n"
                "-----------------\n"
                "ENTRY RECEIPT\n"
                f"Ticket ID: {ticket_id}\n"
                f"Plate: {plate}\n"
                f"Type: {vehicle_type}\n"
                f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                "-----------------\n"
                "Please keep this ticket.\n"
            )
            if print_receipt_raw(text, barcode_data=str(ticket_id)):
                popup.destroy()

        StyledButton(
            btn_row, text="  🖨️ Print & Done  ",
            color_key="btn_primary", hover_key="btn_primary_hover",
            command=_do_print,
        ).pack(side="left", padx=(0, 10))

        StyledButton(
            btn_row, text="  Done  ",
            color_key="btn_gray", hover_key="btn_gray_hover",
            command=popup.destroy,
        ).pack(side="left")

    # ═══════════════════════════════════════════════════════════════════════
    # 3. LOG EXIT
    # ═══════════════════════════════════════════════════════════════════════

    def _show_exit(self):
        self._clear_content()
        self._set_active_nav("exit")

        wrapper = tk.Frame(self.content, bg=COLORS["body_bg"])
        wrapper.pack(fill="both", expand=True, padx=28, pady=20)

        # Search card
        search_card = RoundedFrame(wrapper)
        search_card.pack(fill="x", pady=(0, 18))

        search_inner = tk.Frame(search_card, bg=COLORS["card_bg"])
        search_inner.pack(fill="x", padx=28, pady=24)

        tk.Label(
            search_inner, text="Log Exit", font=FONTS["card_title"],
            bg=COLORS["card_bg"], fg=COLORS["text_primary"],
        ).pack(anchor="w", pady=(0, 4))
        tk.Label(
            search_inner, text="Search by Ticket ID or Plate Number, or use the Scan QR button below.",
            font=FONTS["small"], bg=COLORS["card_bg"], fg=COLORS["text_secondary"],
        ).pack(anchor="w", pady=(0, 16))

        search_row = tk.Frame(search_inner, bg=COLORS["card_bg"])
        search_row.pack(fill="x")

        search_var = tk.StringVar()
        search_entry = StyledEntry(search_row, textvariable=search_var, width=36)
        search_entry.pack(side="left", ipady=6, padx=(0, 12))
        search_entry.focus_set()

        def _upper_search(*_):
            val = search_var.get()
            upper_val = val.upper()
            if val != upper_val:
                search_var.set(upper_val)
                search_entry.icursor(len(upper_val))
        search_var.trace_add("write", _upper_search)

        def _on_search():
            query = search_var.get().strip()
            if not query:
                messagebox.showwarning("Missing Information", "Please enter a Ticket ID or Plate Number.", parent=self.root)
                return

            ticket = db.search_ticket(query)
            if ticket is None:
                messagebox.showwarning("Not Found", "Ticket not found. Check the ticket ID or plate number.", parent=self.root)
                return

            if ticket["status"] == "Voided":
                messagebox.showinfo("Voided", "This ticket has already been voided.", parent=self.root)
                return

            if ticket["status"] == "Closed":
                self._show_closed_ticket_details(ticket)
                return

            # Active ticket — show exit details
            self._show_exit_details(ticket)

        search_btn = StyledButton(
            search_row, text="  🔍  Search  ",
            color_key="btn_primary", hover_key="btn_primary_hover",
            command=_on_search,
        )
        search_btn.pack(side="left")

        def _on_scan_result(ticket_id):
            ticket = db.search_ticket(ticket_id)
            if ticket is None:
                messagebox.showwarning("Not Found", "Ticket not found.", parent=self.root)
                return
            if ticket["status"] == "Voided":
                messagebox.showinfo("Voided", "This ticket has been voided.", parent=self.root)
                return
            if ticket["status"] == "Closed":
                self._show_closed_ticket_details(ticket)
                return
            self._show_exit_details(ticket)

        StyledButton(
            search_row, text="  📷  Scan QR  ",
            color_key="btn_gray", hover_key="btn_gray_hover",
            command=lambda: self._open_qr_scanner(_on_scan_result),
        ).pack(side="left", padx=(8, 0))

        StyledButton(
            search_row, text="  🎫  Lost Ticket  ",
            color_key="btn_danger", hover_key="btn_danger_hover",
            command=self._show_lost_ticket_popup
        ).pack(side="left", padx=(8, 0))

        search_entry.bind("<Return>", lambda e: _on_search())

        # ── Active vehicles table ──
        table_card = RoundedFrame(wrapper)
        table_card.pack(fill="both", expand=True)

        table_header = tk.Frame(table_card, bg=COLORS["card_bg"])
        table_header.pack(fill="x", padx=20, pady=(16, 8))

        tk.Label(
            table_header, text="Currently Parked Vehicles", font=FONTS["card_title"],
            bg=COLORS["card_bg"], fg=COLORS["text_primary"],
        ).pack(side="left")

        self._exit_ticket_count_label = tk.Label(
            table_header, text="", font=FONTS["small"],
            bg=COLORS["card_bg"], fg=COLORS["text_secondary"],
        )
        self._exit_ticket_count_label.pack(side="right")

        tk.Label(
            table_header, text="Click a row to process exit", font=FONTS["small"],
            bg=COLORS["card_bg"], fg=COLORS["accent_blue"],
        ).pack(side="right", padx=(0, 16))

        tk.Frame(table_card, bg=COLORS["divider"], height=1).pack(fill="x", padx=20)

        tree_frame = tk.Frame(table_card, bg=COLORS["card_bg"])
        tree_frame.pack(fill="both", expand=True, padx=20, pady=(8, 16))

        columns = ("ticket_id", "plate_no", "type_name", "entry_time", "elapsed")
        self._exit_tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings", selectmode="browse",
        )

        headings = {
            "ticket_id": ("Ticket ID", 130),
            "plate_no": ("Plate No.", 150),
            "type_name": ("Vehicle Type", 140),
            "entry_time": ("Entry Time", 200),
            "elapsed": ("Time Parked", 140),
        }
        for col, (text, width) in headings.items():
            self._exit_tree.heading(col, text=text, anchor="w")
            self._exit_tree.column(col, width=width, minwidth=80, anchor="w")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self._exit_tree.yview)
        self._exit_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._exit_tree.pack(fill="both", expand=True)

        self._exit_tree.tag_configure("odd", background=COLORS["card_bg"])
        self._exit_tree.tag_configure("even", background=COLORS["table_row_alt"])

        # Populate the table
        self._refresh_exit_table()

        # Double-click or single-click to select a vehicle
        def _on_row_select(event):
            selected = self._exit_tree.selection()
            if not selected:
                return
            item = self._exit_tree.item(selected[0])
            values = item["values"]
            if not values or not values[0]:
                return  # empty-state row
            ticket_id = str(values[0])
            ticket = db.search_ticket(ticket_id)
            if ticket and ticket["status"] == "Active":
                self._show_exit_details(ticket)

        self._exit_tree.bind("<Double-1>", _on_row_select)

        # Store reference so result frame can be used by detail views
        self._exit_result_frame = wrapper

    def _refresh_exit_table(self):
        """Reload the active vehicles table on the Log Exit screen."""
        try:
            tickets = db.get_active_tickets()
            for item in self._exit_tree.get_children():
                self._exit_tree.delete(item)

            count = len(tickets)
            self._exit_ticket_count_label.configure(
                text=f"{count} vehicle{'s' if count != 1 else ''} parked"
            )

            if not tickets:
                self._exit_tree.insert(
                    "", "end",
                    values=("", "", "No vehicles currently parked", "", ""),
                )
                return

            for i, t in enumerate(tickets):
                tag = "even" if i % 2 == 0 else "odd"
                self._exit_tree.insert(
                    "", "end",
                    values=(
                        t["ticket_id"],
                        t["plate_no"],
                        t["type_name"],
                        t["entry_time"],
                        format_elapsed(t["hours_elapsed"]),
                    ),
                    tags=(tag,),
                )
        except Exception:
            pass  # widget may have been destroyed

    def _show_exit_details(self, ticket):
        """Display active ticket details and payment form (replaces exit screen)."""
        self._clear_content()
        self._set_active_nav("exit")

        wrapper = tk.Frame(self.content, bg=COLORS["body_bg"])
        wrapper.pack(fill="both", expand=True, padx=28, pady=20)

        detail_card = RoundedFrame(wrapper)
        detail_card.pack(fill="x", pady=(0, 12))

        inner = tk.Frame(detail_card, bg=COLORS["card_bg"])
        inner.pack(fill="x", padx=28, pady=24)

        tk.Label(
            inner, text="Ticket Details", font=FONTS["card_title"],
            bg=COLORS["card_bg"], fg=COLORS["text_primary"],
        ).pack(anchor="w", pady=(0, 16))

        tk.Frame(inner, bg=COLORS["divider"], height=1).pack(fill="x", pady=(0, 16))

        details_grid = tk.Frame(inner, bg=COLORS["card_bg"])
        details_grid.pack(fill="x")

        fee = db.compute_fee(ticket["hours_elapsed"], ticket["hourly_rate"])

        fields = [
            ("Ticket ID", ticket["ticket_id"]),
            ("Plate No.", ticket["plate_no"]),
            ("Vehicle Type", ticket["type_name"]),
            ("Entry Time", ticket["entry_time"]),
            ("Time Parked", format_elapsed(ticket["hours_elapsed"])),
            ("Rate", format_currency(ticket["hourly_rate"]) + "/hr"),
        ]

        for i, (label, value) in enumerate(fields):
            row = i // 2
            col = i % 2
            f = tk.Frame(details_grid, bg=COLORS["card_bg"])
            f.grid(row=row, column=col, sticky="w", padx=(0, 60), pady=6)
            tk.Label(f, text=label, font=FONTS["small"], bg=COLORS["card_bg"], fg=COLORS["text_secondary"]).pack(anchor="w")
            tk.Label(f, text=value, font=FONTS["body_bold"], bg=COLORS["card_bg"], fg=COLORS["text_primary"]).pack(anchor="w")

        # Fee highlight
        tk.Frame(inner, bg=COLORS["divider"], height=1).pack(fill="x", pady=(20, 16))

        fee_frame = tk.Frame(inner, bg=COLORS["counter_bg"], highlightbackground=COLORS["counter_border"], highlightthickness=1)
        fee_frame.pack(fill="x", ipady=12)

        tk.Label(
            fee_frame, text="TOTAL FEE", font=FONTS["counter_label"],
            bg=COLORS["counter_bg"], fg=COLORS["text_secondary"],
        ).pack()
        tk.Label(
            fee_frame, text=format_currency(fee), font=FONTS["counter_number"],
            bg=COLORS["counter_bg"], fg=COLORS["accent_blue"],
        ).pack()

        # Payment method
        tk.Frame(inner, bg=COLORS["card_bg"], height=16).pack()

        tk.Label(
            inner, text="Payment Method", font=FONTS["label"],
            bg=COLORS["card_bg"], fg=COLORS["text_primary"],
        ).pack(anchor="w", pady=(0, 6))

        pay_var = tk.StringVar(value="Cash")
        pay_combo = ttk.Combobox(
            inner, textvariable=pay_var, values=["Cash", "E-payment"],
            state="readonly", font=FONTS["body"], width=20,
        )
        pay_combo.pack(anchor="w", ipady=4, pady=(0, 12))

        # Cash tendered field (shown only when Cash is selected)
        cash_frame = tk.Frame(inner, bg=COLORS["card_bg"])
        tk.Label(
            cash_frame, text="Cash Tendered (₱)", font=FONTS["label"],
            bg=COLORS["card_bg"], fg=COLORS["text_primary"],
        ).pack(anchor="w", pady=(0, 6))
        cash_var = tk.StringVar()
        StyledEntry(cash_frame, textvariable=cash_var, width=20).pack(anchor="w", ipady=6, pady=(0, 6))
        change_label = tk.Label(
            cash_frame, text="Change: ₱0.00", font=FONTS["body_bold"],
            bg=COLORS["card_bg"], fg=COLORS["text_secondary"],
        )
        change_label.pack(anchor="w", pady=(0, 12))

        def _update_change(*_):
            try:
                tendered = float(cash_var.get())
                change = tendered - fee
                if change >= 0:
                    change_label.configure(
                        text=f"Change: {format_currency(change)}",
                        fg=COLORS["accent_green"]
                    )
                else:
                    change_label.configure(
                        text="Amount too low",
                        fg=COLORS["accent_red"]
                    )
            except ValueError:
                change_label.configure(
                    text="Change: ₱0.00",
                    fg=COLORS["text_secondary"]
                )
        cash_var.trace_add("write", _update_change)

        def _toggle_cash_fields(*_):
            if pay_var.get() == "Cash":
                cash_frame.pack(anchor="w", fill="x", after=pay_combo)
            else:
                cash_frame.pack_forget()
        pay_var.trace_add("write", _toggle_cash_fields)
        _toggle_cash_fields()

        # Buttons row
        btn_row = tk.Frame(inner, bg=COLORS["card_bg"])
        btn_row.pack(anchor="w")

        confirm_btn = StyledButton(
            btn_row, text="  ✓  Confirm Payment  ",
            color_key="accent_green", hover_key="accent_green_hover",
        )
        confirm_btn.pack(side="left", padx=(0, 12))

        def _on_confirm_payment():
            change_amount = 0.0
            payment_method = pay_var.get()
            if payment_method == "Cash":
                try:
                    tendered = float(cash_var.get())
                except ValueError:
                    messagebox.showwarning(
                        "Invalid Amount",
                        "Please enter a valid cash tendered amount.",
                        parent=self.root,
                    )
                    return
                if tendered < fee:
                    messagebox.showwarning(
                        "Insufficient Amount",
                        f"Cash tendered ({format_currency(tendered)}) is less than "
                        f"the total fee ({format_currency(fee)}).",
                        parent=self.root,
                    )
                    return
                change_amount = tendered - fee
            elif payment_method == "E-payment":
                if not XENDIT_API_KEY:
                    messagebox.showerror("Error", "Xendit API Key is missing. Check your .env file.", parent=self.root)
                    return
                self._process_xendit_payment(ticket, fee)
                return

            confirm_btn.configure(state="disabled")
            try:
                receipt = db.log_exit(ticket["ticket_id"], pay_var.get())
                self._show_receipt_popup(receipt, change_amount=change_amount)
                self._show_dashboard()
            except ValueError as e:
                messagebox.showerror("Error", str(e), parent=self.root)
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self.root)
            finally:
                try:
                    confirm_btn.configure(state="normal")
                except tk.TclError:
                    pass

        confirm_btn.configure(command=_on_confirm_payment)

    def _process_xendit_payment(self, ticket, fee):
        auth_string = XENDIT_API_KEY + ":"
        headers = {
            "Authorization": "Basic " + base64.b64encode(auth_string.encode()).decode(),
            "Content-Type": "application/json"
        }
        payload = {
            "external_id": f"ticket_{ticket['ticket_id']}_{int(datetime.now().timestamp())}",
            "amount": float(fee),
            "description": f"Parking Fee for {ticket['plate_no']}",
            "invoice_duration": 300,
            "currency": "PHP"
        }
        try:
            res = requests.post("https://api.xendit.co/v2/invoices", json=payload, headers=headers)
            res.raise_for_status()
            data = res.json()
            invoice_url = data.get("invoice_url")
            invoice_id = data.get("id")
            self._show_xendit_qr_popup(ticket, fee, invoice_url, invoice_id)
        except Exception as e:
            messagebox.showerror("Xendit Error", f"Failed to generate invoice: {e}", parent=self.root)

    def _show_xendit_qr_popup(self, ticket, fee, invoice_url, invoice_id):
        popup = tk.Toplevel(self.root)
        popup.title("Scan to Pay")
        popup.configure(bg=COLORS["card_bg"])
        popup.resizable(False, False)
        popup.grab_set()

        inner = tk.Frame(popup, bg=COLORS["card_bg"])
        inner.pack(padx=32, pady=28)
        
        tk.Label(inner, text="Xendit Payment", font=FONTS["card_title"], bg=COLORS["card_bg"]).pack()
        tk.Label(inner, text=f"Amount: {format_currency(fee)}", font=FONTS["counter_label"], bg=COLORS["card_bg"], fg=COLORS["accent_blue"]).pack(pady=10)

        qr = qrcode.QRCode(version=1, box_size=5, border=1)
        qr.add_data(invoice_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        popup.qr_img = ImageTk.PhotoImage(img)
        tk.Label(inner, image=popup.qr_img, bg=COLORS["card_bg"]).pack(pady=10)
        
        status_label = tk.Label(inner, text="Waiting for payment...", font=FONTS["small"], bg=COLORS["card_bg"], fg=COLORS["accent_orange"])
        status_label.pack(pady=5)

        def check_status():
            if not popup.winfo_exists(): return
            try:
                auth_string = XENDIT_API_KEY + ":"
                headers = {"Authorization": "Basic " + base64.b64encode(auth_string.encode()).decode()}
                res = requests.get(f"https://api.xendit.co/v2/invoices/{invoice_id}", headers=headers)
                if res.status_code == 200:
                    status = res.json().get("status")
                    if status == "PAID":
                        status_label.config(text="Payment Successful!", fg=COLORS["accent_green"])
                        popup.after(1000, lambda: finalize_payment())
                        return
                    elif status == "EXPIRED":
                        status_label.config(text="Invoice Expired", fg=COLORS["accent_red"])
                        return
            except Exception:
                pass
            popup.after(3000, check_status)

        def finalize_payment():
            popup.destroy()
            try:
                receipt = db.log_exit(ticket["ticket_id"], "E-payment")
                self._show_receipt_popup(receipt, change_amount=0.0)
                self._show_dashboard()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self.root)
        
        StyledButton(inner, text="Cancel", color_key="btn_gray", hover_key="btn_gray_hover", command=popup.destroy).pack(pady=10)
        check_status()
        
        # Back link
        tk.Label(inner, text="", bg=COLORS["card_bg"]).pack(pady=4)
        back_btn = tk.Label(
            inner, text="← Back to vehicle list", font=FONTS["small"],
            bg=COLORS["card_bg"], fg=COLORS["accent_blue"], cursor="hand2",
        )
        back_btn.pack(anchor="w")
        back_btn.bind("<Button-1>", lambda e: self._show_exit())

    def _show_lost_ticket_popup(self):
        popup = tk.Toplevel(self.root)
        popup.title("Lost Ticket Exit")
        popup.configure(bg=COLORS["card_bg"])
        popup.resizable(False, False)
        popup.grab_set()

        w, h = 450, 380
        x = (popup.winfo_screenwidth() // 2) - (w // 2)
        y = (popup.winfo_screenheight() // 2) - (h // 2)
        popup.geometry(f"{w}x{h}+{x}+{y}")

        inner = tk.Frame(popup, bg=COLORS["card_bg"])
        inner.pack(fill="both", expand=True, padx=32, pady=28)

        tk.Label(inner, text="🎫  Lost Ticket Exit",
                 font=FONTS["card_title"], bg=COLORS["card_bg"],
                 fg=COLORS["accent_red"]).pack(anchor="w", pady=(0, 4))
        tk.Label(inner,
                 text="Driver could not produce their parking ticket.",
                 font=FONTS["small"], bg=COLORS["card_bg"],
                 fg=COLORS["text_secondary"]).pack(anchor="w", pady=(0, 16))

        tk.Frame(inner, bg=COLORS["divider"], height=1).pack(fill="x", pady=(0, 16))

        tk.Label(inner, text="License Plate Number",
                 font=FONTS["label"], bg=COLORS["card_bg"]).pack(anchor="w")
        plate_var = tk.StringVar()
        plate_entry = StyledEntry(inner, textvariable=plate_var, width=30)
        plate_entry.pack(anchor="w", ipady=6, pady=(0, 12))
        plate_entry.focus_set()

        def _upper(*_):
            v = plate_var.get()
            u = v.upper()
            if v != u:
                plate_var.set(u)
        plate_var.trace_add("write", _upper)

        tk.Label(inner, text="Payment Method",
                 font=FONTS["label"], bg=COLORS["card_bg"]).pack(anchor="w")
        pay_var = tk.StringVar(value="Cash")
        ttk.Combobox(inner, textvariable=pay_var,
                     values=["Cash", "E-payment"],
                     state="readonly", font=FONTS["body"],
                     width=20).pack(anchor="w", ipady=4, pady=(0, 20))

        btn_row = tk.Frame(inner, bg=COLORS["card_bg"])
        btn_row.pack(anchor="w")

        def _on_confirm():
            plate = plate_var.get().strip().upper()
            if not plate:
                messagebox.showwarning("Missing", "Plate number is required.",
                                       parent=popup)
                return

            try:
                if pay_var.get() == "E-payment":
                    messagebox.showwarning("Unavailable", "E-payment is not supported for Lost Tickets at this time.", parent=popup)
                    return
                receipt = db.log_lost_ticket_exit(plate, pay_var.get())
                popup.destroy()
                self._show_receipt_popup(receipt)
                self._show_dashboard()
            except ValueError as e:
                messagebox.showerror("Not Found", str(e), parent=popup)
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=popup)

        StyledButton(btn_row, text="  ✓  Confirm  ",
                     color_key="accent_green",
                     hover_key="accent_green_hover",
                     command=_on_confirm).pack(side="left", padx=(0, 10))

        StyledButton(btn_row, text="  Cancel  ",
                     color_key="btn_gray",
                     hover_key="btn_gray_hover",
                     command=popup.destroy).pack(side="left")

    def _show_closed_ticket_details(self, ticket):
        """Show a closed ticket with optional Reopen button."""
        self._clear_content()
        self._set_active_nav("exit")

        wrapper = tk.Frame(self.content, bg=COLORS["body_bg"])
        wrapper.pack(fill="both", expand=True, padx=28, pady=20)

        detail_card = RoundedFrame(wrapper)
        detail_card.pack(fill="x", pady=(0, 12))

        inner = tk.Frame(detail_card, bg=COLORS["card_bg"])
        inner.pack(fill="x", padx=28, pady=24)

        # Title row with Closed badge
        title_row = tk.Frame(inner, bg=COLORS["card_bg"])
        title_row.pack(fill="x", pady=(0, 16))

        tk.Label(
            title_row, text="Ticket Details", font=FONTS["card_title"],
            bg=COLORS["card_bg"], fg=COLORS["text_primary"],
        ).pack(side="left")

        badge = tk.Label(
            title_row, text="  CLOSED  ", font=FONTS["small"],
            bg=COLORS["full_bg"], fg=COLORS["full_fg"],
        )
        badge.pack(side="right", padx=4, ipady=2, ipadx=8)

        tk.Frame(inner, bg=COLORS["divider"], height=1).pack(fill="x", pady=(0, 16))

        # Ticket info
        details_grid = tk.Frame(inner, bg=COLORS["card_bg"])
        details_grid.pack(fill="x")

        fields = [
            ("Ticket ID", ticket["ticket_id"]),
            ("Plate No.", ticket["plate_no"]),
            ("Vehicle Type", ticket["type_name"]),
            ("Entry Time", ticket["entry_time"]),
        ]

        for i, (label, value) in enumerate(fields):
            row = i // 2
            col = i % 2
            f = tk.Frame(details_grid, bg=COLORS["card_bg"])
            f.grid(row=row, column=col, sticky="w", padx=(0, 60), pady=6)
            tk.Label(f, text=label, font=FONTS["small"], bg=COLORS["card_bg"], fg=COLORS["text_secondary"]).pack(anchor="w")
            tk.Label(f, text=value, font=FONTS["body_bold"], bg=COLORS["card_bg"], fg=COLORS["text_primary"]).pack(anchor="w")

        tk.Frame(inner, bg=COLORS["divider"], height=1).pack(fill="x", pady=(20, 16))

        tk.Label(
            inner, text="This ticket is already closed.",
            font=FONTS["body"], bg=COLORS["card_bg"], fg=COLORS["text_secondary"],
        ).pack(anchor="w", pady=(0, 8))

        # Check if reopen is possible (within 5 minutes of payment)
        payment = db.get_payment_for_ticket(ticket["ticket_id"])
        can_reopen = False
        if payment:
            try:
                exit_time = datetime.strptime(payment["exit_time"], "%Y-%m-%d %H:%M:%S")
                elapsed_minutes = (datetime.now() - exit_time).total_seconds() / 60.0
                if elapsed_minutes <= 5.0:
                    can_reopen = True
                    remaining = 5.0 - elapsed_minutes
                    tk.Label(
                        inner,
                        text=f"Payment was made {elapsed_minutes:.1f} min ago. "
                             f"Reopen available for {remaining:.1f} more min.",
                        font=FONTS["small"], bg=COLORS["card_bg"],
                        fg=COLORS["accent_orange"],
                    ).pack(anchor="w", pady=(0, 16))
            except Exception:
                pass

        if can_reopen:
            reopen_btn = StyledButton(
                inner, text="  🔄  Reopen Ticket  ",
                color_key="accent_orange", hover_key="accent_orange_hover",
            )
            reopen_btn.pack(anchor="w")

            def _on_reopen():
                reopen_btn.configure(state="disabled")
                try:
                    db.reopen_ticket(ticket["ticket_id"])
                    messagebox.showinfo(
                        "Ticket Reopened",
                        f"Ticket {ticket['ticket_id']} has been reopened.\n"
                        f"The vehicle is now marked as Active again.",
                        parent=self.root,
                    )
                    self._show_dashboard()
                except ValueError as e:
                    messagebox.showerror("Error", str(e), parent=self.root)
                except Exception as e:
                    messagebox.showerror("Error", str(e), parent=self.root)
                finally:
                    try:
                        reopen_btn.configure(state="normal")
                    except tk.TclError:
                        pass

            reopen_btn.configure(command=_on_reopen)

        # Back link
        tk.Label(inner, text="", bg=COLORS["card_bg"]).pack(pady=4)
        back_btn = tk.Label(
            inner, text="← Back to vehicle list", font=FONTS["small"],
            bg=COLORS["card_bg"], fg=COLORS["accent_blue"], cursor="hand2",
        )
        back_btn.pack(anchor="w")
        back_btn.bind("<Button-1>", lambda e: self._show_exit())


    def _show_receipt_popup(self, receipt, change_amount=0.0):
        """Show a styled payment receipt dialog."""
        popup = tk.Toplevel(self.root)
        popup.title("Payment Receipt")
        popup.configure(bg=COLORS["card_bg"])
        popup.resizable(False, False)
        popup.grab_set()

        popup.update_idletasks()
        w, h = 420, 600 if change_amount > 0 else 560
        x = (popup.winfo_screenwidth() // 2) - (w // 2)
        y = (popup.winfo_screenheight() // 2) - (h // 2)
        popup.geometry(f"{w}x{h}+{x}+{y}")

        inner = tk.Frame(popup, bg=COLORS["card_bg"])
        inner.pack(expand=True, padx=32, pady=28)

        tk.Label(
            inner, text="✅", font=(FONT_FAMILY, 36),
            bg=COLORS["card_bg"],
        ).pack(pady=(0, 8))

        tk.Label(
            inner, text="Payment Successful", font=FONTS["receipt_title"],
            bg=COLORS["card_bg"], fg=COLORS["accent_green"],
        ).pack(pady=(0, 20))

        tk.Frame(inner, bg=COLORS["divider"], height=1).pack(fill="x", pady=(0, 16))

        details = [
            ("Ticket ID", receipt["ticket_id"]),
            ("Plate No.", receipt["plate_no"]),
            ("Vehicle Type", receipt["type_name"]),
            ("Entry Time", receipt["entry_time"]),
            ("Duration", format_elapsed(receipt["hours_elapsed"])),
            ("Payment", receipt["payment_method"]),
        ]
        if change_amount > 0:
            details.append(("Change Given", format_currency(change_amount)))

        for label, value in details:
            row = tk.Frame(inner, bg=COLORS["card_bg"])
            row.pack(fill="x", pady=3)
            tk.Label(row, text=label, font=FONTS["small"], bg=COLORS["card_bg"],
                     fg=COLORS["text_secondary"], width=14, anchor="w").pack(side="left")
            tk.Label(row, text=value, font=FONTS["receipt_body"], bg=COLORS["card_bg"],
                     fg=COLORS["text_primary"], anchor="w").pack(side="left")

        tk.Frame(inner, bg=COLORS["divider"], height=1).pack(fill="x", pady=(16, 12))

        tk.Label(
            inner, text="TOTAL PAID", font=FONTS["counter_label"],
            bg=COLORS["card_bg"], fg=COLORS["text_secondary"],
        ).pack(pady=(8, 4))
        tk.Label(
            inner, text=format_currency(receipt["total_fee"]),
            font=("Helvetica", 24, "bold"), bg=COLORS["card_bg"], fg=COLORS["accent_blue"],
        ).pack(pady=(0, 20))

        btn_row = tk.Frame(inner, bg=COLORS["card_bg"])
        btn_row.pack()

        def _do_print():
            change_line = ""
            if change_amount > 0:
                change_line = f"Change: {format_currency(change_amount)}\n"
            text = (
                "SpotCheck Parking\n"
                "-----------------\n"
                "PAYMENT RECEIPT\n"
                f"Ticket ID: {receipt['ticket_id']}\n"
                f"Plate: {receipt['plate_no']}\n"
                f"Type: {receipt['type_name']}\n"
                f"Entry: {receipt['entry_time']}\n"
                f"Duration: {format_elapsed(receipt['hours_elapsed'])}\n"
                f"Payment: {receipt['payment_method']}\n"
                "-----------------\n"
                f"TOTAL PAID: {format_currency(receipt['total_fee'])}\n"
                + change_line +
                "-----------------\n"
                "Thank you!\n"
            )
            if print_receipt_raw(text):
                popup.destroy()

        StyledButton(
            btn_row, text="  🖨️ Print & Done  ",
            color_key="btn_primary", hover_key="btn_primary_hover",
            command=_do_print,
        ).pack(side="left", padx=(0, 10))

        StyledButton(
            btn_row, text="  Done  ",
            color_key="btn_gray", hover_key="btn_gray_hover",
            command=popup.destroy,
        ).pack(side="left")

    # ═══════════════════════════════════════════════════════════════════════
    # 4. VOID TICKET
    # ═══════════════════════════════════════════════════════════════════════

    def _show_void(self):
        self._clear_content()
        self._set_active_nav("void")

        wrapper = tk.Frame(self.content, bg=COLORS["body_bg"])
        wrapper.pack(fill="both", expand=True, padx=28, pady=20)

        # Search card
        search_card = RoundedFrame(wrapper)
        search_card.pack(fill="x", pady=(0, 18))

        search_inner = tk.Frame(search_card, bg=COLORS["card_bg"])
        search_inner.pack(fill="x", padx=28, pady=24)

        tk.Label(
            search_inner, text="Void Ticket", font=FONTS["card_title"],
            bg=COLORS["card_bg"], fg=COLORS["accent_red"],
        ).pack(anchor="w", pady=(0, 4))
        tk.Label(
            search_inner, text="Search by Ticket ID or Plate Number, or use the Scan QR button below.",
            font=FONTS["small"], bg=COLORS["card_bg"], fg=COLORS["text_secondary"],
        ).pack(anchor="w", pady=(0, 16))

        search_row = tk.Frame(search_inner, bg=COLORS["card_bg"])
        search_row.pack(fill="x")

        search_var = tk.StringVar()
        search_entry = StyledEntry(search_row, textvariable=search_var, width=36)
        search_entry.pack(side="left", ipady=6, padx=(0, 12))
        search_entry.focus_set()

        def _upper_search(*_):
            val = search_var.get()
            upper_val = val.upper()
            if val != upper_val:
                search_var.set(upper_val)
                search_entry.icursor(len(upper_val))
        search_var.trace_add("write", _upper_search)

        def _on_search():
            query = search_var.get().strip()
            if not query:
                messagebox.showwarning("Missing Information", "Please enter a Ticket ID or Plate Number.", parent=self.root)
                return

            ticket = db.search_ticket(query)
            if ticket is None:
                messagebox.showwarning("Not Found", "Ticket not found. Check the ticket ID or plate number.", parent=self.root)
                return

            if ticket["status"] == "Closed":
                messagebox.showinfo("Already Closed", "This ticket is already closed.", parent=self.root)
                return

            if ticket["status"] == "Voided":
                messagebox.showinfo("Already Voided", "This ticket has already been voided.", parent=self.root)
                return

            self._show_void_details(ticket)

        search_btn = StyledButton(
            search_row, text="  🔍  Search  ",
            color_key="btn_primary", hover_key="btn_primary_hover",
            command=_on_search,
        )
        search_btn.pack(side="left")

        def _on_scan_result_void(ticket_id):
            ticket = db.search_ticket(ticket_id)
            if ticket is None:
                messagebox.showwarning("Not Found", "Ticket not found.", parent=self.root)
                return
            if ticket["status"] == "Closed":
                messagebox.showinfo("Already Closed", "This ticket is already closed.", parent=self.root)
                return
            if ticket["status"] == "Voided":
                messagebox.showinfo("Already Voided", "This ticket has already been voided.", parent=self.root)
                return
            self._show_void_details(ticket)

        StyledButton(
            search_row, text="  📷  Scan QR  ",
            color_key="btn_gray", hover_key="btn_gray_hover",
            command=lambda: self._open_qr_scanner(_on_scan_result_void),
        ).pack(side="left", padx=(8, 0))

        search_entry.bind("<Return>", lambda e: _on_search())

        # ── Active vehicles table ──
        table_card = RoundedFrame(wrapper)
        table_card.pack(fill="both", expand=True)

        table_header = tk.Frame(table_card, bg=COLORS["card_bg"])
        table_header.pack(fill="x", padx=20, pady=(16, 8))

        tk.Label(
            table_header, text="Currently Parked Vehicles", font=FONTS["card_title"],
            bg=COLORS["card_bg"], fg=COLORS["text_primary"],
        ).pack(side="left")

        self._void_ticket_count_label = tk.Label(
            table_header, text="", font=FONTS["small"],
            bg=COLORS["card_bg"], fg=COLORS["text_secondary"],
        )
        self._void_ticket_count_label.pack(side="right")

        tk.Label(
            table_header, text="Click a row to void", font=FONTS["small"],
            bg=COLORS["card_bg"], fg=COLORS["accent_red"],
        ).pack(side="right", padx=(0, 16))

        tk.Frame(table_card, bg=COLORS["divider"], height=1).pack(fill="x", padx=20)

        tree_frame = tk.Frame(table_card, bg=COLORS["card_bg"])
        tree_frame.pack(fill="both", expand=True, padx=20, pady=(8, 16))

        columns = ("ticket_id", "plate_no", "type_name", "entry_time", "elapsed")
        self._void_tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings", selectmode="browse",
        )

        headings = {
            "ticket_id": ("Ticket ID", 130),
            "plate_no": ("Plate No.", 150),
            "type_name": ("Vehicle Type", 140),
            "entry_time": ("Entry Time", 200),
            "elapsed": ("Time Parked", 140),
        }
        for col, (text, width) in headings.items():
            self._void_tree.heading(col, text=text, anchor="w")
            self._void_tree.column(col, width=width, minwidth=80, anchor="w")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self._void_tree.yview)
        self._void_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._void_tree.pack(fill="both", expand=True)

        self._void_tree.tag_configure("odd", background=COLORS["card_bg"])
        self._void_tree.tag_configure("even", background=COLORS["table_row_alt"])

        # Populate the table
        self._refresh_void_table()

        # Double-click to select a vehicle
        def _on_row_select(event):
            selected = self._void_tree.selection()
            if not selected:
                return
            item = self._void_tree.item(selected[0])
            values = item["values"]
            if not values or not values[0]:
                return  # empty-state row
            ticket_id = str(values[0])
            ticket = db.search_ticket(ticket_id)
            if ticket and ticket["status"] == "Active":
                self._show_void_details(ticket)

        self._void_tree.bind("<Double-1>", _on_row_select)

    def _refresh_void_table(self):
        """Reload the active vehicles table on the Void Ticket screen."""
        try:
            tickets = db.get_active_tickets()
            for item in self._void_tree.get_children():
                self._void_tree.delete(item)

            count = len(tickets)
            self._void_ticket_count_label.configure(
                text=f"{count} vehicle{'s' if count != 1 else ''} parked"
            )

            if not tickets:
                self._void_tree.insert(
                    "", "end",
                    values=("", "", "No vehicles currently parked", "", ""),
                )
                return

            for i, t in enumerate(tickets):
                tag = "even" if i % 2 == 0 else "odd"
                self._void_tree.insert(
                    "", "end",
                    values=(
                        t["ticket_id"],
                        t["plate_no"],
                        t["type_name"],
                        t["entry_time"],
                        format_elapsed(t["hours_elapsed"]),
                    ),
                    tags=(tag,),
                )
        except Exception:
            pass  # widget may have been destroyed

    def _show_void_details(self, ticket):
        """Display ticket details and void form (replaces void screen)."""
        self._clear_content()
        self._set_active_nav("void")

        wrapper = tk.Frame(self.content, bg=COLORS["body_bg"])
        wrapper.pack(fill="both", expand=True, padx=28, pady=20)

        detail_card = RoundedFrame(wrapper)
        detail_card.pack(fill="x", pady=(0, 12))

        inner = tk.Frame(detail_card, bg=COLORS["card_bg"])
        inner.pack(fill="x", padx=28, pady=24)

        # Title with warning icon
        title_row = tk.Frame(inner, bg=COLORS["card_bg"])
        title_row.pack(fill="x", pady=(0, 16))

        tk.Label(
            title_row, text="⚠️  Confirm Void", font=FONTS["card_title"],
            bg=COLORS["card_bg"], fg=COLORS["accent_red"],
        ).pack(side="left")

        tk.Frame(inner, bg=COLORS["divider"], height=1).pack(fill="x", pady=(0, 16))

        # Ticket info
        details_grid = tk.Frame(inner, bg=COLORS["card_bg"])
        details_grid.pack(fill="x")

        fields = [
            ("Ticket ID", ticket["ticket_id"]),
            ("Plate No.", ticket["plate_no"]),
            ("Vehicle Type", ticket["type_name"]),
            ("Entry Time", ticket["entry_time"]),
        ]

        for i, (label, value) in enumerate(fields):
            row = i // 2
            col = i % 2
            f = tk.Frame(details_grid, bg=COLORS["card_bg"])
            f.grid(row=row, column=col, sticky="w", padx=(0, 60), pady=6)
            tk.Label(f, text=label, font=FONTS["small"], bg=COLORS["card_bg"], fg=COLORS["text_secondary"]).pack(anchor="w")
            tk.Label(f, text=value, font=FONTS["body_bold"], bg=COLORS["card_bg"], fg=COLORS["text_primary"]).pack(anchor="w")

        tk.Frame(inner, bg=COLORS["divider"], height=1).pack(fill="x", pady=(20, 16))

        # Void reason
        tk.Label(
            inner, text="Void Reason", font=FONTS["label"],
            bg=COLORS["card_bg"], fg=COLORS["text_primary"],
        ).pack(anchor="w", pady=(0, 6))

        reason_var = tk.StringVar(value="Wrong plate")
        reason_combo = ttk.Combobox(
            inner, textvariable=reason_var,
            values=["Wrong plate", "Wrong vehicle type", "Other"],
            state="readonly", font=FONTS["body"], width=28,
        )
        reason_combo.pack(anchor="w", ipady=4, pady=(0, 24))

        other_frame = tk.Frame(inner, bg=COLORS["card_bg"])
        tk.Label(other_frame, text="Notes (Required for 'Other')", font=FONTS["label"], bg=COLORS["card_bg"], fg=COLORS["text_primary"]).pack(anchor="w", pady=(0, 6))
        other_var = tk.StringVar()
        other_entry = StyledEntry(other_frame, textvariable=other_var, width=36)
        other_entry.pack(anchor="w", ipady=6)
        
        def _toggle_other(*args):
            if reason_var.get() == "Other":
                other_frame.pack(anchor="w", fill="x", pady=(0, 24), after=reason_combo)
            else:
                other_frame.pack_forget()
        
        reason_var.trace_add("write", _toggle_other)
        _toggle_other()

        # Warning text
        tk.Label(
            inner, text="This action cannot be undone. No payment will be recorded.",
            font=FONTS["small"], bg=COLORS["card_bg"], fg=COLORS["accent_red"],
        ).pack(anchor="w", pady=(0, 16))

        # Buttons row
        btn_row = tk.Frame(inner, bg=COLORS["card_bg"])
        btn_row.pack(anchor="w")

        confirm_btn = StyledButton(
            btn_row, text="  🚫  Confirm Void  ",
            color_key="btn_danger", hover_key="btn_danger_hover",
        )
        confirm_btn.pack(side="left", padx=(0, 12))

        cancel_btn = StyledButton(
            btn_row, text="  Cancel  ",
            color_key="btn_gray", hover_key="btn_gray_hover",
            command=self._show_void,
        )
        cancel_btn.pack(side="left")

        def _on_confirm_void():
            r = reason_var.get()
            if r == "Other":
                notes = other_var.get().strip()
                if not notes:
                    messagebox.showwarning("Missing Information", "Please provide a reason in the notes field.", parent=self.root)
                    return
                r = f"Other: {notes}"
                
            confirm_btn.configure(state="disabled")
            try:
                db.void_ticket(ticket["ticket_id"], r)
                messagebox.showinfo(
                    "Ticket Voided",
                    f"Ticket {ticket['ticket_id']} has been voided.\n\n"
                    f"Reason: {r}",
                    parent=self.root,
                )
                self._show_dashboard()
            except ValueError as e:
                messagebox.showerror("Error", str(e), parent=self.root)
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self.root)
            finally:
                try:
                    confirm_btn.configure(state="normal")
                except tk.TclError:
                    pass

        confirm_btn.configure(command=_on_confirm_void)

        # Back link
        tk.Label(inner, text="", bg=COLORS["card_bg"]).pack(pady=4)
        back_btn = tk.Label(
            inner, text="← Back to vehicle list", font=FONTS["small"],
            bg=COLORS["card_bg"], fg=COLORS["accent_blue"], cursor="hand2",
        )
        back_btn.pack(anchor="w")
        back_btn.bind("<Button-1>", lambda e: self._show_void())

    # ═══════════════════════════════════════════════════════════════════════
    # 5. REPORTS
    # ═══════════════════════════════════════════════════════════════════════

    def _show_reports(self):
        self._clear_content()
        self._set_active_nav("reports")

        # Scrollable wrapper
        canvas = tk.Canvas(self.content, bg=COLORS["body_bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.content, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=COLORS["body_bg"])

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

        # Bind mousewheel
        def _on_mousewheel(event):
            try:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except tk.TclError:
                pass
        self._mousewheel_binding_id = canvas.bind_all("<MouseWheel>", _on_mousewheel)

        wrapper = tk.Frame(scroll_frame, bg=COLORS["body_bg"])
        wrapper.pack(fill="x", expand=True, padx=28, pady=20)

        # ── Section A: Daily Revenue Summary ──
        rev_card = RoundedFrame(wrapper)
        rev_card.pack(fill="x", pady=(0, 18))

        rev_inner = tk.Frame(rev_card, bg=COLORS["card_bg"])
        rev_inner.pack(fill="x", padx=28, pady=24)

        tk.Label(
            rev_inner, text="📊  Today's Revenue Summary", font=FONTS["card_title"],
            bg=COLORS["card_bg"], fg=COLORS["text_primary"],
        ).pack(anchor="w", pady=(0, 4))
        tk.Label(
            rev_inner, text=datetime.now().strftime("%B %d, %Y"),
            font=FONTS["small"], bg=COLORS["card_bg"], fg=COLORS["text_secondary"],
        ).pack(anchor="w", pady=(0, 16))

        tk.Frame(rev_inner, bg=COLORS["divider"], height=1).pack(fill="x", pady=(0, 12))

        rev_cols = ("type_name", "transactions", "total_revenue", "avg_fee")
        rev_tree = ttk.Treeview(rev_inner, columns=rev_cols, show="headings", height=4)

        for col, (text, w) in {
            "type_name": ("Vehicle Type", 180),
            "transactions": ("Transactions", 140),
            "total_revenue": ("Total Revenue", 180),
            "avg_fee": ("Avg Fee", 140),
        }.items():
            rev_tree.heading(col, text=text, anchor="w")
            rev_tree.column(col, width=w, minwidth=80, anchor="w")

        rev_tree.pack(fill="x", pady=(0, 12))

        summary = db.get_daily_revenue_summary()
        for i, row in enumerate(summary):
            tag = "even" if i % 2 == 0 else "odd"
            rev_tree.insert("", "end", values=(
                row["type_name"],
                row["transactions"],
                format_currency(row["total_revenue"]),
                format_currency(row["avg_fee"]),
            ), tags=(tag,))

        rev_tree.tag_configure("even", background=COLORS["card_bg"])
        rev_tree.tag_configure("odd", background=COLORS["table_row_alt"])

        if not summary:
            rev_tree.insert("", "end", values=("", "", "No transactions today", ""))

        # Total revenue bar
        total = db.get_daily_total_revenue()
        total_frame = tk.Frame(
            rev_inner, bg=COLORS["counter_bg"],
            highlightbackground=COLORS["counter_border"], highlightthickness=1,
        )
        total_frame.pack(fill="x", ipady=10)

        total_inner = tk.Frame(total_frame, bg=COLORS["counter_bg"])
        total_inner.pack()
        tk.Label(
            total_inner, text="Total Revenue Today:  ", font=FONTS["body"],
            bg=COLORS["counter_bg"], fg=COLORS["text_secondary"],
        ).pack(side="left")
        tk.Label(
            total_inner, text=format_currency(total), font=(FONT_FAMILY, 20, "bold"),
            bg=COLORS["counter_bg"], fg=COLORS["accent_blue"],
        ).pack(side="left")

        StyledButton(
            rev_inner, text="  📥  Export Excel  ",
            color_key="btn_gray", hover_key="btn_gray_hover",
            command=lambda: export_to_excel(summary, f"Daily_Revenue_Summary_{datetime.now().strftime('%Y-%m-%d')}.xlsx"),
        ).pack(anchor="w", pady=(8, 0))

        # ── Section B: Long-Stay Alerts ──
        alert_card = RoundedFrame(wrapper)
        alert_card.pack(fill="x", pady=(0, 18))

        alert_inner = tk.Frame(alert_card, bg=COLORS["card_bg"])
        alert_inner.pack(fill="x", padx=28, pady=24)

        alert_title_row = tk.Frame(alert_inner, bg=COLORS["card_bg"])
        alert_title_row.pack(fill="x", pady=(0, 12))

        tk.Label(
            alert_title_row, text="⚠️  Long-Stay Alert", font=FONTS["card_title"],
            bg=COLORS["card_bg"], fg=COLORS["accent_orange"],
        ).pack(side="left")
        tk.Label(
            alert_title_row, text="Vehicles parked over 8 hours", font=FONTS["small"],
            bg=COLORS["card_bg"], fg=COLORS["text_secondary"],
        ).pack(side="right")

        tk.Frame(alert_inner, bg=COLORS["divider"], height=1).pack(fill="x", pady=(0, 12))

        alert_cols = ("ticket_id", "plate_no", "type_name", "entry_time", "elapsed")
        alert_tree = ttk.Treeview(alert_inner, columns=alert_cols, show="headings", height=5)

        for col, (text, w) in {
            "ticket_id": ("Ticket ID", 130),
            "plate_no": ("Plate No.", 150),
            "type_name": ("Vehicle Type", 140),
            "entry_time": ("Entry Time", 200),
            "elapsed": ("Hours Parked", 140),
        }.items():
            alert_tree.heading(col, text=text, anchor="w")
            alert_tree.column(col, width=w, minwidth=80, anchor="w")

        alert_tree.pack(fill="x")

        alerts = db.get_long_stay_alerts()
        if alerts:
            for i, a in enumerate(alerts):
                alert_tree.insert("", "end", values=(
                    a["ticket_id"],
                    a["plate_no"],
                    a["type_name"],
                    a["entry_time"],
                    format_elapsed(a["hours_elapsed"]),
                ), tags=("alert_row",))
            alert_tree.tag_configure("alert_row", background="#FEE2E2")
        else:
            alert_tree.insert("", "end", values=("", "", "No long-stay vehicles", "", ""))

        # ── Section C: Voided Tickets Today ──
        void_card = RoundedFrame(wrapper)
        void_card.pack(fill="x", pady=(0, 18))

        void_inner = tk.Frame(void_card, bg=COLORS["card_bg"])
        void_inner.pack(fill="x", padx=28, pady=24)

        void_title_row = tk.Frame(void_inner, bg=COLORS["card_bg"])
        void_title_row.pack(fill="x", pady=(0, 12))

        tk.Label(
            void_title_row, text="🚫  Voided Tickets Today", font=FONTS["card_title"],
            bg=COLORS["card_bg"], fg=COLORS["accent_red"],
        ).pack(side="left")
        tk.Label(
            void_title_row, text="Corrections made during this shift", font=FONTS["small"],
            bg=COLORS["card_bg"], fg=COLORS["text_secondary"],
        ).pack(side="right")

        tk.Frame(void_inner, bg=COLORS["divider"], height=1).pack(fill="x", pady=(0, 12))

        void_cols = ("ticket_id", "plate_no", "void_reason", "entry_time")
        void_tree = ttk.Treeview(void_inner, columns=void_cols, show="headings", height=5)

        for col, (text, w) in {
            "ticket_id": ("Ticket ID", 130),
            "plate_no": ("Plate No.", 150),
            "void_reason": ("Void Reason", 200),
            "entry_time": ("Entry Time", 200),
        }.items():
            void_tree.heading(col, text=text, anchor="w")
            void_tree.column(col, width=w, minwidth=80, anchor="w")

        void_tree.pack(fill="x")

        voided = db.get_voided_tickets_today()
        if voided:
            for i, v in enumerate(voided):
                tag = "void_even" if i % 2 == 0 else "void_odd"
                void_tree.insert("", "end", values=(
                    v["ticket_id"],
                    v["plate_no"],
                    v["void_reason"] or "—",
                    v["entry_time"],
                ), tags=(tag,))
            void_tree.tag_configure("void_even", background=COLORS["card_bg"])
            void_tree.tag_configure("void_odd", background=COLORS["table_row_alt"])
        else:
            void_tree.insert("", "end", values=("", "", "No voided tickets today", ""))

        StyledButton(
            void_inner, text="  📥  Export Excel  ",
            color_key="btn_gray", hover_key="btn_gray_hover",
            command=lambda: export_to_excel(voided, f"Voided_Tickets_{datetime.now().strftime('%Y-%m-%d')}.xlsx"),
        ).pack(anchor="w", pady=(8, 0))

    # ═══════════════════════════════════════════════════════════════════════
    # QR SCANNER
    # ═══════════════════════════════════════════════════════════════════════

    def _open_qr_scanner(self, on_result):
        """Opens a webcam QR scanner popup. on_result(ticket_id) is called when found."""
        try:
            import cv2
            from pyzbar import pyzbar
        except ImportError:
            messagebox.showerror(
                "Missing Library",
                "QR scanning requires opencv-python and pyzbar.\n"
                "Run: pip install opencv-python pyzbar",
                parent=self.root,
            )
            return

        popup = tk.Toplevel(self.root)
        popup.title("Scan QR Code")
        popup.configure(bg=COLORS["card_bg"])
        popup.resizable(False, False)
        popup.grab_set()

        w, h = 480, 560
        x = (popup.winfo_screenwidth() // 2) - (w // 2)
        y = (popup.winfo_screenheight() // 2) - (h // 2)
        popup.geometry(f"{w}x{h}+{x}+{y}")

        inner = tk.Frame(popup, bg=COLORS["card_bg"])
        inner.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(
            inner, text="Hold the ticket QR code up to the camera.",
            font=FONTS["small"], bg=COLORS["card_bg"],
            fg=COLORS["text_secondary"],
        ).pack(pady=(0, 8))

        cam_label = tk.Label(inner, bg="black")
        cam_label.pack()

        status_label = tk.Label(
            inner, text="Scanning...", font=FONTS["small"],
            bg=COLORS["card_bg"], fg=COLORS["accent_blue"],
        )
        status_label.pack(pady=(8, 0))

        cam_var = tk.StringVar(value="Cam 0 (DSHOW)")
        backends = ["Cam 0 (Default)", "Cam 0 (DSHOW)", "Cam 1 (Default)", "Cam 1 (DSHOW)", "Cam 2 (Default)", "Cam 2 (DSHOW)"]
        cam_select = ttk.Combobox(
            inner, textvariable=cam_var,
            values=backends,
            state="readonly", width=18, font=FONTS["small"]
        )
        cam_select.pack(pady=(8, 0))

        StyledButton(
            inner, text="Cancel",
            color_key="btn_gray", hover_key="btn_gray_hover",
            command=popup.destroy,
        ).pack(pady=(8, 0))

        # Use DSHOW with fixed resolution by default to bypass MSMF lag/timeouts
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap_container = [cap]
        self._scanner_running = True

        def _change_camera(event=None):
            sel = cam_var.get()
            idx = int(sel.split()[1])
            backend = cv2.CAP_DSHOW if "DSHOW" in sel else cv2.CAP_ANY
            
            if cap_container[0]:
                cap_container[0].release()
            
            cap = cv2.VideoCapture(idx, backend)
            # Force standard resolution to prevent DSHOW black screens
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap_container[0] = cap
            
            if not self._scanner_running:
                self._scanner_running = True
                _scan_loop()

        cam_select.bind("<<ComboboxSelected>>", _change_camera)

        def _scan_loop():
            if not self._scanner_running:
                return
            try:
                cap = cap_container[0]
                if not cap or not cap.isOpened():
                    popup.after(30, _scan_loop)
                    return
                
                ret, frame = cap.read()
                if ret:
                    codes = pyzbar.decode(frame)
                    for code in codes:
                        data = code.data.decode("utf-8").strip()
                        if data.startswith("TKT-"):
                            self._scanner_running = False
                            cap.release()
                            popup.destroy()
                            on_result(data)
                            return

                    # Show live camera feed
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame_rgb)
                    img = img.resize((440, 320))
                    self._scanner_photo = ImageTk.PhotoImage(img)
                    cam_label.configure(image=self._scanner_photo)

                popup.after(30, _scan_loop)
            except Exception as e:
                import traceback
                traceback.print_exc()
                self._scanner_running = False
                if cap_container[0]:
                    cap_container[0].release()

        def _on_close():
            self._scanner_running = False
            if cap_container[0]:
                cap_container[0].release()
            popup.destroy()

        popup.protocol("WM_DELETE_WINDOW", _on_close)
        _scan_loop()

    # ═══════════════════════════════════════════════════════════════════════
    # 6. ADMIN PANEL
    # ═══════════════════════════════════════════════════════════════════════

    def _show_admin_panel(self):
        if not self.logged_in_user or self.logged_in_user["role"] != "Admin":
            self._show_dashboard()
            return
            
        self._clear_content()
        self._set_active_nav("admin")

        canvas = tk.Canvas(self.content, bg=COLORS["body_bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.content, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=COLORS["body_bg"])

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

        def _on_mousewheel(event):
            try: canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except tk.TclError: pass
        self._mousewheel_binding_id = canvas.bind_all("<MouseWheel>", _on_mousewheel)

        wrapper = tk.Frame(scroll_frame, bg=COLORS["body_bg"])
        wrapper.pack(fill="x", expand=True, padx=28, pady=20)

        # ── Settings ──
        set_card = RoundedFrame(wrapper)
        set_card.pack(fill="x", pady=(0, 18))
        set_inner = tk.Frame(set_card, bg=COLORS["card_bg"])
        set_inner.pack(fill="x", padx=28, pady=24)
        
        tk.Label(set_inner, text="⚙️  System Settings", font=FONTS["card_title"], bg=COLORS["card_bg"], fg=COLORS["text_primary"]).pack(anchor="w", pady=(0, 16))
        tk.Frame(set_inner, bg=COLORS["divider"], height=1).pack(fill="x", pady=(0, 16))
        
        settings = db.get_settings()
        tk.Label(set_inner, text="Parking Facility Name", font=FONTS["label"], bg=COLORS["card_bg"]).pack(anchor="w")
        name_var = tk.StringVar(value=settings.get("parking_name", "SpotCheck"))
        StyledEntry(set_inner, textvariable=name_var, width=40).pack(anchor="w", ipady=4, pady=(0, 12))
        
        tk.Label(set_inner, text="Long-Stay Alert Threshold (Hours)", font=FONTS["label"], bg=COLORS["card_bg"]).pack(anchor="w")
        thresh_var = tk.StringVar(value=str(settings.get("long_stay_threshold", 8)))
        StyledEntry(set_inner, textvariable=thresh_var, width=15).pack(anchor="w", ipady=4, pady=(0, 12))
        
        tk.Label(set_inner, text="Lost Ticket Fee (₱)", font=FONTS["label"], bg=COLORS["card_bg"]).pack(anchor="w")
        lost_var = tk.StringVar(value=str(settings.get("lost_ticket_fee", 200.0)))
        StyledEntry(set_inner, textvariable=lost_var, width=15).pack(anchor="w", ipady=4, pady=(0, 16))
        
        def _save_settings():
            try:
                db.update_settings(0, name_var.get().strip(), int(thresh_var.get()), float(lost_var.get()))
                messagebox.showinfo("Success", "Settings saved successfully.")
                self.header.winfo_children()[0].winfo_children()[1].configure(text=name_var.get().strip())
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save settings: {e}")
                
        StyledButton(set_inner, text="Save Settings", command=_save_settings).pack(anchor="w")

        # ── Floors Management ──
        floor_card = RoundedFrame(wrapper)
        floor_card.pack(fill="x", pady=(0, 18))
        floor_inner = tk.Frame(floor_card, bg=COLORS["card_bg"])
        floor_inner.pack(fill="x", padx=28, pady=24)
        
        tk.Label(floor_inner, text="🏢  Floors & Capacity", font=FONTS["card_title"], bg=COLORS["card_bg"], fg=COLORS["text_primary"]).pack(anchor="w", pady=(0, 16))
        tk.Frame(floor_inner, bg=COLORS["divider"], height=1).pack(fill="x", pady=(0, 16))

        floor_add_frame = tk.Frame(floor_inner, bg=COLORS["card_bg"])
        floor_add_frame.pack(fill="x", pady=(0, 16))
        tk.Label(floor_add_frame, text="Floor Name", bg=COLORS["card_bg"]).grid(row=0, column=0, sticky="w", padx=4)
        f_name_var = tk.StringVar()
        StyledEntry(floor_add_frame, textvariable=f_name_var, width=20).grid(row=1, column=0, sticky="w", padx=4)
        
        tk.Label(floor_add_frame, text="Capacity", bg=COLORS["card_bg"]).grid(row=0, column=1, sticky="w", padx=4)
        f_cap_var = tk.StringVar()
        StyledEntry(floor_add_frame, textvariable=f_cap_var, width=10).grid(row=1, column=1, sticky="w", padx=4)
        
        def _add_floor():
            try:
                db.add_floor(f_name_var.get().strip(), int(f_cap_var.get()))
                f_name_var.set(""); f_cap_var.set("")
                _refresh_floors()
            except Exception as e:
                messagebox.showerror("Error", str(e))
                
        StyledButton(floor_add_frame, text="Add Floor", command=_add_floor).grid(row=1, column=2, padx=12)

        f_tree = ttk.Treeview(floor_inner, columns=("id", "name", "capacity"), show="headings", height=4)
        f_tree.heading("id", text="ID"); f_tree.column("id", width=50)
        f_tree.heading("name", text="Floor Name"); f_tree.column("name", width=200)
        f_tree.heading("capacity", text="Capacity"); f_tree.column("capacity", width=100)
        f_tree.pack(fill="x")
        
        def _refresh_floors():
            for i in f_tree.get_children(): f_tree.delete(i)
            for f in db.get_floors():
                f_tree.insert("", "end", values=(f["floor_id"], f["name"], f["capacity"]))
        _refresh_floors()

        def _delete_floor():
            sel = f_tree.selection()
            if sel:
                db.remove_floor(f_tree.item(sel[0])["values"][0])
                _refresh_floors()
        StyledButton(floor_inner, text="Delete Selected Floor", color_key="btn_danger", hover_key="btn_danger_hover", command=_delete_floor).pack(anchor="w", pady=(8, 0))

        # ── Vehicle Types Management ──
        veh_card = RoundedFrame(wrapper)
        veh_card.pack(fill="x", pady=(0, 18))
        veh_inner = tk.Frame(veh_card, bg=COLORS["card_bg"])
        veh_inner.pack(fill="x", padx=28, pady=24)
        
        tk.Label(veh_inner, text="🚗  Vehicle Types & Pricing", font=FONTS["card_title"], bg=COLORS["card_bg"], fg=COLORS["text_primary"]).pack(anchor="w", pady=(0, 16))
        tk.Frame(veh_inner, bg=COLORS["divider"], height=1).pack(fill="x", pady=(0, 16))

        veh_add_frame = tk.Frame(veh_inner, bg=COLORS["card_bg"])
        veh_add_frame.pack(fill="x", pady=(0, 16))
        tk.Label(veh_add_frame, text="Type Name", bg=COLORS["card_bg"]).grid(row=0, column=0, sticky="w", padx=4)
        v_name_var = tk.StringVar()
        StyledEntry(veh_add_frame, textvariable=v_name_var, width=20).grid(row=1, column=0, sticky="w", padx=4)
        
        tk.Label(veh_add_frame, text="Hourly Rate (₱)", bg=COLORS["card_bg"]).grid(row=0, column=1, sticky="w", padx=4)
        v_rate_var = tk.StringVar()
        StyledEntry(veh_add_frame, textvariable=v_rate_var, width=10).grid(row=1, column=1, sticky="w", padx=4)
        
        def _add_veh():
            try:
                db.add_vehicle_type(v_name_var.get().strip(), float(v_rate_var.get()))
                v_name_var.set(""); v_rate_var.set("")
                self.vehicle_types = db.get_vehicle_types()
                _refresh_vehs()
            except Exception as e:
                messagebox.showerror("Error", str(e))
                
        StyledButton(veh_add_frame, text="Add Vehicle", command=_add_veh).grid(row=1, column=2, padx=12)

        v_tree = ttk.Treeview(veh_inner, columns=("id", "name", "rate"), show="headings", height=4)
        v_tree.heading("id", text="ID"); v_tree.column("id", width=50)
        v_tree.heading("name", text="Vehicle Type"); v_tree.column("name", width=200)
        v_tree.heading("rate", text="Hourly Rate (₱)"); v_tree.column("rate", width=150)
        v_tree.pack(fill="x")
        
        def _refresh_vehs():
            for i in v_tree.get_children(): v_tree.delete(i)
            for v in db.get_vehicle_types():
                v_tree.insert("", "end", values=(v["type_id"], v["type_name"], v["hourly_rate"]))
        _refresh_vehs()

        def _delete_veh():
            sel = v_tree.selection()
            if sel:
                db.remove_vehicle_type(v_tree.item(sel[0])["values"][0])
                self.vehicle_types = db.get_vehicle_types()
                _refresh_vehs()
        StyledButton(veh_inner, text="Delete Selected Vehicle", color_key="btn_danger", hover_key="btn_danger_hover", command=_delete_veh).pack(anchor="w", pady=(8, 0))

        # ── User Management ──
        user_card = RoundedFrame(wrapper)
        user_card.pack(fill="x", pady=(0, 18))
        user_inner = tk.Frame(user_card, bg=COLORS["card_bg"])
        user_inner.pack(fill="x", padx=28, pady=24)
        
        tk.Label(user_inner, text="👥  User Management", font=FONTS["card_title"], bg=COLORS["card_bg"], fg=COLORS["text_primary"]).pack(anchor="w", pady=(0, 16))
        tk.Frame(user_inner, bg=COLORS["divider"], height=1).pack(fill="x", pady=(0, 16))
        
        # Add User Form
        add_frame = tk.Frame(user_inner, bg=COLORS["card_bg"])
        add_frame.pack(fill="x", pady=(0, 24))
        
        def limit_password(*args):
            val = p_var.get()
            if len(val) > 32:
                p_var.set(val[:32])
                
        tk.Label(add_frame, text="Username", bg=COLORS["card_bg"]).grid(row=0, column=0, sticky="w", pady=4, padx=4)
        u_var = tk.StringVar()
        StyledEntry(add_frame, textvariable=u_var, width=20).grid(row=1, column=0, sticky="w", pady=4, padx=4)
        
        tk.Label(add_frame, text="Display Name", bg=COLORS["card_bg"]).grid(row=0, column=1, sticky="w", pady=4, padx=4)
        d_var = tk.StringVar()
        StyledEntry(add_frame, textvariable=d_var, width=20).grid(row=1, column=1, sticky="w", pady=4, padx=4)
        
        tk.Label(add_frame, text="Password", bg=COLORS["card_bg"]).grid(row=0, column=2, sticky="w", pady=4, padx=4)
        p_var = tk.StringVar()
        p_var.trace_add("write", limit_password)
        StyledEntry(add_frame, textvariable=p_var, show="*", width=20).grid(row=1, column=2, sticky="w", pady=4, padx=4)
        
        tk.Label(add_frame, text="Confirm Password", bg=COLORS["card_bg"]).grid(row=0, column=3, sticky="w", pady=4, padx=4)
        cp_var = tk.StringVar()
        StyledEntry(add_frame, textvariable=cp_var, show="*", width=20).grid(row=1, column=3, sticky="w", pady=4, padx=4)
        
        tk.Label(add_frame, text="Role", bg=COLORS["card_bg"]).grid(row=0, column=4, sticky="w", pady=4, padx=4)
        r_var = tk.StringVar(value="Staff")
        ttk.Combobox(add_frame, textvariable=r_var, values=["Staff", "Admin"], state="readonly", width=12).grid(row=1, column=4, sticky="w", pady=4, padx=4)
        
        def _add_user():
            if not u_var.get() or not d_var.get() or not p_var.get():
                messagebox.showerror("Error", "All fields are required.")
                return
            if p_var.get() != cp_var.get():
                messagebox.showerror("Error", "Passwords do not match.")
                return
            try:
                db.create_user(u_var.get().strip(), d_var.get().strip(), p_var.get(), r_var.get())
                messagebox.showinfo("Success", "User added successfully.")
                u_var.set(""); d_var.set(""); p_var.set(""); cp_var.set("")
                _refresh_users()
            except Exception as e:
                messagebox.showerror("Error", str(e))
                
        StyledButton(add_frame, text="Add User", command=_add_user).grid(row=1, column=5, padx=12, pady=4)

        # Users Table
        u_tree = ttk.Treeview(user_inner, columns=("username", "display_name", "role"), show="headings", height=5)
        u_tree.heading("username", text="Username", anchor="w")
        u_tree.heading("display_name", text="Display Name", anchor="w")
        u_tree.heading("role", text="Role", anchor="w")
        u_tree.column("username", width=150, anchor="w")
        u_tree.column("display_name", width=200, anchor="w")
        u_tree.column("role", width=100, anchor="w")
        u_tree.pack(fill="x")
        
        def _refresh_users():
            for i in u_tree.get_children(): u_tree.delete(i)
            for i, u in enumerate(db.get_all_users()):
                tag = "even" if i % 2 == 0 else "odd"
                u_tree.insert("", "end", values=(u["username"], u["display_name"], u["role"]), tags=(tag,))
        
        u_tree.tag_configure("even", background=COLORS["card_bg"])
        u_tree.tag_configure("odd", background=COLORS["table_row_alt"])
        _refresh_users()

        user_action_frame = tk.Frame(user_inner, bg=COLORS["card_bg"])
        user_action_frame.pack(fill="x", pady=(12, 0))

        def _delete_selected_user():
            selected = u_tree.selection()
            if not selected:
                messagebox.showwarning("Select User", "Please select a user to delete.")
                return
            username = u_tree.item(selected[0])["values"][0]
            if username == self.logged_in_user["username"]:
                messagebox.showerror("Error", "You cannot delete your own account.")
                return
            if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete user '{username}'?"):
                try:
                    db.delete_user(username)
                    messagebox.showinfo("Success", f"User '{username}' deleted successfully.")
                    _refresh_users()
                except Exception as e:
                    messagebox.showerror("Error", str(e))

        def _reset_password():
            selected = u_tree.selection()
            if not selected:
                messagebox.showwarning("Select User", "Please select a user to reset password.")
                return
            username = u_tree.item(selected[0])["values"][0]
            
            # Use simpledialog for new password
            from tkinter import simpledialog
            new_pass = simpledialog.askstring("Reset Password", f"Enter new password for {username}:", show="*")
            if not new_pass:
                return
            
            try:
                db.reset_password(username, new_pass)
                messagebox.showinfo("Success", f"Password for '{username}' has been reset.")
            except Exception as e:
                messagebox.showerror("Error", str(e))

        StyledButton(user_action_frame, text="Delete User", color_key="btn_danger", hover_key="btn_danger_hover", command=_delete_selected_user).pack(side="left", padx=(0, 8))
        StyledButton(user_action_frame, text="Reset Password", color_key="btn_gray", hover_key="btn_gray_hover", command=_reset_password).pack(side="left")

    # ═══════════════════════════════════════════════════════════════════════
    # 7. TRANSACTION HISTORY
    # ═══════════════════════════════════════════════════════════════════════

    def _show_history(self):
        if not self.logged_in_user or self.logged_in_user["role"] != "Admin":
            self._show_dashboard()
            return

        self._clear_content()
        self._set_active_nav("history")

        wrapper = tk.Frame(self.content, bg=COLORS["body_bg"])
        wrapper.pack(fill="both", expand=True, padx=28, pady=20)

        # ── Filter bar ──
        filter_card = RoundedFrame(wrapper)
        filter_card.pack(fill="x", pady=(0, 18))

        filter_inner = tk.Frame(filter_card, bg=COLORS["card_bg"])
        filter_inner.pack(fill="x", padx=28, pady=20)

        tk.Label(
            filter_inner, text="Transaction History", font=FONTS["card_title"],
            bg=COLORS["card_bg"], fg=COLORS["text_primary"],
        ).pack(anchor="w", pady=(0, 12))

        filter_row = tk.Frame(filter_inner, bg=COLORS["card_bg"])
        filter_row.pack(fill="x")

        today_str = datetime.now().strftime("%Y-%m-%d")

        tk.Label(filter_row, text="From:", font=FONTS["label"],
                 bg=COLORS["card_bg"]).pack(side="left", padx=(0, 4))
        date_from_var = tk.StringVar(value=today_str)
        date_from_entry = DateEntry(filter_row, textvariable=date_from_var, date_pattern='y-mm-dd', width=12, state="readonly", showweeknumbers=False)
        date_from_entry.pack(side="left", padx=(0, 12))
        date_from_entry._calendar.unbind('<FocusOut>')

        tk.Label(filter_row, text="To:", font=FONTS["label"],
                 bg=COLORS["card_bg"]).pack(side="left", padx=(0, 4))
        date_to_var = tk.StringVar(value=today_str)
        date_to_entry = DateEntry(filter_row, textvariable=date_to_var, date_pattern='y-mm-dd', width=12, state="readonly", showweeknumbers=False)
        date_to_entry.pack(side="left", padx=(0, 12))
        date_to_entry._calendar.unbind('<FocusOut>')

        tk.Label(filter_row, text="Plate:", font=FONTS["label"],
                 bg=COLORS["card_bg"]).pack(side="left", padx=(0, 4))
        plate_var = tk.StringVar()
        StyledEntry(filter_row, textvariable=plate_var, width=12).pack(
            side="left", ipady=4, padx=(0, 12))

        StyledButton(
            filter_row, text="  🔍 Search  ",
            color_key="btn_primary", hover_key="btn_primary_hover",
            command=lambda: _load_history(),
        ).pack(side="left", padx=(0, 8))

        StyledButton(
            filter_row, text="  📥  Export Excel  ",
            color_key="btn_gray", hover_key="btn_gray_hover",
            command=lambda: export_to_excel(
                self._history_data,
                f"transactions_{date_from_var.get()}_to_{date_to_var.get()}.xlsx"
            ) if hasattr(self, '_history_data') else None,
        ).pack(side="left")

        # ── Table ──
        table_card = RoundedFrame(wrapper)
        table_card.pack(fill="both", expand=True)

        table_inner = tk.Frame(table_card, bg=COLORS["card_bg"])
        table_inner.pack(fill="both", expand=True, padx=20, pady=(16, 20))

        subtitle_label = tk.Label(
            table_inner, text="0 records | Total Revenue: ₱0.00",
            font=FONTS["small"], bg=COLORS["card_bg"],
            fg=COLORS["text_secondary"],
        )
        subtitle_label.pack(anchor="w", pady=(0, 8))

        cols = ("ticket_id", "plate_no", "type_name", "entry_time",
                "exit_time", "duration", "total_fee", "payment_method")
        h_tree = ttk.Treeview(table_inner, columns=cols, show="headings", height=18)

        col_config = {
            "ticket_id": ("Ticket ID", 120),
            "plate_no": ("Plate No.", 130),
            "type_name": ("Vehicle Type", 120),
            "entry_time": ("Entry Time", 165),
            "exit_time": ("Exit Time", 165),
            "duration": ("Duration", 110),
            "total_fee": ("Total Fee", 110),
            "payment_method": ("Payment", 120),
        }
        for col, (text, w) in col_config.items():
            h_tree.heading(col, text=text, anchor="w")
            h_tree.column(col, width=w, minwidth=80, anchor="w")

        h_tree.pack(fill="both", expand=True)

        h_tree.tag_configure("even", background=COLORS["card_bg"])
        h_tree.tag_configure("odd", background=COLORS["table_row_alt"])

        self._history_data = []

        def _load_history():
            df = date_from_var.get().strip()
            dt = date_to_var.get().strip()
            pq = plate_var.get().strip() or None
            self._history_data = db.get_transaction_history(
                date_from=df or None, date_to=dt or None, plate_query=pq
            )

            for item in h_tree.get_children():
                h_tree.delete(item)

            if not self._history_data:
                h_tree.insert(
                    "", "end",
                    values=("", "", "", "No transactions found for selected filters", "", "", "", ""),
                )
                subtitle_label.configure(text="0 records | Total Revenue: ₱0.00")
                return

            total_rev = 0.0
            for i, t in enumerate(self._history_data):
                tag = "even" if i % 2 == 0 else "odd"
                total_rev += t["total_fee"]
                h_tree.insert(
                    "", "end",
                    values=(
                        t["ticket_id"],
                        t["plate_no"],
                        t["type_name"],
                        t["entry_time"],
                        t["exit_time"],
                        format_elapsed(t["hours_elapsed"]),
                        format_currency(t["total_fee"]),
                        t["payment_method"],
                    ),
                    tags=(tag,),
                )

            count = len(self._history_data)
            subtitle_label.configure(
                text=f"{count} record{'s' if count != 1 else ''} | "
                     f"Total Revenue: {format_currency(total_rev)}"
            )

        _load_history()
