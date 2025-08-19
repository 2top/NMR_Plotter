import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from pathlib import Path
import threading, time 
import pandas as pd
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib import ticker
from collections import defaultdict
from collections import deque

try:
    import nmrglue as ng
    HAS_NMRGLUE = True
except Exception:
    HAS_NMRGLUE = False

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE_ASCII = os.path.join(BASE_DIR, "cache_ascii.txt")
CACHE_FILE_PDATA = os.path.join(BASE_DIR, "cache_pdata.txt")

# ---------------------------------------------------------------------------
# Global container used by add_dirs / traverse_directory helpers
# ---------------------------------------------------------------------------
state = {}
existing_data = {}

# --------------------
# Preference Handling
# --------------------
PREF_FILENAME = "preferences.txt"

def get_preferences():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return {
        "import_dir": base_dir,
        "template_dir": os.path.join(base_dir, "plot_templates"),
        "default_template": os.path.join(base_dir, "plot_templates", "default.txt"),
        "figure_save_dir": os.path.join(base_dir, "figures"),
        "couple_x_limits": "1",
        "disable_int_norm": "0",
        "import_mode": "ascii",
        "export_use_fixed_size": "1",  # "1" = export uses fixed W/H/DPI; "0" = WYSIWYG
    }

def get_pref(preferences, key, default=""):
    return preferences.get(key, default)

def load_template_file(filepath):
    try:
        with open(filepath, "r") as f:
            for line_number, line in enumerate(f, 1):
                if not line.strip():
                    continue
                if ':' not in line:
                    print(f"Warning: Line {line_number} is malformed (missing colon): {line.strip()}")
                    continue
                key, value = line.strip().split(":", 1)
                if not key:                         # allow empty values
                    print(f"Warning: Line {line_number} has empty key: {line.strip()}")
                    continue
                if key in state:
                    if isinstance(state[key], tk.Entry):
                        state[key].delete(0, tk.END)
                        state[key].insert(0, value)
                    elif isinstance(state[key], tk.StringVar):
                        state[key].set(value)
    except Exception as e:
        print(f"Error loading default template: {e}")

def load_preferences():
    defaults = get_preferences()
    preferences = defaults.copy()
    try:
        with open(os.path.join(defaults["import_dir"], PREF_FILENAME), "r") as f:
            for line in f:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    if key in preferences:
                        preferences[key] = value
    except Exception as e:
        print(f"Warning: Could not read preferences.txt. Using defaults. Reason: {e}")

    # --- normalize empties & non-existent paths back to defaults ---
    for k in ("import_dir", "template_dir", "figure_save_dir"):
        v = preferences.get(k, "")
        if not v or not os.path.isdir(v):
            preferences[k] = defaults[k]
        # ensure the directory exists
        try:
            os.makedirs(preferences[k], exist_ok=True)
        except Exception as ee:
            print(f"Warning: could not create directory '{preferences[k]}': {ee}")
            preferences[k] = defaults[k]

    # default_template: if empty or not a file, fall back to default path
    dt = preferences.get("default_template", "")
    if not dt or not os.path.isfile(dt):
        cand = defaults["default_template"]
        if os.path.isfile(cand):
            preferences["default_template"] = cand
        else:
            # heuristic: pick the first *.txt in template_dir if present
            tdir = preferences["template_dir"]
            try:
                txts = [p for p in os.listdir(tdir) if p.lower().endswith(".txt")]
                if txts:
                    preferences["default_template"] = os.path.join(tdir, txts[0])
            except Exception:
                pass

    # import_mode: harden to either 'ascii' or 'pdata'
    if preferences.get("import_mode") not in ("ascii", "pdata"):
        preferences["import_mode"] = "ascii"

    return preferences

def save_preferences(preferences):
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))  # <-- always save here
        with open(os.path.join(base_dir, PREF_FILENAME), "w") as f:
            for key, value in preferences.items():
                f.write(f"{key}={value}\n")
        return True
    except Exception as e:
        print(f"Error saving preferences: {e}")
        return False

def _init_status_bar(parent_frame):
    """
    Adds a one-line status bar at the bottom of the given frame (e.g. Data Import frame).
    Stores its StringVar in state['status_var'] for global access.
    """
    status_var = tk.StringVar(value="")
    status_lbl = ttk.Label(parent_frame, textvariable=status_var, anchor='w')
    status_lbl.grid(row=99, column=0, columnspan=10, sticky="ew", padx=5, pady=2)
    state['status_var'] = status_var

def _init_plot_status_bar(parent_frame):
    """
    Adds a one-line status bar at the bottom of the Plot frame.
    Stores its StringVar in state['plot_status_var'] for plot-specific messages.
    """
    plot_status = tk.StringVar(value="")
    lbl = ttk.Label(parent_frame, textvariable=plot_status, anchor='w')
    lbl.grid(row=99, column=0, columnspan=10, sticky='ew', padx=5, pady=2)
    state['plot_status_var'] = plot_status

_plot_status_clear_job = None
def set_plot_status(msg, duration=None):
    """Set the plot-frame status bar message. Optionally clear after duration (ms)."""
    global _plot_status_clear_job
    if 'plot_status_var' not in state:
        # fallback to generic status
        set_status(msg, duration)
        return
    state['plot_status_var'].set(msg)
    if _plot_status_clear_job:
        app.after_cancel(_plot_status_clear_job)
    if duration:
        _plot_status_clear_job = app.after(duration, lambda: state['plot_status_var'].set(''))

def _init_tpl_status_bar(parent_frame):
    tpl_status = tk.StringVar(value="")
    lbl = ttk.Label(parent_frame, textvariable=tpl_status, anchor="w")
    lbl.grid(row=99, column=0, columnspan=10, sticky="ew", padx=5, pady=(2,0))
    state['tpl_status_var'] = tpl_status

_tpl_clear_job = None
def set_tpl_status(msg, duration=3000):
    global _tpl_clear_job
    state['tpl_status_var'].set(msg)

    if _tpl_clear_job:
        app.after_cancel(_tpl_clear_job)
    _tpl_clear_job = app.after(duration, lambda: state['tpl_status_var'].set(""))


_status_clear_job = None  # global tracker
def set_status(msg, duration=None):
    """Set the status bar message. Optionally clear after duration (ms)."""
    global _status_clear_job

    state['status_var'].set(msg)

    if _status_clear_job:
        app.after_cancel(_status_clear_job)
        _status_clear_job = None

    if duration:
        _status_clear_job = app.after(duration, clear_status)

def clear_status():
    """Manually clears the status bar."""
    global _status_clear_job

    state['status_var'].set("")
    if _status_clear_job:
        app.after_cancel(_status_clear_job)
        _status_clear_job = None

def _save_dir_cache(top_dir: str, ascii_list: list[str]):
    """
    Save or update one directory’s scan in last_scan.txt.
    If *top_dir* already exists in the cache, its block is **replaced**.
    """
    ascii_list = [p for p in ascii_list if _is_valid_ascii_layout(top_dir, p)]
    # ---------- read existing blocks ----------
    blocks: dict[str, set[str]] = {}
    if os.path.exists(CACHE_FILE_ASCII):
        with open(CACHE_FILE_ASCII, "r", encoding="utf-8") as fh:
            cur_top = None
            for ln in fh:
                line = ln.rstrip("\n")
                if line.startswith("TOP:"):
                    cur_top = line[4:]
                    blocks[cur_top] = set()
                elif cur_top and line:
                    blocks[cur_top].add(line)

    # ---------- overwrite *only* this directory ----------
    blocks[top_dir] = set(ascii_list)          # <- overwrite, no .update()

    # ---------- write back ----------
    with open(CACHE_FILE_ASCII, "w", encoding="utf-8") as fh:
        for td, paths in blocks.items():
            fh.write(f"TOP:{td}\n")
            for p in sorted(paths):
                fh.write(p + "\n")

def _load_dir_cache() -> list[tuple[str, list[str]]] | None:
    """Return [(top_dir, [ascii1 …]), …] or None if the file is absent/empty."""
    if not os.path.exists(CACHE_FILE_ASCII):
        return None

    blocks = []
    with open(CACHE_FILE_ASCII, "r", encoding="utf-8") as fh:
        cur_top, cur_paths = None, []
        for ln in fh:
            line = ln.rstrip("\n")
            if line.startswith("TOP:"):
                if cur_top:
                    blocks.append((cur_top, cur_paths))
                cur_top, cur_paths = line[4:], []
            elif line:
                cur_paths.append(line)
        if cur_top:
            blocks.append((cur_top, cur_paths))

    return blocks or None

def _save_dir_cache_pdata(top_dir: str, pdata_dirs: list[str]):
    """Save/update one directory’s scan in last_scan_pdata.txt (TOP: blocks)."""
    pdata_dirs = [d for d in pdata_dirs if _is_valid_pdata_layout(top_dir, d)]
    blocks: dict[str, set[str]] = {}
    if os.path.exists(CACHE_FILE_PDATA):
        with open(CACHE_FILE_PDATA, "r", encoding="utf-8") as fh:
            cur_top = None
            for ln in fh:
                line = ln.rstrip("\n")
                if line.startswith("TOP:"):
                    cur_top = line[4:]
                    blocks[cur_top] = set()
                elif cur_top and line:
                    blocks[cur_top].add(line)
    blocks[top_dir] = set(pdata_dirs)  # replace this directory’s block
    with open(CACHE_FILE_PDATA, "w", encoding="utf-8") as fh:
        for td, paths in blocks.items():
            fh.write(f"TOP:{td}\n")
            for p in sorted(paths):
                fh.write(p + "\n")

def _load_dir_cache_pdata() -> list[tuple[str, list[str]]] | None:
    """Return [(top_dir, [pdata_dir …]), …] from last_scan_pdata.txt."""
    if not os.path.exists(CACHE_FILE_PDATA):
        return None
    blocks = []
    with open(CACHE_FILE_PDATA, "r", encoding="utf-8") as fh:
        cur_top, cur_paths = None, []
        for ln in fh:
            line = ln.rstrip("\n")
            if line.startswith("TOP:"):
                if cur_top:
                    blocks.append((cur_top, cur_paths))
                cur_top, cur_paths = line[4:], []
            elif line:
                cur_paths.append(line)
        if cur_top:
            blocks.append((cur_top, cur_paths))
    return blocks or None

def _is_valid_pdata_dir(path: str) -> bool:
    """Accept only pdata/<proc> dirs that include procs and 1r (2rr unsupported)."""
    return (
        os.path.isdir(path)
        and os.path.isfile(os.path.join(path, "procs"))
        and os.path.isfile(os.path.join(path, "1r"))
    )

def _parse_expt_proc_from_any(path_like: str) -> tuple[str, str]:
    """
    Given either a pdata dir or .../pdata/<proc>/ascii-spec.txt,
    return (expno, procno) as strings. Falls back to '?' if unclear.
    """
    p = Path(path_like)
    if p.name == "ascii-spec.txt":
        p = p.parent  # -> pdata/<proc>
    # expect .../<expno>/pdata/<proc>
    parts = [part for part in p.parts]
    try:
        i = len(parts) - 1
        procno = parts[i]
        if parts[i - 1].lower() == "pdata":
            expno = parts[i - 2]
        else:
            expno = "?"
    except Exception:
        expno, procno = "?", "?"
    return expno, procno

def _label_for(path_like: str) -> str:
    expno, procno = _parse_expt_proc_from_any(path_like)
    return f"Expt {expno}, proc {procno}"

def _as_float(val):
    """Coerce Bruker/nmrglue values (which can be arrays/strings) to a float, or None."""
    try:
        if isinstance(val, (list, tuple, np.ndarray)):
            val = np.asarray(val).ravel()[0]
        return float(val)
    except Exception:
        return None

