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
from constants import COMDLG_FILTERSPEC, SIGDN, FileOpenOptions
from hresult import S_OK
from interfaces import (
    CLSID_FileOpenDialog,
    CLSID_FileSaveDialog,
    IFileDialogControlEvents,
    IFileDialogCustomize,
    IFileOpenDialog,
    IFileSaveDialog,
    IID_IFileDialogCustomize,
    IShellItem,
)

if TYPE_CHECKING:
    from _ctypes import _Pointer
    from ctypes import Array
    from ctypes.wintypes import BOOL, DWORD

    from hresult import HRESULT
    from interfaces import IFileDialog, IShellItemArray


class BaseFileDialog:
    def __init__(self, clsid: str, interface: type[IFileDialog]) -> None:
        self.file_dialog: IFileDialog = comtypes.client.CreateObject(clsid, interface=interface)
        self.options: int = 0
        self.dialog_interfaces: list[tuple[comtypes.COMObject, int]] = []

    def _set_options(self, options: int) -> None:
        self.options |= options

    def add_event_handler(self, event_handler: comtypes.COMObject) -> None:
        cookie: int = self.file_dialog.Advise(event_handler)
        self.dialog_interfaces.append((event_handler, cookie))

    def configure(
        self,
        *,
        overwrite_prompt: bool = False,
        strict_file_types: bool = False,
        no_change_dir: bool = False,
        force_filesystem: bool = False,
        all_non_storage_items: bool = False,
        no_validate: bool = False,
        allow_multiple_selection: bool = False,
        path_must_exist: bool = False,
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
    ) -> None:
        if overwrite_prompt:
            self._set_options(FileOpenOptions.FOS_OVERWRITEPROMPT)
        if strict_file_types:
            self._set_options(FileOpenOptions.FOS_STRICTFILETYPES)
        if no_change_dir:
            self._set_options(FileOpenOptions.FOS_NOCHANGEDIR)
        if force_filesystem:
            self._set_options(FileOpenOptions.FOS_FORCEFILESYSTEM)
        if all_non_storage_items:
            self._set_options(FileOpenOptions.FOS_ALLNONSTORAGEITEMS)
        if no_validate:
            self._set_options(FileOpenOptions.FOS_NOVALIDATE)
        if allow_multiple_selection:
            self._set_options(FileOpenOptions.FOS_ALLOWMULTISELECT)
        if path_must_exist:
            self._set_options(FileOpenOptions.FOS_PATHMUSTEXIST)
        if file_must_exist:
            self._set_options(FileOpenOptions.FOS_FILEMUSTEXIST)
        if create_prompt:
            self._set_options(FileOpenOptions.FOS_CREATEPROMPT)
        if share_aware:
            self._set_options(FileOpenOptions.FOS_SHAREAWARE)
        if no_readonly_return:
            self._set_options(FileOpenOptions.FOS_NOREADONLYRETURN)
        if no_test_file_create:
            self._set_options(FileOpenOptions.FOS_NOTESTFILECREATE)
        if hide_mru_places:
            self._set_options(FileOpenOptions.FOS_HIDEMRUPLACES)
        if hide_pinned_places:
            self._set_options(FileOpenOptions.FOS_HIDEPINNEDPLACES)
        if no_dereference_links:
            self._set_options(FileOpenOptions.FOS_NODEREFERENCELINKS)
        if not add_to_recent:
            self._set_options(FileOpenOptions.FOS_DONTADDTORECENT)
        if show_hidden_files:
            self._set_options(FileOpenOptions.FOS_FORCESHOWHIDDEN)
        if default_no_minimode:
            self._set_options(FileOpenOptions.FOS_DEFAULTNOMINIMODE)
        if force_preview_pane_on:
            self._set_options(FileOpenOptions.FOS_FORCEPREVIEWPANEON)

        hr: HRESULT = self.file_dialog.SetOptions(self.options)
        if hr != S_OK:
            raise OSError(hr, "Failed to set options on the dialog")

    def set_folder(self, default_folder: os.PathLike | str) -> None:
        default_folder_path: WindowsPath = WindowsPath(default_folder).expanduser().resolve(strict=False)
        if not default_folder_path.exists() or not default_folder_path.is_dir():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), str(default_folder_path))
        shell_item: _Pointer[IShellItem] = POINTER(IShellItem)()
        hr: HRESULT = windll.shell32.SHCreateItemFromParsingName(
            str(default_folder_path),
            None,
            IShellItem._iid_,
            byref(shell_item),
        )
        if hr != S_OK:
            raise OSError(hr, f"Failed to create shell item from path: {default_folder_path}")
        hr = self.file_dialog.SetFolder(shell_item)
        if hr != S_OK:
            raise OSError(hr, f"Failed to set folder: {default_folder_path}")
        hr = self.file_dialog.SetDefaultFolder(shell_item)
        if hr != S_OK:
            raise OSError(hr, f"Failed to set default folder: {default_folder_path}")

    def set_title(self, title: str) -> None:
        hr: HRESULT = self.file_dialog.SetTitle(title)
        if hr != S_OK:
            raise OSError(hr, f"Failed to set title: {title}")

    def set_ok_button_label(self, ok_button_text: str | None) -> None:
        if ok_button_text:
            hr: HRESULT = self.file_dialog.SetOkButtonLabel(ok_button_text)
            if hr != S_OK:
                raise OSError(hr, f"Failed to set OK button label: {ok_button_text}")
        if isinstance(self.file_dialog, IFileSaveDialog):
            hr = self.file_dialog.SetOkButtonLabel("Save")
            if hr != S_OK:
                raise OSError(hr, "Failed to set OK button label to 'Save'")
        if self.options & FileOpenOptions.FOS_PICKFOLDERS:
            hr = self.file_dialog.SetOkButtonLabel("Select Folder")
            if hr != S_OK:
                raise OSError(hr, "Failed to set OK button label to 'Select Folder'")
        hr = self.file_dialog.SetOkButtonLabel("Select File")
        if hr != S_OK:
            raise OSError(hr, "Failed to set OK button label to 'Select File'")

    def set_file_types(self, file_types: list[tuple[str, str]]) -> None:
        filters: Array[COMDLG_FILTERSPEC] = (COMDLG_FILTERSPEC * len(file_types))(
            *[(c_wchar_p(name), c_wchar_p(spec)) for name, spec in file_types]
        )
        hr: HRESULT = self.file_dialog.SetFileTypes(len(filters), filters)
        if hr != S_OK:
            raise OSError(hr, "Failed to set file types")

    def set_default_extension(self, default_extension: str) -> None:
        hr: HRESULT = self.file_dialog.SetDefaultExtension(default_extension)
        if hr != S_OK:
            raise OSError(hr, f"Failed to set default extension: {default_extension}")

    def show(self, hwnd: HWND) -> bool:
        hr: HRESULT = self.file_dialog.Show(hwnd)
        if hr != S_OK:
            raise OSError(hr, "Failed to show dialog")
        return True

    def unadvise(self) -> None:
        for _interface, cookie in self.dialog_interfaces:
            self.file_dialog.Unadvise(cookie)
        self.dialog_interfaces.clear()


