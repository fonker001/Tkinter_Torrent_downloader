import os
import sys

# Handle both script and compiled modes for cx_Freeze
if getattr(sys, 'frozen', False):
    # Running as compiled executable (cx_Freeze)
    base_path = os.path.dirname(sys.executable)
else:
    # Running as script
    base_path = os.path.dirname(os.path.abspath(__file__))

# Add the appropriate paths
src_path = os.path.join(base_path, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if base_path not in sys.path:
    sys.path.insert(0, base_path)

print(f"Base path: {base_path}")
print(f"Python path: {sys.path}")

try:
    from tkinter import Tk
    from gui.app import YTSBrowser
    print("All imports successful!")
except ImportError as e:
    print(f"Import error: {e}")
    
    # Try to find the module by adding more paths
    possible_paths = [
        os.path.join(base_path, 'src'),
        os.path.join(base_path, 'lib', 'src'),
        base_path,
        os.path.dirname(base_path)
    ]
    
    for path in possible_paths:
        if path not in sys.path and os.path.exists(path):
            sys.path.insert(0, path)
            print(f"Added to path: {path}")
    
    # Try importing again
    try:
        from gui.app import YTSBrowser
        print("Import successful after path adjustment!")
    except ImportError as e2:
        print(f"Final import error: {e2}")
        import tkinter.messagebox
        tkinter.messagebox.showerror("Import Error", f"Failed to import required modules:\n{e2}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        root = Tk()
        app = YTSBrowser(root)
        root.mainloop()
    except Exception as e:
        print(f"Application error: {e}")
        import tkinter.messagebox
        tkinter.messagebox.showerror("Application Error", f"Application failed to start:\n{e}")