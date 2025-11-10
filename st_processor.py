import logging
import re
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class STProcessor:
    def __init__(self):
        self.namespace = ''

    def set_namespace(self, namespace: str):
        """Set the XML namespace"""
        self.namespace = namespace
        logger.info(f"STProcessor namespace set to: {namespace}")

    def extract_code(self, body_element, name: str) -> Optional[str]:
        """Extract ST code from body element - handles xhtml wrapper"""
        try:
            # Method 1: Look for direct ST element
            st_elem = body_element.find(f"{self.namespace}ST")

            if st_elem is not None:
                logger.info(f"Found direct ST element for {name}")

                # Check for xhtml wrapper inside ST element
                xhtml_elem = st_elem.find(f"{self.namespace}xhtml")
                if xhtml_elem is not None:
                    logger.info(f"Found xhtml wrapper inside ST element for {name}")
                    if xhtml_elem.text:
                        code = xhtml_elem.text
                        logger.info(f"xhtml element has text content: {len(code)} characters")

                        stripped_code = code.strip()
                        if stripped_code:
                            logger.info(f"ST code contains actual content: {len(stripped_code)} characters")
                            logger.info(f"First 200 chars: {stripped_code[:200]}")
                            return stripped_code
                        else:
                            logger.warning(f"xhtml element for {name} exists but contains only whitespace")
                    else:
                        logger.warning(f"xhtml element for {name} exists but has no text content")

                # Method 2: Check for direct text in ST element (fallback)
                if st_elem.text:
                    code = st_elem.text
                    logger.info(f"ST element has direct text content: {len(code)} characters")

                    stripped_code = code.strip()
                    if stripped_code:
                        logger.info(f"ST direct text contains content: {len(stripped_code)} characters")
                        logger.info(f"First 200 chars: {stripped_code[:200]}")
                        return stripped_code
                    else:
                        logger.warning(f"ST element for {name} has direct text but only whitespace")

                # Method 3: Check all text content recursively
                all_text = self._extract_all_text(st_elem)
                if all_text and all_text.strip():
                    logger.info(f"Found text content recursively: {len(all_text.strip())} characters")
                    return all_text.strip()

                logger.warning(f"ST element for {name} exists but no code content found in any location")
                return None

            logger.warning(f"No ST element found for {name}")
            return None

        except Exception as e:
            logger.error(f"Error extracting ST code for {name}: {str(e)}")
            return None

    def _extract_all_text(self, element) -> str:
        """Extract all text content recursively from an element and its children"""
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

    def convert_to_mermaid(self, st_code: str, name: str) -> str:
        """Convert ST code to Mermaid flowchart"""
        try:
            logger.info(f"Converting ST to Mermaid for {name}, code length: {len(st_code)} characters")

            if not st_code or st_code.strip() == "":
                logger.warning(f"Empty ST code for {name}")
                return self._create_empty_mermaid(name)

            # Get code statistics for logging
            stats = self.get_code_statistics(st_code)
            logger.info(f"ST code statistics: {stats}")

            # Start with flowchart declaration
            mermaid_lines = [
                "%% ST to Mermaid Flowchart Conversion",
                f"%% Program: {name}",
                f"%% Original code length: {len(st_code)} characters",
                f"%% Lines: {stats['total_lines']} total, {stats['non_empty_lines']} non-empty",
                f"%% Max line length: {stats['max_line_length']} characters",
                f"%% No line length limits applied - all content preserved",
                "",
                "flowchart TD",
            ]

            # For relatively small code, use simple representation
            if len(st_code) < 2000:
                escaped_code = self._escape_mermaid_text(st_code)
                mermaid_lines.extend([
                    f'    start["{name} - ST Program"]',
                    f'    code["ST Code\\n{escaped_code}"]',
                    "    start --> code"
                ])
            else:
                # Split into logical sections but don't truncate
                escaped_code = self._escape_mermaid_text(st_code)
                sections = self._split_into_sections(escaped_code)

                logger.info(f"Split ST code into {len(sections)} logical sections")

                if len(sections) == 1:
                    # Single section - use complete code in one node
                    mermaid_lines.extend([
                        f'    start["{name} - ST Program"]',
                        f'    code1["ST Code\\n{sections[0]}"]',
                        "    start --> code1"
                    ])
                else:
                    # Multiple sections - create flow
                    mermaid_lines.append(f'    start["{name} - ST Program"]')

                    for i, section in enumerate(sections, 1):
                        node_id = f"section{i}"
                        # NO LENGTH LIMITS - use full section content
                        mermaid_lines.append(f'    {node_id}["Section {i}\\n{section}"]')

                        if i == 1:
                            mermaid_lines.append("    start --> section1")
                        else:
                            mermaid_lines.append(f'    section{i - 1} --> {node_id}')

            result = '\n'.join(mermaid_lines)
            logger.info(
                f"Generated Mermaid with {len(result)} characters, {len(sections) if 'sections' in locals() else 1} sections")
            return result

        except Exception as e:
            logger.error(f"Error converting ST to Mermaid for {name}: {str(e)}")
            return self._create_fallback_mermaid(st_code, name)

    def _split_into_sections(self, code: str) -> List[str]:
        """Split code into logical sections without length limits"""
        try:
            # If code is relatively short, don't split it
            if len(code) < 2000:
                return [code]

            sections = []
            current_section = []
            lines = code.split('\n')

            for line in lines:
                line = line.strip()
                if line:
                    current_section.append(line)

                    # Split at logical boundaries, not length boundaries
                    if self._is_logical_boundary(line):
                        if current_section:
                            section_text = '\n'.join(current_section)
                            sections.append(section_text)
                            current_section = []

            # Add any remaining lines
            if current_section:
                section_text = '\n'.join(current_section)
                sections.append(section_text)

            # If no logical splits found or only one section, return the whole code
            if len(sections) <= 1:
                return [code]

            return sections

        except Exception as e:
            logger.error(f"Error splitting ST code into sections: {str(e)}")
            # Return entire code as one section if splitting fails
            return [code]

    def _is_logical_boundary(self, line: str) -> bool:
        """Check if a line represents a logical boundary in ST code"""
        line_upper = line.upper().strip()

        # Keywords that typically end logical blocks
        boundary_keywords = [
            'END_IF', 'END_IF;',
            'END_FOR', 'END_FOR;',
            'END_WHILE', 'END_WHILE;',
            'END_REPEAT', 'END_REPEAT;',
            'END_CASE', 'END_CASE;',
            'END_FUNCTION', 'END_FUNCTION;',
            'END_FUNCTION_BLOCK', 'END_FUNCTION_BLOCK;',
            'END_PROGRAM', 'END_PROGRAM;',
            'END_ACTION', 'END_ACTION;',
            'END_STRUCT', 'END_STRUCT;',
            'END_TYPE', 'END_TYPE;'
        ]

        # Check for boundary keywords
        if any(keyword == line_upper or keyword in line_upper for keyword in boundary_keywords):
            return True

        # Check for semicolon endings (statement terminators)
        if line_upper.endswith(';'):
            return True

        # Check for block starts that should separate from previous content
        block_starts = ['IF ', 'FOR ', 'WHILE ', 'REPEAT ', 'CASE ', 'FUNCTION ', 'FUNCTION_BLOCK ', 'PROGRAM ']
        if any(line_upper.startswith(start) for start in block_starts):
            return True

        return False

    def _escape_mermaid_text(self, text: str) -> str:
        """Escape text for Mermaid syntax - preserve all content"""
        if text is None:
            return ""

        # First replace newlines with Mermaid newline indicator
        text = text.replace('\n', '\\n')

        # Then handle quotes and other special characters that break Mermaid
        replacements = {
            '"': '#quot;',
            '\r': '',  # Remove carriage returns
            '\t': '    ',  # Convert tabs to spaces
            '{': '\\{',
            '}': '\\}',
            '[': '\\[',
            ']': '\\]',
            '(': '\\(',
            ')': '\\)',
        }

        for find, replace in replacements.items():
            text = text.replace(find, replace)

        return text

    def _create_empty_mermaid(self, name: str) -> str:
        """Create Mermaid for empty ST code"""
        return f"""flowchart TD
    empty["{name} - No ST Code"]
    note["ST element exists but contains no executable code"]
    empty --> note

%% No ST code content found for {name}
"""

    def _create_fallback_mermaid(self, st_code: str, name: str) -> str:
        """Create a fallback Mermaid diagram with full code"""
        escaped_code = self._escape_mermaid_text(st_code)

        return f"""flowchart TD
    start["{name} - ST Program"]
    code["Complete ST Code\\n{escaped_code}"]
    start --> code

%% Fallback diagram generated due to conversion error
%% Original code length: {len(st_code)} characters
%% All content preserved without truncation
"""

    def get_code_statistics(self, st_code: str) -> Dict[str, Any]:
        """Get statistics about the ST code"""
        if not st_code:
            return {
                'total_lines': 0,
                'non_empty_lines': 0,
                'total_characters': 0,
                'avg_line_length': 0,
                'max_line_length': 0
            }

        lines = st_code.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]

        line_lengths = [len(line) for line in lines if line]
        max_line_length = max(line_lengths) if line_lengths else 0
        avg_line_length = sum(line_lengths) / len(line_lengths) if line_lengths else 0

        return {
            'total_lines': len(lines),
            'non_empty_lines': len(non_empty_lines),
            'total_characters': len(st_code),
            'avg_line_length': round(avg_line_length, 2),
            'max_line_length': max_line_length
        }