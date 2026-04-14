"""Test the DEXPI drawing toolkit functionality."""

import os
from xml.etree import ElementTree as ET

import pytest

from pydexpi.dexpi_classes.dexpiModel import DexpiModel
from pydexpi.dexpi_classes.graphics import (
    Color,
    ConnectorLine,
    Diagram,
    Ellipse,
    EllipseArc,
    Point,
    Polygon,
    PolyLine,
    RepresentationGroup,
    RepresentationTypeGroup,
    Shape,
    ShapeCatalogue,
    Stroke,
    Text,
)
from pydexpi.loaders import proteus_serializer
from pydexpi.loaders.svg_loader import (
    DrawDiagram,
    DrawNodePosition,
    DrawRepresentationGroup,
    DrawRepresentationTypeGroup,
    DrawShape,
    process_shape_catalogue,
)


@pytest.fixture
def color():
    """Create a test Color instance."""
    return Color(r=255, g=0, b=0)  # Red color


@pytest.fixture
def stroke(color):
    """Create a test Stroke instance."""
    return Stroke(color=color, width=2.0, dashStyle="Solid")


@pytest.fixture
def point_list():
    """Create a list of Point instances for testing."""
    return [
        Point(x=0, y=0),
        Point(x=10, y=0),
        Point(x=10, y=10),
        Point(x=0, y=10),
    ]


@pytest.fixture
def polyline(point_list, stroke):
    """Create a test PolyLine instance."""
    return PolyLine(points=point_list, stroke=stroke)


@pytest.fixture
def polygon(point_list, stroke):
    """Create a test Polygon instance."""
    return Polygon(points=point_list, stroke=stroke, fillStyle="Solid")


@pytest.fixture
def ellipse(stroke):
    """Create a test Ellipse instance."""
    return Ellipse(
        center=Point(x=5, y=5),
        horizontalSemiAxis=5,
        verticalSemiAxis=3,
        stroke=stroke,
        fillStyle="Solid",
        rotation=0.0,
    )


@pytest.fixture
def ellipse_arc(stroke):
    """Create a test EllipseArc instance."""
    return EllipseArc(
        center=Point(x=5, y=5),
        horizontalSemiAxis=5,
        verticalSemiAxis=3,
        startAngle=0,
        endAngle=3.14159,  # π radians (180 degrees)
        stroke=stroke,
        fillStyle="Solid",
        rotation=0.0,
    )


@pytest.fixture
def text():
    """Create a test Text instance."""
    return Text(
        text="Test Text",
        position=Point(x=5, y=5),
        alignment="CenterTop",
        color=Color(r=0, g=0, b=0),  # Black color
        font="Arial",
        rotation=0.0,
        size=12,
    )


@pytest.fixture
def connector_line(point_list, stroke):
    """Create a test ConnectorLine instance."""
    return ConnectorLine(innerPoints=point_list, stroke=stroke)


@pytest.fixture
def shape(polyline, polygon, ellipse, ellipse_arc, text, connector_line):
    """Create a test Shape instance with all primitive types."""
    return Shape(
        name="Test Shape",
        primitives=[polyline, polygon, ellipse, ellipse_arc, text, connector_line],
    )


@pytest.fixture
def representation_group(polyline, polygon, ellipse, ellipse_arc, text, connector_line):
    """Create a test RepresentationTypeGroup instance."""

    class TestGroup(RepresentationTypeGroup):
        def __init__(self):
            super().__init__()  # Initialize parent class first
            self.elements = [polyline, polygon, ellipse, ellipse_arc, text, connector_line]

    return TestGroup()


@pytest.fixture()
def loaded_dexpi():
    """Initialize DEXPI loader."""
    path = "data"
    filename = "C01V04-VER.EX01"
    serializer = proteus_serializer.ProteusSerializer()
    example_dexpi = serializer.load(path, filename)
    return example_dexpi


def normalize_svg(svg_string: str) -> str:
    """Normalize SVG string for comparison."""
    root = ET.fromstring(svg_string)
    return ET.tostring(root, encoding="unicode")


def assert_svg_attributes(element: ET.Element, expected_attrs: dict[str, any]) -> None:
    """Helper function to check SVG element attributes."""
    for key, value in expected_attrs.items():
        assert element.get(key) == str(value)


def test_get_bounding_box_simple(shape: Shape):
    """Test the basic functionality of get_bounds method."""
    drawer = DrawShape(shape)

    # Test default bounds (when no points added)
    top_left, bottom_right = drawer.renderer.get_bounds()
    assert top_left == (0.0, 0.0)
    assert bottom_right == (0.0, 0.0)

    # Add a simple rectangular shape points
    drawer.renderer.update_bounds(0, 0)  # bottom-left
    drawer.renderer.update_bounds(10, 0)  # bottom-right
    drawer.renderer.update_bounds(10, 10)  # top-right
    drawer.renderer.update_bounds(0, 10)  # top-left

    # Test computed bounds
    top_left, bottom_right = drawer.renderer.get_bounds()
    assert top_left == (0.0, 10.0)  # min_x, max_y
    assert bottom_right == (10.0, 0.0)  # max_x, min_y


