import sys
import os
from cx_Freeze import setup, Executable

# Build options
build_exe_options = {
    "packages": [
        "tkinter", 
        "ttkbootstrap", 
        "PIL", 
        "requests", 
        "threading", 
        "json", 
        "os", 
        "sys"
    ],
    "include_files": [
        ("config.json", "config.json"),
        ("src", "src")  # Include entire src directory
    ],
    "excludes": ["test", "unittest"],
    "optimize": 2,
}

base = "Win32GUI" if sys.platform == "win32" else None

setup(
    name="YTS Browser",
    version="1.0.0",
    description="YTS Torrent Browser",
    options={"build_exe": build_exe_options},
    executables=[Executable("src/main.py", base=base, target_name="YTS_Browser.exe")]
)