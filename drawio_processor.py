import os
import logging
import xml.etree.ElementTree as ET
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


class DrawIOProcessor:
    def __init__(self):
        self.namespace = ''
        from st_processor import STProcessor
        from ld_processor import LDProcessor
        from cfc_processor import CFCProcessor
        from fbd_processor import FBDProcessor

        self.st_processor = STProcessor()
        self.ld_processor = LDProcessor()
        self.cfc_processor = CFCProcessor()
        self.fbd_processor = FBDProcessor()

    def set_namespace(self, namespace: str):
        """Set the XML namespace for processing"""
        self.namespace = namespace
        logger.info(f"DrawIO processor namespace set to: {namespace}")

        # Pass namespace to all processors
        self.st_processor.set_namespace(namespace)
        self.ld_processor.set_namespace(namespace)
        self.cfc_processor.set_namespace(namespace)
        self.fbd_processor.set_namespace(namespace)

    def convert_component(self, component_info: Dict, output_dir: str,
                          include_logic: bool = True, include_interface: bool = True) -> bool:
        """Convert a component to Draw.io format"""
        try:
            os.makedirs(output_dir, exist_ok=True)
            element = component_info['element']
            name = component_info['name']
            comp_type = component_info['type']

            logger.info(f"Converting {comp_type}: {name} to Draw.io in directory: {output_dir}")

            files_created = []

            # Extract body content (ST code)
            if include_logic:
                logger.debug(f"Processing logic for {name}")
                body_files = self._convert_body_to_drawio(element, name, output_dir)
                files_created.extend(body_files)
                logger.debug(f"Body files created: {body_files}")

            # Extract interface (variables)
            if include_interface:
                logger.debug(f"Processing interface for {name}")
                interface_files = self._convert_interface_to_drawio(element, name, output_dir)
                files_created.extend(interface_files)
                logger.debug(f"Interface files created: {interface_files}")

            logger.info(f"Created {len(files_created)} Draw.io files: {files_created}")
            return len(files_created) > 0

        except Exception as e:
            logger.error(f"Draw.io conversion failed for {component_info.get('name', 'unknown')}: {str(e)}")
            return False

    def _convert_body_to_drawio(self, element, name: str, output_dir: str) -> List[str]:
        """Convert body content to Draw.io XML"""
        files_created = []

        # Look for body in the element
        body = element.find(f"{self.namespace}body")
        if body is not None:
            logger.debug(f"Found body for {name}")

            # Parse code and convert to Draw.io
            drawio_xml = self._parse_code_body_to_drawio(body, name)
            if drawio_xml:
                filename = os.path.join(output_dir, f"{self._sanitize_filename(name)}_logic.drawio")
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(drawio_xml)
                files_created.append(filename)
                logger.info(f"Created Draw.io logic file: {filename} with {len(drawio_xml)} characters")
            else:
                logger.warning(f"No Draw.io XML generated for body of {name}")
        else:
            logger.warning(f"No body found for {name}")

        return files_created

    def _convert_interface_to_drawio(self, element, name: str, output_dir: str) -> list:
        """Convert interface to Draw.io class diagram"""
        files_created = []

        interface = element.find(f"{self.namespace}interface")
        if interface is not None:
            drawio_xml = self._parse_interface_to_drawio(interface, name)
            if drawio_xml:
                filename = os.path.join(output_dir, f"{self._sanitize_filename(name)}_interface.drawio")
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(drawio_xml)
                files_created.append(filename)
                logger.info(f"Created Draw.io interface file: {filename}")

        return files_created

    def _parse_code_body_to_drawio(self, body_element, name: str) -> Optional[str]:
        """Parse code body and convert to Draw.io format"""
        logger.info(f"=== Parsing code body for Draw.io: {name} ===")

        # Check for ST code
        st_code = self.st_processor.extract_code(body_element, name)
        if st_code:
            logger.info(f"Found ST code for {name}, converting to Draw.io")
            return self._convert_st_to_drawio(st_code, name)

        # Check for LD (Ladder Diagram)
        ld_code = self.ld_processor.extract_code(body_element, name)
        if ld_code:
            logger.info(f"Found LD code for {name}, converting to Draw.io")
            return self._convert_ld_to_drawio(ld_code, name)

        # Check for CFC
        cfc_code = self.cfc_processor.extract_code(body_element, name)
        if cfc_code:
            logger.info(f"Found CFC code for {name}, converting to Draw.io")
            return self._convert_cfc_to_drawio(cfc_code, name)

        # Check for FBD
        fbd_code = self.fbd_processor.extract_code(body_element, name)
        if fbd_code:
            logger.info(f"Found FBD code for {name}, converting to Draw.io")
            return self._convert_fbd_to_drawio(fbd_code, name)

        logger.warning(f"No supported code format found for {name}")
        return None

    def _convert_st_to_drawio(self, st_code: str, name: str) -> str:
        """Convert ST code to Draw.io XML format - NO LINE LENGTH LIMITS"""
        try:
            # Draw.io XML structure
            drawio_template = """<mxfile>
    <diagram name="{name}" id="diagram_1">
        <mxGraphModel dx="1422" dy="881" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="827" pageHeight="1169" math="0" shadow="0">
            <root>
                <mxCell id="0"/>
                <mxCell id="1" parent="0"/>
                {content}
            </root>
        </mxGraphModel>
    </diagram>
</mxfile>"""

            content_cells = []
            y_position = 20

            # Add title cell
            title_cell = f'''
                <mxCell id="title" value="{self._escape_xml_text(name)} - ST Code" style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;" vertex="1" parent="1">
                    <mxGeometry x="100" y="{y_position}" width="600" height="30" as="geometry"/>
                </mxCell>'''
            content_cells.append(title_cell)
            y_position += 50

            # Add code content - NO TRUNCATION, use complete ST code
            lines = st_code.split('\n')
            logger.info(f"Creating Draw.io ST diagram with {len(lines)} lines of code")

            for i, line in enumerate(lines):
                # Use the full line without any truncation
                escaped_line = self._escape_xml_text(line)
                cell_id = f"line_{i}"

                code_cell = f'''
                <mxCell id="{cell_id}" value="{escaped_line}" style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=top;whiteSpace=wrap;rounded=0;fontFamily=Consolas;" vertex="1" parent="1">
                    <mxGeometry x="50" y="{y_position}" width="700" height="20" as="geometry"/>
                </mxCell>'''
                content_cells.append(code_cell)
                y_position += 25

            # Add summary cell
            summary_cell = f'''
                <mxCell id="summary" value="Total: {len(lines)} lines, {len(st_code)} characters" style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=top;whiteSpace=wrap;rounded=0;" vertex="1" parent="1">
                    <mxGeometry x="50" y="{y_position + 10}" width="700" height="20" as="geometry"/>
                </mxCell>'''
            content_cells.append(summary_cell)

            content_xml = '\n'.join(content_cells)
            return drawio_template.format(name=name, content=content_xml)

        except Exception as e:
            logger.error(f"Error converting ST to Draw.io for {name}: {str(e)}")
            return self._create_fallback_drawio(st_code, name, "ST")

    def _convert_ld_to_drawio(self, ld_code: str, name: str) -> str:
        """Convert Ladder Diagram to Draw.io format"""
        try:
            drawio_template = """<mxfile>
    <diagram name="{name}" id="diagram_1">
        <mxGraphModel dx="1422" dy="881" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="827" pageHeight="1169" math="0" shadow="0">
            <root>
                <mxCell id="0"/>
                <mxCell id="1" parent="0"/>
                {content}
            </root>
        </mxGraphModel>
    </diagram>
</mxfile>"""

            content_cells = []
            y_position = 20

            # Add title
            title_cell = f'''
                <mxCell id="title" value="{self._escape_xml_text(name)} - Ladder Diagram" style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;" vertex="1" parent="1">
                    <mxGeometry x="100" y="{y_position}" width="600" height="30" as="geometry"/>
                </mxCell>'''
            content_cells.append(title_cell)
            y_position += 50

            # Add LD content - NO TRUNCATION
            escaped_content = self._escape_xml_text(str(ld_code))
            ld_content_cell = f'''
                <mxCell id="ld_content" value="{escaped_content}" style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=top;whiteSpace=wrap;rounded=0;fontFamily=Consolas;" vertex="1" parent="1">
                    <mxGeometry x="50" y="{y_position}" width="700" height="400" as="geometry"/>
                </mxCell>'''
            content_cells.append(ld_content_cell)

            content_xml = '\n'.join(content_cells)
            return drawio_template.format(name=name, content=content_xml)

        except Exception as e:
            logger.error(f"Error converting LD to Draw.io for {name}: {str(e)}")
            return self._create_fallback_drawio(ld_code, name, "LD")

    def _convert_cfc_to_drawio(self, cfc_code: str, name: str) -> str:
        """Convert CFC to Draw.io format"""
        return self._create_basic_drawio(cfc_code, name, "CFC")

    def _convert_fbd_to_drawio(self, fbd_code: str, name: str) -> str:
        """Convert FBD to Draw.io format"""
        return self._create_basic_drawio(fbd_code, name, "FBD")

    def _create_basic_drawio(self, content: str, name: str, content_type: str) -> str:
        """Create basic Draw.io diagram for any content type"""
        drawio_template = """<mxfile>
    <diagram name="{name}" id="diagram_1">
        <mxGraphModel dx="1422" dy="881" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="827" pageHeight="1169" math="0" shadow="0">
            <root>
                <mxCell id="0"/>
                <mxCell id="1" parent="0"/>
                <mxCell id="title" value="{name} - {type}" style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;" vertex="1" parent="1">
                    <mxGeometry x="100" y="50" width="600" height="30" as="geometry"/>
                </mxCell>
                <mxCell id="content" value="{content}" style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=top;whiteSpace=wrap;rounded=0;fontFamily=Consolas;" vertex="1" parent="1">
                    <mxGeometry x="50" y="100" width="700" height="500" as="geometry"/>
                </mxCell>
            </root>
        </mxGraphModel>
    </diagram>
</mxfile>"""

        escaped_content = self._escape_xml_text(str(content))
        return drawio_template.format(
            name=name,
            type=content_type,
            content=escaped_content
        )

    def _create_fallback_drawio(self, content: str, name: str, content_type: str) -> str:
        """Create fallback Draw.io diagram when conversion fails"""
        drawio_template = """<mxfile>
    <diagram name="{name}" id="diagram_1">
        <mxGraphModel dx="1422" dy="881" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="827" pageHeight="1169" math="0" shadow="0">
            <root>
                <mxCell id="0"/>
                <mxCell id="1" parent="0"/>
                <mxCell id="title" value="{name} - {type} (Fallback)" style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;" vertex="1" parent="1">
                    <mxGeometry x="100" y="50" width="600" height="30" as="geometry"/>
                </mxCell>
                <mxCell id="error" value="Error converting {type} content. Showing raw content below:" style="text;html=1;strokeColor=none;fillColor=#ffe6e6;align=left;verticalAlign=top;whiteSpace=wrap;rounded=0;" vertex="1" parent="1">
                    <mxGeometry x="50" y="100" width="700" height="30" as="geometry"/>
                </mxCell>
                <mxCell id="content" value="{content}" style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=top;whiteSpace=wrap;rounded=0;fontFamily=Consolas;" vertex="1" parent="1">
                    <mxGeometry x="50" y="140" width="700" height="400" as="geometry"/>
                </mxCell>
            </root>
        </mxGraphModel>
    </diagram>
</mxfile>"""

        escaped_content = self._escape_xml_text(str(content))
        return drawio_template.format(
            name=name,
            type=content_type,
            content=escaped_content
        )

    def _parse_interface_to_drawio(self, interface_element, name: str) -> Optional[str]:
        """Parse POU interface and create Draw.io class diagram"""
        try:
            drawio_template = """<mxfile>
    <diagram name="{name} Interface" id="diagram_1">
        <mxGraphModel dx="1422" dy="881" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="827" pageHeight="1169" math="0" shadow="0">
            <root>
                <mxCell id="0"/>
                <mxCell id="1" parent="0"/>
                {content}
            </root>
        </mxGraphModel>
    </diagram>
</mxfile>"""

            content_cells = []
            y_position = 50
            x_position = 100

            # Get all variables
            variables = interface_element.findall(f".//{self.namespace}variable")
            variable_count = len(variables)

            # Calculate class dimensions based on variable count
            class_width = 250
            class_height = 60 + (variable_count * 25)  # Header + variables

            # Class header (swimlane style)
            class_header = f'''
                <mxCell id="class_header" value="{self._escape_xml_text(name)}" style="swimlane;fontStyle=1;align=center;verticalAlign=top;childLayout=stackLayout;horizontal=1;startSize=30;horizontalStack=0;resizeParent=1;resizeParentMax=0;resizeLast=0;collapsible=1;marginBottom=0;" vertex="1" parent="1">
                    <mxGeometry x="{x_position}" y="{y_position}" width="{class_width}" height="{class_height}" as="geometry"/>
                </mxCell>'''
            content_cells.append(class_header)

            # Add variables
            var_y = 30  # Start inside the class header
            for i, var in enumerate(variables):
                name_elem = var.find(f"{self.namespace}name")
                type_elem = var.find(f"{self.namespace}type")

                if name_elem is not None and type_elem is not None:
                    var_name = name_elem.text or "Unknown"
                    var_type = self._get_type_name(type_elem)

                    var_cell = f'''
                <mxCell id="var_{i}" value="{self._escape_xml_text(var_type)} {self._escape_xml_text(var_name)}" style="text;strokeColor=none;fillColor=none;align=left;verticalAlign=top;spacingLeft=4;spacingRight=4;overflow=hidden;rotatable=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;" vertex="1" parent="class_header">
                    <mxGeometry y="{var_y}" width="{class_width}" height="20" as="geometry"/>
                </mxCell>'''
                    content_cells.append(var_cell)
                    var_y += 20

            # Add variable count info
            info_cell = f'''
                <mxCell id="info" value="Variables: {variable_count}" style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=top;whiteSpace=wrap;rounded=0;" vertex="1" parent="1">
                    <mxGeometry x="{x_position}" y="{y_position + class_height + 20}" width="{class_width}" height="20" as="geometry"/>
                </mxCell>'''
            content_cells.append(info_cell)

            content_xml = '\n'.join(content_cells)
            return drawio_template.format(name=name, content=content_xml)

        except Exception as e:
            logger.error(f"Error creating Draw.io interface for {name}: {str(e)}")
            return None

    def _escape_xml_text(self, text: str) -> str:
        """Escape text for XML content - PRESERVES ALL CONTENT"""
        if text is None:
            return ""

        replacements = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&apos;'
        }

        for find, replace in replacements.items():
            text = text.replace(find, replace)

        return text

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