NMR Plotter


Description:

A Python application to visualize and analyze NMR spectroscopy data. NMR Plotter will allow users to import, overlay, and customize NMR spectra plots with many differet formatting options.

Features:

-Import multiple NMR data directories
-Stack or overlay multiple spectra
-Customizable plot parameters (fonts, colors, axes, etc.)
-Export and import plot settings
-Interactive plot manipulation
-Support for different frequency units (ppm, Hz, kHz)


Getting Started:

Cloning the repository (get repo url from green button on github that says Code):

git clone [repository-url]
cd NMR-Plotter


Install required packages:

pip install -r requirements.txt


How to Use:

1. Importing Data

-Click the "Add" button in the Data Import section
-Navigate to your NMR data directory
    -Click on the path at the top to go back a folder
    -Click on the arrow next to the directory to go inside (or just double click)
    -Click add selection to add the directory that is currently highlighted
-Select the directories containing your spectra in the Data Import frame and click 'Add Selection'
-The imported directories will appear in the Data Import tree view
-Select the specific spectra you want to analyze (You can select multiple at once)
    -Opening the dropdown will reveal experiment folders and process numbers/experiment numbers
-Click "Add to Workspace" to move them to the workspace

2. Managing the Workspace

Reordering spectra: Use the ↑↓ buttons to change spectrum order
Removing spectra: Select spectra and click "Remove"
Clearing workspace: Click "Clear" to remove all spectra

3. Plot Customization

Basic Parameters

X/Y Axis Limits: Set plot boundaries using X-Min, X-Max, Y-Min, Y-Max
Data Masking: Limit displayed data range using X-Min Mask and X-Max Mask

Display Mode: Choose between "stack" or "overlay" modes

Stack: Spectra are stacked vertically
Overlay: Spectra are superimposed

Visual Customization

Colors: Select from predefined schemes or use custom colors
Fonts: Customize font type and size for axes and labels
Line Properties: Adjust line thickness
Scaling: 
Spacing: Control spectrum spacing with Y-Offset
Ticks: Adjust major/minor tick spacing and length

Units and Labels

X-Axis Units: Choose between ppm, Hz, or kHz
Nucleus: Specify the nucleus (e.g., "1H", "13C", "31P")

4. Plotting

Configure desired parameters in the Customization section
Click "Plot Data" to generate the plot
Use the Matplotlib toolbar to:

Pan and zoom
Save plot as image
Reset view
Adjust plot layout


5. Saving/Loading Settings

Export Settings: Click "Export" to save current plot parameters
Import Settings: Click "Import" to load previously saved parameters


Common Issues:

-Make sure to enter a unit before plotting
-Make sure to save export files as .txt files


NMR data should be in Bruker format
Required file structure:
data_dir/
├── exp_folder/
|   |__1/  
│      └── pdata/
│            └── 1/
│                └── ascii-spec.txt




Troubleshooting:

-Check the Visual Studio Code terminal for any errors that appear
-Ask Mithun or Aiden!