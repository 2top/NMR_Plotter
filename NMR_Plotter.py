#TODO: idk if the fonts of the axis numbers are actually changing

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import platform
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib import ticker


# Directory selection function (from Stack Overflow)
def askopennames(initialDir='.'):
    if not initialDir:
        return ('', [])
    
    curdir = [initialDir]
    returnList = []
    
    top = tk.Toplevel()
    top.title("Select Directories")
    top.columnconfigure(0, weight=1)
    
    add_btn = tk.Button(top, text="Add Selection")
    tree = ttk.Treeview(top, height=17)
    tree.grid(row=0, sticky='nsew')
    add_btn.grid(row=1, sticky='ew')

    def build_tree(dir):
        """Rebuild the tree view from the current directory."""
        tree.delete(*tree.get_children())  # Clear existing entries
        
        updir = os.path.join(os.path.abspath(dir), '..')
        
        def go_updir():
            """Navigate to the parent directory."""
            p = os.path.abspath(updir)
            dnp = os.path.dirname(updir)
            retdir = filedialog.askdirectory(initialdir=dnp) if os.path.samefile(p, dnp) and platform.system() == 'Windows' else p
            curdir[0] = retdir if retdir else dnp
            build_tree(curdir[0])
        
        tree.heading('#0', text=f"Current Directory: {updir}", anchor='w', command=go_updir)
        
        for c in os.listdir(dir):
            path = os.path.join(dir, c)
            iid = tree.insert('', 'end', text=c, open=False)
            if os.path.isdir(path):
                tree.insert(iid, "end")
    
    def get_selection():
        """Retrieve selected items and add them to the return list."""
        selected_items = tree.selection()
        for s in selected_items:
            item_path = os.path.join(curdir[0], tree.item(s)['text'])
            if os.path.isdir(item_path):
                returnList.append(item_path)
        top.quit()  # Close the dialog

    def rebuild_tree(e):
        """Rebuild tree when a directory is opened."""
        folder = tree.item(tree.focus())['text']
        curdir[0] = os.path.join(curdir[0], folder)
        build_tree(curdir[0])
    
    tree.bind('<<TreeviewOpen>>', rebuild_tree)
    add_btn['command'] = get_selection
    
    build_tree(initialDir)
    top.mainloop()
    top.destroy()
    
    return returnList


def add_dirs(tree):
    """Import directories, update existing_data, and populate the Treeview."""
    global existing_data  # Access the global variable

    # Ask user for directories to import
    dirs = askopennames(initialDir="../../../General/Code_and_Simulations/NMR_plot_python/older_versions/NMR_Plotting_MATLAB_old")
    new_data = {}
    for dir in dirs:
        new_data.update(traverse_directory(dir))

    # Merge new data into the global existing_data
    for key, value in new_data.items():
        if key in existing_data:
            # Merge sub-dictionaries if needed
            existing_data[key].update(value)
        else:
            existing_data[key] = value

    # Update the treeview with the combined data
    populate_treeview(tree, existing_data)


def traverse_directory(root_dir):
    """Traverse a directory and organize experiment data."""
    result = {}
    
    for root, dirs, files in os.walk(root_dir):
        # Skip hidden directories and files
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        files = [f for f in files if not f.startswith('.')]

        # Determine the relative path and its components
        rel_path = os.path.relpath(root, root_dir)
        parts = rel_path.split(os.sep)

        if len(parts) == 1:  # Experiment folder level
            experiment_folder = parts[0]
            if experiment_folder not in result:
                result[experiment_folder] = {}  # Initialize the folder in the result
        elif "ascii-spec.txt" in files:  # Valid data condition
            proc_num = extract_process_number(root)
            exp_num = extract_experiment_number(root)
            combined_key = f"Proc {proc_num}, Expt {exp_num}"
            
            experiment_folder = parts[0]
            result[experiment_folder][combined_key] = os.path.join(root, "ascii-spec.txt")

    # Sort the keys by proc_num and then by expt_num
    for experiment_folder in result:
        sorted_keys = sorted(
            result[experiment_folder].keys(),
            key=lambda x: (
                int(x.split()[1].replace(",", "")),  # Extract proc_num and remove comma
                int(x.split()[3])  # Extract expt_num
        ))
        result[experiment_folder] = {k: result[experiment_folder][k] for k in sorted_keys}

    # Remove experiment folders that have no valid children
    valid_result = {
        folder: children
        for folder, children in result.items()
        if children  # Keep only folders with valid child nodes
    }
    
    return {os.path.basename(root_dir): valid_result}


