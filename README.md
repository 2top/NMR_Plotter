NMR_Plotter

NMR_Plotter is a lightweight Python/Tkinter app for scanning, previewing, styling, and exporting 1D NMR spectra—built for a streamlined Bruker → NMR_Plotter → vector graphics workflow (e.g., Adobe Illustrator, Inkscape). It supports both TopSpin ascii-spec.txt exports and direct Bruker pdata (1r/procs) via nmrglue, with identical plotting behavior either way.

    Browse large collections of processed datasets

    Add spectra to a workspace and reorder

    Mask x-ranges; set units (ppm/Hz/kHz), ticks, fonts, colors

    Toggle overlay vs stack layouts, with x/y offsets

    Save/load style templates for group “house styles”

    Export publication-quality PDF/SVG/PNG/PS/EPS

    Optional fixed-size export (width/height/DPI) for exact figure dimensions

Table of contents

    Install Python (Windows/macOS/Linux)

    Install NMR_Plotter

    Launch

    Data sources: ascii vs pdata

    Typical workflow

    Plotting parameters

    Overlay vs Stack (how traces are shifted)

    Preferences (all options)

    Templates (style presets)

    Scanning, workspace, & caching

    Exporting figures

    Troubleshooting

    Notes

    Citation

    License

Install Python (Windows/macOS/Linux)
Windows

    Download Python 3.12+ from https://www.python.org/downloads/windows/

    Run the installer and check “Add Python to PATH.”

    Open Command Prompt and verify:

    python --version

    Tkinter is included with the official installer—no extra steps.

macOS

    Download the macOS universal2 installer (3.12+) from https://www.python.org/downloads/macos/

    Run the .pkg installer.

    Open Terminal and verify:

    python3 --version

    Tkinter is included with the official python.org installer.

Linux

Install Python, venv, and Tkinter using your package manager, e.g.:

    Ubuntu/Debian

sudo apt update
sudo apt install -y python3 python3-venv python3-pip python3-tk

Fedora

sudo dnf install -y python3 python3-pip python3-tkinter

Arch

    sudo pacman -S --needed python tk

Verify:

python3 --version

Install NMR_Plotter

# 1) Get the code
git clone https://github.com/2top/NMR_Plotter
cd NMR_Plotter

# 2) (Recommended) Create and activate a virtual environment
# Windows (CMD/PowerShell)
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate

# 3) Install dependencies
pip install -r requirements.txt

# 4) (Optional, for pdata support) Install nmrglue
pip install nmrglue

    If pip says it can’t find Tkinter, install your OS package (see above) or use the python.org installer for Windows/macOS.

Launch

From the project folder (with your virtual environment activated, if using one):

# Windows
python NMR_Plotter.py

# macOS/Linux
python3 NMR_Plotter.py

The main window contains:

    Data Import (scan folders, build a pick-list)

    Plot Workspace (spectra you’ll actually plot; reorderable)

    Actions (Plot, Import Template, Save Template, Preferences)

    Plot (Matplotlib canvas + toolbar)

    Plotting Parameters (axis, ticks, fonts, colors, offsets, export size)

Data sources: ascii vs pdata
A) TopSpin ascii-spec.txt (simple on-ramp)

Export processed spectra from TopSpin (e.g., AU convbin2asc). Typical Bruker layout:

<project_root>/<sample>/<expno>/pdata/<procno>/ascii-spec.txt

In ascii mode, NMR_Plotter scans for ascii-spec.txt leaves under the directory you choose and lists only those leaves—keeping the import experience clean.
B) Direct Bruker pdata via nmrglue

Switch Preferences → Import data using → “pdata (nmrglue)”. The app finds valid pdata/<procno> directories that contain procs and 1r, and lists them as “Expt N, proc M.”

