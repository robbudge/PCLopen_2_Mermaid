import xml.etree.ElementTree as ET
import logging

# Set up logging properly
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # FIXED: asctime not asasctime
    handlers=[
        logging.FileHandler('diagnostic.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def analyze_xml_structure(xml_file_path):
    """Quick analysis of XML structure"""
    logger.info(f"Analyzing XML structure: {xml_file_path}")

    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()

        # Extract namespace
        if '}' in root.tag:
            namespace = root.tag.split('}')[0] + '}'
        else:
            namespace = ''

        logger.info(f"Namespace: {namespace}")

        # Find all POU elements
        pous = root.findall(f".//{namespace}pou")
        logger.info(f"Found {len(pous)} POU elements")

        for i, pou in enumerate(pous):
            name = pou.get('name', f'Unknown_{i}')
            logger.info(f"\n=== POU {i}: {name} ===")

            # Check for body
            body = pou.find(f"{namespace}body")
            if body:
                logger.info(f"  ✓ Body found with {len(list(body))} children")
                for j, child in enumerate(body):
                    logger.info(f"    Body child {j}: {child.tag.replace(namespace, '')}")
                    logger.info(f"      Has text: {bool(child.text and child.text.strip())}")
                    if child.text and child.text.strip():
                        text_preview = child.text.strip()[:200]
                        logger.info(f"      Text preview: {text_preview}")

                    # Check for sub-children
                    sub_children = list(child)
                    if sub_children:
                        logger.info(f"      Sub-children: {len(sub_children)}")
                        for k, subchild in enumerate(sub_children):
                            logger.info(f"        Sub-child {k}: {subchild.tag.replace(namespace, '')}")
                            if subchild.text and subchild.text.strip():
                                sub_text_preview = subchild.text.strip()[:100]
                                logger.info(f"          Text: {sub_text_preview}")
            else:
                logger.info("  ✗ No body found")

            # Check for interface
            interface = pou.find(f"{namespace}interface")
            if interface:
                variables = interface.findall(f".//{namespace}variable")
                logger.info(f"  ✓ Interface found with {len(variables)} variables")

                # Show first few variables
                for var_idx, var in enumerate(variables[:5]):  # Show first 5 only
                    name_elem = var.find(f"{namespace}name")
                    type_elem = var.find(f"{namespace}type")
                    logger.info(
                        f"    Variable {var_idx}: {name_elem.text if name_elem else 'None'} : {get_type_name(type_elem, namespace)}")

                if len(variables) > 5:
                    logger.info(f"    ... and {len(variables) - 5} more variables")
            else:
                logger.info("  ✗ No interface found")

            # Look for implementation
            implementation = pou.find(f"{namespace}implementation")
            if implementation:
                logger.info(f"  ✓ Implementation found with {len(list(implementation))} children")
                for impl_child in implementation:
                    logger.info(f"    Implementation child: {impl_child.tag.replace(namespace, '')}")
                    if impl_child.text and impl_child.text.strip():
                        logger.info(f"      Text: {impl_child.text.strip()[:100]}")
            else:
                logger.info("  ✗ No implementation found")

            # Search for any code elements anywhere in the POU
            code_formats = ['ST', 'LD', 'CFC', 'FBD', 'SFC', 'IL']
            found_code = False
            for code_format in code_formats:
                elements = pou.findall(f".//{namespace}{code_format}")
                if elements:
                    found_code = True
                    logger.info(f"  ✓ Found {len(elements)} {code_format} element(s)")
                    for elem_idx, elem in enumerate(elements):
                        if elem.text and elem.text.strip():
                            logger.info(f"    {code_format} element {elem_idx}: {len(elem.text.strip())} chars")
                            logger.info(f"      Preview: {elem.text.strip()[:150]}")
                        else:
                            logger.info(f"    {code_format} element {elem_idx}: No text content")

            if not found_code:
                logger.info("  ✗ No code elements (ST, LD, CFC, FBD, SFC, IL) found anywhere in POU")

    except Exception as e:
        logger.error(f"Error analyzing XML: {str(e)}")
        raise


def get_type_name(type_element, namespace):
    """Extract type name from type element"""
    if type_element is None:
        return "Unknown"

    derived = type_element.find(f"{namespace}derived")
    if derived is not None:
        return derived.get('name', 'Unknown')

    base_type = type_element.find(f"{namespace}baseType")
    if base_type is not None:
        return base_type.text or 'Unknown'

    return 'Unknown'


if __name__ == "__main__":
    # Analyze your H2 XML file
    analyze_xml_structure("H2-1.0.02.xml")