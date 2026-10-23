"""
models.py
---------
This file holds the main CLASSES of the system:
    User, Lecturer, CampusAdministrator, SystemOperator,
    Campus, Resource and Booking.

OOP ideas shown in this file:
    * Classes and objects   - every class below makes objects
    * Inheritance           - Lecturer, CampusAdministrator and SystemOperator
                              all inherit from User
    * Encapsulation         - attributes start with __ (private) and are
                              read through "getter" methods
    * Polymorphism (bonus)  - each user type has its own get_permissions()
"""

from datetime import datetime, date


# ---------------------------------------------------------------------
# Small helper functions for working with times
# ---------------------------------------------------------------------
def time_to_minutes(time_text):
    """Changes a time like '09:30' into minutes after midnight (570)."""
    hours, minutes = time_text.split(":")
    return int(hours) * 60 + int(minutes)


def minutes_to_time(total_minutes):
    """Changes minutes after midnight (570) back into text ('09:30')."""
    return f"{total_minutes // 60:02d}:{total_minutes % 60:02d}"


# =====================================================================
# USER CLASSES (Inheritance)
# =====================================================================
class User:
    """Parent class for every person who logs into the system."""

    def __init__(self, user_id, username, full_name, email, role_name, campus_id=None):
        # Private attributes (encapsulation) - other code must use getters
        self.__user_id = user_id
        self.__username = username
        self.__full_name = full_name
        self.__email = email
        self.__role_name = role_name
        self.__campus_id = campus_id

    # ----- getters -----
    def get_user_id(self):
        return self.__user_id

    def get_username(self):
        return self.__username

    def get_full_name(self):
        return self.__full_name

    def get_email(self):
        return self.__email

    def get_role(self):
        return self.__role_name

    def get_campus_id(self):
        return self.__campus_id

    def can_change_campus(self):
        """By default users may pick any campus after logging in."""
        return True

    def get_permissions(self):
        """Returns a LIST of things this user may do. Child classes override it."""
        return []

    def has_permission(self, permission):
        return permission in self.get_permissions()

    def __str__(self):
        return f"{self.__full_name} ({self.__role_name})"


class Lecturer(User):
    """A lecturer books resources for classes and presentations."""

    def __init__(self, user_id, username, full_name, email, campus_id=None):
        # super() calls the __init__ of the parent class (User)
        super().__init__(user_id, username, full_name, email, "Lecturer", campus_id)

    def get_permissions(self):
        return ["book_resource", "view_history"]


class CampusAdministrator(User):
    """An administrator manages the resources of ONE campus."""

    def __init__(self, user_id, username, full_name, email, campus_id=None):
        super().__init__(user_id, username, full_name, email, "Campus Administrator", campus_id)

    def can_change_campus(self):
        # Administrators are locked to their own campus
        return False

    def get_permissions(self):
        return ["manage_resources", "view_campus_bookings", "usage_report"]


class SystemOperator(User):
    """Institution management - can see everything on every campus."""

    def __init__(self, user_id, username, full_name, email, campus_id=None):
        super().__init__(user_id, username, full_name, email, "System Operator", campus_id)

    def get_permissions(self):
        return ["view_campuses", "view_all_bookings", "reports"]


# DICTIONARY that links a role name (from the database) to the right class
USER_CLASSES = {
    "Lecturer": Lecturer,
    "Campus Administrator": CampusAdministrator,
    "System Operator": SystemOperator,
}


def create_user(user_id, username, full_name, email, role_name, campus_id=None):
    """Makes the correct type of user object based on the role name."""
    user_class = USER_CLASSES.get(role_name, Lecturer)
    return user_class(user_id, username, full_name, email, campus_id)


# =====================================================================
# CAMPUS CLASS - holds the booking rules for each campus
# =====================================================================
class Campus:
    """
    A campus and its booking policy.
    The rules are stored as attributes, so a new campus with new rules
    can be added to the database without changing this code.
    """

    def __init__(self, campus_id, name, location, max_hours, min_days_advance, open_hour, close_hour):
        self.__campus_id = campus_id
        self.__name = name
        self.__location = location
        self.__max_hours = max_hours
        self.__min_days_advance = min_days_advance
        self.__open_hour = open_hour
        self.__close_hour = close_hour

    def get_campus_id(self):
        return self.__campus_id

    def get_name(self):
        return self.__name

    def get_location(self):
        return self.__location

    def get_max_hours(self):
        return self.__max_hours

    def get_min_days_advance(self):
        return self.__min_days_advance

    def get_open_hour(self):
        return self.__open_hour

    def get_close_hour(self):
        return self.__close_hour

    def get_policy_text(self):
        """Short sentence that is shown in the GUI so users know the rules."""
        text = (f"Max {self.__max_hours} hours per booking | "
                f"Open {self.__open_hour:02d}:00 - {self.__close_hour:02d}:00")
        if self.__min_days_advance > 0:
            text += f" | Book at least {self.__min_days_advance} day(s) in advance"
        return text

    def check_booking_rules(self, booking_date_text, start_time_text, duration_hours):
        """
        Checks a booking against THIS campus's rules.
        Returns a tuple: (True/False, message)
        """
        # 1. Check that the date and time are in the right format
        try:
            booking_date = datetime.strptime(booking_date_text, "%Y-%m-%d").date()
            start_datetime = datetime.strptime(booking_date_text + " " + start_time_text,
                                               "%Y-%m-%d %H:%M")
        except ValueError:
            return False, "Please enter the date as YYYY-MM-DD and the time as HH:MM."

        # 2. Duration must be a positive number
        if duration_hours <= 0:
            return False, "Duration must be at least 1 hour."

        # 3. Advance booking rule (e.g. Cape Town = 1 day)
        days_ahead = (booking_date - date.today()).days
        if days_ahead < self.__min_days_advance:
            return False, (f"{self.__name} requires bookings to be made at least "
                           f"{self.__min_days_advance} day(s) in advance.")

        # 4. No bookings in the past
        if start_datetime <= datetime.now():
            return False, "You cannot make a booking in the past."

        # 5. Maximum duration rule (e.g. Johannesburg = 4 hours)
        if duration_hours > self.__max_hours:
            return False, (f"{self.__name} only allows bookings of up to "
                           f"{self.__max_hours} hours.")

        # 6. Opening hours rule
        start_minutes = time_to_minutes(start_time_text)
        end_minutes = start_minutes + duration_hours * 60
        if start_minutes < self.__open_hour * 60 or end_minutes > self.__close_hour * 60:
            return False, (f"{self.__name} bookings must be between "
                           f"{self.__open_hour:02d}:00 and {self.__close_hour:02d}:00.")

        return True, "The booking follows the campus rules."

    def __str__(self):
        return self.__name


