"""
PyIFileDialog - COM Foundation & IUnknown Base Interface

This module provides the fundamental building blocks for all COM (Component Object
Model) interactions in Windows. Every COM object inherits from IUnknown, making
this the bedrock of the entire system.

IUnknown is COM's base interface that provides three essential capabilities:
1. QueryInterface: Ask an object "do you support interface X?"
2. AddRef: Increment the object's reference count (keep it alive)
3. Release: Decrement reference count (allow cleanup when no longer needed)

This reference counting system ensures proper memory management - objects stay
alive as long as someone needs them, and automatically clean up when forgotten.

Key Components:
- IUnknown: The base COM interface with reference counting
- COMBase: Base structure for COM objects
- Various Windows type definitions (HWND, LPWSTR, etc.)
- Helper functions for reference counting operations

Think of this as the foundation that makes all other COM functionality possible.
Without proper IUnknown implementation, COM objects would leak memory or crash.
"""
from __future__ import annotations

from ctypes import (
    POINTER,
    WINFUNCTYPE,
    Structure,
    byref,
    c_int,
    c_uint,
    c_void_p,
    c_wchar_p,
    windll,
    wintypes,
)
from typing import TYPE_CHECKING, Any, Sequence

from com_types import GUID
from hresult import HRESULT

if TYPE_CHECKING:
    from ctypes import _CData, _FuncPointer, _Pointer

REFIID: type[_Pointer[GUID]] = POINTER(GUID)
REFGUID: type[_Pointer[GUID]] = POINTER(GUID)

# Define ULONG and LONG
ULONG = wintypes.DWORD
LONG = wintypes.LONG

# Define basic Windows types
LPVOID = c_void_p
HWND = c_void_p
LPWSTR = c_wchar_p
LPCWSTR = c_wchar_p
UINT = c_uint
BOOL = c_int
DWORD = wintypes.DWORD
HMODULE = c_void_p

# Define HRESULT values
S_OK = HRESULT(0)
E_NOINTERFACE = HRESULT(0x80004002)

# Define CLSCTX_INPROC_SERVER
CLSCTX_INPROC_SERVER = 0x1


# Define SUCCEEDED and FAILED macros
def SUCCEEDED(hr):
    return hr >= 0


def FAILED(hr):
    return hr < 0



# Define InterlockedIncrement manually
def InterlockedIncrement(var_ptr):
    windll.kernel32.EnterCriticalSection(byref(var_ptr))
    var_ptr.contents.value += 1
    result = var_ptr.contents.value
    windll.kernel32.LeaveCriticalSection(byref(var_ptr))
    return result

# Define InterlockedDecrement manually
def InterlockedDecrement(var_ptr):
    windll.kernel32.EnterCriticalSection(byref(var_ptr))
    var_ptr.contents.value -= 1
    result = var_ptr.contents.value
    windll.kernel32.LeaveCriticalSection(byref(var_ptr))
    return result





class COMBase(Structure):
    def __init_subclass__(cls: type[COMBase], **kwargs):
        super().__init_subclass__(**kwargs)

    def query_interface(self, interface_id: GUID):
        assert isinstance(self, IUnknown)
        p_interface = POINTER(self.__class__)()
        hr = self.call("QueryInterface", byref(interface_id), byref(p_interface))
        if hr != 0:
            raise HRESULT(hr).exception("QueryInterface call failed!")
        return p_interface

    def call(self, method_name: str, *args):
        func_type: Sequence[type] | None = None
        for name, types in self._methods_:
            if name == method_name:
                func_type = types
                break
        else:
            raise AttributeError(f"Method '{method_name}' not found in class {self.__class__.__name__}")

        new_cfunctype: type[_FuncPointer] = WINFUNCTYPE(func_type[0], *([POINTER(type(self)), *func_type[1:]]))
        func_ptr: _FuncPointer = getattr(self.lpVtbl.contents, method_name)
        new_func_ptr: _FuncPointer = new_cfunctype(func_ptr)

        return new_func_ptr(self, *args)

    def add_ref(self):
        return self.call("AddRef")

    def release(self):
        return self.call("Release")

# Define IUnknown interface
IID_IUnknown = GUID("{00000000-0000-0000-C000-000000000046}")  # GUID(0x00000000, 0x0000, 0x0000, (0xC0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46))
class IUnknown(COMBase):  # Forward reference of the interface.
    _methods_: dict[str, Any]
    _iid_: GUID = IID_IUnknown
    lpVtbl: _Pointer[IUnknownVTable]
class IUnknownVTable(Structure):
    _fields_: Sequence[tuple[str, type[_CData]] | tuple[str, type[_CData], int]] = [
        ("QueryInterface", WINFUNCTYPE(HRESULT, LPVOID, POINTER(GUID), POINTER(LPVOID))),
        ("AddRef", WINFUNCTYPE(ULONG, POINTER(IUnknown))),
        ("Release", WINFUNCTYPE(ULONG, POINTER(IUnknown))),
    ]
IUnknown._fields_ =  [("lpVtbl", POINTER(IUnknownVTable))]

LPUNKNOWN: type[_Pointer[IUnknown]] = POINTER(IUnknown)
