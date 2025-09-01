# PyIFileDialog 🗂️

> *A lightweight, dependency-free Python library for native Windows file dialogs*

PyIFileDialog brings you the power of Windows' beautiful, modern file dialogs without the heavyweight dependencies. No more dealing with comtypes, pywin32, or other complex COM libraries – this library gives you direct access to Windows' native IFileDialog interfaces using pure Python and ctypes.

## ✨ What Makes This Special?

Think of PyIFileDialog as your friendly bridge between Python and Windows' sophisticated file dialog system. Instead of wrestling with complex COM libraries or settling for basic file pickers, you get:

- **Native Windows Look & Feel** - Your users get the same beautiful, familiar dialogs they see everywhere else in Windows
- **Zero Heavy Dependencies** - Built using only Python's standard library and ctypes
- **Rich Functionality** - Support for file filters, multi-selection, folder picking, and custom dialog options
- **Modern & Maintained** - Designed for modern Python (3.8+) with type hints and clean APIs

## 🚀 Quick Start

Getting started is as simple as importing and calling a function:

```python
from windialogs import open_file_dialog, save_file_dialog, open_folder_dialog

# Open a file - returns a list of selected file paths
selected_files = open_file_dialog(
    title="Choose your adventure",
    default_folder="C:/Users/Documents",
    file_types=[
        ("Text Files", "*.txt"),
        ("Python Files", "*.py"),
        ("All Files", "*.*")
    ]
)

if selected_files:
    print(f"You selected: {selected_files[0]}")

# Save a file - perfect for "Save As" functionality
save_location = save_file_dialog(
    title="Save Your Masterpiece",
    default_extension="txt",
    file_types=[("Text Files", "*.txt"), ("All Files", "*.*")]
)

# Pick a folder - great for destination selection
folder = open_folder_dialog(title="Choose Destination Folder")
```

## 🎯 Real-World Examples

### Image Processing Application

```python
from windialogs import open_file_dialog, save_file_dialog

def import_images():
    """Let users select multiple image files for processing."""
    return open_file_dialog(
        title="Import Images for Processing",
        file_types=[
            ("Common Images", "*.jpg;*.jpeg;*.png;*.gif;*.bmp"),
            ("JPEG Images", "*.jpg;*.jpeg"),
            ("PNG Images", "*.png"),
            ("All Files", "*.*")
        ],
        allow_multiple_selection=True,
        default_folder="C:/Pictures",
        show_hidden_files=False
    )

def export_result():
    """Save processed image with format validation."""
    return save_file_dialog(
        title="Export Processed Image",
        file_types=[
            ("PNG (High Quality)", "*.png"),
            ("JPEG (Compressed)", "*.jpg"),
            ("BMP (Uncompressed)", "*.bmp")
        ],
        default_extension="png",
        overwrite_prompt=True
    )

# Usage
input_files = import_images()
if input_files:
    # Process images...
    output_file = export_result()
    if output_file:
        # Save result...
        print(f"Saved to: {output_file}")
```

### Document Management System

```python
from windialogs import open_folder_dialog, open_file_dialog

def setup_document_workspace():
    """Let users choose workspace folder and import documents."""
    
    # Choose workspace root
    workspace = open_folder_dialog(
        title="Select Document Workspace",
        default_folder="C:/Documents",
        path_must_exist=True
    )
    
    if not workspace:
        return None
    
    # Import existing documents
    documents = open_file_dialog(
        title="Import Existing Documents",
        file_types=[
            ("Documents", "*.pdf;*.doc;*.docx;*.txt;*.rtf"),
            ("PDF Files", "*.pdf"),
            ("Word Documents", "*.doc;*.docx"),
            ("Text Files", "*.txt;*.rtf"),
            ("All Files", "*.*")
        ],
        allow_multiple_selection=True,
        force_filesystem=True,
        add_to_recent=True
    )
    
    return {
        "workspace": workspace[0],
        "documents": documents or []
    }

# Usage
setup = setup_document_workspace()
if setup:
    print(f"Workspace: {setup['workspace']}")
    print(f"Documents: {len(setup['documents'])} files")
```

