"""
PyIFileDialog - Native Windows File Dialog Interface

This is the main user-facing module of PyIFileDialog, providing simple, intuitive
functions for displaying Windows' beautiful native file dialogs. No more dealing
with complex COM libraries or settling for basic file pickers - get the full
power of Windows' modern dialog system with clean Python APIs.

What This Module Provides:
==========================

Core Dialog Functions:
- open_file_dialog(): Select existing files with rich filtering options
- save_file_dialog(): "Save As" dialogs with validation and overwrite protection  
- open_folder_dialog(): Directory selection with multi-folder support
- open_file_and_folder_dialog(): Hybrid approach for maximum flexibility

Under the Hood:
===============

This module orchestrates several complex processes:

1. COM Initialization: Sets up Windows' Component Object Model system
2. Dialog Creation: Instantiates the appropriate IFileDialog COM objects
3. Configuration: Applies your options using Windows constants and flags
4. Display: Shows the native Windows dialog using system APIs
5. Result Processing: Extracts selected paths and formats them for Python
6. Cleanup: Properly releases all COM objects and resources

All of this complexity is hidden behind simple function calls that feel natural
to Python developers. You get professional, native-looking dialogs without
needing to understand the intricacies of COM programming.

Advanced Features:
==================

- Rich file type filtering with custom extensions
- Multi-selection support for files and folders
- Dialog behavior customization (validation, hidden files, etc.)
- Custom button labels and dialog titles
- Default folder and extension handling
- Integration with Windows' recent files and places

Each function accepts intuitive keyword arguments that map to Windows' underlying
dialog options, giving you fine-grained control while maintaining simplicity.

Example Usage:
==============

```python
# Simple file selection
files = open_file_dialog(title="Choose your files")

# Advanced file selection with filtering
files = open_file_dialog(
    title="Import Images",
    file_types=[
        ("Images", "*.jpg;*.png;*.gif"),
        ("JPEG Files", "*.jpg;*.jpeg"),
        ("All Files", "*.*")
    ],
    allow_multiple_selection=True,
    default_folder="C:/Pictures"
)

# Save dialog with validation
save_path = save_file_dialog(
    title="Export Report",
    default_extension="pdf",
    file_types=[("PDF Files", "*.pdf")],
    overwrite_prompt=True
)

# Folder selection
folder = open_folder_dialog(
    title="Choose Destination",
    allow_multiple_selection=False
)
```

Error Handling:
===============

All functions return None if the user cancels the dialog. Actual errors (like
invalid paths or COM failures) raise appropriate Python exceptions with helpful
messages. The module handles Windows-specific errors gracefully, translating
cryptic COM error codes into meaningful exception messages.

Thread Safety:
==============

These functions are designed to be called from the main GUI thread. COM
initialization and dialog display must happen on the same thread that will
process Windows messages. For background threads, ensure proper COM apartment
initialization before calling these functions.
"""
from __future__ import annotations

import errno
import json
import os
import random

from ctypes import POINTER, byref, c_void_p, c_wchar_p, cast as cast_with_ctypes, windll
from ctypes.wintypes import HWND
from pathlib import WindowsPath
from typing import TYPE_CHECKING, Sequence

import comtypes  # pyright: ignore[reportMissingTypeStubs]
import comtypes.client  # pyright: ignore[reportMissingTypeStubs]

from com_helpers import HandleCOMCall
from constants import COMDLG_FILTERSPEC, SFGAO, SIGDN, FileOpenOptions
from hresult import HRESULT, S_OK
from interfaces import CLSID_FileOpenDialog, CLSID_FileSaveDialog, IFileDialogControlEvents, IFileDialogCustomize, IFileOpenDialog, IFileSaveDialog, IID_IFileDialogCustomize, IShellItem

if TYPE_CHECKING:
    from ctypes import c_ulong
    from ctypes.wintypes import BOOL, DWORD, LPWSTR

    from interfaces import IFileDialog, IShellItemArray


class FileDialogControlEvents(comtypes.COMObject):
    _com_interfaces_: Sequence[type[comtypes.IUnknown]] = [IFileDialogControlEvents]

    def __init__(self, file_dialog: IFileDialog):
        self._file_dialog: IFileDialog = file_dialog
        self.selected_path: str | None = None
        super().__init__()

    def OnItemSelected(self, pfdc: IFileDialogCustomize, dwIDCtl: DWORD, dwIDItem: DWORD) -> HRESULT:  # noqa: N803
        # Implement the logic for when an item is selected
        return S_OK

    def OnButtonClicked(self, pfdc: IFileDialogCustomize, dwIDCtl: DWORD) -> HRESULT:  # noqa: N803
        if dwIDCtl == 1001:  # ID for 'Select Folder' button
            print("Button with ID 1001 ('Select Folder') was clicked.")
            self.selected_path = self.get_selected_folder()  # Store the selected path
            if self.selected_path:
                print(f"Stored selected folder: {self.selected_path}")
                self._file_dialog.Close(S_OK)
        return S_OK

    def get_selected_folder(self) -> str | None:
        try:
            selected_item = self._file_dialog.GetCurrentSelection()
        except OSError:
            selected_item = None

        if selected_item:
            szFilePath: str = selected_item.GetDisplayName(SIGDN.SIGDN_FILESYSPATH)
            path = WindowsPath(szFilePath)
            if path.exists() and path.is_dir():
                return str(path)
            if path.exists() and path.is_file():
                return str(path.parent)

        current_folder_item: IShellItem = self._file_dialog.GetFolder()
        if current_folder_item:
            current_folder_path: str = current_folder_item.GetDisplayName(SIGDN.SIGDN_FILESYSPATH)
            return str(WindowsPath(current_folder_path))

        return None

    def OnCheckButtonToggled(self, pfdc: IFileDialogCustomize, dwIDCtl: DWORD, bChecked: BOOL) -> HRESULT:  # noqa: N803
        # Implement the logic for when a check button is toggled
        return S_OK

    def OnControlActivating(self, pfdc: IFileDialogCustomize, dwIDCtl: DWORD) -> HRESULT:  # noqa: N803
        # Implement the logic for when a control is activated
        return S_OK