x-axis construction (pdata):

    Uses Bruker parameters from procs:

        OFFSET (ppm at the leftmost point)

        SW_p (spectral width in Hz)

        SF (spectrometer frequency, MHz; falls back to acqus if needed)

    Units ppm/Hz/kHz are supported; kHz divides the Hz axis by 1000.

    The ppm axis is automatically displayed right-to-left (decreasing ppm).

    Parity: Whether you load ascii or pdata, the same masking, normalization, scaling, offsets, and styling are applied, so results match across sources.

Typical workflow

    Add New Dir and select a folder containing Bruker data.

        ascii mode → lists ascii-spec.txt leaves.

        pdata mode → lists valid pdata/<proc> leaves with procs+1r.

    Select items in Data Import and Add to Plot Workspace.
    Reorder with ↑/↓; remove items or clear all as needed.

    Set units, x-limits (and mask), nucleus, ticks, fonts, colors, mode, offsets, etc.

    Click Plot Spectrum.

    Save Current as Template (optional) to reuse your style.

    Export via the toolbar (PDF/SVG/PNG/PS/EPS). Use fixed size or WYSIWYG (see Preferences).

Plotting parameters

Units & limits

    X-Axis Unit: ppm, Hz, or kHz.

        ascii: ppm uses the ppm column; Hz/kHz use the frequency column (kHz divides by 1000).

        pdata: derived from Bruker parameters; ppm axis is inverted.

    X-Min / X-Max: visible x-range.

    X-Min Mask / X-Max Mask: crop window (see “Couple x-limits” under Preferences).

    Y-Min / Y-Max: vertical range; leave blank to auto-fit.

    Whitespace: extra vertical padding applied to ylim.

Labels & fonts

    Nucleus: label uses a superscript (e.g., 13C) plus unit, e.g., “Chemical Shift (ppm)”.

    Axis Label Font and Tick Label Font: family & size for x-label and tick labels (y-axis ticks are hidden for clean 1D figures).

Ticks

    Major/Minor Spacing: numeric values (e.g., 10 ppm major, 2 ppm minor).

    Major/Minor Length: tick lengths in points.

Lines & colors

    Line Thickness: linewidth for all traces.

    Color Scheme: preset palette or Custom (color name or hex).

Mode & offsets

    Mode: overlay or stack.

    X/Y Offset: applied per-trace; see below.

Export size (UI controls)

    Units: mm, in, or px.

    Width / Height / DPI: for fixed-size export.

    Get current plot size: copies the canvas size to W/H/DPI fields.

Overlay vs Stack (how traces are shifted)

After loading and x-masking, each trace is optionally normalized (see Preferences), then transformed:

    Normalization (default ON): each trace is divided by its maximum positive value (falls back to absolute max if needed).

    Scaling Factor: multiplies intensities after normalization (or raw if normalization is disabled).

Overlay

    For the i-th trace (0-indexed), apply:

        x_i ← x_i + i * x_offset

        y_i ← y_i + i * y_offset

    This makes “diagonal overlays” trivial (e.g., VT or kinetic series).

Stack

    The first trace stays at base.

    Each subsequent trace is shifted upward by the cumulative height of the previous trace(s) plus the user’s y_offset spacing.

    This yields evenly separated stacks that respect each spectrum’s natural height.

Preferences (all options)

Preferences are saved to preferences.txt (alongside the app) and loaded on startup.

    Default starting directory for data import

    Default directory for plot templates

    Default plot template file

        If set, this template auto-loads on startup.

    Default directory to save figures

    Couple x-masking limits to x-limits

        ON (default): mask uses current X-Min/X-Max; mask fields are disabled and mirror x-limits.

        OFF: mask fields are independent; you can crop data outside the visible range.

    Disable intensity normalization

        When ON, plots use raw intensities. Consider setting a Scaling Factor (e.g., 1e-10) for Bruker’s large absolute values.

    Export figure using fixed, specified dimensions

        ON: exports use W/H/DPI fields.

        OFF (WYSIWYG): exports at the current on-screen canvas size.

    Import data using

        ascii-spec.txt or pdata (nmrglue).

        Controls how Add New Dir scans and which cache file is used (cache.txt vs cache_pdata.txt).