def get_open_file_dialog_results(file_open_dialog: IFileOpenDialog) -> list[str]:
    results: list[str] = []
    results_array: IShellItemArray = file_open_dialog.GetResults()
    itemCount: int = results_array.GetCount()

    for i in range(itemCount):
        shell_item: IShellItem = results_array.GetItemAt(i)
        szFilePath: str = shell_item.GetDisplayName(SIGDN.SIGDN_FILESYSPATH)
        if szFilePath and szFilePath.strip():
            results.append(szFilePath)
        else:
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), szFilePath)
    return results


def get_save_file_dialog_results(file_save_dialog: IFileSaveDialog) -> str:
    resultItem: IShellItem = file_save_dialog.GetResult()
    szFilePath = resultItem.GetDisplayName(SIGDN.SIGDN_FILESYSPATH)
    if szFilePath and szFilePath.strip():
        return str(szFilePath)
    raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), str(szFilePath))


### Event Handlers

class FileDialogControlEvents(comtypes.COMObject):
    _com_interfaces_: Sequence[type[comtypes.IUnknown]] = [IFileDialogControlEvents]

    def __init__(self, file_dialog: IFileDialog):
        self._file_dialog: IFileDialog = file_dialog
        self.selected_path: str | None = None
        super().__init__()

    def OnItemSelected(self, pfdc: IFileDialogCustomize, dwIDCtl: DWORD, dwIDItem: DWORD) -> HRESULT:  # noqa: N803
        return S_OK

    def OnButtonClicked(self, pfdc: IFileDialogCustomize, dwIDCtl: DWORD) -> HRESULT:  # noqa: N803
        if dwIDCtl == 1001:
            print("Button with ID 1001 ('Select Folder') was clicked.")
            self.selected_path = self.get_selected_folder()
            if self.selected_path:
                print(f"Stored selected folder: {self.selected_path}")
                self._file_dialog.Close(S_OK)
        return S_OK

    def get_selected_folder(self) -> str | None:
        selected_item: IShellItem = self._file_dialog.GetCurrentSelection()
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
        return S_OK

    def OnControlActivating(self, pfdc: IFileDialogCustomize, dwIDCtl: DWORD) -> HRESULT:  # noqa: N803
        return S_OK