def show_file_dialog(
    fileDialog: IFileOpenDialog | IFileSaveDialog,  # noqa: N803
    hwndOwner: HWND,  # noqa: N803
) -> bool:
    """
    Display a Windows file dialog and handle user interaction.
    
    This is the core function that actually shows the dialog to the user and
    manages the interaction. It handles the complex details of COM error codes
    and user cancellation, providing a clean boolean result.
    
    The function carefully distinguishes between user cancellation (which returns
    False) and actual errors (which raise exceptions). This allows calling code
    to handle these scenarios appropriately.
    
    Args:
        fileDialog: The configured COM dialog object (open or save variant)
        hwndOwner: Handle to the parent window (use 0 for no parent)
    
    Returns:
        bool: True if user completed dialog successfully, False if cancelled
        
    Raises:
        OSError: For actual COM errors or system failures
        
    Implementation Notes:
        - Handles the special Windows error code for user cancellation
        - Uses HRESULT.raise_for_status() for proper error reporting
        - Provides debug output for development/troubleshooting
    """
    hr: HRESULT | int = -1
    CANCELLED_BY_USER = -2147023673

    try:
        hr = fileDialog.Show(hwndOwner)
        print(f"Dialog shown successfully, HRESULT: {hr}")
    except OSError as e:
        if e.winerror == CANCELLED_BY_USER:
            print("Operation was canceled by the user.")
            return False
        raise
    else:
        HRESULT.raise_for_status(hr, "An unexpected error occurred showing the file browser dialog")

    return True


DEFAULT_FILTERS: list[COMDLG_FILTERSPEC] = [
    COMDLG_FILTERSPEC("All Files", "*.*"),
    COMDLG_FILTERSPEC("Text Files", "*.txt"),
    COMDLG_FILTERSPEC("Image Files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif"),
    COMDLG_FILTERSPEC("Document Files", "*.doc;*.docx;*.pdf;*.xls;*.xlsx"),
    COMDLG_FILTERSPEC("Audio Files", "*.mp3;*.wav;*.wma;*.aac"),
    COMDLG_FILTERSPEC("Video Files", "*.mp4;*.avi;*.mkv;*.mov;*.wmv"),
    COMDLG_FILTERSPEC("Archive Files", "*.zip;*.rar;*.7z;*.tar;*.gz"),
    COMDLG_FILTERSPEC("Executable Files", "*.exe;*.bat;*.msi"),
    COMDLG_FILTERSPEC("HTML Files", "*.htm;*.html"),
    COMDLG_FILTERSPEC("XML Files", "*.xml"),
    COMDLG_FILTERSPEC("JavaScript Files", "*.js"),
    COMDLG_FILTERSPEC("CSS Files", "*.css"),
    COMDLG_FILTERSPEC("Python Files", "*.py"),
    COMDLG_FILTERSPEC("C/C++ Files", "*.c;*.cpp;*.h;*.hpp"),
    COMDLG_FILTERSPEC("Java Files", "*.java"),
    COMDLG_FILTERSPEC("Ruby Files", "*.rb"),
    COMDLG_FILTERSPEC("Perl Files", "*.pl"),
    COMDLG_FILTERSPEC("PHP Files", "*.php"),
    COMDLG_FILTERSPEC("Shell Script Files", "*.sh"),
    COMDLG_FILTERSPEC("Batch Files", "*.bat"),
    COMDLG_FILTERSPEC("INI Files", "*.ini"),
    COMDLG_FILTERSPEC("Log Files", "*.log"),
    COMDLG_FILTERSPEC("SVG Files", "*.svg"),
    COMDLG_FILTERSPEC("Markdown Files", "*.md"),
    COMDLG_FILTERSPEC("YAML Files", "*.yaml;*.yml"),
    COMDLG_FILTERSPEC("JSON Files", "*.json"),
    COMDLG_FILTERSPEC("PowerShell Files", "*.ps1"),
    COMDLG_FILTERSPEC("MATLAB Files", "*.m"),
    COMDLG_FILTERSPEC("R Files", "*.r"),
    COMDLG_FILTERSPEC("Lua Files", "*.lua"),
    COMDLG_FILTERSPEC("Rust Files", "*.rs"),
    COMDLG_FILTERSPEC("Go Files", "*.go"),
    COMDLG_FILTERSPEC("Swift Files", "*.swift"),
    COMDLG_FILTERSPEC("Kotlin Files", "*.kt;*.kts"),
    COMDLG_FILTERSPEC("Objective-C Files", "*.m;*.mm"),
    COMDLG_FILTERSPEC("SQL Files", "*.sql"),
    COMDLG_FILTERSPEC("Config Files", "*.conf"),
    COMDLG_FILTERSPEC("CSV Files", "*.csv"),
    COMDLG_FILTERSPEC("TSV Files", "*.tsv"),
    COMDLG_FILTERSPEC("LaTeX Files", "*.tex"),
    COMDLG_FILTERSPEC("BibTeX Files", "*.bib"),
    COMDLG_FILTERSPEC("Makefiles", "Makefile"),
    COMDLG_FILTERSPEC("Gradle Files", "*.gradle"),
    COMDLG_FILTERSPEC("Ant Build Files", "*.build.xml"),
    COMDLG_FILTERSPEC("Maven POM Files", "pom.xml"),
    COMDLG_FILTERSPEC("Dockerfiles", "Dockerfile"),
    COMDLG_FILTERSPEC("Vagrantfiles", "Vagrantfile"),
    COMDLG_FILTERSPEC("Terraform Files", "*.tf"),
    COMDLG_FILTERSPEC("HCL Files", "*.hcl"),
    COMDLG_FILTERSPEC("Kubernetes YAML Files", "*.yaml;*.yml"),
]