Templates (style presets)

Templates are simple key:value text files that map onto the plotting controls. Example:

x_axis_unit: ppm
x_min_entry: -10
x_max_entry: 200
x_min_mask_entry: -10
x_max_mask_entry: 200
y_min_entry: 0
y_max_entry: 1
mode_var: overlay
x_offset_entry: 0
y_offset_entry: 0
nucleus_entry: 13C
color_scheme_var: Default
custom_color_entry: Black
axis_font_type_var: Arial
axis_font_size_entry: 16
label_font_type_var: Arial
label_font_size_entry: 18
line_thickness_entry: 1
scaling_factor_entry: 1
whitespace_entry: 0.05
major_ticks_freq_entry: 20
minor_ticks_freq_entry: 5
major_ticks_len_entry: 7
minor_ticks_len_entry: 3
fig_size_unit: mm
fig_w_var: 85
fig_h_var: 60
fig_dpi_var: 300

    Import Template: loads values into the UI immediately.

    Save Current as Template: writes the current UI state to a .txt.

    Loader ignores blank lines and warns on malformed entries without crashing.

    Great for enforcing lab or journal “house styles.”

Scanning, workspace, & caching

    Add New Dir performs a guarded recursive scan suited to your Import Mode:

        ascii → collects ascii-spec.txt leaves only.

        pdata → collects pdata/<proc> directories containing procs + 1r.

    The Data Import tree groups entries by top folder and sample, and renders leaves as either the file (ascii-spec.txt) or “Expt N, proc M.”

    Add to Plot Workspace moves selected leaves into the plot list; reorder with ↑/↓.

    Load Cached Scan re-loads the last scan quickly:

        ascii cache: cache.txt

        pdata cache: cache_pdata.txt

    Remove Dir (removes a scanned root) and Clear all (workspace) help keep things tidy.

Exporting figures

Use the Matplotlib toolbar Save button.

Formats: PDF, SVG, PNG, PS, EPS
Export directory: defaults to your figure save preference.

Fixed size (recommended for manuscripts):

    Enable Export figure using fixed, specified dimensions in Preferences.

    Set Units (mm/in/px), Width, Height, DPI in Plotting Parameters.

    Export—figures are rendered at those dimensions with Illustrator-friendly settings (text remains selectable, transparency avoided, line clipping disabled).

WYSIWYG:

    Disable the fixed-size option to export at the on-screen canvas size (same Illustrator-friendly settings).

Troubleshooting

    pdata option missing or errors

        Install nmrglue:

        pip install nmrglue

        Or switch Import Mode to ascii-spec.txt.

    “No datasets found” after scanning

        Ensure you selected the correct level in the directory tree.

        ascii mode: the app looks specifically for .../pdata/<proc>/ascii-spec.txt.

        pdata mode: looks for .../pdata/<proc> folders with procs + 1r.

    Empty plot after masking

        Verify that x-mask overlaps your data.

        Turn Couple x-limits ON to tie mask to visible limits.

    Custom color not applied

        Use a valid color name (e.g., crimson) or hex (e.g., #d62728).

    Fonts look different

        Use common fonts installed on your OS; otherwise matplotlib/Tk may substitute.

    Tkinter not found

        Install OS packages (see install section) or use the python.org installers (Windows/macOS include Tkinter).

Notes

    The ppm axis is automatically displayed high→low (right-to-left).

    y-axis ticks are hidden by design for clean 1D figures.

    Normalization can be disabled globally in Preferences; otherwise each trace is normalized per spectrum before scaling.

    A default template (if set in Preferences) auto-loads on startup.

Citation

If you use NMR_Plotter in a publication, please cite the repository. A JORS software metapaper is in preparation.
License

See the repository for licensing.