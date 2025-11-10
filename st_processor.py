import logging
import re
from typing import Dict, Optional, List, Tuple

logger = logging.getLogger(__name__)


class STProcessor:
    def __init__(self):
        self.namespace = ''

    def set_namespace(self, namespace: str):
        """Set the XML namespace for processing"""
        self.namespace = namespace

    def extract_code(self, body_element, name: str) -> Optional[str]:
        """Extract ST code from body element"""
        logger.debug(f"Looking for ST code in {name}")

        # Find ST elements
        st_elements = body_element.findall(f".//{self.namespace}ST")
        logger.debug(f"Found {len(st_elements)} ST elements")

        all_st_code = ""

        for i, st_elem in enumerate(st_elements):
            logger.debug(f"Processing ST element {i + 1}")

            # Method 1: Direct text content
            direct_text = st_elem.text or ""
            if direct_text.strip():
                logger.debug(f"Found direct ST text: {len(direct_text)} chars")
                all_st_code += direct_text + "\n"

            # Method 2: Text in xhtml wrapper
            xhtml_elem = st_elem.find(f".//{self.namespace}xhtml")
            if xhtml_elem is None:
                # Also try without namespace
                xhtml_elem = st_elem.find(".//xhtml")

            if xhtml_elem is not None:
                xhtml_text = xhtml_elem.text or ""
                if xhtml_text.strip():
                    logger.debug(f"Found XHTML wrapped ST text: {len(xhtml_text)} chars")
                    all_st_code += xhtml_text + "\n"

            # Method 3: Try to get all text content recursively
            full_text = self._get_element_text(st_elem)
            if full_text.strip() and full_text != direct_text:
                logger.debug(f"Found recursive ST text: {len(full_text)} chars")
                all_st_code += full_text + "\n"

        if all_st_code.strip():
            logger.info(f"Extracted ST code for {name}: {len(all_st_code)} characters")
            logger.debug(f"First 200 chars: {all_st_code[:200]}...")
            return all_st_code.strip()
        else:
            logger.debug(f"No ST code found for {name}")
            return None

    def _get_element_text(self, element) -> str:
        """Recursively extract all text from an element"""
        text = element.text or ""
        for child in element:
            text += self._get_element_text(child)
            if child.tail:
                text += child.tail
        return text

    def convert_to_mermaid(self, st_code: str, name: str) -> str:
        """Convert ST code to Mermaid flowchart"""
        logger.info(f"Converting ST code to Mermaid for {name}")

        mermaid_lines = [
            "%% Mermaid flowchart for ST logic",
            "%% Generated from PLCopen XML export",
            f"%% Component: {name}",
            f"%% ST Code Length: {len(st_code)} characters",
            "",
            "flowchart TD",
            f"    Start[\"Start: {name}\"]"
        ]

        # Process ST code with improved logic
        processed_lines, last_node = self._process_st_code_improved(st_code, name)
        mermaid_lines.extend(processed_lines)

        # Connect last node to End
        if last_node and last_node != "Start":
            mermaid_lines.append(f"    {last_node} --> End")

        mermaid_lines.append(f"    End[\"End: {name}\"]")

        result = '\n'.join(mermaid_lines)
        logger.info(f"Generated Mermaid flowchart with {len(mermaid_lines)} lines")
        return result

    def _process_st_code_improved(self, st_code: str, component_name: str) -> Tuple[List[str], str]:
        """Improved ST code processing with proper CASE statement handling"""
        logger.debug(f"Processing ST code for {component_name}")

        lines = []
        st_lines = st_code.strip().split('\n')

        logger.debug(f"ST code has {len(st_lines)} lines")

        node_num = 1
        last_action_node = "Start"
        in_case_statement = False
        case_start_node = None
        case_condition_node = None
        case_end_node = None
        case_branches = []  # Track all case branches for connection to end

        i = 0
        while i < len(st_lines):
            original_line = st_lines[i]
            line = original_line.strip()

            if not line:
                i += 1
                continue

            logger.debug(f"Line {i + 1}: {line[:50]}{'...' if len(line) > 50 else ''}")

            # Clean up the line for Mermaid compatibility
            clean_line = self._clean_st_line_for_mermaid(line, original_line)

            # Detect control structures
            upper_line = line.upper()

            # CASE statement handling
            if 'CASE' in upper_line and 'OF' in upper_line:
                logger.debug(f"  Found CASE statement at line {i + 1}")
                in_case_statement = True
                case_start_node = f"Case{node_num}"
                case_condition_node = f"CaseCond{node_num}"
                case_end_node = f"CaseEnd{node_num}"
                case_branches = []  # Reset branches for this CASE

                lines.append(f"    {case_start_node}[\"CASE Statement\"]")
                lines.append(f"    {last_action_node} --> {case_start_node}")
                lines.append(f"    {case_condition_node}{{\"{clean_line}\"}}")
                lines.append(f"    {case_start_node} --> {case_condition_node}")

                last_action_node = case_condition_node
                node_num += 1
                i += 1
                continue

            elif in_case_statement and 'END_CASE' in upper_line:
                logger.debug(f"  Found END_CASE at line {i + 1}")

                # Create CASE end node
                lines.append(f"    {case_end_node}[\"End CASE\"]")

                # Connect all case branches to the end node
                for branch_node in case_branches:
                    lines.append(f"    {branch_node} --> {case_end_node}")

                last_action_node = case_end_node
                in_case_statement = False
                node_num += 1
                i += 1
                continue

            elif in_case_statement and ':' in line and not line.strip().startswith('END_'):
                # This is a CASE branch (e.g., "eZ100_task.Off: Task_OFF();")
                logger.debug(f"  Found CASE branch at line {i + 1}")

                # Extract the branch condition and action
                if ':' in line:
                    condition_part, action_part = line.split(':', 1)
                    condition_clean = self._clean_st_line_for_mermaid(condition_part.strip(), condition_part)
                    action_clean = self._clean_st_line_for_mermaid(action_part.strip(), action_part)

                    # Handle empty actions (like "eZ100_Task.Continuous_Flow_Intake:")
                    if not action_clean.strip():
                        action_clean = "No action"

                    branch_node = f"CaseBranch{node_num}"
                    action_node = f"CaseAction{node_num}"

                    lines.append(f"    {branch_node}[\"{condition_clean}\"]")
                    lines.append(f"    {case_condition_node} --> {branch_node}")
                    lines.append(f"    {action_node}[\"{action_clean}\"]")
                    lines.append(f"    {branch_node} --> {action_node}")

                    # Track this branch for connection to CASE end
                    case_branches.append(action_node)

                    node_num += 1
                i += 1
                continue

            # IF/THEN handling
            elif any(keyword in upper_line for keyword in ['IF', 'THEN']):
                logger.debug(f"  Found IF/THEN condition at line {i + 1}")
                condition_node = f"Condition{node_num}"
                true_action_node = f"Action{node_num}"
                false_action_node = f"Action{node_num + 1}"

                lines.append(f"    {condition_node}{{\"{clean_line}\"}}")
                lines.append(f"    {last_action_node} --> {condition_node}")
                lines.append(f"    {condition_node} -->|True| {true_action_node}")
                lines.append(f"    {condition_node} -->|False| {false_action_node}")

                # Process the true branch
                true_action_clean = self._clean_st_line_for_mermaid("Then branch", "Then branch")
                lines.append(f"    {true_action_node}[\"{true_action_clean}\"]")

                last_action_node = true_action_node
                node_num += 2
                i += 1
                continue

            elif any(keyword in upper_word for keyword in ['ELSIF', 'ELSEIF'] for upper_word in upper_line.split()):
                logger.debug(f"  Found ELSIF condition at line {i + 1}")
                # Connect to previous false branch and create new condition
                condition_node = f"Condition{node_num}"
                lines.append(f"    {condition_node}{{\"{clean_line}\"}}")
                lines.append(f"    Action{node_num - 1} --> {condition_node}")
                lines.append(f"    {condition_node} -->|True| Action{node_num}")
                lines.append(f"    {condition_node} -->|False| Action{node_num + 1}")

                last_action_node = f"Action{node_num}"
                node_num += 2
                i += 1
                continue

            elif 'ELSE' in upper_line.split():
                logger.debug(f"  Found ELSE at line {i + 1}")
                else_node = f"Action{node_num}"
                lines.append(f"    {else_node}[\"Else: {clean_line}\"]")
                lines.append(f"    Action{node_num - 1} --> {else_node}")
                last_action_node = else_node
                node_num += 1
                i += 1
                continue

            elif any(keyword in upper_line for keyword in ['END_IF', 'ENDIF']):
                logger.debug(f"  Found END_IF at line {i + 1}")
                # End of IF statement - last action node remains the same
                i += 1
                continue

            else:
                # Regular action/assignment
                logger.debug(f"  Found action at line {i + 1}")
                action_node = f"Action{node_num}"

                # Ensure the label is not empty
                if not clean_line.strip():
                    clean_line = "Empty statement"

                lines.append(f"    {action_node}[\"{clean_line}\"]")

                # Connect to previous node if not the first action
                if last_action_node != "Start":
                    lines.append(f"    {last_action_node} --> {action_node}")

                last_action_node = action_node
                node_num += 1
                i += 1
                continue

        logger.debug(f"Generated {len(lines)} Mermaid lines from ST code")
        return lines, last_action_node

    def _clean_st_line_for_mermaid(self, line: str, original_line: str = None) -> str:
        """
        Clean ST code line for Mermaid compatibility.
        Mermaid has issues with certain characters in node labels.
        """
        if original_line is None:
            original_line = line

        # Remove excessive whitespace first
        line = ' '.join(line.split())

        # Remove trailing semicolons and colons
        line = line.rstrip(';:')

        # Escape quotes for Mermaid
        line = line.replace('"', '&quot;')

        # Replace problematic characters with safer alternatives
        replacements = {
            ':=': ' ← ',  # Assignment operator
            '=': ' = ',  # Equality
        }

        # Apply replacements
        for old, new in replacements.items():
            line = line.replace(old, new)

        # Remove multiple spaces that might have been created
        line = ' '.join(line.split())

        # For very complex lines, simplify them
        if len(line) > 500:
            # For long assignment statements, show variable and simplified value
            if ':=' in original_line or '=' in original_line:
                parts = re.split(r':=|=', original_line, 1)
                if len(parts) == 2:
                    var_part = parts[0].strip()
                    val_part = parts[1].strip()

                    # Simplify variable part if too long
                    if len(var_part) > 25:
                        var_part = self._simplify_variable_name(var_part)

                    # Simplify value part if too long
                    if len(val_part) > 25:
                        val_part = self._simplify_function_call(val_part)

                    line = f"{var_part} ← {val_part}"

            # Truncate if still too long
            if len(line) > 80:
                line = line[:77] + "..."

        return line.strip()

    def _simplify_variable_name(self, var_name: str) -> str:
        """Simplify long variable names for display"""
        # Remove common prefixes if they make the name too long
        prefixes = ['PVL.', 'GVL.', 'GVL_', 'PVL_']
        for prefix in prefixes:
            if var_name.startswith(prefix) and len(var_name) > 20:
                var_name = var_name[len(prefix):]
                break

        # If still too long, take last part after final dot
        if len(var_name) > 150 and '.' in var_name:
            parts = var_name.split('.')
            if len(parts) > 2:
                var_name = f"{parts[-2]}.{parts[-1]}"
            else:
                var_name = parts[-1]

        return var_name

    def _simplify_function_call(self, func_call: str) -> str:
        """Simplify function calls for display"""
        # Extract function name and simplify parameters
        match = re.match(r'(\w+)\(', func_call)
        if match:
            func_name = match.group(1)
            return f"{func_name}(...)"

        # For complex expressions, just show it's an expression
        if len(func_call) > 30:
            if '(' in func_call:
                return "complex_expr(...)"
            else:
                return "expression"

        return func_call


    def extract_code_from_element(self, body_element, name: str) -> Optional[str]:
        """Extract ST code from body element (public method for hierarchical processor)"""
        return self.extract_code(body_element, name)