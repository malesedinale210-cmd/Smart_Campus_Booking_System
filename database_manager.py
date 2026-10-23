"""
database_manager.py
-------------------
The DatabaseManager class is the ONLY place where SQL is written.
The GUI asks this class for data and this class talks to SQLite.
"""

import os
import sqlite3
import hashlib
from datetime import datetime

from models import create_user, Campus, Resource, Booking


class DatabaseManager:

    def __init__(self, db_file="campus_booking.db"):
        # Work out the folder this file is in, so the program works
        # no matter where it is started from.
        folder = os.path.dirname(os.path.abspath(__file__))
        if os.path.isabs(db_file):
            self.__db_path = db_file
        else:
            self.__db_path = os.path.join(folder, db_file)
        self.__sql_path = os.path.join(folder, "database.sql")

        self.__connection = sqlite3.connect(self.__db_path)
        # Row factory lets us use row["column_name"] instead of row[0]
        self.__connection.row_factory = sqlite3.Row
        self.__connection.execute("PRAGMA foreign_keys = ON")
        self.create_tables_if_needed()

    # -----------------------------------------------------------------
    # Setup
    # -----------------------------------------------------------------
    def create_tables_if_needed(self):
        """Runs database.sql the first time (when the users table is missing)."""
        cursor = self.__connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if cursor.fetchone() is None:
            with open(self.__sql_path, "r", encoding="utf-8") as sql_file:
                self.__connection.executescript(sql_file.read())
            self.__connection.commit()

    def close(self):
        self.__connection.close()

    @staticmethod
    def hash_password(password):
        """Passwords are never stored as plain text - we store a SHA-256 hash."""
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    # -----------------------------------------------------------------
    # Users: register and login
    # -----------------------------------------------------------------
    def register_user(self, username, password, full_name, email, role_name="Lecturer"):
        username = username.strip().lower()     # usernames are not case sensitive
        cursor = self.__connection.execute(
            "SELECT user_id FROM users WHERE username = ?", (username,))
        if cursor.fetchone() is not None:
            return False, "That username is already taken."

        role_row = self.__connection.execute(
            "SELECT role_id FROM roles WHERE role_name = ?", (role_name,)).fetchone()
        if role_row is None:
            return False, "Invalid role."

        try:
            self.__connection.execute(
                "INSERT INTO users (username, password_hash, full_name, email, role_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (username, self.hash_password(password), full_name, email, role_row["role_id"]))
            self.__connection.commit()
            return True, "Account created successfully. You can now log in."
        except sqlite3.Error as error:
            return False, f"Database error: {error}"

    def login(self, username, password):
        """Returns a Lecturer / CampusAdministrator / SystemOperator object, or None."""
        username = username.strip().lower()     # usernames are not case sensitive
        row = self.__connection.execute(
            "SELECT u.*, r.role_name FROM users u "
            "JOIN roles r ON u.role_id = r.role_id WHERE u.username = ?",
            (username,)).fetchone()
        if row is None or row["password_hash"] != self.hash_password(password):
            return None
        return create_user(row["user_id"], row["username"], row["full_name"],
                           row["email"], row["role_name"], row["campus_id"])

    # -----------------------------------------------------------------
    # Campuses
    # -----------------------------------------------------------------
    def get_campuses(self):
        """Returns a DICTIONARY: campus name -> Campus object."""
        campuses = {}
        for row in self.__connection.execute("SELECT * FROM campuses ORDER BY campus_id"):
            campus = Campus(row["campus_id"], row["campus_name"], row["location"],
                            row["max_hours"], row["min_days_advance"],
                            row["open_hour"], row["close_hour"])
            campuses[campus.get_name()] = campus
        return campuses

    # -----------------------------------------------------------------
    # Resources
    # -----------------------------------------------------------------
    def get_resources(self, campus_id):
        """Returns a LIST of Resource objects for one campus."""
        resources = []
        rows = self.__connection.execute(
            "SELECT * FROM resources WHERE campus_id = ? ORDER BY resource_code", (campus_id,))
        for row in rows:
            resources.append(Resource(row["resource_id"], row["resource_code"],
                                      row["resource_name"], row["resource_type"],
                                      row["capacity"], row["status"], row["campus_id"]))
        return resources

    def get_resource_codes(self):
        """Returns a SET of all resource codes - a set makes duplicate checks fast."""
        rows = self.__connection.execute("SELECT resource_code FROM resources")
        return {row["resource_code"] for row in rows}

    def add_resource(self, code, name, resource_type, capacity, campus_id, status="Available"):
        code = code.strip().upper()
        if status not in Resource.VALID_STATUSES:
            return False, "Status must be Available or Unavailable."
        if code in self.get_resource_codes():
            return False, f"A resource with code {code} already exists."

        # Also reject the same name twice on the same campus
        names_on_campus = {r.get_name().lower() for r in self.get_resources(campus_id)}
        if name.strip().lower() in names_on_campus:
            return False, f"A resource called '{name}' already exists on this campus."

        self.__connection.execute(
            "INSERT INTO resources (resource_code, resource_name, resource_type, capacity, status, campus_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (code, name.strip(), resource_type, capacity, status, campus_id))
        self.__connection.commit()
        return True, f"Resource {code} added."

    def update_resource(self, resource_id, name, resource_type, capacity, status):
        if status not in Resource.VALID_STATUSES:
            return False, "Status must be Available or Unavailable."
        self.__connection.execute(
            "UPDATE resources SET resource_name = ?, resource_type = ?, capacity = ?, status = ? "
            "WHERE resource_id = ?",
            (name.strip(), resource_type, capacity, status, resource_id))
        self.__connection.commit()
        return True, "Resource updated."

    def delete_resource(self, resource_id):
        # Do not delete a resource that has bookings - that would break history
        count = self.__connection.execute(
            "SELECT COUNT(*) FROM bookings WHERE resource_id = ?", (resource_id,)).fetchone()[0]
        if count > 0:
            return False, ("This resource has bookings linked to it and cannot be deleted. "
                           "Set its status to 'Unavailable' instead.")
        self.__connection.execute("DELETE FROM resources WHERE resource_id = ?", (resource_id,))
        self.__connection.commit()
        return True, "Resource deleted."

    def is_resource_in_use_now(self, resource_id):
        """Real-time check: is someone using this resource right now?"""
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M")
        for booking in self.get_bookings_for_resource_on_date(resource_id, today):
            if booking.get_start_time() <= current_time < booking.get_end_time():
                return True
        return False

    # -----------------------------------------------------------------
    # Bookings
    # -----------------------------------------------------------------
    def _row_to_booking(self, row):
        """Turns one database row into a Booking object."""
        keys = row.keys()
        return Booking(row["booking_id"], row["user_id"], row["resource_id"], row["campus_id"],
                       row["booking_date"], row["start_time"], row["duration_hours"],
                       row["status"], row["purpose"] or "",
                       row["resource_name"] if "resource_name" in keys else "",
                       row["campus_name"] if "campus_name" in keys else "",
                       row["full_name"] if "full_name" in keys else "")

    def get_bookings_for_resource_on_date(self, resource_id, booking_date):
        """LIST of ACTIVE bookings for one resource on one day."""
        rows = self.__connection.execute(
            "SELECT b.*, u.full_name FROM bookings b JOIN users u ON b.user_id = u.user_id "
            "WHERE b.resource_id = ? AND b.booking_date = ? AND b.status = 'Active' "
            "ORDER BY b.start_time", (resource_id, booking_date))
        return [self._row_to_booking(row) for row in rows]

    def create_booking(self, user, campus, resource, booking_date, start_time,
                       duration_hours, purpose=""):
        """Checks every rule and then saves the booking. Returns (True/False, message)."""
        # Rule 1: resource must be available
        if not resource.is_available():
            return False, f"{resource.get_name()} is currently unavailable and cannot be booked."

        # Rule 2: the resource must belong to the selected campus
        if resource.get_campus_id() != campus.get_campus_id():
            return False, "This resource does not belong to the selected campus."

        # Rule 3: campus-specific rules (duration, advance days, hours)
        ok, message = campus.check_booking_rules(booking_date, start_time, duration_hours)
        if not ok:
            return False, message

        # Rule 4: no overlapping bookings for the same resource
        for existing in self.get_bookings_for_resource_on_date(resource.get_resource_id(), booking_date):
            if existing.overlaps_with(start_time, duration_hours):
                return False, (f"This resource is already booked from {existing.get_start_time()} "
                               f"to {existing.get_end_time()} on {booking_date}.")

        self.__connection.execute(
            "INSERT INTO bookings (user_id, resource_id, campus_id, booking_date, start_time, "
            "duration_hours, purpose, status) VALUES (?, ?, ?, ?, ?, ?, ?, 'Active')",
            (user.get_user_id(), resource.get_resource_id(), campus.get_campus_id(),
             booking_date, start_time, duration_hours, purpose))
        self.__connection.commit()
        return True, "Booking confirmed!"

    def cancel_booking(self, booking_id, user_id):
        row = self.__connection.execute(
            "SELECT * FROM bookings WHERE booking_id = ? AND user_id = ?",
            (booking_id, user_id)).fetchone()
        if row is None:
            return False, "Booking not found."
        booking = self._row_to_booking(row)
        if booking.get_status() == "Cancelled":
            return False, "This booking is already cancelled."
        if not booking.is_future():
            return False, "Only future bookings can be cancelled."
        self.__connection.execute(
            "UPDATE bookings SET status = 'Cancelled' WHERE booking_id = ?", (booking_id,))
        self.__connection.commit()
        return True, "Booking cancelled."

    def get_user_bookings(self, user_id):
        """Booking history for one lecturer (newest first)."""
        rows = self.__connection.execute(
            "SELECT b.*, r.resource_name, c.campus_name, u.full_name FROM bookings b "
            "JOIN resources r ON b.resource_id = r.resource_id "
            "JOIN campuses c ON b.campus_id = c.campus_id "
            "JOIN users u ON b.user_id = u.user_id "
            "WHERE b.user_id = ? ORDER BY b.booking_date DESC, b.start_time DESC", (user_id,))
        return [self._row_to_booking(row) for row in rows]

    def get_bookings(self, campus_id=None):
        """All bookings, or only the bookings for one campus if campus_id is given."""
        sql = ("SELECT b.*, r.resource_name, c.campus_name, u.full_name FROM bookings b "
               "JOIN resources r ON b.resource_id = r.resource_id "
               "JOIN campuses c ON b.campus_id = c.campus_id "
               "JOIN users u ON b.user_id = u.user_id ")
        if campus_id is None:
            rows = self.__connection.execute(sql + "ORDER BY b.booking_date DESC, b.start_time")
        else:
            rows = self.__connection.execute(
                sql + "WHERE b.campus_id = ? ORDER BY b.booking_date DESC, b.start_time", (campus_id,))
        return [self._row_to_booking(row) for row in rows]

    # -----------------------------------------------------------------
    # Reports
    # -----------------------------------------------------------------
    def get_campus_report(self, campus):
        """
        Builds a report DICTIONARY for one campus:
            total bookings, cancelled, total hours, average duration,
            most used resource and usage per resource.
        """
        bookings = self.get_bookings(campus.get_campus_id())   # list
        resources = self.get_resources(campus.get_campus_id())  # list

        # Dictionary: resource code -> usage info
        usage = {}
        for resource in resources:
            usage[resource.get_code()] = {"name": resource.get_name(),
                                          "type": resource.get_type(),
                                          "status": resource.get_status(),
                                          "count": 0, "hours": 0}
        code_by_id = {r.get_resource_id(): r.get_code() for r in resources}

        monthly = {}        # dictionary: month ('2026-10') -> number of bookings (usage trend)
        lecturers = set()   # set = each lecturer counted only once
        active_count = 0
        cancelled_count = 0
        total_hours = 0

        for booking in bookings:
            if booking.get_status() == "Cancelled":
                cancelled_count += 1
                continue
            active_count += 1
            total_hours += booking.get_duration()
            lecturers.add(booking.get_user_id())
            month = booking.get_date()[:7]
            monthly[month] = monthly.get(month, 0) + 1
            code = code_by_id.get(booking.get_resource_id())
            if code in usage:
                usage[code]["count"] += 1
                usage[code]["hours"] += booking.get_duration()

        most_used = "None"
        if active_count > 0:
            best_code = max(usage, key=lambda c: usage[c]["count"])
            most_used = f"{best_code} - {usage[best_code]['name']} ({usage[best_code]['count']} bookings)"

        average = round(total_hours / active_count, 2) if active_count > 0 else 0

        return {
            "campus": campus.get_name(),
            "policy": campus.get_policy_text(),
            "resource_count": len(resources),
            "total_bookings": active_count,
            "cancelled": cancelled_count,
            "total_hours": total_hours,
            "average_duration": average,
            "most_used": most_used,
            "lecturer_count": len(lecturers),
            "usage": usage,
            "monthly": dict(sorted(monthly.items())),
        }

    def get_comparison_report(self):
        """LIST of report dictionaries - one for each campus."""
        return [self.get_campus_report(c) for c in self.get_campuses().values()]