def configure_file_dialog(  # noqa: PLR0913, PLR0912, C901, PLR0915
    file_dialog: IFileOpenDialog | IFileSaveDialog,
    title: str | None = None,
    options: int = 0,
    default_folder: str | None = None,
    ok_button_label: str | None = None,
    file_name_label: str | None = None,
    file_types: list[tuple[str, str]] | None = None,
    default_extension: str | None = None,
    dialog_interfaces: list[comtypes.IUnknown | comtypes.COMObject] | None = None,
    hwnd: HWND | int | None = None,
) -> list[str] | None:  
    """
    Configure and display a Windows file dialog with comprehensive options.
    
    This is the workhorse function that takes a raw COM dialog object and
    transforms it into a fully configured, user-ready dialog. It handles
    all the intricate details of setting options, validating configurations,
    and processing results.
    
    The function performs several critical tasks:
    1. Applies all configuration options to the dialog
    2. Resolves conflicting settings automatically
    3. Sets up file type filters and validation
    4. Displays the dialog and processes user interaction
    5. Extracts and formats the results for Python consumption
    
    Option Conflict Resolution:
    The function automatically detects and resolves conflicting Windows options.
    For example, FOS_ALLNONSTORAGEITEMS conflicts with FOS_FORCEFILESYSTEM,
    so the function will automatically disable the conflicting option and
    provide debug output explaining the change.
    
    Args:
        file_dialog: Pre-created COM dialog object to configure
        title: Dialog window title
        options: Bitwise combination of FileOpenOptions flags
        default_folder: Initial directory to display
        ok_button_label: Custom text for the accept button
        file_name_label: Label for the file name input field
        file_types: List of (description, pattern) tuples for file filtering
        default_extension: Extension to auto-append when saving
        dialog_interfaces: Event handlers and custom interfaces to attach
        hwnd: Parent window handle (0 for no parent)
        
    Returns:
        list[str] | None: Selected file/folder paths, or None if cancelled
        
    Implementation Details:
        - Validates and resolves option conflicts automatically
        - Creates proper Windows shell items for default folders
        - Handles both open and save dialog result processing
        - Manages COM event handler registration/cleanup
        - Provides comprehensive debug output for troubleshooting
    """
    cookies: list[int] = []
    if dialog_interfaces:
        for interface in dialog_interfaces:
            cookie = file_dialog.Advise(interface)
            cookies.append(cookie)
    else:
        dialog_interfaces = []
    hwnd = HWND(hwnd) if isinstance(hwnd, int) else hwnd
    hwnd = HWND(0) if hwnd is None else hwnd
    try:
        if default_folder is not None:
            defaultFolder_path: WindowsPath = WindowsPath(default_folder).expanduser().resolve(strict=False)
            if not defaultFolder_path.exists() and defaultFolder_path.is_dir():
                raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), str(defaultFolder_path))
            shell_item = POINTER(IShellItem)()
            hr = windll.shell32.SHCreateItemFromParsingName(
                str(defaultFolder_path),
                None,
                IShellItem._iid_,
                byref(shell_item),
            )
            if hr == S_OK:
                with HandleCOMCall(f"SetFolder({defaultFolder_path})") as check:
                    check(file_dialog.SetFolder(shell_item))
                with HandleCOMCall(f"SetDefaultFolder({defaultFolder_path})") as check:
                    check(file_dialog.SetDefaultFolder(shell_item))

        # Resolve contradictory options
        if options & FileOpenOptions.FOS_ALLNONSTORAGEITEMS:
            if options & FileOpenOptions.FOS_FORCEFILESYSTEM:
                print("Removing FileOpenOptions.FOS_FORCEFILESYSTEM to prevent conflict with FOS_ALLNONSTORAGEITEMS")
                options &= ~FileOpenOptions.FOS_FORCEFILESYSTEM
            if options & FileOpenOptions.FOS_PICKFOLDERS:
                print("Removing FileOpenOptions.FOS_PICKFOLDERS to prevent conflict with FOS_ALLNONSTORAGEITEMS")
                options &= ~FileOpenOptions.FOS_PICKFOLDERS

        def get_flag_differences(set_options: int, get_options: int) -> list[str]:
            differences: int = set_options ^ get_options  # XOR to find differing bits
            differing_flags: list[str] = []
            for flag in FileOpenOptions:
                if differences & flag:
                    set_in_options = bool(set_options & flag)
                    set_in_cur_options = bool(get_options & flag)
                    differing_flags.append(f"{flag.name}: SetOptions={'SET' if set_in_options else 'UNSET'}, GetOptions={'SET' if set_in_cur_options else 'UNSET'}")
            return differing_flags

        original_dialog_options: int = file_dialog.GetOptions()
        print(f"Original dialog options: {original_dialog_options}")
        with HandleCOMCall(f"SetOptions({options})") as check:
            check(file_dialog.SetOptions(options))
        cur_options: int = file_dialog.GetOptions()
        print(f"GetOptions({cur_options})")

        assert original_dialog_options != cur_options, f"SetOptions call was completely ignored by the dialog interface, attempted to set {options}, " f"but retrieved {cur_options} (the original)"
        if options != cur_options:
            differing_flags: list[str] = get_flag_differences(options, cur_options)
            print(f"Differing flags: {', '.join(differing_flags)}")

        if not options & FileOpenOptions.FOS_PICKFOLDERS and file_types:
            print("Using custom file filters")
            filters = (COMDLG_FILTERSPEC * len(file_types))(*[(c_wchar_p(name), c_wchar_p(spec)) for name, spec in file_types])
            with HandleCOMCall(f"SetFileTypes({len(filters)})") as check:
                check(file_dialog.SetFileTypes(len(filters), cast_with_ctypes(filters, POINTER(c_void_p))))

        if title:
            file_dialog.SetTitle(title)

        if ok_button_label:
            file_dialog.SetOkButtonLabel(ok_button_label)
        elif isinstance(file_dialog, IFileSaveDialog):
            file_dialog.SetOkButtonLabel("Save")
        elif options & FileOpenOptions.FOS_PICKFOLDERS:
            file_dialog.SetOkButtonLabel("Select Folder")
        else:
            file_dialog.SetOkButtonLabel("Select File")

        if file_name_label:
            file_dialog.SetFileNameLabel(file_name_label)
        if default_extension:
            file_dialog.SetDefaultExtension(default_extension)

        if show_file_dialog(file_dialog, hwnd):
            control_event_handler: FileDialogControlEvents | None = next(
                (
                    interface
                    for interface in dialog_interfaces
                    if isinstance(interface, FileDialogControlEvents)
                ),
                None,
            )
            if control_event_handler and control_event_handler.selected_path:
                return [control_event_handler.selected_path]
            return (
                [get_save_file_dialog_results(file_dialog)]
                if isinstance(file_dialog, IFileSaveDialog)
                else get_open_file_dialog_results(file_dialog)
            )

    finally:
        for cookie in cookies:
            file_dialog.Unadvise(cookie)
    return None


