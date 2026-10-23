"""
test_system.py
--------------
Automatic tests for the booking logic (no GUI needed).
Run with:   python -m unittest test_system.py -v
A temporary database is used so the real database is not changed.
"""

import os
import tempfile
import unittest
from datetime import date, timedelta

from database_manager import DatabaseManager
from models import Lecturer, CampusAdministrator, SystemOperator, Booking


class TestBookingSystem(unittest.TestCase):

    def setUp(self):
        # New empty temporary database for every test
        self.temp_folder = tempfile.mkdtemp()
        self.db = DatabaseManager(os.path.join(self.temp_folder, "test.db"))
        self.campuses = self.db.get_campuses()
        self.jhb = self.campuses["Johannesburg Campus"]
        self.dbn = self.campuses["Durban Campus"]
        self.cpt = self.campuses["Cape Town Campus"]
        self.lecturer = self.db.login("thabo", "password123")
        self.in_5_days = (date.today() + timedelta(days=5)).strftime("%Y-%m-%d")

    def tearDown(self):
        self.db.close()

    def get_resource(self, campus, code):
        for resource in self.db.get_resources(campus.get_campus_id()):
            if resource.get_code() == code:
                return resource

    # ----- login and roles (inheritance) -----
    def test_login_creates_correct_classes(self):
        self.assertIsInstance(self.db.login("thabo", "password123"), Lecturer)
        self.assertIsInstance(self.db.login("admin_jhb", "password123"), CampusAdministrator)
        self.assertIsInstance(self.db.login("operator", "password123"), SystemOperator)

    def test_wrong_password_fails(self):
        self.assertIsNone(self.db.login("thabo", "wrong"))

    def test_register_and_duplicate_username(self):
        ok, _ = self.db.register_user("newlect", "secret1", "New Lecturer", "n@r.ac.za")
        self.assertTrue(ok)
        ok, _ = self.db.register_user("newlect", "secret1", "Again", "a@r.ac.za")
        self.assertFalse(ok)

    # ----- campus rules -----
    def test_johannesburg_max_4_hours(self):
        lab = self.get_resource(self.jhb, "JHB-SEM01")
        ok, _ = self.db.create_booking(self.lecturer, self.jhb, lab, self.in_5_days, "08:00", 5, "x")
        self.assertFalse(ok)
        ok, _ = self.db.create_booking(self.lecturer, self.jhb, lab, self.in_5_days, "08:00", 4, "x")
        self.assertTrue(ok)

    def test_durban_allows_6_hours_not_7(self):
        lab = self.get_resource(self.dbn, "DBN-SEM01")
        ok, _ = self.db.create_booking(self.lecturer, self.dbn, lab, self.in_5_days, "07:00", 7, "x")
        self.assertFalse(ok)
        ok, _ = self.db.create_booking(self.lecturer, self.dbn, lab, self.in_5_days, "07:00", 6, "x")
        self.assertTrue(ok)

    def test_cape_town_needs_one_day_advance(self):
        ok, message = self.cpt.check_booking_rules(date.today().strftime("%Y-%m-%d"), "16:30", 0 + 1)
        self.assertFalse(ok)
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        ok, _ = self.cpt.check_booking_rules(tomorrow, "09:00", 2)
        self.assertTrue(ok)

    def test_outside_opening_hours(self):
        ok, _ = self.jhb.check_booking_rules(self.in_5_days, "17:00", 2)  # ends 19:00, closes 18:00
        self.assertFalse(ok)

    def test_past_date_rejected(self):
        yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        ok, _ = self.dbn.check_booking_rules(yesterday, "09:00", 1)
        self.assertFalse(ok)

    def test_bad_date_format(self):
        ok, _ = self.jhb.check_booking_rules("22/10/2026", "09:00", 1)
        self.assertFalse(ok)

    # ----- booking rules -----
    def test_overlap_prevented(self):
        lab = self.get_resource(self.jhb, "JHB-LAB01")
        ok, _ = self.db.create_booking(self.lecturer, self.jhb, lab, self.in_5_days, "09:00", 2, "x")
        self.assertTrue(ok)
        ok, _ = self.db.create_booking(self.lecturer, self.jhb, lab, self.in_5_days, "10:00", 1, "x")
        self.assertFalse(ok)
        # Starting exactly when the other one ends is fine
        ok, _ = self.db.create_booking(self.lecturer, self.jhb, lab, self.in_5_days, "11:00", 1, "x")
        self.assertTrue(ok)

    def test_unavailable_resource_rejected(self):
        lab2 = self.get_resource(self.jhb, "JHB-LAB02")   # Unavailable in test data
        ok, _ = self.db.create_booking(self.lecturer, self.jhb, lab2, self.in_5_days, "09:00", 1, "x")
        self.assertFalse(ok)

    def test_cancel_future_booking_only(self):
        history = self.db.get_user_bookings(self.lecturer.get_user_id())
        future = [b for b in history if b.get_state() == "Upcoming"][0]
        past = [b for b in history if b.get_state() == "Completed"][0]
        self.assertTrue(self.db.cancel_booking(future.get_booking_id(), self.lecturer.get_user_id())[0])
        self.assertFalse(self.db.cancel_booking(past.get_booking_id(), self.lecturer.get_user_id())[0])

    # ----- resources -----
    def test_duplicate_resource_code_rejected(self):
        ok, _ = self.db.add_resource("jhb-lab01", "Another Lab", "Computer Lab", 20, self.jhb.get_campus_id())
        self.assertFalse(ok)
        ok, _ = self.db.add_resource("JHB-LAB09", "Lab 9", "Computer Lab", 20, self.jhb.get_campus_id())
        self.assertTrue(ok)

    def test_cannot_delete_resource_with_bookings(self):
        lab = self.get_resource(self.jhb, "JHB-LAB01")
        self.assertFalse(self.db.delete_resource(lab.get_resource_id())[0])

    # ----- reports -----
    def test_campus_report_values(self):
        report = self.db.get_campus_report(self.jhb)
        self.assertEqual(report["total_bookings"], 5)
        self.assertEqual(report["total_hours"], 10)
        self.assertEqual(report["average_duration"], 2.0)
        self.assertIn("JHB-LAB01", report["most_used"])
        self.assertEqual(len(self.db.get_comparison_report()), 3)

    # ----- extra tests for the improvements -----
    def test_login_is_not_case_sensitive(self):
        self.assertIsNotNone(self.db.login("THABO", "password123"))
        ok, _ = self.db.register_user("Thabo", "secret1", "Copy", "c@r.ac.za")
        self.assertFalse(ok)    # same username, only the case is different

    def test_cape_town_same_day_always_gives_advance_message(self):
        ok, message = self.cpt.check_booking_rules(date.today().strftime("%Y-%m-%d"), "16:30", 1)
        self.assertFalse(ok)
        self.assertIn("in advance", message)

    def test_monthly_trend_in_report(self):
        report = self.db.get_campus_report(self.jhb)
        self.assertEqual(sum(report["monthly"].values()), report["total_bookings"])

    def test_add_resource_with_status(self):
        ok, _ = self.db.add_resource("JHB-LAB10", "Lab 10", "Computer Lab", 20,
                                     self.jhb.get_campus_id(), "Unavailable")
        self.assertTrue(ok)
        self.assertFalse(self.get_resource(self.jhb, "JHB-LAB10").is_available())

    def test_booking_states(self):
        today = date.today().strftime("%Y-%m-%d")
        done = Booking(1, 1, 1, 1, "2020-01-01", "09:00", 2)
        later = Booking(2, 1, 1, 1, (date.today() + timedelta(days=2)).strftime("%Y-%m-%d"), "09:00", 2)
        cancelled = Booking(3, 1, 1, 1, today, "09:00", 2, "Cancelled")
        self.assertEqual(done.get_state(), "Completed")
        self.assertEqual(later.get_state(), "Upcoming")
        self.assertEqual(cancelled.get_state(), "Cancelled")

    def test_overlap_method(self):
        booking = Booking(1, 1, 1, 1, self.in_5_days, "09:00", 2)
        self.assertTrue(booking.overlaps_with("10:30", 1))
        self.assertFalse(booking.overlaps_with("07:00", 2))
        self.assertEqual(booking.get_end_time(), "11:00")


if __name__ == "__main__":
    unittest.main()
