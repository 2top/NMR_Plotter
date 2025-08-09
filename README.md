# NMR_Plotter

NMR_Plotter is a lightweight Python/Tkinter app for scanning, styling, and exporting **1D NMR spectra**. It is designed for a simple **Bruker TopSpin → NMR_Plotter → vector graphics** workflow (Adobe Illustrator, Inkscape). It can take exported `ascii-spec.txt` files (from the TopSpin AU program convbin2asc) or work directly with **pdata** (`1r` / `procs`) via `nmrglue`, with identical plotting behavior either way.

- Browse large collections of processed datasets
- Add spectra to a workspace and reorder them
- Mask x-ranges; set units (ppm/Hz/kHz); control ticks, fonts, colors
- Switch between **overlay** and **stack** layouts; apply **x/y offsets**
- Save and load **style templates** for lab “house styles”
- Export **PDF, SVG, PNG, PS, EPS**
- Optional **fixed-size export** (width/height/DPI) for exact figure dimensions


---

## Table of contents

1. Install Python (Windows, macOS, Linux)  
2. Install NMR_Plotter  
3. Launch  
4. Data sources: ascii vs pdata  
5. Typical workflow  
6. Plotting parameters  
7. Overlay vs Stack (how traces are shifted)  
8. Preferences (all options)  
9. Templates (style presets)  
10. Scanning, workspace, and caching  
11. Exporting figures  
12. Troubleshooting  
13. Notes  
14. Citation  
15. License


---

## 1) Install Python (Windows, macOS, Linux)

### Windows
1) Download Python 3.12+ from: https://www.python.org/downloads/windows/  
2) Run the installer and **check** the box “Add Python to PATH”.  
3) Open **Command Prompt** and verify:
```
python --version
```

### macOS
1) Download the macOS **universal2** installer (3.12+) from: https://www.python.org/downloads/macos/  
2) Run the `.pkg` installer.  
3) Open **Terminal** and verify:
```
python3 --version
```

### Linux
Install Python, venv, pip, and Tkinter using your package manager.

Ubuntu/Debian:
```
sudo apt update
sudo apt install -y python3 python3-venv python3-pip python3-tk
```

Fedora:
```
sudo dnf install -y python3 python3-pip python3-tkinter
```

Arch:
```
sudo pacman -S --needed python tk
```

Verify:
```
python3 --version
```


---

## 2) Install NMR_Plotter

```
# 1) Get the code
git clone https://github.com/2top/NMR_Plotter
cd NMR_Plotter

# 2) (Recommended) Create and activate a virtual environment
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate

# 3) Install dependencies
pip install -r requirements.txt

# 4) (Optional, for pdata support) Install nmrglue
pip install nmrglue
```

If pip reports that Tkinter is missing, install it using your OS package manager (Linux) or install Python from python.org (Windows/macOS include Tk/Tkinter by default).


---

## 3) Launch

From the project folder (activate your virtual environment first if you created one):

```
# Windows
python NMR_Plotter.py

# macOS/Linux
python3 NMR_Plotter.py
```

Main window sections:
- **Data Import** (scan folders, build a pick-list)
- **Plot Workspace** (spectra to plot; reorderable)
- **Actions** (Plot, Import Template, Save Template, Preferences)
- **Plot** (Matplotlib canvas + toolbar)
- **Plotting Parameters** (axis, ticks, fonts, colors, offsets, export size)


---

## 4) Data sources: ascii vs pdata

### A) TopSpin `ascii-spec.txt` (simple on-ramp)
Export processed spectra from TopSpin (e.g., AU `convbin2asc`). Typical Bruker layout:
```
<project_root>/<sample>/<expno>/pdata/<procno>/ascii-spec.txt
```
In **ascii** mode, NMR_Plotter scans for `ascii-spec.txt` leaves under the directory you choose and lists **only those leaves**—keeping the import experience clean.

### B) Direct Bruker **pdata** via `nmrglue`
Switch **Preferences → Import data using → “pdata (nmrglue)”**. The app finds valid `pdata/<procno>` directories that contain **`procs`** and **`1r`**, and lists them as **“Expt N, proc M.”**