def test_primitive_polyline_conversion(shape: Shape):
    """Test conversion of PolyLine to SVG."""
    drawer = DrawShape(shape)
    for primitive in shape.primitives:
        if isinstance(primitive, PolyLine):
            svg_element = drawer.renderer.convert_polyline(primitive)
            assert svg_element.tag == "polyline"
            assert svg_element.get("fill") == "none"
            assert svg_element.get("stroke") == "rgb(255,0,0)"
            assert svg_element.get("stroke-width") == "2.0"


def test_primitive_polygon_conversion(shape: Shape):
    """Test conversion of Polygon to SVG."""
    drawer = DrawShape(shape)
    for primitive in shape.primitives:
        if isinstance(primitive, Polygon):
            svg_element = drawer.renderer.convert_polygon(primitive)
            assert svg_element.tag == "polygon"
            assert svg_element.get("stroke") == "rgb(255,0,0)"
            assert svg_element.get("stroke-width") == "2.0"


def test_primitive_ellipse_conversion(shape: Shape):
    """Test conversion of Ellipse to SVG."""
    drawer = DrawShape(shape)
    for primitive in shape.primitives:
        if isinstance(primitive, Ellipse) and not isinstance(primitive, EllipseArc):
            svg_element = drawer.renderer.convert_ellipse(primitive)
            assert svg_element.tag == "ellipse"
            assert float(svg_element.get("cx")) == 5.0
            assert float(svg_element.get("cy")) == -5.0
            assert float(svg_element.get("rx")) == 5.0
            assert float(svg_element.get("ry")) == 3.0


def test_primitive_ellipse_arc_conversion(shape: Shape):
    """Test conversion of EllipseArc to SVG."""
    drawer = DrawShape(shape)
    for primitive in shape.primitives:
        if isinstance(primitive, EllipseArc):
            svg_element = drawer.renderer.convert_ellipse_arc(primitive)
            assert svg_element.tag == "path"
            assert svg_element.get("d").startswith("M")
            assert svg_element.get("fill") == "none"


def test_primitive_text_conversion(shape: Shape):
    """Test conversion of Text to SVG."""
    drawer = DrawShape(shape)
    for primitive in shape.primitives:
        if isinstance(primitive, Text):
            svg_element = drawer.renderer.convert_text(primitive)
            assert svg_element.tag == "text"
            assert svg_element.text == "Test Text"
            assert float(svg_element.get("x")) == 5.0
            assert float(svg_element.get("y")) == -5.0


def test_primitive_connector_line_conversion(shape: Shape):
    """Test conversion of ConnectorLine to SVG."""
    drawer = DrawShape(shape)
    for primitive in shape.primitives:
        if isinstance(primitive, ConnectorLine):
            svg_element = drawer.renderer.convert_connector_line(primitive)
            assert svg_element.tag == "polyline"
            assert svg_element.get("fill") == "none"
            assert svg_element.get("stroke") == "rgb(255,0,0)"


def test_background_option(shape):
    """Test SVG generation with and without background."""
    drawer = DrawShape(shape)
    ns = {"svg": "http://www.w3.org/2000/svg"}

    # With background (default)
    svg_with_bg = drawer.draw_svg()
    root = ET.fromstring(svg_with_bg)
    assert root.find(".//svg:rect[@fill='#f0f0f0']", namespaces=ns) is not None

    # Without background
    svg_without_bg = drawer.draw_svg(background=False)
    root = ET.fromstring(svg_without_bg)
    assert root.find(".//svg:rect[@fill='#f0f0f0']", namespaces=ns) is None


def test_shape_drawing(shape: Shape):
    """Test drawing a Shape to SVG."""
    drawer = DrawShape(shape)
    svg_str = drawer.draw_svg()
    root = ET.fromstring(svg_str)

    # Check SVG structure
    svg_ns = "http://www.w3.org/2000/svg"
    assert root.tag == f"{{{svg_ns}}}svg"  # SVG namespace is in the tag itself
    assert float(root.get("width")) > 0
    assert float(root.get("height")) > 0
    assert root.get("viewBox") is not None

    # Check metadata
    svg_ns = "http://www.w3.org/2000/svg"
    ns = {"svg": svg_ns}
    metadata = root.find("svg:metadata", ns)
    assert metadata is not None
    assert metadata.text == f"DEXPI Shape: {shape.name}"

    # Check primitives group
    group = root.find("svg:g", ns)
    assert group is not None
    assert group.get("id") == shape.name
    # Check all primitives were converted

    assert len(root.findall(".//svg:polyline", ns)) == 2  # PolyLine and ConnectorLine
    assert len(root.findall(".//svg:polygon", ns)) == 1
    assert len(root.findall(".//svg:ellipse", ns)) == 1
    assert len(root.findall(".//svg:path", ns)) == 1  # EllipseArc
    assert len(root.findall(".//svg:text", ns)) == 1