def open_file_and_folder_dialog(  # noqa: C901, PLR0913, PLR0912
    title: str | None = "Open File",
    default_folder: str | None = None,
    default_extension: str | None = None,
    *,
    overwrite_prompt: bool = False,
    strict_file_types: bool = False,
    no_change_dir: bool = True,
    force_filesystem: bool = True,
    all_non_storage_items: bool = False,
    no_validate: bool = False,
    allow_multiple_selection: bool = False,
    path_must_exist: bool = True,
    file_must_exist: bool = True,
    create_prompt: bool = False,
    share_aware: bool = False,
    no_readonly_return: bool = False,
    no_test_file_create: bool = False,
    hide_mru_places: bool = False,
    hide_pinned_places: bool = False,
    no_dereference_links: bool = False,
    add_to_recent: bool = True,
    show_hidden_files: bool = False,
    default_no_minimode: bool = False,
    force_preview_pane_on: bool = False,
    ok_button_text: str | None = None,
) -> list[str] | None:  # sourcery skip: low-code-quality
    """Opens a file dialog to select files.

    Args:
        title (str | None): The title of the dialog.
        default_folder (str | None): The initial folder to open.
        default_extension (str | None): The default file extension.
        overwrite_prompt (bool): Prompts if the selected file already exists. FileOpenOptions.FOS_OVERWRITEPROMPT.
        strict_file_types (bool): Restricts selection to specified file types. FileOpenOptions.FOS_STRICTFILETYPES.
        no_change_dir (bool): Prevents changing the current working directory. FileOpenOptions.FOS_NOCHANGEDIR.
        force_filesystem (bool): Ensures only file system items are shown. FileOpenOptions.FOS_FORCEFILESYSTEM.
        all_non_storage_items (bool): Allows selection of non-file system items. FileOpenOptions.FOS_ALLNONSTORAGEITEMS.
        no_validate (bool): Disables file name validation. FileOpenOptions.FOS_NOVALIDATE.
        allow_multiple_selection (bool): Allows selecting multiple files. FileOpenOptions.FOS_ALLOWMULTISELECT.
        path_must_exist (bool): Requires the path to exist. FileOpenOptions.FOS_PATHMUSTEXIST.
        file_must_exist (bool): Requires the file to exist. FileOpenOptions.FOS_FILEMUSTEXIST.
        create_prompt (bool): Prompts to create a new file if it doesn't exist. FileOpenOptions.FOS_CREATEPROMPT.
        share_aware (bool): Ensures the dialog is aware of sharing conflicts. FileOpenOptions.FOS_SHAREAWARE.
        no_readonly_return (bool): Prevents selection of read-only items. FileOpenOptions.FOS_NOREADONLYRETURN.
        no_test_file_create (bool): Disables testing file creation ability. FileOpenOptions.FOS_NOTESTFILECREATE.
        hide_mru_places (bool): Hides most recently used places. FileOpenOptions.FOS_HIDEMRUPLACES.
        hide_pinned_places (bool): Hides pinned places. FileOpenOptions.FOS_HIDEPINNEDPLACES.
        no_dereference_links (bool): Prevents dereferencing shortcuts. FileOpenOptions.FOS_NODEREFERENCELINKS.
        add_to_recent (bool): Prevents adding the file to recent files. FileOpenOptions.FOS_DONTADDTORECENT.
        show_hidden_files (bool): Shows hidden files and folders. FileOpenOptions.FOS_FORCESHOWHIDDEN.
        default_no_minimode (bool): Uses default non-minimized mode. FileOpenOptions.FOS_DEFAULTNOMINIMODE.
        force_preview_pane_on (bool): Forces the preview pane to be visible. FileOpenOptions.FOS_FORCEPREVIEWPANEON.
        ok_button_text (str): The text for the button used to select/confirm the dialog.

    Returns:
        list[str] | None: A list of selected file paths or None if cancelled.
    """
    options = 0
    if overwrite_prompt:
        options |= FileOpenOptions.FOS_OVERWRITEPROMPT
    if strict_file_types:
        options |= FileOpenOptions.FOS_STRICTFILETYPES
    if no_change_dir:
        options |= FileOpenOptions.FOS_NOCHANGEDIR
    if force_filesystem:
        options |= FileOpenOptions.FOS_FORCEFILESYSTEM
    if all_non_storage_items:
        options |= FileOpenOptions.FOS_ALLNONSTORAGEITEMS
    if no_validate:
        options |= FileOpenOptions.FOS_NOVALIDATE
    if allow_multiple_selection:
        options |= FileOpenOptions.FOS_ALLOWMULTISELECT
    if path_must_exist:
        options |= FileOpenOptions.FOS_PATHMUSTEXIST
    if file_must_exist:
        options |= FileOpenOptions.FOS_FILEMUSTEXIST
    if create_prompt:
        options |= FileOpenOptions.FOS_CREATEPROMPT
    if share_aware:
        options |= FileOpenOptions.FOS_SHAREAWARE
    if no_readonly_return:
        options |= FileOpenOptions.FOS_NOREADONLYRETURN
    if no_test_file_create:
        options |= FileOpenOptions.FOS_NOTESTFILECREATE
    if hide_mru_places:
        options |= FileOpenOptions.FOS_HIDEMRUPLACES
    if hide_pinned_places:
        options |= FileOpenOptions.FOS_HIDEPINNEDPLACES
    if no_dereference_links:
        options |= FileOpenOptions.FOS_NODEREFERENCELINKS
    if not add_to_recent:
        options |= FileOpenOptions.FOS_DONTADDTORECENT
    if show_hidden_files:
        options |= FileOpenOptions.FOS_FORCESHOWHIDDEN
    if default_no_minimode:
        options |= FileOpenOptions.FOS_DEFAULTNOMINIMODE
    if force_preview_pane_on:
        options |= FileOpenOptions.FOS_FORCEPREVIEWPANEON
    file_dialog: IFileOpenDialog = comtypes.client.CreateObject(CLSID_FileOpenDialog, interface=IFileOpenDialog)
    customize_handler: IFileDialogCustomize = file_dialog.QueryInterface(IFileDialogCustomize, IID_IFileDialogCustomize)
    folder_button_id = 1001
    customize_handler.AddPushButton(folder_button_id, "Select Folder")
    control_event_handler = FileDialogControlEvents(file_dialog)
    return configure_file_dialog(file_dialog, title, options, default_folder, ok_button_text, None, None, default_extension, [control_event_handler])