### Backup Utility

```python
from windialogs import open_folder_dialog

def create_backup_job():
    """Configure source and destination for backup."""
    
    # Select what to backup
    source_folders = open_folder_dialog(
        title="Select Folders to Backup",
        allow_multiple_selection=True,
        force_filesystem=True,
        path_must_exist=True
    )
    
    if not source_folders:
        return None
    
    # Select backup destination
    backup_destination = open_folder_dialog(
        title="Choose Backup Destination",
        allow_multiple_selection=False,
        force_filesystem=True,
        no_change_dir=True
    )
    
    if not backup_destination:
        return None
    
    return {
        "sources": source_folders,
        "destination": backup_destination[0]
    }

# Usage
backup_config = create_backup_job()
if backup_config:
    print(f"Backing up {len(backup_config['sources'])} folders")
    print(f"Destination: {backup_config['destination']}")
```

## 📁 Core Components Explained

PyIFileDialog is architected around several key components that work together harmoniously:

### 🎯 `windialogs.py` - Your Main Interface

This is where the magic happens! It's your one-stop shop for file dialog functionality:

- **`open_file_dialog()`** - For when users need to pick existing files
- **`save_file_dialog()`** - For "Save As" scenarios 
- **`open_folder_dialog()`** - When you need directory selection
- **`open_file_and_folder_dialog()`** - A hybrid approach for maximum flexibility

Each function accepts intuitive parameters like `title`, `default_folder`, `file_types`, and a wealth of customization options. The library handles all the complex COM interactions behind the scenes, giving you simple, Pythonic functions that just work.

### 🔧 `interfaces.py` - COM Interface Definitions

This file contains the Python representations of Windows' COM interfaces. Think of it as the blueprint that tells Python how to communicate with Windows' file dialog system:

- **`IFileOpenDialog`** / **`IFileSaveDialog`** - The core dialog interfaces
- **`IShellItem`** / **`IShellItemArray`** - Represents files and folders in the Windows shell
- **`IFileDialogCustomize`** - Enables custom controls in dialogs

These interfaces are carefully crafted to match Microsoft's official COM specifications, ensuring compatibility and reliability.

### 🏗️ `iunknown.py` - COM Foundation Layer

Every COM object in Windows inherits from IUnknown - this file provides that fundamental building block:

- **Reference counting** - Manages object lifetimes properly
- **Interface querying** - Allows objects to expose multiple interfaces
- **Memory management** - Ensures proper cleanup of COM objects

This is the bedrock that makes all COM communication possible, handling the low-level details so you don't have to.

### 🛠️ `com_helpers.py` - Utility Functions & Context Managers

This module contains helpful utilities that make COM programming more pleasant:

- **`COMInitializeContext`** - Ensures COM is properly initialized
- **`HandleCOMCall`** - Provides robust error handling for COM calls
- **`comtypes2pywin`** - Bridges between different COM implementations when needed

Think of these as your safety net - they handle the boring-but-critical stuff like initialization, cleanup, and error handling.

### 📊 `constants.py` - Windows Constants & Enumerations

Windows uses a lot of numeric constants and flags. This file organizes them into meaningful, typed enumerations:

- **`FileOpenOptions`** - Controls dialog behavior (multi-select, folder picking, etc.)
- **`SFGAO`** - Shell item attributes (is it a file? folder? readonly?)
- **`SIGDN`** - Display name types (full path, relative path, etc.)

Instead of remembering magic numbers, you get clear, self-documenting constants.

### ⚡ `hresult.py` - Windows Error Handling

Windows COM functions return HRESULT codes to indicate success or failure. This module:

- **Decodes error codes** into meaningful messages
- **Provides exception classes** for different error types  
- **Handles success codes** appropriately

No more cryptic numeric error codes - you get proper Python exceptions with helpful messages.

### 🎯 `com_types.py` - COM Type Definitions

Defines the fundamental COM types used throughout the library:

- **GUID** - Globally unique identifiers for COM interfaces
- **Interface IDs** - Specific identifiers for each dialog type
- **Type mappings** - Bridges between Python and Windows types

