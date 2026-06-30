import math
import os
import sqlite3
from datetime import datetime

# ---------------------------------------------------------------------------
# Database path — always sits next to this script
# ---------------------------------------------------------------------------
_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "spotcheck.db")


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

def get_connection() -> sqlite3.Connection:
    """Return a connection with foreign keys enabled and Row factory."""
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Initialization / migration
# ---------------------------------------------------------------------------

def initialize_database() -> None:
    """Create all tables, seed defaults, and handle migrations."""
    conn = get_connection()
    cur = conn.cursor()

    # ---- Create tables ----
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS VehicleType (
            type_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            type_name  TEXT    NOT NULL,
            hourly_rate REAL  NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS Users (
            username      TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            display_name  TEXT NOT NULL,
            role          TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS Floor (
            floor_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT NOT NULL,
            capacity INTEGER NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS Settings (
            id              INTEGER PRIMARY KEY,
            total_capacity  INTEGER NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS Ticket (
            ticket_id   TEXT     PRIMARY KEY,
            plate_no    TEXT     NOT NULL,
            type_id     INTEGER  NOT NULL REFERENCES VehicleType(type_id),
            floor_id    INTEGER  REFERENCES Floor(floor_id),
            entry_time  DATETIME NOT NULL,
            status      TEXT     NOT NULL DEFAULT 'Active',
            void_reason TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS Payment (
            payment_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id      TEXT    NOT NULL REFERENCES Ticket(ticket_id),
            exit_time      DATETIME NOT NULL,
            total_fee      REAL    NOT NULL,
            payment_method TEXT    NOT NULL
        )
        """
    )

    # ---- Migration: add void_reason if missing ----
    columns = [row["name"] for row in cur.execute("PRAGMA table_info(Ticket)")]
    if "void_reason" not in columns:
        cur.execute("ALTER TABLE Ticket ADD COLUMN void_reason TEXT")
    
    if "void_time" not in columns:
        cur.execute("ALTER TABLE Ticket ADD COLUMN void_time DATETIME")

    # ---- Seed Floor (Migration) ----
    cur.execute("SELECT COUNT(*) AS cnt FROM Floor")
    if cur.fetchone()["cnt"] == 0:
        cur.execute("SELECT total_capacity FROM Settings WHERE id = 1")
        row = cur.fetchone()
        cap = row["total_capacity"] if row else 50
        cur.execute("INSERT INTO Floor (name, capacity) VALUES (?, ?)", ("Floor 1", cap))

    if "floor_id" not in columns:
        cur.execute("ALTER TABLE Ticket ADD COLUMN floor_id INTEGER REFERENCES Floor(floor_id)")
        cur.execute("UPDATE Ticket SET floor_id = 1 WHERE floor_id IS NULL")

    settings_cols = [row["name"] for row in cur.execute("PRAGMA table_info(Settings)")]
    if "parking_name" not in settings_cols:
        cur.execute("ALTER TABLE Settings ADD COLUMN parking_name TEXT DEFAULT 'SpotCheck Parking'")
    if "long_stay_threshold" not in settings_cols:
        cur.execute("ALTER TABLE Settings ADD COLUMN long_stay_threshold INTEGER DEFAULT 8")
    if "lost_ticket_fee" not in settings_cols:
        cur.execute("ALTER TABLE Settings ADD COLUMN lost_ticket_fee REAL DEFAULT 200.0")
    if "overnight_fee" not in settings_cols:
        cur.execute("ALTER TABLE Settings ADD COLUMN overnight_fee REAL DEFAULT 150.0")

    # ---- Seed VehicleType ----
    cur.execute("SELECT COUNT(*) AS cnt FROM VehicleType")
    if cur.fetchone()["cnt"] == 0:
        cur.execute(
            "INSERT INTO VehicleType (type_name, hourly_rate) VALUES (?, ?)",
            ("Car", 50),
        )
        cur.execute(
            "INSERT INTO VehicleType (type_name, hourly_rate) VALUES (?, ?)",
            ("Motorcycle", 30),
        )

    # ---- Seed Settings ----
    cur.execute("SELECT COUNT(*) AS cnt FROM Settings")
    if cur.fetchone()["cnt"] == 0:
        cur.execute(
            "INSERT INTO Settings (id, total_capacity, parking_name, long_stay_threshold, lost_ticket_fee, overnight_fee) VALUES (1, 50, 'SpotCheck Parking', 8, 200.0, 150.0)"
        )

    # ---- Seed Users ----
    cur.execute("SELECT COUNT(*) AS cnt FROM Users")
    if cur.fetchone()["cnt"] == 0:
        import hashlib
        default_hash = hashlib.sha256("admin".encode()).hexdigest()
        cur.execute(
            "INSERT INTO Users (username, password_hash, display_name, role) VALUES (?, ?, ?, ?)",
            ("admin", default_hash, "Super Admin", "Admin"),
        )

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Vehicle types
# ---------------------------------------------------------------------------

def get_vehicle_types() -> list[dict]:
    """Return all vehicle types."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM VehicleType").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_vehicle_type(type_name: str, hourly_rate: float) -> None:
    """Add a new vehicle type."""
    conn = get_connection()
    conn.execute("INSERT INTO VehicleType (type_name, hourly_rate) VALUES (?, ?)", (type_name, hourly_rate))
    conn.commit()
    conn.close()

def update_vehicle_type(type_id: int, hourly_rate: float) -> None:
    """Update the hourly rate for a specific vehicle type."""
    conn = get_connection()
    conn.execute("UPDATE VehicleType SET hourly_rate = ? WHERE type_id = ?", (hourly_rate, type_id))
    conn.commit()
    conn.close()

def remove_vehicle_type(type_id: int) -> None:
    """Remove a vehicle type."""
    conn = get_connection()
    conn.execute("DELETE FROM VehicleType WHERE type_id = ?", (type_id,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Capacity helpers
# ---------------------------------------------------------------------------

def get_total_capacity() -> int:
    """Return the total parking capacity summed from Floor table."""
    conn = get_connection()
    row = conn.execute(
        "SELECT SUM(capacity) AS total_capacity FROM Floor"
    ).fetchone()
    conn.close()
    return row["total_capacity"] or 0

def get_floors() -> list[dict]:
    """Return all floors and their capacities."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM Floor ORDER BY floor_id ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_floor(name: str, capacity: int) -> None:
    conn = get_connection()
    conn.execute("INSERT INTO Floor (name, capacity) VALUES (?, ?)", (name, capacity))
    conn.commit()
    conn.close()

def update_floor_capacity(floor_id: int, capacity: int) -> None:
    conn = get_connection()
    conn.execute("UPDATE Floor SET capacity = ? WHERE floor_id = ?", (capacity, floor_id))
    conn.commit()
    conn.close()

def remove_floor(floor_id: int) -> None:
    """Remove a floor. Raises ValueError if active tickets exist on it."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Check for active tickets on this floor
        active = cur.execute(
            "SELECT COUNT(*) AS cnt FROM Ticket WHERE floor_id = ? AND status = 'Active'",
            (floor_id,)
        ).fetchone()
        if active["cnt"] > 0:
            raise ValueError(
                f"Cannot delete: {active['cnt']} active ticket(s) are still assigned to this floor. "
                "Please check out or void those vehicles first."
            )

        # Check this isn't the last floor
        floor_count = cur.execute("SELECT COUNT(*) AS cnt FROM Floor").fetchone()
        if floor_count["cnt"] <= 1:
            raise ValueError("Cannot delete the last remaining floor.")

        # Reassign closed/voided tickets to NULL so the FK doesn't block deletion
        cur.execute(
            "UPDATE Ticket SET floor_id = NULL WHERE floor_id = ? AND status != 'Active'",
            (floor_id,)
        )
        cur.execute("DELETE FROM Floor WHERE floor_id = ?", (floor_id,))
        conn.commit()
    except ValueError:
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def get_settings() -> dict:
    """Retrieve global system settings."""
    conn = get_connection()
    row = conn.execute("SELECT total_capacity, parking_name, long_stay_threshold, lost_ticket_fee FROM Settings WHERE id = 1").fetchone()
    conn.close()
    return dict(row) if row else {}

def update_settings(total_capacity: int, parking_name: str, long_stay_threshold: int, lost_ticket_fee: float) -> None:
    """Update global system settings."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE Settings SET total_capacity = ?, parking_name = ?, long_stay_threshold = ?, lost_ticket_fee = ? WHERE id = 1",
        (total_capacity, parking_name, long_stay_threshold, lost_ticket_fee)
    )
    conn.commit()
    conn.close()


def get_available_slots() -> int:
    """Return total_capacity minus the number of currently Active tickets."""
    conn = get_connection()
    row = conn.execute(
        """
        SELECT
            (SELECT SUM(capacity) FROM Floor)
            -
            (SELECT COUNT(*) FROM Ticket WHERE status = 'Active')
        AS available
        """
    ).fetchone()
    conn.close()
    return row["available"] or 0

def get_available_spots_by_floor() -> list[dict]:
    """Return available spots for each floor."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT 
            f.floor_id, 
            f.name, 
            f.capacity,
            (f.capacity - (SELECT COUNT(*) FROM Ticket t WHERE t.floor_id = f.floor_id AND t.status = 'Active')) AS available
        FROM Floor f
        ORDER BY f.floor_id ASC
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Ticket ID generator (private)
# ---------------------------------------------------------------------------

def _next_ticket_id(cursor: sqlite3.Cursor) -> str:
    """Generate the next ticket ID in the form TKT-NNNN."""
    row = cursor.execute(
        "SELECT MAX(CAST(SUBSTR(ticket_id, 5) AS INT)) AS max_num FROM Ticket"
    ).fetchone()
    next_num = (row["max_num"] or 0) + 1
    return "TKT-" + str(next_num).zfill(4)


# ---------------------------------------------------------------------------
# Entry / exit / void
# ---------------------------------------------------------------------------

def log_entry(plate_no: str, type_id: int, floor_id: int) -> str:
    """
    Log a new parking entry.

    Returns the generated ticket_id.
    Raises ValueError if plate is empty or parking is full.
    """
    plate_no = plate_no.strip().upper()
    if not plate_no:
        raise ValueError("Plate number cannot be empty.")

    # Check capacity for specific floor
    conn = get_connection()
    cur = conn.cursor()
    floor_row = cur.execute(
        """
        SELECT capacity - (SELECT COUNT(*) FROM Ticket WHERE floor_id = ? AND status = 'Active') AS available
        FROM Floor WHERE floor_id = ?
        """, (floor_id, floor_id)
    ).fetchone()
    if not floor_row or floor_row["available"] <= 0:
        conn.close()
        raise ValueError("Selected floor is full. Cannot log a new entry.")

    try:
        cur.execute("BEGIN")
        ticket_id = _next_ticket_id(cur)
        cur.execute(
            """
            INSERT INTO Ticket (ticket_id, plate_no, type_id, floor_id, entry_time, status)
            VALUES (?, ?, ?, ?, datetime('now','localtime'), 'Active')
            """,
            (ticket_id, plate_no, type_id, floor_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return ticket_id


def get_active_tickets() -> list[dict]:
    """
    Return all Active tickets with type_name and hours_elapsed.

    hours_elapsed is computed via julianday difference.
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            t.ticket_id,
            t.plate_no,
            t.type_id,
            v.type_name,
            v.hourly_rate,
            t.entry_time,
            t.status,
            t.void_reason,
            ROUND(
                (julianday(datetime('now','localtime')) - julianday(t.entry_time)) * 24,
                2
            ) AS hours_elapsed
        FROM Ticket t
        JOIN VehicleType v ON t.type_id = v.type_id
        WHERE t.status = 'Active'
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_overstaying_tickets(hours_threshold: float = None) -> list[dict]:
    """
    Return Active tickets that have been parked for longer than hours_threshold.
    If hours_threshold is None, fetches long_stay_threshold from Settings.
    """
    if hours_threshold is None:
        hours_threshold = float(get_settings().get("long_stay_threshold", 24))

    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            t.ticket_id,
            t.plate_no,
            t.type_id,
            v.type_name,
            v.hourly_rate,
            t.entry_time,
            t.status,
            t.void_reason,
            ROUND(
                (julianday(datetime('now','localtime')) - julianday(t.entry_time)) * 24,
                2
            ) AS hours_elapsed
        FROM Ticket t
        JOIN VehicleType v ON t.type_id = v.type_id
        WHERE t.status = 'Active'
          AND (julianday(datetime('now','localtime')) - julianday(t.entry_time)) * 24 >= ?
        ORDER BY hours_elapsed DESC
        """, (hours_threshold,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_active_ticket_count() -> int:
    """Return the number of currently Active tickets."""
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(*) AS cnt FROM Ticket WHERE status = 'Active'"
    ).fetchone()
    conn.close()
    return row["cnt"]


def search_ticket(query: str) -> dict | None:
    """
    Search for a ticket by ticket_id OR plate_no.

    Returns the most recent match (by entry_time) or None.
    """
    query = query.strip().upper()
    conn = get_connection()
    row = conn.execute(
        """
        SELECT
            t.ticket_id,
            t.plate_no,
            t.type_id,
            v.type_name,
            v.hourly_rate,
            t.entry_time,
            t.status,
            t.void_reason,
            ROUND(
                (julianday(datetime('now','localtime')) - julianday(t.entry_time)) * 24,
                2
            ) AS hours_elapsed
        FROM Ticket t
        JOIN VehicleType v ON t.type_id = v.type_id
        WHERE t.ticket_id = ? OR t.plate_no = ?
        ORDER BY t.entry_time DESC
        LIMIT 1
        """,
        (query, query),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def compute_fee(hours_elapsed: float, hourly_rate: float) -> float:
    """
    Compute parking fee: ceil(hours) × rate, minimum 1 hour.
    """
    billable_hours = max(1, math.ceil(hours_elapsed))
    return billable_hours * hourly_rate


def log_exit(ticket_id: str, payment_method: str) -> dict:
    """
    Close an Active ticket and record payment.

    Returns a receipt dict.
    Raises ValueError if ticket not found, already closed, or already voided.
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN")

        row = cur.execute(
            """
            SELECT
                t.ticket_id,
                t.plate_no,
                t.type_id,
                v.type_name,
                v.hourly_rate,
                t.entry_time,
                t.status,
                ROUND(
                    (julianday(datetime('now','localtime')) - julianday(t.entry_time)) * 24,
                    2
                ) AS hours_elapsed
            FROM Ticket t
            JOIN VehicleType v ON t.type_id = v.type_id
            WHERE t.ticket_id = ?
            """,
            (ticket_id,),
        ).fetchone()

        if row is None:
            raise ValueError("Ticket not found. Check the ticket ID or plate number.")
        if row["status"] == "Closed":
            raise ValueError("This ticket is already closed.")
        if row["status"] == "Voided":
            raise ValueError("This ticket has already been voided.")

        hours_elapsed = row["hours_elapsed"]
        hourly_rate = row["hourly_rate"]
        total_fee = compute_fee(hours_elapsed, hourly_rate)

        cur.execute(
            "UPDATE Ticket SET status = 'Closed' WHERE ticket_id = ?",
            (ticket_id,),
        )

        cur.execute(
            """
            INSERT INTO Payment (ticket_id, exit_time, total_fee, payment_method)
            VALUES (?, datetime('now','localtime'), ?, ?)
            """,
            (ticket_id, total_fee, payment_method),
        )

        conn.commit()

        receipt = {
            "ticket_id": row["ticket_id"],
            "plate_no": row["plate_no"],
            "type_name": row["type_name"],
            "entry_time": row["entry_time"],
            "exit_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "hours_elapsed": hours_elapsed,
            "hourly_rate": hourly_rate,
            "total_fee": total_fee,
            "payment_method": payment_method,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return receipt


def log_lost_ticket_exit(
    plate_no: str,
    payment_method: str
) -> dict:
    """
    Process exit for a vehicle whose driver lost their ticket.
    Searches for the most recent Active ticket with matching plate_no.
    Uses lost_ticket_fee from Settings instead of computing from hours.
    Adds overnight_fee if dates differ.
    Returns a receipt dict.
    Raises ValueError if no active ticket found for that plate.
    """
    plate_no = plate_no.strip().upper()
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN")
        row = cur.execute(
            """
            SELECT t.ticket_id, t.plate_no, t.type_id, v.type_name,
                   v.hourly_rate, t.entry_time, t.status,
                   ROUND(
                       (julianday(datetime('now','localtime'))
                       - julianday(t.entry_time)) * 24, 2
                   ) AS hours_elapsed
            FROM Ticket t
            JOIN VehicleType v ON t.type_id = v.type_id
            WHERE t.plate_no = ? AND t.status = 'Active'
            ORDER BY t.entry_time DESC
            LIMIT 1
            """,
            (plate_no,),
        ).fetchone()

        if row is None:
            raise ValueError(
                f"No active ticket found for plate {plate_no}."
            )

        settings = get_settings()
        hours_elapsed = row["hours_elapsed"]
        hourly_rate = row["hourly_rate"]
        parking_fee = compute_fee(hours_elapsed, hourly_rate)
        total_fee = parking_fee + settings.get("lost_ticket_fee", 200.0)

        cur.execute(
            "UPDATE Ticket SET status = 'Closed' WHERE ticket_id = ?",
            (row["ticket_id"],),
        )
        cur.execute(
            """
            INSERT INTO Payment (ticket_id, exit_time, total_fee, payment_method)
            VALUES (?, datetime('now','localtime'), ?, ?)
            """,
            (row["ticket_id"], total_fee, payment_method),
        )
        conn.commit()

        return {
            "ticket_id": row["ticket_id"],
            "plate_no": row["plate_no"],
            "type_name": row["type_name"],
            "entry_time": row["entry_time"],
            "exit_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "hours_elapsed": row["hours_elapsed"],
            "hourly_rate": row["hourly_rate"],
            "total_fee": total_fee,
            "payment_method": payment_method,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def void_ticket(ticket_id: str, void_reason: str) -> dict:
    """
    Void an Active ticket.

    Returns a dict with ticket info.
    Raises ValueError if ticket not found, already closed, or already voided.
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN")

        row = cur.execute(
            """
            SELECT
                t.ticket_id,
                t.plate_no,
                t.type_id,
                v.type_name,
                t.entry_time,
                t.status
            FROM Ticket t
            JOIN VehicleType v ON t.type_id = v.type_id
            WHERE t.ticket_id = ?
            """,
            (ticket_id,),
        ).fetchone()

        if row is None:
            raise ValueError("Ticket not found. Check the ticket ID or plate number.")
        if row["status"] == "Closed":
            raise ValueError("This ticket is already closed.")
        if row["status"] == "Voided":
            raise ValueError("This ticket has already been voided.")

        cur.execute(
            "UPDATE Ticket SET status = 'Voided', void_reason = ?, void_time = datetime('now','localtime') WHERE ticket_id = ?",
            (void_reason, ticket_id),
        )

        conn.commit()

        result = {
            "ticket_id": row["ticket_id"],
            "plate_no": row["plate_no"],
            "type_name": row["type_name"],
            "entry_time": row["entry_time"],
            "status": "Voided",
            "void_reason": void_reason,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return result


# ---------------------------------------------------------------------------
# Payment lookup
# ---------------------------------------------------------------------------

def get_payment_for_ticket(ticket_id: str) -> dict | None:
    """Return the Payment row for a given ticket_id, or None."""
    conn = get_connection()
    row = conn.execute(
        """
        SELECT payment_id, ticket_id, exit_time, total_fee, payment_method
        FROM Payment
        WHERE ticket_id = ?
        """,
        (ticket_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Reopen ticket
# ---------------------------------------------------------------------------

def reopen_ticket(ticket_id: str) -> None:
    """
    Reopen a Closed ticket if within 5 minutes of payment.

    Deletes the associated Payment and sets status back to Active.
    Raises ValueError if ticket not found, not closed, or window expired.
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN")

        row = cur.execute(
            "SELECT ticket_id, status FROM Ticket WHERE ticket_id = ?",
            (ticket_id,),
        ).fetchone()

        if row is None:
            raise ValueError("Ticket not found. Check the ticket ID or plate number.")
        if row["status"] == "Active":
            raise ValueError("This ticket is still active.")
        if row["status"] == "Voided":
            raise ValueError("This ticket has already been voided.")

        # Fetch payment exit_time
        payment_row = cur.execute(
            "SELECT exit_time FROM Payment WHERE ticket_id = ?",
            (ticket_id,),
        ).fetchone()

        if payment_row is None:
            raise ValueError("Ticket not found. Check the ticket ID or plate number.")

        exit_time = datetime.strptime(payment_row["exit_time"], "%Y-%m-%d %H:%M:%S")
        now = datetime.now()
        elapsed = (now - exit_time).total_seconds()

        if elapsed > 300:  # 5 minutes
            raise ValueError(
                "Cannot reopen — payment window expired (5 minutes)."
            )

        cur.execute("DELETE FROM Payment WHERE ticket_id = ?", (ticket_id,))
        cur.execute(
            "UPDATE Ticket SET status = 'Active' WHERE ticket_id = ?",
            (ticket_id,),
        )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def get_daily_revenue_summary() -> list[dict]:
    """
    Today's revenue grouped by vehicle type.

    Uses date(p.exit_time) = date('now','localtime').
    Ordered by total_revenue DESC.
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            v.type_name,
            COUNT(p.payment_id)        AS transactions,
            SUM(p.total_fee)           AS total_revenue,
            ROUND(AVG(p.total_fee), 2) AS avg_fee
        FROM Payment p
        JOIN Ticket t  ON p.ticket_id = t.ticket_id
        JOIN VehicleType v ON t.type_id = v.type_id
        WHERE date(p.exit_time) = date('now','localtime')
        GROUP BY v.type_id
        ORDER BY total_revenue DESC
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_daily_total_revenue() -> float:
    """Return total revenue for today."""
    conn = get_connection()
    row = conn.execute(
        """
        SELECT COALESCE(SUM(total_fee), 0.0) AS total
        FROM Payment
        WHERE date(exit_time) = date('now','localtime')
        """
    ).fetchone()
    conn.close()
    return row["total"]


def get_long_stay_alerts() -> list[dict]:
    """Return Active tickets parked longer than the threshold in Settings."""
    threshold_hours = get_settings().get("long_stay_threshold", 8)
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            t.ticket_id,
            t.plate_no,
            v.type_name,
            t.entry_time,
            ROUND(
                (julianday(datetime('now','localtime')) - julianday(t.entry_time)) * 24,
                2
            ) AS hours_elapsed
        FROM Ticket t
        JOIN VehicleType v ON t.type_id = v.type_id
        WHERE t.status = 'Active'
          AND (julianday(datetime('now','localtime')) - julianday(t.entry_time)) * 24 > ?
        """,
        (threshold_hours,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_voided_tickets_today() -> list[dict]:
    """Return voided tickets whose entry_time is today."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT ticket_id, plate_no, void_reason, entry_time
        FROM Ticket
        WHERE status = 'Voided'
          AND date(void_time) = date('now','localtime')
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def verify_login(username: str, password: str) -> dict | None:
    """Verify credentials and return user info if valid."""
    import hashlib
    conn = get_connection()
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    row = conn.execute(
        "SELECT username, display_name, role FROM Users WHERE username = ? AND password_hash = ?",
        (username, pw_hash)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def create_user(username: str, display_name: str, password: str, role: str) -> None:
    """Create a new user with hashed password."""
    import hashlib
    conn = get_connection()
    existing = conn.execute("SELECT username FROM Users WHERE username = ?", (username,)).fetchone()
    if existing:
        conn.close()
        raise ValueError("Username already exists.")
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    conn.execute(
        "INSERT INTO Users (username, password_hash, display_name, role) VALUES (?, ?, ?, ?)",
        (username, pw_hash, display_name, role)
    )
    conn.commit()
    conn.close()

def get_all_users() -> list[dict]:
    """Return a list of all users."""
    conn = get_connection()
    rows = conn.execute("SELECT username, display_name, role FROM Users ORDER BY role, username").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_user(username: str) -> None:
    """Delete a user by username."""
    conn = get_connection()
    conn.execute("DELETE FROM Users WHERE username = ?", (username,))
    conn.commit()
    conn.close()

def reset_password(username: str, new_password: str) -> None:
    """Reset a user's password."""
    import hashlib
    conn = get_connection()
    pw_hash = hashlib.sha256(new_password.encode()).hexdigest()
    conn.execute("UPDATE Users SET password_hash = ? WHERE username = ?", (pw_hash, username))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Transaction History
# ---------------------------------------------------------------------------

def get_transaction_history(
    date_from: str = None,
    date_to: str = None,
    plate_query: str = None,
) -> list[dict]:
    """
    Return all Closed tickets with payment info.
    Joins Ticket + Payment + VehicleType.
    """
    conn = get_connection()
    sql = """
        SELECT
            t.ticket_id,
            t.plate_no,
            v.type_name,
            t.entry_time,
            p.exit_time,
            ROUND(
                (julianday(p.exit_time) - julianday(t.entry_time)) * 24, 2
            ) AS hours_elapsed,
            p.total_fee,
            p.payment_method
        FROM Ticket t
        JOIN VehicleType v ON t.type_id = v.type_id
        JOIN Payment p ON t.ticket_id = p.ticket_id
        WHERE t.status = 'Closed'
    """
    params = []
    if date_from:
        sql += " AND date(p.exit_time) >= ?"
        params.append(date_from)
    if date_to:
        sql += " AND date(p.exit_time) <= ?"
        params.append(date_to)
    if plate_query:
        sql += " AND t.plate_no LIKE ?"
        params.append(f"%{plate_query.upper()}%")
    sql += " ORDER BY p.exit_time DESC"

    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]