def open_file_dialog(  # noqa: C901, PLR0913, PLR0912
    title: str | None = "Open File",
    default_folder: str | None = None,
    file_types: list[tuple[str, str]] | None = None,
    default_extension: str | None = None,
    *,
    overwrite_prompt: bool = False,
    strict_file_types: bool = False,
    no_change_dir: bool = True,
    force_filesystem: bool = True,
    all_non_storage_items: bool = False,
    no_validate: bool = False,
    allow_multiple_selection: bool = False,
    path_must_exist: bool = True,
    file_must_exist: bool = True,
    create_prompt: bool = False,
    share_aware: bool = False,
    no_readonly_return: bool = False,
    no_test_file_create: bool = False,
    hide_mru_places: bool = False,
    hide_pinned_places: bool = False,
    no_dereference_links: bool = False,
    add_to_recent: bool = True,
    show_hidden_files: bool = False,
    default_no_minimode: bool = False,
    force_preview_pane_on: bool = False,
    ok_button_text: str | None = None,
) -> list[str] | None:  # sourcery skip: low-code-quality
    """Opens a file dialog to select files.

    Args:
        title (str | None): The title of the dialog.
        default_folder (str | None): The initial folder to open.
        file_types (list[tuple[str, str]] | None): A list of file type filters.
        default_extension (str | None): The default file extension.
        overwrite_prompt (bool): Prompts if the selected file already exists. FileOpenOptions.FOS_OVERWRITEPROMPT.
        strict_file_types (bool): Restricts selection to specified file types. FileOpenOptions.FOS_STRICTFILETYPES.
        no_change_dir (bool): Prevents changing the current working directory. FileOpenOptions.FOS_NOCHANGEDIR.
        force_filesystem (bool): Ensures only file system items are shown. FileOpenOptions.FOS_FORCEFILESYSTEM.
        all_non_storage_items (bool): Allows selection of non-file system items. FileOpenOptions.FOS_ALLNONSTORAGEITEMS.
        no_validate (bool): Disables file name validation. FileOpenOptions.FOS_NOVALIDATE.
        allow_multiple_selection (bool): Allows selecting multiple files. FileOpenOptions.FOS_ALLOWMULTISELECT.
        path_must_exist (bool): Requires the path to exist. FileOpenOptions.FOS_PATHMUSTEXIST.
        file_must_exist (bool): Requires the file to exist. FileOpenOptions.FOS_FILEMUSTEXIST.
        create_prompt (bool): Prompts to create a new file if it doesn't exist. FileOpenOptions.FOS_CREATEPROMPT.
        share_aware (bool): Ensures the dialog is aware of sharing conflicts. FileOpenOptions.FOS_SHAREAWARE.
        no_readonly_return (bool): Prevents selection of read-only items. FileOpenOptions.FOS_NOREADONLYRETURN.
        no_test_file_create (bool): Disables testing file creation ability. FileOpenOptions.FOS_NOTESTFILECREATE.
        hide_mru_places (bool): Hides most recently used places. FileOpenOptions.FOS_HIDEMRUPLACES.
        hide_pinned_places (bool): Hides pinned places. FileOpenOptions.FOS_HIDEPINNEDPLACES.
        no_dereference_links (bool): Prevents dereferencing shortcuts. FileOpenOptions.FOS_NODEREFERENCELINKS.
        add_to_recent (bool): Prevents adding the file to recent files. FileOpenOptions.FOS_DONTADDTORECENT.
        show_hidden_files (bool): Shows hidden files and folders. FileOpenOptions.FOS_FORCESHOWHIDDEN.
        default_no_minimode (bool): Uses default non-minimized mode. FileOpenOptions.FOS_DEFAULTNOMINIMODE.
        force_preview_pane_on (bool): Forces the preview pane to be visible. FileOpenOptions.FOS_FORCEPREVIEWPANEON.
        ok_button_text (str): The text for the button used to select/confirm the dialog.

    Returns:
        list[str] | None: A list of selected file paths or None if cancelled.
    """
    options = 0
    if overwrite_prompt:
        options |= FileOpenOptions.FOS_OVERWRITEPROMPT
    if strict_file_types:
        options |= FileOpenOptions.FOS_STRICTFILETYPES
    if no_change_dir:
        options |= FileOpenOptions.FOS_NOCHANGEDIR
    if force_filesystem:
        options |= FileOpenOptions.FOS_FORCEFILESYSTEM
    if all_non_storage_items:
        options |= FileOpenOptions.FOS_ALLNONSTORAGEITEMS
    if no_validate:
        options |= FileOpenOptions.FOS_NOVALIDATE
    if allow_multiple_selection:
        options |= FileOpenOptions.FOS_ALLOWMULTISELECT
    if path_must_exist:
        options |= FileOpenOptions.FOS_PATHMUSTEXIST
    if file_must_exist:
        options |= FileOpenOptions.FOS_FILEMUSTEXIST
    if create_prompt:
        options |= FileOpenOptions.FOS_CREATEPROMPT
    if share_aware:
        options |= FileOpenOptions.FOS_SHAREAWARE
    if no_readonly_return:
        options |= FileOpenOptions.FOS_NOREADONLYRETURN
    if no_test_file_create:
        options |= FileOpenOptions.FOS_NOTESTFILECREATE
    if hide_mru_places:
        options |= FileOpenOptions.FOS_HIDEMRUPLACES
    if hide_pinned_places:
        options |= FileOpenOptions.FOS_HIDEPINNEDPLACES
    if no_dereference_links:
        options |= FileOpenOptions.FOS_NODEREFERENCELINKS
    if not add_to_recent:
        options |= FileOpenOptions.FOS_DONTADDTORECENT
    if show_hidden_files:
        options |= FileOpenOptions.FOS_FORCESHOWHIDDEN
    if default_no_minimode:
        options |= FileOpenOptions.FOS_DEFAULTNOMINIMODE
    if force_preview_pane_on:
        options |= FileOpenOptions.FOS_FORCEPREVIEWPANEON
    file_dialog: IFileOpenDialog = comtypes.client.CreateObject(CLSID_FileOpenDialog, interface=IFileOpenDialog)
    return configure_file_dialog(file_dialog, title, options, default_folder, ok_button_text, None, file_types, default_extension)


