"""
PyIFileDialog - Native Windows File Dialogs for Python

A lightweight, dependency-free Python library that provides access to Windows'
beautiful, modern file dialogs without requiring heavy COM libraries like
comtypes or pywin32.

Quick Start:
    >>> from PyIFileDialog import open_file_dialog, save_file_dialog, open_folder_dialog
    >>> 
    >>> # Select files
    >>> files = open_file_dialog(title="Choose Files")
    >>> 
    >>> # Save a file
    >>> save_path = save_file_dialog(title="Save As")
    >>> 
    >>> # Pick a folder
    >>> folder = open_folder_dialog(title="Select Destination")

Features:
    - Native Windows look and feel
    - No heavy dependencies (ctypes only)
    - Rich file filtering options
    - Multi-selection support
    - Comprehensive customization options
    - Type hints for better IDE support

Requirements:
    - Windows 7 or later
    - Python 3.8+
    - No external dependencies

For detailed documentation and examples, see:
    https://github.com/bolabaden/PyIFileDialog
"""

# Public API - expose the main functions users will need
from windialogs import (
    open_file_dialog,
    save_file_dialog,
    open_folder_dialog,
    open_file_and_folder_dialog,
    DEFAULT_FILTERS,
)

# Version information
__version__ = "1.0.0"
__author__ = "PyIFileDialog Contributors"
__license__ = "MIT"

# Define what gets imported with "from PyIFileDialog import *"
__all__ = [
    "open_file_dialog",
    "save_file_dialog", 
    "open_folder_dialog",
    "open_file_and_folder_dialog",
    "DEFAULT_FILTERS",
]