## 🎛️ Advanced Usage & Customization

PyIFileDialog offers extensive customization options for power users:

### File Type Filters

Create sophisticated file filters to guide users:

```python
file_types = [
    ("Images", "*.jpg;*.png;*.gif;*.bmp"),
    ("Documents", "*.pdf;*.doc;*.docx;*.txt"),
    ("Archives", "*.zip;*.rar;*.7z"),
    ("Everything", "*.*")
]

files = open_file_dialog(file_types=file_types)
```

### Dialog Behavior Options

Fine-tune how your dialogs behave:

```python
files = open_file_dialog(
    allow_multiple_selection=True,     # Let users pick multiple files
    force_filesystem=True,             # Only show real files, not virtual items
    no_change_dir=True,               # Don't change the current directory
    show_hidden_files=True,           # Include hidden files
    path_must_exist=True,             # Validate paths exist
    add_to_recent=False               # Don't add to recent documents
)
```

### Custom Folder Dialogs

When you need folder selection with specific requirements:

```python
folder = open_folder_dialog(
    title="Select Project Directory",
    default_folder="C:/Projects",
    allow_multiple_selection=True,     # Pick multiple folders
    force_filesystem=True,             # Only real directories
    path_must_exist=True              # Must exist already
)
```

## 🔧 How It All Works Together

When you call `open_file_dialog()`, here's the beautiful orchestration that happens:

1. **Initialization** - COM is initialized using `com_helpers.py`
2. **Dialog Creation** - The appropriate COM object is created using interfaces from `interfaces.py`
3. **Configuration** - Your options are applied using constants from `constants.py`
4. **Display** - The native Windows dialog appears
5. **Result Processing** - Selected paths are extracted and returned
6. **Cleanup** - All COM objects are properly released

All of this complexity is hidden behind simple, intuitive function calls. You get the power of Windows' native dialogs without any of the traditional COM programming pain.

## 🎨 Design Philosophy

PyIFileDialog embraces several key principles:

### Simplicity Over Complexity
Rather than exposing every possible COM interface, we focus on the 90% use case with clean, simple APIs. Advanced users can still access lower-level functionality when needed.

### Pythonic APIs
Functions use keyword arguments, sensible defaults, and follow Python naming conventions. You shouldn't need to understand COM to use this library effectively.

### Type Safety
Extensive type hints help your IDE understand what you're working with, reducing bugs and improving the development experience.

### Robustness
Comprehensive error handling ensures your applications fail gracefully when something goes wrong, with helpful error messages instead of cryptic COM errors.

## 💡 When to Use PyIFileDialog

This library shines when you need:

- **Professional file dialogs** in desktop applications
- **Native Windows integration** without heavy dependencies
- **Custom file filtering** and dialog behavior
- **Multi-file selection** capabilities
- **Folder picking** functionality
- **Integration with existing ctypes-based code**

## 🔧 Requirements

- **Windows Operating System** (Windows 7 or later)
- **Python 3.8+** 
- **Standard Library Only** - No external dependencies required!

## 🚨 Troubleshooting & FAQ

### Common Issues

**Q: I get `ImportError: cannot import name 'windll' from 'ctypes'`**

A: This library is Windows-specific and uses Windows COM APIs. The `windll` module is only available on Windows systems. Make sure you're running on Windows, not Linux or macOS.

**Q: The dialog doesn't appear or appears behind other windows**

A: This usually happens when the parent window handle (`hwnd`) is incorrect or when called from a background thread. Try:
```python
# Use 0 for no parent window
files = open_file_dialog(hwnd=0)

# Or get the correct window handle if you have a GUI framework
```

**Q: I get COM errors or access violations**

A: This typically indicates COM apartment threading issues. Make sure you're calling dialog functions from the main GUI thread. For background threads:
```python
import threading

def show_dialog_on_main_thread():
    # Your dialog code here
    pass

# Call from main thread
threading.main_thread().join()  # Ensure we're on main thread
```

**Q: File types filters don't work as expected**

A: Make sure your filter patterns are correctly formatted:
```python
# Correct - multiple extensions separated by semicolons
("Images", "*.jpg;*.png;*.gif")

# Incorrect - don't use commas or spaces
("Images", "*.jpg, *.png, *.gif")  # Wrong!
```