def _load_bruker_pdata(pdata_dir: str, x_unit: str):
    """
    Version-proof Bruker pdata loader: returns (x, y) as 1-D float arrays.
    X built from procs: OFFSET (ppm at leftmost point), SW (hz width), SF (MHz).
    """
    if not HAS_NMRGLUE:
        raise ImportError("nmrglue is not installed; cannot read Bruker pdata.")

    dic, data = ng.bruker.read_pdata(pdata_dir)  # dic contains 'procs' and 'acqus'
    y = np.asarray(data, dtype=float).squeeze().ravel()
    npts = y.size

    procs = dic.get("procs", {})
    acqus = dic.get("acqus", {})

    offset_ppm = _as_float(procs.get("OFFSET"))      # ppm at leftmost point
    sw_hz      = _as_float(procs.get("SW_p"))        # Hz in procs
    sf_mhz     = _as_float(procs.get("SF"))          # spectrometer frequency in MHz

    # Fallbacks if needed
    if sw_hz is None:
        sw_hz = _as_float(acqus.get("SW_h"))         # Hz from acqus
    if sf_mhz in (None, 0.0):
        # last resort: try from acqus
        sf_mhz = _as_float(acqus.get("SFO1")) or _as_float(acqus.get("SF"))

    npts = max(int(npts), 1)

    # Build X axis
    if (x_unit == "ppm") and (offset_ppm is not None) and (sw_hz is not None) and (sf_mhz not in (None, 0.0)) and (npts > 1):
        sw_ppm  = sw_hz / sf_mhz            # 1 ppm = SF_MHz Hz  → ppm = Hz / SF_MHz
        step_ppm = sw_ppm / (npts - 1)      # ensure total span == sw_ppm
        x = offset_ppm - np.arange(npts, dtype=float) * step_ppm
    else:
        # Build in Hz then convert (or fall back to index if params missing)
        if (offset_ppm is not None) and (sw_hz is not None) and (sf_mhz not in (None, 0.0)) and (npts > 1):
            offset_hz = offset_ppm * sf_mhz
            step_hz   = sw_hz / (npts - 1)
            x_hz = offset_hz - np.arange(npts, dtype=float) * step_hz
        else:
            x_hz = np.arange(npts, dtype=float)

        if x_unit == "kHz":
            x = x_hz / 1000.0
        elif x_unit == "Hz":
            x = x_hz
        else:  # asked for ppm but we lack params; safest fallback: show Hz axis
            x = x_hz

    x = np.asarray(x, dtype=float).ravel()
    return x, y


# --------------------
# Preferences Dialog
# --------------------
class PreferencesDialog(tk.Toplevel):
    def __init__(self, master, preferences, on_save_callback):
        super().__init__(master)
        self.transient(master)  # keep dialog on top of parent
        self.grab_set()         # make dialog modal (prevent interaction with main window)
        self.title("Preferences")
        self.preferences = preferences.copy()
        self.modified = False
        self.on_save_callback = on_save_callback

        self.vars = {
            key: tk.StringVar(value=value)
            for key, value in preferences.items()
        }

        self._build_gui()

    def _build_gui(self):
        row = 0
        for key, label_text in [
            ("import_dir", "Default starting directory for data import"),
            ("template_dir", "Default directory for plot templates"),
            ("default_template", "Default plot template file"),
            ("figure_save_dir", "Default directory to save figures")
        ]:
            ttk.Label(self, text=label_text).grid(row=row, column=0, sticky="w", padx=10, pady=5)
            entry = ttk.Entry(self, textvariable=self.vars[key], width=60)
            entry.grid(row=row, column=1, padx=5, pady=5)

            browse_button = ttk.Button(self, text="Browse", command=lambda k=key: self.browse(k))
            browse_button.grid(row=row, column=2, padx=5)
            row += 1

        ttk.Separator(self, orient="horizontal").grid(row=row, column=0, columnspan=3,
                                             sticky="ew", pady=5)
        row += 1

        self.chk_couple = tk.IntVar(value=int(self.vars["couple_x_limits"].get()))
        ttk.Checkbutton(self, text="Couple x-masking limits to x-limits",
                        variable=self.chk_couple, command=self.on_change).grid(
                        row=row, column=0, columnspan=3, sticky="w", padx=10)
        row += 1

        self.chk_norm   = tk.IntVar(value=int(self.vars["disable_int_norm"].get()))
        ttk.Checkbutton(self, text="Disable intensity normalization of plotted spectra (tip: set Scaling factor to ~1e-10)",
                        variable=self.chk_norm, command=self.on_change).grid(
                        row=row, column=0, columnspan=3, sticky="w", padx=10)
        row += 1

        ttk.Checkbutton(self,
            text="Export figure using fixed, specified dimensions (unchecked- WYSIWYG for export)",
            variable=self.vars["export_use_fixed_size"], onvalue="1", offvalue="0"
        ).grid(row=row, column=0, columnspan=3, sticky="w", padx=10, pady=(8,0)); row += 1

        # --- Import mode combobox ---
        self.import_mode_var = tk.StringVar(
            value=("ascii" if self.vars.get("import_mode", tk.StringVar(value="ascii")).get() == "ascii" else "pdata")
        )

        ttk.Label(self, text="Import data using").grid(row=row, column=0, sticky="w", padx=10, pady=(8, 2))

        self.import_mode_combo = ttk.Combobox(
            self,
            state="readonly",
            values=["ascii-spec.txt", "pdata (nmrglue)"],
        )
        # map stored value -> label
        self.import_mode_combo.set("ascii-spec.txt" if self.import_mode_var.get() == "ascii" else "pdata (nmrglue)")
        self.import_mode_combo.grid(row=row, column=1, sticky="w", padx=10, pady=(8, 2))
        self.import_mode_combo.bind("<<ComboboxSelected>>", lambda e: self.on_change())
        row += 1

        self.save_btn = ttk.Button(self, text="Save Preferences", command=self.save, state='disabled')
        self.save_btn.grid(row=row, column=0, columnspan=3, pady=15)

        for var in self.vars.values():
            var.trace_add("write", self.on_change)

    def browse(self, key):
        current = self.vars[key].get() or BASE_DIR

        if key in ("import_dir", "template_dir", "figure_save_dir"):
            initdir = current if os.path.isdir(current) else BASE_DIR
            new_path = filedialog.askdirectory(initialdir=initdir)
        elif key == "default_template":
            initdir = (os.path.dirname(current) if os.path.isfile(current)
                    else (self.vars["template_dir"].get() or BASE_DIR))
            new_path = filedialog.askopenfilename(
                initialdir=initdir,
                filetypes=[("Text files", "*.txt")])
        else:
            new_path = filedialog.askopenfilename(
                initialdir=BASE_DIR,
                filetypes=[("Text files", "*.txt")])

        if new_path:
            self.vars[key].set(new_path)

    def on_change(self, *args):
        self.modified = True
        self.save_btn.config(state="normal")

    def save(self):
        updated = {k: v.get() for k, v in self.vars.items()}
        updated["couple_x_limits"] = str(self.chk_couple.get())
        updated["disable_int_norm"] = str(self.chk_norm.get())

        label = self.import_mode_combo.get()
        updated["import_mode"] = "ascii" if label == "ascii-spec.txt" else "pdata"

        # write to disk
        success = save_preferences(updated)
        if success:
            # update app state and re-apply any coupled-limit wiring
            self.on_save_callback(updated)
            try:
                self.master._apply_coupled_limits()
            except Exception:
                pass
            self.destroy()
# ---------------------------------------------------------------------------
#  Custom toolbar so “Save” starts in preferences["figure_save_dir"]
# ---------------------------------------------------------------------------
class CustomNavigationToolbar(NavigationToolbar2Tk):
    # Hide “Configure subplots” and “Customize” buttons (see section 4)
    toolitems = [t for t in NavigationToolbar2Tk.toolitems
                 if t and t[0] not in {"Subplots", "Customize","Pan"}]

    def press_zoom(self, event):
        # turn off constrained while zooming to avoid the zero-size warning
        self._had_constrained = self.canvas.figure.get_constrained_layout()
        if self._had_constrained:
            self.canvas.figure.set_constrained_layout(False)
        super().press_zoom(event)

    def release_zoom(self, event):
        super().release_zoom(event)
        fig = self.canvas.figure
        # re-pad so labels are visible post-zoom
        try:
            # If constrained_layout is active, subplots_adjust is incompatible and will be skipped.
            if getattr(fig, "get_constrained_layout", lambda: False)():
                # constrained_layout will handle spacing automatically; do nothing here.
                pass
            else:
                fig.subplots_adjust(left=0.06, right=0.94, top=0.94, bottom=0.12)
        except Exception:
            # Be defensive — if anything goes wrong, at least don't crash the GUI.
            pass
        self.canvas.draw_idle()
    
    def save_figure(self, *args):  # overrides the stock method
        default_dir = app.preferences.get("figure_save_dir", ".")
        filetypes = [('PDF', '*.pdf'),
                     ('PNG', '*.png'),
                     ('SVG', '*.svg')
                     # ('PostScript', '*.ps'),  # currently disabled, suboptimal export characteristics
                     # ('EPS', '*.eps'),        # currently disabled, suboptimal export characteristics
                     ]
        filename = filedialog.asksaveasfilename(
            title="Save the figure",
            defaultextension=".pdf",
            filetypes=filetypes,
            initialdir=default_dir
        )
        if not filename:
            return

        ext = os.path.splitext(filename)[1].lower()
        use_fixed = app.preferences.get("export_use_fixed_size", "1") == "1"

        # Keep text selectable; avoid transparency → fewer masks in AI
        rc = {
            "pdf.fonttype": 42,        # embed TrueType; text stays text
            "ps.fonttype": 42,
            "svg.fonttype": "none",    # keep <text> in SVG
            "savefig.transparent": False
        }

        with mpl.rc_context(rc):
            if use_fixed:
                unit = (state.get('fig_size_unit') and state['fig_size_unit'].get()) or "mm"
                w_ui = safe_float(state['fig_w_var'].get(), 85 if unit == "mm" else 3.35)
                h_ui = safe_float(state['fig_h_var'].get(), 60 if unit == "mm" else 2.36)
                dpi  = int(safe_float(state['fig_dpi_var'].get(), 300))

                # convert to inches for matplotlib
                if unit == "mm":
                    w_in, h_in = w_ui / 25.4, h_ui / 25.4
                elif unit == "px":
                    w_in, h_in = w_ui / dpi, h_ui / dpi
                else:
                    w_in, h_in = w_ui, h_ui

                fig = plt.Figure(figsize=(w_in, h_in), dpi=dpi, layout="constrained")
                ax  = fig.add_subplot(111)
                ok  = _draw_plot_on(ax, state)
                if ok:
                    # Illustrator-friendly background and no clipping on lines
                    fig.patch.set_facecolor("white")
                    ax.set_facecolor("white")
                    for ln in ax.lines:
                        ln.set_clip_on(True)

                    if ext == ".pdf":
                        fig.savefig(filename, format="pdf", dpi=dpi, bbox_inches='tight', pad_inches=0.02)
                    elif ext == ".svg":
                        fig.savefig(filename, format="svg", dpi=dpi, bbox_inches='tight', pad_inches=0.02)
                    else:
                        fig.savefig(filename, dpi=dpi, bbox_inches='tight', pad_inches=0.02)
                plt.close(fig)

            else:
                # WYSIWYG export of the on-screen figure, but still AI-friendly
                fig = self.canvas.figure
                fig.patch.set_facecolor("white")
                for ax in fig.axes:
                    ax.set_facecolor("white")
                    for ln in ax.lines:
                        ln.set_clip_on(True)

                if ext == ".pdf":
                    fig.savefig(filename, format="pdf", dpi=fig.dpi, bbox_inches='tight', pad_inches=0.02)
                elif ext == ".svg":
                    fig.savefig(filename, format="svg", dpi=fig.dpi, bbox_inches='tight', pad_inches=0.02)
                else:
                    fig.savefig(filename, dpi=fig.dpi, bbox_inches='tight', pad_inches=0.02)