# =====================================================================
# RESOURCE CLASS
# =====================================================================
class Resource:
    """A bookable item such as a computer lab, projector or seminar room."""

    VALID_STATUSES = ["Available", "Unavailable"]

    def __init__(self, resource_id, code, name, resource_type, capacity, status, campus_id):
        self.__resource_id = resource_id
        self.__code = code
        self.__name = name
        self.__resource_type = resource_type
        self.__capacity = capacity
        self.__status = status
        self.__campus_id = campus_id

    def get_resource_id(self):
        return self.__resource_id

    def get_code(self):
        return self.__code

    def get_name(self):
        return self.__name

    def get_type(self):
        return self.__resource_type

    def get_capacity(self):
        return self.__capacity

    def get_status(self):
        return self.__status

    def get_campus_id(self):
        return self.__campus_id

    def set_status(self, new_status):
        """Setter with validation - only allowed values can be stored."""
        if new_status in Resource.VALID_STATUSES:
            self.__status = new_status
            return True
        return False

    def is_available(self):
        return self.__status == "Available"

    def __str__(self):
        return f"{self.__code} - {self.__name}"


# =====================================================================
# BOOKING CLASS
# =====================================================================
class Booking:
    """One booking of a resource by a user."""

    def __init__(self, booking_id, user_id, resource_id, campus_id, booking_date,
                 start_time, duration_hours, status="Active", purpose="",
                 resource_name="", campus_name="", lecturer_name=""):
        self.__booking_id = booking_id
        self.__user_id = user_id
        self.__resource_id = resource_id
        self.__campus_id = campus_id
        self.__booking_date = booking_date
        self.__start_time = start_time
        self.__duration_hours = duration_hours
        self.__status = status
        self.__purpose = purpose
        # Extra display information (filled in from JOIN queries)
        self.__resource_name = resource_name
        self.__campus_name = campus_name
        self.__lecturer_name = lecturer_name

    def get_booking_id(self):
        return self.__booking_id

    def get_user_id(self):
        return self.__user_id

    def get_resource_id(self):
        return self.__resource_id

    def get_campus_id(self):
        return self.__campus_id

    def get_date(self):
        return self.__booking_date

    def get_start_time(self):
        return self.__start_time

    def get_duration(self):
        return self.__duration_hours

    def get_status(self):
        return self.__status

    def get_purpose(self):
        return self.__purpose

    def get_resource_name(self):
        return self.__resource_name

    def get_campus_name(self):
        return self.__campus_name

    def get_lecturer_name(self):
        return self.__lecturer_name

    def get_end_time(self):
        end_minutes = time_to_minutes(self.__start_time) + self.__duration_hours * 60
        return minutes_to_time(end_minutes)

    def get_start_datetime(self):
        return datetime.strptime(self.__booking_date + " " + self.__start_time, "%Y-%m-%d %H:%M")

    def is_future(self):
        return self.get_start_datetime() > datetime.now()

    def get_end_datetime(self):
        return datetime.strptime(self.__booking_date + " " + self.get_end_time(), "%Y-%m-%d %H:%M")

    def get_state(self):
        """Upcoming, In Progress, Completed or Cancelled - used on the history screen."""
        if self.__status == "Cancelled":
            return "Cancelled"
        if self.is_future():
            return "Upcoming"
        if self.get_end_datetime() > datetime.now():
            return "In Progress"      # started but not finished yet
        return "Completed"

    def overlaps_with(self, start_time, duration_hours):
        """
        True if a new booking (start_time, duration) clashes with this one.
        Two time slots overlap when each one starts before the other ends.
        """
        my_start = time_to_minutes(self.__start_time)
        my_end = my_start + self.__duration_hours * 60
        new_start = time_to_minutes(start_time)
        new_end = new_start + duration_hours * 60
        return new_start < my_end and my_start < new_end