def extract_process_number(dir_path):
    """Extract the process number from a directory path."""
    parts = dir_path.split(os.sep)
    return parts[-3]


def extract_experiment_number(dir_path):
    """Extract the experiment number from a directory path."""
    parts = dir_path.split(os.sep)
    return parts[-1]


def populate_treeview(tree, data):
    """Populate the Treeview with hierarchical data."""
    def insert_items(parent, items):
        for key, value in items.items():
            if not key or key in ('.', '..'):  # Skip invalid entries
                continue
            if isinstance(value, dict):
                # Folder node
                node = tree.insert(parent, "end", text=key, values=(key,))
                insert_items(node, value)
            else:
                # Leaf node
                tree.insert(parent, "end", text=key, values=(value,))
    
    tree.delete(*tree.get_children())
    insert_items('', data)


def add_to_workspace(data_tree, workspace_tree):
    """Add selected items from the data tree to the workspace tree."""
    selected_items = data_tree.selection()
    if not selected_items:
        print("No items selected")
        return
    
    for s in selected_items:
        if data_tree.get_children(s):
            print(f"Item {data_tree.item(s)['text']} is not a leaf node and cannot be added.")
            continue

        full_path = data_tree.item(s)['values'][0]

        # Check if the path points to a valid `ascii-spec.txt`
        if not full_path.endswith("ascii-spec.txt"):
            print(f"Item {data_tree.item(s)['text']} is invalid (not a valid leaf node).")
            continue

        # Shortened file path name
        display_name = "/".join(full_path.split("/")[-5:-1])
        print(f"Adding item: {display_name}")
        workspace_tree.insert("", "end", text=display_name, values=(full_path,))


def remove_dir(data_tree):
    """Remove the selected top-level directory from the data import treeview."""
    selected_items = data_tree.selection()
    for item in selected_items:
        parent = data_tree.parent(item)
        # Ensure only top-level items are removed
        if not parent:
            data_tree.delete(item)
        else:
            print(f"Cannot remove {data_tree.item(item)['text']} as it is not a top-level item.")


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


def clear_workspace(tree):
    """Remove all items from the workspace tree."""
    for item in tree.get_children():
        tree.delete(item)


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
    """Plot the data based on the current state."""
    gather_data(state)
    transform_data(state)
    customize_graph(state)


def gather_data(state):
    """Gather data from the workspace tree and prepare it for plotting."""
    state['file_paths'] = [state['workspace_tree'].item(child)["values"][0] for child in state['workspace_tree'].get_children()]
    state['lines'] = []

    for file_path in state['file_paths']:
        df = pd.read_csv(file_path, skiprows=1)
        # Choose Y column based on the selected x_axis_unit
        if state['x_axis_unit'].get() == "ppm":
            x_column_index = 3
        elif state['x_axis_unit'].get() == "Hz" or state['x_axis_unit'].get() == "kHz":
            x_column_index = 2
            if state['x_axis_unit'].get() == "kHz":
                # Divide y values by 1000 for kHz
                df.iloc[:, x_column_index] /= 1000
        else:
            print("Invalid x-axis unit")
        x_data = df.iloc[:, x_column_index]
        max_y_value = float(df.iloc[:, 1].max())
        y_data = df.iloc[:, 1] / max_y_value

        # Apply data limits
        data_x_min = float(state['x_min_mask_entry'].get()) if state['x_min_mask_entry'].get() else x_data.min()
        data_x_max = float(state['x_max_mask_entry'].get()) if state['x_max_mask_entry'].get() else x_data.max()
        
        mask = (x_data <= data_x_max) & (x_data >= data_x_min)
        x_data = x_data[mask]
        y_data = y_data[mask]

        state['lines'].append([x_data, y_data])  # [[x1,y1],[x2,y2],[x3,y3]...]