# ---------------------------------------------------------------------------
# Main GUI class 
# ---------------------------------------------------------------------------
class NMRPlotterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.preferences = load_preferences()
        self.pref_window = None  # Track if a PreferencesDialog is already open
        self.title("NMR Plotter")
        self._init_styles()
        # one place to keep spectra and widget handles
        self.existing_data: dict[str, pd.DataFrame] = {}
        self.widgets: dict[str, tk.Widget] = {}    # widget registry 

        self._build_gui()

        # ---- choose a sensible start size: 60 % of screen, but never smaller than 900×600 ----
        self.update_idletasks()                      # finish geometry calculations
        scr_w, scr_h = self.winfo_screenwidth(), self.winfo_screenheight()
        w = max(900, int(scr_w * 0.60))
        h = max(600, int(scr_h * 0.60))
        self.geometry(f"{w}x{h}")

        default_template = self.preferences.get("default_template")
        if default_template and os.path.isfile(default_template):
            load_template_file(default_template)
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _init_styles(self):
            style = ttk.Style(self)

            # On Windows the "clam" theme is easiest to colour; remove the next line on macOS/Linux if you prefer
            # style.theme_use("clam")            

            # ---------- base look ----------
            style.configure("Plot.TButton",
                            foreground="#C91E3A",          # light-blue text
                            background=style.lookup("TButton", "background"),
                            font=("Helvetica", 10, "bold"),
                            borderwidth=1)

            # ---------- dynamic states ----------
            style.map("Plot.TButton",
                    foreground=[("active",   "#98162C"),   # darker blue on hover/press
                                ("disabled", "#D48C96")],  # grey-blue when disabled
                    background=[("disabled",
                                style.lookup("TButton", "background"))])  # keep normal bg
    
    def apply_preferences(self, updated_prefs):
        self.preferences = updated_prefs
        save_preferences(updated_prefs)
        self._apply_coupled_limits() 
    
    def open_preferences(self):
        if self.pref_window is None or not self.pref_window.winfo_exists():
            self.pref_window = PreferencesDialog(self, self.preferences, self.apply_preferences)

    def on_closing(self):
        """Close child dialogs, stop timers, release figures and exit cleanly."""
        # Close the Preferences dialog if it is still open
        if getattr(self, "pref_window", None) and self.pref_window.winfo_exists():
            self.pref_window.destroy()

        # Cancel the delayed-call that updates the status bar (if scheduled)
        global _status_clear_job
        try:
            if _status_clear_job:
                self.after_cancel(_status_clear_job)          # stop pending .after
        except Exception:
            pass
        _status_clear_job = None

        # Close all matplotlib figures that live outside Tk’s control
        plt.close('all')

        # Destroy the Tk application and leave Python
        self.destroy()
        sys.exit(0)

    def _apply_coupled_limits(self):
        """Enforce (or release) the x-limit ↔ mask link."""
        coupled = self.preferences.get("couple_x_limits", "1") == "1"

        x_min, x_max         = state['x_min_entry'],  state['x_max_entry']
        mask_min, mask_max   = state['x_min_mask_entry'], state['x_max_mask_entry']
        target_state         = "disabled" if coupled else "normal"

        # --- helper -------------------------------------------------------------
        def copy_limits_into_masks():
            mask_min.config(state="normal")
            mask_max.config(state="normal")
            mask_min.delete(0, tk.END); mask_min.insert(0, x_min.get())
            mask_max.delete(0, tk.END); mask_max.insert(0, x_max.get())
            mask_min.config(state=target_state)
            mask_max.config(state=target_state)

        # (re)wire whenever x-limits change
        for ent in (x_min, x_max):
            ent.bind("<KeyRelease>", lambda e: coupled and copy_limits_into_masks())

        # initial application
        copy_limits_into_masks() if coupled else (
            mask_min.config(state="normal"),
            mask_max.config(state="normal") )

    # ------------------------------------------------------------
    # Build all widgets (frames, buttons, entries, canvas, etc.)
    # ------------------------------------------------------------
    def _build_gui(self):

        self.state = state

        # DATA INPUT FRAME
        data_frame = ttk.LabelFrame(self, text="Data Import")
        data_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10, rowspan=2, columnspan=2)

        data_tree = ttk.Treeview(data_frame, show="tree")
        data_tree.column("#0", width=300, stretch=True, anchor='w')
        data_tree.grid(row=0, column=0, sticky="nsew", padx=5, columnspan=5)
        
        add_dir_btn = ttk.Button(data_frame ,text="Add New Dir", command=lambda: add_dirs(data_tree))
        add_dir_btn.grid(row=1, column=0, sticky="", padx=5, pady=5)

        load_cache_btn = ttk.Button(
            data_frame,
            text="Load Cached Scan",
            command=lambda: (load_cached_dir_tree_pdata(data_tree)
                            if app.preferences.get("import_mode", "ascii") == "pdata"
                     else load_cached_dir_tree(data_tree))
)
        load_cache_btn.grid(row=1, column=1, sticky="", padx=5, pady=5)

        remove_dir_btn = ttk.Button(data_frame, text="Remove Dir", command=lambda: remove_dir(data_tree))
        remove_dir_btn.grid(row=1, column=2, sticky="", padx=5, pady=5)

        clear_dirs_btn = ttk.Button(data_frame, text="Clear all", command=lambda: clear_dirs(data_tree))
        clear_dirs_btn.grid(row=1, column=3, sticky="", padx=5, pady=5)

        add_workspace_btn = ttk.Button(data_frame, text="Add to Plot Workspace", command=lambda: add_to_workspace(data_tree, workspace_tree))
        add_workspace_btn.grid(row=1, column=4, sticky="", padx=5, pady=5, ipady=5)

        _init_status_bar(data_frame)
        
        # WORKSPACE FRAME
        workspace_frame = ttk.LabelFrame(self, text="Plot Workspace")
        workspace_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=10, rowspan=2, columnspan=2)   

        workspace_tree = ttk.Treeview(workspace_frame, show="tree")
        workspace_tree.column("#0", width=300, anchor='w')
        workspace_tree.grid(row=0, column=0, sticky="nsew", padx=5, columnspan=4)

        move_up_btn = ttk.Button(workspace_frame, text="↑", command=lambda: move_up(workspace_tree))
        move_up_btn.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        move_down_btn = ttk.Button(workspace_frame, text="↓", command=lambda: move_down(workspace_tree))
        move_down_btn.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)

        remove_workspace_btn = ttk.Button(workspace_frame, text="Remove", command=lambda: remove_from_workspace(workspace_tree))
        remove_workspace_btn.grid(row=1, column=2, sticky="nsew", padx=5, pady=5)

        clear_workspace_btn = ttk.Button(workspace_frame, text="Clear", command=lambda: clear_workspace(workspace_tree))
        clear_workspace_btn.grid(row=1, column=3, sticky="nsew", padx=5, pady=5)

        plot_data_btn = ttk.Button(workspace_frame,
                                text="Plot Spectrum",
                                command=lambda: plot_graph(state),
                                state='disabled',
                                style="Plot.TButton")
        plot_data_btn.grid(row=2, column=0, columnspan=4, sticky="nsew", padx=5, pady=(15,5), ipady=5)
        self.widgets['plot_data_btn'] = plot_data_btn
        state['plot_data_btn']        = plot_data_btn

        workspace_frame.grid_rowconfigure(2, weight=1)   # give the new row stretch

        # ACTION FRAME
        action_frame = ttk.LabelFrame(self, text="Templates and Preferences")
        action_frame.grid(row=4, column=0, sticky="nsew", padx=10, pady=10, rowspan=1, columnspan=2)

        import_btn = ttk.Button(action_frame, text="Import Template", command=lambda: import_plot_template(state, initial_dir=self.preferences["template_dir"]))
        import_btn.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        export_btn = ttk.Button(action_frame, text="Save Current as Template", command=lambda: export_plot_template(state))
        export_btn.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        preferences_btn = ttk.Button(action_frame, text="Preferences", command=self.open_preferences)
        preferences_btn.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)

        _init_tpl_status_bar(action_frame)

        # CANVAS FRAME
        canvas_frame = ttk.LabelFrame(self, text="Plot") 
        canvas_frame.grid(row=0, column=2, sticky="nsew", rowspan=5, columnspan=2, padx=10, pady=10)

        plot_container = ttk.Frame(canvas_frame)
        plot_container.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        toolbar_frame = ttk.Frame(plot_container)
        toolbar_frame.grid(row=0, column=0, sticky="ew")

        canvas_holder = tk.Frame(plot_container, bg="white")
        canvas_holder.grid(row=1, column=0, sticky="nsew")

        # make the canvas row stretch
        plot_container.grid_rowconfigure(1, weight=1)
        plot_container.grid_columnconfigure(0, weight=1)
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)

        # keep references (match ascii)
        state['toolbar_frame'] = toolbar_frame
        state['canvas_holder'] = canvas_holder
        _init_plot_status_bar(canvas_frame)
        show_empty_plot(state)
        

        # PLOTTING PARAMETERS (Customization) FRAME
        customization_frame = ttk.LabelFrame(self, text="Plotting Parameters")
        customization_frame.grid(row=5, column=0, sticky="nsew", padx=10, pady=10, columnspan=4)

        # Make all entry columns (1,3,5,7,9) stretch with a sensible min width,
        # and keep label columns (0,2,4,6,8) non-stretching but aligned right.
        for c in (0, 2, 4, 6, 8):
            customization_frame.grid_columnconfigure(c, weight=0, minsize=100)
        for c in (1, 3, 5, 7, 9):
            customization_frame.grid_columnconfigure(c, weight=1, minsize=70)

        # Right-align labels in the label columns so text hugs the entries.
        for w in customization_frame.grid_slaves():
            try:
                gi = w.grid_info()
                if int(gi.get("column", -1)) in (0, 2, 4, 6, 8) and isinstance(w, ttk.Label):
                    w.configure(anchor="e")
            except Exception:
                pass

        # column 1

        x_axis_unit_label = ttk.Label(customization_frame, text="X-Axis Unit:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        x_axis_unit = tk.StringVar()
        x_axis_unit_combobox = ttk.Combobox(customization_frame, textvariable=x_axis_unit, values=["ppm","Hz","kHz"], width=5)
        x_axis_unit_combobox.grid(row=0, column=1, sticky="w", padx=8, pady=5)

        x_min_label = ttk.Label(customization_frame, text="X-Min:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        x_min_entry = ttk.Entry(customization_frame, width=5)
        x_min_entry.grid(row=1, column=1, sticky="w", padx=10, pady=5)

        x_max_label = ttk.Label(customization_frame, text="X-Max:").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        x_max_entry = ttk.Entry(customization_frame, width=5)
        x_max_entry.grid(row=2, column=1, sticky="w", padx=10, pady=5)

        x_min_mask_label = ttk.Label(customization_frame, text="X-Min Mask:").grid(row=3, column=0, sticky="w", padx=10, pady=5)
        x_min_mask_entry = ttk.Entry(customization_frame, width=5)
        x_min_mask_entry.grid(row=3, column=1, sticky="w", padx=10, pady=5)

        x_max_mask_label = ttk.Label(customization_frame, text="X-Max Mask:").grid(row=4, column=0, sticky="w", padx=10, pady=5)
        x_max_mask_entry = ttk.Entry(customization_frame, width=5)
        x_max_mask_entry.grid(row=4, column=1, sticky="w", padx=10, pady=5)

        # column 2

        nucleus_label = ttk.Label(customization_frame, text="Nucleus:").grid(row=0, column=2, sticky="w", padx=10, pady=5)
        nucleus_entry = ttk.Entry(customization_frame, width=5)
        nucleus_entry.grid(row=0, column=3, sticky="w", padx=10, pady=5)

        y_min_label = ttk.Label(customization_frame, text="Y-Min:").grid(row=1, column=2, sticky="w", padx=10, pady=5)
        y_min_entry = ttk.Entry(customization_frame, width=5)
        y_min_entry.grid(row=1, column=3, sticky="w", padx=10, pady=5)

        y_max_label = ttk.Label(customization_frame, text="Y-Max:").grid(row=2, column=2, sticky="w", padx=10, pady=5)
        y_max_entry = ttk.Entry(customization_frame, width=5)
        y_max_entry.grid(row=2, column=3, sticky="w", padx=10, pady=5)

        scaling_factor_label = ttk.Label(customization_frame, text="Scaling Factor:").grid(row=3, column=2, sticky="w", padx=10, pady=5)
        scaling_factor_entry = ttk.Entry(customization_frame, width=5)
        scaling_factor_entry.grid(row=3, column=3, sticky="w", padx=10, pady=5)

        whitespace_label = ttk.Label(customization_frame, text="Whitespace:").grid(row=4, column=2, sticky="w", padx=10, pady=5)
        whitespace_entry = ttk.Entry(customization_frame, width=5)
        whitespace_entry.grid(row=4, column=3, sticky="w", padx=10, pady=5)

        # column 3

        label_font_type_label = ttk.Label(customization_frame, text="Axis Label Font Type:").grid(row=0, column=4, sticky="w", padx=10, pady=5)
        label_font_type_var = tk.StringVar()
        label_font_type_combobox = ttk.Combobox(customization_frame, values=["Arial", "Times New Roman", "Courier New"], textvariable=label_font_type_var, width=5, state="readonly")
        label_font_type_combobox.grid(row=0, column=5, sticky="w", padx=8, pady=5)

        label_font_size_label = ttk.Label(customization_frame, text="Axis Label Font Size:").grid(row=1, column=4, sticky="w", padx=10, pady=5)
        label_font_size_entry = ttk.Entry(customization_frame, width=5)
        label_font_size_entry.grid(row=1, column=5, sticky="w", padx=10, pady=5)
        
        line_thickness_label = ttk.Label(customization_frame, text="Line Thickness:").grid(row=2, column=4, sticky="w", padx=10, pady=5)
        line_thickness_entry = ttk.Entry(customization_frame, width=5)
        line_thickness_entry.grid(row=2, column=5, sticky="w", padx=10, pady=5)
        
        color_scheme_label = ttk.Label(customization_frame, text="Color Scheme:").grid(row=3, column=4, sticky="w", padx=10, pady=5)
        color_scheme_var = tk.StringVar()

        # use non-reversed colormaps; add a single-color choice at the top
        _cmaps = [name for name in mpl.colormaps if not name.endswith("_r")]
        _cmaps.sort()
        color_scheme_values = ["Single color — user specified"] + _cmaps

        color_scheme_combobox = ttk.Combobox(
            customization_frame,
            values=color_scheme_values,
            textvariable=color_scheme_var,
            width=18,  # slightly wider so full names like 'viridis' fit
            state="readonly"
        )
        color_scheme_combobox.grid(row=3, column=5, sticky="w", padx=8, pady=5)
        color_scheme_combobox.current(0)  # default to single color (acts like your old "Custom")

        custom_color_label = ttk.Label(customization_frame, text="Custom Color:").grid(row=4, column=4, sticky="w", padx=10, pady=5)
        custom_color_entry = ttk.Entry(customization_frame, width=5)
        custom_color_entry.grid(row=4, column=5, sticky="w", padx=10, pady=5)


        # column 4

        axis_font_type_label = ttk.Label(customization_frame, text="Tick Label Font Type:").grid(row=0, column=6, sticky="w", padx=10, pady=5)
        axis_font_type_var = tk.StringVar()
        axis_font_type_combobox = ttk.Combobox(customization_frame, values=["Arial", "Times New Roman", "Courier New"], textvariable=axis_font_type_var, width=5, state="readonly")
        axis_font_type_combobox.grid(row=0, column=7, sticky="w", padx=8, pady=5)
        axis_font_type_combobox.current(0)   # default = Arial

        axis_font_size_label = ttk.Label(customization_frame, text="Tick Label Font Size:").grid(row=1, column=6, sticky="w", padx=10, pady=5)
        axis_font_size_entry = ttk.Entry(customization_frame, width=5)
        axis_font_size_entry.grid(row=1, column=7, sticky="w", padx=10, pady=5)

        mode_label = ttk.Label(customization_frame, text="Mode:").grid(row=2, column=6, sticky="w", padx=10, pady=5)
        mode_var = tk.StringVar()
        mode_combobox = ttk.Combobox(customization_frame, values=["stack", "overlay"], textvariable=mode_var, width=5, state="readonly")
        mode_combobox.grid(row=2, column=7, sticky="w", padx=8, pady=5)
        mode_combobox.current(0)

        # Compact X/Y Offset row (row 3, col 6–7)
        off = ttk.Frame(customization_frame)
        off.grid(row=3, column=6, columnspan=2, sticky="ew", padx=10, pady=5)

        ttk.Label(off, text="X-Offset:").grid(row=0, column=0, sticky="w")
        x_offset_entry = ttk.Entry(off, width=5)
        x_offset_entry.grid(row=0, column=1, sticky="w", padx=(2, 8))

        ttk.Label(off, text="Y-Offset:").grid(row=0, column=2, sticky="e")
        y_offset_entry = ttk.Entry(off, width=5)
        y_offset_entry.grid(row=0, column=5, sticky="e", padx=(2, 8))


        # column 5

        major_ticks_freq_label = ttk.Label(customization_frame, text="Major Ticks Spacing:").grid(row=0, column=8, sticky="w", padx=10, pady=5)
        major_ticks_freq_entry = ttk.Entry(customization_frame, width=5)
        major_ticks_freq_entry.grid(row=0, column=9, sticky="w", padx=10, pady=5)

        minor_ticks_freq_label = ttk.Label(customization_frame, text="Minor Ticks Interval:").grid(row=1, column=8, sticky="w", padx=10, pady=5)
        minor_ticks_freq_entry = ttk.Entry(customization_frame, width=5)
        minor_ticks_freq_entry.grid(row=1, column=9, sticky="w", padx=10, pady=5)

        major_ticks_len_label = ttk.Label(customization_frame, text="Major Ticks Length:").grid(row=2, column=8, sticky="w", padx=10, pady=5)
        major_ticks_len_entry = ttk.Entry(customization_frame, width=5)
        major_ticks_len_entry.grid(row=2, column=9, sticky="w", padx=10, pady=5)

        minor_ticks_len_label = ttk.Label(customization_frame, text="Minor Ticks Length:").grid(row=3, column=8, sticky="w", padx=10, pady=5)
        minor_ticks_len_entry = ttk.Entry(customization_frame, width=5)
        minor_ticks_len_entry.grid(row=3, column=9, sticky="w", padx=10, pady=5)
        

        # Compact export size row: row 4, col 6–7 (right under the new X/Y offset line)
        exp = ttk.Frame(customization_frame)
        exp.grid(row=4, column=6, columnspan=2, sticky="w", padx=10, pady=5)

        ttk.Label(exp, text="Size:").grid(row=0, column=0, sticky="w")

        # Units
        size_unit_var = tk.StringVar(value="mm")  # choose "mm" by default (friendlier than inches)
        size_unit_combo = ttk.Combobox(exp, values=["mm", "in", "px"], width=4, state="readonly", textvariable=size_unit_var)
        size_unit_combo.grid(row=0, column=1, sticky="w", padx=(4, 12))

        # Width
        state['fig_w_var'] = tk.StringVar(value="85")  # 85 mm ≈ 3.35 in
        ttk.Label(exp, text="W").grid(row=0, column=2, sticky="e")
        fig_w_entry = ttk.Entry(exp, width=4, textvariable=state['fig_w_var'])
        fig_w_entry.grid(row=0, column=3, sticky="w", padx=(2, 8))

        # Height
        state['fig_h_var'] = tk.StringVar(value="60")  # 60 mm ≈ 2.36 in
        ttk.Label(exp, text="H").grid(row=0, column=4, sticky="e")
        fig_h_entry = ttk.Entry(exp, width=4, textvariable=state['fig_h_var'])
        fig_h_entry.grid(row=0, column=5, sticky="w", padx=(2, 8))

        # DPI
        state['fig_dpi_var'] = tk.StringVar(value="300")
        ttk.Label(exp, text="DPI").grid(row=0, column=6, sticky="e")
        fig_dpi_entry = ttk.Entry(exp, width=4, textvariable=state['fig_dpi_var'])
        fig_dpi_entry.grid(row=0, column=7, sticky="w", padx=(2, 8))

        tick_tools = ttk.Frame(customization_frame)
        tick_tools.grid(row=4, column=8, columnspan=2, sticky="ew", padx=10, pady=(0,5))
        tick_tools.grid_columnconfigure(0, weight=0)  # checkbox column
        tick_tools.grid_columnconfigure(1, weight=1)  # button stretches

        # Mode toggle: resizable vs fixed figure (placed inside the 'exp' subframe)
        state['resizable_mode_var'] = tk.BooleanVar(value=False)  # default: fixed (not resizable)

        resizable_chk = ttk.Checkbutton(
            tick_tools,
            text="Resizable figure mode",
            variable=state['resizable_mode_var']
        )
        resizable_chk.grid(row=0, column=0, sticky="w", padx=(0,8), pady=0)

        grab_btn = ttk.Button(
            tick_tools,
            text="Get current plot size",
            command=lambda: get_current_plot_size(state)
        )
        grab_btn.grid(row=0, column=1, sticky="ew", padx=0, pady=0)

        # Make sure the grab button is enabled/disabled automatically when the toggle changes
        def _on_resizable_toggle(*_):
            grab_btn.config(state='normal' if state['resizable_mode_var'].get() else 'disabled')

        def _on_resizable_toggle_and_replot(*_):
            # first do the existing toggle work (enable/disable inputs etc.)
            try:
                _on_resizable_toggle()
            except Exception:
                pass
            # then immediately replot to reflect the new mode
            try:
                plot_graph(state)
            except Exception:
                pass

        # initial enable/disable
        _on_resizable_toggle()
        # hook up a trace so toggle updates the button state instantly
        try:
            state['resizable_mode_var'].trace_add('write', _on_resizable_toggle_and_replot)
        except Exception:
            # older tkinter versions
            state['resizable_mode_var'].trace('w', lambda *a: _on_resizable_toggle())
        
        # Configure the main grid
        self.grid_rowconfigure(0, weight=1, minsize=50)  # Row for Data Frame and Canvas (Canvas is on right side row 0)
        self.grid_rowconfigure(2, weight=1, minsize=50)  # Row for Workspace
        self.grid_rowconfigure(4, weight=1, minsize=70)  # Row for Actions
        self.grid_rowconfigure(5, weight=1, minsize=200)  # Row for Customization

        self.grid_columnconfigure(0, weight=1, uniform="half")  # Column for Data Import, Workspace, Actions, Customization
        self.grid_columnconfigure(2, weight=2, uniform="half")  # Column for Canvas Frame

        # Configure the frames
        data_frame.grid_rowconfigure(0, weight=1)  # Allow the data tree to expand
        data_frame.grid_rowconfigure(1, weight=0)   # Add-Dir / Load-Cache / … buttons
        for col in range(4):
            data_frame.grid_columnconfigure(col, weight=1)  # Allow the buttons to expand

        workspace_frame.grid_rowconfigure(0, weight=1)  # Allow the workspace tree to expand
        workspace_frame.grid_rowconfigure(1, weight=0)   # ↑/↓/Remove/Clear buttons
        workspace_frame.grid_rowconfigure(2, weight=0)   # Plot Spectrum button (stays visible)
        for col in range(4):
            workspace_frame.grid_columnconfigure(col, weight=1)  # Allow the buttons to expand

        action_frame.grid_rowconfigure(0, weight=0)  # Allow the action buttons to expand
        for col in range(4):
            action_frame.grid_columnconfigure(col, weight=1)  # Allow the buttons to expand
        
        canvas_frame.grid_rowconfigure(0, weight=1)  # Allow the canvas to expand
        canvas_frame.grid_columnconfigure(0, weight=1)  # Allow the canvas to expand

        # Customization Options Expansion
        for col in range(10): 
            customization_frame.grid_columnconfigure(col, weight=1)  # Allow all columns to expand

        for row in range(5):
            customization_frame.grid_rowconfigure(row, weight=1)

        # Store all GUI elements in the state dictionary
        state['data_tree'] = data_tree
        state['workspace_tree'] = workspace_tree
        
        state['canvas_frame'] = canvas_frame
        state['x_min_entry'] = x_min_entry
        state['x_max_entry'] = x_max_entry
        state['y_min_entry'] = y_min_entry
        state['y_max_entry'] = y_max_entry
        state['x_axis_unit'] = x_axis_unit
        state['x_min_mask_entry'] = x_min_mask_entry
        state['x_max_mask_entry'] = x_max_mask_entry
        state['mode_var'] = mode_var
        state['x_offset_entry'] = x_offset_entry
        state['y_offset_entry'] = y_offset_entry
        state['nucleus_entry'] = nucleus_entry
        state['color_scheme_var'] = color_scheme_var
        state['color_scheme_var'] = color_scheme_var
        state['custom_color_entry'] = custom_color_entry
        state['axis_font_type_var'] = axis_font_type_var
        state['axis_font_size_entry'] = axis_font_size_entry
        state['label_font_type_var'] = label_font_type_var
        state['label_font_size_entry'] = label_font_size_entry
        state['line_thickness_entry'] = line_thickness_entry
        state['scaling_factor_entry'] = scaling_factor_entry
        state['whitespace_entry'] = whitespace_entry
        state['major_ticks_freq_entry'] = major_ticks_freq_entry
        state['minor_ticks_freq_entry'] = minor_ticks_freq_entry
        state['major_ticks_len_entry'] = major_ticks_len_entry
        state['minor_ticks_len_entry'] = minor_ticks_len_entry
        state['fig_w_entry']   = fig_w_entry
        state['fig_h_entry']   = fig_h_entry
        state['fig_dpi_entry'] = fig_dpi_entry

        state['fig_size_unit'] = size_unit_var     # for templates
        state['fig_w'] = state['fig_w_var']
        state['fig_h'] = state['fig_h_var']
        state['fig_dpi'] = state['fig_dpi_var']


        self._apply_coupled_limits() 
    

def safe_float(text, default=None):
    # Utility: safe float conversion (blank or non-numeric → default)
    try:
        return float(text)
    except (TypeError, ValueError):
        return default

def is_bruker_pdata_dir(path: str) -> bool:
    """Return True if *path* looks like a Bruker processed directory (pdata/<proc>)."""
    if not os.path.isdir(path):
        return False
    procs = os.path.join(path, "procs")
    one_r = os.path.join(path, "1r")
    two_rr = os.path.join(path, "2rr")
    return os.path.isfile(procs) and (os.path.isfile(one_r) or os.path.isfile(two_rr))

def find_pdata_dir(path: str) -> str | None:
    """
    Given anything inside a Bruker dataset, find the nearest pdata/<proc> dir
    that contains procs + 1r/2rr. If *path* itself is such a dir, return it.
    """
    if is_bruker_pdata_dir(path):
        return path
    # walk up at most 5 levels just to be safe
    cur = os.path.abspath(path)
    for _ in range(5):
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        # common layout: .../<expt>/pdata/<proc>/
        if os.path.basename(parent).lower() == "pdata":
            # check all children
            for child in os.listdir(parent):
                cand = os.path.join(parent, child)
                if is_bruker_pdata_dir(cand):
                    return cand
        if is_bruker_pdata_dir(parent):
            return parent
        cur = parent
    # brute-force search below original root as a last resort
    if os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            if is_bruker_pdata_dir(root):
                return root
    return None

def _quick_validate_bruker_top(
    selected_dir: str,
    *,
    expected_depth: int = 4,   # relative parts: sample/expt/pdata/proc
    max_visits: int = 600,     # hard cap on how many dirs we’ll look at
    max_depth: int = 6         # never look deeper than this from selected_dir
) -> tuple[bool, str | None]:
    """
    Fast, bounded validator. Returns (True, None) only when we find a valid
    Bruker proc dir (procs + 1r or ascii-spec.txt) at exactly:
        <sel>/<sample>/<expt>/pdata/<proc>  (depth == expected_depth)

    Returns (False, reason) when:
      - The user is too LOW (sel/pdata exists)
      - The first valid dataset we spot is deeper than expected → TOO HIGH
      - We hit the visit/depth limits or see no valid layout quickly
    """
    sel = Path(selected_dir)
    if not sel.exists() or not sel.is_dir():
        return False, "Selected path does not exist or is not a directory."

    # Too LOW: they clicked directly into an experiment (has 'pdata' here)
    if (sel / "pdata").exists():
        return False, "Selected folder looks like an experiment-level folder (too LOW)."

    # Bounded breadth-first search using os.scandir (fast, avoids stat-ing all children)
    q = deque([(str(sel), 0)])
    visits = 0

    def _is_proc_dir(path: str) -> bool:
        # Accept pdata/<proc> that has 'procs' AND (1r or ascii-spec.txt)
        procs = os.path.join(path, "procs")
        one_r = os.path.join(path, "1r")
        ascsp = os.path.join(path, "ascii-spec.txt")
        return os.path.isfile(procs) and (os.path.isfile(one_r) or os.path.isfile(ascsp))

    while q:
        cur, depth = q.popleft()
        if depth > max_depth:
            continue

        try:
            with os.scandir(cur) as it:
                for entry in it:
                    if not entry.is_dir(follow_symlinks=False):
                        continue

                    visits += 1
                    if visits > max_visits:
                        # We refuse to scan a huge tree from too high up
                        return False, "Selected folder appears to be too high (quick check limit reached)."

                    # Fast path: if this directory itself is a valid proc folder, measure its depth.
                    if _is_proc_dir(entry.path):
                        rel_depth = len(Path(entry.path).relative_to(sel).parts)
                        if rel_depth == expected_depth:
                            return True, None
                        if rel_depth > expected_depth:
                            return False, "Selected folder appears to be too high in the directory tree."
                        # If somehow shallower, keep going (very unusual)

                    # Cheap pruning: if we already hit 'pdata' at this level, don’t recurse past proc level
                    if entry.name.lower() == "pdata":
                        # Only look one level into pdata (proc folders)
                        try:
                            with os.scandir(entry.path) as procs:
                                for p in procs:
                                    if p.is_dir(follow_symlinks=False) and _is_proc_dir(p.path):
                                        rel_depth = len(Path(p.path).relative_to(sel).parts)
                                        if rel_depth == expected_depth:
                                            return True, None
                                        if rel_depth > expected_depth:
                                            return False, "Selected folder appears to be too high in the directory tree."
                        except PermissionError:
                            pass
                        # Don’t queue deeper past pdata
                        continue

                    # Otherwise, queue this child for a shallow look
                    q.append((entry.path, depth + 1))

        except PermissionError:
            # Skip unreadable branches silently
            continue

    return False, "Could not detect Bruker ascii/pdata layout under the selected folder."

def scan_bruker_structure(selected_dir):
    """
    Validate a Bruker directory tree where the user selects the folder that
    directly contains sample folders.  Expected relative layout is:

        selected_dir/
            └── <sample_name>/          (any string)
                └── <expt#>/            (numeric)
                    └── pdata/
                        └── <proc#>/    (numeric)
                            └── ascii-spec.txt

    On success returns (ascii_paths, True, set()).
    On mismatch returns (partial_paths, False, {"reason", ...}).
    """
    ascii_paths     = []
    structure_ok    = False
    bad_reasons     = set()
    expected_depth  = 4          # <sample> / <expt#> / pdata / <proc#>

    for root, dirs, files in os.walk(selected_dir):
        rel_parts = Path(root).relative_to(selected_dir).parts

        # We never need to look deeper than the proc folder
        if len(rel_parts) > expected_depth:
            dirs.clear()
            continue

        if "ascii-spec.txt" in files:
            depth = len(rel_parts)

            # Flag selections that are too high / low
            if depth != expected_depth:
                if depth > expected_depth:
                    bad_reasons.add(
                        f"Directory too HIGH – ascii-spec.txt is {depth - expected_depth} "
                        f"level(s) deeper (e.g., {root})"
                    )
                else:
                    bad_reasons.add(
                        f"Directory too LOW – you chose inside a sample/experiment folder (e.g., {root})"
                    )
                continue

            # depth == expected_depth → detailed sanity checks
            sample, expt, pdata_dir, proc = rel_parts

            if not expt.isdigit():
                bad_reasons.add(f"Experiment folder '{expt}' is not numeric");   continue
            if pdata_dir != "pdata":
                bad_reasons.add(f"Expected 'pdata', found '{pdata_dir}' in {root}");   continue
            if not proc.isdigit():
                bad_reasons.add(f"Proc folder '{proc}' is not numeric");   continue

            ascii_paths.append(os.path.join(root, "ascii-spec.txt"))
            structure_ok = True        # at least one valid dataset found

        # Optional early test: stop descending into non-numeric experiment dirs
        if len(rel_parts) == 2 and not rel_parts[1].isdigit():
            dirs.clear()

    return ascii_paths, structure_ok, bad_reasons

def add_dirs(tree):
    """Directory selection + validation + loading based on import_mode."""
    global existing_data

    selected_dir = filedialog.askdirectory(
        initialdir=app.preferences.get("import_dir", os.path.expanduser("~")),
        title="Select Data Directory"
    )
    if not selected_dir:
        return

    import_mode = app.preferences.get("import_mode", "ascii")

    # Show immediate feedback and flush to the UI before the thread starts
    filetype = "ascii-spec.txt" if import_mode == "ascii" else "pdata"
    pretty = os.path.basename(selected_dir) or selected_dir
    set_status(f"🔎 Scanning {pretty} for {filetype} files…")
    try:
        app.update_idletasks()
    except Exception:
        pass

    # --- QUICK VALIDATION: abort early for 'too high' / 'too low' cases ---
    ok, reason = _quick_validate_bruker_top(selected_dir)
    if not ok:
        set_status("❌ Import aborted - folder level appears incorrect.")
        return
    # --- end quick validation ---

    def _count_leaves(tree_dict: dict) -> int:
        total = 0
        for top in tree_dict.values():
            for sample_children in top.values():
                total += len(sample_children)
        return total

    def worker_ascii():
        t0 = time.perf_counter()
        try:
            result = traverse_directory_ascii(selected_dir)
            n = _count_leaves(result)
        except Exception as e:
            return app.after(0, lambda: set_status(f"❌ Scan failed: {e}"))

        if n == 0:
            return app.after(0, lambda: set_status("❌ No valid ascii-spec.txt files found- did you run convbin2asc?"))

        def finalize():
            nonlocal result, n
            for k, v in result.items():
                existing_data.setdefault(k, {}).update(v)
            populate_treeview(tree, existing_data)

            ascii_paths = []
            for _, samples in result.items():
                for _, label_map in samples.items():
                    ascii_paths.extend(label_map.values())

            _save_dir_cache(selected_dir, ascii_paths)
            dt = time.perf_counter() - t0
            set_status(f"✅ Loaded {n} ascii-spec.txt dataset{'s' if n != 1 else ''} in {dt:.1f}s")

        app.after(0, finalize)

    def worker_pdata():
        t0 = time.perf_counter()
        try:
            result = traverse_directory_pdata(selected_dir)
            n = _count_leaves(result)
        except Exception as e:
            return app.after(0, lambda: set_status(f"❌ Scan failed: {e}"))

        if n == 0:
            return app.after(0, lambda: set_status("❌ No valid Bruker pdata/<proc> directories (procs + 1r) found."))

        def finalize():
            nonlocal result, n
            for k, v in result.items():
                existing_data.setdefault(k, {}).update(v)
            populate_treeview(tree, existing_data)

            pdata_dirs = []
            for _, samples in result.items():
                for _, label_map in samples.items():
                    pdata_dirs.extend(label_map.values())

            _save_dir_cache_pdata(selected_dir, pdata_dirs)
            dt = time.perf_counter() - t0
            set_status(f"✅ Loaded {n} Bruker pdata dataset{'s' if n != 1 else ''} in {dt:.1f}s")

        app.after(0, finalize)

    threading.Thread(
        target=worker_ascii if import_mode == "ascii" else worker_pdata,
        daemon=True
    ).start()

def load_cached_dir_tree(tree):
    blocks = _load_dir_cache()
    if not blocks:
        set_status("No cached scan found.")
        return

    tree.delete(*tree.get_children())
    tree_dict: dict[str, dict[str, dict[str,str]]] = {}
    skipped_lines = False  # track if we hit malformed entries

    for top_dir, ascii_files in blocks:
        samples: dict[str, dict[str, str]] = defaultdict(dict)

        for f in ascii_files:
            try:
                parts = Path(f).relative_to(top_dir).parts
            except Exception:
                skipped_lines = True
                continue

            if len(parts) < 5 or parts[-1].lower() != "ascii-spec.txt" or parts[-3].lower() != "pdata":
                skipped_lines = True
                continue
            if not (parts[-4].isdigit() and parts[-2].isdigit()):
                skipped_lines = True
                continue

            sample = parts[0]
            expt   = parts[-4]
            proc   = parts[-2]
            label = f"Expt {expt}, proc {proc}"
            samples[sample][label] = f

        for samp, sub in samples.items():
            samples[samp] = dict(sorted(
                sub.items(),
                key=lambda kv: (int(kv[0].split()[1].rstrip(',')),
                                int(kv[0].split()[3]))
            ))
        parts_top = Path(top_dir).parts
        if len(parts_top) >= 2:
            label_top = f"{parts_top[-2]}/{parts_top[-1]}"
        else:
            label_top = parts_top[-1]  # fallback if somehow only one part
        tree_dict[label_top] = samples

    populate_treeview(tree, tree_dict, type_hint="ascii")
    global existing_data
    existing_data.clear()
    existing_data.update(tree_dict)

    msg = f"✅ Loaded cached ascii-spec.txt scans from {len(blocks)} folder(s)"
    if skipped_lines:
        msg += " — Some cache entries were invalid. You may need to clear the cache."
    set_status(msg)

def load_cached_dir_tree_pdata(tree):
    blocks = _load_dir_cache_pdata()
    if not blocks:
        set_status("No cached pdata scan found.")
        return

    tree.delete(*tree.get_children())
    tree_dict: dict[str, dict[str, dict[str, str]]] = {}
    skipped_lines = False  # track if we hit malformed entries

    for top_dir, pdata_dirs in blocks:
        samples: dict[str, dict[str, str]] = defaultdict(dict)

        for d in pdata_dirs:
            try:
                parts = Path(d).relative_to(top_dir).parts
            except Exception:
                skipped_lines = True
                continue

            # Expect: <sample>/<expt>/pdata/<proc>
            if len(parts) < 4 or parts[-2].lower() != "pdata":
                skipped_lines = True
                continue
            if not (parts[-3].isdigit() and parts[-1].isdigit()):
                skipped_lines = True
                continue

            sample = parts[0]
            expt   = parts[-3]
            proc   = parts[-1]
            label = f"Expt {expt}, proc {proc}"
            samples[sample][label] = d

        for samp, sub in samples.items():
            samples[samp] = dict(sorted(
                sub.items(),
                key=lambda kv: (int(kv[0].split()[1].rstrip(',')),
                                int(kv[0].split()[3]))
            ))
        parts_top = Path(top_dir).parts
        if len(parts_top) >= 2:
            label_top = f"{parts_top[-2]}/{parts_top[-1]}"
        else:
            label_top = parts_top[-1]  # fallback if somehow only one part
        tree_dict[label_top] = samples

    populate_treeview(tree, tree_dict, type_hint="pdata")
    global existing_data
    existing_data = tree_dict

    msg = f"✅ Loaded cached pdata scans from {len(blocks)} folder(s)"
    if skipped_lines:
        msg += " — Some cache entries were invalid. You may need to clear the cache."
    set_status(msg)

def _is_valid_ascii_layout(top_dir: str, f: str) -> bool:
    try:
        parts = Path(f).relative_to(top_dir).parts
    except Exception:
        return False
    return (
        len(parts) >= 5
        and parts[-1].lower() == "ascii-spec.txt"
        and parts[-3].lower() == "pdata"
        and parts[-4].isdigit()
        and parts[-2].isdigit()
    )

def _is_valid_pdata_layout(top_dir: str, d: str) -> bool:
    try:
        parts = Path(d).relative_to(top_dir).parts
    except Exception:
        return False
    return (
        len(parts) >= 4
        and parts[-2].lower() == "pdata"
        and parts[-3].isdigit()
        and parts[-1].isdigit()
    )


def traverse_directory_ascii(root_dir: str) -> dict:
    """
    {basename(root_dir): {sample: {"Expt N, proc M": <ascii-path>}}}
    Only include .../pdata/<proc>/ascii-spec.txt files.
    """
    top_label = os.path.basename(root_dir)
    samples: dict[str, dict[str, str]] = defaultdict(dict)

    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if not d.startswith('.')]
        filenames = [f for f in filenames if not f.startswith('.')]

        if "ascii-spec.txt" in filenames:
            ascii_path = os.path.join(dirpath, "ascii-spec.txt")
            # sample = folder immediately under root_dir
            rel = Path(dirpath).relative_to(root_dir)
            sample = rel.parts[0] if rel.parts else os.path.basename(root_dir)
            label = _label_for(ascii_path)
            samples[sample][label] = ascii_path

    # numeric-ish sort
    def _k(lbl: str):
        try:
            parts = lbl.split()
            return (int(parts[1].rstrip(',')), int(parts[3]))
        except Exception:
            return (10**9, 10**9)

    for samp in list(samples.keys()):
        samples[samp] = dict(sorted(samples[samp].items(), key=lambda kv: _k(kv[0])))

    return {top_label: dict(samples)}


def traverse_directory_pdata(root_dir: str) -> dict:
    """
    {basename(root_dir): {sample: {"Expt N, proc M": <pdata-dir>}}}
    Only include pdata/<proc> dirs with procs + 1r (ignore 2rr).
    """
    top_label = os.path.basename(root_dir)
    samples: dict[str, dict[str, str]] = defaultdict(dict)

    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if not d.startswith('.')]
        filenames = [f for f in filenames if not f.startswith('.')]

        if _is_valid_pdata_dir(dirpath):
            rel = Path(dirpath).relative_to(root_dir)
            sample = rel.parts[0] if rel.parts else os.path.basename(root_dir)
            label = _label_for(dirpath)
            samples[sample][label] = dirpath

    def _k(lbl: str):
        try:
            parts = lbl.split()
            return (int(parts[1].rstrip(',')), int(parts[3]))
        except Exception:
            return (10**9, 10**9)

    for samp in list(samples.keys()):
        samples[samp] = dict(sorted(samples[samp].items(), key=lambda kv: _k(kv[0])))

    return {top_label: dict(samples)}