def save_file_dialog(  # noqa: C901, PLR0913, PLR0912
    title: str | None = "Save File",
    default_folder: str | None = None,
    file_types: list[tuple[str, str]] | None = None,
    default_extension: str | None = None,
    *,
    overwrite_prompt: bool = True,
    strict_file_types: bool = False,
    no_change_dir: bool = True,
    force_filesystem: bool = True,
    all_non_storage_items: bool = False,
    no_validate: bool = False,
    path_must_exist: bool = True,
    file_must_exist: bool = False,
    create_prompt: bool = False,
    share_aware: bool = False,
    no_readonly_return: bool = False,
    no_test_file_create: bool = False,
    hide_mru_places: bool = False,
    hide_pinned_places: bool = False,
    no_dereference_links: bool = False,
    add_to_recent: bool = True,
    show_hidden_files: bool = False,
    default_no_minimode: bool = False,
    force_preview_pane_on: bool = False,
    ok_button_text: str | None = None,
) -> list[str] | None:  # sourcery skip: low-code-quality
    """Opens a file dialog to save a file.

    Args:
        title (str | None): The title of the dialog.
        default_folder (str | None): The initial folder to open.
        file_types (list[tuple[str, str]] | None): A list of file type filters.
        default_extension (str | None): The default file extension.
        overwrite_prompt (bool): Prompts if the selected file already exists. FileOpenOptions.FOS_OVERWRITEPROMPT.
        strict_file_types (bool): Restricts selection to specified file types. FileOpenOptions.FOS_STRICTFILETYPES.
        no_change_dir (bool): Prevents changing the current working directory. FileOpenOptions.FOS_NOCHANGEDIR.
        force_filesystem (bool): Ensures only file system items are shown. FileOpenOptions.FOS_FORCEFILESYSTEM.
        all_non_storage_items (bool): Allows selection of non-file system items. FileOpenOptions.FOS_ALLNONSTORAGEITEMS.
        no_validate (bool): Disables file name validation. FileOpenOptions.FOS_NOVALIDATE.
        path_must_exist (bool): Requires the path to exist. FileOpenOptions.FOS_PATHMUSTEXIST.
        file_must_exist (bool): Requires the file to exist. FileOpenOptions.FOS_FILEMUSTEXIST.
        create_prompt (bool): Prompts to create a new file if it doesn't exist. FileOpenOptions.FOS_CREATEPROMPT.
        share_aware (bool): Ensures the dialog is aware of sharing conflicts. FileOpenOptions.FOS_SHAREAWARE.
        no_readonly_return (bool): Prevents selection of read-only items. FileOpenOptions.FOS_NOREADONLYRETURN.
        no_test_file_create (bool): Disables testing file creation ability. FileOpenOptions.FOS_NOTESTFILECREATE.
        hide_mru_places (bool): Hides most recently used places. FileOpenOptions.FOS_HIDEMRUPLACES.
        hide_pinned_places (bool): Hides pinned places. FileOpenOptions.FOS_HIDEPINNEDPLACES.
        no_dereference_links (bool): Prevents dereferencing shortcuts. FileOpenOptions.FOS_NODEREFERENCELINKS.
        add_to_recent (bool): Prevents adding the file to recent files. FileOpenOptions.FOS_DONTADDTORECENT.
        show_hidden_files (bool): Shows hidden files and folders. FileOpenOptions.FOS_FORCESHOWHIDDEN.
        default_no_minimode (bool): Uses default non-minimized mode. FileOpenOptions.FOS_DEFAULTNOMINIMODE.
        force_preview_pane_on (bool): Forces the preview pane to be visible. FileOpenOptions.FOS_FORCEPREVIEWPANEON.
        ok_button_text (str): The text for the button used to select/confirm the dialog.

    Returns:
        list[str] | None: A list of selected file paths or None if cancelled.
    """
    options = 0
    if overwrite_prompt:
        options |= FileOpenOptions.FOS_OVERWRITEPROMPT
    if strict_file_types:
        options |= FileOpenOptions.FOS_STRICTFILETYPES
    if no_change_dir:
        options |= FileOpenOptions.FOS_NOCHANGEDIR
    if force_filesystem:
        options |= FileOpenOptions.FOS_FORCEFILESYSTEM
    if all_non_storage_items:
        options |= FileOpenOptions.FOS_ALLNONSTORAGEITEMS
    if no_validate:
        options |= FileOpenOptions.FOS_NOVALIDATE
    if path_must_exist:
        options |= FileOpenOptions.FOS_PATHMUSTEXIST
    if file_must_exist:
        options |= FileOpenOptions.FOS_FILEMUSTEXIST
    if create_prompt:
        options |= FileOpenOptions.FOS_CREATEPROMPT
    if share_aware:
        options |= FileOpenOptions.FOS_SHAREAWARE
    if no_readonly_return:
        options |= FileOpenOptions.FOS_NOREADONLYRETURN
    if no_test_file_create:
        options |= FileOpenOptions.FOS_NOTESTFILECREATE
    if hide_mru_places:
        options |= FileOpenOptions.FOS_HIDEMRUPLACES
    if hide_pinned_places:
        options |= FileOpenOptions.FOS_HIDEPINNEDPLACES
    if no_dereference_links:
        options |= FileOpenOptions.FOS_NODEREFERENCELINKS
    if not add_to_recent:
        options |= FileOpenOptions.FOS_DONTADDTORECENT
    if show_hidden_files:
        options |= FileOpenOptions.FOS_FORCESHOWHIDDEN
    if default_no_minimode:
        options |= FileOpenOptions.FOS_DEFAULTNOMINIMODE
    if force_preview_pane_on:
        options |= FileOpenOptions.FOS_FORCEPREVIEWPANEON
    options &= ~FileOpenOptions.FOS_PICKFOLDERS  # Required (exceptions otherwise)
    options &= ~FileOpenOptions.FOS_ALLOWMULTISELECT  # Required (exceptions otherwise)
    file_dialog: IFileSaveDialog = comtypes.client.CreateObject(CLSID_FileSaveDialog, interface=IFileSaveDialog)
    return configure_file_dialog(file_dialog, title, options, default_folder, ok_button_text, None, file_types, default_extension)


