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

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

We welcome contributions! Whether it's bug reports, feature requests, or code contributions, please feel free to get involved.

## ⭐ Show Your Support

If PyIFileDialog has made your Windows development experience better, consider giving it a star! It helps others discover this helpful library.

---

*Built with ❤️ for the Python community by developers who believe that working with Windows APIs shouldn't require a PhD in COM programming.*