def extract_experiment_number(dir_path):
    """Return the Bruker experiment number folder

    Falls back to None if the path is too shallow instead of raising IndexError.
    """
    parts = dir_path.split(os.sep)
    return parts[-3] if len(parts) >= 3 else None


def extract_proc_number(dir_path):
    """Extract the proc number from a directory path."""
    parts = dir_path.split(os.sep)
    return parts[-1]

def _guess_leaf_type(path_str: str) -> str:
    """Return 'ascii', 'pdata', or 'unknown' using only string/path parts."""
    if not isinstance(path_str, str):
        return "unknown"
    low = path_str.lower()
    if low.endswith("ascii-spec.txt"):
        return "ascii"
    # Heuristic: any path with .../pdata/<proc#> is pdata
    try:
        parts = [p.lower() for p in Path(path_str).parts]
        if "pdata" in parts:
            # last part is usually the proc number
            last = Path(path_str).name
            if last.isdigit():
                return "pdata"
            # allow pdata/<proc>/ wherever proc is numeric
            # if not numeric, still probably pdata but mark unknown to be safe
            return "unknown"
    except Exception:
        pass
    return "unknown"

def populate_treeview(tree, data, type_hint: str | None = None):
    """Populate a Treeview with {top: {sample: {label: path}}}.
       Adds (ascii)/(pdata) on top-level labels when mixed.
       type_hint: optionally 'ascii' or 'pdata' to skip filesystem checks.
    """
    def has_ascii_pdata(d):
        has_a, has_p = False, False

        def walk(val):
            nonlocal has_a, has_p
            if isinstance(val, dict):
                for v in val.values():
                    walk(v)
            else:
                if not isinstance(val, str):
                    return
                if type_hint == "ascii":
                    has_a = True
                elif type_hint == "pdata":
                    has_p = True
                else:
                    t = _guess_leaf_type(val)
                    if t == "ascii": has_a = True
                    elif t == "pdata": has_p = True

        walk(d)
        return has_a, has_p

    all_has_a, all_has_p = has_ascii_pdata(data)

    def insert_items(parent, items, level=0):
        for key, value in items.items():
            if isinstance(value, dict):
                display = key
                if level == 0 and all_has_a and all_has_p:
                    sub_a, sub_p = has_ascii_pdata({key: value})
                    if sub_a and not sub_p:
                        display = f"{key} (ascii)"
                    elif sub_p and not sub_a:
                        display = f"{key} (pdata)"
                node = tree.insert(parent, "end", text=display, values=(key,))
                insert_items(node, value, level + 1)
            else:
                tree.insert(parent, "end", text=key, values=(value,))

    tree.delete(*tree.get_children(""))
    insert_items("", data)

