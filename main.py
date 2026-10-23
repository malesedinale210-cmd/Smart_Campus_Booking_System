"""
main.py
-------
Start the Smart Campus Resource Booking System by running:
    python main.py
"""

import tkinter as tk

from database_manager import DatabaseManager
from gui import LoginWindow


def main():
    # Create the database connection (creates the database the first time)
    db = DatabaseManager()

    # Create the main Tkinter window
    root = tk.Tk()
    root.geometry("820x560")

    # Close the database properly when the window is closed
    def on_close():
        db.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)

    # Show the login screen first
    LoginWindow(root, db)
    root.mainloop()


if __name__ == "__main__":
    main()