def open_folder_dialog(  # noqa: C901, PLR0913, PLR0912
    title: str | None = "Select Folder",
    default_folder: str | None = None,
    *,
    overwrite_prompt: bool = False,
    strict_file_types: bool = False,
    no_change_dir: bool = False,
    force_filesystem: bool = True,
    no_validate: bool = False,
    allow_multiple_selection: bool = False,
    path_must_exist: bool = True,
    file_must_exist: bool = False,
    create_prompt: bool = False,
    share_aware: bool = False,
    no_readonly_return: bool = False,
    no_test_file_create: bool = False,
    hide_mru_places: bool = False,
    hide_pinned_places: bool = False,
    no_dereference_links: bool = False,
    add_to_recent: bool = True,
    show_hidden_files: bool = False,
    default_no_minimode: bool = False,
    force_preview_pane_on: bool = False,
    ok_button_text: str | None = None,
) -> list[str] | None:  # sourcery skip: low-code-quality
    """Opens a dialog to select folders.

    Args:
        title (str | None): The title of the dialog.
        default_folder (str | None): The initial folder to open.
        overwrite_prompt (bool): Prompts if the selected file already exists. FileOpenOptions.FOS_OVERWRITEPROMPT.
        strict_file_types (bool): Restricts selection to specified file types. FileOpenOptions.FOS_STRICTFILETYPES.
        no_change_dir (bool): Prevents changing the current working directory. FileOpenOptions.FOS_NOCHANGEDIR.
        force_filesystem (bool): Ensures only file system items are shown. FileOpenOptions.FOS_FORCEFILESYSTEM.
        no_validate (bool): Disables file name validation. FileOpenOptions.FOS_NOVALIDATE.
        allow_multiple_selection (bool): Allows selecting multiple files. FileOpenOptions.FOS_ALLOWMULTISELECT.
        path_must_exist (bool): Requires the path to exist. FileOpenOptions.FOS_PATHMUSTEXIST.
        file_must_exist (bool): Requires the file to exist. FileOpenOptions.FOS_FILEMUSTEXIST.
        create_prompt (bool): Prompts to create a new file if it doesn't exist. FileOpenOptions.FOS_CREATEPROMPT.
        share_aware (bool): Ensures the dialog is aware of sharing conflicts. FileOpenOptions.FOS_SHAREAWARE.
        no_readonly_return (bool): Prevents selection of read-only items. FileOpenOptions.FOS_NOREADONLYRETURN.
        no_test_file_create (bool): Disables testing file creation ability. FileOpenOptions.FOS_NOTESTFILECREATE.
        hide_mru_places (bool): Hides most recently used places. FileOpenOptions.FOS_HIDEMRUPLACES.
        hide_pinned_places (bool): Hides pinned places. FileOpenOptions.FOS_HIDEPINNEDPLACES.
        no_dereference_links (bool): Prevents dereferencing shortcuts. FileOpenOptions.FOS_NODEREFERENCELINKS.
        add_to_recent (bool): Prevents adding the file to recent files. FileOpenOptions.FOS_DONTADDTORECENT.
        show_hidden_files (bool): Shows hidden files and folders. FileOpenOptions.FOS_FORCESHOWHIDDEN.
        default_no_minimode (bool): Uses default non-minimized mode. FileOpenOptions.FOS_DEFAULTNOMINIMODE.
        force_preview_pane_on (bool): Forces the preview pane to be visible. FileOpenOptions.FOS_FORCEPREVIEWPANEON.
        ok_button_text (str): The text for the button used to select/confirm the dialog.

    Returns:
        list[str] | None: A list of selected folder paths or None if cancelled.
    """
    options = 0
    options |= FileOpenOptions.FOS_PICKFOLDERS
    options &= ~FileOpenOptions.FOS_ALLNONSTORAGEITEMS
    if overwrite_prompt:
        options |= FileOpenOptions.FOS_OVERWRITEPROMPT
    if strict_file_types:
        options |= FileOpenOptions.FOS_STRICTFILETYPES
    if no_change_dir:
        options |= FileOpenOptions.FOS_NOCHANGEDIR
    if force_filesystem:
        options |= FileOpenOptions.FOS_FORCEFILESYSTEM
    if no_validate:
        options |= FileOpenOptions.FOS_NOVALIDATE
    if allow_multiple_selection:
        options |= FileOpenOptions.FOS_ALLOWMULTISELECT
    if path_must_exist:
        options |= FileOpenOptions.FOS_PATHMUSTEXIST
    if file_must_exist:
        options |= FileOpenOptions.FOS_FILEMUSTEXIST
    if create_prompt:
        options |= FileOpenOptions.FOS_CREATEPROMPT
    if share_aware:
        options |= FileOpenOptions.FOS_SHAREAWARE
    if no_readonly_return:
        options |= FileOpenOptions.FOS_NOREADONLYRETURN
    if no_test_file_create:
        options |= FileOpenOptions.FOS_NOTESTFILECREATE
    if hide_mru_places:
        options |= FileOpenOptions.FOS_HIDEMRUPLACES
    if hide_pinned_places:
        options |= FileOpenOptions.FOS_HIDEPINNEDPLACES
    if no_dereference_links:
        options |= FileOpenOptions.FOS_NODEREFERENCELINKS
    if not add_to_recent:
        options |= FileOpenOptions.FOS_DONTADDTORECENT
    if show_hidden_files:
        options |= FileOpenOptions.FOS_FORCESHOWHIDDEN
    if default_no_minimode:
        options |= FileOpenOptions.FOS_DEFAULTNOMINIMODE
    if force_preview_pane_on:
        options |= FileOpenOptions.FOS_FORCEPREVIEWPANEON
    file_dialog: IFileOpenDialog = comtypes.client.CreateObject(CLSID_FileOpenDialog, interface=IFileOpenDialog)
    return configure_file_dialog(file_dialog, title, options, default_folder, ok_button_text, None, None, None)


def get_open_file_dialog_results(
    file_open_dialog: IFileOpenDialog,
) -> list[str]:
    results: list[str] = []
    results_array: IShellItemArray = file_open_dialog.GetResults()
    itemCount: int = results_array.GetCount()

    for i in range(itemCount):
        shell_item: IShellItem = results_array.GetItemAt(i)
        szFilePath: str = shell_item.GetDisplayName(SIGDN.SIGDN_FILESYSPATH)
        if szFilePath and szFilePath.strip():
            results.append(szFilePath)
            print(f"Item {i} file path: {szFilePath}")
        else:
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), szFilePath)
    return results


def get_save_file_dialog_results(fileSaveDialog: IFileSaveDialog) -> str:  # noqa: N803
    results = ""
    resultItem: IShellItem = fileSaveDialog.GetResult()

    szFilePath = resultItem.GetDisplayName(SIGDN.SIGDN_FILESYSPATH)
    szFilePathStr = str(szFilePath)
    if szFilePathStr and szFilePathStr.strip():
        results = szFilePathStr
        print(f"Selected file path: {szFilePath}")
    else:
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), str(szFilePath))

    attributes: int | c_ulong = resultItem.GetAttributes(SFGAO.SFGAO_FILESYSTEM | SFGAO.SFGAO_FOLDER)
    print(f"Selected item attributes: {attributes}")

    parentItem: IShellItem | comtypes.IUnknown = resultItem.GetParent()
    if isinstance(parentItem, IShellItem):
        szParentName: LPWSTR | str = parentItem.GetDisplayName(SIGDN.SIGDN_NORMALDISPLAY)
        print(f"Selected item parent: {szParentName}")

    return results