def transform_data(state):
    """Transform the data based on user-defined settings (scaling, offsets, etc.)."""
    scaling_factor_str = state['scaling_factor_entry'].get()
    scaling_factor = float(scaling_factor_str) if scaling_factor_str and scaling_factor_str.replace('.', '', 1).isdigit() else 1.0

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
                cumulative_y_offset = max(line[1]) + y_offset_increment
            else:
                # Store original max before modification
                original_max = max(line[1])
                # Apply cumulative offset to current line
                line[1] += cumulative_y_offset
                # Update cumulative offset with original max + spacing
                cumulative_y_offset += original_max + y_offset_increment


def customize_graph(state):
    """Customize and display the graph based on user settings."""
    clear_plot(state)

    fig, ax = plt.subplots()
    set_axis_limits(state, ax)
    axis_title = get_axis_title(state['nucleus_entry'].get(), state['x_axis_unit'].get())
    set_axis_ticks(state, ax)

    selected_scheme = state['color_scheme_var'].get()
    if selected_scheme == "Custom":
        custom_color = state['custom_color_entry'].get()
        if custom_color and validate_color(custom_color):
            colors = [custom_color]
        else:
            messagebox.showerror("Error", "Please enter a valid color name or hex code")
            return
    else:
        colors = state['color_schemes'].get(selected_scheme, state['color_schemes']["Default"])

    ax.set_xlabel(axis_title, fontdict={'family': state['label_font_type_var'].get() if state['label_font_type_var'].get() else 'Arial', 'size': float(state['label_font_size_entry'].get()) if state['label_font_size_entry'].get() else 10})

    for idx, line in enumerate(reversed(state['lines'])):
        line_color = colors[0] if selected_scheme == "Custom" else colors[idx % len(colors)]
        ax.plot(line[0], line[1], linewidth=float(state['line_thickness_entry'].get()) if state['line_thickness_entry'].get() else None, color=line_color)

    ax.invert_xaxis()
    fig.tight_layout()

    # Preserve the aspect ratio
    set_width, set_height = fig.get_size_inches() * fig.dpi * 1.1

    canvas = FigureCanvasTkAgg(fig, master=state['placeholder_canvas'])
    canvas.get_tk_widget().config(width=set_width, height=set_height)
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
    canvas.draw()
    
    # Add Matplotlib toolbar
    toolbar = NavigationToolbar2Tk(canvas, state['placeholder_canvas'])
    toolbar.update()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)


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
    x_ticks_spacing = float(state['major_ticks_freq_entry'].get()) if state['major_ticks_freq_entry'].get() else None
    x_minor_ticks_spacing = float(state['minor_ticks_freq_entry'].get()) if state['minor_ticks_freq_entry'].get() else None

    if x_ticks_spacing is not None:
        ax.xaxis.set_major_locator(ticker.MultipleLocator(x_ticks_spacing))

    if x_minor_ticks_spacing is not None:
        ax.xaxis.set_minor_locator(ticker.MultipleLocator(x_minor_ticks_spacing))

    # Set font properties directly on the x-axis tick labels
    font_properties = {'family': state['axis_font_type_var'].get() if state['label_font_type_var'].get() else 'Arial', 'size': float(state['axis_font_size_entry'].get()) if state['axis_font_size_entry'].get() else 10}
    for label in ax.xaxis.get_majorticklabels():
        label.set_fontfamily(font_properties['family'])
        label.set_fontsize(font_properties['size'])

    # Hide y-axis ticks and labels
    ax.yaxis.set_major_locator(plt.NullLocator())
    ax.yaxis.set_minor_locator(plt.NullLocator())

    # Additional customization
    major_tick_length = float(state['major_ticks_len_entry'].get()) if state['major_ticks_len_entry'].get() else 4.0  # Default value: 4.0
    minor_tick_length = float(state['minor_ticks_len_entry'].get()) if state['major_ticks_len_entry'].get() else 2.0  # Default value: 2.0

    ax.tick_params(axis='both', which='major', length=major_tick_length)
    ax.tick_params(axis='both', which='minor', length=minor_tick_length)