def add_to_workspace(data_tree, workspace_tree):
    selected_items = data_tree.selection()
    if not selected_items:
        set_status("No items selected", 4000)
        return

    import_mode = app.preferences.get("import_mode", "ascii")
    added = 0

    for s in selected_items:
        # still forbid folders (only leaves)
        if data_tree.get_children(s):
            set_status(f"⚠️  '{data_tree.item(s)['text']}' is a folder; select individual datasets.", 5000)
            continue

        full_path = data_tree.item(s)['values'][0]

        if import_mode == "ascii":
            # must be .../ascii-spec.txt
            if not full_path.endswith("ascii-spec.txt"):
                set_status(f"⚠️  '{data_tree.item(s)['text']}' is not a valid dataset.", 5000)
                continue

            proc_folder   = extract_proc_number(os.path.dirname(full_path))
            expt_folder   = extract_experiment_number(os.path.dirname(full_path))
            sample_folder = os.path.basename(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(full_path))))
            )
            display_name = f"{sample_folder} / expt {expt_folder} / proc {proc_folder}"

        else:  # pdata mode
            # must be a pdata/<proc> dir with procs + 1r
            if not _is_valid_pdata_dir(full_path):
                set_status(f"⚠️  '{data_tree.item(s)['text']}' is not a valid pdata dataset (need procs + 1r).", 5000)
                continue

            expt_folder, proc_folder = _parse_expt_proc_from_any(full_path)
            sample_folder = os.path.basename(
                os.path.dirname(os.path.dirname(os.path.dirname(full_path)))
            )
            display_name = f"{sample_folder} / expt {expt_folder} / proc {proc_folder}"

        workspace_tree.insert("", "end", text=display_name, values=(full_path,))
        added += 1

    if added and 'plot_data_btn' in state:
        state['plot_data_btn'].config(state='normal')

    if added:
        set_status(f"✅  Added {added} dataset{'s' if added > 1 else ''} to workspace", 4000)