# Example usage
if __name__ == "__main__":
    # Randomizing arguments for open_file_dialog
    open_file_args = {
        "title": "Open File" if random.choice([True, False]) else None,  # noqa: S311
        "default_folder": "C:\\Users" if random.choice([True, False]) else None,  # noqa: S311
        "default_extension": "txt" if random.choice([True, False]) else None,  # noqa: S311
        "overwrite_prompt": random.choice([True, False]),  # noqa: S311
        "strict_file_types": random.choice([True, False]),  # noqa: S311
        "no_change_dir": random.choice([True, False]),  # noqa: S311
        "force_filesystem": random.choice([True, False]),  # noqa: S311
        "all_non_storage_items": False,  # random.choice([True, False]),  # noqa: S311
        "no_validate": random.choice([True, False]),  # noqa: S311
        "allow_multiple_selection": random.choice([True, False]),  # noqa: S311
        "path_must_exist": random.choice([True, False]),  # noqa: S311
        "file_must_exist": random.choice([True, False]),  # noqa: S311
        "create_prompt": random.choice([True, False]),  # noqa: S311
        "share_aware": random.choice([True, False]),  # noqa: S311
        "no_readonly_return": random.choice([True, False]),  # noqa: S311
        "no_test_file_create": random.choice([True, False]),  # noqa: S311
        "hide_mru_places": random.choice([True, False]),  # noqa: S311
        "hide_pinned_places": random.choice([True, False]),  # noqa: S311
        "no_dereference_links": random.choice([True, False]),  # noqa: S311
        "add_to_recent": random.choice([True, False]),  # noqa: S311
        "show_hidden_files": random.choice([True, False]),  # noqa: S311
        "default_no_minimode": random.choice([True, False]),  # noqa: S311
        "force_preview_pane_on": random.choice([True, False]),  # noqa: S311
    }
    print("\nOpen file args")
    print(json.dumps(open_file_args, indent=4, sort_keys=True))
    selected_files: list[str] | None = open_file_and_folder_dialog(**open_file_args)
    print("Selected files:", selected_files)

    # Randomizing arguments for open_folder_dialog
    open_folder_args = {
        "title": "Select Folder" if random.choice([True, False]) else None,  # noqa: S311
        "default_folder": "C:\\Users" if random.choice([True, False]) else None,  # noqa: S311
        "overwrite_prompt": random.choice([True, False]),  # noqa: S311
        "strict_file_types": random.choice([True, False]),  # noqa: S311
        "no_change_dir": random.choice([True, False]),  # noqa: S311
        "force_filesystem": random.choice([True, False]),  # noqa: S311
        "no_validate": random.choice([True, False]),  # noqa: S311
        "allow_multiple_selection": random.choice([True, False]),  # noqa: S311
        "path_must_exist": random.choice([True, False]),  # noqa: S311
        "file_must_exist": random.choice([True, False]),  # noqa: S311
        "create_prompt": random.choice([True, False]),  # noqa: S311
        "share_aware": random.choice([True, False]),  # noqa: S311
        "no_readonly_return": random.choice([True, False]),  # noqa: S311
        "no_test_file_create": random.choice([True, False]),  # noqa: S311
        "hide_mru_places": random.choice([True, False]),  # noqa: S311
        "hide_pinned_places": random.choice([True, False]),  # noqa: S311
        "no_dereference_links": random.choice([True, False]),  # noqa: S311
        "add_to_recent": random.choice([True, False]),  # noqa: S311
        "show_hidden_files": random.choice([True, False]),  # noqa: S311
        "default_no_minimode": random.choice([True, False]),  # noqa: S311
        "force_preview_pane_on": random.choice([True, False]),  # noqa: S311
    }
    print("\nOpen folder args")
    print(json.dumps(open_folder_args, indent=4, sort_keys=True))
    selected_folders: list[str] | None = open_folder_dialog(**open_folder_args)
    print("Selected folders:", selected_folders)

    # Randomizing arguments for save_file_dialog
    save_file_args = {
        "title": "Save File" if random.choice([True, False]) else None,  # noqa: S311
        "default_folder": "C:\\Users" if random.choice([True, False]) else None,  # noqa: S311
        "file_types": [("Text Files", "*.txt")] if random.choice([True, False]) else None,  # noqa: S311
        "default_extension": "txt" if random.choice([True, False]) else None,  # noqa: S311
        "overwrite_prompt": random.choice([True, False]),  # noqa: S311
        "strict_file_types": random.choice([True, False]),  # noqa: S311
        "no_change_dir": random.choice([True, False]),  # noqa: S311
        "force_filesystem": random.choice([True, False]),  # noqa: S311
        "all_non_storage_items": random.choice([True, False]),  # noqa: S311
        "no_validate": random.choice([True, False]),  # noqa: S311
        "path_must_exist": random.choice([True, False]),  # noqa: S311
        "file_must_exist": random.choice([True, False]),  # noqa: S311
        "create_prompt": random.choice([True, False]),  # noqa: S311
        "share_aware": random.choice([True, False]),  # noqa: S311
        "no_readonly_return": random.choice([True, False]),  # noqa: S311
        "no_test_file_create": random.choice([True, False]),  # noqa: S311
        "hide_mru_places": random.choice([True, False]),  # noqa: S311
        "hide_pinned_places": random.choice([True, False]),  # noqa: S311
        "no_dereference_links": random.choice([True, False]),  # noqa: S311
        "add_to_recent": random.choice([True, False]),  # noqa: S311
        "show_hidden_files": random.choice([True, False]),  # noqa: S311
        "default_no_minimode": random.choice([True, False]),  # noqa: S311
        "force_preview_pane_on": random.choice([True, False]),  # noqa: S311
    }
    print("\nSave file args")
    print(json.dumps(save_file_args, indent=4, sort_keys=True))
    saved_file: list[str] | None = save_file_dialog(**save_file_args)
    print("Saved file:", saved_file)