**Q: Dialog options seem to be ignored**

A: Windows automatically resolves conflicting options. Check the debug output to see which options were modified. Some combinations are mutually exclusive:
```python
# These conflict - Windows will auto-resolve
open_file_dialog(
    force_filesystem=True,        # Conflicts with...
    all_non_storage_items=True   # ...this option
)
```

### Performance Tips

**Reuse Dialog Objects**: For repeated operations, consider reusing dialog configurations:
```python
# Cache common filter sets
IMAGE_FILTERS = [
    ("Images", "*.jpg;*.png;*.gif"),
    ("All Files", "*.*")
]

# Reuse in multiple places
files1 = open_file_dialog(file_types=IMAGE_FILTERS)
files2 = open_file_dialog(file_types=IMAGE_FILTERS)
```

**Avoid Excessive Options**: Only specify options you actually need. Default values are optimized for common use cases.

### Best Practices

1. **Always check for None returns** - Users can cancel dialogs
2. **Use appropriate default folders** - Start where users expect
3. **Provide clear dialog titles** - Help users understand the purpose
4. **Use meaningful file type descriptions** - "Images" not "img files"
5. **Test with different Windows versions** - Behavior can vary slightly

### Integration with GUI Frameworks

**Tkinter Integration**:
```python
import tkinter as tk
from windialogs import open_file_dialog

def browse_files():
    # Get tkinter window handle if needed
    hwnd = root.winfo_id() if hasattr(root, 'winfo_id') else 0
    files = open_file_dialog(hwnd=hwnd)
    if files:
        file_var.set(files[0])

root = tk.Tk()
file_var = tk.StringVar()
# ... rest of GUI setup
```

**PyQt/PySide Integration**:
```python
from PyQt5.QtWidgets import QWidget
from windialogs import open_file_dialog

class MainWindow(QWidget):
    def browse_files(self):
        # Get Qt window handle
        hwnd = int(self.winId()) if hasattr(self, 'winId') else 0
        files = open_file_dialog(hwnd=hwnd)
        if files:
            self.process_files(files)
```

### Debugging Tips

Enable debug output by monitoring console output when testing. The library provides detailed information about:
- COM initialization status
- Option conflicts and resolutions
- Dialog configuration details
- File selection results

For complex scenarios, use Python's logging module to capture debug information:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Your dialog calls will now show detailed debug info
files = open_file_dialog(title="Debug Test")
```

## 📚 API Reference

### Core Functions

#### `open_file_dialog(**kwargs) -> list[str] | None`

Opens a dialog for selecting existing files.

**Parameters:**
- `title` (str, optional): Dialog window title
- `default_folder` (str, optional): Initial directory path
- `file_types` (list[tuple[str, str]], optional): File type filters as (description, pattern) pairs
- `default_extension` (str, optional): Default file extension
- `allow_multiple_selection` (bool): Enable multi-file selection (default: False)
- `force_filesystem` (bool): Only show real files/folders (default: True)
- `path_must_exist` (bool): Require selected paths to exist (default: True)
- `file_must_exist` (bool): Require selected files to exist (default: True)
- `show_hidden_files` (bool): Include hidden files (default: False)
- `add_to_recent` (bool): Add selections to recent files (default: True)
- `ok_button_text` (str, optional): Custom button text

**Returns:** List of selected file paths, or None if cancelled

#### `save_file_dialog(**kwargs) -> list[str] | None`

Opens a dialog for saving/creating files.

**Parameters:**
- `title` (str, optional): Dialog window title
- `default_folder` (str, optional): Initial directory path
- `file_types` (list[tuple[str, str]], optional): File type filters
- `default_extension` (str, optional): Default file extension
- `overwrite_prompt` (bool): Prompt before overwriting (default: True)
- `force_filesystem` (bool): Only show real locations (default: True)
- `path_must_exist` (bool): Require parent directory to exist (default: True)
- `ok_button_text` (str, optional): Custom button text

**Returns:** List containing the save path, or None if cancelled

#### `open_folder_dialog(**kwargs) -> list[str] | None`

Opens a dialog for selecting folders/directories.

**Parameters:**
- `title` (str, optional): Dialog window title
- `default_folder` (str, optional): Initial directory path
- `allow_multiple_selection` (bool): Enable multi-folder selection (default: False)
- `force_filesystem` (bool): Only show real directories (default: True)
- `path_must_exist` (bool): Require selected paths to exist (default: True)
- `show_hidden_files` (bool): Include hidden folders (default: False)
- `ok_button_text` (str, optional): Custom button text

**Returns:** List of selected folder paths, or None if cancelled

### Advanced Options

All dialog functions support these additional options for fine-tuned control:

#### Validation Options
- `strict_file_types` (bool): Enforce file type restrictions
- `no_validate` (bool): Disable path validation
- `create_prompt` (bool): Prompt to create non-existent files

#### Behavior Options
- `no_change_dir` (bool): Don't change current working directory
- `no_readonly_return` (bool): Prevent selection of read-only items
- `no_test_file_create` (bool): Skip file creation tests
- `share_aware` (bool): Handle file sharing conflicts

#### UI Options
- `hide_mru_places` (bool): Hide most recently used places
- `hide_pinned_places` (bool): Hide pinned locations
- `default_no_minimode` (bool): Use full-size dialog
- `force_preview_pane_on` (bool): Always show preview pane

#### Link Handling
- `no_dereference_links` (bool): Don't follow shortcuts/symlinks

### File Type Filter Examples

```python
# Simple filters
file_types = [
    ("Text Files", "*.txt"),
    ("All Files", "*.*")
]

