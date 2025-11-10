import os
import logging
from typing import Dict, Optional, List
from st_processor import STProcessor
from ld_processor import LDProcessor
from cfc_processor import CFCProcessor
from fbd_processor import FBDProcessor

logger = logging.getLogger(__name__)


class MermaidProcessor:
    def __init__(self):
        self.namespace = ''
        self.st_processor = STProcessor()
        self.ld_processor = LDProcessor()
        self.cfc_processor = CFCProcessor()
        self.fbd_processor = FBDProcessor()

    def set_namespace(self, namespace: str):
        """Set the XML namespace for processing"""
        self.namespace = namespace
        logger.info(f"Mermaid processor namespace set to: {namespace}")

        # Pass namespace to all processors
        self.st_processor.set_namespace(namespace)
        self.ld_processor.set_namespace(namespace)
        self.cfc_processor.set_namespace(namespace)
        self.fbd_processor.set_namespace(namespace)

    def convert_component(self, component_info: Dict, output_dir: str,
                          include_logic: bool = True, include_interface: bool = True) -> bool:
        """Convert a component to Mermaid format"""
        try:
            os.makedirs(output_dir, exist_ok=True)
            element = component_info['element']
            name = component_info['name']
            comp_type = component_info['type']

            logger.info(f"Converting {comp_type}: {name} to directory: {output_dir}")

            files_created = []

            # Extract body content (ST code)
            if include_logic:
                logger.debug(f"Processing logic for {name}")
                body_files = self._convert_body_to_mermaid(element, name, output_dir)
                files_created.extend(body_files)
                logger.debug(f"Body files created: {body_files}")

            # Extract interface (variables)
            if include_interface:
                logger.debug(f"Processing interface for {name}")
                interface_files = self._convert_interface_to_mermaid(element, name, output_dir)
                files_created.extend(interface_files)
                logger.debug(f"Interface files created: {interface_files}")

            logger.info(f"Created {len(files_created)} files: {files_created}")
            return len(files_created) > 0

        except Exception as e:
            logger.error(f"Conversion failed for {component_info.get('name', 'unknown')}: {str(e)}")
            return False

    def _convert_body_to_mermaid(self, element, name: str, output_dir: str) -> List[str]:
        """Convert body content to Mermaid flowchart"""
        files_created = []

        # Look for body in the element
        body = element.find(f"{self.namespace}body")
        if body is not None:
            logger.debug(f"Found body for {name}")

            # Debug: Check what's in the body
            logger.debug(f"Body children: {[child.tag for child in body]}")

            # Try different code formats
            mermaid_code = self._parse_code_body(body, name)
            if mermaid_code:
                filename = os.path.join(output_dir, f"{self._sanitize_filename(name)}_logic.mmd")
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(mermaid_code)
                files_created.append(filename)
                logger.info(f"Created logic file: {filename} with {len(mermaid_code)} characters")
            else:
                logger.warning(f"No Mermaid code generated for body of {name}")
        else:
            logger.warning(f"No body found for {name}")

        return files_created

    def _parse_code_body(self, body_element, name: str) -> Optional[str]:
        """Parse code body and detect format (ST, LD, CFC, etc.)"""
        logger.info(f"=== Parsing code body for {name} ===")

        # Check for ST code
        st_code = self.st_processor.extract_code(body_element, name)
        if st_code:
            logger.info(f"Found ST code for {name}, length: {len(st_code)}")
            return self.st_processor.convert_to_mermaid(st_code, name)

        # Check for LD (Ladder Diagram)
        ld_code = self.ld_processor.extract_code(body_element, name)
        if ld_code:
            logger.info(f"Found LD code for {name}")
            return self.ld_processor.convert_to_mermaid(ld_code, name)

        # Check for CFC
        cfc_code = self.cfc_processor.extract_code(body_element, name)
        if cfc_code:
            logger.info(f"Found CFC code for {name}")
            return self.cfc_processor.convert_to_mermaid(cfc_code, name)

        # Check for FBD
        fbd_code = self.fbd_processor.extract_code(body_element, name)
        if fbd_code:
            logger.info(f"Found FBD code for {name}")
            return self.fbd_processor.convert_to_mermaid(fbd_code, name)

        logger.warning(f"No supported code format found for {name}")
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
                logger.debug(f"Created interface file: {filename}")

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
                logger.warning(f"No variables found in interface for {name}")
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
        # Remove spaces and special characters
        name = ''.join(c if c.isalnum() else '_' for c in name)
        # Ensure it starts with a letter
        if name and not name[0].isalpha():
            name = 'Class_' + name
        return name