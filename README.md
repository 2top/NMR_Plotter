NMR_Plotter

NMR_Plotter is a Python/Tkinter application for quickly scanning, previewing, and plotting processed NMR spectra that have been exported from TopSpin with the AU program convbin2asc.

It is designed to let you:

    Browse large collections of processed NMR datasets

    Add selected spectra to a plotting workspace

    Quickly adjust plot appearance and scaling

    Save/load plotting templates

    Export publication-quality figures (PDF, PNG, etc.)

1. Installing NMR_Plotter
Step 1 — Download the program

    Go to https://github.com/2top/NMR_Plotter.

    Click Code ▸ Download ZIP (or use git clone if you’re comfortable with Git).

    Extract the ZIP somewhere convenient (e.g., your Documents folder).

Step 2 — Install Python (if you don’t already have it)

    Windows:

        Download the latest Python 3.x installer from https://www.python.org/downloads/.

        Run the installer and check the box “Add Python to PATH” before clicking Install Now.

    macOS:
    Install via Homebrew (brew install python) or from the Python.org downloads page.

    Linux:
    Use your package manager, e.g. sudo apt install python3 python3-tk pip.

Tkinter comes with most Python installations. If you get an error about tkinter missing, install it via your package manager (sudo apt install python3-tk, etc.).
Step 3 — Install required Python packages

Open a terminal/command prompt in the NMR_Plotter folder and run:

pip install pandas matplotlib

2. Preparing your NMR data

NMR_Plotter works with ascii-spec.txt files created by TopSpin’s convbin2asc AU program.

For each processed dataset you want to plot:

    In TopSpin, process your spectrum normally (.fid → pdata).

    Load the processed dataset.

    Run convbin2asc in TopSpin (e.g., type convbin2asc in the command line).

    This writes an ascii-spec.txt file into:

    /path/to/sample_name/expno/pdata/procno/ascii-spec.txt

    where:

        sample_name is your dataset folder

        expno is the experiment number (numeric)

        procno is the processed data number (numeric)

Keep your processed datasets in a parent directory so the structure looks like:

ParentDirectory/
    SampleA/
        1/
            pdata/
                1/
                    ascii-spec.txt
    SampleB/
        2/
            pdata/
                1/
                    ascii-spec.txt
    ...

3. Launching NMR_Plotter

In a terminal/command prompt, navigate to the NMR_Plotter folder and run:

python NMR_Plotter.py

The main window will open.
4. Workflow and GUI Overview
Data Import (upper-left frame)

    Add New Dir — Choose a top-level folder containing your processed sample folders (as above).

        The program validates the structure and lists all ascii-spec.txt files found under that top-level.

        This also updates the cache (last_scan.txt) so you can reload without rescanning.

    Load Cached Scan — Reloads previously scanned top-level directories from last_scan.txt.

    Remove Dir — Removes the selected top-level directory from the list.

    Clear All — Removes all top-level directories from the list.

    Add to Plot Workspace — Adds the currently selected spectrum(s) (leaf nodes in the tree) to the Plot Workspace.

A status bar below shows scan progress or warnings.
Plot Workspace (middle-left frame)

    Lists spectra you have queued for plotting.

    ↑ / ↓ — Reorder the spectra.

    Remove — Delete the selected spectrum from the workspace.

    Clear — Empty the workspace.

    Plot Spectrum — Plots all spectra currently in the workspace according to the Plotting Parameters.

        Disabled until at least one spectrum is added.

Templates and Preferences (lower-left frame)

    Import Template — Load a saved plot style/template file (.txt). Updates plotting parameter fields immediately.

    Save Current as Template — Save the current plotting parameter values to a .txt template.

    Preferences — Set default directories (import, templates, save-figures), default template file, and toggle features:

        Couple x-mask to x-limits

        Disable intensity normalization
        Saved to preferences.txt in the program folder.

Plot Area (right frame)

Shows the Matplotlib plot when you press Plot Spectrum.
A toolbar below the plot allows panning, zooming, and saving the figure:

    The Save button starts in the directory specified in Preferences → Default directory to save figures.

Plotting Parameters (bottom frame)

Every field updates how the spectra are plotted:

    X-Axis Unit: ppm, Hz, or kHz (selects column from ascii-spec.txt).

    X-Min / X-Max: Visible x-axis limits.

    X-Min Mask / X-Max Mask: Masking region (used if “couple” is off).

    Nucleus: e.g., 13C (adds superscript to axis label).

    Y-Min / Y-Max: Vertical limits.

    Scaling Factor: Multiply intensities by this factor.

    Whitespace: Extra vertical space above/below traces.

    Axis Label Font Type/Size: Controls font for axis labels.

    Line Thickness: Width of plot lines.

    Color Scheme: Choose preset or Custom (enter color name/hex in Custom Color).

    Tick Label Font Type/Size: Controls font for tick labels.

    Mode: stack or overlay spectra.

    X/Y Offset: Shift spectra horizontally/vertically (increment per spectrum).

    Major/Minor Ticks Spacing: Tick intervals.

    Major/Minor Ticks Length: Tick mark lengths.

5. Typical Usage Example

    Scan your data

        Click Add New Dir, choose the parent folder with your processed samples.

        Data Import tree will show samples → experiments → proc levels.

    Select spectra to plot

        Expand the tree, click the desired leaf (Expt N, proc M).

        Click Add to Plot Workspace.

    Plot

        Click Plot Spectrum in the Plot Workspace frame.

        Adjust any Plotting Parameters and click Plot Spectrum again to refresh.

    Save style (optional)

        Click Save Current as Template to save your plotting settings.

    Reuse style

        Later, click Import Template to reload those settings.

    Export figure

        Use the Matplotlib toolbar’s Save button to save as PDF, PNG, etc.
        The default folder is set in Preferences.

6. File Behavior

    preferences.txt — Stores your Preferences dialog choices; created automatically if missing.

    last_scan.txt — Stores lists of spectra found in scanned directories; created on first successful scan.

    plot_templates/ — Where your template .txt files can live (default location in Preferences).


Troubleshooting:

-Check the Visual Studio Code terminal for any errors that appear
-Contact Tom, Mithun, or Aidan for help!