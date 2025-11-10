import os
import logging
import xml.etree.ElementTree as ET
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


class DiagnosticProcessor:
    def __init__(self):
        self.namespace = ''

    def set_namespace(self, namespace: str):
        """Set the XML namespace"""
        self.namespace = namespace
        logger.info(f"Diagnostic processor namespace set to: {namespace}")

    def analyze_component(self, component_info: Dict, output_dir: str) -> bool:
        """Create a detailed analysis of the component structure"""
        try:
            os.makedirs(output_dir, exist_ok=True)
            element = component_info['element']
            name = component_info['name']
            comp_type = component_info['type']

            logger.info(f"=== DIAGNOSTIC ANALYSIS for {name} ({comp_type}) ===")

            # Create diagnostic report
            diagnostic_report = self._create_diagnostic_report(element, name, comp_type)

            filename = os.path.join(output_dir, f"{self._sanitize_filename(name)}_diagnostic.txt")
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(diagnostic_report)

            logger.info(f"Created diagnostic file: {filename}")
            print(f"\n=== DIAGNOSTIC REPORT for {name} ===")
            print(diagnostic_report)

            return True

        except Exception as e:
            logger.error(f"Diagnostic analysis failed for {component_info.get('name', 'unknown')}: {str(e)}")
            return False

    def _create_diagnostic_report(self, element, name: str, comp_type: str) -> str:
        """Create a comprehensive diagnostic report"""
        report_lines = []

        report_lines.append(f"DIAGNOSTIC REPORT for {name} ({comp_type})")
        report_lines.append("=" * 50)
        report_lines.append(f"Namespace: {self.namespace}")
        report_lines.append(f"Element tag: {element.tag}")
        report_lines.append(f"Element attributes: {element.attrib}")
        report_lines.append("")

        # Analyze interface
        report_lines.append("INTERFACE ANALYSIS:")
        report_lines.append("-" * 20)
        interface = element.find(f"{self.namespace}interface")
        if interface is not None:
            report_lines.append("✓ Interface found")
            variables = interface.findall(f".//{self.namespace}variable")
            report_lines.append(f"Number of variables: {len(variables)}")

            for i, var in enumerate(variables):
                name_elem = var.find(f"{self.namespace}name")
                type_elem = var.find(f"{self.namespace}type")
                report_lines.append(f"  Variable {i}:")
                report_lines.append(f"    Name: {name_elem.text if name_elem else 'None'}")
                report_lines.append(f"    Type: {self._get_type_name(type_elem) if type_elem else 'None'}")
        else:
            report_lines.append("✗ No interface found")
        report_lines.append("")

        # Analyze body
        report_lines.append("BODY ANALYSIS:")
        report_lines.append("-" * 20)
        body = element.find(f"{self.namespace}body")
        if body is not None:
            report_lines.append("✓ Body found")
            report_lines.append(f"Body attributes: {body.attrib}")
            report_lines.append(f"Body direct text: '{body.text if body.text else 'None'}'")
            report_lines.append("")

            # Analyze body children
            body_children = list(body)
            report_lines.append(f"Number of body children: {len(body_children)}")

            for i, child in enumerate(body_children):
                report_lines.append(f"  Child {i}: {child.tag}")
                report_lines.append(f"    Attributes: {child.attrib}")
                report_lines.append(f"    Direct text: '{child.text if child.text else 'None'}'")
                report_lines.append(f"    Number of sub-children: {len(list(child))}")

                # Analyze sub-children
                for j, subchild in enumerate(child):
                    report_lines.append(f"      Sub-child {j}: {subchild.tag}")
                    report_lines.append(f"        Attributes: {subchild.attrib}")
                    report_lines.append(f"        Direct text: '{subchild.text if subchild.text else 'None'}'")

                    # Look for any text content in this branch
                    all_text = self._extract_all_text(subchild)
                    if all_text:
                        report_lines.append(f"        All text content ({len(all_text)} chars):")
                        report_lines.append(f"        '{all_text[:500]}{'...' if len(all_text) > 500 else ''}'")
        else:
            report_lines.append("✗ No body found")
        report_lines.append("")

        # Look for implementation
        report_lines.append("IMPLEMENTATION ANALYSIS:")
        report_lines.append("-" * 25)
        implementation = element.find(f"{self.namespace}implementation")
        if implementation is not None:
            report_lines.append("✓ Implementation found")
            impl_children = list(implementation)
            report_lines.append(f"Number of implementation children: {len(impl_children)}")

            for i, child in enumerate(impl_children):
                report_lines.append(f"  Implementation child {i}: {child.tag}")
                report_lines.append(f"    Text: '{child.text if child.text else 'None'}'")
        else:
            report_lines.append("✗ No implementation found")
        report_lines.append("")

        # Look for any ST, LD, CFC, FBD elements anywhere
        report_lines.append("CODE FORMAT SEARCH:")
        report_lines.append("-" * 20)
        code_formats = ['ST', 'LD', 'CFC', 'FBD', 'SFC', 'IL']
        for code_format in code_formats:
            elements = element.findall(f".//{self.namespace}{code_format}")
            report_lines.append(f"{code_format}: Found {len(elements)} elements")
            for i, elem in enumerate(elements):
                report_lines.append(f"  {code_format} element {i}:")
                report_lines.append(f"    Text: '{elem.text if elem.text else 'None'}'")
                if elem.text and len(elem.text.strip()) > 0:
                    report_lines.append(f"    Text length: {len(elem.text.strip())} characters")
                    report_lines.append(
                        f"    Preview: {elem.text.strip()[:100]}{'...' if len(elem.text.strip()) > 100 else ''}")
        report_lines.append("")

        # Recursive search for any text content
        report_lines.append("COMPLETE TEXT CONTENT SEARCH:")
        report_lines.append("-" * 30)
        all_text = self._extract_all_text(element)
        if all_text:
            report_lines.append(f"Found {len(all_text)} characters of text content:")
            report_lines.append(f"'{all_text[:1000]}{'...' if len(all_text) > 1000 else ''}'")
        else:
            report_lines.append("No text content found anywhere in element")

        return '\n'.join(report_lines)

    def _extract_all_text(self, element) -> str:
        """Extract all text content recursively"""
        texts = []

        # Add element's own text
        if element.text and element.text.strip():
            texts.append(element.text.strip())

        # Add text from all children recursively
        for child in element:
            child_text = self._extract_all_text(child)
            if child_text:
                texts.append(child_text)

        return '\n'.join(texts)

    def _get_type_name(self, type_element) -> str:
        """Extract type name from type element"""
        if type_element is None:
            return "Unknown"

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