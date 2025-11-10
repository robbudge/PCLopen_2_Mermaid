import os
import logging
from typing import Dict, List, Set, Optional
from st_processor import STProcessor
from ld_processor import LDProcessor
from cfc_processor import CFCProcessor
from fbd_processor import FBDProcessor

logger = logging.getLogger(__name__)


class HierarchicalProcessor:
    def __init__(self, gui_manager):
        self.gui_manager = gui_manager
        self.st_processor = STProcessor()
        self.ld_processor = LDProcessor()
        self.cfc_processor = CFCProcessor()
        self.fbd_processor = FBDProcessor()
        self.processed_components: Set[str] = set()
        self.component_hierarchy: Dict[str, List[str]] = {}

    def set_namespace(self, namespace: str):
        """Set the XML namespace for processing"""
        self.namespace = namespace
        self.st_processor.set_namespace(namespace)
        self.ld_processor.set_namespace(namespace)
        self.cfc_processor.set_namespace(namespace)
        self.fbd_processor.set_namespace(namespace)

    def process_component_hierarchically(self, component_info: Dict, output_dir: str,
                                         include_logic: bool = True, include_interface: bool = True) -> bool:
        """Process a component and all its called components hierarchically"""
        try:
            os.makedirs(output_dir, exist_ok=True)
            component_id = self._get_component_id(component_info)

            if component_id in self.processed_components:
                logger.info(f"Component {component_info['name']} already processed, skipping")
                return True

            self.processed_components.add(component_id)
            logger.info(f"=== Processing {component_info['name']} hierarchically ===")

            # First, process all called components
            called_components = self._find_called_components(component_info)
            logger.info(f"Found {len(called_components)} called components: {[c['name'] for c in called_components]}")

            # Process called components first (depth-first)
            for called_component in called_components:
                called_id = self._get_component_id(called_component)
                if called_id not in self.processed_components:
                    self.process_component_hierarchically(called_component, output_dir, include_logic,
                                                          include_interface)

            # Now process the current component with knowledge of its calls
            return self._process_component_with_hierarchy(component_info, output_dir, include_logic, include_interface)

        except Exception as e:
            logger.error(f"Hierarchical processing failed for {component_info.get('name', 'unknown')}: {str(e)}")
            return False

    def _get_component_id(self, component_info: Dict) -> str:
        """Get unique identifier for component"""
        return f"{component_info['name']}_{component_info.get('type', 'unknown')}"

    def _find_called_components(self, component_info: Dict) -> List[Dict]:
        """Find all components called by this component"""
        called_components = []
        element = component_info['element']

        # Extract ST code to find function calls
        st_code = self._extract_st_code(element)
        if st_code:
            calls = self._find_function_calls_in_st(st_code)
            for call in calls:
                component = self._find_component_by_name(call)
                if component:
                    called_components.append(component)

        # Also check for actions within this POU
        if component_info['type'] == 'POU':
            actions = element.findall(f".//{self.namespace}action")
            for action in actions:
                action_name = action.get('name')
                if action_name:
                    # This action is a sub-component of the POU
                    action_component = {
                        'name': f"{component_info['name']}.{action_name}",
                        'type': 'Action',
                        'element': action,
                        'description': f"Action {action_name} in {component_info['name']}",
                        'parent': self._get_component_id(component_info)
                    }
                    called_components.append(action_component)

        return called_components

    def _extract_st_code(self, element) -> Optional[str]:
        """Extract ST code from element"""
        body = element.find(f"{self.namespace}body")
        if body is not None:
            return self.st_processor.extract_code_from_element(body, "temp")
        return None

    def _find_function_calls_in_st(self, st_code: str) -> List[str]:
        """Find function calls in ST code"""
        calls = []

        # Look for patterns like FunctionName(), POU_Name(), etc.
        patterns = [
            r'(\w+)\(\)',  # Function calls with ()
            r'(\w+)\s*\(',  # Function calls with parameters
            r'(\w+);',  # Function calls without parameters
        ]

        for pattern in patterns:
            matches = re.findall(pattern, st_code)
            calls.extend(matches)

        # Filter out common keywords and system functions
        excluded_keywords = {'IF', 'THEN', 'ELSE', 'END_IF', 'CASE', 'OF', 'END_CASE',
                             'FOR', 'WHILE', 'REPEAT', 'END_FOR', 'END_WHILE', 'END_REPEAT'}

        filtered_calls = []
        for call in calls:
            call_clean = call.strip()
            if (call_clean and
                    not call_clean.upper() in excluded_keywords and
                    not call_clean.startswith('END') and
                    len(call_clean) > 2):  # Filter out very short names
                filtered_calls.append(call_clean)

        return list(set(filtered_calls))  # Remove duplicates

    def _find_component_by_name(self, name: str) -> Optional[Dict]:
        """Find a component by name in the object_ids"""
        # First try exact match
        for obj_id, component in self.gui_manager.object_ids.items():
            if component['name'] == name:
                return component

        # Try partial matches (for actions like "Task_OFF" when called as "Task_OFF()")
        for obj_id, component in self.gui_manager.object_ids.items():
            if name in component['name'] or component['name'] in name:
                return component

        return None

    def _process_component_with_hierarchy(self, component_info: Dict, output_dir: str,
                                          include_logic: bool, include_interface: bool) -> bool:
        """Process a single component with hierarchical awareness"""
        name = component_info['name']
        comp_type = component_info['type']

        logger.info(f"Processing {comp_type}: {name} with hierarchy")

        files_created = []

        # Process main logic with subgraphs for called components
        if include_logic:
            hierarchical_mermaid = self._create_hierarchical_mermaid(component_info, output_dir)
            if hierarchical_mermaid:
                filename = os.path.join(output_dir, f"{self._sanitize_filename(name)}_hierarchical.mmd")
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(hierarchical_mermaid)
                files_created.append(filename)
                logger.info(f"Created hierarchical file: {filename}")

        # Also create standalone version
        if include_logic:
            standalone_mermaid = self._create_standalone_mermaid(component_info)
            if standalone_mermaid:
                filename = os.path.join(output_dir, f"{self._sanitize_filename(name)}_standalone.mmd")
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(standalone_mermaid)
                files_created.append(filename)

        # Process interface
        if include_interface:
            interface_files = self._convert_interface_to_mermaid(component_info['element'], name, output_dir)
            files_created.extend(interface_files)

        return len(files_created) > 0

    def _create_hierarchical_mermaid(self, component_info: Dict, output_dir: str) -> str:
        """Create Mermaid flowchart with subgraphs for called components"""
        name = component_info['name']
        element = component_info['element']

        # Get the base flowchart
        base_flowchart = self._create_standalone_mermaid(component_info)
        if not base_flowchart:
            return None

        # Find called components for this specific component
        called_components = self._find_called_components(component_info)

        if not called_components:
            return base_flowchart  # No subcomponents, return base flowchart

        # Convert base flowchart to hierarchical version with subgraphs
        lines = base_flowchart.split('\n')
        hierarchical_lines = []

        # Add subgraph definitions before the main flowchart
        hierarchical_lines.extend(self._create_subgraph_definitions(called_components, output_dir))
        hierarchical_lines.append("")  # Empty line for separation
        hierarchical_lines.extend(lines)

        # Replace action calls with subgraph links
        final_lines = self._replace_calls_with_subgraphs(hierarchical_lines, called_components)

        return '\n'.join(final_lines)

    def _create_subgraph_definitions(self, called_components: List[Dict], output_dir: str) -> List[str]:
        """Create subgraph definitions for called components"""
        subgraph_lines = []

        for component in called_components:
            comp_name = component['name']
            safe_name = self._sanitize_subgraph_name(comp_name)

            # First, ensure the called component has its own flowchart
            self._ensure_component_flowchart(component, output_dir)

            subgraph_lines.append(f"    subgraph {safe_name}[\"{comp_name}\"]")
            subgraph_lines.append(f"        direction TB")
            subgraph_lines.append(f"        {safe_name}_Start[\"Start: {comp_name}\"]")
            subgraph_lines.append(f"        {safe_name}_Logic[Logic processing...]")
            subgraph_lines.append(f"        {safe_name}_End[\"End: {comp_name}\"]")
            subgraph_lines.append(f"        {safe_name}_Start --> {safe_name}_Logic")
            subgraph_lines.append(f"        {safe_name}_Logic --> {safe_name}_End")
            subgraph_lines.append(f"    end")

        return subgraph_lines

    def _ensure_component_flowchart(self, component: Dict, output_dir: str):
        """Ensure a component has its own flowchart file"""
        comp_name = component['name']
        standalone_file = os.path.join(output_dir, f"{self._sanitize_filename(comp_name)}_standalone.mmd")

        if not os.path.exists(standalone_file):
            # Create standalone flowchart for this component
            standalone_mermaid = self._create_standalone_mermaid(component)
            if standalone_mermaid:
                with open(standalone_file, 'w', encoding='utf-8') as f:
                    f.write(standalone_mermaid)
                logger.info(f"Created standalone flowchart for called component: {comp_name}")

    def _replace_calls_with_subgraphs(self, lines: List[str], called_components: List[Dict]) -> List[str]:
        """Replace action calls with subgraph links in the flowchart"""
        new_lines = []

        for line in lines:
            new_line = line
            for component in called_components:
                comp_name = component['name']
                safe_name = self._sanitize_subgraph_name(comp_name)

                # Look for lines that call this component
                if f"[\"{comp_name}()\"]" in line or f"[\"{comp_name}\"]" in line:
                    # Replace the action node with a link to the subgraph
                    node_match = re.search(r'(\w+)\[.*\]', line)
                    if node_match:
                        node_name = node_match.group(1)
                        new_line = f"    {node_name}([\"{comp_name}\"])"
                        # Add connection to subgraph
                        new_lines.append(new_line)
                        new_lines.append(f"    click {node_name} \"#{safe_name}\"")
                        break

            if new_line == line:  # No replacement happened
                new_lines.append(line)

        return new_lines

    def _create_standalone_mermaid(self, component_info: Dict) -> str:
        """Create standalone Mermaid flowchart for a component"""
        element = component_info['element']
        name = component_info['name']

        # Use the appropriate processor based on content
        body = element.find(f"{self.namespace}body")
        if body is not None:
            # Try ST first
            st_code = self.st_processor.extract_code_from_element(body, name)
            if st_code:
                return self.st_processor.convert_to_mermaid(st_code, name)

            # Try other formats...
            # (LD, CFC, FBD would go here)

        return None

    def _convert_interface_to_mermaid(self, element, name: str, output_dir: str) -> list:
        """Convert interface to Mermaid class diagram"""
        files_created = []

        interface = element.find(f"{self.namespace}interface")
        if interface is not None:
            mermaid_code = self._parse_interface(interface, name)
            if mermaid_code:
                filename = os.path.join(output_dir, f"{self._sanitize_filename(name)}_interface.mmd")
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(mermaid_code)
                files_created.append(filename)

        return files_created

    def _parse_interface(self, interface_element, name: str) -> Optional[str]:
        """Parse POU interface and create Mermaid class diagram"""
        try:
            mermaid_lines = [
                "%% Mermaid class diagram for interface",
                f"%% Component: {name}",
                "",
                "classDiagram",
                f"    class {self._sanitize_class_name(name)} {{"
            ]

            variables = interface_element.findall(f".//{self.namespace}variable")
            variable_count = 0

            for var in variables:
                name_elem = var.find(f"{self.namespace}name")
                type_elem = var.find(f"{self.namespace}type")

                if name_elem is not None and type_elem is not None:
                    var_name = name_elem.text or "Unknown"
                    var_type = self._get_type_name(type_elem)
                    mermaid_lines.append(f"        {var_type} {var_name}")
                    variable_count += 1

            mermaid_lines.append("    }")

            if variable_count > 0:
                return '\n'.join(mermaid_lines)
            else:
                return None

        except Exception as e:
            logger.error(f"Error parsing interface for {name}: {str(e)}")
            return None

    def _get_type_name(self, type_element) -> str:
        """Extract type name from type element"""
        derived = type_element.find(f"{self.namespace}derived")
        if derived is not None:
            return derived.get('name', 'Unknown')

        base_type = type_element.find(f"{self.namespace}baseType")
        if base_type is not None:
            return base_type.text or 'Unknown'

        return 'Unknown'

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize filename by removing invalid characters"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        return name

    def _sanitize_class_name(self, name: str) -> str:
        """Sanitize class name for Mermaid"""
        name = ''.join(c if c.isalnum() else '_' for c in name)
        if name and not name[0].isalpha():
            name = 'Class_' + name
        return name

    def _sanitize_subgraph_name(self, name: str) -> str:
        """Sanitize name for Mermaid subgraph"""
        return re.sub(r'[^a-zA-Z0-9_]', '_', name)