**x-axis construction (pdata):**
- Uses Bruker parameters from `procs`:
  - `OFFSET` (ppm at the leftmost point)
  - `SW_p` (spectral width in Hz)
  - `SF` (spectrometer frequency, MHz; falls back to `acqus` if needed)
- Supports units **ppm/Hz/kHz**; `kHz` divides the Hz axis by 1000.
- The ppm axis is automatically displayed high→low (right-to-left).

**Parity:** Whether you load ascii or pdata, the same masking, normalization, scaling, offsets, and styling are applied, so results match across sources.


---

## 5) Typical workflow

1) **Add New Dir** and select a folder containing Bruker data.  
   - **ascii mode** → lists `ascii-spec.txt` leaves only.  
   - **pdata mode** → lists valid `pdata/<proc>` leaves with `procs` + `1r`.
2) Select items in **Data Import** and **Add to Plot Workspace**.  
   Reorder with ↑/↓; remove items or clear all as needed.
3) Set **units**, **x-limits** (and mask), **nucleus**, **ticks**, **fonts**, **colors**, **mode**, **offsets**, etc.
4) Click **Plot Spectrum**.
5) **Save Current as Template** (optional) to reuse your style.
6) **Export** via the toolbar (PDF/SVG/PNG/PS/EPS). Use **fixed size** or **WYSIWYG** (see Preferences).


---

## 6) Plotting parameters

**Units & limits**
- **X-Axis Unit:** `ppm`, `Hz`, or `kHz`.
  - ascii: `ppm` uses the ppm column; `Hz/kHz` use the frequency column (`kHz` divides by 1000).
  - pdata: derived from Bruker parameters; ppm axis is inverted.
- **X-Min / X-Max:** visible x-range.
- **X-Min Mask / X-Max Mask:** crop window (see “Couple x-limits” under Preferences).
- **Y-Min / Y-Max:** vertical range; leave blank to auto-fit.
- **Whitespace:** extra vertical padding added to `ylim`.

**Labels & fonts**
- **Nucleus:** label uses a superscript (e.g., `13C`) and the unit, e.g., “Chemical Shift (ppm)”.
- **Axis Label Font** and **Tick Label Font:** family & size for x-label and tick labels (y-axis ticks are hidden for clean 1D figures).

**Ticks**
- **Major/Minor Spacing:** numeric values for `MultipleLocator`.
- **Major/Minor Length:** tick lengths in points.

**Lines & colors**
- **Line Thickness:** linewidth for all traces.
- **Color Scheme:** preset palette or **Custom** (color name or hex).

**Mode & offsets**
- **Mode:** `overlay` or `stack`.
- **X/Y Offset:** per-trace increments (details below).

**Export size (UI controls)**
- **Units:** `mm`, `in`, or `px`.
- **Width / Height / DPI:** used when **fixed-size export** is enabled.
- **Get current plot size:** copies the canvas size to the W/H/DPI fields.


---

## 7) Overlay vs Stack (how traces are shifted)

After loading and applying the x-mask, each trace is optionally **normalized** (see Preferences), then transformed:

- **Normalization (default ON):** each trace is divided by its maximum **positive** value (falls back to absolute max if necessary).
- **Scaling Factor:** multiplies intensities after normalization (or the raw intensities if normalization is disabled).

**Overlay**
- For the *i*-th trace (0-indexed), apply:
  - `x_i = x_i + i * x_offset`
  - `y_i = y_i + i * y_offset`
- This makes “diagonal overlays” trivial (e.g., VT/kinetic series).

**Stack**
- The first trace stays at base.
- Each subsequent trace is shifted upward by the **cumulative** height of the previous trace(s) **plus** the user’s `y_offset` spacing.
- This produces evenly separated stacks that respect each spectrum’s natural height.


---

## 8) Preferences (all options)

Preferences are saved to `preferences.txt` (next to the app) and loaded on startup.

Paths:
- **import_dir** — default starting directory for data import
- **template_dir** — default directory for plot templates
- **default_template** — template file to auto-load on startup (optional)
- **figure_save_dir** — default directory to save figures

