"""
gui.py
------
All the Tkinter windows of the system:
    LoginWindow, RegisterWindow, Dashboard, BookingScreen, HistoryScreen,
    ResourceScreen, BookingsScreen, CampusListScreen and ReportsScreen.

Widgets used: Label, Button, Entry, Combobox, Treeview and messagebox.
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, timedelta, datetime

# LIST of start times shown in the booking combobox (07:00, 07:30 ... 20:30)
TIME_SLOTS = [f"{hour:02d}:{minute:02d}" for hour in range(7, 21) for minute in (0, 30)]
# LIST of durations (in hours)
DURATIONS = [str(number) for number in range(1, 9)]
# LIST of resource types for the admin screen
RESOURCE_TYPES = ["Computer Lab", "Projector", "Seminar Room", "Presentation Equipment"]

TITLE_FONT = ("Arial", 16, "bold")
HEADING_FONT = ("Arial", 12, "bold")


# ---------------------------------------------------------------------
# Helper functions used by many screens
# ---------------------------------------------------------------------
def clear_window(window):
    """Removes every widget from a window so a new screen can be drawn."""
    for widget in window.winfo_children():
        widget.destroy()


def make_table(parent, columns, height=10, width=110):
    """Creates a Treeview (table) with a scrollbar. Returns (frame, tree)."""
    frame = tk.Frame(parent)
    tree = ttk.Treeview(frame, columns=columns, show="headings", height=height)
    for column in columns:
        tree.heading(column, text=column)
        tree.column(column, width=width, anchor="center")
    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    return frame, tree


def clear_table(tree):
    tree.delete(*tree.get_children())


# =====================================================================
# LOGIN WINDOW
# =====================================================================
class LoginWindow:

    def __init__(self, root, db):
        self.root = root
        self.db = db
        clear_window(root)
        root.title("Smart Campus Resource Booking - Login")

        frame = tk.Frame(root, padx=30, pady=30)
        frame.pack(expand=True)

        tk.Label(frame, text="Smart Campus Resource Booking System",
                 font=TITLE_FONT).grid(row=0, column=0, columnspan=2, pady=(0, 5))
        tk.Label(frame, text="Richfield Graduate Institution").grid(row=1, column=0, columnspan=2, pady=(0, 20))

        tk.Label(frame, text="Username:").grid(row=2, column=0, sticky="e", pady=5)
        self.username_entry = tk.Entry(frame, width=30)
        self.username_entry.grid(row=2, column=1, pady=5)

        tk.Label(frame, text="Password:").grid(row=3, column=0, sticky="e", pady=5)
        self.password_entry = tk.Entry(frame, width=30, show="*")
        self.password_entry.grid(row=3, column=1, pady=5)

        tk.Button(frame, text="Login", width=15, command=self.login).grid(row=4, column=0, columnspan=2, pady=10)
        tk.Button(frame, text="Register as Lecturer", width=20,
                  command=self.open_register).grid(row=5, column=0, columnspan=2)

        # Pressing Enter also logs in
        root.bind("<Return>", lambda event: self.login())
        self.username_entry.focus()

    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if username == "" or password == "":
            messagebox.showwarning("Missing details", "Please enter your username and password.")
            return

        user = self.db.login(username, password)
        if user is None:
            messagebox.showerror("Login failed", "Incorrect username or password.")
            self.password_entry.delete(0, tk.END)
            return

        self.root.unbind("<Return>")
        messagebox.showinfo("Welcome", f"Welcome, {user.get_full_name()}!")
        Dashboard(self.root, self.db, user)

    def open_register(self):
        RegisterWindow(self.root, self.db)


# =====================================================================
# REGISTRATION WINDOW
# =====================================================================
class RegisterWindow:

    def __init__(self, root, db):
        self.db = db
        self.window = tk.Toplevel(root)
        self.window.title("Register New Lecturer")
        self.window.grab_set()   # keep focus on this window

        frame = tk.Frame(self.window, padx=20, pady=20)
        frame.pack()

        tk.Label(frame, text="Create a Lecturer Account", font=HEADING_FONT).grid(row=0, column=0, columnspan=2, pady=10)

        # Dictionary of entry boxes - makes it easy to loop over them
        self.entries = {}
        labels = ["Full Name", "Email", "Username", "Password", "Confirm Password"]
        for row_number, label in enumerate(labels, start=1):
            tk.Label(frame, text=label + ":").grid(row=row_number, column=0, sticky="e", pady=4)
            entry = tk.Entry(frame, width=30)
            if "Password" in label:
                entry.config(show="*")
            entry.grid(row=row_number, column=1, pady=4)
            self.entries[label] = entry

        tk.Label(frame, text="Role:").grid(row=6, column=0, sticky="e", pady=4)
        self.role_combo = ttk.Combobox(frame, values=["Lecturer"], state="readonly", width=27)
        self.role_combo.current(0)
        self.role_combo.grid(row=6, column=1, pady=4)
        tk.Label(frame, text="(Administrator accounts are created by the System Operator)",
                 font=("Arial", 8)).grid(row=7, column=0, columnspan=2)

        tk.Button(frame, text="Register", width=15, command=self.register).grid(row=8, column=0, columnspan=2, pady=10)

    def register(self):
        # Read all values into a dictionary
        values = {label: entry.get().strip() for label, entry in self.entries.items()}

        # ----- input validation -----
        for label, value in values.items():
            if value == "":
                messagebox.showwarning("Missing details", f"Please enter your {label}.", parent=self.window)
                return
        if "@" not in values["Email"] or "." not in values["Email"]:
            messagebox.showwarning("Invalid email", "Please enter a valid email address.", parent=self.window)
            return
        if len(values["Username"]) < 3 or " " in values["Username"]:
            messagebox.showwarning("Invalid username", "Username must be 3+ characters with no spaces.", parent=self.window)
            return
        if len(values["Password"]) < 6:
            messagebox.showwarning("Weak password", "Password must be at least 6 characters.", parent=self.window)
            return
        if values["Password"] != values["Confirm Password"]:
            messagebox.showwarning("Password mismatch", "The passwords do not match.", parent=self.window)
            return

        ok, message = self.db.register_user(values["Username"], values["Password"],
                                            values["Full Name"], values["Email"], self.role_combo.get())
        if ok:
            messagebox.showinfo("Success", message, parent=self.window)
            self.window.destroy()
        else:
            messagebox.showerror("Registration failed", message, parent=self.window)


# =====================================================================
# MAIN DASHBOARD - buttons change depending on the user's role
# =====================================================================
class Dashboard:

    def __init__(self, root, db, user):
        self.root = root
        self.db = db
        self.user = user
        self.campuses = db.get_campuses()   # dictionary name -> Campus

        clear_window(root)
        root.title(f"Dashboard - {user.get_role()}")

        frame = tk.Frame(root, padx=20, pady=20)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text=f"Welcome, {user.get_full_name()}", font=TITLE_FONT).pack()
        tk.Label(frame, text=f"Role: {user.get_role()}").pack(pady=(0, 15))

        # ----- Campus selection -----
        campus_frame = tk.LabelFrame(frame, text="Campus Selection", padx=10, pady=10)
        campus_frame.pack(fill="x", pady=5)

        tk.Label(campus_frame, text="Select campus:").grid(row=0, column=0, sticky="w")
        self.campus_combo = ttk.Combobox(campus_frame, values=list(self.campuses.keys()),
                                         state="readonly", width=30)
        self.campus_combo.grid(row=0, column=1, padx=10, sticky="w")
        self.campus_combo.bind("<<ComboboxSelected>>", self.on_campus_change)

        self.active_label = tk.Label(campus_frame, text="", font=HEADING_FONT, fg="dark green")
        self.active_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))
        self.policy_label = tk.Label(campus_frame, text="", fg="blue")
        self.policy_label.grid(row=2, column=0, columnspan=2, sticky="w")

        # Choose the starting campus
        start_index = 0
        if not user.can_change_campus():
            # Administrators are locked to their own campus
            for index, campus in enumerate(self.campuses.values()):
                if campus.get_campus_id() == user.get_campus_id():
                    start_index = index
            self.campus_combo.config(state="disabled")
        self.campus_combo.current(start_index)
        self.on_campus_change()

        # ----- Role based buttons -----
        # Dictionary: permission -> (button text, function to run)
        button_actions = {
            "book_resource": ("View & Book Resources", self.open_booking),
            "view_history": ("My Bookings / History", self.open_history),
            "manage_resources": ("Manage Resources", self.open_resources),
            "view_campus_bookings": ("View Campus Bookings", self.open_campus_bookings),
            "usage_report": ("Monitor Resource Usage", self.open_campus_report),
            "view_campuses": ("View All Campuses", self.open_campus_list),
            "view_all_bookings": ("View All Bookings", self.open_all_bookings),
            "reports": ("Reports & Campus Comparison", self.open_operator_reports),
        }

        menu_frame = tk.LabelFrame(frame, text="Menu", padx=10, pady=10)
        menu_frame.pack(fill="x", pady=10)
        for permission in self.user.get_permissions():
            text, command = button_actions[permission]
            tk.Button(menu_frame, text=text, width=30, command=command).pack(pady=4)

        tk.Button(frame, text="Logout", width=15, command=self.logout).pack(pady=10)

    def get_active_campus(self):
        return self.campuses[self.campus_combo.get()]

    def on_campus_change(self, event=None):
        campus = self.get_active_campus()
        self.active_label.config(text=f"Active campus: {campus.get_name()}")
        self.policy_label.config(text=f"Booking policy: {campus.get_policy_text()}")

    # ----- button functions -----
    def open_booking(self):
        BookingScreen(self.root, self.db, self.user, self.get_active_campus())

    def open_history(self):
        HistoryScreen(self.root, self.db, self.user)

    def open_resources(self):
        ResourceScreen(self.root, self.db, self.get_active_campus())

    def open_campus_bookings(self):
        BookingsScreen(self.root, self.db, self.get_active_campus())

    def open_campus_report(self):
        ReportsScreen(self.root, self.db, self.get_active_campus(), show_comparison=False)

    def open_campus_list(self):
        CampusListScreen(self.root, self.db)

    def open_all_bookings(self):
        BookingsScreen(self.root, self.db, None)

    def open_operator_reports(self):
        ReportsScreen(self.root, self.db, self.get_active_campus(), show_comparison=True)

    def logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to log out?"):
            # Close any extra windows that are still open
            for widget in self.root.winfo_children():
                if isinstance(widget, tk.Toplevel):
                    widget.destroy()
            LoginWindow(self.root, self.db)


# =====================================================================
# BOOKING SCREEN (Lecturer)
# =====================================================================
class BookingScreen:

    def __init__(self, root, db, user, campus):
        self.db = db
        self.user = user
        self.campus = campus
        self.resource_lookup = {}   # dictionary: tree row id -> Resource object

        self.window = tk.Toplevel(root)
        self.window.title(f"Book a Resource - {campus.get_name()}")
        self.window.geometry("900x640")

        tk.Label(self.window, text=f"Resources at {campus.get_name()}", font=HEADING_FONT).pack(pady=5)
        tk.Label(self.window, text=f"Policy in effect: {campus.get_policy_text()}", fg="blue").pack()

        # ----- resources table -----
        columns = ("Code", "Name", "Type", "Capacity", "Status", "Right Now")
        table_frame, self.resource_tree = make_table(self.window, columns, height=8)
        table_frame.pack(fill="x", padx=10, pady=5)
        self.resource_tree.bind("<<TreeviewSelect>>", lambda event: self.show_day_bookings())

        # ----- booking form -----
        form = tk.LabelFrame(self.window, text="New Booking", padx=10, pady=10)
        form.pack(fill="x", padx=10, pady=5)

        tk.Label(form, text="Date (YYYY-MM-DD):").grid(row=0, column=0, sticky="e")
        self.date_entry = tk.Entry(form, width=15)
        # Default date = tomorrow (works for every campus rule)
        self.date_entry.insert(0, (date.today() + timedelta(days=1)).strftime("%Y-%m-%d"))
        self.date_entry.grid(row=0, column=1, padx=5, pady=3)

        tk.Label(form, text="Start time:").grid(row=0, column=2, sticky="e")
        self.time_combo = ttk.Combobox(form, values=TIME_SLOTS, state="readonly", width=8)
        self.time_combo.set("09:00")
        self.time_combo.grid(row=0, column=3, padx=5)

        tk.Label(form, text="Duration (hours):").grid(row=0, column=4, sticky="e")
        self.duration_combo = ttk.Combobox(form, values=DURATIONS, state="readonly", width=5)
        self.duration_combo.set("1")
        self.duration_combo.grid(row=0, column=5, padx=5)

        tk.Label(form, text="Purpose:").grid(row=1, column=0, sticky="e")
        self.purpose_entry = tk.Entry(form, width=50)
        self.purpose_entry.grid(row=1, column=1, columnspan=4, sticky="w", padx=5, pady=3)

        tk.Button(form, text="Check Bookings On Date", command=self.show_day_bookings).grid(row=2, column=1, pady=5)
        tk.Button(form, text="Book Resource", command=self.book).grid(row=2, column=3, pady=5)
        tk.Button(form, text="Refresh", command=self.load_resources).grid(row=2, column=5, pady=5)

        # ----- existing bookings on the chosen date -----
        tk.Label(self.window, text="Existing bookings for the selected resource on that date:").pack(anchor="w", padx=10)
        day_frame, self.day_tree = make_table(self.window, ("Start", "End", "Hours", "Booked By"), height=5)
        day_frame.pack(fill="x", padx=10, pady=5)

        self.load_resources()

    def load_resources(self, keep_code=None):
        """Fills the table. If keep_code is given, that resource stays selected."""
        clear_table(self.resource_tree)
        self.resource_lookup = {}
        for resource in self.db.get_resources(self.campus.get_campus_id()):
            if not resource.is_available():
                right_now = "Not bookable"
            elif self.db.is_resource_in_use_now(resource.get_resource_id()):
                right_now = "In use"
            else:
                right_now = "Free"
            row_id = self.resource_tree.insert("", tk.END, values=(
                resource.get_code(), resource.get_name(), resource.get_type(),
                resource.get_capacity(), resource.get_status(), right_now))
            self.resource_lookup[row_id] = resource
            if resource.get_code() == keep_code:
                self.resource_tree.selection_set(row_id)

    def get_selected_resource(self):
        selected = self.resource_tree.selection()
        if not selected:
            return None
        return self.resource_lookup[selected[0]]

    def show_day_bookings(self):
        clear_table(self.day_tree)
        resource = self.get_selected_resource()
        if resource is None:
            return
        booking_date = self.date_entry.get().strip()
        for booking in self.db.get_bookings_for_resource_on_date(resource.get_resource_id(), booking_date):
            self.day_tree.insert("", tk.END, values=(booking.get_start_time(), booking.get_end_time(),
                                                     booking.get_duration(), booking.get_lecturer_name()))

    def book(self):
        resource = self.get_selected_resource()
        if resource is None:
            messagebox.showwarning("No resource", "Please select a resource in the table first.", parent=self.window)
            return

        booking_date = self.date_entry.get().strip()
        start_time = self.time_combo.get()
        duration = int(self.duration_combo.get())
        purpose = self.purpose_entry.get().strip()

        if purpose == "":
            messagebox.showwarning("Missing purpose", "Please enter the purpose of the booking.", parent=self.window)
            return

        ok, message = self.db.create_booking(self.user, self.campus, resource,
                                             booking_date, start_time, duration, purpose)
        if ok:
            messagebox.showinfo("Booked", f"{message}\n{resource.get_name()} on {booking_date} at {start_time}.",
                                parent=self.window)
            self.purpose_entry.delete(0, tk.END)
            self.load_resources(resource.get_code())
            self.show_day_bookings()
        else:
            messagebox.showerror("Booking not allowed", message, parent=self.window)


# =====================================================================
# BOOKING HISTORY SCREEN (Lecturer)
# =====================================================================
class HistoryScreen:

    def __init__(self, root, db, user):
        self.db = db
        self.user = user

        self.window = tk.Toplevel(root)
        self.window.title("My Bookings and History")
        self.window.geometry("950x450")

        tk.Label(self.window, text="My Bookings", font=HEADING_FONT).pack(pady=5)

        top = tk.Frame(self.window)
        top.pack(pady=5)
        tk.Label(top, text="Show:").pack(side="left")
        self.filter_combo = ttk.Combobox(top, values=["All", "Upcoming", "In Progress", "Completed", "Cancelled"],
                                         state="readonly", width=12)
        self.filter_combo.set("All")
        self.filter_combo.pack(side="left", padx=5)
        self.filter_combo.bind("<<ComboboxSelected>>", lambda event: self.load_bookings())

        columns = ("ID", "Campus", "Resource", "Date", "Start", "End", "Hours", "Purpose", "Status")
        table_frame, self.tree = make_table(self.window, columns, height=12, width=100)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        tk.Button(self.window, text="Cancel Selected Booking", command=self.cancel).pack(pady=8)
        self.load_bookings()

    def load_bookings(self):
        clear_table(self.tree)
        chosen = self.filter_combo.get()
        for booking in self.db.get_user_bookings(self.user.get_user_id()):
            state = booking.get_state()
            if chosen != "All" and chosen != state:
                continue
            self.tree.insert("", tk.END, values=(
                booking.get_booking_id(), booking.get_campus_name(), booking.get_resource_name(),
                booking.get_date(), booking.get_start_time(), booking.get_end_time(),
                booking.get_duration(), booking.get_purpose(), state))

    def cancel(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Nothing selected", "Please select a booking to cancel.", parent=self.window)
            return
        values = self.tree.item(selected[0], "values")
        booking_id = int(values[0])
        if values[8] != "Upcoming":
            messagebox.showwarning("Not allowed", "Only upcoming bookings can be cancelled.", parent=self.window)
            return
        if messagebox.askyesno("Confirm", f"Cancel booking {booking_id}?", parent=self.window):
            ok, message = self.db.cancel_booking(booking_id, self.user.get_user_id())
            if ok:
                messagebox.showinfo("Cancelled", message, parent=self.window)
            else:
                messagebox.showerror("Error", message, parent=self.window)
            self.load_bookings()


# =====================================================================
# RESOURCE MANAGEMENT SCREEN (Campus Administrator)
# =====================================================================
class ResourceScreen:

    def __init__(self, root, db, campus):
        self.db = db
        self.campus = campus
        self.resource_lookup = {}
        self.selected_resource = None

        self.window = tk.Toplevel(root)
        self.window.title(f"Manage Resources - {campus.get_name()}")
        self.window.geometry("800x520")

        tk.Label(self.window, text=f"Resources at {campus.get_name()}", font=HEADING_FONT).pack(pady=5)

        columns = ("Code", "Name", "Type", "Capacity", "Status")
        table_frame, self.tree = make_table(self.window, columns, height=10, width=140)
        table_frame.pack(fill="x", padx=10, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self.fill_form)

        form = tk.LabelFrame(self.window, text="Resource Details", padx=10, pady=10)
        form.pack(fill="x", padx=10, pady=5)

        tk.Label(form, text="Code (unique):").grid(row=0, column=0, sticky="e")
        self.code_entry = tk.Entry(form, width=20)
        self.code_entry.grid(row=0, column=1, padx=5, pady=3)

        tk.Label(form, text="Name:").grid(row=0, column=2, sticky="e")
        self.name_entry = tk.Entry(form, width=25)
        self.name_entry.grid(row=0, column=3, padx=5, pady=3)

        tk.Label(form, text="Type:").grid(row=1, column=0, sticky="e")
        self.type_combo = ttk.Combobox(form, values=RESOURCE_TYPES, state="readonly", width=18)
        self.type_combo.grid(row=1, column=1, padx=5, pady=3)

        tk.Label(form, text="Capacity:").grid(row=1, column=2, sticky="e")
        self.capacity_entry = tk.Entry(form, width=10)
        self.capacity_entry.grid(row=1, column=3, sticky="w", padx=5, pady=3)

        tk.Label(form, text="Status:").grid(row=2, column=0, sticky="e")
        self.status_combo = ttk.Combobox(form, values=["Available", "Unavailable"], state="readonly", width=18)
        self.status_combo.set("Available")
        self.status_combo.grid(row=2, column=1, padx=5, pady=3)

        buttons = tk.Frame(self.window)
        buttons.pack(pady=8)
        tk.Button(buttons, text="Add", width=12, command=self.add).pack(side="left", padx=5)
        tk.Button(buttons, text="Update", width=12, command=self.update).pack(side="left", padx=5)
        tk.Button(buttons, text="Delete", width=12, command=self.delete).pack(side="left", padx=5)
        tk.Button(buttons, text="Clear Form", width=12, command=self.clear_form).pack(side="left", padx=5)

        self.load_resources()

    def load_resources(self):
        clear_table(self.tree)
        self.resource_lookup = {}
        for resource in self.db.get_resources(self.campus.get_campus_id()):
            row_id = self.tree.insert("", tk.END, values=(resource.get_code(), resource.get_name(),
                                                          resource.get_type(), resource.get_capacity(),
                                                          resource.get_status()))
            self.resource_lookup[row_id] = resource

    def fill_form(self, event=None):
        selected = self.tree.selection()
        if not selected:
            return
        resource = self.resource_lookup[selected[0]]
        self.selected_resource = resource
        self.clear_entries()
        self.code_entry.insert(0, resource.get_code())
        self.code_entry.config(state="disabled")   # the code cannot be changed
        self.name_entry.insert(0, resource.get_name())
        self.type_combo.set(resource.get_type())
        self.capacity_entry.insert(0, str(resource.get_capacity()))
        self.status_combo.set(resource.get_status())

    def clear_entries(self):
        self.code_entry.config(state="normal")
        self.code_entry.delete(0, tk.END)
        self.name_entry.delete(0, tk.END)
        self.capacity_entry.delete(0, tk.END)
        self.type_combo.set("")
        self.status_combo.set("Available")

    def clear_form(self):
        self.selected_resource = None
        self.clear_entries()
        self.tree.selection_remove(self.tree.selection())

    def read_form(self):
        """Validates the form. Returns (name, type, capacity) or None if invalid."""
        name = self.name_entry.get().strip()
        resource_type = self.type_combo.get()
        capacity_text = self.capacity_entry.get().strip()
        if name == "" or resource_type == "" or capacity_text == "":
            messagebox.showwarning("Missing details", "Please fill in name, type and capacity.", parent=self.window)
            return None
        try:
            capacity = int(capacity_text)
            if capacity <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Invalid capacity", "Capacity must be a whole number above 0.", parent=self.window)
            return None
        return name, resource_type, capacity

    def add(self):
        code = self.code_entry.get().strip()
        if self.selected_resource is not None:
            messagebox.showinfo("Tip", "Click 'Clear Form' before adding a new resource.", parent=self.window)
            return
        if code == "":
            messagebox.showwarning("Missing code", "Please enter a unique resource code.", parent=self.window)
            return
        details = self.read_form()
        if details is None:
            return
        name, resource_type, capacity = details
        ok, message = self.db.add_resource(code, name, resource_type, capacity,
                                           self.campus.get_campus_id(), self.status_combo.get())
        self.show_result(ok, message)

    def update(self):
        if self.selected_resource is None:
            messagebox.showwarning("Nothing selected", "Select a resource to update.", parent=self.window)
            return
        details = self.read_form()
        if details is None:
            return
        name, resource_type, capacity = details
        ok, message = self.db.update_resource(self.selected_resource.get_resource_id(), name,
                                              resource_type, capacity, self.status_combo.get())
        self.show_result(ok, message)

    def delete(self):
        if self.selected_resource is None:
            messagebox.showwarning("Nothing selected", "Select a resource to delete.", parent=self.window)
            return
        if not messagebox.askyesno("Confirm", f"Delete {self.selected_resource.get_name()}?", parent=self.window):
            return
        ok, message = self.db.delete_resource(self.selected_resource.get_resource_id())
        self.show_result(ok, message)

    def show_result(self, ok, message):
        if ok:
            messagebox.showinfo("Success", message, parent=self.window)
            self.clear_form()
            self.load_resources()
        else:
            messagebox.showerror("Error", message, parent=self.window)


# =====================================================================
# BOOKINGS SCREEN - campus bookings (admin) or all bookings (operator)
# =====================================================================
class BookingsScreen:

    def __init__(self, root, db, campus=None):
        """If campus is None, bookings for ALL campuses are shown."""
        self.db = db
        self.campus = campus
        self.campuses = db.get_campuses()

        self.window = tk.Toplevel(root)
        self.window.geometry("1000x480")

        if campus is None:
            self.window.title("All Bookings - All Campuses")
            top = tk.Frame(self.window)
            top.pack(pady=5)
            tk.Label(top, text="Filter by campus:").pack(side="left")
            self.filter_combo = ttk.Combobox(top, values=["All Campuses"] + list(self.campuses.keys()),
                                             state="readonly", width=25)
            self.filter_combo.set("All Campuses")
            self.filter_combo.pack(side="left", padx=5)
            self.filter_combo.bind("<<ComboboxSelected>>", lambda event: self.load_bookings())
        else:
            self.window.title(f"Bookings - {campus.get_name()}")
            tk.Label(self.window, text=f"Bookings at {campus.get_name()}", font=HEADING_FONT).pack(pady=5)

        columns = ("ID", "Campus", "Lecturer", "Resource", "Date", "Start", "End", "Hours", "Status")
        table_frame, self.tree = make_table(self.window, columns, height=15, width=105)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.summary_label = tk.Label(self.window, text="")
        self.summary_label.pack(pady=5)
        self.load_bookings()

    def load_bookings(self):
        clear_table(self.tree)
        if self.campus is not None:
            bookings = self.db.get_bookings(self.campus.get_campus_id())
        elif self.filter_combo.get() == "All Campuses":
            bookings = self.db.get_bookings()
        else:
            bookings = self.db.get_bookings(self.campuses[self.filter_combo.get()].get_campus_id())

        upcoming = 0
        for booking in bookings:
            state = booking.get_state()
            if state == "Upcoming":
                upcoming += 1
            self.tree.insert("", tk.END, values=(
                booking.get_booking_id(), booking.get_campus_name(), booking.get_lecturer_name(),
                booking.get_resource_name(), booking.get_date(), booking.get_start_time(),
                booking.get_end_time(), booking.get_duration(), state))
        self.summary_label.config(text=f"Total bookings shown: {len(bookings)}   |   Upcoming: {upcoming}")


# =====================================================================
# CAMPUS LIST SCREEN (System Operator)
# =====================================================================
class CampusListScreen:

    def __init__(self, root, db):
        self.window = tk.Toplevel(root)
        self.window.title("All Campuses")
        self.window.geometry("950x250")

        tk.Label(self.window, text="All Campuses and Their Booking Rules", font=HEADING_FONT).pack(pady=5)
        columns = ("Campus", "Location", "Max Hours", "Days in Advance", "Opening Hours", "Resources")
        table_frame, tree = make_table(self.window, columns, height=6, width=150)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        for campus in db.get_campuses().values():
            resource_count = len(db.get_resources(campus.get_campus_id()))
            tree.insert("", tk.END, values=(
                campus.get_name(), campus.get_location(), campus.get_max_hours(),
                campus.get_min_days_advance(),
                f"{campus.get_open_hour():02d}:00 - {campus.get_close_hour():02d}:00",
                resource_count))


# =====================================================================
# REPORTS SCREEN (Admin = one campus, Operator = all + comparison)
# =====================================================================
class ReportsScreen:

    def __init__(self, root, db, campus, show_comparison):
        self.db = db
        self.campus = campus
        self.show_comparison = show_comparison
        self.campuses = db.get_campuses()

        self.window = tk.Toplevel(root)
        self.window.title("Reports")
        self.window.geometry("1150x730" if show_comparison else "800x540")

        top = tk.Frame(self.window)
        top.pack(pady=5)
        tk.Label(top, text="Campus Report:", font=HEADING_FONT).pack(side="left")
        if show_comparison:
            # Operators can switch between campuses
            self.campus_combo = ttk.Combobox(top, values=list(self.campuses.keys()), state="readonly", width=25)
            self.campus_combo.set(campus.get_name())
            self.campus_combo.pack(side="left", padx=5)
            self.campus_combo.bind("<<ComboboxSelected>>", self.change_campus)
        else:
            tk.Label(top, text=campus.get_name(), font=HEADING_FONT).pack(side="left", padx=5)

        self.summary_label = tk.Label(self.window, text="", justify="left", font=("Courier", 10))
        self.summary_label.pack(anchor="w", padx=15, pady=5)

        # Usage trend: bookings per month (little bar chart made of # signs)
        self.trend_label = tk.Label(self.window, text="", justify="left", font=("Courier", 10))
        self.trend_label.pack(anchor="w", padx=15)

        columns = ("Code", "Resource", "Type", "Status", "Times Booked", "Total Hours")
        usage_frame, self.usage_tree = make_table(self.window, columns, height=5, width=120)
        usage_frame.pack(fill="x", padx=10, pady=5)

        if show_comparison:
            tk.Label(self.window, text="Cross-Campus Comparison", font=HEADING_FONT).pack(pady=(10, 0))
            columns = ("Campus", "Rules", "Resources", "Bookings", "Cancelled",
                       "Total Hours", "Avg Duration", "Lecturers")
            compare_frame, self.compare_tree = make_table(self.window, columns, height=3, width=100)
            self.compare_tree.column("Rules", width=330)
            compare_frame.pack(fill="x", padx=10, pady=5)
            self.observation_label = tk.Label(self.window, text="", justify="left", fg="dark green")
            self.observation_label.pack(anchor="w", padx=15)
            self.load_comparison()

        tk.Button(self.window, text="Save Report to Text File", command=self.save_report).pack(pady=10)
        self.load_campus_report()

    def change_campus(self, event=None):
        self.campus = self.campuses[self.campus_combo.get()]
        self.load_campus_report()

    def load_campus_report(self):
        report = self.db.get_campus_report(self.campus)
        self.summary_label.config(text=(
            f"Policy:                  {report['policy']}\n"
            f"Total bookings:          {report['total_bookings']}\n"
            f"Cancelled bookings:      {report['cancelled']}\n"
            f"Total hours booked:      {report['total_hours']}\n"
            f"Average duration:        {report['average_duration']} hours\n"
            f"Most used resource:      {report['most_used']}\n"
            f"Lecturers using campus:  {report['lecturer_count']}"))
        self.trend_label.config(text=self.make_trend_text(report))
        clear_table(self.usage_tree)
        for code, info in report["usage"].items():
            self.usage_tree.insert("", tk.END, values=(code, info["name"], info["type"],
                                                       info["status"], info["count"], info["hours"]))

    def make_trend_text(self, report):
        """Bookings per month as text, e.g.  2026-10  ##### 5"""
        if len(report["monthly"]) == 0:
            return "Bookings per month (trend): no bookings yet"
        lines = ["Bookings per month (trend):"]
        for month, count in report["monthly"].items():
            lines.append(f"   {month}  {'#' * count} {count}")
        return "\n".join(lines)

    def load_comparison(self):
        reports = self.db.get_comparison_report()
        clear_table(self.compare_tree)
        for report in reports:
            self.compare_tree.insert("", tk.END, values=(
                report["campus"], report["policy"], report["resource_count"], report["total_bookings"],
                report["cancelled"], report["total_hours"], report["average_duration"],
                report["lecturer_count"]))

        # Simple observations about how the rules affect usage
        busiest = max(reports, key=lambda r: r["total_bookings"])
        longest = max(reports, key=lambda r: r["average_duration"])
        self.observation_label.config(text=(
            f"Busiest campus: {busiest['campus']} with {busiest['total_bookings']} bookings.\n"
            f"Longest average booking: {longest['campus']} ({longest['average_duration']} hours) - "
            f"its policy is: {longest['policy']}.\n"
            f"Monthly trend (bookings per month):\n" + "\n".join(
                f"   {r['campus'].replace(' Campus', '')}: " +
                (", ".join(f"{m} = {c}" for m, c in r["monthly"].items()) or "none")
                for r in reports)))

    def save_report(self):
        """'Generate report' - writes the report to a .txt file in the reports folder."""
        folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
        os.makedirs(folder, exist_ok=True)
        file_name = os.path.join(folder, f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

        lines = ["SMART CAMPUS RESOURCE BOOKING SYSTEM - REPORT",
                 f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ""]
        reports = self.db.get_comparison_report() if self.show_comparison else [self.db.get_campus_report(self.campus)]
        for report in reports:
            lines.append("=" * 60)
            lines.append(report["campus"])
            lines.append("=" * 60)
            lines.append(f"Policy: {report['policy']}")
            lines.append(f"Total bookings: {report['total_bookings']}")
            lines.append(f"Cancelled: {report['cancelled']}")
            lines.append(f"Total hours: {report['total_hours']}")
            lines.append(f"Average duration: {report['average_duration']} hours")
            lines.append("Bookings per month: " + (", ".join(
                f"{m} = {c}" for m, c in report["monthly"].items()) or "none"))
            lines.append(f"Most used resource: {report['most_used']}")
            lines.append("Usage per resource:")
            for code, info in report["usage"].items():
                lines.append(f"   {code:<12} {info['name']:<25} {info['count']} bookings, {info['hours']} hours")
            lines.append("")

        with open(file_name, "w", encoding="utf-8") as report_file:
            report_file.write("\n".join(lines))
        messagebox.showinfo("Report saved", f"Report saved to:\n{file_name}", parent=self.window)
