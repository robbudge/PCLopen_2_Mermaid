import xml.etree.ElementTree as ET
import logging

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for maximum detail
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('deep_diagnostic.log', mode='w', encoding='utf-8'),  # Overwrite each time
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def deep_analyze_xml(xml_file_path):
    """Deep analysis of XML structure - will show EVERYTHING"""
    logger.info(f"DEEP ANALYZING XML: {xml_file_path}")

    try:
        # Parse the XML
        tree = ET.parse(xml_file_path)
        root = tree.getroot()

        logger.info("=" * 80)
        logger.info("ROOT ELEMENT ANALYSIS")
        logger.info("=" * 80)
        logger.info(f"Root tag: {root.tag}")
        logger.info(f"Root attributes: {root.attrib}")

        # Extract namespace
        if '}' in root.tag:
            namespace = root.tag.split('}')[0] + '}'
        else:
            namespace = ''
        logger.info(f"Detected namespace: '{namespace}'")

        # Get ALL elements in the entire file to understand structure
        all_elements = list(root.iter())
        logger.info(f"Total elements in XML: {len(all_elements)}")

        # Look for project structure
        logger.info("\n" + "=" * 80)
        logger.info("PROJECT STRUCTURE SEARCH")
        logger.info("=" * 80)

        # Common PLCopen elements to look for
        plcopen_elements = [
            'project', 'types', 'pous', 'pou', 'interface', 'body',
            'implementation', 'ST', 'LD', 'FBD', 'CFC', 'SFC', 'IL',
            'variable', 'name', 'type', 'documentation'
        ]

        for element_name in plcopen_elements:
            elements = root.findall(f".//{namespace}{element_name}")
            if elements:
                logger.info(f"Found {len(elements)} '{element_name}' elements")

        # Find ALL POU elements with detailed analysis
        logger.info("\n" + "=" * 80)
        logger.info("DETAILED POU ANALYSIS")
        logger.info("=" * 80)

        pous = root.findall(f".//{namespace}pou")
        logger.info(f"Found {len(pous)} POU elements total")

        for pou_index, pou in enumerate(pous):
            pou_name = pou.get('name', f'UNNAMED_POU_{pou_index}')
            logger.info(f"\n{'=' * 60}")
            logger.info(f"POU #{pou_index}: {pou_name}")
            logger.info(f"{'=' * 60}")

            # POU attributes
            logger.info(f"POU attributes: {pou.attrib}")

            # Analyze ALL direct children of POU
            pou_children = list(pou)
            logger.info(f"POU has {len(pou_children)} direct children:")

            for child_index, child in enumerate(pou_children):
                child_tag_clean = child.tag.replace(namespace, '')
                logger.info(f"  Child {child_index}: {child_tag_clean}")
                logger.info(f"    Attributes: {child.attrib}")
                logger.info(f"    Has text: {bool(child.text)}")
                if child.text:
                    text_preview = child.text.strip() if child.text.strip() else "WHITESPACE_ONLY"
                    logger.info(f"    Text preview: '{text_preview[:500]}'")

                # Analyze grandchildren
                grand_children = list(child)
                if grand_children:
                    logger.info(f"    Has {len(grand_children)} sub-children:")
                    for grand_index, grand_child in enumerate(grand_children):
                        grand_tag_clean = grand_child.tag.replace(namespace, '')
                        logger.info(f"      Sub-child {grand_index}: {grand_tag_clean}")
                        logger.info(f"        Attributes: {grand_child.attrib}")
                        logger.info(f"        Has text: {bool(grand_child.text)}")
                        if grand_child.text:
                            grand_text = grand_child.text.strip() if grand_child.text.strip() else "WHITESPACE_ONLY"
                            logger.info(f"        Text: '{grand_text[:300]}'")

            # Specific search for interface
            interface = pou.find(f"{namespace}interface")
            if interface:
                logger.info(f"\n  INTERFACE FOUND:")
                variables = interface.findall(f".//{namespace}variable")
                logger.info(f"    Number of variables: {len(variables)}")

                for var_index, var in enumerate(variables[:10]):  # Show first 10 only
                    name_elem = var.find(f"{namespace}name")
                    type_elem = var.find(f"{namespace}type")
                    logger.info(f"    Variable {var_index}:")
                    logger.info(f"      Name: '{name_elem.text if name_elem else 'MISSING'}'")
                    logger.info(f"      Type: {get_type_name(type_elem, namespace)}")
            else:
                logger.info(f"\n  NO INTERFACE FOUND")

            # Specific search for body
            body = pou.find(f"{namespace}body")
            if body:
                logger.info(f"\n  BODY FOUND:")
                logger.info(f"    Body attributes: {body.attrib}")
                body_children = list(body)
                logger.info(f"    Body has {len(body_children)} children:")

                for body_child_index, body_child in enumerate(body_children):
                    body_child_tag_clean = body_child.tag.replace(namespace, '')
                    logger.info(f"      Body child {body_child_index}: {body_child_tag_clean}")
                    logger.info(f"        Attributes: {body_child.attrib}")
                    logger.info(f"        Has text: {bool(body_child.text)}")

                    if body_child.text:
                        body_text = body_child.text.strip() if body_child.text.strip() else "WHITESPACE_ONLY"
                        logger.info(f"        Text length: {len(body_child.text)}")
                        logger.info(f"        Text preview: '{body_text[:400]}'")

                    # Look for implementation within body
                    if body_child_tag_clean == 'implementation':
                        impl_children = list(body_child)
                        logger.info(f"        Implementation has {len(impl_children)} children:")
                        for impl_child in impl_children:
                            impl_tag_clean = impl_child.tag.replace(namespace, '')
                            logger.info(f"          Implementation child: {impl_tag_clean}")
                            if impl_child.text:
                                impl_text = impl_child.text.strip() if impl_child.text.strip() else "WHITESPACE_ONLY"
                                logger.info(f"            Text: '{impl_text[:300]}'")
            else:
                logger.info(f"\n  NO BODY FOUND")

            # Search for ANY code content anywhere in the POU
            logger.info(f"\n  CODE CONTENT SEARCH:")
            code_found = False
            for code_type in ['ST', 'LD', 'CFC', 'FBD', 'SFC', 'IL']:
                code_elements = pou.findall(f".//{namespace}{code_type}")
                if code_elements:
                    code_found = True
                    logger.info(f"    Found {len(code_elements)} {code_type} elements:")
                    for code_elem in code_elements:
                        if code_elem.text and code_elem.text.strip():
                            code_text = code_elem.text.strip()
                            logger.info(f"      {code_type} code found: {len(code_text)} characters")
                            logger.info(f"      First 200 chars: '{code_text[:200]}'")
                        else:
                            logger.info(f"      {code_type} element exists but has no text content")

            if not code_found:
                logger.info(f"    NO CODE ELEMENTS FOUND ANYWHERE IN POU")

        # Final summary
        logger.info("\n" + "=" * 80)
        logger.info("SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total POUs: {len(pous)}")

        # Count POUs with different content types
        pous_with_interface = 0
        pous_with_body = 0
        pous_with_code = 0

        for pou in pous:
            if pou.find(f"{namespace}interface") is not None:
                pous_with_interface += 1
            if pou.find(f"{namespace}body") is not None:
                pous_with_body += 1
            # Check for any code
            code_found = False
            for code_type in ['ST', 'LD', 'CFC', 'FBD', 'SFC', 'IL']:
                if pou.find(f".//{namespace}{code_type}") is not None:
                    code_found = True
                    break
            if code_found:
                pous_with_code += 1

        logger.info(f"POUs with interface: {pous_with_interface}")
        logger.info(f"POUs with body: {pous_with_body}")
        logger.info(f"POUs with code: {pous_with_code}")

    except Exception as e:
        logger.error(f"ERROR during analysis: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")


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
    print("Starting deep XML analysis...")
    print("This will show EVERYTHING in your XML file")
    print("Check both console output and deep_diagnostic.log file")
    print()

    deep_analyze_xml("H2-1.0.02.xml")

    print()
    print("Analysis complete! Check the logs for detailed information.")