Toggles/mode:
- **couple_x_limits** (`1` or `0`) — when `1` (default), the **x-mask** is tied to **X-Min/X-Max**; when `0`, mask fields are independent.
- **disable_int_norm** (`1` or `0`) — when `1`, use raw intensities (consider a small **Scaling Factor** for Bruker’s large numbers).
- **import_mode** (`ascii` or `pdata`) — controls how **Add New Dir** scans and which cache file is used.
- **export_use_fixed_size** (`1` or `0`) — when `1` (default), exports use W/H/DPI; when `0`, exports are WYSIWYG.

These can be edited in the **Preferences** dialog or in `preferences.txt` directly.


---

## 9) Templates (style presets)

Templates are simple `key:value` text files that map onto the plotting controls. Example:

```
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
```

- **Import Template**: loads values into the UI immediately.
- **Save Current as Template**: writes the current UI state to a `.txt`.
- Loader ignores blank lines and warns on malformed entries without crashing.
- Great for enforcing lab or journal “house styles.”


---

## 10) Scanning, workspace, and caching

- **Add New Dir** performs a guarded recursive scan suited to your **Import Mode**:
  - **ascii** → collects `ascii-spec.txt` leaves only.
  - **pdata** → collects `pdata/<proc>` directories containing `procs` + `1r`.
- The **Data Import** tree groups entries by top folder and sample, and renders leaves as either the file (`ascii-spec.txt`) or **“Expt N, proc M.”**
- **Add to Plot Workspace** moves selected leaves into the plot list; reorder with ↑/↓.
- **Load Cached Scan** re-loads the last scan quickly:
  - **ascii cache:** `cache.txt`
  - **pdata cache:** `cache_pdata.txt`
- **Remove Dir** (removes a scanned root) and **Clear** (workspace) help keep things tidy.


---

## 11) Exporting figures

Use the Matplotlib toolbar **Save** button.

**Formats:** PDF, SVG, PNG, PS, EPS  
**Export directory:** defaults to your **figure save** preference.

**Fixed size (recommended for manuscripts):**
1) Enable **Export figure using fixed, specified dimensions** in Preferences.  
2) Set **Units (mm/in/px), Width, Height, DPI** in Plotting Parameters.  
3) Export — figures are rendered at those dimensions with Illustrator-friendly settings (text remains selectable, transparency avoided, line clipping disabled).

**WYSIWYG:**
- Disable the fixed-size option to export at the on-screen canvas size (same Illustrator-friendly settings).


---

## 12) Troubleshooting

- **pdata option missing or error**
  - Install `nmrglue`:
    ```
    pip install nmrglue
    ```
  - Or switch Import Mode to `ascii-spec.txt`.

- **“No datasets found” after scanning**
  - Ensure you selected the correct **level** in the directory tree.
  - ascii mode: the app looks for `.../pdata/<proc>/ascii-spec.txt`.
  - pdata mode: the app looks for `.../pdata/<proc>` folders with `procs` and `1r`.

- **Empty plot after masking**
  - Verify that **x-mask** overlaps your data.
  - Turn **Couple x-limits** ON to tie mask to visible limits.

- **Custom color not applied**
  - Use a valid color name (e.g., `crimson`) or hex (e.g., `#d62728`).

- **Fonts look different**
  - Use common fonts installed on your OS; otherwise matplotlib/Tk may substitute.

- **Tkinter not found**
  - Install OS packages (see install section) or use the python.org installers (Windows/macOS include Tkinter).


---

## 13) Notes

- The ppm axis is displayed high→low (right-to-left).  
- Y-axis ticks are hidden by design for clean 1D figures.  
- Normalization is enabled by default; turn it off in Preferences if you prefer raw intensities.  
- A default template (if set in Preferences) auto-loads on startup.


---

## 14) Citation

If you use NMR_Plotter in a publication, please cite the repository. A Journal of Open Research Software (JORS) software metapaper is in preparation.


---

## 15) License

See the repository for licensing.