def clear_plot(state):
    """Clear the current plot."""
    for widget in state['placeholder_canvas'].winfo_children():
        widget.destroy()
        plt.close()


def validate_color(color):
    """Validate if the color is a valid name or hex code."""
    try:
        plt.plot([], color=color)
        return True
    except ValueError:
        return False


def export_data(state):
    """Export settings while excluding GUI widgets."""
    file = filedialog.asksaveasfilename(defaultextension='.txt')
    if file:
        exportable_state = {}
        
        # Collect only the values we want to export
        for widget_name, widget in state.items():
            if isinstance(widget, tk.Entry):
                exportable_state[widget_name] = widget.get()
            elif isinstance(widget, tk.StringVar):
                exportable_state[widget_name] = widget.get()
            elif widget_name not in ['data_tree', 'workspace_tree', 'placeholder_canvas', 
                                   'canvas_frame', 'color_schemes', 'lines', 'file_paths']:
                exportable_state[widget_name] = str(widget)
        
        with open(file, 'w') as f:
            for key, value in exportable_state.items():
                f.write(f"{key}:{value}\n")
        
        messagebox.showinfo("Notice", "Settings successfully exported!")

def import_data(state):
    """Import settings while preserving GUI widget types."""
    file = filedialog.askopenfile(mode='r')
    if file:
        try:
            for line_number, line in enumerate(file, 1):
                # Skip empty lines
                if not line.strip():
                    continue
                
                # Check if line contains a colon
                if ':' not in line:
                    print(f"Warning: Line {line_number} is malformed (missing colon): {line.strip()}")
                    continue
                
                try:
                    key, value = line.strip().split(":", 1)  # Split on first colon only
                    
                    # Skip empty keys or values
                    if not key or not value:
                        print(f"Warning: Line {line_number} has empty key or value: {line.strip()}")
                        continue
                    
                    # Only process known state keys
                    if key in state:
                        if isinstance(state[key], tk.Entry):
                            state[key].delete(0, tk.END)
                            state[key].insert(0, value)
                        elif isinstance(state[key], tk.StringVar):
                            state[key].set(value)
                        # Skip widgets that shouldn't be imported
                        elif key not in ['data_tree', 'workspace_tree', 'placeholder_canvas', 
                                       'canvas_frame', 'color_schemes']:
                            try:
                                state[key] = value
                            except Exception as e:
                                print(f"Warning: Could not import value for {key}: {str(e)}")
                    else:
                        print(f"Warning: Unknown key in settings file: {key}")
                
                except Exception as e:
                    print(f"Warning: Error processing line {line_number}: {str(e)}")
                    continue
            
            messagebox.showinfo("Notice", "Settings successfully imported!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import settings: {str(e)}")
        finally:
            file.close()
    else:
        messagebox.showwarning("Notice", "No file selected!")


