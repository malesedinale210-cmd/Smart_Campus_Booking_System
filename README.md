Smart Campus Resource Booking System  (Programming 512)
=======================================================

HOW TO RUN
  1. Install Python 3.10 or newer (Tkinter and SQLite are included with Python).
     On Linux also run:  sudo apt install python3-tk
  2. Open a terminal in this folder and run:   python main.py
     (on Windows you can also use:  py main.py)
  The database file campus_booking.db and the sample data are created
  automatically the first time the program runs (from database.sql).

  Automatic tests:  python -m unittest test_system.py -v
  Fresh start:      close the program, delete campus_booking.db, run main.py again.

TEST LOGINS  (password for every account = password123)
  operator    System Operator
  admin_jhb   Campus Administrator - Johannesburg
  admin_dbn   Campus Administrator - Durban
  admin_cpt   Campus Administrator - Cape Town
  thabo, naledi, johan   Lecturers
  (new lecturers can register on the login window)

FILES
  main.py              starts the program
  gui.py               all Tkinter windows
  models.py            User, Lecturer, CampusAdministrator, SystemOperator,
                       Campus, Resource, Booking classes
  database_manager.py  DatabaseManager - all SQLite code
  database.sql         creates the tables and loads the test data
  test_system.py       automatic tests
  reports/             created when a report is saved

CAMPUS BOOKING RULES (stored in the campuses table)
  Johannesburg  max 4 hours, open 08:00-18:00
  Durban        max 6 hours, open 07:00-20:00
  Cape Town     max 5 hours, open 08:00-17:00, book at least 1 day ahead
