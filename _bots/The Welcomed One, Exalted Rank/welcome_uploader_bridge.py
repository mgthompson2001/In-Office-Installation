# welcome_uploader_bridge.py
# Bridge to open the Welcome Packet Uploader inside your existing V14 Tkinter GUI.
# Drop this file in the SAME folder as your V14 bot script AND
# isws_welcome_packet_uploader_v14style_FIXED.py

from __future__ import annotations
import importlib, os, sys, traceback
import tkinter as tk
from tkinter import ttk, messagebox

UPLOADER_MODULE = "isws_welcome_packet_uploader_v14style_FIXED"

def _import_uploader():
    try:
        return importlib.import_module(UPLOADER_MODULE)
    except Exception as e:
        messagebox.showerror("Uploader not found",
            f"Could not import '{UPLOADER_MODULE}'.\n"
            "Make sure isws_welcome_packet_uploader_v14style_FIXED.py\n"
            "is in the same folder as your V14 script.\n\n"
            f"ImportError: {e}")
        return None

def open_uploader(parent: tk.Misc | None = None) -> tuple[tk.Toplevel, object] | None:
    """
    Create a Toplevel window inside the existing Tk mainloop and mount the uploader App.
    Returns (window, app) on success.
    """
    mod = _import_uploader()
    if not mod: return None
    if not hasattr(mod, "App"):
        messagebox.showerror("Uploader error", "Module does not expose class 'App'.")
        return None

    # Create a child window of the V14 app
    top = tk.Toplevel(parent if parent is not None else None)
    try:
        top.title(getattr(mod, "APP_TITLE", "Welcome Packet Uploader"))
        # Optional: center roughly over parent
        try:
            p = top.winfo_toplevel() if parent is None else parent.winfo_toplevel()
            p.update_idletasks()
            px = p.winfo_rootx(); py = p.winfo_rooty()
            pw = p.winfo_width() or 1100
            ph = p.winfo_height() or 800
            x = px + max(0, (pw - 1040)//2)
            y = py + max(0, (ph - 800)//3)
            top.geometry(f"+{x}+{y}")
        except Exception:
            pass
        # Mount the uploader app into this Toplevel
        app = mod.App(top)
        top.transient(parent if parent is not None else top.winfo_toplevel())
        top.grab_set()  # modal-ish; remove if you want non-modal
        top.focus_force()
        return top, app
    except Exception as e:
        traceback.print_exc()
        messagebox.showerror("Uploader error", f"Failed to open uploader window:\n{e}")
        try: top.destroy()
        except Exception: pass
        return None

def add_uploader_button(container: tk.Misc, text: str = "Open Welcome Packet Uploader", style: str | None = None):
    """
    Convenience: adds a button to any frame/container that opens the uploader.
    Usage in your V14 file:
        from welcome_uploader_bridge import add_uploader_button
        add_uploader_button(toolbar_frame)  # wherever you want the button
    """
    def _launch():
        parent = container.winfo_toplevel()
        open_uploader(parent)

    kwargs = {"text": text, "command": _launch}
    if style: kwargs["style"] = style  # e.g., "V14.TButton" if defined in your app
    btn = ttk.Button(container, **kwargs)
    # Let the caller pack/grid/place. If you want default pack, uncomment:
    # btn.pack(side="left", padx=8, pady=4)
    return btn