def main():
    root = tk.Tk()
    root.title("NMR Plotter")

    global existing_data
    existing_data = {}

    state = {}
    
    # DATA INPUT FRAME
    data_frame = ttk.LabelFrame(root, text="Data Import")
    data_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10, rowspan=2, columnspan=2)

    data_tree = ttk.Treeview(data_frame)
    data_tree.column("#0", width=500, anchor='w')
    data_tree.heading("#0", text="")
    data_tree.grid(row=0, column=0, sticky="nsew", padx=5, columnspan=4)
    
    add_dir_btn = ttk.Button(data_frame ,text="Add", command=lambda: add_dirs(data_tree))
    add_dir_btn.grid(row=1, column=0, sticky="", padx=5, pady=5)

    remove_dir_btn = ttk.Button(data_frame, text="Remove", command=lambda: remove_dir(data_tree))
    remove_dir_btn.grid(row=1, column=1, sticky="", padx=5, pady=5)

    clear_dirs_btn = ttk.Button(data_frame, text="Clear", command=lambda: clear_dirs(data_tree))
    clear_dirs_btn.grid(row=1, column=2, sticky="", padx=5, pady=5)

    add_workspace_btn = ttk.Button(data_frame, text="Add to Workspace", command=lambda: add_to_workspace(data_tree, workspace_tree))
    add_workspace_btn.grid(row=1, column=3, sticky="", padx=5, pady=5, ipady=5)

    
    # WORKSPACE FRAME
    workspace_frame = ttk.LabelFrame(root, text="Workspace")
    workspace_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=10, rowspan=2, columnspan=2)   

    workspace_tree = ttk.Treeview(workspace_frame)
    workspace_tree.column("#0", width=500, anchor='w')
    workspace_tree.heading("#0", text="")
    workspace_tree.grid(row=0, column=0, sticky="nsew", padx=5, columnspan=4)

    move_up_btn = ttk.Button(workspace_frame, text="↑", command=lambda: move_up(workspace_tree))
    move_up_btn.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

    move_down_btn = ttk.Button(workspace_frame, text="↓", command=lambda: move_down(workspace_tree))
    move_down_btn.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)

    remove_workspace_btn = ttk.Button(workspace_frame, text="Remove", command=lambda: remove_from_workspace(workspace_tree))
    remove_workspace_btn.grid(row=1, column=2, sticky="nsew", padx=5, pady=5)

    clear_workspace_btn = ttk.Button(workspace_frame, text="Clear", command=lambda: clear_workspace(workspace_tree))
    clear_workspace_btn.grid(row=1, column=3, sticky="nsew", padx=5, pady=5)


    # ACTION FRAME
    action_frame = ttk.LabelFrame(root, text="Actions")
    action_frame.grid(row=4, column=0, sticky="nsew", padx=10, pady=10, rowspan=1, columnspan=2)

    plot_data_btn = ttk.Button(action_frame, text="Plot Data", command=lambda: plot_graph(state))
    plot_data_btn.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

    import_btn = ttk.Button(action_frame, text="Import", command=lambda: import_data(state))
    import_btn.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)

    export_btn = ttk.Button(action_frame, text="Export", command=lambda: export_data(state))
    export_btn.grid(row=0, column=3, sticky="nsew", padx=5, pady=5)


    # CANVAS FRAME
    canvas_frame = ttk.LabelFrame(root, text="Plot")
    canvas_frame.grid(row=0, column=2, sticky="nsew", rowspan=5, columnspan=2, padx=10, pady=10)

    placeholder_canvas = tk.Canvas(canvas_frame, width=800, height=600, bg="white")
    placeholder_canvas.grid(row=0, column=0, sticky="nsew", padx=5)
    


    # CUSTOMIZATION FRAME
    customization_frame = ttk.LabelFrame(root, text="Customization")
    customization_frame.grid(row=5, column=0, sticky="nsew", padx=10, pady=10, columnspan=4)

    # column 1

    x_min_label = ttk.Label(customization_frame, text="X-Min:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
    x_min_entry = ttk.Entry(customization_frame, width=6)
    x_min_entry.grid(row=0, column=1, sticky="w", padx=10, pady=5)

    x_max_label = ttk.Label(customization_frame, text="X-Max:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
    x_max_entry = ttk.Entry(customization_frame, width=6)
    x_max_entry.grid(row=1, column=1, sticky="w", padx=10, pady=5)

    y_min_label = ttk.Label(customization_frame, text="Y-Min:").grid(row=2, column=0, sticky="w", padx=10, pady=5)
    y_min_entry = ttk.Entry(customization_frame, width=6)
    y_min_entry.grid(row=2, column=1, sticky="w", padx=10, pady=5)

    y_max_label = ttk.Label(customization_frame, text="Y-Max:").grid(row=3, column=0, sticky="w", padx=10, pady=5)
    y_max_entry = ttk.Entry(customization_frame, width=6)
    y_max_entry.grid(row=3, column=1, sticky="w", padx=10, pady=5)

    x_axis_unit_label = ttk.Label(customization_frame, text="X-Axis Unit:").grid(row=4, column=0, sticky="w", padx=10, pady=5)
    x_axis_unit = tk.StringVar()
    x_axis_unit_combobox = ttk.Combobox(customization_frame, textvariable=x_axis_unit, values=["ppm","Hz","kHz"], width=5)
    x_axis_unit_combobox.grid(row=4, column=1, sticky="w", padx=8, pady=5)

    # column 2

    # mode stuff
    x_min_mask_label = ttk.Label(customization_frame, text="X-Min Mask:").grid(row=0, column=2, sticky="w", padx=10, pady=5)
    x_min_mask_entry = ttk.Entry(customization_frame, width=6)
    x_min_mask_entry.grid(row=0, column=3, sticky="w", padx=10, pady=5)

    x_max_mask_label = ttk.Label(customization_frame, text="X-Max Mask:").grid(row=1, column=2, sticky="w", padx=10, pady=5)
    x_max_mask_entry = ttk.Entry(customization_frame, width=6)
    x_max_mask_entry.grid(row=1, column=3, sticky="w", padx=10, pady=5)

    mode_label = ttk.Label(customization_frame, text="Mode:").grid(row=2, column=2, sticky="w", padx=10, pady=5)
    mode_var = tk.StringVar()
    mode_combobox = ttk.Combobox(customization_frame, values=["stack", "overlay"], textvariable=mode_var, width=5, state="readonly")
    mode_combobox.grid(row=2, column=3, sticky="w", padx=8, pady=5)
    mode_combobox.current(0)

    x_offset_label = ttk.Label(customization_frame, text="X-Offset:").grid(row=3, column=2, sticky="w", padx=10, pady=5)
    x_offset_entry = ttk.Entry(customization_frame, width=6)
    x_offset_entry.grid(row=3, column=3, sticky="w", padx=10, pady=5)

    y_offset_label = ttk.Label(customization_frame, text="Y-Offset:").grid(row=4, column=2, sticky="w", padx=10, pady=5)
    y_offset_entry = ttk.Entry(customization_frame, width=6)
    y_offset_entry.grid(row=4, column=3, sticky="w", padx=10, pady=5)


    # column 3

    nucleus_label = ttk.Label(customization_frame, text="Nucleus:").grid(row=0, column=4, sticky="w", padx=10, pady=5)
    nucleus_entry = ttk.Entry(customization_frame, width=6)
    nucleus_entry.grid(row=0, column=5, sticky="w", padx=10, pady=5)

    # color stuff
    color_scheme_label = ttk.Label(customization_frame, text="Color Scheme:").grid(row=1, column=4, sticky="w", padx=10, pady=5)
    color_scheme_var = tk.StringVar()
    color_scheme_combobox = ttk.Combobox(customization_frame, values=["Default", "Scheme1", "Scheme2", "Scheme3", "Custom"], textvariable=color_scheme_var, width=5, state="readonly")
    color_scheme_combobox.grid(row=1, column=5, sticky="w", padx=8, pady=5)
    color_scheme_combobox.current(0)

    custom_color_label = ttk.Label(customization_frame, text="Custom Color:").grid(row=2, column=4, sticky="w", padx=10, pady=5)
    custom_color_entry = ttk.Entry(customization_frame, width=6)
    custom_color_entry.grid(row=2, column=5, sticky="w", padx=10, pady=5)

    axis_font_type_label = ttk.Label(customization_frame, text="Axis Font Type:").grid(row=3, column=4, sticky="w", padx=10, pady=5)
    axis_font_type_var = tk.StringVar()
    axis_font_type_combobox = ttk.Combobox(customization_frame, values=["Arial", "Times New Roman", "Courier New"], textvariable=axis_font_type_var, width=5, state="readonly")
    axis_font_type_combobox.grid(row=3, column=5, sticky="w", padx=8, pady=5)

    axis_font_size_label = ttk.Label(customization_frame, text="Axis Font Size:").grid(row=4, column=4, sticky="w", padx=10, pady=5)
    axis_font_size_entry = ttk.Entry(customization_frame, width=6)
    axis_font_size_entry.grid(row=4, column=5, sticky="w", padx=10, pady=5)


    # column 4

    label_font_type_label = ttk.Label(customization_frame, text="Label Font Type:").grid(row=0, column=6, sticky="w", padx=10, pady=5)
    label_font_type_var = tk.StringVar()
    label_font_type_combobox = ttk.Combobox(customization_frame, values=["Arial", "Times New Roman", "Courier New"], textvariable=label_font_type_var, width=5, state="readonly")
    label_font_type_combobox.grid(row=0, column=7, sticky="w", padx=8, pady=5)

    label_font_size_label = ttk.Label(customization_frame, text="Label Font Size:").grid(row=1, column=6, sticky="w", padx=10, pady=5)
    label_font_size_entry = ttk.Entry(customization_frame, width=6)
    label_font_size_entry.grid(row=1, column=7, sticky="w", padx=10, pady=5)

    line_thickness_label = ttk.Label(customization_frame, text="Line Thickness:").grid(row=2, column=6, sticky="w", padx=10, pady=5)
    line_thickness_entry = ttk.Entry(customization_frame, width=6)
    line_thickness_entry.grid(row=2, column=7, sticky="w", padx=10, pady=5)

    scaling_factor_label = ttk.Label(customization_frame, text="Scaling Factor:").grid(row=3, column=6, sticky="w", padx=10, pady=5)
    scaling_factor_entry = ttk.Entry(customization_frame, width=6)
    scaling_factor_entry.grid(row=3, column=7, sticky="w", padx=10, pady=5)

    whitespace_label = ttk.Label(customization_frame, text="Whitespace:").grid(row=4, column=6, sticky="w", padx=10, pady=5)
    whitespace_entry = ttk.Entry(customization_frame, width=6)
    whitespace_entry.grid(row=4, column=7, sticky="w", padx=10, pady=5)


    # column 5

    major_ticks_freq_label = ttk.Label(customization_frame, text="Major Ticks Spacing:").grid(row=0, column=8, sticky="w", padx=10, pady=5)
    major_ticks_freq_entry = ttk.Entry(customization_frame, width=6)
    major_ticks_freq_entry.grid(row=0, column=9, sticky="w", padx=10, pady=5)

    minor_ticks_freq_label = ttk.Label(customization_frame, text="Minor Ticks Interval:").grid(row=1, column=8, sticky="w", padx=10, pady=5)
    minor_ticks_freq_entry = ttk.Entry(customization_frame, width=6)
    minor_ticks_freq_entry.grid(row=1, column=9, sticky="w", padx=10, pady=5)

    major_ticks_len_label = ttk.Label(customization_frame, text="Major Ticks Length:").grid(row=2, column=8, sticky="w", padx=10, pady=5)
    major_ticks_len_entry = ttk.Entry(customization_frame, width=6)
    major_ticks_len_entry.grid(row=2, column=9, sticky="w", padx=10, pady=5)

    minor_ticks_len_label = ttk.Label(customization_frame, text="Minor Ticks Length:").grid(row=3, column=8, sticky="w", padx=10, pady=5)
    minor_ticks_len_entry = ttk.Entry(customization_frame, width=6)
    minor_ticks_len_entry.grid(row=3, column=9, sticky="w", padx=10, pady=5)


    # Configure the main grid
    root.grid_rowconfigure(0, weight=1, minsize=50)  # Row for Data Import and Plot
    root.grid_rowconfigure(1, weight=1, minsize=50)  # Row for Workspace
    root.grid_rowconfigure(2, weight=1, minsize=50)  # Row for Actions
    root.grid_rowconfigure(3, weight=1, minsize=50)  # Row for Canvas
    root.grid_rowconfigure(4, weight=1, minsize=50)  # Row for Customization

    root.grid_columnconfigure(0, weight=1, minsize=100)  # Column for Data Import and Workspace
    root.grid_columnconfigure(1, weight=1, minsize=100)  # Column for Actions
    root.grid_columnconfigure(2, weight=1, minsize=200)  # Column for Plot
    root.grid_columnconfigure(3, weight=1, minsize=100)  # Column for Customization

    # Configure the frames
    data_frame.grid_rowconfigure(0, weight=1)  # Allow the data tree to expand
    data_frame.grid_columnconfigure(0, weight=1)  # Allow the buttons to expand
    data_frame.grid_columnconfigure(1, weight=1)
    data_frame.grid_columnconfigure(2, weight=1)
    data_frame.grid_columnconfigure(3, weight=1)

    workspace_frame.grid_rowconfigure(0, weight=1)  # Allow the workspace tree to expand
    workspace_frame.grid_columnconfigure(0, weight=1)  # Allow the buttons to expand
    workspace_frame.grid_columnconfigure(1, weight=1)
    workspace_frame.grid_columnconfigure(2, weight=1)
    workspace_frame.grid_columnconfigure(3, weight=1)

    # action_frame.grid_rowconfigure(0, weight=1, minsize=30)  # Allow the action buttons to expand
    action_frame.grid_columnconfigure(0, weight=1)  # Allow the buttons to expand
    action_frame.grid_columnconfigure(1, weight=1)
    action_frame.grid_columnconfigure(2, weight=1)
    action_frame.grid_columnconfigure(3, weight=1)

    canvas_frame.grid_rowconfigure(0, weight=1)  # Allow the canvas to expand
    canvas_frame.grid_columnconfigure(0, weight=1)  # Allow the canvas to expand

    customization_frame.grid_rowconfigure(0, weight=1)  # Allow the customization options to expand
    customization_frame.grid_rowconfigure(1, weight=1)
    customization_frame.grid_rowconfigure(2, weight=1)
    customization_frame.grid_rowconfigure(3, weight=1)
    customization_frame.grid_rowconfigure(4, weight=1)
    customization_frame.grid_rowconfigure(5, weight=1)
    customization_frame.grid_rowconfigure(6, weight=1)
    customization_frame.grid_rowconfigure(7, weight=1)
    customization_frame.grid_rowconfigure(8, weight=1)
    customization_frame.grid_rowconfigure(9, weight=1)

    for col in range(10):  # Assuming you have 10 columns in customization_frame
        customization_frame.grid_columnconfigure(col, weight=1)  # Allow all columns to expand

    # Store all GUI elements in the state dictionary
    state['data_tree'] = data_tree
    state['workspace_tree'] = workspace_tree
    state['placeholder_canvas'] = placeholder_canvas
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
    state['color_schemes'] = {
        "Default": ["black"],
        "Scheme1": ["red", "green", "blue", "cyan", "magenta", "yellow", "black"],
        "Scheme2": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2"],
        "Scheme3": ["#17becf", "#bcbd22", "#7f7f7f", "#aec7e8", "#ffbb78", "#98df8a", "#ff9896"],
        "Custom": []  # This will be populated dynamically
    }
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

    root.mainloop()

if __name__ == "__main__":
    main()