def test_representation_group_drawing(representation_group):
    """Test drawing a RepresentationTypeGroup to SVG."""
    drawer = DrawRepresentationTypeGroup(representation_group)
    svg_str = drawer.draw_svg()
    root = ET.fromstring(svg_str)

    # Check SVG structure
    svg_ns = "http://www.w3.org/2000/svg"
    ns = {"svg": svg_ns}
    assert root.tag == f"{{{svg_ns}}}svg"
    assert float(root.get("width")) > 0
    assert float(root.get("height")) > 0
    assert root.get("viewBox") is not None

    # Check metadata
    metadata = root.find("svg:metadata", ns)
    assert metadata is not None
    assert "DEXPI RepresentationTypeGroup:" in metadata.text

    # Check group
    group = root.find("svg:g", ns)
    assert group is not None
    assert group.get("class") == "testgroup"

    # Check all elements were converted
    assert len(root.findall(".//svg:polyline", ns)) == 2  # PolyLine and ConnectorLine
    assert len(root.findall(".//svg:polygon", ns)) == 1
    assert len(root.findall(".//svg:ellipse", ns)) == 1
    assert len(root.findall(".//svg:path", ns)) == 1  # EllipseArc
    assert len(root.findall(".//svg:text", ns)) == 1


def test_shape(loaded_dexpi: DexpiModel, tmp_path):
    """Test saving SVG to file."""
    # Get the first shape from the loaded DEXPI model
    loaded_dexpi_shape_catalogue: ShapeCatalogue = loaded_dexpi.shapeCatalogues[0]
    loaded_dexpi_shape: Shape = loaded_dexpi_shape_catalogue.shapes[0]

    drawer = DrawShape(loaded_dexpi_shape)
    filepath = drawer.save_svg(loaded_dexpi_shape.name, tmp_path)
    assert os.path.exists(filepath)

    with open(filepath, encoding="utf-8") as f:
        content = f.read()
        assert content.startswith('<?xml version="1.0" encoding="UTF-8"?>')
        assert '<svg xmlns="http://www.w3.org/2000/svg"' in content
        assert f"<metadata>DEXPI Shape: {loaded_dexpi_shape.name}" in content


def test_process_shape_catalogue(loaded_dexpi: DexpiModel, tmp_path):
    """Test processing a full shape catalogue and saving all shapes as SVG files."""
    # Create output directory
    output_dir = tmp_path / "catalogue_test"
    output_dir.mkdir()

    # Get the shape catalogue from the loaded DEXPI model
    loaded_dexpi_shape_catalogue: DexpiModel = loaded_dexpi.shapeCatalogues[0]

    # Process the shape catalogue
    result = process_shape_catalogue(loaded_dexpi_shape_catalogue, output_dir)

    # Verify the result is a dictionary mapping shape names to file paths
    assert isinstance(result, dict)
    assert len(result) > 0

    # Verify that the number of results matches the number of shapes in the catalogue
    assert len(result) == len(loaded_dexpi_shape_catalogue.shapes)

    # Verify each shape was processed
    for shape in loaded_dexpi_shape_catalogue.shapes:
        assert shape.name in result
        filepath = result[shape.name]

        # Verify the file exists
        assert os.path.exists(filepath)

        # Verify the filepath format is correct
        safe_name = "_".join(shape.name.split())
        expected_filename = f"{safe_name}.svg"
        assert filepath.endswith(expected_filename)
        assert str(output_dir) in filepath

        # Verify the file content is valid SVG
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
            assert content.startswith('<?xml version="1.0" encoding="UTF-8"?>')
            assert '<svg xmlns="http://www.w3.org/2000/svg"' in content
            assert f"<metadata>DEXPI Shape: {shape.name}" in content


