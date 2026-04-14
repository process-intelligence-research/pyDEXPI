"""Drawing toolkit for DEXPI diagrams and shapes.

This module provides functionality to convert DEXPI diagrams and shapes to SVG format.
It consolidates drawing-related functionality into a single, cohesive toolkit.
"""

import math
import os
from abc import ABC, abstractmethod
from pathlib import Path
from xml.etree import ElementTree as ET

from pydexpi.dexpi_classes.graphics import (
    Color,
    ConnectorLine,
    DashStyle,
    Diagram,
    Ellipse,
    EllipseArc,
    GraphicalPrimitive,
    NodePosition,
    Point,
    Polygon,
    PolyLine,
    RepresentationGroup,
    RepresentationTypeGroup,
    Shape,
    ShapeCatalogue,
    ShapeUsage,
    Stroke,
    Text,
)


class SvgRenderer:
    """Core SVG rendering functionality without abstract methods.

    This class contains all the concrete implementation for converting DEXPI
    elements to SVG format. It handles coordinate conversion, primitive conversion,
    bounds management, and SVG generation. Use this class via composition in
    classes that need SVG rendering capabilities.
    """

    # Constants for default styles and A3 dimensions (in mm)
    A3_WIDTH = 420.0  # mm
    A3_HEIGHT = 297.0  # mm

    def __init__(self, padding: float = 0.0, pretty: bool = False):
        """Initialize the renderer with optional padding and pretty mode.

        Args:
            padding: Extra space around the drawing in SVG units
            pretty: If True, applies thinner line widths (0.3x) and scales to fit A3 size
        """
        self.padding = padding
        self.pretty = pretty
        self.line_width_multiplier = 0.3 if pretty else 1.0
        self.zoom = 1.0  # Will be calculated later if pretty is True
        self.min_x = float("inf")
        self.min_y = float("inf")
        self.max_x = float("-inf")
        self.max_y = float("-inf")

    def to_svg_y(self, y: float) -> float:
        """Convert DEXPI Y coordinate to SVG Y coordinate.

        DEXPI uses mathematical coordinate system (Y increases upward)
        SVG uses screen coordinate system (Y increases downward)

        Args:
            y: Y coordinate in DEXPI coordinate system

        Returns:
            float: Y coordinate in SVG coordinate system
        """
        return -y  # Negate Y to convert from mathematical to screen coordinates

    def from_svg_y(self, svg_y: float) -> float:
        """Convert SVG Y coordinate back to DEXPI Y coordinate.

        SVG uses screen coordinate system (Y increases downward)
        DEXPI uses mathematical coordinate system (Y increases upward)

        Args:
            svg_y: Y coordinate in SVG coordinate system

        Returns:
            float: Y coordinate in DEXPI coordinate system
        """
        return -svg_y  # Negate Y to convert from screen to mathematical coordinates

    def calculate_zoom_for_a3(self) -> float:
        """Calculate the zoom factor to fit content within A3 dimensions.

        Returns:
            float: Zoom factor to scale the content to fit A3 (420mm x 297mm)
        """
        # Calculate content dimensions
        content_width = self.max_x - self.min_x + 2 * self.padding
        content_height = self.max_y - self.min_y + 2 * self.padding

        # Calculate zoom factors for both dimensions
        zoom_x = self.A3_WIDTH / content_width if content_width > 0 else 1.0
        zoom_y = self.A3_HEIGHT / content_height if content_height > 0 else 1.0

        # Return the smaller zoom to ensure content fits within A3
        return min(zoom_x, zoom_y)

    def consolidate_bounds(self, other: "SvgRenderer") -> None:
        """Consolidate bounding box with another renderer's bounds.

        Use this method when incorporating elements from another renderer
        to ensure the bounding box encompasses all elements.

        Args:
            other: Another SvgRenderer instance whose bounds should be included
        """
        self.min_x = min(self.min_x, other.min_x)
        self.min_y = min(self.min_y, other.min_y)
        self.max_x = max(self.max_x, other.max_x)
        self.max_y = max(self.max_y, other.max_y)

    def reset_bounds(self) -> None:
        """Reset the bounding box coordinates."""
        self.min_x = float("inf")
        self.min_y = float("inf")
        self.max_x = float("-inf")
        self.max_y = float("-inf")

    def update_bounds(self, x: float, y: float) -> None:
        """Update the bounding box."""
        self.min_x = min(self.min_x, x)
        self.min_y = min(self.min_y, y)
        self.max_x = max(self.max_x, x)
        self.max_y = max(self.max_y, y)

    def get_bounds(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """Get the bounding box coordinates.

        Returns:
            A tuple of (top_left, bottom_right) points where:
            - top_left: Upper-left corner (min_x, max_y)
            - bottom_right: Lower-right corner (max_x, min_y)
        """
        if (
            self.min_x == float("inf")
            or self.min_y == float("inf")
            or self.max_x == float("-inf")
            or self.max_y == float("-inf")
        ):
            return ((0.0, 0.0), (0.0, 0.0))  # Default bounds with y-coords flipped

        return ((self.min_x, self.max_y), (self.max_x, self.min_y))

    def update_svg_dimensions(self, svg: ET.Element) -> tuple[float, float]:
        """Update SVG element dimensions based on current bounds.

        Returns:
            tuple[float, float]: The calculated width and height
        """
        width = self.max_x - self.min_x + 2 * self.padding
        height = self.max_y - self.min_y + 2 * self.padding

        # Apply zoom to the displayed size
        display_width = width * self.zoom
        display_height = height * self.zoom

        # Convert Y coordinates to SVG coordinate system for viewBox
        # max_y in DEXPI (top) becomes min Y in SVG (top)
        svg_min_y = self.to_svg_y(self.max_y)
        viewbox_y = svg_min_y - self.padding

        # Set display dimensions (zoomed) but keep viewBox at original size
        # This makes the content appear larger without changing coordinates
        svg.set("width", str(display_width))
        svg.set("height", str(display_height))
        svg.set(
            "viewBox",
            f"{self.min_x - self.padding} {viewbox_y} {width} {height}",
        )

        return display_width, display_height

    def create_svg_root(self) -> ET.Element:
        """Create the SVG root element with proper dimensions."""
        # Use default bounds if none were set
        if (
            self.min_x == float("inf")
            or self.min_y == float("inf")
            or self.max_x == float("-inf")
            or self.max_y == float("-inf")
        ):
            self.min_x = self.min_y = 0
            self.max_x = self.max_y = 0

        svg = ET.Element("svg")
        svg.set("xmlns", "http://www.w3.org/2000/svg")

        # Set initial dimensions
        self.update_svg_dimensions(svg)

        return svg

    def convert_color(self, color: Color) -> str:
        """Convert DEXPI color to SVG color string."""
        if hasattr(color, "r") and hasattr(color, "g") and hasattr(color, "b"):
            return f"rgb({color.r},{color.g},{color.b})"
        return "rgb(0,0,0)"  # default black

    def convert_stroke(self, stroke: Stroke) -> dict:
        """Convert DEXPI stroke to SVG stroke attributes."""
        attrs = {}
        if stroke:
            attrs["stroke"] = self.convert_color(stroke.color)
            # Apply line width multiplier to make lines thinner while maintaining proportions
            stroke_width = stroke.width * self.line_width_multiplier
            attrs["stroke-width"] = str(stroke_width)

            # Use vector-effect to prevent stroke from scaling with viewBox
            # This keeps line widths consistent regardless of diagram size
            attrs["vector-effect"] = "non-scaling-stroke"

            if hasattr(stroke, "dashStyle"):
                # Scale dash patterns relative to stroke width for consistency
                if stroke.dashStyle.value == "Dashed":
                    dash_length = max(4, stroke_width * 4)
                    attrs["stroke-dasharray"] = f"{dash_length},{dash_length}"
                elif stroke.dashStyle.value == "Dotted":
                    dot_length = max(1, stroke_width)
                    gap_length = max(2, stroke_width * 2)
                    attrs["stroke-dasharray"] = f"{dot_length},{gap_length}"
        return attrs

    def convert_primitive(self, primitive) -> ET.Element | None:
        """Convert a DEXPI primitive to SVG element."""
        if isinstance(primitive, PolyLine):
            return self.convert_polyline(primitive)
        elif isinstance(primitive, Polygon):
            return self.convert_polygon(primitive)
        elif isinstance(primitive, Ellipse):
            return self.convert_ellipse(primitive)
        elif isinstance(primitive, EllipseArc):
            return self.convert_ellipse_arc(primitive)
        elif isinstance(primitive, Text):
            return self.convert_text(primitive)
        elif isinstance(primitive, ConnectorLine):
            return self.convert_connector_line(primitive)
        return None

    def convert_polyline(self, polyline: PolyLine) -> ET.Element:
        """Convert DEXPI polyline to SVG polyline element."""
        points = []
        for point in polyline.points:
            self.update_bounds(point.x, point.y)
            svg_y = self.to_svg_y(point.y)
            points.append(f"{point.x},{svg_y}")

        element = ET.Element("polyline")
        element.set("points", " ".join(points))
        element.set("fill", "none")

        stroke_attrs = self.convert_stroke(polyline.stroke)
        for key, value in stroke_attrs.items():
            element.set(key, value)

        return element

    def convert_polygon(self, polygon: Polygon) -> ET.Element:
        """Convert DEXPI polygon to SVG polygon element."""
        points = []
        for point in polygon.points:
            self.update_bounds(point.x, point.y)
            svg_y = self.to_svg_y(point.y)
            points.append(f"{point.x},{svg_y}")

        element = ET.Element("polygon")
        element.set("points", " ".join(points))

        fill = (
            "none"
            if hasattr(polygon, "fillStyle") and polygon.fillStyle.value == "Solid"
            else "none"
        )
        element.set("fill", fill)

        stroke_attrs = self.convert_stroke(polygon.stroke)
        for key, value in stroke_attrs.items():
            element.set(key, value)

        return element

    def convert_ellipse(self, ellipse: Ellipse) -> ET.Element:
        """Convert DEXPI ellipse to SVG ellipse element."""
        self.update_bounds(
            ellipse.center.x - ellipse.horizontalSemiAxis,
            ellipse.center.y - ellipse.verticalSemiAxis,
        )
        self.update_bounds(
            ellipse.center.x + ellipse.horizontalSemiAxis,
            ellipse.center.y + ellipse.verticalSemiAxis,
        )

        element = ET.Element("ellipse")
        element.set("cx", str(ellipse.center.x))
        svg_cy = self.to_svg_y(ellipse.center.y)
        element.set("cy", str(svg_cy))
        element.set("rx", str(ellipse.horizontalSemiAxis))
        element.set("ry", str(ellipse.verticalSemiAxis))

        if hasattr(ellipse, "rotation") and ellipse.rotation != 0:
            element.set(
                "transform",
                f"rotate({math.degrees(ellipse.rotation)} {ellipse.center.x} {svg_cy})",
            )

        fill = (
            "none"
            if hasattr(ellipse, "fillStyle") and ellipse.fillStyle.value == "Solid"
            else "none"
        )
        element.set("fill", fill)

        stroke_attrs = self.convert_stroke(ellipse.stroke)
        for key, value in stroke_attrs.items():
            element.set(key, value)

        return element

    def convert_ellipse_arc(self, arc: EllipseArc) -> ET.Element:
        """Convert DEXPI ellipse arc to SVG path element."""
        self.update_bounds(
            arc.center.x - arc.horizontalSemiAxis,
            arc.center.y - arc.verticalSemiAxis,
        )
        self.update_bounds(
            arc.center.x + arc.horizontalSemiAxis,
            arc.center.y + arc.verticalSemiAxis,
        )

        # Convert angles to radians if needed
        start_angle_rad = (
            arc.startAngle
            if math.isclose(arc.startAngle, math.radians(arc.startAngle))
            else math.radians(arc.startAngle)
        )
        end_angle_rad = (
            arc.endAngle
            if math.isclose(arc.endAngle, math.radians(arc.endAngle))
            else math.radians(arc.endAngle)
        )

        # SVG arc parameters
        angle_diff = (end_angle_rad - start_angle_rad) % (2 * math.pi)
        large_arc = 1 if angle_diff > math.pi else 0
        # When Y-axis is flipped, sweep direction must also be flipped (1 becomes 0, 0 becomes 1)
        sweep = 0  # Flip sweep direction to account for Y-axis inversion

        # Calculate points
        start_x = arc.center.x + arc.horizontalSemiAxis * math.cos(start_angle_rad)
        start_y = arc.center.y + arc.verticalSemiAxis * math.sin(start_angle_rad)
        end_x = arc.center.x + arc.horizontalSemiAxis * math.cos(end_angle_rad)
        end_y = arc.center.y + arc.verticalSemiAxis * math.sin(end_angle_rad)

        # Convert to SVG coordinates
        svg_start_y = self.to_svg_y(start_y)
        svg_end_y = self.to_svg_y(end_y)

        # Create SVG path
        element = ET.Element("path")
        d = f"M {start_x:.2f},{svg_start_y:.2f} "  # Start point
        d += f"A {arc.horizontalSemiAxis:.2f},{arc.verticalSemiAxis:.2f} "  # Radii
        d += f"{math.degrees(arc.rotation):.2f} {large_arc},{sweep} "  # Arc parameters
        d += f"{end_x:.2f},{svg_end_y:.2f}"  # End point
        element.set("d", d)
        element.set("fill", "none")

        stroke_attrs = self.convert_stroke(arc.stroke)
        for key, value in stroke_attrs.items():
            element.set(key, value)

        return element

    def convert_text(self, text: Text) -> ET.Element:
        """Convert DEXPI text to SVG text element."""
        self.update_bounds(text.position.x, text.position.y)

        svg_y = self.to_svg_y(text.position.y)
        element = ET.Element("text")
        element.set("x", str(text.position.x))
        element.set("y", str(svg_y))
        element.text = text.text

        # Handle text alignment
        if text.alignment:
            if text.alignment.value.startswith("Left"):
                element.set("text-anchor", "start")
            elif text.alignment.value.startswith("Right"):
                element.set("text-anchor", "end")
            else:  # Center alignment
                element.set("text-anchor", "middle")

            # Vertical alignment
            if text.alignment.value.endswith("Top"):
                element.set("dy", "0.5em")
            elif text.alignment.value.endswith("Bottom"):
                element.set("dy", "0.0em")
            else:  # Center vertical
                element.set("dy", "0.5em")

        # Font properties
        if text.font:
            # Use Arial as fallback font
            font_family = f"'{text.font}', Arial"
            element.set("font-family", font_family)
        if text.size:
            element.set("font-size", str(text.size))

        # Rotation
        if text.rotation != 0:
            element.set(
                "transform",
                f"rotate({text.rotation} {text.position.x} {svg_y})",
            )

        # Text color
        element.set("fill", self.convert_color(text.color) if text.color else "black")

        return element

    def convert_connector_line(self, line: ConnectorLine) -> ET.Element:
        """Convert DEXPI connector line to SVG line element."""
        for point in line.innerPoints:
            self.update_bounds(point.x, point.y)

        element = ET.Element("polyline")
        points = [f"{p.x},{self.to_svg_y(p.y)}" for p in line.innerPoints]
        element.set("points", " ".join(points))
        element.set("fill", "none")

        stroke_attrs = self.convert_stroke(line.stroke)
        for key, value in stroke_attrs.items():
            element.set(key, value)

        return element

    def add_background_rect(self, svg: ET.Element, width: float, height: float) -> None:
        """Add a background rectangle to the SVG element.

        Args:
            svg: The SVG element to add the background to
            width: The width of the background rectangle
            height: The height of the background rectangle
        """
        # Convert Y coordinates to SVG coordinate system for background rect
        # max_y in DEXPI (top) becomes min Y in SVG (top)
        svg_min_y = self.to_svg_y(self.max_y)
        bg_y = svg_min_y - self.padding

        bg = ET.Element("rect")
        bg.set("x", str(self.min_x - self.padding))
        bg.set("y", str(bg_y))
        bg.set("width", str(width))
        bg.set("height", str(height))
        bg.set("fill", "#f0f0f0")
        svg.insert(0, bg)

    def create_svg_content(self, svg: ET.Element, background: bool = True) -> tuple[float, float]:
        """Create the SVG content with common elements and processing.

        Args:
            svg: The SVG root element to add content to
            background: If True, add a background rectangle

        Returns:
            tuple[float, float]: The width and height of the SVG
        """
        width, height = self.update_svg_dimensions(svg)

        if background:
            self.add_background_rect(svg, width, height)

        return width, height

    @abstractmethod
    def _add_metadata(self, svg: ET.Element) -> None:
        """Add metadata to the SVG element.

        Args:
            svg: The SVG element to add metadata to
        """
        pass

    @abstractmethod
    def _create_content_group(self, svg: ET.Element) -> ET.Element:
        """Create and return a group element for the main content.

        Args:
            svg: The parent SVG element

        Returns:
            ET.Element: The created group element
        """
        pass

    @abstractmethod
    def _get_primitives(self) -> list:
        """Get the list of primitives to convert.

        Returns:
            list: List of primitive elements to convert
        """
        pass

    def transform_content_group(
        self,
        translate: tuple[float, float],
        rotate: float,
        scale: tuple[float, float],
        is_mirrored: bool,
        svg: ET.Element,
    ) -> str:
        """Create an SVG transform attribute string and update viewBox based on transformations.

        Args:
            translate: A tuple (tx, ty) specifying translation in x and y directions
            rotate: Rotation angle in radians
            scale: A tuple (sx, sy) specifying scale factors in x and y directions
            svg: The SVG element whose viewBox needs to be updated

        Returns:
            str: SVG transform attribute string combining translate, rotate, and scale
        """
        transforms = []
        corners = [
            (self.min_x, self.min_y),
            (self.min_x, self.max_y),
            (self.max_x, self.min_y),
            (self.max_x, self.max_y),
        ]
        transformed_corners = []

        # First apply scale and mirroring if needed
        effective_scale = list(scale)
        if is_mirrored:
            effective_scale[0] *= -1  # Mirror along Y-axis by negating X scale

        # Apply scale transform if scale is not identity or if mirrored
        if effective_scale != [1.0, 1.0] or is_mirrored:
            transforms.append(f"scale({effective_scale[0]:.2f},{effective_scale[1]:.2f})")
            for x, y in corners:
                transformed_corners.append((x * effective_scale[0], y * effective_scale[1]))
        else:
            transformed_corners = corners.copy()

        # Then apply rotation
        if rotate != 0.0:
            angle_deg = rotate
            transforms.append(f"rotate({angle_deg:.2f})")
            rotated_corners = []
            for x, y in transformed_corners:
                rx = x * math.cos(math.radians(rotate)) - y * math.sin(math.radians(rotate))
                ry = x * math.sin(math.radians(rotate)) + y * math.cos(math.radians(rotate))
                rotated_corners.append((rx, ry))
            transformed_corners = rotated_corners

        # Finally apply translation
        if translate != (0.0, 0.0):
            transforms.append(f"translate({translate[0]:.2f},{translate[1]:.2f})")
            translated_corners = []
            for x, y in transformed_corners:
                translated_corners.append((x + translate[0], y + translate[1]))
            transformed_corners = translated_corners

        # Reset bounds and update with transformed corners
        self.min_x = float("inf")
        self.min_y = float("inf")
        self.max_x = float("-inf")
        self.max_y = float("-inf")

        for x, y in transformed_corners:
            self.update_bounds(x, y)

        # Add padding to bounds
        width = self.max_x - self.min_x + 2 * self.padding
        height = self.max_y - self.min_y + 2 * self.padding

        # Convert Y coordinates to SVG coordinate system for viewBox
        # max_y in DEXPI (top) becomes min Y in SVG (top)
        svg_min_y = self.to_svg_y(self.max_y)
        viewbox_y = svg_min_y - self.padding

        # Update SVG viewBox
        svg.set("viewBox", f"{self.min_x - self.padding} {viewbox_y} {width} {height}")
        svg.set("width", str(width))
        svg.set("height", str(height))

        # Return transforms in reverse order for proper SVG transformation
        return " ".join(reversed(transforms))


class DrawSVG(ABC):
    """Minimal interface for DEXPI-to-SVG conversion using composition.

    This ABC defines the interface that concrete classes must implement,
    while delegating all rendering operations to a composed SvgRenderer instance.
    """

    def __init__(self, padding: float = 0.0, pretty: bool = False):
        """Initialize with a renderer for composition.

        Args:
            padding: Extra space around the drawing in SVG units
            pretty: If True, applies thinner line widths (0.3x) and scales to fit A3 size
        """
        self.renderer = SvgRenderer(padding, pretty)

    # Convenience delegation methods for common rendering operations
    def to_svg_y(self, y: float) -> float:
        """Delegate to renderer's to_svg_y method."""
        return self.renderer.to_svg_y(y)

    def convert_color(self, color: Color) -> str:
        """Delegate to renderer's convert_color method."""
        return self.renderer.convert_color(color)

    def consolidate_bounds(self, other: "DrawSVG") -> None:
        """Consolidate bounds with another DrawSVG instance's renderer."""
        self.renderer.consolidate_bounds(other.renderer)

    def transform_content_group(
        self,
        translate: tuple[float, float],
        rotate: float,
        scale: tuple[float, float],
        is_mirrored: bool,
        svg: ET.Element,
    ) -> str:
        """Delegate to renderer's transform_content_group method."""
        return self.renderer.transform_content_group(translate, rotate, scale, is_mirrored, svg)

    @abstractmethod
    def _add_metadata(self, svg: ET.Element) -> None:
        """Add metadata to the SVG element.

        Args:
            svg: The SVG element to add metadata to
        """
        pass

    @abstractmethod
    def _create_content_group(self, svg: ET.Element) -> ET.Element:
        """Create and return a group element for the main content.

        Args:
            svg: The parent SVG element

        Returns:
            ET.Element: The created group element
        """
        pass

    @abstractmethod
    def _get_primitives(self) -> list:
        """Get the list of primitives to convert.

        Returns:
            list: List of primitive elements to convert
        """
        pass

    def draw_svg(self, return_element: bool = False, background: bool = True) -> str | ET.Element:
        """Convert the DEXPI object to SVG.

        Args:
            return_element: If True, returns the SVG Element instead of string
            background: If True, add a background rectangle

        Returns:
            str | ET.Element: The SVG representation as a string or Element
        """
        self.renderer.reset_bounds()
        svg = self.renderer.create_svg_root()

        # Add metadata (implementation-specific)
        self._add_metadata(svg)

        # Create content group (implementation-specific)
        group = self._create_content_group(svg)

        # Convert each primitive
        for primitive in self._get_primitives():
            element = self.renderer.convert_primitive(primitive)
            if element is not None:
                group.append(element)

        # Calculate zoom for A3 if pretty mode is enabled
        if self.renderer.pretty:
            self.renderer.zoom = self.renderer.calculate_zoom_for_a3()

        # Update dimensions and add background
        width, height = self.renderer.update_svg_dimensions(svg)

        if background:
            self.renderer.add_background_rect(svg, width, height)

        ET.indent(svg, space="  ")

        if return_element:
            return svg

        xml_str = ET.tostring(svg, encoding="unicode", xml_declaration=True)
        if xml_str.startswith("<?xml"):
            xml_str = '<?xml version="1.0" encoding="UTF-8"?>' + xml_str[xml_str.find("?>") + 2 :]
        return xml_str

    def save_svg(self, object_name: str, filepath: str, background: bool = True) -> str:
        """Save SVG content to a file.

        Args:
            object_name: Name of the object being saved (used for auto-generating filename)
            filepath: Path to save the SVG file. If directory, a filename will be generated
            background: If True, add a background rectangle

        Returns:
            str: The absolute path to the saved file
        """
        filepath: Path = Path(filepath)
        if filepath.is_dir() or not filepath.suffix:
            safe_name: str = "_".join(object_name.split())
            filepath = filepath / f"{safe_name}.svg"

        filepath.parent.mkdir(parents=True, exist_ok=True)

        svg_content = self.draw_svg(return_element=False, background=background)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(svg_content)

        return str(filepath)


class DrawShape(DrawSVG):
    """Converter for DEXPI shapes to SVG format."""

    def __init__(self, shape: Shape, padding: float = 0.0, pretty: bool = False):
        """Initialize with a shape to convert.

        Args:
            shape: The shape to convert
            padding: Extra space around the drawing
            pretty: If True, applies thinner line widths (0.3x) and scales to fit A3 size
        """
        super().__init__(padding, pretty)
        self.shape = shape

    def _add_metadata(self, svg: ET.Element) -> None:
        """Add shape-specific metadata."""
        metadata = ET.SubElement(svg, "metadata")
        metadata.text = f"DEXPI Shape: {self.shape.name}"
        if hasattr(self.shape, "symbolRegistrationNumber") and self.shape.symbolRegistrationNumber:
            metadata.text += f" (Registration: {self.shape.symbolRegistrationNumber})"

    def _create_content_group(self, svg: ET.Element) -> ET.Element:
        """Create group for shape primitives."""
        group = ET.SubElement(svg, "g")
        if self.shape.name:
            group.set("id", self.shape.name)
        return group

    def _get_primitives(self) -> list:
        """Get shape primitives."""
        return self.shape.primitives


# Convenient functions for common operations
def process_shape_catalogue(catalogue: ShapeCatalogue, output_dir: str) -> dict[str, str]:
    """Process all shapes in a shape catalogue and save them as SVG files."""
    os.makedirs(output_dir, exist_ok=True)
    result = {}

    for shape in catalogue.shapes:
        safe_name = "_".join(shape.name.split())
        filename = f"{safe_name}.svg"
        filepath = os.path.join(output_dir, filename)

        drawer = DrawShape(shape)
        drawer.save_svg(shape.name, filepath)
        result[shape.name] = filepath

    return result


class DrawShapeUsage(DrawSVG):
    """Converter for DEXPI shape usage to SVG format."""

    def __init__(self, shape_usage: ShapeUsage, padding: float = 0.0, pretty: bool = False):
        """Initialize with a shape usage to convert.

        Args:
            shape_usage: The shape usage to convert
            padding: Extra space around the drawing
            pretty: If True, applies thinner line widths (0.3x) and scales to fit A3 size
        """
        super().__init__(padding, pretty)
        self.shape_usage = shape_usage
        # Create a DrawShape instance for the referenced shape
        self.shape_drawer = DrawShape(self.shape_usage.shape, padding, pretty)

    def _add_metadata(self, svg: ET.Element) -> None:
        """Add shape usage-specific metadata."""
        # Get metadata from shape drawer first
        shape_svg = self.shape_drawer.draw_svg(return_element=True)
        shape_metadata = shape_svg.find("metadata")
        if shape_metadata is not None:
            metadata = ET.SubElement(svg, "metadata")
            # Add shape usage info to the shape metadata
            metadata.text = f"ShapeUsage of {shape_metadata.text}"

    def _create_content_group(self, svg: ET.Element) -> ET.Element:
        """Create group for shape usage content.

        This creates a group and applies the necessary transformations based on
        position, rotation, scale and mirror settings.
        """
        # Create a group for this shape usage
        group = ET.SubElement(svg, "g")

        # First draw the shape using shape_drawer
        shape_element = self.shape_drawer.draw_svg(return_element=True, background=False)

        # Extract shape's content group and copy its bounds
        shape_content = shape_element.find("g")
        if shape_content is not None:
            # Copy the shape's bounds for proper transformation
            self.renderer.min_x = self.shape_drawer.renderer.min_x
            self.renderer.min_y = self.shape_drawer.renderer.min_y
            self.renderer.max_x = self.shape_drawer.renderer.max_x
            self.renderer.max_y = self.shape_drawer.renderer.max_y

            # Calculate transformations based on shape usage properties
            translate = (self.shape_usage.position.x, self.to_svg_y(self.shape_usage.position.y))
            rotate = self.shape_usage.rotation
            scale = (
                self.shape_usage.scaleX,
                self.shape_usage.scaleY,
            )
            is_mirrored = self.shape_usage.isMirrored

            # Apply transformations
            transform = self.transform_content_group(translate, rotate, scale, is_mirrored, svg)
            if transform:
                shape_content.set("transform", transform)

            # Add the transformed shape content to our group
            group.append(shape_content)

        return group

    def _get_primitives(self) -> list:
        """Get shape primitives from the referenced shape."""
        # We don't use this since we're using shape_drawer to draw primitives
        return []


class DrawRepresentationTypeGroup(DrawSVG):
    """Converter for DEXPI diagrams to SVG format."""

    def __init__(self, group: RepresentationTypeGroup, padding: float = 0.0, pretty: bool = False):
        """Initialize with a representation group to convert.

        Args:
            group: The representation group to convert
            padding: Extra space around the drawing
            pretty: If True, applies thinner line widths (0.3x) and scales to fit A3 size
        """
        super().__init__(padding, pretty)
        self.group = group

    def _add_metadata(self, svg: ET.Element) -> None:
        """Add group-specific metadata."""
        metadata = ET.SubElement(svg, "metadata")
        metadata.text = f"DEXPI RepresentationTypeGroup: {self.group.__class__.__name__}"

    def _create_content_group(self, svg: ET.Element) -> ET.Element:
        """Create group for representation type elements.

        This handles both GraphicalPrimitive elements and ShapeUsage elements:
        - ShapeUsage elements are rendered directly using DrawShapeUsage (with transformations)
        - GraphicalPrimitive elements (PolyLine, Polygon, Ellipse, EllipseArc,
          ConnectorLine, Text) are returned by _get_primitives() for standard processing
        """
        group = ET.SubElement(svg, "g")
        group.set("class", self.group.__class__.__name__.lower())

        # Handle ShapeUsage elements directly (they require transformation handling)
        for element in self.group.elements:
            if isinstance(element, ShapeUsage):
                # Create DrawShapeUsage to handle transformations
                shape_drawer = DrawShapeUsage(element, self.renderer.padding, self.renderer.pretty)
                # Draw the shape and add it to our group
                shape_element = shape_drawer.draw_svg(return_element=True, background=False)
                if shape_element is not None:
                    # Extract the content group from the shape
                    shape_content = shape_element.find("g")
                    if shape_content is not None:
                        group.append(shape_content)
            # GraphicalPrimitive elements are handled by _get_primitives() below

        return group

    def _get_primitives(self) -> list:
        """Get graphical primitive elements for rendering.

        Returns only GraphicalPrimitive elements (PolyLine, Polygon, Ellipse,
        EllipseArc, ConnectorLine, Text) since ShapeUsage elements are
        handled directly in _create_content_group.
        """
        return [
            element for element in self.group.elements if isinstance(element, GraphicalPrimitive)
        ]


class DrawNodePosition(DrawSVG):
    """Converter for DEXPI node positions to SVG format.

    Draws a crosshair marker at the node position to visually indicate connection points.
    """

    def __init__(
        self,
        node_position: NodePosition,
        padding: float = 0.0,
        marker_size: float = 10.0,
        pretty: bool = False,
    ):
        """Initialize with a node position to convert.

        Args:
            node_position: The node position to convert
            padding: Extra space around the drawing
            marker_size: Size of the crosshair marker in drawing units
            pretty: If True, applies thinner line widths (0.3x) and scales to fit A3 size
        """
        super().__init__(padding, pretty)
        self.node_position = node_position
        self.marker_size = marker_size

    def _add_metadata(self, svg: ET.Element) -> None:
        """Add node position-specific metadata."""
        pass

    def _create_content_group(self, svg: ET.Element) -> ET.Element:
        """Create group for node position marker."""
        group = ET.SubElement(svg, "g")
        group.set("class", "node-position")
        return group

    def _get_primitives(self) -> list:
        """Create primitives to represent the node position.

        Returns a list containing two PolyLine objects forming a crosshair.
        """
        x = self.node_position.position.x
        y = self.node_position.position.y
        half_size = self.marker_size / 2

        # Create default stroke style for the marker
        stroke = Stroke(
            color=Color(r=0, g=0, b=0),  # Black color
            dashStyle=DashStyle.Solid,
            width=1.0 * self.renderer.line_width_multiplier,  # Apply line width multiplier
        )

        # Create horizontal line
        horizontal = PolyLine(
            points=[Point(x=x - half_size, y=y), Point(x=x + half_size, y=y)], stroke=stroke
        )

        # Create vertical line
        vertical = PolyLine(
            points=[Point(x=x, y=y - half_size), Point(x=x, y=y + half_size)], stroke=stroke
        )

        return [horizontal, vertical]


class DrawRepresentationGroup(DrawSVG):
    """Converter for DEXPI representation groups to SVG format.

    A representation group can contain:
    - Other representation groups
    - Representation type groups (which contain graphical elements)
    - Node positions
    """

    def __init__(
        self,
        group: RepresentationGroup,
        padding: float = 0.0,
        show_node_position: bool = False,
        pretty: bool = False,
    ):
        """Initialize with a representation group to convert.

        Args:
            group: The representation group to convert
            padding: Extra space around the drawing
            show_node_position: If True, displays node position markers (default: False)
            pretty: If True, applies thinner line widths (0.3x) and scales to fit A3 size
        """
        super().__init__(padding, pretty)
        self.group = group
        self.show_node_position = show_node_position

    def _add_metadata(self, svg: ET.Element) -> None:
        """Add group-specific metadata with representation ID."""
        metadata = ET.SubElement(svg, "metadata")
        metadata.text = f"DEXPI RepresentationGroup representing: {self.group.represents.id}"

    def _create_content_group(self, svg: ET.Element) -> ET.Element:
        """Create group for representation content, handling nested groups and node positions."""
        # Create main group
        group = ET.SubElement(svg, "g")
        group.set("id", self.group.represents.id)
        group.set("class", "representation-group")

        # Process nested groups
        for nested_group in self.group.groups:
            if isinstance(nested_group, RepresentationGroup):
                # Recursively handle nested representation groups
                drawer = DrawRepresentationGroup(
                    nested_group,
                    self.renderer.padding,
                    show_node_position=self.show_node_position,
                    pretty=self.renderer.pretty,
                )
                nested_svg = drawer.draw_svg(return_element=True, background=False)
                content = nested_svg.find("g")
                if content is not None:
                    group.append(content)
                    # Consolidate bounds with nested group
                    self.consolidate_bounds(drawer)
            elif isinstance(nested_group, RepresentationTypeGroup):
                # Handle representation type groups using DrawRepresentationTypeGroup
                drawer = DrawRepresentationTypeGroup(
                    nested_group, self.renderer.padding, self.renderer.pretty
                )
                nested_svg = drawer.draw_svg(return_element=True, background=False)
                content = nested_svg.find("g")
                if content is not None:
                    group.append(content)
                    # Consolidate bounds with type group
                    self.consolidate_bounds(drawer)

        # Process node positions
        if self.show_node_position:
            for node_position in self.group.nodePositions:
                drawer = DrawNodePosition(
                    node_position,
                    self.renderer.padding,
                    marker_size=2.0,
                    pretty=self.renderer.pretty,
                )
                node_svg = drawer.draw_svg(return_element=True, background=False)
                content = node_svg.find("g")
                if content is not None:
                    group.append(content)
                    # Consolidate bounds with node position
                    self.consolidate_bounds(drawer)

        return group

    def _get_primitives(self) -> list:
        """Primitives will be handled by the nested groups' _create_content_group methods."""
        return []


class DrawDiagram(DrawSVG):
    """Converter for DEXPI diagrams to SVG format."""

    def __init__(
        self,
        diagram: Diagram,
        padding: float = 0.0,
        show_node_position: bool = False,
        pretty: bool = False,
    ):
        """Initialize with a DEXPI diagram to convert.

        Args:
            diagram: The DEXPI diagram to convert
            padding: Extra space around the drawing
            show_node_position: If True, displays node position markers (default: False)
            pretty: If True, applies thinner line widths (0.3x) and scales to fit A3 size
        """
        super().__init__(padding, pretty)
        self.diagram = diagram
        self.show_node_position = show_node_position

        # Set initial bounds from diagram
        self.renderer.min_x = diagram.minX
        self.renderer.min_y = diagram.minY
        self.renderer.max_x = diagram.maxX
        self.renderer.max_y = diagram.maxY

    def _add_metadata(self, svg: ET.Element) -> None:
        """Add diagram-specific metadata."""
        metadata = ET.SubElement(svg, "metadata")
        metadata.text = f"DEXPI Diagram: {self.diagram.name}"

    def _create_content_group(self, svg: ET.Element) -> ET.Element:
        """Create group for diagram elements.

        Since Diagram is a RepresentationGroup, we use DrawRepresentationGroup
        to handle all nested groups and elements.
        """
        # Create main group for the diagram
        group = ET.SubElement(svg, "g")
        group.set("id", f"diagram-{self.diagram.name}")
        group.set("class", "diagram")

        # Set background color from diagram
        if self.diagram.backgroundColor:
            group.set("fill", self.convert_color(self.diagram.backgroundColor))

        # Process nested groups using DrawRepresentationGroup logic
        for nested_group in self.diagram.groups:
            if isinstance(nested_group, RepresentationGroup):
                # Recursively handle nested representation groups
                drawer = DrawRepresentationGroup(
                    nested_group,
                    self.renderer.padding,
                    show_node_position=self.show_node_position,
                    pretty=self.renderer.pretty,
                )
                nested_svg = drawer.draw_svg(return_element=True, background=False)
                content = nested_svg.find("g")
                if content is not None:
                    group.append(content)
                    # Consolidate bounds with nested group
                    self.consolidate_bounds(drawer)
            elif isinstance(nested_group, RepresentationTypeGroup):
                # Handle representation type groups using DrawRepresentationTypeGroup
                drawer = DrawRepresentationTypeGroup(
                    nested_group, self.renderer.padding, self.renderer.pretty
                )
                nested_svg = drawer.draw_svg(return_element=True, background=False)
                content = nested_svg.find("g")
                if content is not None:
                    group.append(content)
                    # Consolidate bounds with type group
                    self.consolidate_bounds(drawer)

        # Process node positions if requested
        if self.show_node_position:
            for node_position in self.diagram.nodePositions:
                drawer = DrawNodePosition(
                    node_position,
                    self.renderer.padding,
                    marker_size=2.0,
                    pretty=self.renderer.pretty,
                )
                node_svg = drawer.draw_svg(return_element=True, background=False)
                content = node_svg.find("g")
                if content is not None:
                    group.append(content)
                    # Consolidate bounds with node position
                    self.consolidate_bounds(drawer)

        return group

    def _get_primitives(self) -> list:
        """Get diagram elements.

        Primitives are handled by nested groups' _create_content_group methods,
        so we return an empty list here.
        """
        return []