def remove_dir(data_tree):
    """Remove the selected top-level directory from the data import treeview."""
    selected_items = data_tree.selection()
    for item in selected_items:
        parent = data_tree.parent(item)
        # Ensure only top-level items are removed
        if not parent:
            data_tree.delete(item)
        else:
            set_status(f"⚠️  Cannot remove '{data_tree.item(item)['text']}' because it isn’t a top-level item.", 5000)


def clear_dirs(data_tree):
    """Remove all top-level directories from the data import treeview."""
    top_level_items = data_tree.get_children()
    for item in top_level_items:
        data_tree.delete(item)


def remove_from_workspace(tree):
    """Remove the selected items from the workspace tree."""
    selected_items = tree.selection()
    for item in selected_items:
        tree.delete(item)
    # Disable Plot button if workspace is now empty
    if not tree.get_children():
        if 'plot_data_btn' in state:
            state['plot_data_btn'].config(state='disabled')


def clear_workspace(tree):
    """Remove all items from the workspace tree."""
    for item in tree.get_children():
        tree.delete(item)
    if 'plot_data_btn' in state:
        state['plot_data_btn'].config(state='disabled')


def move_up(tree):
    """Move the selected item up in the treeview."""
    selected_items = tree.selection()
    if not selected_items:
        return  # No item selected

    for item in selected_items:
        index = tree.index(item)
        if index > 0:  # Ensure it isn't already at the top
            parent = tree.parent(item)
            tree.move(item, parent, index - 1)


