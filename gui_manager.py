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
        self.output_format = None

    def start_application(self, mermaid_processor):
        """Start the main application flow"""
        self.mermaid_processor = mermaid_processor
        self.show_initial_gui()

    def show_initial_gui(self):
        """Show initial GUI for file selection and options"""
        self.initial_root = tk.Tk()
        self.initial_root.title("PLCopen XML to Mermaid Converter")
        self.initial_root.geometry("500x400")

        # Center the window
        self._center_window(self.initial_root)

        # Main frame
        main_frame = ttk.Frame(self.initial_root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="PLCopen XML to Mermaid Converter",
                                font=('Arial', 16, 'bold'))
        title_label.pack(pady=10)

        # Description
        desc_label = ttk.Label(main_frame,
                               text="Convert CODESYS PLCopen XML exports to Mermaid flowcharts",
                               font=('Arial', 10))
        desc_label.pack(pady=5)

        # Options frame
        options_frame = ttk.LabelFrame(main_frame, text="Conversion Options", padding="10")
        options_frame.pack(fill=tk.X, pady=20)

        # Output format selection
        self.output_format = tk.StringVar(value="mermaid")
        format_frame = ttk.Frame(options_frame)
        format_frame.pack(fill=tk.X, pady=5)

        ttk.Label(format_frame, text="Output Format:").pack(side=tk.LEFT)
        ttk.Radiobutton(format_frame, text="Mermaid", variable=self.output_format,
                        value="mermaid").pack(side=tk.LEFT, padx=10)

        # Include options
        self.include_logic = tk.BooleanVar(value=True)
        self.include_interface = tk.BooleanVar(value=True)
        self.include_enums = tk.BooleanVar(value=True)

        ttk.Checkbutton(options_frame, text="Include Logic Flowcharts",
                        variable=self.include_logic).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(options_frame, text="Include Interface Diagrams",
                        variable=self.include_interface).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(options_frame, text="Include Enumerators",
                        variable=self.include_enums).pack(anchor=tk.W, pady=2)

        # File selection section
        file_frame = ttk.LabelFrame(main_frame, text="File Selection", padding="10")
        file_frame.pack(fill=tk.X, pady=10)

        self.selected_file = tk.StringVar(value="No file selected")
        file_status = ttk.Label(file_frame, textvariable=self.selected_file,
                                foreground="blue", wraplength=400)
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
            output_dir = "mermaid_output"

        # Convert to Mermaid
        self._convert_to_mermaid(selected_id, output_dir)

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
        browser_root = tk.Toplevel()  # Use Toplevel instead of Tk for secondary window
        browser_root.title("Component Browser - Select Component to Convert")
        browser_root.geometry("1000x700")
        self._center_window(browser_root)

        selected_object_id = tk.StringVar()

        # Create main frame
        main_frame = ttk.Frame(browser_root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Title
        title_label = ttk.Label(main_frame, text="Select a Component to Convert",
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

        # Control buttons at bottom
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=10)

        ttk.Button(control_frame, text="Cancel",
                   command=browser_root.destroy).pack(side=tk.RIGHT, padx=5)

        # Wait for the browser window to close
        browser_root.transient(self.initial_root)
        browser_root.grab_set()
        self.initial_root.wait_window(browser_root)

        return selected_object_id.get() if selected_object_id.get() else None

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

        self.listbox = tk.Listbox(list_frame, font=('Arial', 10))
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        list_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.configure(yscrollcommand=list_scroll.set)

        # Right panel - Details
        right_frame = ttk.Frame(paned_window)
        paned_window.add(right_frame, weight=1)

        ttk.Label(right_frame, text="Component Details:", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=5)

        self.details_text = tk.Text(right_frame, wrap=tk.WORD, font=('Arial', 10))
        self.details_text.pack(fill=tk.BOTH, expand=True, pady=5)

        # Add scrollbar to details text
        details_scroll = ttk.Scrollbar(self.details_text, orient=tk.VERTICAL, command=self.details_text.yview)
        details_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.details_text.configure(yscrollcommand=details_scroll.set)

        # Populate listbox
        component_list = []
        for obj_id, info in self.object_ids.items():
            display_text = f"{info['name']} ({info['type']})"
            component_list.append((display_text, obj_id))

        component_list.sort(key=lambda x: x[0])
        for display_text, obj_id in component_list:
            self.listbox.insert(tk.END, display_text)

        self.component_map = {display_text: obj_id for display_text, obj_id in component_list}

        # Bind events
        self.listbox.bind('<<ListboxSelect>>', lambda e: self._on_list_select(e, selected_object_id))
        self.listbox.bind('<Double-1>', lambda e: self._on_list_double_click(e, selected_object_id, root_window))

        def on_filter_change(*args):
            filter_text = filter_var.get().lower()
            self.listbox.delete(0, tk.END)
            for display_text, obj_id in component_list:
                if filter_text in display_text.lower():
                    self.listbox.insert(tk.END, display_text)

        # Use trace_add for newer Tk versions
        filter_var.trace_add('write', on_filter_change)

        # Select button
        select_button = ttk.Button(left_frame, text="Select Component",
                                   command=lambda: self._on_select_button(selected_object_id, root_window))
        select_button.pack(pady=10)

    def _on_list_select(self, event, selected_object_id):
        """Handle list selection"""
        selection = self.listbox.curselection()
        if selection:
            display_text = self.listbox.get(selection[0])
            obj_id = self.component_map.get(display_text)
            if obj_id:
                self._show_object_details(obj_id)

    def _on_list_double_click(self, event, selected_object_id, root_window):
        """Handle list double click"""
        selection = self.listbox.curselection()
        if selection:
            display_text = self.listbox.get(selection[0])
            obj_id = self.component_map.get(display_text)
            if obj_id:
                selected_object_id.set(obj_id)
                root_window.destroy()

    def _on_select_button(self, selected_object_id, root_window):
        """Handle select button click"""
        selection = self.listbox.curselection()
        if selection:
            display_text = self.listbox.get(selection[0])
            obj_id = self.component_map.get(display_text)
            if obj_id:
                selected_object_id.set(obj_id)
                root_window.destroy()
        else:
            messagebox.showwarning("Warning", "Please select a component first")

    def _show_object_details(self, object_id):
        """Show details for selected object"""
        self.details_text.delete(1.0, tk.END)

        if object_id and object_id in self.object_ids:
            obj_info = self.object_ids[object_id]
            self.details_text.insert(tk.END, f"Name: {obj_info['name']}\n")
            self.details_text.insert(tk.END, f"Type: {obj_info['type']}\n")
            self.details_text.insert(tk.END, f"ObjectID: {object_id}\n")
            self.details_text.insert(tk.END, f"Description: {obj_info['description']}\n")

            if obj_info.get('parent'):
                self.details_text.insert(tk.END, f"Parent: {obj_info['parent']}\n")

            # Show ST code preview
            element = obj_info['element']
            body = element.find(f"{self.namespace}body")
            if body is not None:
                st_elem = body.find(f"{self.namespace}ST")
                if st_elem is not None and st_elem.text:
                    st_preview = st_elem.text.strip()
                    if st_preview:
                        self.details_text.insert(tk.END, f"\nST Code Preview:\n{st_preview}\n")

            self.details_text.insert(tk.END, f"\n\nDouble-click or click 'Select Component' to choose this component")
        else:
            self.details_text.insert(tk.END, "No component selected")

    def _convert_to_mermaid(self, object_id: str, output_dir: str):
        """Convert selected component to Mermaid flowchart"""
        logger.info(f"Converting ObjectID {object_id} to Mermaid...")

        if object_id not in self.object_ids:
            messagebox.showerror("Error", f"ObjectID {object_id} not found")
            return

        # Get component info
        component_info = self.object_ids[object_id]

        # Set namespace in mermaid processor
        self.mermaid_processor.set_namespace(self.namespace)

        # Convert the main component
        success = self.mermaid_processor.convert_component(
            component_info,
            output_dir,
            include_logic=self.include_logic.get(),
            include_interface=self.include_interface.get()
        )

        # If it's a POU, also convert all its actions
        if success and component_info['type'] == 'POU':
            self._convert_pou_actions(component_info, output_dir)

        if success:
            logger.info(f"Successfully generated Mermaid files in {output_dir}")
            messagebox.showinfo("Success", f"Mermaid files generated in:\n{output_dir}")
            self.status_var.set("Conversion completed successfully")
        else:
            messagebox.showerror("Error", "Failed to generate Mermaid files")
            self.status_var.set("Conversion failed")

    def _convert_pou_actions(self, pou_info: Dict, output_dir: str):
        """Convert all actions within a POU"""
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

                # Convert the action
                self.mermaid_processor.convert_component(
                    action_info,
                    output_dir,
                    include_logic=self.include_logic.get(),
                    include_interface=self.include_interface.get()
                )