from tkinter import Tk
from src.gui.app import YTSBrowser

if __name__ == "__main__":
    root = Tk()
    app = YTSBrowser(root)
    root.mainloop()