def move_down(tree):
    """Move the selected item down in the treeview."""
    selected_items = tree.selection()
    if not selected_items:
        return  # No item selected

    for item in selected_items:
        index = tree.index(item)
        parent = tree.parent(item)
        children = tree.get_children(parent)
        if index < len(children) - 1:  # Ensure it isn't already at the bottom
            tree.move(item, parent, index + 1)


def plot_graph(state):
    """Plot the data based on the current state.

    Behavior:
      - If resizable_mode_var is False (fixed mode), extract the W/H/DPI from the UI
        and set state['desired_fig_spec'] (in inches + dpi). customize_graph() will
        create the figure using that physical size and the live view will be scaled
        down to fit the canvas if needed.
      - If resizable_mode_var is True, clear any desired_fig_spec so the live figure
        will be allowed to adapt / be resized.
    """
    set_tpl_status("")          # clear template messages
    gather_data(state)
    transform_data(state)

    # Read UI-provided desired figure size
    unit = (state.get('fig_size_unit') and state['fig_size_unit'].get()) or "mm"
    try:
        w_ui = float(state['fig_w_var'].get())
    except Exception:
        w_ui = None
    try:
        h_ui = float(state['fig_h_var'].get())
    except Exception:
        h_ui = None
    try:
        dpi = int(safe_float(state.get('fig_dpi_var', tk.StringVar(value="100")).get(), 100))
    except Exception:
        dpi = 100

    resizable = bool(state.get('resizable_mode_var') and state['resizable_mode_var'].get())

    if not resizable and w_ui and h_ui:
        # convert to inches
        if unit == "mm":
            w_in, h_in = w_ui / 25.4, h_ui / 25.4
        elif unit == "px":
            # pixels -> inches via dpi
            w_in, h_in = w_ui / dpi, h_ui / dpi
        else:  # inches
            w_in, h_in = w_ui, h_ui
        state['desired_fig_spec'] = (w_in, h_in, dpi)
    else:
        # Resizable mode: do not force a desired_fig_spec
        if 'desired_fig_spec' in state:
            del state['desired_fig_spec']

    # Now create and display the figure according to mode/spec
    customize_graph(state)

def gather_data(state):
    """Collect selected entries and load data irrespective of origin (ascii/pdata)."""
    state['file_paths'] = [
        state['workspace_tree'].item(child)["values"][0]
        for child in reversed(state['workspace_tree'].get_children())
    ]
    state['lines'] = []

    # Always plot in the unit currently selected in the UI (template sets this on startup)
    x_unit = (state['x_axis_unit'].get() or "").strip() or "ppm"

    for path in state['file_paths']:
        try:
            # --- decide loader by path, not by preferences ---
            if _is_valid_pdata_dir(path):
                # pdata/<proc> with procs + 1r
                if not HAS_NMRGLUE:
                    messagebox.showerror(
                        "Missing dependency",
                        "This dataset is Bruker pdata, but 'nmrglue' is not installed.\n\n"
                        "Install with:\n    pip install nmrglue"
                    )
                    continue
                x_data, y_data = _load_bruker_pdata(path, x_unit)

            elif path.endswith("ascii-spec.txt"):
                # ascii export
                df = pd.read_csv(path, skiprows=1)
                if x_unit == "ppm":
                    x_col = 3
                elif x_unit in ("Hz", "kHz"):
                    x_col = 2
                else:
                    x_col = 3
                x_data = df.iloc[:, x_col].to_numpy(dtype=float)
                y_data = df.iloc[:, 1].to_numpy(dtype=float)
                if x_unit == "kHz":
                    x_data = x_data / 1000.0

            else:
                # Unknown: skip this item but keep plotting others
                set_status(f"⚠️ Unrecognized dataset in workspace: {os.path.basename(path)}", 6000)
                continue

            # --- X-range cropping: honor "couple x-limits to mask" preference ---
            coupled = app.preferences.get("couple_x_limits", "1") == "1"
            if coupled:
                xmin_str = state['x_min_entry'].get()
                xmax_str = state['x_max_entry'].get()
            else:
                xmin_str = state['x_min_mask_entry'].get()
                xmax_str = state['x_max_mask_entry'].get()

            xmin = float(xmin_str) if xmin_str else float(np.nanmin(x_data))
            xmax = float(xmax_str) if xmax_str else float(np.nanmax(x_data))
            lo, hi = (xmin, xmax) if xmin <= xmax else (xmax, xmin)
            mask = (x_data >= lo) & (x_data <= hi)

            if not np.any(mask):
                set_status(f"⚠️ No points in range [{xmin}, {xmax}] for {os.path.basename(path)}; check X limits.", 6000)
                continue

            x_data = x_data[mask]
            y_data = y_data[mask]

            # Hand off to the same plotting pipeline (normalization handled there)
            state['lines'].append([x_data, y_data])

        except Exception as e:
            set_status(f"⚠️ Failed to load: {os.path.basename(path)}  ({e})", 6000)

def transform_data(state):
    """Transform the data based on user-defined settings (scaling, offsets, etc.)."""
    # --- intensity normalization (if enabled in preferences) ---
    disable_norm = app.preferences.get("disable_int_norm", "0") == "1"
    if not disable_norm:
        for i, line in enumerate(state['lines']):
            y = line[1]
            # Prefer positive max; if not present, fall back to absolute max
            ymax = float(np.max(y)) if np.max(y) > 0 else float(np.max(np.abs(y)))
            if ymax and np.isfinite(ymax):
                line[1] = y / ymax
    scaling_factor_str = state['scaling_factor_entry'].get()
    scaling_factor = safe_float(scaling_factor_str, 1.0)

    x_offset_increment = float(state['x_offset_entry'].get()) if state['x_offset_entry'].get() else 0
    y_offset_increment = float(state['y_offset_entry'].get()) if state['y_offset_entry'].get() else 0
    
    cumulative_y_offset = 0  # Initialize cumulative y-offset for stacking

    for idx, line in enumerate(state['lines']):
        # Apply scaling factor to y-data
        line[1] *= scaling_factor
        
        if state['mode_var'].get().lower() == "overlay":
            # Apply x and y offsets (increases as index increases)
            line[0] += x_offset_increment * idx
            line[1] += y_offset_increment * idx
        elif state['mode_var'].get().lower() == "stack":
            if idx == 0:
                # First line remains at base level
                cumulative_y_offset = max(line[1]) + (y_offset_increment if len(state['lines']) > 1 else 0)
            else:
                # Store original max before modification
                original_max = max(line[1])
                # Apply cumulative offset to current line
                line[1] += cumulative_y_offset
                # Update cumulative offset for the *next* line only (no last spacer)
                if idx < len(state['lines']) - 1:
                    cumulative_y_offset += original_max + y_offset_increment

def _draw_plot_on(ax, state):
    set_axis_limits(state, ax)
    axis_title = get_axis_title(state['nucleus_entry'].get(), state['x_axis_unit'].get())
    set_axis_ticks(state, ax)
    ax.set_facecolor("white")
    ax.figure.set_facecolor("white")
    selected_scheme = state['color_scheme_var'].get()

    # How many lines do we need to color?
    n_lines = max(1, len(state.get('lines', [])))

    if selected_scheme == "Single color — user specified":
        # Reuse your existing validator and entry
        custom_color = state['custom_color_entry'].get()
        if custom_color and validate_color(custom_color):
            colors = [custom_color] * n_lines
        else:
            messagebox.showerror("Error", "Please enter a valid color name or hex code")
            return False
    else:
        # Treat selection as a matplotlib colormap name
        try:
            cmap = mpl.colormaps[selected_scheme]
            # sample evenly across the colormap
            if n_lines == 1:
                colors = [cmap(0.5)]
            else:
                colors = [cmap(i / (n_lines - 1)) for i in range(n_lines)]
        except Exception:
            # fallback if something odd gets loaded from a template
            colors = ["black"] * n_lines

    ax.set_xlabel(axis_title, fontdict={
        'family': state['label_font_type_var'].get() or 'Arial',
        'size'  : float(state['label_font_size_entry'].get()) if state['label_font_size_entry'].get() else 10
    })

    for idx, line in enumerate(state['lines']):
        ax.plot(
            line[0], line[1],
            linewidth=float(state['line_thickness_entry'].get()) if state['line_thickness_entry'].get() else None,
            color=colors[idx],
            clip_on=True
        )

    ax.invert_xaxis()
    return True

def customize_graph(state):
    """Customize and display the graph based on user settings."""
    for f in (state['canvas_holder'], state['toolbar_frame']):
        for child in f.winfo_children():
            child.destroy()

    # Determine whether we're in resizable (live) mode or fixed mode.
    resizable = bool(state.get('resizable_mode_var') and state['resizable_mode_var'].get())

    # If fixed mode, build desired spec from UI and create figure at that physical size
    if not resizable:
        unit = (state.get('fig_size_unit') and state['fig_size_unit'].get()) or "mm"
        w_ui = safe_float(state['fig_w_var'].get(), 85 if unit == "mm" else 3.35)
        h_ui = safe_float(state['fig_h_var'].get(), 60 if unit == "mm" else 2.36)
        dpi  = int(safe_float(state['fig_dpi_var'].get(), 300))
        if unit == "mm":
            w_in, h_in = w_ui / 25.4, h_ui / 25.4
        elif unit == "px":
            w_in, h_in = w_ui / dpi, h_ui / dpi
        else:
            w_in, h_in = w_ui, h_ui
        desired = (w_in, h_in, dpi)
        # create figure at physical size and enable constrained layout so labels never overflow
        fig = plt.Figure(figsize=(w_in, h_in), dpi=dpi, constrained_layout=True)
    else:
        # live/resizable fallback: create on-screen figure with constrained layout so labels
        # are always included and not clipped when it is sized to the window.
        # We use a modest default size; it will be resized to match the canvas content area.
        try:
            fig = plt.Figure(figsize=(8, 6), dpi=100, constrained_layout=True)
        except TypeError:
            # older matplotlib might not accept constrained_layout here; fall back gracefully
            fig = plt.Figure(figsize=(8, 6), dpi=100)
        desired = None

    ax = fig.add_subplot(111)

    # For fixed-sized figures we're using constrained_layout which handles labels.
    if not resizable:
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")
    else:
        # generous padding so labels don't clip in live mode
        try:
            # If constrained_layout is active, subplots_adjust is incompatible and will be skipped.
            if getattr(fig, "get_constrained_layout", lambda: False)():
                # constrained_layout will handle spacing automatically; do nothing here.
                pass
            else:
                fig.subplots_adjust(left=0.06, right=0.94, top=0.94, bottom=0.12)
        except Exception:
            # Be defensive — if anything goes wrong, at least don't crash the GUI.
            pass

    if not _draw_plot_on(ax, state):
        return

    state['current_figure'] = fig
    w_in, h_in = fig.get_size_inches()
    dpi = fig.get_dpi()
    if desired:
        state['desired_fig_spec'] = desired
    else:
        state['desired_fig_spec'] = (w_in, h_in, dpi)

    _bind_holder_resize_once(state)
    _scale_and_place_canvas(state)

    toolbar = CustomNavigationToolbar(state.get('matplotlib_canvas'), state['toolbar_frame'])
    toolbar.update()

def _apply_figure_padding(fig):
    """Apply symmetric padding unless constrained_layout is active.

    If constrained_layout is active, let Matplotlib handle spacing.
    If that layout engine fails (rare), fall back to a sensible subplots_adjust.
    """
    try:
        # If constrained_layout is on, prefer that (it places labels inside)
        if getattr(fig, "get_constrained_layout", lambda: False)():
            # try letting constrained_layout compute the layout; if it fails we will fallback
            try:
                fig.canvas.draw_idle()
                return
            except Exception:
                # fall through to manual subplots_adjust below
                pass

        # Default manual (symmetric) padding for non-constrained figures
        fig.subplots_adjust(left=0.06, right=0.94, top=0.94, bottom=0.12)
    except Exception:
        # defensive no-op: don't crash the UI for layout problems
        try:
            fig.subplots_adjust(left=0.06, right=0.94, top=0.94, bottom=0.12)
        except Exception:
            pass