# Multiple extensions per filter
file_types = [
    ("Images", "*.jpg;*.png;*.gif;*.bmp"),
    ("Documents", "*.pdf;*.doc;*.docx"),
    ("Archives", "*.zip;*.rar;*.7z")
]

# Specific patterns
file_types = [
    ("Python Files", "*.py"),
    ("Python Packages", "*.whl;*.egg"),
    ("Configuration", "*.ini;*.cfg;*.conf"),
]
```

### Return Value Patterns

All functions follow consistent return patterns:

```python
# Single file selection
result = open_file_dialog()
if result:
    file_path = result[0]  # Always a list, even for single selection
    print(f"Selected: {file_path}")
else:
    print("User cancelled")

# Multiple file selection
result = open_file_dialog(allow_multiple_selection=True)
if result:
    for file_path in result:
        print(f"Processing: {file_path}")
else:
    print("No files selected")

# Save dialog
result = save_file_dialog()
if result:
    save_path = result[0]  # Single item list for save operations
    print(f"Saving to: {save_path}")
```

### Error Handling

```python
try:
    files = open_file_dialog(default_folder="C:/NonexistentPath")
except FileNotFoundError:
    print("Default folder doesn't exist")
except OSError as e:
    print(f"COM error: {e}")
```

### Threading Considerations

```python
import threading
from windialogs import open_file_dialog

def safe_dialog_call():
    """Ensure dialog is called from main thread."""
    if threading.current_thread() is threading.main_thread():
        return open_file_dialog()
    else:
        # Use your GUI framework's thread-safe method
        # For example, with tkinter:
        # root.after_idle(lambda: open_file_dialog())
        raise RuntimeError("File dialogs must be called from main thread")
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

We welcome contributions! Whether it's bug reports, feature requests, or code contributions, please feel free to get involved.

## ⭐ Show Your Support

If PyIFileDialog has made your Windows development experience better, consider giving it a star! It helps others discover this helpful library.

---

*Built with ❤️ for the Python community by developers who believe that working with Windows APIs shouldn't require a PhD in COM programming.*

## 🤝 Contributing

We welcome contributions! Whether it's bug reports, feature requests, or code contributions, please feel free to get involved.

## ⭐ Show Your Support

If PyIFileDialog has made your Windows development experience better, consider giving it a star! It helps others discover this helpful library.

---

*Built with ❤️ for the Python community by developers who believe that working with Windows APIs shouldn't require a PhD in COM programming.*