def test_representation_type_group_for_border(loaded_dexpi: DexpiModel, tmp_path):
    """Test processing a RepresentationTypeGroup and saving as SVG file."""
    # Create output directory
    output_dir = tmp_path / "representation_type_group_test"
    output_dir.mkdir()

    # Get the border RepresentationTypeGroup from the loaded DEXPI model
    loaded_dexpi_border = loaded_dexpi.diagram.groups[0]

    # Process the representation type group
    drawer = DrawRepresentationTypeGroup(loaded_dexpi_border)
    svg_str = drawer.draw_svg()

    # Parse the SVG for testing
    root = ET.fromstring(svg_str)
    svg_ns = "http://www.w3.org/2000/svg"
    ns = {"svg": svg_ns}

    # Verify SVG structure and size
    assert root.tag == f"{{{svg_ns}}}svg"
    assert float(root.get("width")) > 0
    assert float(root.get("height")) > 0
    assert root.get("viewBox") is not None

    # Test the outer border rectangles (two rectangles: thin and thick border)
    polylines = root.findall(".//svg:polyline", ns)
    assert len(polylines) >= 2  # At least the two main border rectangles

    # Test text elements for grid labels
    texts = root.findall(".//svg:text", ns)

    # Should have numbers 1-12 on top and bottom (24 total)
    # and letters A-H on both sides (16 total)
    # Total text elements should be 40
    assert len(texts) == 40

    # Test coordinate labels
    number_labels = set()
    letter_labels = set()
    for text in texts:
        content = text.text
        if content.isdigit() or len(content) == 2:  # For numbers 1-12
            number_labels.add(content)
        elif len(content) == 1 and content.isalpha():  # For letters A-H
            letter_labels.add(content)

    # Verify all numbers 1-12 are present
    assert len(number_labels) == 12
    assert all(str(i) in number_labels for i in range(1, 13))

    # Verify all letters A-H are present
    expected_letters = set("ABCDEFGH")
    assert letter_labels == expected_letters

    # Save the SVG to file
    filepath = drawer.save_svg("border_representation_type_group", output_dir)
    assert os.path.exists(filepath)

    # Verify the saved file content
    with open(filepath, encoding="utf-8") as f:
        content = f.read()
        assert content.startswith('<?xml version="1.0" encoding="UTF-8"?>')
        assert '<svg xmlns="http://www.w3.org/2000/svg"' in content


def test_node_position(loaded_dexpi: DexpiModel, tmp_path):
    """Test node position drawing functionality."""
    # Get a RepresentationTypeGroup from the DEXPI model
    diagram: Diagram = loaded_dexpi.diagram
    he1_representation: RepresentationGroup = diagram.groups[2]
    he1_nozzle: RepresentationGroup = he1_representation.groups[3]
    he1_node_representation: RepresentationGroup = he1_nozzle.groups[2]
    node_position = he1_node_representation.nodePositions[0]

    # Create the drawer with a specific marker size
    marker_size = 10.0
    drawer = DrawNodePosition(node_position, marker_size=marker_size)

    # Get the SVG string
    svg_str = drawer.draw_svg()
    root = ET.fromstring(svg_str)

    # Define SVG namespace for XPath
    svg_ns = "http://www.w3.org/2000/svg"
    ns = {"svg": svg_ns}

    # Test node position group
    group = root.find("svg:g", ns)
    assert group is not None
    assert group.get("class") == "node-position"


def test_representation_group(loaded_dexpi: DexpiModel, tmp_path):
    """Test processing a RepresentationGroup and saving as SVG file."""
    # Create output directory
    output_dir = tmp_path / "representation_group_test"
    output_dir.mkdir()

    # Get a RepresentationGroup from the loaded DEXPI model
    loaded_diagram = loaded_dexpi.diagram

    # Instantiate the RepresentationGroup drawer
    drawer = DrawRepresentationGroup(group=loaded_diagram, padding=0.0, show_node_position=True)
    file_path = drawer.save_svg("representation_group", output_dir)
    assert os.path.exists(file_path)


def test_diagram(loaded_dexpi: DexpiModel, tmp_path):
    """Test processing a RepresentationGroup and saving as SVG file."""
    # Create output directory
    output_dir = tmp_path / "diagram_test"
    output_dir.mkdir()

    # Get a RepresentationGroup from the loaded DEXPI model
    loaded_diagram = loaded_dexpi.diagram

    # Instantiate the RepresentationGroup drawer
    drawer = DrawDiagram(diagram=loaded_diagram, padding=0.0, show_node_position=True)
    file_path = drawer.save_svg(loaded_diagram.name, output_dir)
    assert os.path.exists(file_path)


def test_diagram_export(loaded_dexpi: DexpiModel, tmp_path):
    """Test processing a RepresentationGroup and saving as SVG file."""
    # Create output directory
    # output_dir = "tests/test_converter/diagram_test"
    # os.makedirs(output_dir, exist_ok=True)

    # Create output directory
    output_dir = tmp_path / "diagram_test"
    output_dir.mkdir()

    # Get a RepresentationGroup from the loaded DEXPI model
    loaded_diagram = loaded_dexpi.diagram

    # Instantiate the RepresentationGroup drawer
    drawer = DrawDiagram(diagram=loaded_diagram, padding=0.0, show_node_position=False, pretty=True)
    file_path = drawer.save_svg(loaded_diagram.name, output_dir)
    assert os.path.exists(file_path)
