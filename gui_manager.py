import os
import logging
import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class GUIManager:
    def __init__(self):
        self.root = None
        self.namespace = ''
        self.object_ids = {}
        self.project_structure = {}
        self.pou_elements = {}
        self.xml_file_path = None
        self.component_map = {}

        # GUI state variables
        self.include_logic = None
        self.include_interface = None
        self.include_enums = None

    def start_application(self, mermaid_processor, drawio_processor):
        """Start the main application flow"""
        self.mermaid_processor = mermaid_processor
        self.drawio_processor = drawio_processor
        self.show_initial_gui()

    def show_initial_gui(self):
        """Show initial GUI for file selection and options"""
        self.initial_root = tk.Tk()
        self.initial_root.title("PLCopen XML to Diagram Converter")
        self.initial_root.geometry("550x450")

        # Center the window
        self._center_window(self.initial_root)

        # Main frame
        main_frame = ttk.Frame(self.initial_root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="PLCopen XML to Diagram Converter",
                                font=('Arial', 16, 'bold'))
        title_label.pack(pady=10)

        # Description
        desc_label = ttk.Label(main_frame,
                               text="Convert CODESYS PLCopen XML exports to Mermaid flowcharts and Draw.io diagrams",
                               font=('Arial', 10), wraplength=500)
        desc_label.pack(pady=5)

        # Options frame
        options_frame = ttk.LabelFrame(main_frame, text="Conversion Options", padding="10")
        options_frame.pack(fill=tk.X, pady=20)

        # Output format selection
        format_frame = ttk.Frame(options_frame)
        format_frame.pack(fill=tk.X, pady=5)

        ttk.Label(format_frame, text="Output Formats:", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(0, 5))

        # Multiple format selection
        format_subframe = ttk.Frame(format_frame)
        format_subframe.pack(fill=tk.X, padx=20)

        self.include_mermaid = tk.BooleanVar(value=True)
        self.include_drawio = tk.BooleanVar(value=False)

        ttk.Checkbutton(format_subframe, text="Mermaid (.mmd files)",
                        variable=self.include_mermaid).pack(side=tk.LEFT, padx=10)
        ttk.Checkbutton(format_subframe, text="Draw.io (.drawio files)",
                        variable=self.include_drawio).pack(side=tk.LEFT, padx=10)

        # Include options
        include_frame = ttk.Frame(options_frame)
        include_frame.pack(fill=tk.X, pady=5)

        ttk.Label(include_frame, text="Content to Include:", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(0, 5))

        include_subframe = ttk.Frame(include_frame)
        include_subframe.pack(fill=tk.X, padx=20)

        self.include_logic = tk.BooleanVar(value=True)
        self.include_interface = tk.BooleanVar(value=True)
        self.include_enums = tk.BooleanVar(value=True)

        ttk.Checkbutton(include_subframe, text="Include Logic Flowcharts",
                        variable=self.include_logic).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(include_subframe, text="Include Interface Diagrams",
                        variable=self.include_interface).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(include_subframe, text="Include Enumerators",
                        variable=self.include_enums).pack(anchor=tk.W, pady=2)

        # File selection section
        file_frame = ttk.LabelFrame(main_frame, text="File Selection", padding="10")
        file_frame.pack(fill=tk.X, pady=10)

        self.selected_file = tk.StringVar(value="No file selected")
        file_status = ttk.Label(file_frame, textvariable=self.selected_file,
                                foreground="blue", wraplength=500)
        file_status.pack(anchor=tk.W, pady=5)

        button_frame = ttk.Frame(file_frame)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(button_frame, text="Select XML File",
                   command=self._select_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Start Conversion",
                   command=self._start_conversion).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Exit",
                   command=self.initial_root.destroy).pack(side=tk.LEFT, padx=5)

        # Status bar
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=10)

        self.status_var = tk.StringVar(value="Ready to convert")
        ttk.Label(status_frame, textvariable=self.status_var,
                  font=('Arial', 8)).pack(side=tk.LEFT)

        self.initial_root.mainloop()

    def _center_window(self, window):
        """Center the window on screen"""
        window.update_idletasks()
        width = window.winfo_width()
        height = window.winfo_height()
        x = (window.winfo_screenwidth() // 2) - (width // 2)
        y = (window.winfo_screenheight() // 2) - (height // 2)
        window.geometry('{}x{}+{}+{}'.format(width, height, x, y))

    def _select_file(self):
        """Handle file selection"""
        file_path = filedialog.askopenfilename(
            title="Select PLCopen XML File",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )
        if file_path:
            self.xml_file_path = file_path
            self.selected_file.set(f"Selected: {file_path}")
            self.status_var.set("File selected - Click 'Start Conversion' to continue")
            logger.info(f"File selected: {file_path}")

    def _start_conversion(self):
        """Start the conversion process"""
        if not self.xml_file_path:
            messagebox.showerror("Error", "Please select an XML file first")
            return

        # Validate format selection
        if not self.include_mermaid.get() and not self.include_drawio.get():
            messagebox.showerror("Error", "Please select at least one output format (Mermaid or Draw.io)")
            return

        self.status_var.set("Parsing XML file...")
        self.initial_root.update()

        # Parse XML structure
        if not self._parse_xml_structure():
            return

        # Show component browser
        selected_id = self._show_component_browser()
        if not selected_id:
            self.status_var.set("Conversion cancelled")
            return

        # Get output directory
        output_dir = filedialog.askdirectory(title="Select Output Directory")
        if not output_dir:
            output_dir = "diagram_output"

        # Convert to selected formats
        self._convert_to_formats(selected_id, output_dir)

    def _get_selected_formats(self) -> List[str]:
        """Get list of selected output formats"""
        formats = []
        if self.include_mermaid.get():
            formats.append('mermaid')
        if self.include_drawio.get():
            formats.append('drawio')
        return formats

    def _parse_xml_structure(self) -> bool:
        """Parse XML file and identify structure"""
        try:
            logger.info("Parsing XML structure...")
            tree = ET.parse(self.xml_file_path)
            root = tree.getroot()

            # Extract namespace
            if '}' in root.tag:
                self.namespace = root.tag.split('}')[0] + '}'
            else:
                self.namespace = ''

            logger.info(f"Namespace detected: {self.namespace}")

            # Extract all POU elements and their actions
            self._extract_pous_and_actions(root)

            # Extract project structure for navigation
            self._extract_project_structure(root)

            logger.info(f"Total components extracted: {len(self.object_ids)}")
            self.status_var.set(f"Found {len(self.object_ids)} components - Select one to convert")
            return True

        except Exception as e:
            logger.error(f"Failed to parse XML file: {str(e)}")
            messagebox.showerror("Error", f"Failed to parse XML file: {str(e)}")
            self.status_var.set("Error parsing XML file")
            return False

    def _extract_pous_and_actions(self, root):
        """Extract all POU elements and their actions"""
        logger.info("Extracting POU elements and actions...")
        self.object_ids = {}
        self.pou_elements = {}

        # Find the types -> pous section
        types_elem = root.find(f".//{self.namespace}types")
        if types_elem is None:
            logger.error("No 'types' element found in XML")
            return

        pous_elem = types_elem.find(f"{self.namespace}pous")
        if pous_elem is None:
            logger.error("No 'pous' element found in types")
            return

        # Extract all POU elements
        pou_elements = pous_elem.findall(f"{self.namespace}pou")
        logger.info(f"Found {len(pou_elements)} POU elements")

        for pou in pou_elements:
            self._process_pou_element(pou)

    def _process_pou_element(self, pou_element):
        """Process a single POU element and extract all its components"""
        pou_name = pou_element.get('name', 'Unknown_POU')
        logger.debug(f"Processing POU: {pou_name}")

        # Get the main POU ObjectID
        pou_object_id = self._get_object_id(pou_element)
        if pou_object_id:
            self.object_ids[pou_object_id] = {
                'name': pou_name,
                'type': 'POU',
                'element': pou_element,
                'description': self._get_description(pou_element),
                'parent': None
            }
            self.pou_elements[pou_name] = pou_element
            logger.debug(f"  Main POU ObjectID: {pou_object_id}")

        # Extract actions within this POU
        actions = pou_element.find(f"{self.namespace}actions")
        if actions is not None:
            action_elements = actions.findall(f"{self.namespace}action")
            logger.debug(f"  Found {len(action_elements)} actions in {pou_name}")

            for action in action_elements:
                self._process_action_element(action, pou_name, pou_object_id)

    def _process_action_element(self, action_element, pou_name, pou_object_id):
        """Process a single action element"""
        action_name = action_element.get('name', 'Unknown_Action')
        action_object_id = self._get_object_id(action_element)

        if action_object_id:
            self.object_ids[action_object_id] = {
                'name': f"{pou_name}.{action_name}",
                'type': 'Action',
                'element': action_element,
                'description': f"Action {action_name} in {pou_name}",
                'parent': pou_object_id
            }
            logger.debug(f"    Action: {action_name} -> ObjectID: {action_object_id}")

    def _get_object_id(self, element) -> Optional[str]:
        """Extract ObjectID from element using multiple methods"""
        # Method 1: Check for objectId child element
        object_id_elem = element.find(f"{self.namespace}objectId")
        if object_id_elem is not None and object_id_elem.text:
            return object_id_elem.text.strip()

        # Method 2: Check for ObjectId in addData
        add_data = element.find(f"{self.namespace}addData")
        if add_data is not None:
            data_elems = add_data.findall(f"{self.namespace}data")
            for data_elem in data_elems:
                if 'objectid' in data_elem.get('name', '').lower():
                    object_id_elem = data_elem.find(f"{self.namespace}ObjectId")
                    if object_id_elem is not None and object_id_elem.text:
                        return object_id_elem.text.strip()

        # Method 3: Check for objectId attribute
        object_id_attr = element.get('objectId')
        if object_id_attr:
            return object_id_attr.strip()

        return None

    def _get_description(self, element) -> str:
        """Extract description from element"""
        description_elem = element.find(f"{self.namespace}documentation/{self.namespace}description")
        if description_elem is not None and description_elem.text:
            return description_elem.text.strip()
        return "No description"

    def _extract_project_structure(self, root):
        """Extract the project structure for navigation"""
        logger.info("Extracting project structure...")

        project_structure_path = f".//{self.namespace}addData/{self.namespace}data[@name='http://www.3s-software.com/plcopenxml/projectstructure']/{self.namespace}ProjectStructure"
        project_structure_elem = root.find(project_structure_path)

        if project_structure_elem is not None:
            self.project_structure = self._parse_folder_structure(project_structure_elem)
            logger.info(f"Project structure extracted with {len(self.project_structure)} root items")
        else:
            logger.warning("No project structure found in XML")
            self.project_structure = {}

    def _parse_folder_structure(self, folder_element) -> Dict:
        """Recursively parse folder structure"""
        structure = {}

        for child in folder_element:
            tag_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag

            if tag_name == 'Folder':
                folder_name = child.get('Name', 'Unnamed Folder')
                structure[folder_name] = {
                    'type': 'folder',
                    'children': self._parse_folder_structure(child)
                }

            elif tag_name == 'Object':
                object_name = child.get('Name', 'Unnamed Object')
                object_id = child.get('ObjectId')
                structure[object_name] = {
                    'type': 'object',
                    'object_id': object_id,
                    'children': self._parse_folder_structure(child)
                }

        return structure

    def _show_component_browser(self) -> Optional[str]:
        """Show component browser and return selected ObjectID"""
        logger.info("Opening component browser...")

        # Create the browser window
        browser_root = tk.Toplevel(self.initial_root)
        browser_root.title("Component Browser - Select Component to Convert")
        browser_root.geometry("1000x700")
        self._center_window(browser_root)

        selected_object_id = tk.StringVar()

        # Create main frame
        main_frame = ttk.Frame(browser_root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Title
        title_label = ttk.Label(main_frame,
                                text=f"Select a Component to Convert ({len(self.object_ids)} components found)",
                                font=('Arial', 12, 'bold'))
        title_label.pack(pady=10)

        # Create notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: All Components
        components_frame = ttk.Frame(notebook)
        notebook.add(components_frame, text="All Components")

        # Populate components tab
        self._populate_components_tab(components_frame, selected_object_id, browser_root)

        # Control buttons at bottom - ONLY CANCEL BUTTON
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=10)

        cancel_button = ttk.Button(control_frame, text="Cancel",
                                   command=browser_root.destroy)
        cancel_button.pack(side=tk.RIGHT, padx=5)

        # Wait for the browser window to close
        browser_root.transient(self.initial_root)
        browser_root.grab_set()
        browser_root.focus_set()

        logger.info("Component browser displayed, waiting for user selection...")
        self.initial_root.wait_window(browser_root)

        selected_id = selected_object_id.get()
        logger.info(f"User selected component: {selected_id}")

        return selected_id if selected_id else None

    def _populate_components_tab(self, parent, selected_object_id, root_window):
        """Populate the all components tab"""
        # Create paned window
        paned_window = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left panel - List of all components
        left_frame = ttk.Frame(paned_window)
        paned_window.add(left_frame, weight=1)

        ttk.Label(left_frame, text="All Components:", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=5)

        # Filter frame
        filter_frame = ttk.Frame(left_frame)
        filter_frame.pack(fill=tk.X, pady=5)

        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT)
        filter_var = tk.StringVar()
        filter_entry = ttk.Entry(filter_frame, textvariable=filter_var)
        filter_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Listbox with scrollbar
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        listbox = tk.Listbox(list_frame, font=('Arial', 10))
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        list_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=listbox.yview)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        listbox.configure(yscrollcommand=list_scroll.set)

        # Right panel - Details
        right_frame = ttk.Frame(paned_window)
        paned_window.add(right_frame, weight=1)

        ttk.Label(right_frame, text="Component Details:", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=5)

        details_text = tk.Text(right_frame, wrap=tk.NONE, font=('Arial', 10))
        details_text.pack(fill=tk.BOTH, expand=True, pady=5)

        # Add scrollbars to details text
        v_scrollbar = ttk.Scrollbar(details_text, orient=tk.VERTICAL, command=details_text.yview)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar = ttk.Scrollbar(details_text, orient=tk.HORIZONTAL, command=details_text.xview)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        details_text.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        # Populate listbox
        component_list = []
        for obj_id, info in self.object_ids.items():
            display_text = f"{info['name']} ({info['type']})"
            component_list.append((display_text, obj_id))

        component_list.sort(key=lambda x: x[0])

        for display_text, obj_id in component_list:
            listbox.insert(tk.END, display_text)

        component_map = {display_text: obj_id for display_text, obj_id in component_list}

        def show_object_details(obj_id):
            """Show details for selected object"""
            details_text.delete(1.0, tk.END)

            if obj_id and obj_id in self.object_ids:
                obj_info = self.object_ids[obj_id]
                details_text.insert(tk.END, f"Name: {obj_info['name']}\n")
                details_text.insert(tk.END, f"Type: {obj_info['type']}\n")
                details_text.insert(tk.END, f"ObjectID: {obj_id}\n")
                details_text.insert(tk.END, f"Description: {obj_info['description']}\n")

                if obj_info.get('parent'):
                    details_text.insert(tk.END, f"Parent: {obj_info['parent']}\n")

                # Show ST code preview if available
                element = obj_info['element']
                body = element.find(f"{self.namespace}body")
                if body is not None:
                    st_elem = body.find(f"{self.namespace}ST")
                    if st_elem is not None and st_elem.text:
                        st_preview = st_elem.text.strip()
                        if st_preview:
                            details_text.insert(tk.END, f"\nST Code Preview:\n{st_preview[:500]}...\n")

                details_text.insert(tk.END, f"\n\nDouble-click to select or click 'Select Component'")

        def on_list_select(event):
            """Handle list selection"""
            selection = listbox.curselection()
            if selection:
                display_text = listbox.get(selection[0])
                obj_id = component_map.get(display_text)
                if obj_id:
                    show_object_details(obj_id)

        def on_list_double_click(event):
            """Handle list double click"""
            selection = listbox.curselection()
            if selection:
                display_text = listbox.get(selection[0])
                obj_id = component_map.get(display_text)
                if obj_id:
                    selected_object_id.set(obj_id)
                    root_window.destroy()

        def on_select_button():
            """Handle select button click - FIXED: Now properly sets selection and closes window"""
            selection = listbox.curselection()
            if selection:
                display_text = listbox.get(selection[0])
                obj_id = component_map.get(display_text)
                if obj_id:
                    logger.info(f"Select button clicked - setting selection to: {obj_id}")
                    selected_object_id.set(obj_id)
                    root_window.destroy()  # This will close the browser and proceed to output directory
            else:
                messagebox.showwarning("Warning", "Please select a component first")

        def on_filter_change(*args):
            filter_text = filter_var.get().lower()
            listbox.delete(0, tk.END)
            for display_text, obj_id in component_list:
                if filter_text in display_text.lower():
                    listbox.insert(tk.END, display_text)

        # Bind events
        listbox.bind('<<ListboxSelect>>', on_list_select)
        listbox.bind('<Double-1>', on_list_double_click)
        filter_var.trace_add('write', on_filter_change)

        # Add the select button INSIDE the left frame
        select_button_frame = ttk.Frame(left_frame)
        select_button_frame.pack(fill=tk.X, pady=10)

        select_button = ttk.Button(select_button_frame, text="Select Component",
                                   command=on_select_button)
        select_button.pack(pady=5)

        # Select the first item by default
        if component_list:
            listbox.selection_set(0)
            listbox.activate(0)
            first_display_text = listbox.get(0)
            first_obj_id = component_map.get(first_display_text)
            if first_obj_id:
                show_object_details(first_obj_id)

    def _convert_to_formats(self, object_id: str, output_dir: str):
        """Convert selected component to multiple formats"""
        formats = self._get_selected_formats()
        logger.info(f"Converting ObjectID {object_id} to formats: {formats}")

        if object_id not in self.object_ids:
            messagebox.showerror("Error", f"ObjectID {object_id} not found")
            return

        # Get component info
        component_info = self.object_ids[object_id]

        # Set namespace in processors
        self.mermaid_processor.set_namespace(self.namespace)
        self.drawio_processor.set_namespace(self.namespace)

        # Track success for each format
        format_success = {}
        files_created = []

        # Convert to each selected format
        for format_type in formats:
            try:
                if format_type == 'mermaid':
                    success = self.mermaid_processor.convert_component(
                        component_info,
                        output_dir,
                        include_logic=self.include_logic.get(),
                        include_interface=self.include_interface.get()
                    )
                    format_success['mermaid'] = success
                    if success:
                        files_created.extend(self._get_created_files(output_dir, component_info['name'], 'mmd'))

                elif format_type == 'drawio':
                    success = self.drawio_processor.convert_component(
                        component_info,
                        output_dir,
                        include_logic=self.include_logic.get(),
                        include_interface=self.include_interface.get()
                    )
                    format_success['drawio'] = success
                    if success:
                        files_created.extend(self._get_created_files(output_dir, component_info['name'], 'drawio'))

            except Exception as e:
                logger.error(f"Error converting to {format_type} for {component_info['name']}: {str(e)}")
                format_success[format_type] = False

        # If it's a POU, also convert all its actions
        if any(format_success.values()) and component_info['type'] == 'POU':
            self._convert_pou_actions(component_info, output_dir, formats)

        # Show results
        successful_formats = [f for f, success in format_success.items() if success]
        if successful_formats:
            format_names = {
                'mermaid': 'Mermaid (.mmd)',
                'drawio': 'Draw.io (.drawio)'
            }
            created_formats = [format_names[f] for f in successful_formats]

            file_list = "\n".join([f"  • {os.path.basename(f)}" for f in files_created])

            logger.info(f"Successfully generated files in {output_dir}")
            messagebox.showinfo("Success",
                                f"Files generated in:\n{output_dir}\n\n"
                                f"Formats: {', '.join(created_formats)}\n\n"
                                f"Created files:\n{file_list}")
            self.status_var.set(f"Conversion completed - {len(successful_formats)} format(s) generated")
        else:
            messagebox.showerror("Error", "Failed to generate any files in the selected formats")
            self.status_var.set("Conversion failed")

    def _get_created_files(self, output_dir: str, component_name: str, extension: str) -> List[str]:
        """Get list of created files for a component"""
        files = []
        base_name = self._sanitize_filename(component_name)

        logic_file = os.path.join(output_dir, f"{base_name}_logic.{extension}")
        interface_file = os.path.join(output_dir, f"{base_name}_interface.{extension}")

        if os.path.exists(logic_file):
            files.append(logic_file)
        if os.path.exists(interface_file):
            files.append(interface_file)

        return files

    def _convert_pou_actions(self, pou_info: Dict, output_dir: str, formats: List[str]):
        """Convert all actions within a POU to multiple formats"""
        pou_element = pou_info['element']
        pou_name = pou_info['name']

        # Find actions within this POU
        actions = pou_element.find(f"{self.namespace}actions")
        if actions is not None:
            action_elements = actions.findall(f"{self.namespace}action")
            logger.info(f"Converting {len(action_elements)} actions for POU: {pou_name}")

            for action in action_elements:
                action_name = action.get('name', 'Unknown_Action')
                action_info = {
                    'name': f"{pou_name}.{action_name}",
                    'type': 'Action',
                    'element': action,
                    'description': f"Action {action_name} in {pou_name}",
                    'parent': pou_info
                }

                # Convert the action to each format
                for format_type in formats:
                    try:
                        if format_type == 'mermaid':
                            self.mermaid_processor.convert_component(
                                action_info,
                                output_dir,
                                include_logic=self.include_logic.get(),
                                include_interface=self.include_interface.get()
                            )
                        elif format_type == 'drawio':
                            self.drawio_processor.convert_component(
                                action_info,
                                output_dir,
                                include_logic=self.include_logic.get(),
                                include_interface=self.include_interface.get()
                            )
                    except Exception as e:
                        logger.error(f"Error converting action {action_name} to {format_type}: {str(e)}")

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize filename by removing invalid characters"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        return name