### Specific Dialog Classes

class OpenFileDialog(BaseFileDialog):
    def __init__(self, event_handlers=None):
        super().__init__(CLSID_FileOpenDialog, IFileOpenDialog)
        if event_handlers:
            for handler in event_handlers:
                self.add_event_handler(handler)
        self._set_options(FileOpenOptions.FOS_FORCEFILESYSTEM | FileOpenOptions.FOS_PATHMUSTEXIST)

    def configure(self, title="Open File", **kwargs):
        super().configure(title, **kwargs)


class SaveFileDialog(BaseFileDialog):
    def __init__(self, event_handlers=None):
        super().__init__(CLSID_FileSaveDialog, IFileSaveDialog)
        if event_handlers:
            for handler in event_handlers:
                self.add_event_handler(handler)
        self._set_options(FileOpenOptions.FOS_OVERWRITEPROMPT)

    def configure(self, title="Save File", **kwargs):
        super().configure(title, **kwargs)


class OpenFolderDialog(OpenFileDialog):
    def __init__(self, event_handlers=None):
        super().__init__(event_handlers)
        self._set_options(FileOpenOptions.FOS_PICKFOLDERS)


### Utility Functions

def configure_file_dialog(
    file_dialog: IFileDialog,
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
            default_folder_path: WindowsPath = WindowsPath(default_folder).expanduser().resolve(strict=False)
            if not default_folder_path.exists() or not default_folder_path.is_dir():
                raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), str(default_folder_path))
            shell_item = POINTER(IShellItem)()
            hr = windll.shell32.SHCreateItemFromParsingName(
                str(default_folder_path),
                None,
                IShellItem._iid_,
                byref(shell_item),
            )
            if hr == S_OK:
                with HandleCOMCall(f"SetFolder({default_folder_path})") as check:
                    check(file_dialog.SetFolder(shell_item))
                with HandleCOMCall(f"SetDefaultFolder({default_folder_path})") as check:
                    check(file_dialog.SetDefaultFolder(shell_item))

        original_dialog_options: int = file_dialog.GetOptions()
        with HandleCOMCall(f"SetOptions({options})") as check:
            check(file_dialog.SetOptions(options))
        cur_options: int = file_dialog.GetOptions()

        assert original_dialog_options != cur_options, (
            f"SetOptions call was completely ignored by the dialog interface, attempted to set {options}, "
            f"but retrieved {cur_options} (the original)"
        )

        if file_types:
            filters = (COMDLG_FILTERSPEC * len(file_types))(
                *[
                    (c_wchar_p(name), c_wchar_p(spec))
                    for name, spec in file_types
                ]
            )
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

        if file_dialog.Show(hwnd) == S_OK:
            control_event_handler = next(
                (interface for interface in dialog_interfaces if isinstance(interface, FileDialogControlEvents)),
                None
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


def open_file_and_folder_dialog(**kwargs) -> list[str] | None:
    folder_button_id = 1001
    control_event_handler = FileDialogControlEvents(None)  # To be replaced after dialog creation
    dialog = OpenFileDialog(event_handlers=[control_event_handler])
    dialog.configure(**kwargs)

    customize_handler = dialog.file_dialog.QueryInterface(IFileDialogCustomize, IID_IFileDialogCustomize)
    customize_handler.AddPushButton(folder_button_id, "Select Folder")
    control_event_handler._file_dialog = dialog.file_dialog

    try:
        if dialog.show(kwargs.get("hwnd", 0)):
            if control_event_handler.selected_path:
                return [control_event_handler.selected_path]
            return get_open_file_dialog_results(dialog.file_dialog)
    finally:
        dialog.unadvise()

    return None


def open_folder_dialog(**kwargs) -> list[str] | None:
    dialog = OpenFolderDialog()
    dialog.configure(**kwargs)

    try:
        if dialog.show(kwargs.get("hwnd", 0)):
            return get_open_file_dialog_results(dialog.file_dialog)
    finally:
        dialog.unadvise()

    return None


def save_file_dialog(**kwargs) -> str | None:
    dialog = SaveFileDialog()
    dialog.configure(**kwargs)

    try:
        if dialog.show(kwargs.get("hwnd", 0)):
            return get_save_file_dialog_results(dialog.file_dialog)
    finally:
        dialog.unadvise()

    return None


### Main Block Implementation

if __name__ == "__main__":
    open_file_args = {
        "title": "Open File" if random.choice([True, False]) else None,
        "default_folder": "C:\\Users" if random.choice([True, False]) else None,
        "default_extension": "txt" if random.choice([True, False]) else None,
        "overwrite_prompt": random.choice([True, False]),
        "strict_file_types": random.choice([True, False]),
        "no_change_dir": random.choice([True, False]),
        "force_filesystem": random.choice([True, False]),
        "all_non_storage_items": False,
        "no_validate": random.choice([True, False]),
        "allow_multiple_selection": random.choice([True, False]),
        "path_must_exist": random.choice([True, False]),
        "file_must_exist": random.choice([True, False]),
        "create_prompt": random.choice([True, False]),
        "share_aware": random.choice([True, False]),
        "no_readonly_return": random.choice([True, False]),
        "no_test_file_create": random.choice([True, False]),
        "hide_mru_places": random.choice([True, False]),
        "hide_pinned_places": random.choice([True, False]),
        "no_dereference_links": random.choice([True, False]),
        "add_to_recent": random.choice([True, False]),
        "show_hidden_files": random.choice([True, False]),
        "default_no_minimode": random.choice([True, False]),
        "force_preview_pane_on": random.choice([True, False]),
    }
    print("\nOpen file args")
    print(json.dumps(open_file_args, indent=4, sort_keys=True))
    selected_files = open_file_and_folder_dialog(**open_file_args)
    print("Selected files:", selected_files)

    open_folder_args = {
        "title": "Select Folder" if random.choice([True, False]) else None,
        "default_folder": "C:\\Users" if random.choice([True, False]) else None,
        "overwrite_prompt": random.choice([True, False]),
        "strict_file_types": random.choice([True, False]),
        "no_change_dir": random.choice([True, False]),
        "force_filesystem": random.choice([True, False]),
        "no_validate": random.choice([True, False]),
        "allow_multiple_selection": random.choice([True, False]),
        "path_must_exist": random.choice([True, False]),
        "file_must_exist": random.choice([True, False]),
        "create_prompt": random.choice([True, False]),
        "share_aware": random.choice([True, False]),
        "no_readonly_return": random.choice([True, False]),
        "no_test_file_create": random.choice([True, False]),
        "hide_mru_places": random.choice([True, False]),
        "hide_pinned_places": random.choice([True, False]),
        "no_dereference_links": random.choice([True, False]),
        "add_to_recent": random.choice([True, False]),
        "show_hidden_files": random.choice([True, False]),
        "default_no_minimode": random.choice([True, False]),
        "force_preview_pane_on": random.choice([True, False]),
    }
    print("\nOpen folder args")
    print(json.dumps(open_folder_args, indent=4, sort_keys=True))
    selected_folders = open_folder_dialog(**open_folder_args)
    print("Selected folders:", selected_folders)

    save_file_args = {
        "title": "Save File" if random.choice([True, False]) else None,
        "default_folder": "C:\\Users" if random.choice([True, False]) else None,
        "file_types": [("Text Files", "*.txt")] if random.choice([True, False]) else None,
        "default_extension": "txt" if random.choice([True, False]) else None,
        "overwrite_prompt": random.choice([True, False]),
        "strict_file_types": random.choice([True, False]),
        "no_change_dir": random.choice([True, False]),
        "force_filesystem": random.choice([True, False]),
        "all_non_storage_items": random.choice([True, False]),
        "no_validate": random.choice([True, False]),
        "path_must_exist": random.choice([True, False]),
        "file_must_exist": random.choice([True, False]),
        "create_prompt": random.choice([True, False]),
        "share_aware": random.choice([True, False]),
        "no_readonly_return": random.choice([True, False]),
        "no_test_file_create": random.choice([True, False]),
        "hide_mru_places": random.choice([True, False]),
        "hide_pinned_places": random.choice([True, False]),
        "no_dereference_links": random.choice([True, False]),
        "add_to_recent": random.choice([True, False]),
        "show_hidden_files": random.choice([True, False]),
        "default_no_minimode": random.choice([True, False]),
        "force_preview_pane_on": random.choice([True, False]),
    }
    print("\nSave file args")
    print(json.dumps(save_file_args, indent=4, sort_keys=True))
    saved_file = save_file_dialog(**save_file_args)
    print("Saved file:", saved_file)
