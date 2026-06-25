import tkinter as tk
import database as db
from gui import SpotCheckApp


def main():
    # Ensure database and tables exist
    db.initialize_database()

    # Launch Tkinter application
    root = tk.Tk()
    app = SpotCheckApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