def _inches_to_units(w_in, h_in, dpi, unit):
    if unit == "mm":
        return w_in * 25.4, h_in * 25.4
    if unit == "px":
        return w_in * dpi, h_in * dpi
    return w_in, h_in  # inches

def get_current_plot_size(state):
    # Only meaningful in resizable/live mode
    if not (state.get('resizable_mode_var') and state['resizable_mode_var'].get()):
        set_plot_status("Get current plot size only available in resizable mode. Toggle 'Resizable figure mode' to use it.", 4000)
        return

    fig = state.get('current_figure')
    if not fig:
        messagebox.showwarning("No plot", "Plot a spectrum first.")
        return

    w_in, h_in = fig.get_size_inches()
    dpi = fig.get_dpi()
    unit = (state.get('fig_size_unit') and state['fig_size_unit'].get()) or "mm"
    w, h = _inches_to_units(w_in, h_in, dpi, unit)
    fmt = (lambda v: f"{v:.0f}") if unit == "px" else (lambda v: f"{v:.2f}")
    state['fig_w_var'].set(fmt(w))
    state['fig_h_var'].set(fmt(h))
    state['fig_dpi_var'].set(str(int(dpi)))
    set_plot_status(f"Captured current plot size: {fmt(w)}×{fmt(h)} {unit} @ {int(dpi)} DPI", 4000)

def _bind_holder_resize_once(state):
    if state.get('_resize_bound'):
        return
    holder = state['canvas_holder']
    def _on_conf(e):
        try:
            _scale_and_place_canvas(state)
        except Exception:
            pass
    holder.bind("<Configure>", _on_conf)
    state['_resize_bound'] = True

def _scale_and_place_canvas(state):
    """Place & size the live figure widget into the canvas_holder.

    - In resizable (live) mode: fill the canvas_holder (minus small symmetric padding).
    - In fixed mode: create the figure at the desired physical size and scale down
      to fit (never scale up).
    """
    fig = state.get('current_figure')
    holder = state.get('canvas_holder')
    if not fig or not holder or not holder.winfo_exists():
        return

    holder.update_idletasks()
    avail_w = max(1, holder.winfo_width())
    avail_h = max(1, holder.winfo_height())

     # determine symmetric padding (in pixels) with a safe fallback
    pad_default = 6
    pad_px = pad_default
    try:
        we = state.get('whitespace_entry', None)
        # handle a few possible types: tk.StringVar, widget with .get(), or raw value
        if isinstance(we, tk.StringVar):
            raw_val = we.get()
        elif hasattr(we, "get") and callable(we.get):
            # could be an Entry widget or similar
            raw_val = we.get()
        else:
            raw_val = we
        # try to coerce to number (allow floats, but use int pixels)
        if raw_val is None:
            pad_px = pad_default
        else:
            pad_px = int(float(raw_val))
            if pad_px < pad_default:
                pad_px = pad_default

    except Exception:
        pad_px = pad_default

    # detect fixed vs resizable mode
    resizable = bool(state.get('resizable_mode_var') and state['resizable_mode_var'].get())

    if not resizable and 'desired_fig_spec' in state:
        # fixed mode: use user's desired physical figure spec (in inches + dpi)
        w_in, h_in, dpi = state['desired_fig_spec']
        des_w_px = max(1, int(round(w_in * dpi)))
        des_h_px = max(1, int(round(h_in * dpi)))

        # available content area after padding
        content_w = max(1, avail_w - 2 * pad_px)
        content_h = max(1, avail_h - 2 * pad_px)

        # scale down if needed (never scale up)
        scale = min(1.0, content_w / des_w_px, content_h / des_h_px)
        disp_w_px = max(1, int(des_w_px * scale))
        disp_h_px = max(1, int(des_h_px * scale))

        # set the figure's on-screen size (in inches)
        fig.set_dpi(dpi)
        fig.set_size_inches(disp_w_px / dpi, disp_h_px / dpi, forward=True)
        view_scale = scale

    else:
        # resizable / live mode: fill the holder (minus padding)
        content_w = max(1, avail_w - 2 * pad_px)
        content_h = max(1, avail_h - 2 * pad_px)

        # set figure size in inches to match the display area (so labels are laid out)
        dpi = fig.get_dpi()
        fig.set_dpi(dpi)
        fig.set_size_inches(content_w / dpi, content_h / dpi, forward=True)

        # we are filling the area; no scaling factor to report (view_scale = 1.0)
        disp_w_px = content_w
        disp_h_px = content_h
        view_scale = 1.0

    # Apply symmetric padding so labels and axis titles are not clipped.
    try:
        _apply_figure_padding(fig)
    except Exception:
        pass

    # ensure we use the same canvas instance when possible
    canvas = state.get('matplotlib_canvas')
    if canvas is None or canvas.figure is not fig:
        canvas = FigureCanvasTkAgg(fig, master=holder)
        state['matplotlib_canvas'] = canvas

    widget = canvas.get_tk_widget()
    holder.pack_propagate(False)  # keep holder size; don't let widget force it

    # center the widget inside the holder and set width/height to disp_* (px)
    widget.place(relx=0.5, rely=0.5, anchor="center", width=disp_w_px, height=disp_h_px)

    # draw
    try:
        canvas.draw()
    except Exception:
        canvas.draw_idle()

    state['view_scale'] = view_scale
    if view_scale < 1.0:
        set_plot_status(f"View scaled to {int(view_scale*100)}% to fit window", 3000)

def set_axis_limits(state, ax):
    """Set the axis limits based on user input."""
    x_min = float(state['x_min_entry'].get()) if state['x_min_entry'].get() else min(state['lines'][-1][0])
    x_max = float(state['x_max_entry'].get()) if state['x_max_entry'].get() else max(state['lines'][0][0])

    ax.set_xlim(x_min, x_max)
    
    y_min = float(state['y_min_entry'].get()) if state['y_min_entry'].get() else 0
    y_max = float(state['y_max_entry'].get()) if state['y_max_entry'].get() else 1

    if state['mode_var'].get() == "stack" and state['y_max_entry'].get() == '':
        y_max = max(state['lines'][-1][1])
    elif state['mode_var'].get() == "overlay" and state['y_max_entry'].get() == '':
        y_max = max(state['lines'][-1][1])

    # Retrieve the whitespace value entered by the user
    whitespace_value = float(state['whitespace_entry'].get()) if state['whitespace_entry'].get() else 0.1

    ax.set_ylim(y_min - whitespace_value, y_max + whitespace_value)

def get_axis_title(nucleus, x_axis_unit):
    """Generate the axis title based on the nucleus and x-axis unit."""
    if not nucleus:
        return

    if x_axis_unit == "ppm":
        unit_string = "Chemical Shift (ppm)"
    elif x_axis_unit == "Hz":
        unit_string = "Frequency (Hz)"
    elif x_axis_unit == "kHz":
        unit_string = "Frequency (kHz)"
    else:
        print("Invalid x-axis unit selection")
        return

    numeric_part = ""
    element_name = ""
    
    for i in range(0, len(nucleus)):
        if nucleus[i].isdigit():
            numeric_part += nucleus[i]
        else:
            element_name += nucleus[i]

    # Use LaTeX syntax for font styling
    title_with_superscript = r"$\mathregular{^{%s}}$%s %s" % (numeric_part, element_name, unit_string)

    return title_with_superscript

def set_axis_ticks(state, ax):
    """Set the axis ticks based on user input."""
    x_ticks_spacing = safe_float(state['major_ticks_freq_entry'].get()) if state['major_ticks_freq_entry'].get() else None
    x_minor_ticks_spacing = safe_float(state['minor_ticks_freq_entry'].get()) if state['minor_ticks_freq_entry'].get() else None

    if x_ticks_spacing is not None:
        ax.xaxis.set_major_locator(ticker.MultipleLocator(x_ticks_spacing))

    if x_minor_ticks_spacing is not None:
        ax.xaxis.set_minor_locator(ticker.MultipleLocator(x_minor_ticks_spacing))

    # Set font properties directly on the x-axis tick labels
    font_properties = {
        # use Axis-font combobox; default to Arial if blank
        'family': state['axis_font_type_var'].get() if state['axis_font_type_var'].get() else 'Arial',
        'size'  : float(state['axis_font_size_entry'].get()) if state['axis_font_size_entry'].get() else 10
    }

    # Hide y-axis ticks and labels
    ax.yaxis.set_major_locator(ticker.NullLocator())
    ax.yaxis.set_minor_locator(ticker.NullLocator())

    # Additional customization

    major_len = safe_float(state['major_ticks_len_entry'].get()) or 4.0
    minor_len = safe_float(state['minor_ticks_len_entry'].get()) or 2.0

    # length & size
    ax.tick_params(axis='x',
                   which='major', length=major_len, labelsize=font_properties['size'])
    ax.tick_params(axis='x',
                   which='minor', length=minor_len, labelsize=font_properties['size'])

    # family
    for lbl in ax.get_xticklabels():
        lbl.set_family(font_properties['family'])

def show_empty_plot(state):
    # clear any old children
    for f in ('canvas_holder', 'toolbar_frame'):
        if f in state and state[f].winfo_exists():
            for c in state[f].winfo_children():
                c.destroy()
    # friendly placeholder
    ph = tk.Canvas(state['canvas_holder'], bg="white")
    ph.pack(fill="both", expand=True)
    ph.create_text(12, 12, anchor="nw",
                   text="Add spectra to the plot workspace and click 'Plot Spectrum'")


def validate_color(color):
    """Validate if the color is a valid name or hex code."""
    try:
        plt.plot([], color=color)
        return True
    except ValueError:
        return False


def export_plot_template(state):
    file = filedialog.asksaveasfilename(
        initialdir=app.preferences["template_dir"], defaultextension='.txt')
    if not file:
        return
    with open(file, 'w', encoding='utf-8') as f:
        EXCLUDE = {"status_var", "tpl_status_var"} 
        for key, widget in state.items():
            if key in EXCLUDE:
                continue
            if isinstance(widget, tk.Entry):
                f.write(f"{key}:{widget.get()}\n")
            elif isinstance(widget, tk.StringVar):
                f.write(f"{key}:{widget.get()}\n")
    set_tpl_status("✅  Template saved")

def import_plot_template(state, initial_dir=None, file_path=None):
    if initial_dir is None:
        initial_dir = app.preferences.get("template_dir", ".")
    # ------------------------------------------------------------------ #
    # 1) get the pathname
    template_path = filedialog.askopenfilename(
        title="Import Template",
        filetypes=[("Text files", "*.txt")],
        initialdir=initial_dir
    )
    if not template_path:                     # user hit “Cancel”
        set_tpl_status("No template file selected")
        return
    # ------------------------------------------------------------------ #
    try:
        # 2) open the file
        with open(template_path, "r", encoding="utf-8") as fh:
            for line_number, line in enumerate(fh, 1):
                if not line.strip():
                    continue

                if ':' not in line:
                    print(f"Warning: Line {line_number} is malformed (missing colon): {line.strip()}")
                    continue

                key, value = line.strip().split(":", 1)
                if not key:                         # allow empty values
                    print(f"Warning: Line {line_number} has empty key: {line.strip()}")
                    continue

                if key in state:
                    if isinstance(state[key], tk.Entry):
                        state[key].delete(0, tk.END)
                        state[key].insert(0, value)
                    elif isinstance(state[key], tk.StringVar):
                        state[key].set(value)
                    elif key not in ['data_tree', 'workspace_tree', 'placeholder_canvas',
                                     'canvas_frame', 'color_schemes']:
                        try:
                            state[key] = value
                        except Exception as e:
                            print(f"Warning: Could not import value for {key}: {str(e)}")
                else:
                    print(f"Warning: Unknown key in settings file: {key}")

        set_tpl_status(f"✅  Template loaded ({os.path.basename(template_path)})")

    except Exception as e:
        set_tpl_status("Failed to load template")
        print(f"Template import error: {e}")

if __name__ == "__main__":
    app = NMRPlotterApp()
    app.mainloop()