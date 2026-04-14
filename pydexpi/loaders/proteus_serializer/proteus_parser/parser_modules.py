"""Parser modules for Proteus XML loading.

In general, each module is responsible for parsing a specific type of element from the Proteus XML
structure. The modules rely on an external function that handles instantiation of the parsers for
an XML element."""

from __future__ import annotations

import datetime
import math
import types
import xml.etree.ElementTree as ET

import pydexpi.toolkits.piping_toolkit as ptk
from pydexpi.dexpi_classes import (
    customization,
    dataTypes,
    dexpiModel,
    enumerations,
    equipment,
    graphics,
    instrumentation,
    metaData,
    physicalQuantities,
    piping,
)
from pydexpi.dexpi_classes.pydantic_classes import DexpiBaseModel
from pydexpi.loaders.proteus_serializer.proteus_parser.core import (
    ErrorLevels,
    InternalParserError,
    ModuleContext,
    ParserModule,
)
from pydexpi.loaders.proteus_serializer.proteus_parser.parsing_utils import (
    ErrorTemplates,
    add_by_inferring_type,
    filter_none,
    is_associated_with,
    redirect_errors_to_registry,
)
from pydexpi.toolkits import base_model_utils as bmt


### GENERIC MODULES ###
class GenericAttributeParser(ParserModule):
    """Parses generic attributes from XML elements.

    Processes attribute sets (DexpiAttributes, CustomAttributes, DexpiCustomAttributes)
    and converts them into the appropriate format for DEXPI component classes. No reference or
    control pass is required.

    Attributes
    ----------
    valid_attribute_lists : list of str (class attribute)
        Valid attribute set types according to DEXPI standards.
    context : ModuleContext
        The context containing the ID-, and element stack, error-, and object registry.
    element : ET.Element
        The XML element containing the attributes to be parsed.
    """

    valid_attribute_lists = [
        "DexpiAttributes",
        "CustomAttributes",
        "DexpiCustomAttributes",
    ]

    def __init__(
        self,
        context: ModuleContext,
        parent_element: ET.Element,
    ) -> None:
        """Initialize the GenericAttributeParser.

        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        parent_element : ET.Element
            The XML element containing the attributes to be parsed.
        """
        super().__init__(context)
        self.element = parent_element

    def compositional_pass(
        self,
        component_class: type[DexpiBaseModel],
    ) -> dict:
        """Parse all attributes in the compositional pass.

        The attributes are retrieved from all valid generic attribute sets in the XML element. The
        attributes are then merged into a single dictionary, with duplicate attributes checked and
        logged as errors.

        Parameters
        ----------
        component_class : type[DexpiBaseModel]
            The DEXPI component class for which attributes are being parsed.

        Returns
        -------
        dict
            A dictionary of parsed attributes, where keys are attribute names and values are the
            corresponding attribute values in the DEXPI format.
        """
        # Get all attribute sets from the XML element
        attr_set_elements = self.element.findall("GenericAttributes")

        generic_attr_sets = [
            self.parse_single_attribute_set(attr_set, component_class)
            for attr_set in attr_set_elements
        ]

        # Check for duplicate attributes across all sets
        duplicates = GenericAttributeParser.check_for_duplicates(generic_attr_sets)
        if duplicates:
            self.register_error(
                f"Duplicate attributes found: {', '.join(duplicates)}. Duplicates ignored.",
                level=ErrorLevels.ERROR,
            )

        # Merge all generic attributes into a single dictionary
        all_generic_attributes = GenericAttributeParser.merge_attributes(generic_attr_sets)
        return all_generic_attributes

    def parse_single_attribute_set(
        self,
        element: ET.Element,
        component_class: type[DexpiBaseModel],
    ) -> dict:
        """Parse a single attribute set from an attribute set XML element.

        Parameters
        ----------
        element : ET.Element
            The XML element containing the attribute set to be parsed.
        component_class : type[DexpiBaseModel]
            The DEXPI component class for which attributes are being parsed.

        Returns
        -------
        dict
            A dictionary of parsed attributes for the given attribute set.
        """
        try:
            attributes = {}
            attr_set_type = element.get("Set")
            component_attributes = component_class.model_fields
            multi_language_strings = {}

            # If attribute set type is not recognized, log a warning and return empty attributes
            if attr_set_type not in self.valid_attribute_lists:
                self.register_error(
                    f"Invalid attribute set discovered: {attr_set_type}. Attributes ignored.",
                    level=ErrorLevels.WARNING,
                )
                return attributes

            for attribute in element:
                # Edit proteus attribute name to correspond to DEXPI class field.
                name = attribute.get("Name")
                name = name.removesuffix("AssignmentClass")
                name = name.removesuffix("Specialization")
                name = name[0].lower() + name[1:]
                # Only parse an attribute if it exists both in proteus and DEXPI.
                if name in component_attributes:
                    value = attribute.get("Value")
                    # skip attribute if value is not given
                    if value is None:
                        continue
                    field_annotation = component_attributes[name].annotation
                    if isinstance(field_annotation, types.UnionType):
                        unit = component_attributes[name].annotation.__args__[0]
                    else:
                        unit = component_attributes[name].annotation
                    unit_name = unit.__name__
                    if unit is str:
                        attributes[name] = str(value)
                    elif unit is int:
                        attributes[name] = int(value)
                    elif unit is dataTypes.MultiLanguageString:
                        if name not in multi_language_strings.keys():
                            multi_language_strings[name] = []
                        single_language_string = dataTypes.SingleLanguageString(
                            language=attribute.get("Language"),
                            value=attribute.get("Value"),
                        )
                        multi_language_strings[name].append(single_language_string)
                    elif hasattr(physicalQuantities, unit_name):
                        # null value for a physical quantity is currently not implemented
                        unit_name = unit_name.removeprefix("Nullable")
                        unit_class = getattr(physicalQuantities, unit_name)
                        dexpi_attribute = unit_class(
                            value=value,
                            unit=unit_class.model_fields["unit"]
                            .annotation[attribute.get("Units")]
                            .value,
                        )
                        attributes[name] = dexpi_attribute
                    elif hasattr(enumerations, unit_name):
                        unit_class = getattr(enumerations, unit_name)
                        attributes[name] = unit_class[value]
                    else:
                        self.register_error(
                            f"Unsupported attribute type for {name}: {unit_name}. "
                            "Attribute ignored.",
                            level=ErrorLevels.ERROR,
                        )
        except Exception as e:
            self.register_error(
                f"Error parsing attributes: {e}",
                level=ErrorLevels.ERROR,
                proteus_id=self.context.get_last_id(),
                exception=e,
            )
            attributes = {}

        return attributes

    @staticmethod
    def check_for_duplicates(attribute_sets: list[dict]) -> set[str]:
        """Check for duplicate attribute names across multiple attribute sets.

        Parameters
        ----------
        attribute_sets : list of dict
            A list of dictionaries representing attribute sets.

        Returns
        -------
        set of str
            A set of duplicate attribute names.
        """
        seen = set()
        duplicates = set()
        for attributes in attribute_sets:
            for name in attributes.keys():
                if name in seen:
                    duplicates.add(name)
                else:
                    seen.add(name)
        return duplicates

    @staticmethod
    def merge_attributes(attribute_sets: list[dict]) -> dict:
        """Merge multiple attribute sets into a single dictionary. Duplicates are skipped.

        Parameters
        ----------
        attribute_sets : list of dict
            A list of dictionaries representing attribute sets, where each dictionary contains
            attribute names as keys.

        Returns
        -------
        dict
            A dictionary containing all attributes from the provided sets, with duplicates handled.
        """
        merged_attributes = {}
        for attributes in attribute_sets:
            for name, value in attributes.items():
                if name not in merged_attributes:
                    merged_attributes[name] = value
        return merged_attributes


class AssociationParser(ParserModule):
    """Parser for association elements in the Proteus XML structure.

    This class is responsible for parsing association elements, retrieving the respective objects
    in the reference pass, providing all necessary information, and check validity of the
    association. Retrieves the element ID and type during compositional pass, and retrieves the
    associated object in the reference pass. No control pass is required.

    Attributes
    ----------
    context : ModuleContext
        The context containing the ID-, and element stack, error-, and object registry.
    element : ET.Element
        The XML element containing the association to be parsed.
    association_id : str
        The ID of the association, retrieved from the XML element.
    association_type : str
        The type of the association, retrieved from the XML element.
    referenced_item : DexpiBaseModel
        The DEXPI object associated with this association, retrieved in the reference pass.
    """

    def __init__(self, context: ModuleContext, element: ET.Element) -> None:
        """Initialize the AssociationParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        element : ET.Element
            The XML element containing the association to be parsed.
        """
        super().__init__(context)
        self.element = element

        self.association_id = None
        self.association_type = None
        self.referenced_item = None

    @redirect_errors_to_registry
    def compositional_pass(self) -> None:
        """Parse the association in the compositional pass by retrieving the ID and type.

        Returns
        -------
        None
            This method does not return any value, as no object is created in this pass.
        """
        # Get the ID of the association
        if self.element is not None:
            self.association_id = self.element.get("ItemID")
            self.association_type = self.element.get("Type")

    @redirect_errors_to_registry
    def reference_pass(self) -> None:
        """Retrieve the referenced item from the context's object registry.

        This method attempts to find the associated object in the context's object registry using
        the association ID. If found, it sets `referenced_item` to the associated object.
        """
        # Call super to call reference pass on all submodules
        super().reference_pass()

        # Retrieve the referenced item from the context's object registry
        if self.association_id is not None:
            self.referenced_item = self.get_object_from_registry(self.association_id)

    def is_valid(self) -> bool:
        """Check if the association is valid.

        An association is considered valid if it has a valid ID, type, and referenced item (not
        None).

        Returns
        -------
        bool
            True if the association is valid, False otherwise.
        """
        return (
            self.association_id is not None
            and self.association_type is not None
            and self.referenced_item is not None
        )

    def get_error_message(self) -> str:
        """Get the error message for an invalid association.

        Returns
        -------
        str
            An error message indicating the issue with the association.
        """
        if self.association_id is None:
            return "Association ItemID is missing in the XML element. Association skipped."
        elif self.association_type is None:
            return "Association Type is missing in the XML element. Association skipped."
        elif self.referenced_item is None:
            return (
                f"Associated object with ID {self.association_id} not found. Association skipped."
            )
        else:
            raise RuntimeError("No error in this association parser.")

    def get_id(self) -> str:
        """Get the ID of the associated object.

        Returns
        -------
        str
            The ID of the associated object.
        """
        return self.association_id

    def get_type(self) -> str:
        """Get the type of the association.

        Returns
        -------
        str
            The type of the association.
        """
        return self.association_type

    def get_referenced_item(self) -> DexpiBaseModel:
        """Get the referenced item of the association.

        The referenced item is previously retrieved in the reference pass.

        Returns
        -------
        DexpiBaseModel
            The DEXPI object associated with this association.
        """
        return self.referenced_item


class OffPageConnectorReferenceParser(ParserModule):
    """Parser for OffPageConnectorReference elements in the DEXPI model.

    This parser handles both OffPageConnectorObjectReference and OffPageConnectorReferenceByNumber
    for both piping and information flow elements. The correct type is retrieved from the
    ComponentClass Element. In the compositional pass,
    it composes the generic attributes and creates the appropriate OffPageConnectorReference object.
    In the reference pass, it resolves associations and sets the referenced connector if the
    reference is an object reference.

    Attributes
    ----------
    context : ModuleContext
        The context containing the ID-, and element stack, error-, and object registry.
    element : ET.Element
        The XML element containing the pipe off-page connector reference to be parsed.
    association_parsers : list[AssociationParser]
        List of association parsers to be used by the pipe off-page connector reference parser.
    generic_attribute_parser : GenericAttributeParser
        The parser for generic attributes.
    reference_obj : piping.PipeOffPageConnectorReference |
                    instrumentation.SignalOffPageConnectorReference |
                    None
        The reference object being constructed by the parser. It can be either a
        PipeOffPageConnectorReference or a SignalOffPageConnectorReference, depending on the
        context.
    """

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        association_parsers: list[AssociationParser],
        generic_attribute_parser: GenericAttributeParser,
    ) -> None:
        """Initialize the OffPageConnectorReferenceParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The module context providing access to the ID stack and error registry.
        element : ET.Element
            The XML element containing the pipe off-page connector reference to be parsed.
        association_parsers : list[AssociationParser]
            List of association parsers to be used by the pipe off-page connector reference parser.
        generic_attribute_parser : GenericAttributeParser
            The parser for generic attributes.
        """
        super().__init__(context)
        self.element = element
        self.ref_id = None
        self.reference_obj = None

        self.association_parsers = association_parsers
        self.register_submodule_list(association_parsers)

        self.generic_attribute_parser = generic_attribute_parser
        self.register_submodule(generic_attribute_parser)

    @redirect_errors_to_registry
    def compositional_pass(
        self,
    ) -> (
        piping.PipeOffPageConnectorReference
        | instrumentation.SignalOffPageConnectorReference
        | None
    ):
        """Parse the pipe off-page connector reference in the compositional pass.

        This method retrieves the ID of the reference, determines the class type from the
        ComponentClass attribute, retrieves the class from the piping or instrumentation module,
        composes the generic attributes, and creates an instance of the appropriate reference class.
        It registers the reference object in the context's object registry.

        Returns
        -------
        piping.PipeOffPageConnectorReference | instrumentation.SignalOffPageConnectorReference | None
            An instance of the PipeOffPageConnectorReference or SignalOffPageConnectorReference class
            created from the parsed data, or None if an error occurs.
        """
        # Get element ID. If not available, log an error.
        self.ref_id = self.element.get("ID")
        if self.ref_id is None:
            self.register_error(*ErrorTemplates.id_not_found("OffPageConnectorReference"))
            return None

        # Determine the class type from the ComponentClass attribute
        class_name = self.element.get("ComponentClass")

        # Retrieve the class from the piping or the instrumentation module
        try:
            ParserClass = getattr(piping, class_name)
        except AttributeError:
            try:
                ParserClass = getattr(instrumentation, class_name)
            except AttributeError:
                self.register_error(
                    f"Unknown ComponentClass '{class_name}' for pipe off-page connector reference.",
                    level=ErrorLevels.ERROR,
                )
                return None

        # Compose generic attributes
        generic_attributes = self.generic_attribute_parser.compositional_pass(ParserClass)

        # Compose the associations
        for association_parser in self.association_parsers:
            association_parser.compositional_pass()

        # Create a PipeOffPageConnectorReference with the composed attributes
        self.reference_obj = ParserClass(proteusID=self.ref_id, **generic_attributes)

        # Register the pipe off-page connector reference
        self.register_object(self.ref_id, self.reference_obj)

        return self.reference_obj

    @redirect_errors_to_registry
    def reference_pass(self) -> None:
        """Perform a reference pass over the pipe off-page connector reference.

        Establishes associations for the pipe off-page connector reference if it is a reference
        by object. If the reference is a reference by number, no associations are allowed.
        """

        # Call super().reference_pass() to call reference pass on all submodules
        super().reference_pass()

        # Skip pass if the reference object or ID is not available due to previous error
        if not self.reference_obj or not self.ref_id:
            self.register_error(*ErrorTemplates.skip_pass("reference", "OffPageConnectorReference"))
            return

        if isinstance(
            self.reference_obj,
            piping.PipeOffPageConnectorObjectReference
            | instrumentation.SignalOffPageConnectorObjectReference,
        ):
            # If the reference is an object reference, resolve associations
            for association_parser in self.association_parsers:
                assoc_type = association_parser.get_type()
                if not association_parser.is_valid():
                    # Log error and skip association
                    self.register_error(
                        association_parser.get_error_message(),
                        level=ErrorLevels.ERROR,
                    )
                    continue

                elif assoc_type != "refers to":
                    # Not permitted for off-page connector references, add warning
                    self.register_error(
                        *ErrorTemplates.inval_assoc_type("OffPageConnectorReference", assoc_type)
                    )
                    continue
                else:
                    associated_object = association_parser.get_referenced_item()
                    associated_id = association_parser.get_id()

                    try:
                        self.reference_obj.referencedConnector = associated_object
                    except ValueError as e:
                        # If the association cannot be added, log an error
                        self.register_error(
                            *ErrorTemplates.assoc_adding_error(
                                "OffPageConnectorReference",
                                associated_id,
                            ),
                            exception=e,
                        )
        else:
            # If the reference is a reference by number, no associations are allowed.
            if self.association_parsers:
                self.register_error(
                    "Associations are not allowed for OffPageConnectorReference by number. "
                    "Associations skipped.",
                    level=ErrorLevels.WARNING,
                )


### EQUIPMENT MODULES ###
class NozzleParser(ParserModule):
    """The NozzleParser is a module for parsing nozzles from XML elements.

    This class processes nozzle elements and converts them into DEXPI nozzles. It has connection
    point parsers to parse the relevant connection points. No reference pass is required, but
    control pass is performed to check associations.

    Attributes
    ----------
    context : ModuleContext
        The context containing the ID-, and element stack, error-, and object registry.
    element : ET.Element
        The XML element containing the nozzles to be parsed.
    connection_point_parsers : list[ConnectionPointParser]
        List of connection point parsers to be used by the nozzle parser.
    association_parsers : list[AssociationParser]
        List of association parsers to be used by the nozzle parser.
    generic_attribute_parser : GenericAttributeParser
        Generic attribute parser to be used by the nozzle parser.
    nozzle_obj : equipment.Nozzle
        The DEXPI nozzle object created from the parsed attributes and connection points.
    nozzle_id : str
        The ID of the DEXPI nozzle object."""

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        connection_point_parsers: list[ConnectionPointParser],
        association_parsers: list[AssociationParser],
        generic_attribute_parser: GenericAttributeParser,
        shape_usage_parser: ShapeUsageParser,
        label_parsers: list[LabelParser],
    ) -> None:
        """Initialize the NozzleParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        element : ET.Element
            The XML element containing the nozzle to be parsed.
        connection_point_parsers : list[ConnectionPointParser]
            List of connection point parsers to be used by the nozzle parser.
        association_parsers : list[AssociationParser]
            List of association parsers to be used by the nozzle parser.
        generic_attribute_parser : GenericAttributeParser
            Generic attribute parser to be used by the nozzle parser.
        """
        super().__init__(context)
        self.element = element
        self.nozzle_id = None
        self.nozzle_obj = None
        self.nozzle_dwg = None

        # Set and register connection point parsers
        self.connection_point_parsers = connection_point_parsers
        self.register_submodule_list(connection_point_parsers)

        # Set and register association parsers
        self.association_parsers = association_parsers
        self.register_submodule_list(association_parsers)

        # Set and register generic attribute parser
        self.generic_attribute_parser = generic_attribute_parser
        self.register_submodule(generic_attribute_parser)

        # Set and register shape usage parser
        self.shape_usage_parser = shape_usage_parser
        self.register_submodule(shape_usage_parser)

        # Set and register label parsers
        self.label_parsers = label_parsers
        self.register_submodule_list(label_parsers)

    @redirect_errors_to_registry
    def compositional_pass(self) -> equipment.Nozzle | None:
        """Parse the nozzle in the compositional pass.

        This method retrieves the nozzle ID, composes connection points, and merges generic
        attributes. It creates an instance of the Nozzle class with the composed attributes and
        registers it. In the reference pass, it establishes the reference to the chamber attribute
        if available. The control pass checks for any missed "is located in" and "is the location
        of" associations and attempts to establish them by inference if missing.

        Returns
        -------
        equipment.Nozzle | None
            The Nozzle class created with the parsed attributes and connection points, or None if
            an error occurs.
        """

        # Get the ID of the nozzle. If not available, log an error.
        self.nozzle_id = self.element.get("ID")
        if self.nozzle_id is None:
            self.register_error(*ErrorTemplates.id_not_found("Nozzle"))
            return None

        # Compose connection points
        piping_nodes = []
        for connection_point_parser in self.connection_point_parsers:
            parsed_nodes = connection_point_parser.compositional_pass()
            if parsed_nodes is not None:
                piping_nodes.extend(parsed_nodes)

        # Compose association parsers
        for association_parser in self.association_parsers:
            association_parser.compositional_pass()

        # Compose generic attributes
        generic_attributes = self.generic_attribute_parser.compositional_pass(equipment.Nozzle)

        # Make nozzle
        nozzle_kwargs = generic_attributes.copy()
        nozzle_kwargs["nodes"] = filter_none(piping_nodes)

        new_nozzle = equipment.Nozzle(proteusId=self.nozzle_id, **nozzle_kwargs)
        self.nozzle_obj = new_nozzle

        # Register nozzle
        self.register_object(self.nozzle_id, new_nozzle)

        return new_nozzle

    @redirect_errors_to_registry
    def reference_pass(self):
        """Perform a reference pass to collect the nozzle's referenced chambers"""
        # Call super to call reference pass on all submodules
        super().reference_pass()

        # Skip pass if the reference object or ID is not available due to previous error
        if not (self.nozzle_obj and self.nozzle_id):
            self.register_error(*ErrorTemplates.skip_pass("reference", "Nozzle"))
            return

        # Get and add associated elements
        for association_parser in self.association_parsers:
            # If associated ID is not available, log an error and skip the association
            if not association_parser.is_valid():
                self.register_error(
                    association_parser.get_error_message(),
                    level=ErrorLevels.ERROR,
                )
                continue

            assoc_object = association_parser.get_referenced_item()
            assoc_id = association_parser.get_id()
            assoc_type = association_parser.get_type()
            if assoc_type == "is located in":
                try:
                    self.nozzle_obj.chamber = assoc_object
                except Exception as e:
                    self.register_error(
                        f"Error encountered trying to add chamber reference to {assoc_id} to "
                        f"nozzle: {e}",
                        ErrorLevels.ERROR,
                        exception=e,
                    )

            elif assoc_type == "is the location of":
                # Handled in control pass, so skipped here
                pass
            else:
                # Not permitted for nozzles, add warning
                self.register_error(
                    f"Association of type {assoc_type} is not "
                    "permitted for nozzles. Association skipped.",
                    level=ErrorLevels.WARNING,
                )

    @redirect_errors_to_registry
    def control_pass(self) -> None:
        """Perform a control pass over the nozzle's associations.

        Iterate over association elements and check if they are valid. If they are valid, but not
        created during the compositional pass, attempt to recover the association by adding it
        by inferring type. Log all inconsistencies encountered.
        """
        # Call super.control_pass() to call control pass on all submodules
        super().control_pass()

        # Skip pass if the reference object or ID is not available due to previous error
        if not (self.nozzle_obj and self.nozzle_id):
            self.register_error(*ErrorTemplates.skip_pass("control", "Nozzle"))
            return

        # Otherwise, proceed with control pass
        for association_parser in self.association_parsers:
            if not association_parser.is_valid():
                # Log error and skip association
                self.register_error(
                    association_parser.get_error_message(),
                    level=ErrorLevels.ERROR,
                )
                continue

            elif association_parser.get_type() not in ["is located in", "is the location of"]:
                # Not permitted for nozzles, but warning already added in reference pass.
                pass

            else:
                associated_object = association_parser.get_referenced_item()
                association_id = association_parser.get_id()
                if not (
                    is_associated_with(self.nozzle_obj, associated_object)
                    or is_associated_with(associated_object, self.nozzle_obj)
                ):
                    # Log warning and try to add association in control pass
                    self.register_error(*ErrorTemplates.no_assoc_ctrl("Nozzle", association_id))
                    try:
                        fld = add_by_inferring_type(self.nozzle_obj, associated_object)
                        # Log an info error if the association was added in control pass
                        inf = ErrorTemplates.assoc_added_ctrl("Nozzle", association_id, fld)
                        self.register_error(*inf)
                    except ValueError:
                        # Try adding association in reverse order
                        try:
                            fld = add_by_inferring_type(associated_object, self.nozzle_obj)
                            # Log an info error if the association was added in control pass
                            inf = ErrorTemplates.assoc_added_ctrl("Nozzle", association_id, fld)
                            self.register_error(*inf)
                        except ValueError as e:
                            # If the association cannot be added, log an error
                            self.register_error(
                                *ErrorTemplates.assoc_not_added_ctrl("Nozzle", association_id),
                                exception=e,
                            )

    def drawing_pass(self) -> graphics.RepresentationGroup | None:
        """Perform a drawing pass over the nozzle."""

        # Partial groups and node_positions list for representation group
        groups = []
        node_positions = []

        # Process shape usage
        shape_usage = self.shape_usage_parser.drawing_pass()
        if shape_usage:
            static = graphics.Static(elements=[shape_usage])
            groups.append(static)

        # Process labels
        labels = [parser.drawing_pass() for parser in self.label_parsers]
        labels = filter_none(labels)
        for label in labels:
            groups.append(label)

        self.nozzle_dwg = graphics.RepresentationGroup(
            represents=self.nozzle_obj, groups=groups, nodePositions=node_positions
        )

        # Process node positions from connection points
        connection_points_dict = {}
        for parser in self.connection_point_parsers:
            cp_dict = parser.drawing_pass()
            if cp_dict:
                connection_points_dict.update(cp_dict)

        # Separate PipingNodePosition and InstrumentationNodePosition
        piping_positions = []
        instrumentation_positions = []

        # Process the positions from the dictionary values
        for position in connection_points_dict.values():
            if isinstance(position, graphics.PipingNodePosition):
                piping_positions.append(position)
            elif isinstance(position, graphics.InstrumentationNodePosition):
                instrumentation_positions.append(position)

        # Add piping positions as connection points in a RepresentationGroup
        if piping_positions:
            connection_point = graphics.RepresentationGroup(
                represents=self.nozzle_obj, groups=[], nodePositions=piping_positions
            )
            self.nozzle_dwg.groups.append(connection_point)

        # Add instrumentation positions directly to the main node_positions
        if instrumentation_positions:
            self.nozzle_dwg.nodePositions.extend(instrumentation_positions)

        self.register_object(f"{self.nozzle_id}_cp_node_positions", connection_points_dict)

        return self.nozzle_dwg


class EquipmentParser(ParserModule):
    """The EquipmentParser is a module for parsing equipment from XML elements.

    This class processes equipment elements and converts them into DEXPI equipment classes. Includes
    nozzles, subequipment, associations, and generic attributes. Establishes the "is location of"
    relationships in the reference pass, and attempts to recover "is located in" and "is location
    of" relationships in the control pass.

    Attributes
    ----------
    context : ModuleContext
        The context containing the ID-, and element stack, error-, and object registry.
    element : ET.Element
        The XML element containing the equipment to be parsed.
    nozzle_parsers : list[NozzleParser]
        List of nozzle parsers to be used by the equipment parser.
    subequipment_parsers : list[EquipmentParser]
        List of subequipment parsers to be used by the equipment parser.
    association_parsers : list[AssociationParser]
        List of association parsers to be used by the equipment parser.
    generic_attribute_parser : GenericAttributeParser
        The generic attribute parser to be used by the equipment parser.
    shape_usage_parser : ShapeUsageParser
        The shape usage parser to be used by the equipment parser.
    graphical_primitive_parsers : list[GraphicalPrimitiveParser]
        List of graphical primitive parsers to be used by the equipment parser.
    label_parsers : list[LabelParser]
        List of label parsers to be used by the equipment parser.
    equipment_obj : equipment.Equipment
        The equipment object being constructed by the parser.
    equipment_id : str
        The ID of the equipment being constructed.
    """

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        nozzle_parsers: list[NozzleParser],
        subequipment_parsers: list[EquipmentParser],
        association_parsers: list[AssociationParser],
        generic_attribute_parser: GenericAttributeParser,
        shape_usage_parser: ShapeUsageParser,
        graphical_primitive_parsers: list[GraphicalPrimitiveParser],
        label_parsers: list[LabelParser],
    ) -> None:
        """Initialize the EquipmentParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        element : ET.Element
            The XML element containing the equipment to be parsed.
        nozzle_parsers : list[NozzleParser]
            List of nozzle parsers to be used by the equipment parser.
        subequipment_parsers : list[EquipmentParser]
            List of subequipment parsers to be used by the equipment parser.
        association_parsers : list[AssociationParser]
            List of association parsers to be used by the equipment parser.
        generic_attribute_parser : GenericAttributeParser
            The generic attribute parser to be used by the equipment parser.
        shape_usage_parser : ShapeUsageParser
            The shape usage parser to be used by the equipment parser.
        graphical_primitive_parsers : list[GraphicalPrimitiveParser]
            List of graphical primitive parsers to be used by the equipment parser.
        label_parsers : list[LabelParser]
            List of label parsers to be used by the equipment parser.
        """
        super().__init__(context)
        self.element = element
        self.equipment_obj = None
        self.equipment_id = None
        self.equipment_dwg = None

        # Initialize parser for nozzles
        self.nozzle_parsers = nozzle_parsers
        self.register_submodule_list(nozzle_parsers)

        # Initialize parser for subequipment
        self.subequipment_parsers = subequipment_parsers
        self.register_submodule_list(subequipment_parsers)

        # Initialize parser for associations
        self.association_parsers = association_parsers
        self.register_submodule_list(association_parsers)

        # Initialize parser for generic attributes
        self.gen_attr_parser = generic_attribute_parser
        self.register_submodule(generic_attribute_parser)

        # Initialize parser for shape usage
        self.shape_usage_parser = shape_usage_parser
        # There is a possibility that shape usage parser is None, e.g. for subequipment
        if shape_usage_parser is not None:
            self.register_submodule(shape_usage_parser)

        # Initialize parsers for graphical primitives
        self.graphical_primitive_parsers = graphical_primitive_parsers
        self.register_submodule_list(graphical_primitive_parsers)

        # Initialize parser for labels
        self.label_parsers = label_parsers
        self.register_submodule_list(label_parsers)

    @redirect_errors_to_registry
    def compositional_pass(self) -> equipment.Equipment | None:
        """Perform a compositional pass over the equipment and its components.

        This method processes the equipment element and its subcomponents, including nozzles and
        subequipment, to create a equipment object. The type is inferred from the ComponentClass XML
        attribute. For this, the value of Component class is retrieved from the equipment pyDEXPI
        equipment package. If None is found, a warning is logged and the equipment is treated as
        CustomEquipment.

        Returns
        -------
        equipment.Equipment | None
            The constructed equipment object if successful, or None if an error occurs during
            parsing.
        """
        # Get the ID of the equipment. If not available, log an error.
        self.equipment_id = self.element.get("ID")
        if self.equipment_id is None:
            self.register_error(*ErrorTemplates.id_not_found("Equipment"))
            return None

        kwargs = {}

        # Get the equipment type
        class_name = self.element.get("ComponentClass")

        # Manage the differentiation between subtagged and tagged column sections
        if class_name == "ColumnSection":
            class_name = (
                "TaggedColumnSection"
                if self.context.element_stack[-2] != "Equipment"
                else "SubTaggedColumnSection"
            )

        # If class name not part of equipment, treat it as custom equipment
        try:
            MyClass = getattr(equipment, class_name)
        except AttributeError:
            MyClass = equipment.CustomEquipment
            kwargs["typeName"] = class_name

            # Log a warning that the class name is invalid
            self.register_error(
                f"Invalid class {class_name} for equipment. Using CustomEquipment instead.",
                level=ErrorLevels.WARNING,
            )

        # Process nozzles
        nozzles = [parser.compositional_pass() for parser in self.nozzle_parsers]

        # Process subequipment
        subequipment = [parser.compositional_pass() for parser in self.subequipment_parsers]

        # Compose associations
        for association_parser in self.association_parsers:
            association_parser.compositional_pass()

        # Process generic attributes
        generic_attributes = self.gen_attr_parser.compositional_pass(MyClass)
        kwargs.update(generic_attributes)

        # Create the equipment object
        equipment_obj = MyClass(proteusId=self.equipment_id, nozzles=filter_none(nozzles), **kwargs)

        # Add subequipment by inferring type
        for subequipment_item in subequipment:
            add_by_inferring_type(subequipment_item, equipment_obj)

        # Register the equipment object
        self.register_object(self.equipment_id, equipment_obj)

        self.equipment_obj = equipment_obj
        return equipment_obj

    @redirect_errors_to_registry
    def reference_pass(self) -> None:
        """Perform a reference pass over the equipment's associations.

        This method processes the associations of the equipment by iterating through the association
        elements of type "is the location of". It retrieves associated objects and adds them to the
        equipment object by inferring the type from the field annotation.
        """
        # Call super to call reference pass on all submodules
        super().reference_pass()

        # Skip pass if the reference object or ID is not available due to previous error
        if not (self.equipment_obj and self.equipment_id):
            self.register_error(*ErrorTemplates.skip_pass("reference", "Equipment"))
            return

        # Get and add associated elements
        for association_parser in self.association_parsers:
            # If associated ID is not available, log an error and skip the association
            if not association_parser.is_valid():
                self.register_error(
                    association_parser.get_error_message(),
                    level=ErrorLevels.ERROR,
                )
                continue

            # Add the associated object by inferring type. Skip nozzle associations, they are
            # handled by nozzle parsers.
            assoc_object = association_parser.get_referenced_item()
            assoc_id = association_parser.get_id()
            assoc_type = association_parser.get_type()
            if assoc_type == "is the location of" and not isinstance(
                assoc_object, equipment.Nozzle
            ):
                try:
                    add_by_inferring_type(assoc_object, self.equipment_obj)
                    # This error handling is necessary because sometimes the association
                    # is the other way around for reference attributes in dexpi
                except ValueError:
                    try:
                        add_by_inferring_type(self.equipment_obj, assoc_object)
                        # Log info error if the association was added in reverse
                        self.register_error(
                            f"Association {self.equipment_id} with {assoc_id} added in "
                            "reverse order.",
                            level=ErrorLevels.INFO,
                        )
                    except ValueError as e:
                        # If the association cannot be added, log an error
                        self.register_error(
                            *ErrorTemplates.assoc_adding_error("Equipment", assoc_id),
                            exception=e,
                        )
            elif assoc_type == "is the location of" and isinstance(assoc_object, equipment.Nozzle):
                # This association is handled in control pass, so we skip it here
                pass
            elif association_parser.get_type() == "is located in":
                # This association is handled in control pass, so we skip it here
                pass
            else:
                # Not permitted for equipment, add warning
                self.register_error(*ErrorTemplates.inval_assoc_type("Equipment", assoc_type))

    @redirect_errors_to_registry
    def control_pass(self) -> None:
        """Perform a control pass over the equipment's associations.

        This method checks if all associations have been made correctly by checking the
        complementary association element. For this, it checks the associations of type
        "is located in" and "is the location of". Any association that is not previously established
        will be attempted to be recovered by adding it by inferring type.
        """
        # Call super.control_pass() to call control pass on all submodules
        super().control_pass()

        # Skip pass if the reference object or ID is not available due to previous error
        if not (self.equipment_obj and self.equipment_id):
            self.register_error(*ErrorTemplates.skip_pass("control", "Equipment"))
            return

        # Otherwise, proceed with control pass
        for association_parser in self.association_parsers:
            if not association_parser.is_valid():
                # Log error and skip association
                self.register_error(
                    association_parser.get_error_message(),
                    level=ErrorLevels.ERROR,
                )
                continue

            else:
                associated_object = association_parser.get_referenced_item()
                associated_id = association_parser.get_id()
                if association_parser.get_type() == "is the location of" and not isinstance(
                    associated_object, equipment.Nozzle
                ):
                    # Handled in reference pass
                    pass
                elif association_parser.get_type() == "is located in":
                    if not (
                        is_associated_with(self.equipment_obj, associated_object)
                        or is_associated_with(associated_object, self.equipment_obj)
                    ):
                        # Log warning and try to add association in control pass
                        self.register_error(
                            *ErrorTemplates.no_assoc_ctrl("Equipment", associated_id)
                        )
                        try:
                            fld = add_by_inferring_type(self.equipment_obj, associated_object)
                            # Log an info error if the association was added in control pass
                            self.register_error(
                                *ErrorTemplates.assoc_added_ctrl("Equipment", associated_id, fld)
                            )
                        except ValueError:
                            # This error handling is necessary because sometimes the association
                            # is the other way around for reference attributes in dexpi
                            try:
                                fld = add_by_inferring_type(associated_object, self.equipment_obj)
                                # Log info error if the association was added in reverse
                                self.register_error(
                                    *ErrorTemplates.assoc_added_ctrl(
                                        "Equipment", associated_id, fld, reverse=True
                                    )
                                )
                            except ValueError as e:
                                # If the association cannot be added, log an error
                                self.register_error(
                                    *ErrorTemplates.assoc_not_added_ctrl(
                                        "Equipment", associated_id
                                    ),
                                    exception=e,
                                )

    @redirect_errors_to_registry
    def drawing_pass(self) -> graphics.RepresentationGroup | None:
        """Perform a drawing pass over the equipment's shape usage and labels.

        This method processes the shape usage and label elements of the equipment, if available,
        to create a visual representation of the equipment. It assigns the shape usage and labels
        of equipment object. Also construct from submodules.
        """

        # Skip pass if the reference object or ID is not available due to previous error
        if not (self.equipment_obj and self.equipment_id):
            self.register_error(*ErrorTemplates.skip_pass("drawing", "Equipment"))
            return

        # Process nozzles
        nozzles_dwg = [parser.drawing_pass() for parser in self.nozzle_parsers]

        # Partial groups and node_positions list for representation group
        groups = []
        node_positions = []

        # Process graphical primitives
        graphical_primitives = []
        for primitive_parser in self.graphical_primitive_parsers:
            primitive = primitive_parser.compositional_pass()
            if primitive is not None:
                graphical_primitives.append(primitive)

        # Process shape usage and combine with graphical primitives in Static element
        static_elements = []

        # Add shape usage if available
        shape_usage = self.shape_usage_parser.drawing_pass()
        if shape_usage:
            static_elements.append(shape_usage)

        # Add graphical primitives to static elements
        static_elements.extend(graphical_primitives)

        # Create Static group if we have any elements
        if static_elements:
            static = graphics.Static(elements=static_elements)
            groups.append(static)

        # Process labels
        labels = [parser.drawing_pass() for parser in self.label_parsers]
        labels = filter_none(labels)
        for label in labels:
            groups.append(label)

        self.equipment_dwg = graphics.RepresentationGroup(
            represents=self.equipment_obj, groups=groups, nodePositions=node_positions
        )

        for nozzle_item in nozzles_dwg:
            if nozzle_item is not None:
                self.equipment_dwg.groups.append(nozzle_item)

        return self.equipment_dwg


### PIPING MODULES ###
class PipingNodeParser(ParserModule):
    """The PipingNodeParser is a module for parsing piping nodes from XML elements.

    This class processes piping node elements and converts them into DEXPI piping nodes. It also
    handles generic attribute parsing. No reference pass or control pass is required.

    Attributes
    ----------
    context : ModuleContext
        The context containing the ID-, and element stack, error-, and object registry.
    element : ET.Element
        The XML element containing the piping node to be parsed.
    generic_attribute_parser : GenericAttributeParser
        The generic attribute parser to be used by the piping node parser.
    position_parsers : list[PositionParser]
        List of position parsers to be used by the piping node parser.
    """

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        generic_attribute_parser: GenericAttributeParser,
        position_parsers: list[PositionParser],
    ) -> None:
        """Initialize the PipingNodeParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        element : ET.Element
            The XML element containing the piping node to be parsed.
        generic_attribute_parser : GenericAttributeParser
            The generic attribute parser to be used by the piping node parser.
        position_parsers : list[PositionParser]
            List of position parsers to be used by the piping node parser.
        """
        super().__init__(context)
        self.element = element
        self.piping_node_id = None
        self.piping_node = None
        self.piping_node_dwg = None

        # Set generic attribute parser
        self.generic_attribute_parser = generic_attribute_parser
        self.register_submodule(self.generic_attribute_parser)

        # Set position parsers
        self.position_parsers = position_parsers
        self.register_submodule_list(position_parsers)

    @redirect_errors_to_registry
    def compositional_pass(self) -> piping.PipingNode | None:
        """Parse the piping node in the compositional pass.

        Retrieves the node ID, composes generic attributes, and creates an instance of PipingNode
        with the composed attributes. Registers the node in the context's object registry.


        Returns
        -------
        piping.PipingNode | None
            An instance of the PipingNode class created from the parsed data, or None if an error
            occurs.
        """
        # Get the ID of the node. If not available, log an error.
        self.piping_node_id = self.element.get("ID")
        if self.piping_node_id is None:
            self.register_error(*ErrorTemplates.id_not_found("Node"))

        # Make generic attribute set parsers
        generic_attributes = self.generic_attribute_parser.compositional_pass(piping.PipingNode)

        # Create a PipingNode with the composed attributes
        self.piping_node = piping.PipingNode(proteusId=self.piping_node_id, **generic_attributes)

        # Register node
        self.register_object(self.piping_node_id, self.piping_node)

        return self.piping_node

    @redirect_errors_to_registry
    def drawing_pass(self) -> tuple[str, graphics.PipingNodePosition] | None:
        """Perform a drawing pass over the piping node's position.

        This method processes the position element of the piping node, if available, to create a
        visual representation of the piping node's position. It assigns the position to the piping
        node object.
        """
        if len(self.position_parsers) > 1:
            self.register_error(
                f"Found {len(self.position_parsers)} Position elements for PipingNode, "
                "expected at most 1. Using the first one.",
                level=ErrorLevels.WARNING,
            )
        elif len(self.position_parsers) == 0:
            return None

        position_parser = self.position_parsers[0]

        # Process position
        position, _, _ = position_parser.compositional_pass()
        if position:
            self.piping_node_dwg = graphics.PipingNodePosition(
                node=self.piping_node, position=position
            )
            return self.piping_node_id, self.piping_node_dwg
        else:
            self.register_error(
                "No position found for piping node. Drawing pass skipped.",
                level=ErrorLevels.ERROR,
            )
            return None


class ConnectionPointParser(ParserModule):
    """The ConnectionPointParser is a module for parsing connection points from XML elements.

    This class processes connection points and converts them into DEXPI piping nodes. No reference
    or control pass is required. Keeps track of the flow in and out indices, which are determined
    during the compositional pass.

    Attributes
    ----------
    context : ModuleContext
        The context in which the module operates, providing access to the ID stack and error registry.
    element : ET.Element
        The XML element containing the connection points to be parsed.
    piping_node_parsers : list[PipingNodeParser]
        A list of piping node parsers to be used for parsing the connection points.
    flow_in_index : int | None
        The index of the inflow connection point, set during the compositional pass. -1 indicates
        that the inflow connection point has not been parsed yet.
    flow_out_index : int | None
        The index of the outflow connection point, set during the compositional pass. -1 indicates
        that the outflow connection point has not been parsed yet.
    """

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        piping_node_parsers: list[PipingNodeParser],
        instrumentation_node_parsers: list[InstrumentationNodeParser],
    ) -> None:
        """Initialize the ConnectionPointParser with the XML element and context.

        Also sets node to keep track generic attribute sets for each node.

        Parameters
        ----------
        context : ModuleContext
            The module context providing access to the ID stack and error registry.
        element : ET.Element
            The XML element containing the connection points to be parsed.
        piping_node_parsers : list[PipingNodeParser]
            List of piping node parsers to be used by the connection point parser.
        instrumentation_node_parsers : list[InstrumentationNodeParser]
            List of instrumentation node parsers to be used by the connection point parser.
        """

        super().__init__(context)
        self.element = element
        self.connection_points_dwg = None

        # Set and register piping node parsers
        self.piping_node_parsers = piping_node_parsers
        self.register_submodule_list(piping_node_parsers)

        # Set and register instrumentation node parsers
        self.instrumentation_node_parsers = instrumentation_node_parsers
        self.register_submodule_list(instrumentation_node_parsers)

        # Initialize some special proteus attributes to be parsed in compositional pass (-1 as
        # sentinel value. -1 means not parsed yet, None means not available in XML):
        self.flow_in_index = -1
        self.flow_out_index = -1

    @redirect_errors_to_registry
    def compositional_pass(self) -> list[piping.PipingNode] | None:
        """Parse all connection points in the compositional pass.

        This method iterates through all "Node" elements in the XML, and collects and returns the
        created PipingNode instances. Retrieves and determines the main inflow and outflow nodes.
        Also contains some further consistency checks, such as comparing the NumPoints attribute
        with the number of parsed nodes.

        Returns
        -------
        list[piping.PipingNode] | None
            A list of PipingNode instances created from the parsed connection points or None if
            an error occurs during parsing.
        """
        piping_nodes = [parser.compositional_pass() for parser in self.piping_node_parsers]

        # Retrieve the special proteus attributes for connection points
        # Num_points (Irrelevant for parsing, but can be used for extra validation):
        try:
            num_points = int(self.element.get("NumPoints", None))
            if num_points is None:
                self.register_error(
                    "NumPoints attribute in ConnectionPoints is missing in the XML element. "
                    "Irrelevant for parsing.",
                    level=ErrorLevels.WARNING,
                )
            else:
                if num_points != len(self.element.findall("Node")):
                    self.register_error(
                        f"Potential mismatch in number of connection points: {num_points} "
                        f"specified but {len(self.element.findall('Node'))} found.",
                        level=ErrorLevels.WARNING,
                    )
        except Exception as e:
            self.register_error(
                f"Error parsing NumPoints attribute (Irrelevant for parsing): {e}",
                level=ErrorLevels.WARNING,
                exception=e,
            )

        # Flow_in_index and flow_out_index:
        try:
            idx = self.element.get("FlowIn", None)
            self.flow_in_index = int(idx) if idx is not None else None
        except Exception as e:
            self.register_error(
                f"Error parsing FlowIn attributes: {e}. Defaulting to None.",
                level=ErrorLevels.WARNING,
                exception=e,
            )
            self.flow_in_index = None
        try:
            idx = self.element.get("FlowOut", None)
            self.flow_out_index = int(idx) if idx is not None else None
        except Exception as e:
            self.register_error(
                f"Error parsing FlowOut attributes: {e}. Defaulting to None.",
                level=ErrorLevels.WARNING,
                exception=e,
            )
            self.flow_out_index = None

        return filter_none(piping_nodes)

    def get_inflow_index(self) -> int | None:
        """Get the index of the inflow connection point.

        Returns
        -------
        int
            The index of the inflow connection point, or None if not set.
        """
        if self.flow_in_index == -1:
            raise InternalParserError("Run compositional pass before accessing inflow index.")
        return self.flow_in_index

    def get_outflow_index(self) -> int | None:
        """Get the index of the outflow connection point.

        Returns
        -------
        int
            The index of the outflow connection point, or None if not set.
        """
        if self.flow_out_index == -1:
            raise InternalParserError("Run compositional pass before accessing outflow index.")
        return self.flow_out_index

    @redirect_errors_to_registry
    def drawing_pass(self) -> dict[str, graphics.NodePosition] | None:
        """Perform a drawing pass over the connection points.

        Returns
        -------
        dict[str, graphics.NodePosition] | None
            A dictionary mapping connection point IDs to their NodePosition objects.
            Returns None if no valid connection points were found.
        """
        # Get results from both piping and instrumentation node parsers
        piping_results = [parser.drawing_pass() for parser in self.piping_node_parsers]
        instrumentation_results = [
            parser.drawing_pass() for parser in self.instrumentation_node_parsers
        ]

        # Combine and filter out None results
        all_results = filter_none(piping_results + instrumentation_results)

        # Convert list of (id, position) tuples to dictionary
        self.connection_points_dwg = {id_: pos for id_, pos in all_results}

        return self.connection_points_dwg if self.connection_points_dwg else None


class PipingComponentParser(ParserModule):
    """The PipingComponentParser is a module for parsing piping components from XML elements.

    This class processes piping component elements and converts them into DEXPI piping components.
    No reference pass is required, but the control pass checks if all referencing associations have
    been resolved.

    Attributes
    ----------
    context : ModuleContext
        The context containing the ID-, and element stack, error-, and object registry.
    element : ET.Element
        The XML element representing the piping component.
    connection_point_parsers : list[ConnectionPointParser]
        List of connection point parsers to be used by the piping component parser.
    association_parsers : list[AssociationParser]
        List of association parsers to be used by the piping component parser.
    generic_attribute_parser : GenericAttributeParser
        The generic attribute parser to be used by the piping component parser.
    component_obj : piping.PipingNetworkSegmentItem | None
        The piping component object being constructed by the parser.
    component_id : str | None
        The ID of the piping component being constructed.
    nodes : list[piping.PipingNode]
        List of piping nodes that are part of the component.
    main_inflow_node : piping.PipingNode | None
        The main inflow node of the component, determined during the compositional pass.
    main_outflow_node : piping.PipingNode | None
        The main outflow node of the component, determined during the compositional pass.
    """

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        connection_point_parsers: list[ConnectionPointParser],
        association_parsers: list[AssociationParser],
        generic_attribute_parser: GenericAttributeParser,
        shape_usage_parser: ShapeUsageParser,
        label_parsers: list[LabelParser],
    ) -> None:
        """Initialize the PipingComponentParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The module context providing access to the ID stack and error registry.
        element : ET.Element
            The XML element containing the piping component to be parsed.
        connection_point_parsers : list[ConnectionPointParser]
            List of connection point parsers to be used by the piping component parser.
        association_parsers : list[AssociationParser]
            List of association parsers to be used by the piping component parser.
        generic_attribute_parser : GenericAttributeParser
            The generic attribute parser to be used by the piping component parser.
        shape_usage_parser : ShapeUsageParser
            The shape usage parser to be used by the piping component parser.
        label_parsers : list[LabelParser]
            List of label parsers to be used by the piping component parser.
        """
        super().__init__(context)
        self.element = element
        self.component_obj = None
        self.component_id = None
        self.component_dwg = None

        # Set and register connection point parsers
        self.connection_point_parsers = connection_point_parsers
        self.register_submodule_list(connection_point_parsers)

        # Set and register association parsers
        self.association_parsers = association_parsers
        self.register_submodule_list(association_parsers)

        # Set and register generic attribute parser
        self.gen_attr_parser = generic_attribute_parser
        self.register_submodule(generic_attribute_parser)

        # Set and register shape usage parser
        self.shape_usage_parser = shape_usage_parser
        self.register_submodule(shape_usage_parser)

        # Set and register label parsers
        self.label_parsers = label_parsers
        self.register_submodule_list(label_parsers)

        # Keep track of nodes in the component
        self.nodes = []

        # Keep track of main inflow node and main outflow node
        self.main_inflow_node = None
        self.main_outflow_node = None

    @redirect_errors_to_registry
    def compositional_pass(self) -> piping.PipingNetworkSegmentItem | None:
        """Parse the piping component in the compositional pass.

        This method retrieves all data from the XML element and composes connection points,
        associations, and generic attributes. It creates an instance of the PipingNetworkSegmentItem
        class with the composed attributes, registers, and returns it.

        Returns
        -------
        piping.PipingNetworkSegmentItem | None
            An instance of the PipingNetworkSegmentItem class created from the parsed attributes and
            connection points or None if an error occurred during parsing.
        """
        # Get the ID of the piping component. If not available, log an error.
        self.component_id = self.element.get("ID")
        if self.component_id is None:
            self.register_error(*ErrorTemplates.id_not_found("PipingComponent"))
            return None

        kwargs = {}

        # Get the component type
        class_name = self.element.get("ComponentClass")

        # If class name not part of piping, treat it as custom equipment
        try:
            MyClass = getattr(piping, class_name)
        except AttributeError:
            MyClass = piping.CustomPipingComponent
            kwargs["typeName"] = class_name

            # Log a warning that the class name is invalid
            self.register_error(
                f"Invalid class {class_name} for PipingComponent. Using CustomPipingComponent "
                f"instead.",
                level=ErrorLevels.WARNING,
            )

        # Compose connection points
        piping_nodes = []
        for connection_point_parser in self.connection_point_parsers:
            parsed_nodes = connection_point_parser.compositional_pass()
            if parsed_nodes is not None:
                piping_nodes.extend(parsed_nodes)

            # Retrieve inflow and outflow nodes
            inflow_index = connection_point_parser.get_inflow_index()
            outflow_index = connection_point_parser.get_outflow_index()

            if inflow_index is not None:
                if self.main_inflow_node is None:
                    if inflow_index > len(piping_nodes):
                        self.register_error(
                            f"Inflow index {inflow_index} is out of bounds for the number of "
                            f"piping nodes {len(piping_nodes)}. Using first node instead.",
                            level=ErrorLevels.ERROR,
                            proteus_id=self.component_id,
                        )
                    else:
                        self.main_inflow_node = piping_nodes[inflow_index - 1]
                else:
                    self.register_error(
                        "Multiple inflow nodes found. Only one inflow node is allowed. "
                        "Using first encountered node.",
                        level=ErrorLevels.ERROR,
                        proteus_id=self.component_id,
                    )
            if outflow_index is not None:
                if self.main_outflow_node is None:
                    if outflow_index > len(piping_nodes):
                        self.register_error(
                            f"Outflow index {outflow_index} is out of bounds for the number of "
                            f"piping nodes {len(piping_nodes)}. Using first node instead.",
                            level=ErrorLevels.ERROR,
                            proteus_id=self.component_id,
                        )
                    else:
                        self.main_outflow_node = piping_nodes[outflow_index - 1]
                else:
                    self.register_error(
                        "Multiple outflow nodes found. Only one outflow node is allowed. "
                        "Using first encountered node.",
                        level=ErrorLevels.ERROR,
                        proteus_id=self.component_id,
                    )

        # Compose associations
        for association_parser in self.association_parsers:
            association_parser.compositional_pass()

        # Compose generic attributes
        generic_attributes = self.gen_attr_parser.compositional_pass(MyClass)

        # Create a PipingNetworkSegmentItem with the composed attributes
        segment_item_kwargs = generic_attributes.copy()
        segment_item_kwargs["nodes"] = piping_nodes

        new_segment_item = MyClass(proteusId=self.component_id, **segment_item_kwargs)

        # Register segment item
        self.register_object(self.component_id, new_segment_item)

        # Keep track of obj in self.component obj and nodes in self.nodes
        self.nodes = piping_nodes
        self.component_obj = new_segment_item

        return new_segment_item

    @redirect_errors_to_registry
    def control_pass(self) -> None:
        """Perform a control pass over the piping component's associations.

        This is to catch the 'is the location of' associations as sensing locations that are missed
        in the reference pass."""
        # Call super.control_pass() to call control pass on all submodules
        super().control_pass()

        # Skip pass if the reference object or ID is not available due to previous error
        if not (self.component_obj and self.component_id):
            self.register_error(*ErrorTemplates.skip_pass("control", "PipingComponent"))
            return

        # Otherwise, proceed with control pass. Check if associations have been made correctly.
        for association_parser in self.association_parsers:
            if not association_parser.is_valid():
                # Log error and skip association
                self.register_error(
                    association_parser.get_error_message(),
                    level=ErrorLevels.ERROR,
                )
                continue

            elif association_parser.get_type() not in ["is the location of", "is referenced by"]:
                # Not permitted for piping components, add warning
                self.register_error(
                    f"Association of type {association_parser.get_type()} is not "
                    "permitted for piping components. Association skipped.",
                    level=ErrorLevels.WARNING,
                )

            else:
                associated_object = association_parser.get_referenced_item()
                association_id = association_parser.get_id()
                if not is_associated_with(self.component_obj, associated_object):
                    # Log warning and try to add association in control pass
                    self.register_error(
                        *ErrorTemplates.no_assoc_ctrl("PipingComponent", association_id)
                    )
                    try:
                        fld = add_by_inferring_type(self.component_obj, associated_object)
                        # Log an info error if the association was added in control pass
                        self.register_error(
                            *ErrorTemplates.assoc_added_ctrl("PipingComponent", association_id, fld)
                        )
                    except ValueError as e:
                        # If the association cannot be added, log an error
                        self.register_error(
                            *ErrorTemplates.assoc_not_added_ctrl("PipingComponent", association_id),
                            exception=e,
                        )

    @redirect_errors_to_registry
    def drawing_pass(self) -> graphics.RepresentationGroup | None:
        """Perform a drawing pass over the piping component's shape usage and labels.

        This method processes the shape usage and label elements of the piping component, if
        available, to create a visual representation of the piping component. It assigns the shape
        usage and labels of piping component object. Also construct from submodules.
        """

        # Skip pass if the reference object or ID is not available due to previous error
        if not (self.component_obj and self.component_id):
            self.register_error(*ErrorTemplates.skip_pass("drawing", "PipingComponent"))
            return

        # Partial groups and node_positions list for representation group
        groups = []
        node_positions = []

        # Process shape usage
        shape_usage = self.shape_usage_parser.drawing_pass()
        if shape_usage:
            static = graphics.Static(elements=[shape_usage])
            groups.append(static)

        # Process labels
        labels_dwg = [parser.drawing_pass() for parser in self.label_parsers]
        labels = filter_none(labels_dwg)
        for label in labels:
            groups.append(label)

        self.component_dwg = graphics.RepresentationGroup(
            represents=self.component_obj, groups=groups, nodePositions=node_positions
        )

        # Process node positions from connection points
        # We only have one connection point parser per equipment
        connection_points_dict = self.connection_point_parsers[0].drawing_pass()

        if connection_points_dict:
            # Create a representation group with all node positions
            connection_point = graphics.RepresentationGroup(
                represents=self.component_obj,
                groups=[],
                nodePositions=list(connection_points_dict.values()),
            )
            self.component_dwg.groups.append(connection_point)

        self.register_object(f"{self.component_id}_cp_node_positions", connection_points_dict)

        return self.component_dwg

    def get_main_inflow_node(self) -> piping.PipingNode | None:
        """Get the main inflow node of the piping component.

        This is the node that is explicitly found as inflow node or, by default, the first node.
        If no nodes are available, it returns None.

        Returns
        -------
        piping.PipingNode | None
            The main inflow node of the piping component.
        """
        if self.main_inflow_node is not None:
            return self.main_inflow_node
        # If no explicit inflow node is found, return the first inflow node or None
        # if no nodes are available.
        return self.nodes[0] if len(self.nodes) > 0 else None

    def get_main_outflow_node(self) -> piping.PipingNode | None:
        """Get the main outflow node of the piping component.

        This is the node that is explicitly found as outflow node or, by default, the second node.
        If no nodes are available, it returns None.

        Returns
        -------
        piping.PipingNode | None
            The main outflow node of the piping component.
        """
        if self.main_outflow_node is not None:
            return self.main_outflow_node
        # If no explicit outflow node is found, return the first outflow node or None
        # if no nodes are available.
        return self.nodes[1] if len(self.nodes) > 1 else None


class PipeOffPageConnectorParser(PipingComponentParser):
    """Parser for PipeOffPageConnector elements in the DEXPI model.

    It behaves like the component parser, but additionally handles the pipe off-page connector
    references.  In the compositional pass, it additionally composes the pipe off-page connector
    references. The control of the inverse OPC reference is also handled by the parent class
    PipingComponentParser via the "is referenced by" association.

    Attributes
    ----------
    reference_parsers : list[OffPageConnectorReferenceParser]
        A list of parsers for the pipe off-page connector references."""

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        connection_point_parsers: list[ConnectionPointParser],
        reference_parsers: list[OffPageConnectorReferenceParser],
        association_parsers: list[AssociationParser],
        generic_attribute_parser: GenericAttributeParser,
        shape_usage_parser: ShapeUsageParser,
        label_parsers: list[LabelParser],
    ) -> None:
        """Initialize the PipeOffPageConnectorParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The module context providing access to the ID stack and error registry.
        element : ET.Element
            The XML element containing the pipe off-page connector to be parsed.
        connection_point_parsers : list[ConnectionPointParser]
            List of connection point parsers to be used by the pipe off-page connector parser.
        association_parsers : list[AssociationParser]
            List of association parsers to be used by the pipe off-page connector parser.
        generic_attribute_parser : GenericAttributeParser
            The generic attribute parser to be used by the pipe off-page connector parser.
        shape_usage_parser : ShapeUsageParser
            The shape usage parser to be used by the pipe off-page connector parser.
        label_parsers : list[LabelParser]
            List of label parsers to be used by the pipe off-page connector parser.
        """
        super().__init__(
            context,
            element,
            connection_point_parsers,
            association_parsers,
            generic_attribute_parser,
            shape_usage_parser,
            label_parsers,
        )

        self.opc = None
        self.opc_id = None
        self.opc_dwg = None

        self.reference_parsers = reference_parsers
        self.register_submodule_list(reference_parsers)

        # register shape usage parser
        self.shape_usage_parser = shape_usage_parser
        self.register_submodule(shape_usage_parser)

        # register label parsers
        self.label_parsers = label_parsers
        self.register_submodule_list(label_parsers)

    @redirect_errors_to_registry
    def compositional_pass(self) -> piping.PipeOffPageConnector | None:
        """Parse the pipe off-page connector in the compositional pass.

        Performs the compositional pass just like the PipingComponentParser, but also handles
        the pipe off-page connector references. If multiple references are found, it keeps only the
        first valid one and logs a warning.

        Returns
        -------
        piping.PipeOffPageConnector | None
            An instance of the PipeOffPageConnector class created from the parsed data, or None
            if an error occurs during parsing.
        """
        self.opc: piping.PipeOffPageConnector = super().compositional_pass()

        if self.opc is None:
            # If the parent compositional pass failed, do nothing
            return self.opc

        if len(self.reference_parsers) > 1:
            # Log a warning if there are multiple reference parsers
            self.register_error(
                "Multiple PipeOffPageConnectorReference parsers found. Keeping only the first "
                "valid one.",
                level=ErrorLevels.WARNING,
            )
        for reference_parser in self.reference_parsers:
            reference_obj = reference_parser.compositional_pass()
            if reference_obj:
                # If the reference object is valid, add it to the PipeOffPageConnector
                self.opc.connectorReference = reference_obj
                break

        return self.opc

    @redirect_errors_to_registry
    def drawing_pass(self) -> graphics.RepresentationGroup | None:
        """Perform a drawing pass over the piping component's shape usage and labels.

        This method processes the shape usage and label elements of the piping component, if
        available, to create a visual representation of the piping component. It assigns the shape
        usage and labels of piping component object. Also construct from submodules.
        """

        # Skip pass if the reference object or ID is not available due to previous error
        self.opc_id = self.element.get("ID")
        if not (self.opc and self.opc_id):
            self.register_error(*ErrorTemplates.skip_pass("drawing", "PipeOffPageConnector"))
            return

        # Partial groups and node_positions list for representation group
        groups = []
        node_positions = []

        # Process shape usage
        shape_usage = self.shape_usage_parser.drawing_pass()
        if shape_usage:
            static = graphics.Static(elements=[shape_usage])
            groups.append(static)

        # Process labels
        labels_dwg = [parser.drawing_pass() for parser in self.label_parsers]
        labels = filter_none(labels_dwg)
        for label in labels:
            groups.append(label)

        self.opc_dwg = graphics.RepresentationGroup(
            represents=self.opc, groups=groups, nodePositions=node_positions
        )

        # Process node positions from connection points
        # We only have one connection point parser per off-page connector
        connection_points_dict = self.connection_point_parsers[0].drawing_pass()

        if connection_points_dict:
            # Create a representation group with all node positions
            connection_point = graphics.RepresentationGroup(
                represents=self.opc, groups=[], nodePositions=list(connection_points_dict.values())
            )
            self.opc_dwg.groups.append(connection_point)

        self.register_object(f"{self.opc_id}_cp_node_positions", connection_points_dict)

        return self.opc_dwg


class PropertyBreakParser(PipingComponentParser):
    """Parser for PropertyBreak elements in the DEXPI model.

    In this implementation, it behaves exactly like PipingComponentParser."""


class CenterLineParser(ParserModule):
    """Parser for CenterLine elements in the DEXPI model.

    Creates a Pipe for a center line and parses related generic attributes in
    compositional pass. No reference or control pass is required.

    Attributes
    ----------
    context : ModuleContext
        The context containing the ID-, and element stack, error-, and object registry.
    element : ET.Element
        The XML element containing the center line to be parsed.
    generic_attribute_parser : GenericAttributeParser
        The parser for generic attributes.
    presentation_parsers : list[PresentationParser]
        List of presentation parsers to be used by the center line parser.
    """

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        generic_attribute_parser: GenericAttributeParser,
        presentation_parsers: list[PresentationParser],
        coordinate_parsers: list[CoordinateParser],
    ) -> None:
        """Initialize the CenterLineParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The module context providing access to the ID stack and error registry.
        element : ET.Element
            The XML element containing the center line to be parsed.
        generic_attribute_parser : GenericAttributeParser
            The parser for generic attributes.
        presentation_parsers : list[PresentationParser]
            List of presentation parsers to be used by the center line parser.
        coordinate_parsers : list[CoordinateParser]
            List of coordinate parsers to be used by the center line parser.
        """
        super().__init__(context)
        self.element = element
        self.center_line_dwg = None
        self.center_line_pipe = None

        # Set and register generic attribute parser
        self.generic_attribute_parser = generic_attribute_parser
        self.register_submodule(generic_attribute_parser)

        # Set and register presentation parsers
        self.presentation_parsers = presentation_parsers
        self.register_submodule_list(presentation_parsers)

        # Set and register coordinate parsers
        self.coordinate_parsers = coordinate_parsers
        self.register_submodule_list(coordinate_parsers)

    @redirect_errors_to_registry
    def compositional_pass(self) -> piping.Pipe | None:
        """Parse the center line in the compositional pass.

        Parses the generic attributes and creates a Pipe for the center line.

        Returns
        -------
        piping.Pipe | None
            An instance of the Pipe class created from the parsed data or None if an error
            occurs during parsing.
        """
        # Compose generic attributes
        generic_attrs = self.generic_attribute_parser.compositional_pass(piping.Pipe)

        # Create the Pipe for the center line
        self.center_line_pipe = piping.Pipe(
            generic_attributes=generic_attrs,
        )

        return self.center_line_pipe

    @redirect_errors_to_registry
    def drawing_pass(self) -> graphics.ConnectorLine | None:
        """Perform a drawing pass over the center line's presentation and coordinates.

        This method processes the presentation and coordinate elements of the center line, if
        available, to create a visual representation of the center line. It assigns the presentation
        and coordinates to the center line object.
        """

        # Process presentation
        if len(self.presentation_parsers) > 1:
            self.register_error(
                f"Found {len(self.presentation_parsers)} Presentation elements for CenterLine, "
                "expected at most 1. Using the first one.",
                level=ErrorLevels.WARNING,
            )
        elif len(self.presentation_parsers) == 0:
            return None

        presentation_parser = self.presentation_parsers[0]

        presentation = presentation_parser.compositional_pass()

        coordinates = [parser.compositional_pass() for parser in self.coordinate_parsers]
        coordinates = filter_none(coordinates)

        connector_line = graphics.ConnectorLine(
            innerPoints=coordinates,
            stroke=presentation,
            source=None,
            target=None,
        )

        self.center_line_dwg = graphics.Static(elements=[connector_line])

        return self.center_line_dwg


class PipingNetworkSegmentParser(ParserModule):
    """Parser for PipingNetworkSegment elements in the DEXPI model.

    Converts PipingNetworkSegment XML elements into pyDEXPI PipingNetworkSegment objects. Composes
    all components, connections, associations, and generic attributes in compositional pass and
    creates the pyDEXPI PipingNetworkSegment object. Hereby, DirectPipingConnections are inferred
    from the absence of pipes between components (as defined by DEXPI spec). In the reference pass,
    all explicit and implicit sources and targets of the segment connections are established, as
    well as the explicit sources and targets of the segment itself (In accordance with the DEXPI
    convention). In control pass, checks if the associations of the object were correctly
    established, and tries to recover missed associations.

    Attributes
    ----------
    context : ModuleContext
        The context containing the ID-, and element stack, error-, and object registry.
    element : ET.Element
        The XML element containing the piping network segment to be parsed.
    item_parsers : list[PipingComponentParser | PipeOffPageConnectorParser | PropertyBreakParser]
        A list of parsers for the items in the piping network segment.
    center_line_parsers : list[CenterLineParser]
        A list of parsers for the center lines in the piping network segment.
    ordered_element_parsers : list[PipingComponentParser | PipeOffPageConnectorParser |
                                   PropertyBreakParser | CenterLineParser]
        A list of parsers for the ordered elements in the piping network segment that preserve the
        order of elements.
    association_parsers : list[AssociationParser]
        A list of parsers for the associations in the piping network segment.
    generic_attribute_parser : GenericAttributeParser
        A parser for the generic attributes of the piping network segment.
    pns_id : str | None
        The ID of the piping network segment being constructed. Set during compositional pass.
    pn_segment : piping.PipingNetworkSegment | None
        The PipingNetworkSegment object being constructed. Set during compositional pass.
    pns_elements : list | None
        The elements of the piping network segment being constructed. Set during compositional pass.
    from_id : str | None
        The ID of the connection point from which the segment starts. Set during compositional pass.
    to_id : str | None
        The ID of the connection point at which the segment ends. Set during compositional pass.
    from_node_index : int | None
        The index of the node in from_id item from which the segment starts. Set during
        compositional pass.
    to_node_index : int | None
        The index of the node in to_id item at which the segment ends. Set during
        compositional pass.
    main_inflow_nodes : dict[str, piping.PipingNode]
        A dictionary mapping component IDs to their main inflow nodes. Set during compositional
        pass.
    main_outflow_nodes : dict[str, piping.PipingNode]
        A dictionary mapping component IDs to their main outflow nodes. Set during compositional
        pass.
    """

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        item_parsers: list[
            PipingComponentParser | PipeOffPageConnectorParser | PropertyBreakParser
        ],
        center_line_parsers: list[CenterLineParser],
        ordered_element_parsers: list[
            PipingComponentParser
            | PipeOffPageConnectorParser
            | PropertyBreakParser
            | CenterLineParser
        ],
        association_parsers: list[AssociationParser],
        generic_attribute_parser: GenericAttributeParser,
        symbol_parsers: list[SymbolParser],
    ) -> None:
        """Initialize the PipingNetworkSegmentParser with the XML element and context.

        Sets the submodules for generic attributes, piping components, and connection points. Makes
        sure that the ordered_element_parsers contains all and only item_parsers and
        center_line_parsers, and raises an internal parser error if not. Initializes all further
        attributes that are needed for the parsing process.

        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        element : ET.Element
            The XML element containing the piping network segment to be parsed.
        item_parsers : list[PipingComponentParser |
                            PipeOffPageConnectorParser |
                            PropertyBreakParser]
            A list of parsers for the items in the piping network segment.
        center_line_parsers : list[CenterLineParser]
            A list of parsers for the center lines in the piping network segment.
        ordered_element_parsers : list[PipingComponentParser |
                                       PipeOffPageConnectorParser |
                                       PropertyBreakParser |
                                       CenterLineParser]
            A list of parsers for the ordered elements in the piping network segment.
        association_parsers : list[AssociationParser]
            A list of parsers for the associations in the piping network segment.
        generic_attribute_parser : GenericAttributeParser
            A parser for the generic attributes of the piping network segment.
        symbol_parsers : list[SymbolParser]
            A list of parsers for the symbols in the piping network segment.
        """
        super().__init__(context)
        self.element = element
        self.pns_id = None
        self.pn_segment = None
        self.segment_dwg = None

        # Consistency check to make sure that the ordered_element_parsers contains all and only
        # item_parsers and center_line_parsers. Raise an exception if not (this is a parser
        # error, not a DEXPI error).
        expected_parsers = set(item_parsers + center_line_parsers)
        actual_parsers = set(ordered_element_parsers)

        if expected_parsers != actual_parsers:
            raise InternalParserError(
                "Ordered element parsers must contain all and only item parsers and "
                "center line parsers."
            )

        # Set item parsers
        self.item_parsers = item_parsers

        # Set center line parsers
        self.center_line_parsers = center_line_parsers

        # Set and register ordered element parser reference
        self.ordered_element_parsers = ordered_element_parsers
        self.register_submodule_list(ordered_element_parsers)

        # Set and register association parsers
        self.association_parsers = association_parsers
        self.register_submodule_list(association_parsers)

        # Set and register generic attribute parser
        self.generic_attribute_parser = generic_attribute_parser
        self.register_submodule(generic_attribute_parser)

        # Set and register symbol parsers
        self.symbol_parsers = symbol_parsers
        self.register_submodule_list(symbol_parsers)

        # Initialize attribute for the PipingNetworkSegment elements. This will be set to a list in
        # the compositional pass. None means not parsed yet.
        self.pns_elements = None

        # Initialize attributes for connection points. Directly extract the connection points to
        # avoid ambiguity of None meaning not parsed or not found. This way, None always means not
        # found.
        self.from_id = None
        self.to_id = None
        self.from_node_index = None
        self.to_node_index = None
        self._extract_connections()

        # Keep track of all item main inflow and main outflow nodes.
        self.main_inflow_nodes = {}
        self.main_outflow_nodes = {}

    @redirect_errors_to_registry
    def compositional_pass(self) -> piping.PipingNetworkSegment | None:
        """Parse the PipingNetworkSegment in the compositional pass.

        Compose all components, connections and generic attributes and keep track of connection
        points, main inflow and outflow nodes. Create an instance of the PipingNetworkSegment class
        with the composed attributes and register it. No internal or external sources or targets are
        defined. This happens in the reference pass.

        Returns
        -------
        piping.PipingNetworkSegment | None
            An instance of the PipingNetworkSegment class created from the parsed attributes and
            components, or None if an error occurs during parsing.
        """

        # Extract pns id
        self.pns_id = self.element.get("ID")
        if self.pns_id is None:
            self.register_error(*ErrorTemplates.id_not_found("PipingNetworkSegment"))
            return None

        # Compose all piping components and connections
        self.pns_elements = []
        items = []
        connections = []
        last_was_item = False
        for element_parser in self.ordered_element_parsers:
            component_element = element_parser.compositional_pass()

            # Infer a direct piping connection if the last parser was an item parser (Comparison
            # done on parser object, since an internal error may return None for the parsed
            # object)
            if element_parser in self.item_parsers and last_was_item:
                direct_connection = piping.DirectPipingConnection()
                self.pns_elements.append(direct_connection)
                connections.append(direct_connection)

            if element_parser in self.item_parsers:
                last_was_item = True
                items.append(component_element)
                # If the element is not None, register main inflow and outflow nodes
                if component_element is not None:
                    self.main_inflow_nodes[component_element.id] = (
                        element_parser.get_main_inflow_node()
                    )
                    self.main_outflow_nodes[component_element.id] = (
                        element_parser.get_main_outflow_node()
                    )

            elif element_parser in self.center_line_parsers:
                last_was_item = False
                connections.append(component_element)
            else:
                msg = f"Unknown component parser type: {element_parser}. Internal error in "
                "Parser."
                exception = InternalParserError(msg)
                self.register_error(msg, level=ErrorLevels.CRITICAL, exception=exception)
                continue

            self.pns_elements.append(component_element)

        # Compose associations
        for association_parser in self.association_parsers:
            association_parser.compositional_pass()

        # Compose generic attributes
        generic_attrs = self.generic_attribute_parser.compositional_pass(
            piping.PipingNetworkSegment
        )

        # Create the PipingNetworkSegment with the composed attributes. No internal or external
        # sources or targets are defined yet. This happens in the reference pass.
        kwargs = generic_attrs.copy()
        kwargs["items"] = filter_none(items)
        kwargs["connections"] = filter_none(connections)

        new_segment = piping.PipingNetworkSegment(proteusId=self.pns_id, **kwargs)

        # Register the PipingNetworkSegment object
        self.register_object(self.pns_id, new_segment)

        # Set the pn_segment attribute to the new segment
        self.pn_segment = new_segment

        return new_segment

    @redirect_errors_to_registry
    def reference_pass(self) -> None:
        """Perform a reference pass over the PipingNetworkSegment.

        This method calls the reference pass on all component parsers. Then, it checks if the
        segment is reversed and reverses the order of all items and connections if so. Then, it
        creates internal and external source and target connections, respectively, according to the
        DEXPI convention.
        """
        # Call super to call reference pass on all submodules
        super().reference_pass()

        # Skip pass if the reference object or ID is not available due to previous error
        if self.pns_id is None or self.pn_segment is None:
            self.register_error(*ErrorTemplates.skip_pass("reference", "PipingNetworkSegment"))
            return

        # Check if the segment is reversed. If so, reverse the order of all items and connections
        if self._infer_is_reversed():
            self.pn_segment.items.reverse()
            self.pn_segment.connections.reverse()

            self.item_parsers.reverse()
            self.center_line_parsers.reverse()
            self.ordered_element_parsers.reverse()
            self.pns_elements.reverse()

        # After potential reversal, append missing direct piping connections to start and end if
        # required by the external connection points.
        self._infer_direct_connections_at_ends()

        # Go through all elements and assign sources and targets.
        for i, element in enumerate(self.pns_elements):
            if isinstance(element, piping.PipingConnection):
                # Assign source
                if i > 0 and isinstance(self.pns_elements[i - 1], piping.PipingNetworkSegmentItem):
                    source_item = self.pns_elements[i - 1]
                    element.sourceItem = source_item
                    source_node = self.main_outflow_nodes.get(source_item.id)
                    element.sourceNode = source_node

                # Assign target
                if i < len(self.pns_elements) - 1 and isinstance(
                    self.pns_elements[i + 1], piping.PipingNetworkSegmentItem
                ):
                    target_item = self.pns_elements[i + 1]
                    element.targetItem = target_item
                    target_node = self.main_inflow_nodes.get(target_item.id)
                    element.targetNode = target_node

        # Set the external segment source and target.
        if self.from_id is not None:
            self.pn_segment.sourceItem = self.get_object_from_registry(self.from_id)
            if self.from_node_index is not None:
                self.pn_segment.sourceNode = self.pn_segment.sourceItem.nodes[self.from_node_index]

            # If the first element is a piping connection, set its source item and node to the
            # source item and node of the segment.
            first_element = self.pns_elements[0]
            if isinstance(first_element, piping.PipingConnection):
                first_element.sourceItem = self.pn_segment.sourceItem
                first_element.sourceNode = self.pn_segment.sourceNode

        # If no external source is defined and the first element is an item, the first item is
        # inferred as source to produce a valid segment. If the item has a main inflow node, it is
        # used as source node.
        if self.pn_segment.sourceItem is None and self.ordered_element_parsers:
            if self.ordered_element_parsers[0] in self.item_parsers:
                source_item = self.pns_elements[0]
                self.pn_segment.sourceItem = source_item
                self.pn_segment.sourceNode = self.main_inflow_nodes.get(source_item.id)

        # Set the external segment target same as source above.
        if self.to_id is not None:
            self.pn_segment.targetItem = self.get_object_from_registry(self.to_id)
            if self.to_node_index is not None:
                self.pn_segment.targetNode = self.pn_segment.targetItem.nodes[self.to_node_index]

            # If the last element is a piping connection, set its target item and node to the
            # target item and node of the segment.
            last_element = self.pns_elements[-1]
            if isinstance(last_element, piping.PipingConnection):
                last_element.targetItem = self.pn_segment.targetItem
                last_element.targetNode = self.pn_segment.targetNode

        if self.pn_segment.targetItem is None and self.ordered_element_parsers:
            if self.ordered_element_parsers[-1] in self.item_parsers:
                target_item = self.pns_elements[-1]
                self.pn_segment.targetItem = target_item
                self.pn_segment.targetNode = self.main_outflow_nodes.get(target_item.id)

    @redirect_errors_to_registry
    def control_pass(self) -> None:
        """Perform a control pass over the segment's associations.

        This is to catch the 'is location of' associations as sensing locations that are missed in
        the reference pass."""
        # Call super.control_pass() to call control pass on all submodules
        super().control_pass()

        # Skip pass if the reference object or ID is not available due to previous error
        if not (self.pn_segment and self.pns_id):
            self.register_error(*ErrorTemplates.skip_pass("control", "PipingNetworkSegment"))
            return

        # Otherwise, proceed with control pass. Check if associations have been made correctly.
        for association_parser in self.association_parsers:
            if not association_parser.is_valid():
                # Log error and skip association
                self.register_error(
                    association_parser.get_error_message(),
                    level=ErrorLevels.ERROR,
                )
                continue

            elif association_parser.get_type() != "is the location of":
                # Not permitted for pn segments, add warning
                self.register_error(
                    f"Association of type {association_parser.get_type()} is not "
                    "permitted for PipingNetworkSegments. Association skipped.",
                    level=ErrorLevels.WARNING,
                )

            else:
                associated_object = association_parser.get_referenced_item()
                association_id = association_parser.get_id()
                if not is_associated_with(self.pn_segment, associated_object):
                    # Log warning and try to add association in control pass
                    self.register_error(
                        *ErrorTemplates.no_assoc_ctrl("PipingNetworkSegment", association_id)
                    )
                    try:
                        fld = add_by_inferring_type(self.pn_segment, associated_object)
                        # Log an info error if the association was added in control pass
                        self.register_error(
                            *ErrorTemplates.assoc_added_ctrl(
                                "PipingNetworkSegment", association_id, fld
                            )
                        )
                    except ValueError as e:
                        # If the association cannot be added, log an error
                        self.register_error(
                            *ErrorTemplates.assoc_not_added_ctrl(
                                "PipingNetworkSegment", association_id
                            ),
                            exception=e,
                        )

    @redirect_errors_to_registry
    def drawing_pass(self) -> graphics.RepresentationGroup | None:
        """Perform a drawing pass over the PipingNetworkSegment.

        This method calls the drawing pass on all submodules and collects their graphical
        representations into a RepresentationGroup.

        Returns
        -------
        graphics.RepresentationGroup | None
            A RepresentationGroup containing all graphical representations from submodules, or
            None if an error occurs during the drawing pass.
        """

        # Collect graphical representations from all submodules
        if not (self.pn_segment and self.pns_id):
            self.register_error(*ErrorTemplates.skip_pass("drawing", "PipingNetworkSystem"))
            return

        # Partial groups and node_positions list for representation group
        groups = []
        node_positions = []

        self.segment_dwg = graphics.RepresentationGroup(
            represents=self.pn_segment, groups=groups, nodePositions=node_positions
        )

        items_dwg = [parser.drawing_pass() for parser in self.item_parsers]

        for item_dwg in items_dwg:
            if item_dwg is not None:
                self.segment_dwg.groups.append(item_dwg)

        symbols_dwg = [parser.drawing_pass() for parser in self.symbol_parsers]
        for symbol_dwg in symbols_dwg:
            if symbol_dwg is not None:
                self.segment_dwg.groups.append(symbol_dwg)

        center_line_dwg = [parser.drawing_pass() for parser in self.center_line_parsers]
        for cl_dwg in center_line_dwg:
            if cl_dwg is not None:
                center_line_dwg = graphics.RepresentationGroup(
                    represents=self.pn_segment,
                    groups=[cl_dwg],
                    nodePositions=[],
                )
                self.segment_dwg.groups.append(center_line_dwg)

        return self.segment_dwg

    def drawing_reference_pass(self) -> None:
        """Perform a drawing reference pass over the PipingNetworkSegment."""

        connection_element = self.element.find("Connection")
        if connection_element is not None:
            from_id = connection_element.get("FromID")
            to_id = connection_element.get("ToID")
            from_node = connection_element.get("FromNode")
            to_node = connection_element.get("ToNode")

            if from_id and to_id and from_node and to_node:
                # Find Source and Target object from ObjectRegistry
                source_object = self.get_object_from_registry(from_id + "_cp_node_positions")
                target_object = self.get_object_from_registry(to_id + "_cp_node_positions")

                if source_object is None:
                    self.register_error(
                        f"Source node with ID {from_id} not found in registry.",
                        level=ErrorLevels.WARNING,
                    )
                    return
                if target_object is None:
                    self.register_error(
                        f"Target node with ID {to_id} not found in registry.",
                        level=ErrorLevels.WARNING,
                    )
                    return

                if source_object and target_object:
                    # Get values as list and access by index (1-based to 0-based conversion)
                    source_values = list(source_object.values())
                    target_values = list(target_object.values())
                    
                    # Check if the index is within bounds
                    from_node_idx = int(from_node) - 1
                    to_node_idx = int(to_node) - 1
                    
                    if from_node_idx < 0 or from_node_idx >= len(source_values):
                        self.register_error(
                            f"Source node index {from_node} out of range for object {from_id} (has {len(source_values)} nodes).",
                            level=ErrorLevels.WARNING,
                        )
                        return
                    
                    if to_node_idx < 0 or to_node_idx >= len(target_values):
                        self.register_error(
                            f"Target node index {to_node} out of range for object {to_id} (has {len(target_values)} nodes).",
                            level=ErrorLevels.WARNING,
                        )
                        return
                    
                    source_node = source_values[from_node_idx]
                    target_node = target_values[to_node_idx]

                    if source_node is not None and target_node is not None:
                        # Add node positions to the information flow drawing
                        if self.segment_dwg is not None:
                            # Find all connector lines in the drawing using helper method
                            connector_lines: list[graphics.ConnectorLine] = []

                            for group in self.segment_dwg.groups:
                                connector_lines.extend(self._find_connector_lines(group))

                            if connector_lines:
                                num_lines = len(connector_lines)
                                # Handle first connector line
                                connector_lines[0].source = source_node

                                if num_lines == 1:
                                    # If only one line, target connects directly to target_node
                                    connector_lines[0].target = target_node

                                else:
                                    # First line's target is its last inner point (if it exists and differs from source)
                                    last_point = (
                                        connector_lines[0].innerPoints[-1]
                                        if connector_lines[0].innerPoints
                                        else None
                                    )
                                    if last_point and last_point != source_node.position:
                                        registered_node = self._get_node_position(last_point)
                                        connector_lines[0].target = registered_node
                                    else:
                                        connector_lines[0].target = None

                                # Handle middle connector lines (if any)
                                for i in range(1, num_lines - 1):
                                    prev_line = connector_lines[i - 1]
                                    curr_line = connector_lines[i]
                                    # Source is previous line's last inner point
                                    last_point_prev = (
                                        prev_line.innerPoints[-1] if prev_line.innerPoints else None
                                    )
                                    if last_point_prev:
                                        registered_node = self._get_node_position(last_point_prev)
                                        curr_line.source = registered_node
                                    else:
                                        curr_line.source = None

                                    # Target is current line's last inner point
                                    last_point_curr = (
                                        curr_line.innerPoints[-1] if curr_line.innerPoints else None
                                    )
                                    if last_point_curr and (
                                        not curr_line.source
                                        or last_point_curr != curr_line.source.position
                                    ):
                                        registered_node = self._get_node_position(last_point_curr)
                                        curr_line.target = registered_node
                                    else:
                                        curr_line.target = None

                                # Handle last connector line (if more than one line)
                                if num_lines > 1:
                                    prev_line = connector_lines[-2]
                                    last_line = connector_lines[-1]
                                    # Source is previous line's last inner point
                                    last_point = (
                                        prev_line.innerPoints[-1] if prev_line.innerPoints else None
                                    )
                                    if last_point:
                                        registered_node = self._get_node_position(last_point)
                                        last_line.source = registered_node
                                    else:
                                        last_line.source = None
                                    last_line.target = target_node  # Already a NodePosition

                                # Register an informational message
                                if num_lines > 1:
                                    self.register_error(
                                        f"Found {num_lines} connector lines in segment. Connecting them sequentially using known connection and inner points.",
                                        level=ErrorLevels.INFO,
                                        proteus_id=self.pns_id,
                                    )
                else:
                    self.register_error(
                        f"Could not find node positions for connection: FromNode={from_node}, ToNode={to_node}",
                        level=ErrorLevels.WARNING,
                    )

    def _find_connector_lines(self, group) -> list[graphics.ConnectorLine]:
        """Find all connector lines recursively in a given group.

        This helper method searches through a group and its subgroups to find all
        connector line elements.

        Parameters
        ----------
        group : graphics.Static | graphics.RepresentationGroup
            The group to search for connector lines

        Returns
        -------
        list[graphics.ConnectorLine]
            A list of found connector line elements
        """
        connector_lines = []
        if isinstance(group, graphics.Static):
            for element in group.elements:
                if isinstance(element, graphics.ConnectorLine):
                    connector_lines.append(element)
        elif isinstance(group, graphics.RepresentationGroup):
            for subgroup in group.groups:
                connector_lines.extend(self._find_connector_lines(subgroup))
        return connector_lines

    def _get_node_position(self, node_pos: graphics.Point) -> graphics.NodePosition | None:
        """Find and return a matching NodePosition from the object registry.

        This method searches for a NodePosition in the registry that matches the given
        position coordinates.

        Parameters
        ----------
        node_pos : graphics.Point
            The point coordinates to find matching NodePosition for in the registry

        Returns
        -------
        graphics.NodePosition | None
            The matching NodePosition object if found in the registry, None otherwise
        """
        # Get all objects with '_cp_node_positions' in their key from registry
        node_positions = {}
        for key, obj in self.context.object_registry.objects.items():
            if "_cp_node_positions" in key and obj is not None:
                node_positions.update(obj)

        # Iterate through all node positions and check their points
        for position_obj in node_positions.values():
            if (
                hasattr(position_obj, "position")
                and hasattr(position_obj.position, "x")
                and hasattr(position_obj.position, "y")
            ):
                if position_obj.position.x == node_pos.x and position_obj.position.y == node_pos.y:
                    return position_obj

        return None

    def _extract_connections(self) -> None:
        """Extract connection relationships from the PipingNetworkSegment element.

        This method retrieves the connections from the XML element and sets the attributes
        for from_id, to_id, from_node_index, and to_node_index. It also registers errors if
        multiple connection elements or attributes are found.
        """
        try:
            attrs = {
                "FromID": None,
                "ToID": None,
                "FromNode": None,
                "ToNode": None,
            }

            # Find all ConnectionPoints in the PipingNetworkSegment element
            connection_points = self.element.findall("Connection")

            # If more than one connection point is found, log a warning. This is not expected
            # directly
            if len(connection_points) > 1:
                self.register_error(
                    "Multiple ConnectionPoints found in PipingNetworkSegment. "
                    "Will only parse the first of each element encountered",
                    level=ErrorLevels.WARNING,
                )

            # Iterate through the connection points and extract attributes. If multiple attributes
            # are found, log an error and use the first encountered value.
            for connection_point in connection_points:
                for attr_name in ["FromID", "ToID", "FromNode", "ToNode"]:
                    if connection_point.get(attr_name) is not None:
                        if attrs[attr_name] is not None:
                            self.register_error(
                                f"Multiple {attr_name} attributes found in ConnectionPoints. "
                                "Will only parse the first of each element encountered.",
                                level=ErrorLevels.ERROR,
                            )
                        else:
                            attrs[attr_name] = connection_point.get(attr_name)

            # Set attributes
            self.from_id = attrs["FromID"]
            self.to_id = attrs["ToID"]
            if attrs["FromNode"] is None:
                self.from_node_index = None
            else:
                try:
                    self.from_node_index = int(attrs["FromNode"])
                except (ValueError, TypeError):
                    self.register_error(
                        f"Invalid FromNode index: {attrs['FromNode']}",
                        level=ErrorLevels.ERROR,
                    )
                self.from_node_index = None
            if attrs["ToNode"] is None:
                self.to_node_index = None
            else:
                try:
                    self.to_node_index = int(attrs["ToNode"])
                except (ValueError, TypeError):
                    self.register_error(
                        f"Invalid ToNode index: {attrs['ToNode']}",
                        level=ErrorLevels.ERROR,
                    )
                self.to_node_index = None

        except Exception as e:
            self.register_error(
                f"Error extracting connection points: {e}",
                level=ErrorLevels.ERROR,
                exception=e,
            )

    def _infer_is_reversed(
        self,
    ) -> bool:
        """Infer if the piping network segment is reversed based on connection points.

        This method checks if the last element in the pns_elements is the source or if the first
        element is the target. If either condition is true, it indicates that the piping network
        segment is reversed. Method should be called after compositional pass. Does not handle
        errors.

        Returns
        -------
        bool
            True if the piping network segment is reversed, False otherwise.
        """
        # If there are no pns_elements, return False
        if not self.pns_elements:
            return False

        source_obj = self.get_object_from_registry(self.from_id)
        target_obj = self.get_object_from_registry(self.to_id)

        # If the last element is the source or the first element is the target, it is reversed
        return source_obj is self.pns_elements[-1] or target_obj is self.pns_elements[0]

    def _infer_direct_connections_at_ends(self) -> None:
        """Checks if direct piping connections are needed at the start or end of the segment.

        This method infers if a direct piping connection is needed at the start or the end of the
        segment. This is needed if an external source/target is defined, but the first/last element
        is an item, or the segment is empty completely. In this case, a direct piping connection is
        added to the start/end.

        This method needs to be called AFTER the potential reversal of the segment, since it assumes
        that the first element is the start and the last element is the end of the segment. It
        needs to be called BEFORE establishing the internal and external sources and targets of the
        connections and the segment itself, since it does not take care of that for the potentially
        created connections."""

        source_obj = self.get_object_from_registry(self.from_id)
        first_element = self.pns_elements[0] if self.pns_elements else None

        if source_obj is not None and source_obj is not first_element:
            if isinstance(first_element, piping.PipingNetworkSegmentItem) or first_element is None:
                direct_connection = piping.DirectPipingConnection()
                self.pns_elements.insert(0, direct_connection)
                self.pn_segment.connections.insert(0, direct_connection)

        target_obj = self.get_object_from_registry(self.to_id)
        last_element = self.pns_elements[-1] if self.pns_elements else None

        if target_obj is not None and target_obj is not last_element:
            if isinstance(last_element, piping.PipingNetworkSegmentItem) or last_element is None:
                direct_connection = piping.DirectPipingConnection()
                self.pns_elements.append(direct_connection)
                self.pn_segment.connections.append(direct_connection)


class PipingNetworkSystemParser(ParserModule):
    """Parser for PipingNetworkSystem elements in the DEXPI model.

    Extracts the PipingNetworkSystem from the XML element. Composes all segments and
    generic attributes in the compositional pass and returns an instance of PipingNetworkSystem.
    In the reference pass, it checks if there are any unconnected segments and infers an implicit
    connection between them if so, according to the DEXPI convention. No control pass is required.

    Attributes
    ----------
    context : ModuleContext
        The context containing the ID-, and element stack, error-, and object registry.
    element : ET.Element
        The XML element containing the piping network system to be parsed.
    segment_parsers : list[PipingNetworkSegmentParser]
        A list of parsers for the piping network segments in the system.
    generic_attribute_parser : GenericAttributeParser
        A parser for the generic attributes of the piping network system.
    system_id : str | None
        The ID of the piping network system being constructed. Set during compositional pass.
    the_system : piping.PipingNetworkSystem | None
        The PipingNetworkSystem object being constructed. Set during compositional pass.
    segment_ids : list[str]
        A list of IDs of the segments in the piping network system. Set during compositional pass.
    """

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        segment_parsers: list[PipingNetworkSegmentParser],
        generic_attribute_parser: GenericAttributeParser,
        label_parsers: list[LabelParser],
    ) -> None:
        """Initialize the PipingNetworkSystemParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The module context containing the ID-, and element stack, error-, and object registry.
        element : ET.Element
            The XML element containing the piping network system to be parsed.
        segment_parsers : list[PipingNetworkSegmentParser]
            A list of parsers for the piping network segments in the system.
        generic_attribute_parser : GenericAttributeParser
            A parser for the generic attributes of the piping network system.
        label_parsers : list[LabelParser]
            A list of parsers for the labels in the piping network system.
        """
        super().__init__(context)
        self.element = element
        self.system_id = None
        self.the_system = None
        self.system_dwg = None

        self.segment_ids = []

        # Set and register segment parsers
        self.segment_parsers = segment_parsers
        self.register_submodule_list(segment_parsers)

        # Initialize parsers for generic attributes
        self.gen_attr_parser = generic_attribute_parser
        self.register_submodule(generic_attribute_parser)

        # Initialize parsers for labels
        self.label_parsers = label_parsers
        self.register_submodule_list(label_parsers)

    @redirect_errors_to_registry
    def compositional_pass(self):
        """Parse the PipingNetworkSystem in the compositional pass.

        Composes all segments and generic attributes and creates a PipingNetworkSystem with the
        parsed data. Registers the system object in the module context. Also logs any errors that
        occur during compositional parsing.

        Returns
        -------
        piping.PipingNetworkSystem | None
            An instance of the PipingNetworkSystem class created from the parsed attributes, or
            None if an error occurred during parsing.
        """
        # Extract pns id
        self.system_id = self.element.get("ID")
        if self.system_id is None:
            self.register_error(*ErrorTemplates.id_not_found("PipingNetworkSystem"))
            return None

        # Compose all piping network segments
        segments = []
        for segment_parser in self.segment_parsers:
            segment = segment_parser.compositional_pass()
            self.segment_ids.append(segment_parser.pns_id)
            if segment is not None:
                segments.append(segment)

        # Compose generic attributes
        generic_attrs = self.gen_attr_parser.compositional_pass(piping.PipingNetworkSystem)

        kwargs = generic_attrs.copy()
        kwargs["segments"] = segments

        self.the_system = piping.PipingNetworkSystem(proteusId=self.system_id, **kwargs)

        # Register the PipingNetworkSystem object
        self.register_object(self.element.get("ID"), self.the_system)

        return self.the_system

    @redirect_errors_to_registry
    def reference_pass(self) -> None:
        """Perform a reference pass over the PipingNetworkSystem.

        This method calls the reference pass on all submodules. Checks if there are any unconnected
        segments. If there are, a connection is inferred between its neighboring segments.
        """
        # Call super to call reference pass on all submodules
        super().reference_pass()

        # Skip pass if the reference object or ID is not available due to previous error
        if self.the_system is None or self.system_id is None:
            self.register_error(*ErrorTemplates.skip_pass("reference", "PipingNetworkSystem"))
            return

        # Check if connections need to be inferred between the segments
        for i, segment_id in enumerate(self.segment_ids):
            if segment_id is None:
                continue

            segment = self.get_object_from_registry(segment_id)
            has_no_source = segment.sourceItem is None
            has_no_target = segment.targetItem is None

            # Attempt to infer a connection if the segment is free and unconnected
            if i > 0 and has_no_source:
                # Check if the previous segment is connected internally, in which case connection
                # can be inferred
                prev_segment_id = self.segment_ids[i - 1]
                if prev_segment_id is not None:
                    prev_segment = self.get_object_from_registry(prev_segment_id)
                    if (
                        prev_segment
                        and prev_segment.targetItem in prev_segment.items
                        and prev_segment.targetItem is not None
                    ):
                        # Get connector node index:
                        connector_node_index = (
                            prev_segment.targetItem.nodes.index(prev_segment.targetNode)
                            if prev_segment.targetNode
                            else None
                        )

                        ptk.connect_piping_network_segment(
                            segment,
                            prev_segment.targetItem,
                            connector_node_index=connector_node_index,
                            as_source=True,
                        )

                        # Log info about the inferred connection
                        self.register_error(
                            f"Inferred connection between segment {i} and previous segment.",
                            level=ErrorLevels.INFO,
                        )

            if i < len(self.the_system.segments) - 1 and has_no_target:
                # Check if the next segment is connected internally, in which case connection
                # can be inferred
                next_segment_id = self.segment_ids[i + 1]
                if next_segment_id is not None:
                    next_segment = self.get_object_from_registry(next_segment_id)
                    if (
                        next_segment
                        and next_segment.sourceItem in next_segment.items
                        and next_segment.sourceItem is not None
                    ):
                        # Get connector node index:
                        connector_node_index = (
                            next_segment.sourceItem.nodes.index(next_segment.sourceNode)
                            if next_segment.sourceNode
                            else None
                        )

                        ptk.connect_piping_network_segment(
                            segment,
                            next_segment.sourceItem,
                            connector_node_index=connector_node_index,
                            as_source=False,
                        )

                        # Log info about the inferred connection
                        self.register_error(
                            f"Inferred connection between segment {i} and next segment.",
                            level=ErrorLevels.INFO,
                            proteus_id=self.system_id,
                        )

    @redirect_errors_to_registry
    def drawing_pass(self) -> graphics.RepresentationGroup | None:
        """Perform a drawing pass over the pns labels."""

        # Skip pass if the reference object or ID is not available due to previous error
        if not (self.the_system and self.system_id):
            self.register_error(*ErrorTemplates.skip_pass("drawing", "PipingNetworkSystem"))
            return

        # Partial groups and node_positions list for representation group
        groups = []
        node_positions = []

        # Process labels
        labels = [parser.drawing_pass() for parser in self.label_parsers]
        labels = filter_none(labels)
        for label in labels:
            groups.append(label)

        self.system_dwg = graphics.RepresentationGroup(
            represents=self.the_system, groups=groups, nodePositions=node_positions
        )

        segements_dwg = [parser.drawing_pass() for parser in self.segment_parsers]
        segements_dwg = filter_none(segements_dwg)
        for segment_dwg in segements_dwg:
            self.system_dwg.groups.append(segment_dwg)

        return self.system_dwg


### INSTRUMENTATION PARSERS ###
class ActuatingSystemComponentParser(ParserModule):
    """Parser for ActuatingSystemComponent elements in the DEXPI model.

    Parsing ActuatingSystemComponent elements into corresponding pyDEXPI objects. In the
    compositional pass, determines the correct pyDEXPI class based on the ComponentClass attribute.
    Modeled as CustomActuatingSystemComponent if the class name is not part of the pyDEXPI
    instrumentation package. Composes all associations and generic attributes, and creates the
    component object. Establishes associations of type "refers to" (if the class is an
    OperatedValveReference). No control pass is required.

    Attributes
    ----------
    context : ModuleContext
        The context containing the ID-, and element stack, error-, and object registry.
    element : ET.Element
        The XML element containing the ActuatingSystemComponent to be parsed.
    association_parsers : list[AssociationParser]
        A list of parsers for the associations related to the ActuatingSystemComponent.
    generic_attribute_parser : GenericAttributeParser
        A parser for the generic attributes of the ActuatingSystemComponent.
    component_id : str | None
        The ID of the ActuatingSystemComponent being constructed. Set during compositional pass.
    component : OperatedValveReference | ControlledActuator | Positioner |
                CustomActuatingSystemComponent | None
        The ActuatingSystemComponent object being constructed. Set during compositional pass.
    """

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        association_parsers: list[AssociationParser],
        generic_attribute_parser: GenericAttributeParser,
        shape_usage_parser: ShapeUsageParser,
        label_parsers: list[LabelParser],
        connection_point_parsers: list[ConnectionPointParser],
    ) -> None:
        """Initialize the ActuatingSystemComponentParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The module context providing access to the ID stack and error registry.
        element : ET.Element
            The XML element containing the ActuatingSystemComponent to be parsed.
        association_parsers : list[AssociationParser]
            A list of parsers for the associations related to the ActuatingSystemComponent.
        generic_attribute_parser : GenericAttributeParser
            A parser for the generic attributes of the ActuatingSystemComponent.
        shape_usage_parser : ShapeUsageParser
            A parser for the shape usage of the ActuatingSystemComponent.
        label_parsers : list[LabelParser]
            A list of parsers for the labels of the ActuatingSystemComponent.
        connection_point_parsers : list[ConnectionPointParser]
            A list of parsers for the connection points of the ActuatingSystemComponent.
        """
        super().__init__(context)
        self.element = element
        self.component_id = None
        self.component = None
        self.as_component_dwg = None

        # Set and register association parsers
        self.association_parsers = association_parsers
        self.register_submodule_list(association_parsers)

        # Set and register generic attribute parser
        self.generic_attribute_parser = generic_attribute_parser
        self.register_submodule(generic_attribute_parser)

        # Set and register shape usage parser
        self.shape_usage_parser = shape_usage_parser
        # There is a potential of actuating system components not having a shape usage
        if shape_usage_parser is not None:
            self.register_submodule(shape_usage_parser)

        # Set and register label parsers
        self.label_parsers = label_parsers
        self.register_submodule_list(label_parsers)

        # Set and register connection point parsers
        self.connection_point_parsers = connection_point_parsers
        self.register_submodule_list(connection_point_parsers)

    def compositional_pass(
        self,
    ) -> (
        instrumentation.OperatedValveReference
        | instrumentation.ControlledActuator
        | instrumentation.Positioner
        | instrumentation.CustomActuatingSystemComponent
        | None
    ):
        """Parse the ActuatingSystemComponent in the compositional pass.

        Retrieves the correct pyDEXPI class based on the ComponentClass attribute, and instantiates
        the component with parsed data.

        Returns
        -------
        OperatedValveReference | ControlledActuator | Positioner | CustomActuatingSystemComponent |
        None
            An instance of the ActuatingSystemComponent class created from the parsed attributes,
            or None if an error occurs during parsing.
        """
        # Extract ID
        self.component_id = self.element.get("ID")
        if self.component_id is None:
            self.register_error(*ErrorTemplates.id_not_found("ActuatingSystemComponent"))
            return None

        kwargs = {}

        # Get component type
        class_name = self.element.get("ComponentClass")

        # If class name not part of instrumentation, treat it as custom equipment
        try:
            MyClass = getattr(instrumentation, class_name)
        except AttributeError:
            MyClass = instrumentation.CustomActuatingSystemComponent
            kwargs["typeName"] = class_name

            # Log a warning that the class name is invalid
            self.register_error(
                f"Invalid class {class_name} for ActuatingSystemComponent. Using "
                f"CustomActuatingSystemComponent instead.",
                level=ErrorLevels.WARNING,
            )

        # Compose associations
        for association_parser in self.association_parsers:
            association_parser.compositional_pass()

        # Compose generic attributes
        generic_attrs = self.generic_attribute_parser.compositional_pass(MyClass)
        kwargs.update(generic_attrs)

        # Make component and register it
        self.component = MyClass(proteusId=self.component_id, **kwargs)

        self.register_object(self.component_id, self.component)
        return self.component

    @redirect_errors_to_registry
    def reference_pass(self) -> None:
        """Perform a reference pass over the ActuatingSystemComponent.

        Establishes associations of type "refers to" if the component is an OperatedValveReference,
        and logs errors if the associations are not valid.
        """
        # Call super to call reference pass on all submodules
        super().reference_pass()

        # Skip pass if the reference object or ID is not available due to previous error
        if self.component is None or self.component_id is None:
            self.register_error(*ErrorTemplates.skip_pass("reference", "ActuatingSystemComponent"))
            return

        # Establish associations of type "refers to" if the component is an OperatedValveReference
        for association_parser in self.association_parsers:
            if not association_parser.is_valid():
                # Log error and skip association
                self.register_error(
                    association_parser.get_error_message(),
                    level=ErrorLevels.ERROR,
                )
                continue

            # Check if the component is valid
            assoc_type = association_parser.get_type()
            if assoc_type == "refers to" and isinstance(
                self.component, instrumentation.OperatedValveReference
            ):
                # If the component is a reference, check if it is valid
                referenced_item = association_parser.get_referenced_item()
                referenced_item_id = association_parser.get_id()
                try:
                    self.component.valve = referenced_item
                except Exception as e:
                    self.register_error(
                        f"Error setting valve attribute to {referenced_item_id} for "
                        f"OperatedValveReference {self.component_id}: {e}",
                        level=ErrorLevels.ERROR,
                        exception=e,
                    )
            else:
                self.register_error(
                    *ErrorTemplates.inval_assoc_type("ActuatingSystemComponent", assoc_type)
                )

    @redirect_errors_to_registry
    def drawing_pass(self) -> graphics.RepresentationGroup | None:
        """Perform a drawing pass over the ActuatingSystemComponent.

        This method calls the drawing pass on all submodules and collects their graphical
        representations into a RepresentationGroup.

        Returns
        -------
        graphics.RepresentationGroup | None
            A RepresentationGroup containing all graphical representations from submodules, or
            None if an error occurs during the drawing pass.
        """

        # Collect graphical representations from all submodules
        if not (self.component and self.component_id):
            self.register_error(*ErrorTemplates.skip_pass("drawing", "ActuatingSystemComponent"))
            return

        # Partial groups and node_positions list for representation group
        groups = []
        node_positions = []

        # Process shape usage
        if self.shape_usage_parser is not None:
            shape_usage = self.shape_usage_parser.drawing_pass()
            if shape_usage is not None:
                static = graphics.Static(elements=[shape_usage])
                groups.append(static)

        # Process labels
        if self.label_parsers:
            labels = [parser.drawing_pass() for parser in self.label_parsers]
            labels = filter_none(labels)
            for label in labels:
                groups.append(label)

        # Process connection points
        connection_points_dict = {}
        if self.connection_point_parsers:
            # Combine all connection points from parsers into a single dictionary
            for parser in self.connection_point_parsers:
                cp_dict = parser.drawing_pass()
                if cp_dict:
                    connection_points_dict.update(cp_dict)

            # Add all node positions to the representation group
            node_positions.extend(connection_points_dict.values())

        self.as_component_dwg = graphics.RepresentationGroup(
            represents=self.component, groups=groups, nodePositions=node_positions
        )

        self.register_object(f"{self.component_id}_cp_node_positions", connection_points_dict)

        return self.as_component_dwg


class ActuatingSystemParser(ParserModule):
    """Parser for ActuatingSystem elements in the DEXPI model.

    Parses ActuatingSystem elements into an instance of the ActuatingSystem class. Collects all
    subcomponents and attributes in compositional pass, and returns created instance of
    ActuatingSystem. No reference or control pass required

    Attributes
    ----------
    context : ModuleContext
        The context in which the parser is operating.
    element : ET.Element
        The XML element containing the ActuatingSystem to be parsed.
    component_parsers : list[ActuatingSystemComponentParser]
        The component parsers for the ActuatingSystem.
    generic_attribute_parser : GenericAttributeParser
        The parser for the generic attributes of the ActuatingSystem.
    actuating_system_id : str | None
        The ID of the ActuatingSystem. Set during compositional pass.
    actuating_system : instrumentation.ActuatingSystem | None
        The parsed ActuatingSystem instance. Set during compositional pass.
    """

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        component_parsers: list[ActuatingSystemComponentParser],
        association_parsers: list[AssociationParser],
        generic_attribute_parser: GenericAttributeParser,
        label_parsers: list[LabelParser],
    ) -> None:
        super().__init__(context)
        self.element = element
        self.actuating_system_id = None
        self.actuating_system = None
        self.actuating_system_dwg = None

        # Set and register component parsers
        self.component_parsers = component_parsers
        self.register_submodule_list(component_parsers)

        # Set and register association parsers
        self.association_parsers = association_parsers
        self.register_submodule_list(association_parsers)

        # Set and register generic attribute parser
        self.generic_attribute_parser = generic_attribute_parser
        self.register_submodule(generic_attribute_parser)

        # Set and register label parsers
        self.label_parsers = label_parsers
        self.register_submodule_list(label_parsers)

    @redirect_errors_to_registry
    def compositional_pass(self) -> instrumentation.ActuatingSystem | None:
        """Parse the ActuatingSystem in the compositional pass.

        Composes all components and generic attributes, and creates an instance of the
        ActuatingSystem class.

        Returns
        -------
        instrumentation.ActuatingSystem | None
            An instance of the ActuatingSystem class created from the parsed attributes, or None
            if an error occurred during parsing.
        """
        # Extract ID. If not found, register an error and return None.
        self.actuating_system_id = self.element.get("ID")
        if self.actuating_system_id is None:
            self.register_error(*ErrorTemplates.id_not_found("ActuatingSystem"))
            return None

        # Compose association parsers
        for association_parser in self.association_parsers:
            association_parser.compositional_pass()

        # Compose all components. Sort them into ControlledActuator, OperatedValveReference,
        # Positioner, and CustomActuatingSystemComponent
        actuator = None
        valve_ref = None
        positioner = None
        custom_components = []
        for component_parser in self.component_parsers:
            component = component_parser.compositional_pass()
            if component:
                if isinstance(component, instrumentation.ControlledActuator):
                    if actuator is not None:
                        self.register_error(
                            "Multiple ControlledActuator components found. Only one is allowed "
                            "in an ActuatingSystem. Keeping the first one encountered.",
                            level=ErrorLevels.ERROR,
                        )
                    else:
                        actuator = component
                elif isinstance(component, instrumentation.OperatedValveReference):
                    if valve_ref is not None:
                        self.register_error(
                            "Multiple OperatedValveReference components found. Only one is "
                            "allowed in an ActuatingSystem. Keeping the first one encountered.",
                            level=ErrorLevels.ERROR,
                        )
                    else:
                        valve_ref = component
                elif isinstance(component, instrumentation.Positioner):
                    if positioner is not None:
                        self.register_error(
                            "Multiple Positioner components found. Only one is allowed "
                            "in an ActuatingSystem. Keeping the first one encountered.",
                            level=ErrorLevels.ERROR,
                        )
                    else:
                        positioner = component
                elif isinstance(component, instrumentation.CustomActuatingSystemComponent):
                    custom_components.append(component)
                else:
                    self.register_error(
                        f"Unexpected component {component} encountered in Actuating system",
                        level=ErrorLevels.ERROR,
                    )

        # Compose generic attributes
        generic_attrs = self.generic_attribute_parser.compositional_pass(
            instrumentation.ActuatingSystem
        )

        # Create the ActuatingSystem object
        self.actuating_system = instrumentation.ActuatingSystem(
            proteusId=self.actuating_system_id,
            controlledActuator=actuator,
            operatedValveReference=valve_ref,
            positioner=positioner,
            customComponents=filter_none(custom_components),
            **generic_attrs,
        )

        # Register and return the ActuatingSystem object
        self.register_object(self.actuating_system_id, self.actuating_system)
        return self.actuating_system

    @redirect_errors_to_registry
    def control_pass(self) -> None:
        """Checks if associations of type "fulfills" to ActuatingFunction objects have been made."""
        # Call super to call control pass on all submodules
        super().control_pass()

        # Skip pass if the reference object or ID is not available due to previous error
        if self.actuating_system_id is None or self.actuating_system is None:
            self.register_error(*ErrorTemplates.skip_pass("control", "ActuatingSystem"))
            return

        # Iterate through all association parsers and check if they are valid. Check if they have
        # been established in reference pass, and if not, try to add them in control pass.
        for association_parser in self.association_parsers:
            if not association_parser.is_valid():
                # Log error and skip association
                self.register_error(
                    association_parser.get_error_message(),
                    level=ErrorLevels.ERROR,
                )
                continue

            assoc_type = association_parser.get_type()
            if assoc_type != "fulfills":
                # Not permitted for ActuatingSystem, add warning
                self.register_error(*ErrorTemplates.inval_assoc_type("ActuatingSystem", assoc_type))
                continue

            else:
                associated_object = association_parser.get_referenced_item()
                association_id = association_parser.get_id()
                if not is_associated_with(self.actuating_system, associated_object):
                    # Log warning and try to add association in control pass
                    self.register_error(
                        *ErrorTemplates.no_assoc_ctrl("ActuatingSystem", association_id)
                    )
                    try:
                        fld = add_by_inferring_type(self.actuating_system, associated_object)
                        # Log an info error if the association was added in control pass
                        self.register_error(
                            *ErrorTemplates.assoc_added_ctrl("ActuatingSystem", association_id, fld)
                        )
                    except ValueError as e:
                        # If the association cannot be added, log an error
                        self.register_error(
                            *ErrorTemplates.assoc_not_added_ctrl("ActuatingSystem", association_id),
                            exception=e,
                        )

    @redirect_errors_to_registry
    def drawing_pass(self) -> graphics.RepresentationGroup | None:
        """Perform a drawing pass over the actuating system labels and components."""

        # Skip pass if the reference object or ID is not available due to previous error
        if not (self.actuating_system and self.actuating_system_id):
            self.register_error(*ErrorTemplates.skip_pass("drawing", "ActuatingSystem"))
            return

        # Partial groups and node_positions list for representation group
        groups = []
        node_positions = []

        # Process labels
        labels = [parser.drawing_pass() for parser in self.label_parsers]
        labels = filter_none(labels)
        for label in labels:
            groups.append(label)

        # generate actuating system dwg
        self.actuating_system_dwg = graphics.RepresentationGroup(
            represents=self.actuating_system, groups=groups, nodePositions=node_positions
        )

        as_components = [parser.drawing_pass() for parser in self.component_parsers]
        for as_component in as_components:
            if as_component is not None:
                self.actuating_system_dwg.groups.append(as_component)

        return self.actuating_system_dwg


class ProcessSignalGeneratingSystemComponentParser(ParserModule):
    """Parser for ProcessSignalGeneratingSystemComponent elements in the DEXPI model.

    Parses ProcessSignalGeneratingSystemComponent elements into an instance of the appropriate
    pyDEXPI class. In the compositional pass, it determines the correct class based on the
    ComponentClass attribute. In the reference pass, it establishes all associations of type
    "refers to" if the component is an InlinePrimaryElementReference. No control pass is required.

    Attributes
    ----------
    context : ModuleContext
        The context containing the ID-, and element stack, error-, and object registry.
    element : ET.Element
        The XML element containing the ProcessSignalGeneratingSystemComponent to be parsed.
    association_parsers : list[AssociationParser]
        A list of parsers for the associations related to the component.
    generic_attribute_parser : GenericAttributeParser
        A parser for the generic attributes of the component.
    component_id : str | None
        The ID of the ProcessSignalGeneratingSystemComponent being constructed. Set during
        compositional pass.
    component : Transmitter | PrimaryElement | CustomProcessSignalGeneratingSystemComponent | None
        The ProcessSignalGeneratingSystemComponent object being constructed. Set during
        compositional pass.
    """

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        association_parsers: list[AssociationParser],
        generic_attribute_parser: GenericAttributeParser,
        shape_usage_parser: ShapeUsageParser,
        label_parsers: list[LabelParser],
    ) -> None:
        """Initialize the ProcessSignalGeneratingSystemComponentParser with the element and context.

        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        element : ET.Element
            The XML element containing the ProcessSignalGeneratingSystemComponent to be parsed.
        association_parsers : list[AssociationParser]
            A list of parsers for the associations related to the component.
        generic_attribute_parser : GenericAttributeParser
            A parser for the generic attributes of the component.
        """
        super().__init__(context)
        self.element = element
        self.component = None
        self.component_id = None
        self.psgsc_dwg = None

        # Set and register association parsers
        self.association_parsers = association_parsers
        self.register_submodule_list(association_parsers)

        # Set and register generic attribute parser
        self.generic_attribute_parser = generic_attribute_parser
        self.register_submodule(generic_attribute_parser)

        # Set and register shape usage parser
        self.shape_usage_parser = shape_usage_parser
        self.register_submodule(shape_usage_parser)

        # Set and register label parsers
        self.label_parsers = label_parsers
        self.register_submodule_list(label_parsers)

    @redirect_errors_to_registry
    def compositional_pass(
        self,
    ) -> (
        instrumentation.Transmitter
        | instrumentation.PrimaryElement
        | instrumentation.CustomProcessSignalGeneratingSystemComponent
        | None
    ):
        """Parse the ProcessSignalGeneratingSystemComponent in compositional pass.

        Retrieves the correct pyDEXPI class based on the ComponentClass attribute, and instantiates
        the component with parsed data. If no valid class is found, it uses
        CustomProcessSignalGeneratingSystemComponent.

        Returns
        -------
        Transmitter | PrimaryElement | CustomProcessSignalGeneratingSystemComponent | None
            The ProcessSignalGeneratingSystemComponent instance created from the parsed attributes,
            or None if an error occurs during parsing.
        """
        # Extract ID. If not found, register an error and return None.
        self.component_id = self.element.get("ID")
        if self.component_id is None:
            self.register_error(*ErrorTemplates.id_not_found("ProcessSignalGeneratingSystem"))
            return None

        kwargs = {}

        # Get component type
        class_name = self.element.get("ComponentClass")

        # If class name not part of instrumentation, treat it as custom equipment
        try:
            MyClass = getattr(instrumentation, class_name)
        except AttributeError:
            MyClass = instrumentation.CustomProcessSignalGeneratingSystemComponent
            kwargs["typeName"] = class_name

            # Log a warning that the class name is invalid
            self.register_error(
                f"Invalid class {class_name} for ProcessSignalGeneratingSystemComponent. Using "
                f"CustomProcessSignalGeneratingSystemComponent instead.",
                level=ErrorLevels.WARNING,
            )

        # Compose associations
        for association_parser in self.association_parsers:
            association_parser.compositional_pass()

        # Compose generic attributes
        generic_attrs = self.generic_attribute_parser.compositional_pass(MyClass)
        kwargs.update(generic_attrs)

        # Make component and register it
        self.component = MyClass(proteusId=self.component_id, **kwargs)

        self.register_object(self.component_id, self.component)
        return self.component

    @redirect_errors_to_registry
    def reference_pass(self) -> None:
        """Perform a reference pass over the ProcessSignalGeneratingSystemComponent.

        Establishes associations of type "refers to" if the component is an
        InlinePrimaryElementReference.
        """
        # Call super to call reference pass on all submodules
        super().reference_pass()

        # Skip pass if the reference object or ID is not available due to previous error
        if self.component is None or self.component_id is None:
            self.register_error(
                *ErrorTemplates.skip_pass("reference", "ProcessSignalGeneratingSystemComponent")
            )
            return

        # Establish associations
        for association_parser in self.association_parsers:
            if not association_parser.is_valid():
                # Log error and skip association
                self.register_error(
                    association_parser.get_error_message(),
                    level=ErrorLevels.ERROR,
                )
                continue

            # Check if the component is valid
            assoc_type = association_parser.get_type()
            if assoc_type == "refers to" and isinstance(
                self.component, instrumentation.InlinePrimaryElementReference
            ):
                # If the component is a reference, check if it is valid
                referenced_item = association_parser.get_referenced_item()
                referenced_item_id = association_parser.get_id()
                try:
                    self.component.inlinePrimaryElement = referenced_item
                except Exception as e:
                    self.register_error(
                        *ErrorTemplates.assoc_adding_error(
                            "ProcessSignalGeneratingSystemComponent", referenced_item_id
                        ),
                        exception=e,
                    )
            else:
                self.register_error(
                    *ErrorTemplates.inval_assoc_type(
                        "ProcessSignalGeneratingSystemComponent", assoc_type
                    )
                )

    @redirect_errors_to_registry
    def drawing_pass(self) -> graphics.RepresentationGroup | None:
        """Perform a drawing pass over the ProcessSignalGeneratingSystemComponent.

        This method calls the drawing pass on all submodules and collects their graphical
        representations into a RepresentationGroup.

        Returns
        -------
        graphics.RepresentationGroup | None
            A RepresentationGroup containing all graphical representations from submodules, or
            None if an error occurs during the drawing pass.
        """

        # Collect graphical representations from all submodules
        if not (self.component and self.component_id):
            self.register_error(
                *ErrorTemplates.skip_pass("drawing", "ProcessSignalGeneratingSystemComponent")
            )
            return

        # Partial groups and node_positions list for representation group
        groups = []
        node_positions = []

        # Process shape usage
        shape_usage = self.shape_usage_parser.drawing_pass()
        if shape_usage is not None:
            static = graphics.Static(elements=[shape_usage])
            groups.append(static)

        # Process labels
        labels = [parser.drawing_pass() for parser in self.label_parsers]
        labels = filter_none(labels)
        for label in labels:
            groups.append(label)

        self.psgsc_dwg = graphics.RepresentationGroup(
            represents=self.component, groups=groups, nodePositions=node_positions
        )

        return self.psgsc_dwg


class ProcessSignalGeneratingSystemParser(ParserModule):
    """Parser for ProcessSignalGeneratingSystem elements in the DEXPI model.

    Parses ProcessSignalGeneratingSystem elements into an instance of the
    ProcessSignalGeneratingSystem class. Collects all subcomponents and attributes in compositional
    pass, and returns created instance of ProcessSignalGeneratingSystem. No reference or control
    pass required.

    Attributes
    ----------
    context : ModuleContext
        The context containing the ID-, and element stack, error-, and object registry.
    element : ET.Element
        The XML element containing the ProcessSignalGeneratingSystem to be parsed.
    component_parsers : list[ProcessSignalGeneratingSystemComponentParser]
        The component parsers for the ProcessSignalGeneratingSystem.
    generic_attribute_parser : GenericAttributeParser
        The parser for the generic attributes of the ProcessSignalGeneratingSystem.
    process_signal_system_id : str | None
        The ID of the ProcessSignalGeneratingSystem. Set during compositional pass.
    process_signal_system : instrumentation.ProcessSignalGeneratingSystem | None
        The parsed ProcessSignalGeneratingSystem instance. Set during compositional pass.
    """

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        component_parsers: list[ProcessSignalGeneratingSystemComponentParser],
        generic_attribute_parser: GenericAttributeParser,
        label_parsers: list[LabelParser],
    ) -> None:
        """Initialize the ProcessSignalGeneratingSystemParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        element : ET.Element
            The XML element containing the ProcessSignalGeneratingSystem to be parsed.
        component_parsers : list[ProcessSignalGeneratingSystemComponentParser]
            A list of parsers for the components in the system.
        generic_attribute_parser : GenericAttributeParser
            A parser for the generic attributes of the system.
        """
        super().__init__(context)
        self.element = element
        self.process_signal_system_id = None
        self.process_signal_system = None
        self.process_signal_system_dwg = None

        # Set and register component parsers
        self.component_parsers = component_parsers
        self.register_submodule_list(component_parsers)

        # Set and register generic attribute parser
        self.generic_attribute_parser = generic_attribute_parser
        self.register_submodule(generic_attribute_parser)

        # Set and register label parsers
        self.label_parsers = label_parsers
        self.register_submodule_list(label_parsers)

    @redirect_errors_to_registry
    def compositional_pass(self) -> instrumentation.ProcessSignalGeneratingSystem | None:
        """Parse the ProcessSignalGeneratingSystem in the compositional pass.

        Composes all components and generic attributes, and creates an instance of the
        ProcessSignalGeneratingSystem class.

        Returns
        -------
        instrumentation.ProcessSignalGeneratingSystem | None
            An instance of the ProcessSignalGeneratingSystem class created from the parsed
            attributes, or None if an error occurred during parsing.
        """
        # Extract ID. If not found, register an error and return None.
        self.process_signal_system_id = self.element.get("ID")
        if self.process_signal_system_id is None:
            self.register_error(*ErrorTemplates.id_not_found("ProcessSignalGeneratingSystem"))
            return None

        # Compose all components. Sort them into Transmitter, PrimaryElement,
        # and CustomProcessSignalGeneratingSystemComponent
        transmitters = []
        primary_elements = []
        custom_components = []

        for component_parser in self.component_parsers:
            component = component_parser.compositional_pass()
            if component:
                if isinstance(component, instrumentation.Transmitter):
                    transmitters.append(component)
                elif isinstance(component, instrumentation.PrimaryElement):
                    primary_elements.append(component)
                elif isinstance(
                    component, instrumentation.CustomProcessSignalGeneratingSystemComponent
                ):
                    custom_components.append(component)
                else:
                    self.register_error(
                        f"Unexpected component {component} encountered in "
                        f"ProcessSignalGeneratingSystem",
                        level=ErrorLevels.ERROR,
                    )

        # Compose generic attributes
        generic_attrs = self.generic_attribute_parser.compositional_pass(
            instrumentation.ProcessSignalGeneratingSystem
        )

        # Create the ProcessSignalGeneratingSystem object
        process_signal_system = instrumentation.ProcessSignalGeneratingSystem(
            proteusId=self.process_signal_system_id,
            transmitters=filter_none(transmitters),
            primaryElements=filter_none(primary_elements),
            customComponents=filter_none(custom_components),
            **generic_attrs,
        )

        # Register and return the ProcessSignalGeneratingSystem object
        self.register_object(self.process_signal_system_id, process_signal_system)
        self.process_signal_system = process_signal_system

        return process_signal_system

    @redirect_errors_to_registry
    def drawing_pass(self) -> graphics.RepresentationGroup | None:
        """Perform a drawing pass over the process signal generating system labels."""

        # Skip pass if the reference object or ID is not available due to previous error
        if not (self.process_signal_system and self.process_signal_system_id):
            self.register_error(
                *ErrorTemplates.skip_pass("drawing", "ProcessSignalGeneratingSystem")
            )
            return

        # Partial groups and node_positions list for representation group
        groups = []
        node_positions = []

        # Process labels
        labels = [parser.drawing_pass() for parser in self.label_parsers]
        labels = filter_none(labels)
        for label in labels:
            groups.append(label)

        # generate process signal generating system dwg
        self.process_signal_system_dwg = graphics.RepresentationGroup(
            represents=self.process_signal_system, groups=groups, nodePositions=node_positions
        )

        psgs_components = [parser.drawing_pass() for parser in self.component_parsers]
        # Add subequipment by inferring type

        for psgs_component in psgs_components:
            if psgs_component is not None:
                self.process_signal_system_dwg.groups.append(psgs_component)

        return self.process_signal_system_dwg


class ActuatingFunctionParser(ParserModule):
    """Parser for ActuatingFunction elements in the DEXPI model.

    Parses ActuatingFunction elements into an instance of the ActuatingFunction class. Collects all
    associations and generic attributes in compositional pass, and returns created instance of
    ActuatingFunction. In the reference pass, it establishes associations of type "is located in"
    as the ActuatingLocation attribute of the ActuatingFunction, and associations of type
    "is fulfilled by" as the ActuatingElement attribute of the ActuatingFunction. In control pass,
    it checks if the associations of type "is logical start of" and "is logical end of" to
    InformationFlow objects have been made.

    Attributes
    ----------
    context : ModuleContext
        The context containing the ID-, and element stack, error-, and object registry.
    element : ET.Element
        The XML element containing the ActuatingFunction to be parsed.
    association_parsers : list[AssociationParser]
        A list of parsers for the associations related to the ActuatingFunction.
    generic_attribute_parser : GenericAttributeParser
        A parser for the generic attributes of the ActuatingFunction.
    actuating_function_id : str | None
        The ID of the ActuatingFunction being constructed. Set during compositional pass.
    actuating_function : instrumentation.ActuatingFunction | None
        The ActuatingFunction object being constructed. Set during compositional pass.
    """

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        association_parsers: list[AssociationParser],
        generic_attribute_parser: GenericAttributeParser,
    ) -> None:
        """Initialize the ActuatingFunctionParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        element : ET.Element
            The XML element containing the ActuatingFunction to be parsed.
        association_parsers : list[AssociationParser]
            A list of parsers for the associations related to the ActuatingFunction.
        generic_attribute_parser : GenericAttributeParser
            A parser for the generic attributes of the ActuatingFunction.
        """
        super().__init__(context)
        self.element = element
        self.actuating_function_id = None
        self.actuating_function = None

        # Set and register association parsers
        self.association_parsers = association_parsers
        self.register_submodule_list(association_parsers)

        # Set and register generic attribute parser
        self.generic_attribute_parser = generic_attribute_parser
        self.register_submodule(generic_attribute_parser)

    @redirect_errors_to_registry
    def compositional_pass(self) -> instrumentation.ActuatingFunction | None:
        """Parse the ActuatingFunction in the compositional pass.

        Composes all associations and generic attributes, and creates an instance of the
        ActuatingFunction class.

        Returns
        -------
        instrumentation.ActuatingFunction | None
            An instance of the ActuatingFunction class created from the parsed attributes, or None
            if an error occurred during parsing.
        """
        # Extract ID. If not found, register an error and return None.
        self.actuating_function_id = self.element.get("ID")
        if self.actuating_function_id is None:
            self.register_error(*ErrorTemplates.id_not_found("ActuatingFunction"))
            return None

        # Compose associations
        for association_parser in self.association_parsers:
            association_parser.compositional_pass()

        # Compose generic attributes
        generic_attrs = self.generic_attribute_parser.compositional_pass(
            instrumentation.ActuatingFunction
        )

        # Create the ActuatingFunction object
        self.actuating_function = instrumentation.ActuatingFunction(
            proteusId=self.actuating_function_id, **generic_attrs
        )

        # Register and return the ActuatingFunction object
        self.register_object(self.actuating_function_id, self.actuating_function)
        return self.actuating_function

    @redirect_errors_to_registry
    def reference_pass(self) -> None:
        """Parse the ActuatingFunction in the reference pass.

        Establishes associations of type "is located in" as the ActuatingLocation attribute of the
        ActuatingFunction. Establishes associations of type "is fulfilled by" as the system
        attribute of the ActuatingFunction. Since both associations can be at max one, it
        logs an error if multiple associations of the same type are found and keeps the first one
        encountered.
        """
        # Call super to call reference pass on all submodules
        super().reference_pass()

        # Skip pass if the reference object or ID is not available due to previous error
        if self.actuating_function is None or self.actuating_function_id is None:
            self.register_error(*ErrorTemplates.skip_pass("reference", "ActuatingFunction"))
            return

        # Establish associations of type "is located in" and "is fulfilled by"
        for association_parser in self.association_parsers:
            # Log error and skip association if not valid
            if not association_parser.is_valid():
                self.register_error(
                    association_parser.get_error_message(),
                    level=ErrorLevels.ERROR,
                )
                continue

            # Check if the association is of type "is located in"
            assoc_type = association_parser.get_type()
            assoc_id = association_parser.get_id()
            if assoc_type == "is located in":
                if self.actuating_function.actuatingLocation is not None:
                    self.register_error(
                        f"Multiple 'is located in' associations found for ActuatingFunction "
                        f"{self.actuating_function_id}. Keeping the first one encountered.",
                        level=ErrorLevels.ERROR,
                    )
                else:
                    try:
                        self.actuating_function.actuatingLocation = (
                            association_parser.get_referenced_item()
                        )
                    except Exception as e:
                        self.register_error(
                            *ErrorTemplates.assoc_adding_error("ActuatingFunction", assoc_id),
                            exception=e,
                        )

            # Check if the association is of type "is fulfilled by"
            elif association_parser.get_type() == "is fulfilled by":
                if self.actuating_function.systems is not None:
                    self.register_error(
                        f"Multiple 'is fulfilled by' associations found for ActuatingFunction "
                        f"{self.actuating_function_id}. Keeping the first one encountered.",
                        level=ErrorLevels.ERROR,
                    )
                else:
                    try:
                        self.actuating_function.systems = association_parser.get_referenced_item()
                    except Exception as e:
                        self.register_error(
                            *ErrorTemplates.assoc_adding_error("ActuatingFunction", assoc_id),
                            exception=e,
                        )
            elif association_parser.get_type() in ["is logical start of", "is logical end of"]:
                # Processed in control pass, so skip here
                continue

            # If unexpected association type, log a warning
            else:
                self.register_error(
                    *ErrorTemplates.inval_assoc_type("ActuatingFunction", assoc_type)
                )

    @redirect_errors_to_registry
    def control_pass(self) -> None:
        """Perform a control pass over the ActuatingFunction associations.

        Checks if associations of type "is logical start of" and "is logical end of" to
        InformationFlow objects have been made."""
        # Call super to call control pass on all submodules
        super().control_pass()

        # Skip pass if the reference object or ID is not available due to previous error
        if self.actuating_function_id is None or self.actuating_function is None:
            self.register_error(*ErrorTemplates.skip_pass("control", "ActuatingFunction"))
            return

        # Iterate through all association parsers and check if they are valid. Check if they have
        # been established in reference pass, and if not, try to add them in control pass.
        for association_parser in self.association_parsers:
            if not association_parser.is_valid():
                # Invalid association errors logged in reference pass
                continue

            elif association_parser.get_type() in ["is logical start of", "is logical end of"]:
                associated_object = association_parser.get_referenced_item()
                association_id = association_parser.get_id()
                if not is_associated_with(self.actuating_function, associated_object):
                    # Log warning and try to add association in control pass
                    self.register_error(
                        *ErrorTemplates.no_assoc_ctrl("ActuatingFunction", association_id)
                    )
                    try:
                        fld = add_by_inferring_type(self.actuating_function, associated_object)
                        # Log an info error if the association was added in control pass
                        self.register_error(
                            *ErrorTemplates.assoc_added_ctrl(
                                "ActuatingFunction", association_id, fld
                            )
                        )
                    except ValueError as e:
                        # If the association cannot be added, log an error
                        self.register_error(
                            *ErrorTemplates.assoc_not_added_ctrl(
                                "ActuatingFunction", association_id
                            ),
                            exception=e,
                        )


class ActuatingElectricalFunctionParser(ParserModule):
    """Parser for ActuatingElectricalFunction elements in the DEXPI model.

    Parses ActuatingElectricalFunction elements into an instance of the ActuatingElectricalFunction
    class. Collects all associations and generic attributes in compositional pass, and returns
    created instance of ActuatingElectricalFunction. In the reference pass, it establishes
    associations of type "is located in" as the ActuatingElectricalLocation attribute of the
    ActuatingElectricalFunction. Associations of type "is fulfilled by" to the
    ActuatingElectricalSystems are disregarded, as ActuatingElectricalSystems are illdefined in
    DEXPI 1.3. In control pass, it checks if the associations of type "is logical end of" to
    InformationFlow objects have been made.

    Attributes
    ----------
    context : ModuleContext
        The context containing the ID-, and element stack, error-, and object registry.
    element : ET.Element
        The XML element containing the ActuatingElectricalFunction to be parsed.
    association_parsers : list[AssociationParser]
        A list of parsers for the associations related to the ActuatingElectricalFunction.
    generic_attribute_parser : GenericAttributeParser
        A parser for the generic attributes of the ActuatingElectricalFunction.
    actuating_function_id : str | None
        The ID of the ActuatingElectricalFunction being constructed. Set during compositional pass.
    actuating_function : instrumentation.ActuatingElectricalFunction | None
        The ActuatingElectricalFunction object being constructed. Set during compositional pass.
    """

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        association_parsers: list[AssociationParser],
        generic_attribute_parser: GenericAttributeParser,
    ) -> None:
        """Initialize the ActuatingElectricalFunctionParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        element : ET.Element
            The XML element containing the ActuatingElectricalFunction to be parsed.
        association_parsers : list[AssociationParser]
            A list of parsers for the associations related to the ActuatingElectricalFunction.
        generic_attribute_parser : GenericAttributeParser
            A parser for the generic attributes of the ActuatingElectricalFunction.
        """
        super().__init__(context)
        self.element = element
        self.actuating_function_id = None
        self.actuating_function = None

        # Set and register association parsers
        self.association_parsers = association_parsers
        self.register_submodule_list(association_parsers)

        # Set and register generic attribute parser
        self.generic_attribute_parser = generic_attribute_parser
        self.register_submodule(generic_attribute_parser)

    @redirect_errors_to_registry
    def compositional_pass(self) -> instrumentation.ActuatingElectricalFunction | None:
        """Parse the ActuatingElectricalFunction in the compositional pass.

        Composes all associations and generic attributes, and creates an instance of the
        ActuatingElectricalFunction class.

        Returns
        -------
        instrumentation.ActuatingElectricalFunction | None
            An instance of the ActuatingElectricalFunction class created from the parsed attributes,
            or None if an error occurred during parsing.
        """
        # Extract ID. If not found, register an error and return None.
        self.actuating_function_id = self.element.get("ID")
        if self.actuating_function_id is None:
            self.register_error(*ErrorTemplates.id_not_found("ActuatingFunction"))
            return None

        # Compose associations
        for association_parser in self.association_parsers:
            association_parser.compositional_pass()

        # Compose generic attributes
        generic_attrs = self.generic_attribute_parser.compositional_pass(
            instrumentation.ActuatingElectricalFunction
        )

        # Create the ActuatingElectricalFunction object
        self.actuating_function = instrumentation.ActuatingElectricalFunction(
            proteusId=self.actuating_function_id, **generic_attrs
        )

        # Register and return the ActuatingElectricalFunction object
        self.register_object(self.actuating_function_id, self.actuating_function)
        return self.actuating_function

    @redirect_errors_to_registry
    def reference_pass(self) -> None:
        """Parse the ActuatingElectricalFunction in the reference pass.

        Establishes associations of type "is located in" as the ActuatingElectricalLocation
        attribute of the ActuatingElectricalFunction. Associations of type "is fulfilled by" are
        disregarded, due to ambiguous and faulty design of ActuatingElectricalSystem in DEXPI 1.3.
        """
        # Call super to call reference pass on all submodules
        super().reference_pass()

        # Skip pass if the reference object or ID is not available due to previous error
        if self.actuating_function is None or self.actuating_function_id is None:
            self.register_error(
                *ErrorTemplates.skip_pass("reference", "ActuatingElectricalFunction")
            )
            return

        # Establish associations of type "is located in"
        for association_parser in self.association_parsers:
            # Log error and skip association if not valid
            if not association_parser.is_valid():
                self.register_error(
                    association_parser.get_error_message(),
                    level=ErrorLevels.ERROR,
                )
                continue

            # Check if the association is of type "is located in"
            assoc_type = association_parser.get_type()
            if assoc_type == "is located in":
                if self.actuating_function.actuatingElectricalLocation is not None:
                    self.register_error(
                        f"Multiple 'is located in' associations found for "
                        f"ActuatingElectricalFunction {self.actuating_function_id}. Keeping the "
                        f"first one encountered.",
                        level=ErrorLevels.ERROR,
                    )
                else:
                    try:
                        self.actuating_function.actuatingElectricalLocation = (
                            association_parser.get_referenced_item()
                        )
                    except Exception as e:
                        self.register_error(
                            *ErrorTemplates.assoc_adding_error(
                                "ActuatingElectricalFunction", association_parser.get_id()
                            ),
                            exception=e,
                        )

            # Check if the association is of type "is fulfilled by"
            elif assoc_type == "is fulfilled by":
                self.register_error(
                    "Association of type 'is fulfilled by' to "
                    "ActuatingElectricalSystem objects is not implemented, due to unclear "
                    "definition of ActuatingElectricalSystem in DEXPI 1.3.",
                    level=ErrorLevels.ERROR,
                )
            elif assoc_type in ["is logical end of"]:
                # Processed in control pass, so skip here
                continue

            # If unexpected association type, log a warning
            else:
                self.register_error(
                    *ErrorTemplates.inval_assoc_type("ActuatingElectricalFunction", assoc_type)
                )

    @redirect_errors_to_registry
    def control_pass(self) -> None:
        """Perform a control pass over the ActuatingElectricalFunction associations.

        Checks if associations of type "is logical end of" to InformationFlow objects have been
        made."""
        # Call super to call control pass on all submodules
        super().control_pass()

        # Skip pass if the reference object or ID is not available due to previous error
        if self.actuating_function_id is None or self.actuating_function is None:
            self.register_error(*ErrorTemplates.skip_pass("control", "ActuatingElectricalFunction"))
            return

        # Iterate through all association parsers and check if they are valid. Check if they have
        # been established in reference pass, and if not, try to add them in control pass.
        for association_parser in self.association_parsers:
            if not association_parser.is_valid():
                # Invalid association errors logged in reference pass
                continue

            elif association_parser.get_type() in ["is logical end of"]:
                associated_object = association_parser.get_referenced_item()
                association_id = association_parser.get_id()
                if not is_associated_with(self.actuating_function, associated_object):
                    # Log warning and try to add association in control pass
                    self.register_error(
                        *ErrorTemplates.no_assoc_ctrl("ActuatingFunction", association_id)
                    )
                    try:
                        fld = add_by_inferring_type(self.actuating_function, associated_object)
                        # Log an info error if the association was added in control pass
                        self.register_error(
                            *ErrorTemplates.assoc_added_ctrl(
                                "ActuatingElectricalFunction", association_id, fld
                            )
                        )
                    except ValueError as e:
                        # If the association cannot be added, log an error
                        self.register_error(
                            *ErrorTemplates.assoc_not_added_ctrl(
                                "ActuatingElectricalFunction", association_id
                            ),
                            exception=e,
                        )


class ProcessSignalGeneratingFunctionParser(ParserModule):
    """Parser for ProcessSignalGeneratingFunction elements in the DEXPI model.

    Parses ProcessSignalGeneratingFunction elements into an instance of the
    ProcessSignalGeneratingFunction class. Collects all associations and generic attributes in
    compositional pass, and returns created instance of ProcessSignalGeneratingFunction.
    In the reference pass, it establishes associations of type "is located in"
    as the SensingLocation attribute of the ProcessSignalGeneratingFunction, and associations of
    type "is fulfilled by" as the SensingLocation attribute of the ProcessSignalGeneratingFunction.
    In control pass, it checks if the associations of type "is logical start of" and
    "is logical end of" to InformationFlow objects have been made.

    Attributes
    ----------
    context : ModuleContext
        The context containing the ID-, and element stack, error-, and object registry.
    element : ET.Element
        The XML element containing the ProcessSignalGeneratingFunction to be parsed.
    association_parsers : list[AssociationParser]
        A list of parsers for the associations related to the ProcessSignalGeneratingFunction.
    generic_attribute_parser : GenericAttributeParser
        A parser for the generic attributes of the ProcessSignalGeneratingFunction.
    psgf_id : str | None
        The ID of the ProcessSignalGeneratingFunction being parsed.
    psgf : instrumentation.ProcessSignalGeneratingFunction | None
        The ProcessSignalGeneratingFunction object being constructed. Set during compositional pass.

    """

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        association_parsers: list[AssociationParser],
        generic_attribute_parser: GenericAttributeParser,
    ) -> None:
        """Initialize the ProcessSignalGeneratingFunctionParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        element : ET.Element
            The XML element containing the ProcessSignalGeneratingFunction to be parsed.
        association_parsers : list[AssociationParser]
            A list of parsers for the associations related to the ProcessSignalGeneratingFunction.
        generic_attribute_parser : GenericAttributeParser
            A parser for the generic attributes of the ProcessSignalGeneratingFunction.
        """
        super().__init__(context)
        self.element = element
        self.psgf_id = None
        self.psgf = None

        # Set and register association parsers
        self.association_parsers = association_parsers
        self.register_submodule_list(self.association_parsers)

        # Set and register generic attribute parser
        self.generic_attribute_parser = generic_attribute_parser
        self.register_submodule(self.generic_attribute_parser)

    @redirect_errors_to_registry
    def compositional_pass(self) -> instrumentation.ProcessSignalGeneratingFunction | None:
        """Parse the ProcessSignalGeneratingFunction in the compositional pass.

        Composes all associations and generic attributes, and creates an instance of the
        ProcessSignalGeneratingFunction class.

        Returns
        -------
        instrumentation.ProcessSignalGeneratingFunction | None
            An instance of the ProcessSignalGeneratingFunction class created from the parsed
            attributes, or None if an error occurred during parsing.
        """
        # Extract ID
        self.psgf_id = self.element.get("ID")
        if self.psgf_id is None:
            self.register_error(*ErrorTemplates.id_not_found("ProcessSignalGeneratingFunction"))
            return None

        # Compose associations
        for association_parser in self.association_parsers:
            association_parser.compositional_pass()

        # Compose generic attributes
        generic_attrs = self.generic_attribute_parser.compositional_pass(
            instrumentation.ProcessSignalGeneratingFunction
        )

        # Create the ProcessSignalGeneratingFunction object
        self.psgf = instrumentation.ProcessSignalGeneratingFunction(
            proteusId=self.psgf_id, **generic_attrs
        )

        # Register and return the ProcessSignalGeneratingFunction object
        self.register_object(self.psgf_id, self.psgf)
        return self.psgf

    @redirect_errors_to_registry
    def reference_pass(self) -> None:
        """Parse the ProcessSignalGeneratingFunction in the reference pass.

        Establishes associations of type "is located in" as the SensingLocation attribute of the
        ProcessSignalGeneratingFunction. Establishes associations of type "is fulfilled by" as the
        system attribute of the ProcessSignalGeneratingFunction. Since both associations can be at
        max one, it logs an error if multiple associations of the same type are found and keeps the
        first one encountered.
        """
        # Call super to call reference pass on all submodules
        super().reference_pass()

        # Skip reference pass if id or object are not available due to previous error in
        # compositional pass.
        if self.psgf is None or self.psgf_id is None:
            self.register_error(
                *ErrorTemplates.skip_pass("reference", "ProcessSignalGeneratingFunction")
            )
            return

        # Establish associations of type "is located in" and "is fulfilled by"
        for association_parser in self.association_parsers:
            # Log error and skip association if not valid
            if not association_parser.is_valid():
                self.register_error(
                    association_parser.get_error_message(),
                    level=ErrorLevels.ERROR,
                )
                continue

            # Check if the association is of type "is located in"
            assoc_type = association_parser.get_type()
            assoc_id = association_parser.get_id()
            if assoc_type == "is located in":
                if self.psgf.sensingLocation is not None:
                    i = self.psgf_id
                    self.register_error(
                        f"Multiple 'is located in' associations found for "
                        f"ProcessSignalGeneratingFunction {i}. Keeping the first one encountered.",
                        level=ErrorLevels.ERROR,
                    )
                else:
                    try:
                        self.psgf.sensingLocation = association_parser.get_referenced_item()
                    except Exception as e:
                        self.register_error(
                            *ErrorTemplates.assoc_adding_error(
                                "ProcessSignalGeneratingFunction", assoc_id
                            ),
                            exception=e,
                        )

            # Check if the association is of type "is fulfilled by"
            elif assoc_type == "is fulfilled by":
                if self.psgf.systems is not None:
                    i = self.psgf_id
                    self.register_error(
                        f"Multiple 'is fulfilled by' associations found for "
                        f"ProcessSignalGeneratingFunction {i}. Keeping the first one encountered.",
                        level=ErrorLevels.ERROR,
                    )
                else:
                    try:
                        self.psgf.systems = association_parser.get_referenced_item()
                    except Exception as e:
                        i = self.psgf_id
                        self.register_error(
                            *ErrorTemplates.assoc_adding_error(
                                "ProcessSignalGeneratingFunction", assoc_id
                            ),
                            exception=e,
                        )
            elif assoc_type in ["is logical start of"]:
                # Processed in control pass, so skip here
                continue

            # If unexpected association type, log a warning
            else:
                self.register_error(
                    *ErrorTemplates.inval_assoc_type("ProcessSignalGeneratingFunction", assoc_type)
                )

    @redirect_errors_to_registry
    def control_pass(self) -> None:
        """Perform a control pass over the ProcessSignalGeneratingFunctionParser associations.

        Checks if associations of type "is logical start of" to InformationFlow objects have been
        made."""
        # Call super to call control pass on all submodules
        super().control_pass()

        # Skip pass if the reference object or ID is not available due to previous error
        if self.psgf_id is None or self.psgf is None:
            self.register_error(
                *ErrorTemplates.skip_pass("control", "ProcessSignalGeneratingFunction")
            )
            return

        # Iterate through all association parsers and check if they are valid. Check if they have
        # been established in reference pass, and if not, try to add them in control pass.
        for association_parser in self.association_parsers:
            if not association_parser.is_valid():
                # Invalid association errors logged in reference pass
                continue

            elif association_parser.get_type() in ["is logical start of"]:
                associated_object = association_parser.get_referenced_item()
                association_id = association_parser.get_id()
                if not is_associated_with(self.psgf, associated_object):
                    # Log warning and try to add association in control pass
                    err = ErrorTemplates.no_assoc_ctrl(
                        "ProcessSignalGeneratingFunction", association_id
                    )
                    self.register_error(*err)
                    try:
                        fld = add_by_inferring_type(self.psgf, associated_object)
                        # Log an info error if the association was added in control pass
                        self.register_error(
                            *ErrorTemplates.assoc_added_ctrl(
                                "ProcessSignalGeneratingFunction", association_id, fld
                            )
                        )
                    except ValueError as e:
                        # If the association cannot be added, log an error
                        self.register_error(
                            *ErrorTemplates.assoc_not_added_ctrl(
                                "ProcessSignalGeneratingFunction", association_id
                            ),
                            exception=e,
                        )


class SignalOffPageConnectorParser(ParserModule):
    """Parser for SignalOffPageConnector elements in the DEXPI model.

    Parses SignalOffPageConnector elements into an instance of the SignalOffPageConnector class.
    Collects all associations and generic attributes in compositional pass, and returns created
    instance of SignalOffPageConnector. In the reference pass, it establishes associations of type
    "is location of" as the source attribute and "is referenced by" as the target attribute.

    Attributes
    ----------
    context : ModuleContext
        The context containing the ID-, and element stack, error-, and object registry.
    element : ET.Element
        The XML element containing the SignalOffPageConnector to be parsed.
    reference_parsers : list[OffPageConnectorReferenceParser]
        A list of parsers for the off-page connector references related to the
        SignalOffPageConnector
    association_parsers : list[AssociationParser]
        A list of parsers for the associations related to the SignalOffPageConnector.
    generic_attribute_parser : GenericAttributeParser
        A parser for the generic attributes of the SignalOffPageConnector.
    signal_off_page_connector_id : str | None
        The ID of the SignalOffPageConnector being parsed. Set during compositional pass.
    obj : instrumentation.SignalOffPageConnector | None
        The SignalOffPageConnector object being constructed. Set during compositional pass.
    """

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        reference_parsers: list[OffPageConnectorReferenceParser],
        association_parsers: list[AssociationParser],
    ) -> None:
        """Initialize the SignalOffPageConnectorParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        element : ET.Element
            The XML element containing the SignalOffPageConnector to be parsed.
        reference_parsers : list[OffPageConnectorReferenceParser]
            A list of parsers for the off-page connector references related to the
            SignalOffPageConnector.
        association_parsers : list[AssociationParser]
            A list of parsers for the associations related to the SignalOffPageConnector.
        """
        super().__init__(context)
        self.element = element
        self.signal_off_page_connector_id = None
        self.obj = None

        # Set and register off-page connector reference parsers
        self.reference_parsers = reference_parsers
        self.register_submodule_list(reference_parsers)

        # Set and register association parsers
        self.association_parsers = association_parsers
        self.register_submodule_list(association_parsers)

    @redirect_errors_to_registry
    def compositional_pass(self) -> instrumentation.SignalOffPageConnector | None:
        """Parse the SignalOffPageConnector in the compositional pass.

        Composes all associations and references, and creates an instance of the
        SignalOffPageConnector class.

        Returns
        -------
        instrumentation.SignalOffPageConnector | None
            An instance of the SignalOffPageConnector class created from the parsed attributes, or
            None if an error occurred during parsing.
        """
        # Extract ID. If not found, register an error and return None.
        self.signal_off_page_connector_id = self.element.get("ID")
        if self.signal_off_page_connector_id is None:
            self.register_error(*ErrorTemplates.id_not_found("SignalOffPageConnector"))
            return None

        # Get class name
        class_name = self.element.get("ComponentClass")

        try:
            MyClass = getattr(instrumentation, class_name)
        except AttributeError:
            self.register_error(
                f"Invalid class {class_name} for SignalOffPageConnector. Using "
                f"SignalOffPageConnector instead.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Compose and collect references
        if len(self.reference_parsers) > 1:
            # Log a warning if there are multiple reference parsers
            self.register_error(
                "Multiple PipeOffPageConnectorReference parsers found. Keeping only the first "
                "valid one.",
                level=ErrorLevels.WARNING,
            )

        for reference_parser in self.reference_parsers:
            reference_obj = reference_parser.compositional_pass()
            if reference_obj:
                # If the reference object is valid, break
                break

        # Compose associations
        for association_parser in self.association_parsers:
            association_parser.compositional_pass()

        self.obj = MyClass(
            proteusId=self.signal_off_page_connector_id, connectorReference=reference_obj
        )

        # Register the object
        self.register_object(self.signal_off_page_connector_id, self.obj)

        return self.obj

    @redirect_errors_to_registry
    def control_pass(self) -> None:
        """Perform a control pass over the SignalOffPageConnectorParser associations.

        Checks that associations of type "is logical start of" and "is logical end of" to
        InformationFlow objects have been made. Also checks if associations of type
        "is referenced by" to OPC references have been made, and if not, tries to add them in
        control pass."""
        # Call super to call control pass on all submodules
        super().control_pass()

        # Skip pass if the reference object or ID is not available due to previous error
        if self.signal_off_page_connector_id is None or self.obj is None:
            self.register_error(*ErrorTemplates.skip_pass("control", "SignalOffPageConnector"))
            return

        # Otherwise, iterate through all association parsers and check if they are valid.
        for association_parser in self.association_parsers:
            if not association_parser.is_valid():
                # Log and skip invalid associations
                self.register_error(
                    association_parser.get_error_message(),
                    level=ErrorLevels.ERROR,
                )
                continue

            assoc_type = association_parser.get_type()
            if assoc_type in ["is logical start of", "is logical end of", "is referenced by"]:
                associated_object = association_parser.get_referenced_item()
                assoc_id = association_parser.get_id()
                if not is_associated_with(self.obj, associated_object):
                    # Log warning and try to add association in control pass
                    self.register_error(
                        *ErrorTemplates.no_assoc_ctrl("SignalOffPageConnector", assoc_id)
                    )
                    try:
                        fld = add_by_inferring_type(self.obj, associated_object)
                        # Log an info error if the association was added in control pass
                        self.register_error(
                            *ErrorTemplates.assoc_added_ctrl(
                                "SignalOffPageConnector", assoc_id, fld
                            )
                        )
                    except ValueError as e:
                        # If the association cannot be added, log an error
                        self.register_error(
                            *ErrorTemplates.assoc_not_added_ctrl(
                                "SignalOffPageConnector", assoc_id
                            ),
                            exception=e,
                        )
            else:
                # If unexpected association type, log a warning
                self.register_error(
                    *ErrorTemplates.inval_assoc_type("SignalOffPageConnector", assoc_type)
                )


class InformationFlowParser(ParserModule):
    """Parser for InformationFlow elements in the DEXPI model.

    Parses InformationFlow elements into an instance of the SignalConveyingFunction class (or
    appropriate subclass retrieved from ComponentClass). Collects all associations and generic
    attributes in compositional pass, and returns created instance of SignalConveyingFunction.
    In the reference pass, it establishes associations of type "has logical start" and
    "has logical end" as source and target attributes.

    Attributes
    ----------
    context : ModuleContext
        The context containing the ID-, and element stack, error-, and object registry.
    element : ET.Element
        The XML element containing the InformationFlow to be parsed.
    association_parsers : list[AssociationParser]
        A list of parsers for the associations related to the InformationFlow.
    generic_attribute_parser : GenericAttributeParser
        A parser for the generic attributes of the InformationFlow.
    center_line_parsers : list[CenterLineParser]
        List of center line parsers to be used by the information flow parser.
    information_flow_id : str | None
        The ID of the InformationFlow element being parsed. Set during compositional pass.
    obj : instrumentation.SignalConveyingFunction | None
        The SignalConveyingFunction object being constructed. Set during compositional pass.
    """

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        association_parsers: list[AssociationParser],
        generic_attribute_parser: GenericAttributeParser,
        center_line_parsers: list[CenterLineParser],
    ) -> None:
        """Initialize the InformationFlowParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        element : ET.Element
            The XML element containing the InformationFlow to be parsed.
        association_parsers : list[AssociationParser]
            A list of parsers for the associations related to the InformationFlow.
        generic_attribute_parser : GenericAttributeParser
            A parser for the generic attributes of the InformationFlow.
        center_line_parsers : list[CenterLineParser]
            List of center line parsers to be used by the information flow parser.
        """
        super().__init__(context)
        self.element = element
        self.information_flow_id = None
        self.obj = None
        self.information_flow_dwg = None

        # Set and register association parsers
        self.association_parsers = association_parsers
        self.register_submodule_list(association_parsers)

        # Set and register generic attribute parser
        self.generic_attribute_parser = generic_attribute_parser
        self.register_submodule(generic_attribute_parser)

        # Set and register center line parser
        self.center_line_parsers = center_line_parsers
        self.register_submodule_list(center_line_parsers)

    @redirect_errors_to_registry
    def compositional_pass(self) -> instrumentation.SignalConveyingFunction | None:
        """Parse the InformationFlow in the compositional pass.

        Composes all associations and generic attributes, and creates an instance of the
        SignalConveyingFunction. If the ComponentClass attribute is not found in the
        instrumentation module, it uses SignalConveyingFunction as a fallback and adds a custom
        typeName attribute.

        Returns
        -------
        instrumentation.SignalConveyingFunction | None
            An instance of the SignalConveyingFunction class created from the parsed attributes, or
            None if an error occurred during parsing.
        """
        # Extract ID. If not found, log an error and return None.
        self.information_flow_id = self.element.get("ID")
        if self.information_flow_id is None:
            self.register_error(*ErrorTemplates.id_not_found("InformationFlow"))
            return None

        kwargs = {}

        # Get the component type
        class_name = self.element.get("ComponentClass")

        # If class name not part of instrumentation, treat it as SignalConveyingFunction
        custom_type = None
        try:
            MyClass = getattr(instrumentation, class_name)
        except AttributeError:
            MyClass = instrumentation.SignalConveyingFunction
            custom_type = customization.CustomStringAttribute(
                attributeName="typeName",
                value=class_name,
            )

            # Log a warning that the class name is invalid
            self.register_error(
                f"Invalid class {class_name} for InformationFlow. Using "
                f"SignalConveyingFunction instead and adding custom typeName attribute.",
                level=ErrorLevels.WARNING,
            )

        # Compose associations
        for association_parser in self.association_parsers:
            association_parser.compositional_pass()

        # Compose generic attributes
        generic_attrs = self.generic_attribute_parser.compositional_pass(MyClass)
        kwargs.update(generic_attrs)

        if custom_type is not None:
            if "customAttributes" not in kwargs:
                kwargs["customAttributes"] = []
            kwargs["customAttributes"].append(custom_type)

        # Make component and register it
        self.obj = MyClass(proteusId=self.information_flow_id, **kwargs)

        self.register_object(self.information_flow_id, self.obj)

        return self.obj

    @redirect_errors_to_registry
    def reference_pass(self) -> None:
        """Perform a reference pass over the InformationFlow.

        Establishes associations of type "has logical start" and "has logical end" as the
        source and target attributes of the SignalConveyingFunction, respectively.
        If multiple associations of the same type are found, it logs an error and keeps the first
        one encountered.
        """
        # Call super to call reference pass on all submodules
        super().reference_pass()

        # Skip pass if the reference object or ID is not available due to previous error
        if self.obj is None or self.information_flow_id is None:
            self.register_error(*ErrorTemplates.skip_pass("reference", "InformationFlow"))
            return

        # Establish associations of type "has logical start" and "has logical end"
        for association_parser in self.association_parsers:
            if not association_parser.is_valid():
                # Log error and skip association
                self.register_error(
                    association_parser.get_error_message(),
                    level=ErrorLevels.ERROR,
                )
                continue

            assoc_type = association_parser.get_type()
            assoc_id = association_parser.get_id()
            if assoc_type == "has logical start":
                if self.obj.source is not None:
                    self.register_error(
                        f"Multiple 'has logical start' associations found for InformationFlow "
                        f"{self.information_flow_id}. Keeping the first one encountered.",
                        level=ErrorLevels.ERROR,
                    )
                else:
                    try:
                        self.obj.source = association_parser.get_referenced_item()
                    except Exception as e:
                        self.register_error(
                            *ErrorTemplates.assoc_adding_error("InformationFlow", assoc_id),
                            exception=e,
                        )

            elif assoc_type == "has logical end":
                if self.obj.target is not None:
                    self.register_error(
                        f"Multiple 'has logical end' associations found for InformationFlow "
                        f"{self.information_flow_id}. Keeping the first one encountered.",
                        level=ErrorLevels.ERROR,
                    )
                else:
                    try:
                        self.obj.target = association_parser.get_referenced_item()
                    except Exception as e:
                        self.register_error(
                            *ErrorTemplates.assoc_adding_error("InformationFlow", assoc_id),
                            exception=e,
                        )

            else:
                self.register_error(*ErrorTemplates.inval_assoc_type("InformationFlow", assoc_type))

    def drawing_pass(self) -> graphics.RepresentationGroup | None:
        """Parse the InformationFlow in the drawing pass.

        Composes the center line and adds it to a RepresentationGroup.

        Returns
        -------
        graphics.RepresentationGroup | None
            An instance of the RepresentationGroup class containing the center line, or None if an
            error occurred during parsing.
        """
        if len(self.center_line_parsers) > 1:
            self.register_error(
                f"Found {len(self.center_line_parsers)} CenterLine elements for InformationFlow, "
                "expected at most 1. Using the first one.",
                level=ErrorLevels.WARNING,
            )
        elif len(self.center_line_parsers) == 0:
            return None

        center_line_parser = self.center_line_parsers[0]

        # Skip pass if the reference object or ID is not available due to previous error
        if self.obj is None or self.information_flow_id is None:
            self.register_error(*ErrorTemplates.skip_pass("drawing", "InformationFlow"))
            return None

        node_positions = []

        # Compose center line
        connector_line_static = center_line_parser.drawing_pass()
        self.information_flow_dwg = graphics.RepresentationGroup(
            represents=self.obj,
            groups=[connector_line_static],
            nodePositions=node_positions,
        )

        return self.information_flow_dwg

    def drawing_reference_pass(self) -> None:
        """Perform a drawing reference pass over the InformationFlow.

        Calls drawing reference pass on all submodules."""
        # Call super to call drawing reference pass on all submodules

        connection_element = self.element.find("Connection")
        if connection_element is not None:
            from_id = connection_element.get("FromID")
            to_id = connection_element.get("ToID")
            from_node = connection_element.get("FromNode")
            to_node = connection_element.get("ToNode")

            if from_id and to_id and from_node and to_node:
                # Find Source and Target object from ObjectRegistry
                source_object = self.get_object_from_registry(from_id + "_cp_node_positions")
                target_object = self.get_object_from_registry(to_id + "_cp_node_positions")

                if source_object is None:
                    self.register_error(
                        f"Source node with ID {from_id} not found in registry.",
                        level=ErrorLevels.WARNING,
                    )
                if target_object is None:
                    self.register_error(
                        f"Target node with ID {to_id} not found in registry.",
                        level=ErrorLevels.WARNING,
                    )

                if source_object and target_object:
                    # Get values as list and access by index (1-based to 0-based conversion)
                    source_values = list(source_object.values())
                    target_values = list(target_object.values())
                    source_node = source_values[int(from_node) - 1] if source_values else None
                    target_node = target_values[int(to_node) - 1] if target_values else None

                    if source_node is not None and target_node is not None:
                        # Add node positions to the information flow drawing
                        if self.information_flow_dwg is not None:
                            self.information_flow_dwg.nodePositions.extend(
                                [source_node, target_node]
                            )

                            # Update the connector line's source and target nodes
                            if isinstance(
                                self.information_flow_dwg.groups[0], graphics.Static
                            ) and isinstance(
                                self.information_flow_dwg.groups[0].elements[0],
                                graphics.ConnectorLine,
                            ):
                                connector_line = self.information_flow_dwg.groups[0].elements[0]
                                connector_line.source = source_node
                                connector_line.target = target_node
                    else:
                        self.register_error(
                            f"Could not find node positions for connection: FromNode={from_node}, ToNode={to_node}",
                            level=ErrorLevels.WARNING,
                        )


class InstrumentationNodeParser(ParserModule):
    """Parser for InstrumentationNode elements in the DEXPI model.

    Parses InstrumentationNode elements into an instance of the InstrumentationNodePosition class.

    Attributes
    ----------
    context : ModuleContext
        The context containing the ID-, and element stack, error-, and object registry.
    element : ET.Element
        The XML element containing the InstrumentationNode to be parsed.
    position_parsers : list[PositionParser]
        List of position parsers to be used by the instrumentation node parser.
    """

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        position_parsers: list[PositionParser],
    ) -> None:
        """Initialize the InstrumentationNodeParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        element : ET.Element
            The XML element containing the InstrumentationNode to be parsed.
        position_parsers : list[PositionParser]
            List of position parsers to be used by the instrumentation node parser.
        """
        super().__init__(context)
        self.element = element
        self.instrumentation_node_id = None
        self.instrumentation_node_dwg = None

        # Set and register position parser
        self.position_parsers = position_parsers
        self.register_submodule_list(position_parsers)

    def compositional_pass(self) -> None:
        pass

    @redirect_errors_to_registry
    def drawing_pass(self) -> tuple[str, graphics.InstrumentationNodePosition] | None:
        """Parse the InstrumentationNode in the drawing pass.

        Composes the position and creates an instance of the InstrumentationNodePosition class.

        Returns
        -------
        instrumentation.InstrumentationNodePosition | None
            An instance of the InstrumentationNodePosition class created from the parsed
            attributes, or None if an error occurred during parsing.
        """
        if len(self.position_parsers) > 1:
            self.register_error(
                f"Found {len(self.position_parsers)} Position elements for InstrumentationNode, "
                "expected at most 1. Using the first one.",
                level=ErrorLevels.WARNING,
            )
        elif len(self.position_parsers) == 0:
            return None

        position_parser = self.position_parsers[0]
        if position_parser is not None:
            self.register_submodule(position_parser)

        # Extract ID
        self.instrumentation_node_id = self.element.get("ID")

        # Compose position
        position, _, _ = position_parser.compositional_pass()

        if position is None:
            self.register_error(*ErrorTemplates.skip_pass("drawing", "InstrumentationNode"))
            return None

        # Create the InstrumentationNodePosition object
        self.instrumentation_node_dwg = graphics.InstrumentationNodePosition(position=position)

        return self.instrumentation_node_id, self.instrumentation_node_dwg


class ProcessInstrumentationFunctionParser(ParserModule):
    """Parser for ProcessInstrumentationFunction elements in the DEXPI model.

    Parses ProcessInstrumentationFunction elements into an instance of the
    ProcessInstrumentationFunction class. Parses and creates the object in compositional pass,
    and checks if associations of type "is logical start of" and "is logical end of" were correctly
    established in control pass. No reference pass is required.

    Attributes
    ----------
    context : ModuleContext
        The context containing the ID-, and element stack, error-, and object registry.
    element : ET.Element
        The XML element containing the ProcessInstrumentationFunction to be parsed.
    actuating_electrical_function_parsers : list[ActuatingElectricalFunctionParser]
        A list of parsers for the actuating electrical functions related to the
        ProcessInstrumentationFunction.
    actuating_function_parsers : list[ActuatingFunctionParser]
        A list of parsers for the actuating functions related to the
        ProcessInstrumentationFunction.
    signal_generating_function_parsers : list[ProcessSignalGeneratingFunctionParser]
        A list of parsers for the process signal generating functions related to the
        ProcessInstrumentationFunction.
    signal_opc_parsers : list[SignalOffPageConnectorParser]
        A list of parsers for the signal off-page connectors related to the
        ProcessInstrumentationFunction.
    information_flow_parsers : list[InformationFlowParser]
        A list of parsers for the signal conveying functions related to the
        ProcessInstrumentationFunction.
    association_parsers : list[AssociationParser]
        A list of parsers for the associations related to the ProcessInstrumentationFunction.
    generic_attribute_parser : GenericAttributeParser
        A parser for the generic attributes of the ProcessInstrumentationFunction.
    pif_id : str | None
        The ID of the ProcessInstrumentationFunction being parsed. Set during compositional pass.
    pif_obj : instrumentation.ProcessInstrumentationFunction | None
        The ProcessInstrumentationFunction object being constructed. Set during compositional pass.
    """

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        actuating_electrical_function_parsers: list[ActuatingElectricalFunctionParser],
        actuating_function_parsers: list[ActuatingFunctionParser],
        signal_generating_function_parsers: list[ProcessSignalGeneratingFunctionParser],
        signal_opc_parsers: list[SignalOffPageConnectorParser],
        information_flow_parsers: list[InformationFlowParser],
        association_parsers: list[AssociationParser],
        generic_attribute_parser: GenericAttributeParser,
        shape_usage_parser: ShapeUsageParser,
        label_parsers: list[LabelParser],
        connection_point_parsers: list[ConnectionPointParser],
    ) -> None:
        """Initialize the ProcessInstrumentationFunctionParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        element : ET.Element
            The XML element containing the ProcessInstrumentationFunction to be parsed.
        actuating_electrical_function_parsers : list[ActuatingElectricalFunctionParser]
            A list of parsers for the actuating electrical functions related to the
            ProcessInstrumentationFunction.
        actuating_function_parsers : list[ActuatingFunctionParser]
            A list of parsers for the actuating functions related to the
            ProcessInstrumentationFunction.
        signal_generating_function_parsers : list[ProcessSignalGeneratingFunctionParser]
            A list of parsers for the process signal generating functions related to the
            ProcessInstrumentationFunction.
        signal_opc_parsers : list[SignalOffPageConnectorParser]
            A list of parsers for the signal off-page connectors related to the
            ProcessInstrumentationFunction.
        information_flow_parsers : list[InformationFlowParser]
            A list of parsers for the signal conveying functions related to the
            ProcessInstrumentationFunction.
        association_parsers : list[AssociationParser]
            A list of parsers for the associations related to the ProcessInstrumentationFunction.
        generic_attribute_parser : GenericAttributeParser
            A parser for the generic attributes of the ProcessInstrumentationFunction.
        shape_usage_parser : ShapeUsageParser
            A parser for the shape usage of the ProcessInstrumentationFunction.
        label_parsers : list[LabelParser]
            A list of parsers for the labels related to the ProcessInstrumentationFunction.
        connection_point_parsers : list[ConnectionPointParser]
            A list of parsers for the connection points related to the ProcessInstrumentationFunction.

        """
        super().__init__(context)
        self.element = element
        self.pif_id = None
        self.pif_obj = None
        self.pif_dwg = None

        # Set and register all submodule parsers
        self.actuating_electrical_function_parsers = actuating_electrical_function_parsers
        self.register_submodule_list(actuating_electrical_function_parsers)

        self.actuating_function_parsers = actuating_function_parsers
        self.register_submodule_list(actuating_function_parsers)

        self.signal_generating_function_parsers = signal_generating_function_parsers
        self.register_submodule_list(signal_generating_function_parsers)

        self.signal_opc_parsers = signal_opc_parsers
        self.register_submodule_list(signal_opc_parsers)

        self.information_flow_parsers = information_flow_parsers
        self.register_submodule_list(information_flow_parsers)

        # Set and register association parsers
        self.association_parsers = association_parsers
        self.register_submodule_list(association_parsers)

        # Set and register generic attribute parser
        self.generic_attribute_parser = generic_attribute_parser
        self.register_submodule(generic_attribute_parser)

        # Set and register shape usage parser
        self.shape_usage_parser = shape_usage_parser
        self.register_submodule(shape_usage_parser)

        # Set and register label parsers
        self.label_parsers = label_parsers
        self.register_submodule_list(label_parsers)

        # Set and register connection point parsers
        self.connection_point_parsers = connection_point_parsers
        self.register_submodule_list(connection_point_parsers)

    @redirect_errors_to_registry
    def compositional_pass(self) -> instrumentation.ProcessInstrumentationFunction | None:
        """Parse the ProcessInstrumentationFunction in the compositional pass.

        Composes all associations, actuating electrical functions, actuating functions,
        process signal generating functions, signal off-page connectors, signal conveying functions,
        and generic attributes, and creates an instance of the ProcessInstrumentationFunction class.

        Returns
        -------
        instrumentation.ProcessInstrumentationFunction | None
            An instance of the ProcessInstrumentationFunction class created from the parsed
            attributes, or None if an error occurred during parsing.
        """
        # Extract ID. If not found, register an error and return None.
        self.pif_id = self.element.get("ID")
        if self.pif_id is None:
            self.register_error(*ErrorTemplates.id_not_found("ProcessInstrumentationFunction"))
            return None

        # Compose associations
        for association_parser in self.association_parsers:
            association_parser.compositional_pass()

        # Compose actuating electrical functions
        actuating_electrical_functions = []
        for parser in self.actuating_electrical_function_parsers:
            aef = parser.compositional_pass()
            if aef is not None:
                actuating_electrical_functions.append(aef)

        # Compose actuating functions
        actuating_functions = []
        for parser in self.actuating_function_parsers:
            af = parser.compositional_pass()
            if af is not None:
                actuating_functions.append(af)

        # Compose process signal generating functions
        process_signal_generating_functions = []
        for parser in self.signal_generating_function_parsers:
            psgf = parser.compositional_pass()
            if psgf is not None:
                process_signal_generating_functions.append(psgf)

        # Compose signal off-page connectors
        signal_off_page_connectors = []
        for parser in self.signal_opc_parsers:
            sopc = parser.compositional_pass()
            if sopc is not None:
                signal_off_page_connectors.append(sopc)

        # Compose signal conveying functions
        signal_conveying_functions = []
        for parser in self.information_flow_parsers:
            ifp = parser.compositional_pass()
            if ifp is not None:
                signal_conveying_functions.append(ifp)

        # Compose generic attributes
        generic_attrs = self.generic_attribute_parser.compositional_pass(
            instrumentation.ProcessInstrumentationFunction
        )

        self.pif_obj = instrumentation.ProcessInstrumentationFunction(
            proteusId=self.pif_id,
            actuatingElectricalFunctions=filter_none(actuating_electrical_functions),
            actuatingFunctions=filter_none(actuating_functions),
            processSignalGeneratingFunctions=filter_none(process_signal_generating_functions),
            signalOffPageConnectors=filter_none(signal_off_page_connectors),
            signalConveyingFunctions=filter_none(signal_conveying_functions),
            **generic_attrs,
        )

        # Register the object
        self.register_object(self.pif_id, self.pif_obj)

        return self.pif_obj

    @redirect_errors_to_registry
    def control_pass(self) -> None:
        """Perform a control pass over the associations.

        Checks if associations of type "is logical start of" and "is logical end of" to
        InformationFlow objects have been made."""
        # Call super to call control pass on all submodules
        super().control_pass()

        # Skip pass if the reference object or ID is not available due to previous error
        if self.pif_id is None or self.pif_obj is None:
            self.register_error(
                *ErrorTemplates.skip_pass("control", "ProcessInstrumentationFunction")
            )
            return

        # Iterate through all association parsers and check if they are valid.
        for association_parser in self.association_parsers:
            if not association_parser.is_valid():
                # Log error and skip association
                self.register_error(
                    association_parser.get_error_message(),
                    level=ErrorLevels.ERROR,
                )
                continue

            # Check for associations of type "is logical start of" and "is logical end of"
            assoc_type = association_parser.get_type()
            if assoc_type in ["is logical start of", "is logical end of", "is a part of"]:
                associated_object = association_parser.get_referenced_item()
                assoc_id = association_parser.get_id()
                if not is_associated_with(self.pif_obj, associated_object):
                    # Log warning and try to add association in control pass
                    self.register_error(
                        *ErrorTemplates.no_assoc_ctrl("ProcessInstrumentationFunction", assoc_id)
                    )
                    try:
                        fld = add_by_inferring_type(self.pif_obj, associated_object)
                        # Log an info error if the association was added in control pass
                        self.register_error(
                            *ErrorTemplates.assoc_added_ctrl(
                                "ProcessInstrumentationFunction", assoc_id, fld
                            )
                        )
                    except ValueError as e:
                        # If the association cannot be added, log an error
                        self.register_error(
                            *ErrorTemplates.assoc_not_added_ctrl(
                                "ProcessInstrumentationFunction", assoc_id
                            ),
                            exception=e,
                        )
            else:
                self.register_error(
                    *ErrorTemplates.inval_assoc_type("ProcessInstrumentationFunction", assoc_type)
                )

    @redirect_errors_to_registry
    def drawing_pass(self) -> graphics.RepresentationGroup | None:
        """Perform a drawing pass to create a graphical representation of the component."""

        # Collect graphical representations from all submodules
        if not (self.pif_obj and self.pif_id):
            self.register_error(
                *ErrorTemplates.skip_pass("drawing", "ProcessInstrumentationFunction")
            )
            return

        # Partial groups and node_positions list for representation group
        groups = []
        node_positions = []

        # Process shape usage
        shape_usage = self.shape_usage_parser.drawing_pass()
        if shape_usage is not None:
            static = graphics.Static(elements=[shape_usage])
            groups.append(static)

        # Process labels
        labels = [parser.drawing_pass() for parser in self.label_parsers]
        labels = filter_none(labels)
        for label in labels:
            groups.append(label)

        # Process connection points and collect them in a dictionary
        connection_point_dict = {}
        connection_points = [parser.drawing_pass() for parser in self.connection_point_parsers]
        connection_points = filter_none(connection_points)
        for cp_entries in connection_points:
            connection_point_dict.update(cp_entries)

        # Convert dictionary values to node_positions list
        node_positions.extend(connection_point_dict.values())

        # Process information flow drawings
        information_flow_dwgs = [parser.drawing_pass() for parser in self.information_flow_parsers]
        information_flow_dwgs = filter_none(information_flow_dwgs)
        for if_dwg in information_flow_dwgs:
            groups.append(if_dwg)

        self.pif_dwg = graphics.RepresentationGroup(
            represents=self.pif_obj, groups=groups, nodePositions=node_positions
        )

        self.register_object(f"{self.pif_id}_dwg", self.pif_dwg)
        self.register_object(f"{self.pif_id}_cp_node_positions", connection_point_dict)

        return self.pif_dwg


class InstrumentationLoopFunctionParser(ParserModule):
    """Parser for InstrumentationLoopFunction elements in the DEXPI model.

    Parses InstrumentationLoopFunction elements into an instance of the InstrumentationLoopFunction
    in the compositional pass. Collects references to ProcessInstrumentationFunction in reference
    pass. No control pass is needed.

    Attributes
    ----------
    context : ModuleContext
        The context containing the ID-, and element stack, error-, and object registry.
    element : ET.Element
        The XML element containing the InstrumentationLoopFunction to be parsed.
    association_parsers : list[AssociationParser]
        A list of parsers for the associations related to the InstrumentationLoopFunction.
    generic_attribute_parser : GenericAttributeParser
        A parser for the generic attributes of the InstrumentationLoopFunction.
    ilf_id : str | None
        The ID of the InstrumentationLoopFunction being parsed. Set during compositional pass.
    ilf_obj : instrumentation.InstrumentationLoopFunction | None
        The InstrumentationLoopFunction object being constructed. Set during compositional pass.
    """

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        association_parsers: list[AssociationParser],
        generic_attribute_parser: GenericAttributeParser,
    ) -> None:
        """Initialize the InstrumentationLoopFunctionParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        element : ET.Element
            The XML element containing the InstrumentationLoopFunction to be parsed.
        association_parsers : list[AssociationParser]
            A list of parsers for the associations related to the InstrumentationLoopFunction.
        generic_attribute_parser : GenericAttributeParser
            A parser for the generic attributes of the InstrumentationLoopFunction.
        """
        super().__init__(context)
        self.element = element
        self.ilf_id = None
        self.ilf_obj = None

        # Set and register association parsers
        self.association_parsers = association_parsers
        self.register_submodule_list(association_parsers)

        # Set and register generic attribute parser
        self.generic_attribute_parser = generic_attribute_parser

    @redirect_errors_to_registry
    def compositional_pass(self) -> instrumentation.InstrumentationLoopFunction | None:
        """Parse the InstrumentationLoopFunction in the compositional pass.

        Composes all associations and generic attributes, and creates an instance of the
        InstrumentationLoopFunction class.

        Returns
        -------
        instrumentation.InstrumentationLoopFunction | None
            An instance of the InstrumentationLoopFunction class created from the parsed attributes,
            or None if an error occurred during parsing.
        """
        # Extract ID
        self.ilf_id = self.element.get("ID")
        if self.ilf_id is None:
            self.register_error(*ErrorTemplates.id_not_found("InstrumentationLoopFunction"))
            return None

        # Compose associations
        for association_parser in self.association_parsers:
            association_parser.compositional_pass()

        # Compose generic attributes
        generic_attrs = self.generic_attribute_parser.compositional_pass(
            instrumentation.InstrumentationLoopFunction
        )

        # Create the InstrumentationLoopFunction object
        self.ilf_obj = instrumentation.InstrumentationLoopFunction(
            proteusId=self.ilf_id, **generic_attrs
        )

        # Register the object
        self.register_object(self.ilf_id, self.ilf_obj)

        return self.ilf_obj

    @redirect_errors_to_registry
    def reference_pass(self) -> None:
        """Perform a reference pass over the InstrumentationLoopFunction.

        Establish connections to the associated process instrumentation functions by parsing the
        associations of type "is a collection including".
        """
        # Call super to call reference pass on all submodules
        super().reference_pass()

        # Skip reference pass if id or object are not available due to previous error in
        # compositional pass.
        if self.ilf_obj is None or self.ilf_id is None:
            self.register_error(
                *ErrorTemplates.skip_pass("reference", "InstrumentationLoopFunction")
            )
            return

        # Iterate through all association parsers and check if they are valid.
        pifs = []
        for association_parser in self.association_parsers:
            association_parser.reference_pass()
            if not association_parser.is_valid():
                # Log error and skip association
                self.register_error(
                    association_parser.get_error_message(),
                    level=ErrorLevels.ERROR,
                )
                continue

            # Check for associations of type "is a collection including"
            assoc_type = association_parser.get_type()
            if assoc_type == "is a collection including":
                associated_pif = association_parser.get_referenced_item()
                if not isinstance(associated_pif, instrumentation.ProcessInstrumentationFunction):
                    self.register_error(
                        f"Association of InstrumentationLoopFunction with  "
                        f"{association_parser.get_id()} is not a ProcessInstrumentationFunction. "
                        f"Skipping association.",
                        level=ErrorLevels.ERROR,
                    )
                    continue
                pifs.append(associated_pif)

            else:
                self.register_error(
                    *ErrorTemplates.inval_assoc_type("InstrumentationLoopFunction", assoc_type)
                )
                continue

        # Set the process instrumentation functions in the InstrumentationLoopFunction object
        self.ilf_obj.processInstrumentationFunctions = pifs


### DRAWING PARSERS ###
class CoordinateParser(ParserModule):
    """Parser for coordinate information in XML elements.

    This class processes coordinate data from XML elements and provides methods to extract coordinate (X,Y)."""

    def __init__(self, context: ModuleContext, element: ET.Element) -> None:
        """Initialize the PointParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        element : ET.Element
            The XML element that may contain coordinate information.
        """
        super().__init__(context)
        self.element = element
        self.coordinate_obj = None

    def compositional_pass(self) -> graphics.Point | None:
        """Parse the element to extract x and y values.

        Returns
        -------
        graphics.Point | None
            Point object with x and y values from the element or None if invalid
        """

        if self.element is None:
            # Register an error and return None if the element is missing
            self.register_error(
                message="Missing element for PointParser. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Parse x and y attributes
        if "X" not in self.element.attrib:
            self.register_error(
                message="Missing X attribute in element. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None
        else:
            x = float(self.element.get("X"))
        if "Y" not in self.element.attrib:
            self.register_error(
                message="Missing Y attribute in element. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None
        else:
            y = float(self.element.get("Y"))

        self.coordinate_obj = graphics.Point(x=x, y=y)

        return self.coordinate_obj


class PresentationParser(ParserModule):
    """Parser for presentation information in XML elements.
    This class processes presentation data from XML elements and provides methods to extract stroke
    and color information."""

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
    ) -> None:
        """Initialize the PresentationParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        element : ET.Element
            The XML element that may contain presentation information.
        """
        super().__init__(context)
        self.element = element
        self.presentation_obj = None

    @redirect_errors_to_registry
    def compositional_pass(self) -> graphics.Stroke | graphics.Color | None:
        """Perform a compositional pass over the presentation element.

        This method processes the presentation element to create either a Stroke or Color object.
        If the element contains both color and line properties, it creates a Stroke object.
        If the element only contains color properties, it creates a Color object.
        If the element contains only line properties, it creates a Stroke object with default color.
        If the element is None or contains no relevant attributes, None is returned.

        Returns
        -------
        graphics.Stroke | graphics.Color | None
            The constructed Stroke or Color object representing the presentation information or None if invalid
        """

        # If no element is provided, return None
        if self.element is None:
            self.register_error(
                message="Missing element for PresentationParser. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Check if color attributes are present in the presentation element
        has_color = all(attr in self.element.attrib for attr in ["R", "G", "B"])
        has_line_properties = (
            "LineWeight" in self.element.attrib and "LineType" in self.element.attrib
        )

        # If no relevant properties found, return None
        if not has_color and not has_line_properties:
            self.register_error(
                message="No color or line properties found in presentation element.",
                level=ErrorLevels.WARNING,
            )
            return None

        # Process color information if available
        color = None
        if has_color:
            # Parse RGB values and convert to integers in range 0-255
            # In some cases, values might be provided as floats in range 0-1
            r_value = float(self.element.get("R"))
            g_value = float(self.element.get("G"))
            b_value = float(self.element.get("B"))

            # Check if values are in 0-1 range and scale if needed
            if max(r_value, g_value, b_value) <= 1.0:
                r = int(r_value * 255)
                g = int(g_value * 255)
                b = int(b_value * 255)
            else:
                r = int(r_value)
                g = int(g_value)
                b = int(b_value)

            # Ensure values are within valid range
            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))

            color = graphics.Color(r=r, g=g, b=b)

        # Process line properties if available
        if has_line_properties:
            # Default values
            width = 1.0
            dash_style = graphics.DashStyle("Solid")

            # Get width if available
            if "LineWeight" in self.element.attrib:
                line_weight_value = self.element.get("LineWeight")

                # Check for empty string
                if line_weight_value == "":
                    self.register_error(
                        message="Empty string LineWeight value. Return Color only.",
                        level=ErrorLevels.WARNING,
                    )
                    self.presentation_obj = color
                    return self.presentation_obj

            # Get line type if available
            if "LineType" in self.element.attrib:
                line_type_value = self.element.get("LineType")

                # Check for empty string
                if line_type_value == "":
                    self.register_error(
                        message="Empty string LineType value. Return Color only.",
                        level=ErrorLevels.WARNING,
                    )
                    self.presentation_obj = color
                    return self.presentation_obj

                else:
                    try:
                        dash_style = bmt.resolve_enum_member(graphics.DashStyle, line_type_value)

                    except (ValueError, TypeError):
                        self.register_error(
                            message=f"Invalid LineType value '{line_type_value}'. Using 'Solid' as default.",
                            level=ErrorLevels.WARNING,
                        )
                        dash_style = graphics.DashStyle.Solid

            # Use default color (black) if no color is defined
            if color is None:
                color = graphics.Color(r=0, g=0, b=0)

            self.presentation_obj = graphics.Stroke(color=color, dashStyle=dash_style, width=width)

            return self.presentation_obj

        self.presentation_obj = color
        return self.presentation_obj


class PositionParser(ParserModule):
    """Parser for position information in XML elements.

    This class processes position data from XML elements and provides methods to extract position,
    rotation, and mirroring information. No reference or control pass is required.

    Attributes
    ----------
    context : ModuleContext
        The context containing the ID-, and element stack, error-, and object registry.
    element : ET.Element
        The XML element containing the position information to be parsed.
    """

    def __init__(self, context: ModuleContext, element: ET.Element) -> None:
        """Initialize the PositionParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        element : ET.Element
            The XML element that may contain position information.
        """
        super().__init__(context)
        self.element = element
        self.position_obj = None

    def compositional_pass(self) -> tuple | None:
        """Parse position information from the element.

        Returns
        -------
        tuple | None
            (position, rotation, is_mirrored) where:
            - position is a Point object representing the location
            - rotation is a float representing the rotation angle in degrees
            - is_mirrored is a boolean indicating if the element is mirrored
            Returns None if no position data is found or if parsing fails
        """

        position_element = self.element
        is_position = position_element.tag == "Position"

        if not is_position:
            self.register_error(
                message="No Position element found. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Initialize with default values
        position = None
        rotation = None
        is_mirrored = False

        # Get location (x, y coordinates)
        location_element = position_element.find("Location")
        if location_element is not None:
            # Check for X attribute
            if "X" not in location_element.attrib:
                self.register_error(
                    message="Missing X attribute in Location element. Returning None.",
                    level=ErrorLevels.ERROR,
                )
                return None
            else:
                x_coord = float(location_element.get("X"))

            # Check for Y attribute
            if "Y" not in location_element.attrib:
                self.register_error(
                    message="Missing Y attribute in Location element. Returning None.",
                    level=ErrorLevels.ERROR,
                )
                return None
            else:
                y_coord = float(location_element.get("Y"))
            position = graphics.Point(x=x_coord, y=y_coord)
        else:
            self.register_error(
                message="No Location element found. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Calculate rotation from Axis and Reference vectors
        axis_element = position_element.find("Axis")
        reference_element = position_element.find("Reference")
        if axis_element is not None and reference_element is not None:
            # Get axis vector Z component (we only need this one)
            if "Z" not in axis_element.attrib:
                self.register_error(
                    message="Missing Z attribute in Axis element. Returning None.",
                    level=ErrorLevels.ERROR,
                )
                return None
            else:
                axis_z = float(axis_element.get("Z"))

            # Get reference vector X and Y for angle calculation
            if "X" not in reference_element.attrib:
                self.register_error(
                    message="Missing X attribute in Reference element. Returning None.",
                    level=ErrorLevels.ERROR,
                )
                return None
            else:
                ref_x = float(reference_element.get("X"))
            if "Y" not in reference_element.attrib:
                self.register_error(
                    message="Missing Y attribute in Reference element. Returning None.",
                    level=ErrorLevels.ERROR,
                )
                return None
            else:
                ref_y = float(reference_element.get("Y"))

            # Calculate rotation - assuming Z axis is up and rotation is in XY plane
            if axis_z != 0 and (ref_x != 0 or ref_y != 0):
                # Calculate angle in radians and convert to degrees
                # We subtract from 360 to convert CCW to CW rotation and normalize to 0-360
                rotation = (360 - math.degrees(math.atan2(ref_y, ref_x))) % 360
                # Check for mirroring (if Z component of axis is negative)
                if axis_z < 0:
                    is_mirrored = True

        self.position_obj = position, rotation, is_mirrored

        return self.position_obj


class ScaleParser(ParserModule):
    """Parser for scale information in XML elements.

    This class processes scale data from XML elements and provides methods to extract scale factors
    and detect mirroring. No reference or control pass is required.

    Attributes
    ----------
    context : ModuleContext
        The context containing the ID-, and element stack, error-, and object registry.
    element : ET.Element
        The XML element containing the scale information to be parsed.
    """

    def __init__(self, context: ModuleContext, element: ET.Element) -> None:
        """Initialize the ScaleParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        element : ET.Element
            The XML element that may contain scale information.
        """
        super().__init__(context)
        self.element = element
        self.scale_obj = None

    def compositional_pass(self) -> tuple | None:
        """Parse scale information from the element.

        Returns
        -------
        tuple | None
            (scale_x, scale_y, is_mirrored_scale) where:
            - scale_x is a float representing the x scale factor
            - scale_y is a float representing the y scale factor
            - is_mirrored_scale is a boolean indicating if scale indicates mirroring
            Returns None if no scale data is found or parsing fails
        """

        # Initialize with default values
        scale_x = None
        scale_y = None
        is_mirrored_scale = False

        if self.element is None:
            self.register_error(
                message="No Scale element found. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        if self.element.tag != "Scale":
            self.register_error(
                message="Element is not a Scale element. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Check for X attribute
        if "X" not in self.element.attrib:
            self.register_error(
                message="Missing X attribute in Scale element. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None
        else:
            scale_x = float(self.element.get("X"))

        # Check for Y attribute
        if "Y" not in self.element.attrib:
            self.register_error(
                message="Missing Y attribute in Scale element. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None
        else:
            scale_y = float(self.element.get("Y"))

        # Detect mirroring from negative scale values
        if scale_x < 0 or scale_y < 0:
            is_mirrored_scale = True

            # Use absolute values for scale
            scale_x = abs(scale_x)
            scale_y = abs(scale_y)

        self.scale_obj = scale_x, scale_y, is_mirrored_scale

        return self.scale_obj


### PARSE GRAPHICAL PRIMITIVES ###
class GraphicalPrimitiveParser(ParserModule):
    """Parent parser for graphical primitive information in XML elements.

    Used for unified type hinting.
    """


class PolylineParser(GraphicalPrimitiveParser):
    """Parser for polyline information in XML elements.

    This class processes polyline data from XML elements and provides methods to extract
    polyline properties such as points and stroke information.
    """

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        presentation_parsers: list[PresentationParser],
        coordinate_parsers: list[CoordinateParser],
    ) -> None:
        """Initialize the PolylineParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        element : ET.Element
            The XML element that may contain polyline information.
        presentation_parsers : list[PresentationParser]
            List of presentation parsers to use for parsing presentation (stroke) information.
        coordinate_parsers : list[CoordinateParser]
            List of coordinate parsers to use for parsing coordinate (point) information.
        """
        super().__init__(context)
        self.element = element
        self.polyline_obj = None

        # Initialize parsers for presentation
        self.presentation_parsers = presentation_parsers
        self.register_submodule_list(presentation_parsers)

        # Initialize parser for coordinates
        self.coordinate_parsers = coordinate_parsers
        self.register_submodule_list(coordinate_parsers)

    @redirect_errors_to_registry
    def compositional_pass(self) -> graphics.PolyLine | None:
        """Perform a compositional pass over the polyline element.

        Returns
        -------
        graphics.PolyLine | None
            The constructed PolyLine object representing the polyline element or None if invalid
        """

        # If no element is provided, return None
        if self.element is None:
            self.register_error(
                message="Missing element for PolylineParser. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Parse presentation data for presentation
        if len(self.presentation_parsers) > 1:
            self.register_error(
                f"Found {len(self.presentation_parsers)} Presentation elements for PolyLine, "
                "expected at most 1. Using the first one.",
                level=ErrorLevels.WARNING,
            )
        elif len(self.presentation_parsers) == 0:
            return None

        presentation_parser = self.presentation_parsers[0] if self.presentation_parsers else None

        presentation = presentation_parser.compositional_pass()
        if presentation is None:
            self.register_error(
                message="Invalid stroke for PolyLine. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Parse coordinates into Point objects
        coordinates = []
        for coord_parser in self.coordinate_parsers:
            coordinate = coord_parser.compositional_pass()
            if coordinate is not None:
                coordinates.append(coordinate)

        # If no valid points were found, return None
        if not coordinates:
            self.register_error(
                message="No valid coordinates found for PolyLine. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Create and return the PolyLine object
        self.polyline_obj = graphics.PolyLine(points=coordinates, stroke=presentation)
        return self.polyline_obj


class PolygonParser(GraphicalPrimitiveParser):
    """Parser for polygon information in XML elements.

    This class processes polygon data from XML elements and provides methods to extract
    polygon properties such as points, stroke information, and fill style.
    """

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        presentation_parsers: list[PresentationParser],
        coordinate_parsers: list[CoordinateParser],
    ) -> None:
        """Initialize the PolygonParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        element : ET.Element
            The XML element that may contain polygon information.
        presentation_parsers : list[PresentationParser]
            List of presentation parsers to use for parsing presentation (stroke) information.
        coordinate_parsers : list[CoordinateParser]
            List of coordinate parsers to use for parsing coordinate (point) information.
        """
        super().__init__(context)
        self.element = element
        self.polygon_obj = None

        # Initialize parser for stroke
        if len(presentation_parsers) > 1:
            self.register_error(
                f"Found {len(presentation_parsers)} Presentation elements for Polygon, "
                "expected at most 1. Using the first one.",
                level=ErrorLevels.WARNING,
            )
        self.presentation_parser = presentation_parsers[0] if presentation_parsers else None
        if self.presentation_parser is not None:
            self.register_submodule(self.presentation_parser)

        # Initialize parser for coordinates
        self.coordinate_parsers = coordinate_parsers
        self.register_submodule_list(coordinate_parsers)

    @redirect_errors_to_registry
    def compositional_pass(self) -> graphics.Polygon | None:
        """Perform a compositional pass over the polygon element.

        This method processes the polygon element to create a Polygon object,
        combining points, stroke information, and fill style.

        Returns
        -------
        graphics.Polygon | None
            The constructed Polygon object representing the polygon element or None if invalid
        """

        # If no element is provided, return None
        if self.element is None:
            self.register_error(
                message="Missing element for PolygonParser. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Get the first Polygon element
        poly_element = self.element.find("Polygon")
        if poly_element is None:
            self.register_error(
                message="No Polygon element found in the provided XML element. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Parse presentation data for stroke
        presentation = self.presentation_parser.compositional_pass()
        if presentation is None:
            self.register_error(
                message="Invalid stroke for Polygon. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Parse coordinates into Point objects
        coordinates = []
        for coord_parser in self.coordinate_parsers:
            coordinate = coord_parser.compositional_pass()
            if coordinate is not None:
                coordinates.append(coordinate)

        # Parse fill style from the Polygon element
        fill_style = graphics.FillStyle.Solid  # Default fill style
        fill_style_str = poly_element.get("Filled")
        fill_style_enum = bmt.resolve_enum_member(graphics.FillStyle, fill_style_str)

        if fill_style_str is not None:
            try:
                fill_style = graphics.FillStyle(fill_style_enum)
            except Exception:
                self.register_error(
                    message=f"Invalid Filled attribute '{fill_style_str}'. Using default.",
                    level=ErrorLevels.WARNING,
                )

        # Create and return the Polygon object
        self.polygon_obj = graphics.Polygon(
            points=coordinates, stroke=presentation, fillStyle=fill_style
        )
        return self.polygon_obj


class TextParser(GraphicalPrimitiveParser):
    """Parser for text information in XML elements.

    This class processes text data from XML elements and provides methods to extract text properties
    such as content, font, size, position, rotation, alignment, and color.
    """

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        position_parsers: list[PositionParser],
        presentation_parsers: list[PresentationParser],
    ) -> None:
        """Initialize the TextParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        element : ET.Element
            The XML element that may contain text information.
        position_parsers : list[PositionParser]
            List of position parsers to use for parsing position information.
        presentation_parsers : list[PresentationParser]
            List of presentation parsers to use for parsing presentation (color) information.
        """
        super().__init__(context)
        self.element = element
        self.text_obj = None

        # Initialize parser for position - using PositionParser for position, rotation, and mirroring
        if len(position_parsers) > 1:
            self.register_error(
                f"Found {len(position_parsers)} Position elements for Text, "
                "expected at most 1. Using the first one.",
                level=ErrorLevels.WARNING,
            )
        self.position_parser = position_parsers[0] if position_parsers else None
        if self.position_parser is not None:
            self.register_submodule(self.position_parser)

        # Initialize parser for presentation
        if len(presentation_parsers) > 1:
            self.register_error(
                f"Found {len(presentation_parsers)} Presentation elements for Text, "
                "expected at most 1. Using the first one.",
                level=ErrorLevels.WARNING,
            )
        self.presentation_parser = presentation_parsers[0] if presentation_parsers else None
        if self.presentation_parser is not None:
            self.register_submodule(self.presentation_parser)

    @redirect_errors_to_registry
    def compositional_pass(self) -> graphics.Text | None:
        """Perform a compositional pass over the text element.

        This method processes the text element to create a Text object,
        combining text content, font, size, position, rotation, alignment, and color information.

        Returns
        -------
        graphics.Text | None
            The constructed Text object representing the text element or None if invalid
        """

        if self.element is None:
            # Return None if no element is provided
            self.register_error(
                message="Missing element for TextParser. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        is_text = self.element.tag == "Text"
        if is_text is False:
            self.register_error(
                message="No Text element found in the provided XML element. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Extract basic text properties
        if "String" not in self.element.attrib:
            self.register_error(
                message="Missing String attribute in Text element.",
                level=ErrorLevels.ERROR,
            )

            return None

        else:
            text_string = self.element.get("String")

        if "Font" not in self.element.attrib:
            self.register_error(
                message="Missing Font attribute in Text element.",
                level=ErrorLevels.ERROR,
            )

        else:
            font = self.element.get("Font")

        # Use Height for size, with Width as a fallback if available
        if "Height" not in self.element.attrib:
            self.register_error(
                message="Missing Height attribute in Text element. Returning None.",
                level=ErrorLevels.ERROR,
            )

        else:
            try:
                size = float(self.element.get("Height"))
            except (ValueError, TypeError):
                self.register_error(
                    message="Invalid Height attribute in Text element. Returning None.",
                    level=ErrorLevels.ERROR,
                )

        # Parse TextAngle if available
        rotation = None
        if "TextAngle" in self.element.attrib:
            try:
                rotation = float(self.element.get("TextAngle"))
            except (ValueError, TypeError):
                self.register_error(
                    message="Invalid TextAngle attribute in Text element. Returning None.",
                    level=ErrorLevels.ERROR,
                )

        # Parse justification/alignment
        alignment = None  # Default alignment
        justification = self.element.get("Justification")
        if justification is not None:
            try:
                justification_str = bmt.resolve_enum_member(graphics.TextAlignment, justification)
                alignment = graphics.TextAlignment(justification_str)
            except Exception:
                self.register_error(
                    message=f"Invalid Justification attribute '{justification}'. Using default.",
                    level=ErrorLevels.WARNING,
                )

        # Parse position using PositionParser to get position, rotation, and mirroring
        position_data = self.position_parser.compositional_pass()
        if position_data is None:
            self.register_error(
                message="Invalid Position in Text element. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        position, position_rotation, _ = position_data

        # Use the TextAngle if available, otherwise fall back to position rotation
        if "TextAngle" not in self.element.attrib:
            rotation = position_rotation

        # Extract color from presentation if available
        presentation_result = self.presentation_parser.compositional_pass()
        if presentation_result is None:
            self.register_error(
                message="Invalid presentation in Text element. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Check if the presentation result is a Color or a Stroke
        if isinstance(presentation_result, graphics.Color):
            color = presentation_result
        elif isinstance(presentation_result, graphics.Stroke):
            color = presentation_result.color
        else:
            self.register_error(
                message="Unknown presentation type in Text element. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Create template if format specification is available
        template = None
        format_spec_element = self.element.find("TextStringFormatSpecification")
        if format_spec_element is not None:
            # Create a new TextTemplate object
            template = graphics.TextTemplate(fragments=[])

            # Process all ObjectAttributesReference elements
            ref_elements = format_spec_element.findall("ObjectAttributesReference")
            if ref_elements:
                for ref_element in ref_elements:
                    # Create a TextTemplateFragment for each reference
                    fragment = graphics.TextTemplateFragment()
                    template.fragments.append(fragment)

        # Create and return the Text object
        self.text_obj = graphics.Text(
            text=text_string,
            font=font,
            size=size,
            position=position,
            rotation=rotation,
            alignment=alignment,
            color=color,
            template=template,
        )

        return self.text_obj


### Graphical Primitives to be continued ###
class ConnectorLineParser(GraphicalPrimitiveParser):
    """Parser for connector line information in XML elements.

    This class processes connector line data from XML elements and provides methods to extract
    connector line properties such as points and stroke information.
    """

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        presentation_parsers: list[PresentationParser],
        coordinate_parsers: list[CoordinateParser],
    ) -> None:
        """Initialize the ConnectorLineParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        element : ET.Element
            The XML element that may contain connector line information.
        presentation_parsers : list[PresentationParser]
            List of presentation parsers to use for parsing presentation (stroke) information.
        coordinate_parsers : list[CoordinateParser]
            List of coordinate parsers to use for parsing coordinate (point) information.
        """
        super().__init__(context)
        self.element = element
        self.connector_line_obj = None

        # Initialize parsers for stroke
        self.presentation_parsers = presentation_parsers
        self.register_submodule_list(presentation_parsers)

        # Initialize parser for coordinates
        self.coordinate_parsers = coordinate_parsers
        self.register_submodule_list(coordinate_parsers)

    @redirect_errors_to_registry
    def compositional_pass(self) -> graphics.ConnectorLine | None:
        """Perform a compositional pass over the connector line element.

        This method processes the connector line element to create a ConnectorLine object,
        combining points and stroke information.

        Returns
        -------
        graphics.ConnectorLine | None
            The constructed ConnectorLine object representing the connector line element or None if invalid
        """

        # If no element is provided, return None
        if self.element is None:
            self.register_error(
                message="Missing element for ConnectorLineParser. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Parse presentation data for stroke
        if len(self.presentation_parsers) > 1:
            self.register_error(
                f"Found {len(self.presentation_parsers)} Presentation elements for ConnectorLine, "
                "expected at most 1. Using the first one.",
                level=ErrorLevels.WARNING,
            )
        elif len(self.presentation_parsers) == 0:
            return None

        presentation_parser = self.presentation_parsers[0]
        stroke = presentation_parser.compositional_pass()
        if stroke is None:
            self.register_error(
                message="Invalid stroke for ConnectorLine. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Parse coordinates into Point objects
        coordinates = []
        for coord_parser in self.coordinate_parsers:
            coordinate = coord_parser.compositional_pass()
            if coordinate is not None:
                coordinates.append(coordinate)

        # If no valid points were found, return None
        if not coordinates:
            self.register_error(
                message="No valid coordinates found for ConnectorLine. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Create and return the ConnectorLine object
        self.connector_line_obj = graphics.ConnectorLine(points=coordinates, stroke=stroke)
        return self.connector_line_obj


class EllipseParser(GraphicalPrimitiveParser):
    """Parser for ellipse information in XML elements.

    This class processes ellipse data from XML elements and provides methods to extract
    ellipse properties such as center point, radii, stroke information, and fill style.
    """

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        presentation_parsers: list[PresentationParser],
        position_parsers: list[PositionParser],
    ) -> None:
        """Initialize the EllipseParser with the XML element and context.
        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        element : ET.Element
            The XML element that may contain ellipse information.
        presentation_parsers : list[PresentationParser]
            List of presentation parsers to use for parsing presentation (stroke) information.
        position_parsers : list[PositionParser]
            List of position parsers to use for parsing position information.
        """
        super().__init__(context)
        self.element = element
        self.ellipse_obj = None

        # Initialize parsers for presentation (stroke)
        self.presentation_parsers = presentation_parsers
        self.register_submodule_list(presentation_parsers)

        # Initialize parsers for position
        self.position_parsers = position_parsers
        self.register_submodule_list(position_parsers)

    @redirect_errors_to_registry
    def compositional_pass(self) -> graphics.Ellipse | None:
        """Perform a compositional pass over the ellipse or circle element.

        This method processes the element to create an Ellipse object,
        combining center point, radii, stroke information, and fill style.

        Returns
        -------
        graphics.Ellipse | None
            The constructed Ellipse object representing the ellipse or circle element or None if invalid
        """

        # If no element is provided, return None
        if self.element is None:
            self.register_error(
                message="Missing element for EllipseParser. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Try to find Ellipse or Circle element
        element_tag = self.element.tag
        is_ellipse = element_tag == "Ellipse"
        is_circle = element_tag == "Circle"

        if not (is_ellipse or is_circle):
            self.register_error(
                message="No Ellipse or Circle element found in the provided XML element. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Parse presentation data for stroke
        if len(self.presentation_parsers) > 1:
            self.register_error(
                f"Found {len(self.presentation_parsers)} Presentation elements for Ellipse, "
                "expected at most 1. Using the first one.",
                level=ErrorLevels.WARNING,
            )
        elif len(self.presentation_parsers) == 0:
            return None

        self.presentation_parser = self.presentation_parsers[0]

        stroke = self.presentation_parser.compositional_pass()
        if stroke is None:
            self.register_error(
                message="Invalid stroke information for Ellipse. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Parse position data for center and rotation
        if len(self.position_parsers) > 1:
            self.register_error(
                message=f"Found {len(self.position_parsers)} Position elements for Ellipse, "
                "expected at most 1. Using the first one.",
                level=ErrorLevels.WARNING,
            )
        elif len(self.position_parsers) == 0:
            return None

        self.position_parser = self.position_parsers[0]

        position_data = self.position_parser.compositional_pass()
        if position_data is None:
            self.register_error(
                message="Invalid position information for Ellipse. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Parse fillStyle with default value
        fill_style = graphics.FillStyle.Solid  # Default fill style
        fill_style_str = self.element.get("Filled")
        if fill_style_str is not None:
            try:
                fill_style_enum = bmt.resolve_enum_member(graphics.FillStyle, fill_style_str)
                fill_style = graphics.FillStyle(fill_style_enum)
            except Exception:
                self.register_error(
                    message=f"Invalid Filled attribute '{fill_style_str}'. Using default.",
                    level=ErrorLevels.WARNING,
                )

        position, rotation, _ = position_data
        # If position is None, return None
        if position is None:
            self.register_error(
                message="Invalid position for Ellipse. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        if is_ellipse:
            # Parse primary axis and secondary axis
            if "PrimaryAxis" not in self.element.attrib:
                self.register_error(
                    message="Missing PrimaryAxis attribute in Ellipse element. Returning None.",
                    level=ErrorLevels.ERROR,
                )
                return None

            try:
                primary_axis = float(self.element.get("PrimaryAxis"))
            except (TypeError, ValueError):
                self.register_error(
                    message="Invalid PrimaryAxis attribute in Ellipse element. Returning None.",
                    level=ErrorLevels.ERROR,
                )
                return None

            if "SecondaryAxis" not in self.element.attrib:
                self.register_error(
                    message="Missing SecondaryAxis attribute in Ellipse element. Returning None.",
                    level=ErrorLevels.ERROR,
                )
                return None

            try:
                secondary_axis = float(self.element.get("SecondaryAxis"))
            except (TypeError, ValueError):
                self.register_error(
                    message="Invalid SecondaryAxis attribute in Ellipse element. Returning None.",
                    level=ErrorLevels.ERROR,
                )
                return None

            # Compose and return the Ellipse object
            self.ellipse_obj = graphics.Ellipse(
                center=position,
                fillStyle=fill_style,
                horizontalSemiAxis=primary_axis,
                verticalSemiAxis=secondary_axis,
                rotation=rotation,
                stroke=stroke,
            )
            return self.ellipse_obj

        else:  # Circle element
            # Parse radius
            if "Radius" not in self.element.attrib:
                self.register_error(
                    message="Missing Radius attribute in Circle element. Returning None.",
                    level=ErrorLevels.ERROR,
                )
                return None
            try:
                radius = float(self.element.get("Radius"))
            except (TypeError, ValueError):
                self.register_error(
                    message="Invalid Radius attribute in Circle element. Returning None.",
                    level=ErrorLevels.ERROR,
                )
                return None

            # Compose and return the Ellipse object as a circle (equal axes)
            self.ellipse_obj = graphics.Ellipse(
                center=position,
                fillStyle=fill_style,
                horizontalSemiAxis=radius,
                verticalSemiAxis=radius,
                rotation=rotation,
                stroke=stroke,
            )
            return self.ellipse_obj


class EllipseArcParser(GraphicalPrimitiveParser):
    """Parser for ellipse arc information in XML elements.

    This class processes ellipse arc data from XML elements and provides methods to extract
    ellipse arc properties such as center point, radii, start and end angles, stroke information, and fill style.
    """

    def __init__(
        self, context: ModuleContext, element: ET.Element, ellipse_parsers: list[EllipseParser]
    ) -> None:
        """Initialize the EllipseArcParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        element : ET.Element
            The XML element that may contain ellipse arc information.
        ellipse_parsers : list[EllipseParser]
            List of ellipse parsers to use for parsing ellipse information.
        """
        super().__init__(context)
        self.element = element
        self.ellipse_arc_obj = None

        # Initialize parser for center point
        self.ellipse_parsers = ellipse_parsers
        self.register_submodule_list(ellipse_parsers)

    @redirect_errors_to_registry
    def compositional_pass(self) -> graphics.EllipseArc | None:
        """Perform a compositional pass over the ellipse arc element.
        This method processes the ellipse arc element to create an EllipseArc object,
        combining center point, radii, start and end angles, stroke information, and fill style.

        Returns
        -------
        graphics.EllipseArc | None
            The constructed EllipseArc object representing the ellipse arc element or None if invalid
        """

        # If no element is provided, return None
        if self.element is None:
            self.register_error(
                message="Missing element for EllipseArcParser. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Get the first EllipseArc element
        element_tag = self.element.tag
        is_trimmed_curve = element_tag == "TrimmedCurve"

        if not is_trimmed_curve:
            self.register_error(
                message="No TrimmedCurve element found in the provided XML elemen. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Check if StartAngle attribute exists
        if "StartAngle" not in self.element.attrib:
            self.register_error(
                message="Missing StartAngle attribute in TrimmedCurve element. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Parse start angle
        try:
            start_angle = float(self.element.get("StartAngle"))
        except (TypeError, ValueError):
            self.register_error(
                message="Invalid StartAngle attribute in TrimmedCurve element. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Check if EndAngle attribute exists
        if "EndAngle" not in self.element.attrib:
            self.register_error(
                message="Missing EndAngle attribute in TrimmedCurve element. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Parse end angle
        try:
            end_angle = float(self.element.get("EndAngle"))
        except (TypeError, ValueError):
            self.register_error(
                message="Invalid EndAngle attribute in TrimmedCurve element. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Parse the ellipse using EllipseParser
        if len(self.ellipse_parsers) > 1:
            self.register_error(
                f"Found {len(self.ellipse_parsers)} Ellipse/Circle elements for EllipseArc, "
                "expected at most 1. Using the first one.",
                level=ErrorLevels.WARNING,
            )
        elif len(self.ellipse_parsers) == 0:
            return None
        ellipse_parser = self.ellipse_parsers[0]

        ellipse = ellipse_parser.compositional_pass()
        if ellipse is None:
            self.register_error(
                message="Failed to parse ellipse for EllipseArc. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Compose and return the EllipseArc object
        self.ellipse_arc_obj = graphics.EllipseArc(
            center=ellipse.center,
            endAngle=end_angle,
            horizontalSemiAxis=ellipse.horizontalSemiAxis,
            rotation=ellipse.rotation,
            startAngle=start_angle,
            stroke=ellipse.stroke,
            verticalSemiAxis=ellipse.verticalSemiAxis,
        )
        return self.ellipse_arc_obj


class ShapeParser(ParserModule):
    """Parser for Shape elements in XML.

    This class processes Shape data from XML elements and uses GraphicalPrimitiveParser
    to extract shape information, creating a Shape object.
    """

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        generic_attribute_parser: GenericAttributeParser,
        graphical_primitive_parsers: list[GraphicalPrimitiveParser],
    ) -> None:
        """Initialize the ShapeParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        element : ET.Element
            The XML element that contains shape information.
        generic_attribute_parser : GenericAttributeParser
            The parser to use for parsing generic attributes.
        graphical_primitive_parsers : list[GraphicalPrimitiveParser]
            List of parsers for graphical primitives (PolyLine, Polygon, Ellipse, etc.).
        """
        super().__init__(context)
        self.element = element
        self.shape_obj = None

        # Initialize parser for generic attributes
        self.generic_attribute_parser = generic_attribute_parser
        self.register_submodule(generic_attribute_parser)

        # Initialize parsers for graphical primitives
        self.graphical_primitive_parsers = graphical_primitive_parsers
        self.register_submodule_list(graphical_primitive_parsers)

    @redirect_errors_to_registry
    def compositional_pass(self) -> graphics.Shape | None:
        """Perform a compositional pass over the shape element.

        This method processes the shape element to create a Shape object,
        combining polylines, polygons, ellipses, and texts.

        Returns
        -------
        graphics.Shape | None
            The constructed Shape object representing the shape element or None if invalid
        """

        # Skip pass if element is not available
        if self.element is None:
            self.register_error(
                message="Missing element for ShapeParser. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Extract ID and name attributes
        id_attr = self.element.get("ID")
        if id_attr is None:
            self.register_error(
                message="Missing ID attribute in Shape element. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Determine the appropriate shape class from the element's tag
        # Example: "PipingComponent" -> "PipingComponentShape"
        shape_class_name = None
        element_tag = self.element.tag
        if element_tag:
            # Handle special case for Equipment tag
            if element_tag == "Equipment":
                shape_class_name = "TaggedPlantItemShape"
            else:
                # Add "Shape" suffix to the element tag
                shape_class_name = f"{element_tag}Shape"

            # Check if this class name exists in graphics module
            if not hasattr(graphics, shape_class_name):
                self.register_error(
                    message=f"Shape class {shape_class_name} not found in graphics module for tag {element_tag}, using default Shape",
                    level=ErrorLevels.ERROR,
                )
                shape_class_name = None

        # Default to Shape if we couldn't determine a specific class
        shape_class = getattr(graphics, shape_class_name) if shape_class_name else graphics.Shape

        # Extract ComponentName attribute - this will be the shape name
        component_name = self.element.get("ComponentName")
        if component_name is None:
            self.register_error(
                message=f"Missing ComponentName attribute in Shape element with ID {id_attr}. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Extract generic attributes using GenericAttributeParser
        generic_attributes = self.generic_attribute_parser.compositional_pass(graphics.Shape)

        # Extract the symbol registration number if available
        symbol_registration_number = generic_attributes.get("symbolRegistrationNumber")

        # Parse all graphical primitives
        primitives = []
        for primitive_parser in self.graphical_primitive_parsers:
            primitive = primitive_parser.compositional_pass()
            if primitive is not None:
                primitives.append(primitive)

        # Check if we have any primitives
        if not primitives:
            self.register_error(
                message=f"No valid primitives found in Shape with ID {id_attr}. Returning None.",
                level=ErrorLevels.WARNING,
            )
            # Continue anyway since a shape can be empty

        # Create and return the Shape object using the determined shape class
        self.shape_obj = shape_class(
            proteusId=id_attr,
            name=component_name,
            symbolRegistrationNumber=symbol_registration_number,
            primitives=primitives,
        )
        # Register the shape in the object registry with its ID for reference by other elements
        self.context.object_registry.register_object(id_attr, self.shape_obj)
        return self.shape_obj


class ShapeCatalogueParser(ParserModule):
    """Parser for ShapeCatalogue elements in XML.

    This class processes ShapeCatalogue data from XML elements and uses ShapeParser to extract
    shape information for each Equipment element, creating a ShapeCatalogue object.
    """

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        shape_parsers: list[ShapeParser],
    ) -> None:
        """Initialize the ShapeCatalogueParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        element : ET.Element
            The XML element that contains shape catalogue information.
        shape_parsers : Type[ShapeParser]
            The parser class to use for parsing shape information.
        """
        super().__init__(context)
        self.element = element
        self.shape_catalogue_obj = None

        # Initialize parser for shapes
        self.shape_parsers = shape_parsers
        self.register_submodule_list(shape_parsers)

    @redirect_errors_to_registry
    def compositional_pass(self) -> graphics.ShapeCatalogue | None:
        """Perform a compositional pass over the ShapeCatalogue element.

        This method processes the ShapeCatalogue element to create a ShapeCatalogue object,
        parsing all Equipment elements as shapes.

        Returns
        -------
        graphics.ShapeCatalogue | None
            The constructed ShapeCatalogue object representing the shape catalogue or None if invalid
        """

        # Skip pass if element is not available
        if self.element is None:
            self.register_error(
                message="Missing element for ShapeCatalogueParser. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Extract ID and name attributes
        name = self.element.get("Name")
        if name is None:
            self.register_error(
                message="Missing Name attribute in ShapeCatalogue element. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Instantiate empty components
        shapes = []

        for shape_parser in self.shape_parsers:
            shape = shape_parser.compositional_pass()
            if shape is not None:
                shapes.append(shape)

        # Check if we have any shapes
        if not shapes:
            self.register_error(
                message="No valid shapes found in ShapeCatalogue. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Create and return the ShapeCatalogue object
        self.shape_catalogue_obj = graphics.ShapeCatalogue(
            name=name,
            shapes=shapes,
        )
        return self.shape_catalogue_obj


class ShapeUsageParser(ParserModule):
    """Parser for ShapeUsage information in XML elements."""

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        position_parsers: list[PositionParser],
        scale_parsers: list[ScaleParser],
    ) -> None:
        """Initialize the ShapeUsageParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        element : ET.Element
            The XML element that may contain ShapeUsage information.
        position_parsers : list[PositionParser]
            List of position parsers to use for parsing position information.
        scale_parsers : list[ScaleParser]
            List of scale parsers to use for parsing scale information.
        """
        super().__init__(context)
        self.element = element
        self.shape_usage_obj = None

        # Initialize parsers for position
        self.position_parsers = position_parsers
        self.register_submodule_list(position_parsers)

        # Initialize parser for scale
        self.scale_parsers = scale_parsers
        self.register_submodule_list(scale_parsers)

    def compositional_pass(self) -> None:
        """ShapeUsageParser does not implement compositional_pass, as the drawing object is created in the ShapeCatalogueParser.
        In this parser, the drawing information is stich together with shape usage information (position, rotation, scale, mirroring) in the drawing_pass.

        compositional_pass need to be here as it is an abstract method in the parent class.
        """
        pass

    @redirect_errors_to_registry
    def drawing_pass(self) -> graphics.ShapeUsage | None:
        """Perform a drawing pass over the ShapeUsage element.

        This method processes the ShapeUsage element to create a ShapeUsage object,
        combining position, rotation, scale, and mirroring information.

        Parameters
        ----------
        shape_obj : graphics.Shape, optional
            Shape object to reference in the ShapeUsage

        Returns
        -------
        graphics.ShapeUsage | None
            The constructed ShapeUsage object representing the shape usage information or None if invalid
        """

        # If position is none return None
        if len(self.position_parsers) > 1:
            self.register_error(
                f"Found {len(self.position_parsers)} Position elements for ShapeUsage, "
                "expected at most 1. Using the first one.",
                level=ErrorLevels.WARNING,
            )
        elif len(self.position_parsers) == 0:
            return None
        position_parser = self.position_parsers[0]

        # Extract scale information. If missing or faulty, use default scale 1,1,false
        if len(self.scale_parsers) > 1:
            self.register_error(
                f"Found {len(self.scale_parsers)} Scale elements for ShapeUsage, "
                "expected at most 1. Using the first one.",
                level=ErrorLevels.WARNING,
            )
        elif len(self.scale_parsers) == 0:
            scale_data = (1.0, 1.0, False)
        else:
            scale_parser = self.scale_parsers[0]
            scale_data = scale_parser.compositional_pass()
            if scale_data is None:
                self.register_error(
                    message="Invalid scale information for ShapeUsage. Using default scale 1,1,false.",
                    level=ErrorLevels.ERROR,
                )
                scale_data = (1.0, 1.0, False)

        component_shape_name = self.element.get("ComponentName")
        if component_shape_name is None:
            self.register_error("ComponentName not found for Equipment", level=ErrorLevels.WARNING)
            return None

        # Find the appropriate shape in the ShapeCatalogue based on ComponentName
        shape_obj = None

        # Get all ShapeCatalogue objects from the context (from PlantModelParser)
        shape_catalogue_objs = [
            obj
            for obj in self.context.object_registry.objects.values()
            if isinstance(obj, graphics.Shape)
        ]

        # Look for a Shape with matching name in any ShapeCatalogue
        for shape in shape_catalogue_objs:
            if shape.name == component_shape_name:
                shape_obj = shape
                break

        if not shape_obj:
            self.register_error(
                f"Shape with name '{component_shape_name}' not found in any ShapeCatalogue",
                level=ErrorLevels.WARNING,
            )

        # Parse position, rotation, and mirroring from position element
        position_data = position_parser.compositional_pass()
        if position_data is None:
            self.register_error(
                message="Invalid position information for ShapeUsage. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        position, rotation, is_mirrored_pos = position_data

        scale_x, scale_y, is_mirrored_scale = scale_data
        # Combine mirroring information from both sources
        is_mirrored = is_mirrored_pos or is_mirrored_scale
        # Create and return the ShapeUsage object

        self.shape_usage_obj = graphics.ShapeUsage(
            position=position,
            rotation=rotation,
            scaleX=scale_x,
            scaleY=scale_y,
            isMirrored=is_mirrored,
            shape=shape_obj,
        )

        return self.shape_usage_obj


class SymbolParser(ParserModule):
    """Parser for Symbol elements in XML."""

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        shape_usage_parser: ShapeUsageParser,
    ) -> None:
        """Initialize the SymbolParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        element : ET.Element
            The XML element that contains symbol information.
        shape_usage_parser : ShapeUsageParser
            The parser class to use for parsing shape usage information.
        """
        super().__init__(context)
        self.element = element
        self.symbol_id = None
        self.symbol_obj = None

        # Initialize parser for shape usages
        self.shape_usage_parsers = shape_usage_parser
        self.register_submodule(shape_usage_parser)

    def compositional_pass(self) -> None:
        pass

    @redirect_errors_to_registry
    def drawing_pass(self) -> graphics.Symbol | None:
        """Perform a compositional pass over the symbol element.

        This method processes the symbol element to create a Symbol object,
        combining all shape usages.

        Returns
        -------
        graphics.Symbol | None
            The constructed Symbol object representing the symbol element or None if invalid
        """

        # Skip pass if element is not available
        if self.element is None:
            self.register_error(
                message="Missing element for SymbolParser. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Extract ID and name attributes
        self.symbol_id = self.element.get("ID")
        if self.symbol_id is None:
            self.register_error(
                message="Missing ID attribute in Symbol element. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        shape_usage = self.shape_usage_parsers.drawing_pass()

        # Try to get the appropriate class based on the element tag
        element_tag = self.element.tag
        try:
            # Get the class from graphics module using the element tag
            symbol_class = getattr(graphics, element_tag)
        except (AttributeError, TypeError):
            # Failsafe: use graphics.Symbol if element_tag is not a valid class in graphics
            symbol_class = graphics.Symbol

        # Create the object with the determined class
        self.symbol_obj = symbol_class(proteusId=self.symbol_id, elements=[shape_usage])

        self.register_object(self.symbol_id, self.symbol_obj)

        return self.symbol_obj


class DrawingBorderParser(ParserModule):
    """Parser for DrawingBorder elements in XML."""

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        polyline_parsers: list[PolylineParser],
        text_parsers: list[TextParser],
    ) -> None:
        """Initialize the ShapeParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        element : ET.Element
            The XML element that contains shape information.
        polyline_parsers : Type[PolylineParser]
            The parser class to use for parsing polyline information.
        text_parsers : Type[TextParser]
            The parser class to use for parsing text information.
        """
        super().__init__(context)
        self.element = element
        self.border_obj = None

        # Initialize parsers for different shape components
        self.polyline_parsers = polyline_parsers
        self.register_submodule_list(polyline_parsers)

        self.text_parsers = text_parsers
        self.register_submodule_list(text_parsers)

    @redirect_errors_to_registry
    def compositional_pass(self) -> graphics.Shape | None:
        """Perform a compositional pass over the shape element.

        This method processes the shape element to create a Shape object,
        combining polylines, polygons, ellipses, and texts.

        Returns
        -------
        graphics.Shape | None
            The constructed Shape object representing the shape element or None if invalid
        """

        # Skip pass if element is not available
        if self.element is None:
            self.register_error(
                message="Missing element for ShapeParser. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Instantiate empty components
        primitives = []

        # Parse polylines
        for polyline_parser in self.polyline_parsers:
            polyline = polyline_parser.compositional_pass()
            if polyline is not None:
                primitives.append(polyline)

        # Parse texts
        for text_parser in self.text_parsers:
            text = text_parser.compositional_pass()
            if text is not None:
                primitives.append(text)

        # Check if we have any primitives
        if not primitives:
            self.register_error(
                message="No valid primitives found in Border. Returning None.",
                level=ErrorLevels.WARNING,
            )
            # Continue anyway since a border can be empty

        # Create a Border object with the primitives
        self.border_obj = graphics.Border(elements=primitives)

        return self.border_obj


class LabelParser(ParserModule):
    """Parser for DrawingLabel elements in XML."""

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        polyline_parsers: list[PolylineParser],
        text_parsers: list[TextParser],
    ) -> None:
        """Initialize the ShapeParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        element : ET.Element
            The XML element that contains shape information.
        polyline_parsers : Type[PolylineParser]
            The parser class to use for parsing polyline information.
        text_parsers : Type[TextParser]
            The parser class to use for parsing text information.
        """
        super().__init__(context)
        self.element = element
        self.label_obj = None

        # Initialize parsers for different shape components
        self.polyline_parsers = polyline_parsers
        self.register_submodule_list(polyline_parsers)

        self.text_parsers = text_parsers
        self.register_submodule_list(text_parsers)

    def compositional_pass(self) -> None:
        pass

    @redirect_errors_to_registry
    def drawing_pass(self) -> graphics.Label | None:
        """Perform a compositional pass over the label element.

        This method processes the label element to create a Label object,
        combining polylines and texts.

        Returns
        -------
        graphics.Label | None
            The constructed Label object representing the label element or None if invalid
        """

        # Skip pass if element is not available
        if self.element is None:
            self.register_error(
                message="Missing element for LabelParser. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Extract ID attribute
        id_attr = self.element.get("ID")
        if id_attr is None:
            self.register_error(
                "Missing ID attribute in Label element. compositional pass skipped.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Determine the appropriate label class from the ID by removing numbering suffix
        # Example: "PipeTagLabelShape-1" -> "PipeTagLabelShape"
        label_class_name = None
        if id_attr:
            # Extract the base class name from the ID
            if "-" in id_attr:
                # For IDs like "PipeTagLabelShape-1"
                label_class_name = id_attr.split("-")[0]
            else:
                # For IDs that don't have a hyphen, use as is
                label_class_name = id_attr

            # Check if this class name exists in graphics module
            if not hasattr(graphics, label_class_name):
                self.register_error(
                    message=f"Label class {label_class_name} not found in graphics module for ID {id_attr}, using default Label",
                    level=ErrorLevels.ERROR,
                )
                label_class_name = None

        # Default to Label if we couldn't determine a specific class
        label_class = getattr(graphics, label_class_name) if label_class_name else graphics.Label

        # Extract ComponentClass attribute
        component_class = self.element.get("ComponentClass")
        if component_class is None:
            self.register_error(
                f"Missing ComponentClass attribute in Label element with ID {id_attr}. compositional pass skipped.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Instantiate empty components
        primitives = []

        # Parse polylines
        for polyline_parser in self.polyline_parsers:
            polyline = polyline_parser.compositional_pass()
            if polyline is not None:
                primitives.append(polyline)

        # Parse texts
        for text_parser in self.text_parsers:
            text = text_parser.compositional_pass()
            if text is not None:
                primitives.append(text)

        # Check if we have any primitives
        if not primitives:
            self.register_error(
                message=f"No valid primitives found in Label with ID {id_attr}. Returning None.",
                level=ErrorLevels.WARNING,
            )
            # Continue anyway since a label can be empty

        # Create a Label object with the primitives using the determined label class
        self.label_obj = label_class(proteusId=id_attr, elements=primitives)

        # Register the label in the object registry with its ID for reference by other elements
        self.context.object_registry.register_object(id_attr, self.label_obj)
        return self.label_obj


class DiagramParser(ParserModule):
    """Parser for Drawing information in XML elements.

    This class processes Drawing data from XML elements and provides methods to extract
    diagram properties such as name, type, background color, and extents.
    """

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        presentation_parsers: list[PresentationParser],
        drawing_border_parsers: list[DrawingBorderParser],
        drawing_label_parsers: list[LabelParser],
    ) -> None:
        """Initialize the DiagramParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        element : ET.Element
            The XML element that contains drawing information.
        presentation_parsers : list[PresentationParser]
            List of presentation parsers for presentation information (for background color).
        drawing_border_parsers : list[DrawingBorderParser]
            List of drawing border parsers to use.
        drawing_label_parsers : list[LabelParser]
            List of label parsers to use.
        """
        super().__init__(context)
        self.element = element
        self.diagram_obj = None

        # Initialize parsers for presentation
        self.presentation_parsers = presentation_parsers
        self.register_submodule_list(presentation_parsers)

        # Initialize border parsers
        self.border_parsers = drawing_border_parsers
        self.register_submodule_list(drawing_border_parsers)

        # Initialize label parsers
        self.label_parsers = drawing_label_parsers
        self.register_submodule_list(drawing_label_parsers)

    def compositional_pass(self) -> None:
        """Diagram pass doesnt need compositional pass, as all the object have
        been created in the drawing pass of the conceptualModel of the DEXPI object.


        compositional_pass need to be here as it is an abstract method in the parent class."""
        pass

    @redirect_errors_to_registry
    def drawing_pass(self) -> graphics.Diagram | None:
        """Parse diagram information from the element.

        Returns
        -------
        graphics.Diagram | None
            A Diagram object containing the drawing information, or None if parsing fails.
        """
        # Get the name and type attributes
        name = self.element.get("Name")
        if name is None:
            self.register_error(
                message="Missing Name attribute in Drawing element. Returning None.",
                level=ErrorLevels.ERROR,
            )
            return None

        # Get the background color from the presentation parser
        if len(self.presentation_parsers) > 1:
            self.register_error(
                f"Found {len(self.presentation_parsers)} Presentation elements for Diagram, "
                "expected at most 1. Using the first one.",
                level=ErrorLevels.WARNING,
            )
        elif len(self.presentation_parsers) == 0:
            return None
        presentation_parser = self.presentation_parsers[0]

        background_color = None
        background_color = presentation_parser.compositional_pass()

        # Parse the extents
        min_x, min_y, max_x, max_y = 0, 0, 0, 0

        extent_element = self.element.find("Extent")
        if extent_element is not None:
            min_element = extent_element.find("Min")
            if min_element is not None:
                if "X" in min_element.attrib:
                    min_x = float(min_element.get("X"))
                if "Y" in min_element.attrib:
                    min_y = float(min_element.get("Y"))

            max_element = extent_element.find("Max")
            if max_element is not None:
                if "X" in max_element.attrib:
                    max_x = float(max_element.get("X"))
                if "Y" in max_element.attrib:
                    max_y = float(max_element.get("Y"))
        else:
            self.register_error(
                message="No Extent element found in Drawing. Using default extents.",
                level=ErrorLevels.WARNING,
            )

        # Create a temporary DexpiBaseModel instance to satisfy the 'represents' requirement
        # This will be properly linked to the actual conceptual model when the diagram is used in PlantModelParser
        conceptual_model_placeholder = dexpiModel.ConceptualModel()

        # Create the diagram object
        self.diagram_obj = graphics.Diagram(
            backgroundColor=background_color,
            name=name,
            minX=min_x,
            minY=min_y,
            maxX=max_x,
            maxY=max_y,
            represents=conceptual_model_placeholder,  # Add the required 'represents' field
        )

        # Instantiate empty components
        drawing_border = []

        for border_parser in self.border_parsers:
            border = border_parser.compositional_pass()
            if border is not None:
                drawing_border.append(border)
                # Add the border to the diagram's groups list
                self.diagram_obj.groups.append(border)

        # Check if we have any borders
        if not drawing_border:
            self.register_error(
                message="No valid borders found in Drawing. Using empty borders list.",
                level=ErrorLevels.INFO,
            )

        drawing_label = []

        for label_parser in self.label_parsers:
            lbl = label_parser.drawing_pass()
            if lbl is not None:
                drawing_label.append(lbl)
                # Add the label to the diagram's groups list
                self.diagram_obj.groups.append(lbl)

        # Check if we have any labels
        if not drawing_label:
            self.register_error(
                message="No valid labels found in Drawing. Using empty labels list.",
                level=ErrorLevels.INFO,
            )

        return self.diagram_obj


### MODEL PARSERS ###
class MetaDataParser(ParserModule):
    """Parser for MetaData elements in Proteus XML.

    Parses generic attributes to create a MetaData object. No reference or control pass is
    required."""

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        generic_attribute_parser: GenericAttributeParser,
    ) -> None:
        """Initialize the MetaDataParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        element : ET.Element
            The XML element that contains MetaData information.
        generic_attribute_parser : GenericAttributeParser
            The parser to use for parsing generic attributes.
        """
        super().__init__(context)
        self.element = element

        # Make and register the generic attribute parser
        self.generic_attribute_parser = generic_attribute_parser
        self.register_submodule(generic_attribute_parser)

    @redirect_errors_to_registry
    def compositional_pass(self) -> metaData.MetaData | None:
        """Parse the generica attributes in a MetaData element to create a MetaData object.

        Returns
        -------
        metaData.MetaData | None
            The constructed MetaData object or None if an error occurs in parsing.
        """
        # Get the ID
        id_attr = self.element.get("ID")
        if id_attr is None:
            self.register_error(
                message="Missing ID attribute in MetaData element.",
                level=ErrorLevels.WARNING,
            )
        generic_attributes = self.generic_attribute_parser.compositional_pass(metaData.MetaData)
        meta_data_obj = metaData.MetaData(proteusId=id_attr, **generic_attributes)

        return meta_data_obj


class PlantModelParser(ParserModule):
    """The DexpiModelParser is a module for parsing DEXPI models from XML elements.

    This class first compiles the model information from the PlantInformation tag and then
    processes the elements of the conceptual model to create a DEXPI model. No reference or control
    pass is required.

    Attributes
    ----------
    context : ModuleContext
        The context containing the ID-, and element stack, error-, and object registry.
    element : ET.Element
        The XML element containing the DEXPI model to be parsed.
    dexpi_model : dexpiModel.DexpiModel | None
        The parsed DEXPI model object, or None if not yet parsed.
    metadata_parser : MetaDataParser
        The parser for the metadata of the DEXPI model.
    equipment_parsers : list[EquipmentParser]
        A list of parsers for the equipment in the DEXPI model.
    piping_network_system_parsers : list[PipingNetworkSystemParser]
        A list of parsers for the piping network systems in the DEXPI model.
    actuating_system_parsers : list[ActuatingSystemParser]
        A list of parsers for the actuating systems in the DEXPI model.
    process_signal_generating_system_parsers : list[ProcessSignalGeneratingSystemParser]
        A list of parsers for the process signal generating systems in the DEXPI model.
    process_instrumentation_function_parsers : list[ProcessInstrumentationFunctionParser]
        A list of parsers for the process instrumentation functions in the DEXPI model.
    shape_catalogue_parsers : list[ShapeCatalogueParser]
        A list of parsers for the shape catalogue in the DEXPI model.
    drawing_parsers : list[DiagramParser]
        List of diagram parsers to use for parsing drawing information.
    """

    def __init__(
        self,
        context: ModuleContext,
        element: ET.Element,
        metadata_parsers: list[MetaDataParser],
        equipment_parsers: list[EquipmentParser],
        piping_network_system_parsers: list[PipingNetworkSystemParser],
        actuating_system_parsers: list[ActuatingSystemParser],
        process_signal_generating_system_parsers: list[ProcessSignalGeneratingSystemParser],
        process_instrumentation_function_parsers: list[ProcessInstrumentationFunctionParser],
        instrumentation_loop_function_parsers: list[InstrumentationLoopFunctionParser],
        shape_catalogue_parsers: list[ShapeCatalogueParser],
        drawing_parsers: list[DiagramParser],
    ) -> None:
        """Initialize the DexpiModelParser with the XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        element : ET.Element
            The XML element containing the DEXPI model to be parsed.
        metadata_parser : MetaDataParser
            The parser for the metadata of the DEXPI model.
        equipment_parsers : list[EquipmentParser]
            A list of parsers for the equipment in the DEXPI model.
        piping_network_system_parsers : list[PipingNetworkSystemParser]
            A list of parsers for the piping network systems in the DEXPI model.
        actuating_system_parsers : list[ActuatingSystemParser]
            A list of parsers for the actuating systems in the DEXPI model.
        process_signal_generating_system_parsers : list[ProcessSignalGeneratingSystemParser]
            A list of parsers for the process signal generating systems in the DEXPI model.
        process_instrumentation_function_parsers : list[ProcessInstrumentationFunctionParser]
            A list of parsers for the process instrumentation functions in the DEXPI model.
        instrumentation_loop_function_parsers : list[InstrumentationLoopFunctionParser]
            A list of parsers for the instrumentation loop functions in the DEXPI model.
        shape_catalogue_parsers : list[ShapeCatalogueParser]
            A list of parsers for the shape catalogue in the DEXPI model.
        drawing_parsers : list[DiagramParser]
            List of diagram parsers to use for parsing drawing information.
        """
        super().__init__(context)
        self.element = element
        self.dexpi_model = None

        # Set and register metadata parsers
        self.metadata_parsers = metadata_parsers
        self.register_submodule_list(metadata_parsers)

        # Set and register equipment parsers
        self.equipment_parsers = equipment_parsers
        self.register_submodule_list(equipment_parsers)

        # Set and register piping network system parsers
        self.pnsystem_parsers = piping_network_system_parsers
        self.register_submodule_list(piping_network_system_parsers)

        # Set and register actuating system parsers
        self.actuating_system_parsers = actuating_system_parsers
        self.register_submodule_list(actuating_system_parsers)

        # Set and register process signal generating system parsers
        self.process_signal_generating_system_parsers = process_signal_generating_system_parsers
        self.register_submodule_list(process_signal_generating_system_parsers)

        # Set and register process instrumentation function parsers
        self.process_instrumentation_function_parsers = process_instrumentation_function_parsers
        self.register_submodule_list(process_instrumentation_function_parsers)

        # Set and register instrumentation loop function parsers
        self.instrumentation_loop_function_parsers = instrumentation_loop_function_parsers
        self.register_submodule_list(instrumentation_loop_function_parsers)

        # Set and register shape catalogue parsers
        self.shape_catalogue_parsers = shape_catalogue_parsers
        self.register_submodule_list(shape_catalogue_parsers)

        # Set and register diagram parsers
        self.drawing_parsers = drawing_parsers
        self.register_submodule_list(drawing_parsers)

    def compositional_pass(self) -> dexpiModel.DexpiModel:
        """Parse the DEXPI model in the compositional pass.

        Extracts all required data from the plant information tag, and composes all main DEXPI
        model elements. Since the DEXPI model requires some fixed fields, it raises critical errors
        if these are missing or incorrect.

        Returns
        -------
        dexpiModel.DexpiModel
            An instance of the DexpiModel class created from the parsed attributes.

        """
        # Retrieve model information from PlantInformation tag
        plant_info = self.element.find("PlantInformation")
        if plant_info is None:
            exception = ValueError(
                "PlantInformation tag is missing in the DEXPI model. "
                "This information is required for a valid DEXPI model."
            )
            self.register_error(
                "PlantInformation tag is missing. Info required for dexpi model.",
                level=ErrorLevels.CRITICAL,
                exception=exception,
            )
            raise exception

        # Check for required fields in PlantInformation
        missing_fields = [
            field
            for field in [
                "Date",
                "Time",
                "OriginatingSystem",
                "OriginatingSystemVendor",
                "OriginatingSystemVersion",
            ]
            if plant_info.get(field) is None
        ]
        if missing_fields:
            self.register_error(
                f"Missing fields in PlantInformation: {', '.join(missing_fields)}. "
                "Info required for dexpi model.",
                level=ErrorLevels.CRITICAL,
            )

        # Manage fixed fields
        app = plant_info.get("Application")
        if app != "Dexpi":
            self.register_error(
                f"Unexpected Application value: {app}. Expected 'Dexpi'.",
                level=ErrorLevels.WARNING,
            )
        ver = plant_info.get("ApplicationVersion")
        if ver[0:3] != "1.3":
            self.register_error(
                f"Unexpected ApplicationVersion value: {ver}. Expected '1.3'.",
                level=ErrorLevels.WARNING,
            )
        disc = plant_info.get("Discipline")
        if disc != "PID":
            self.register_error(
                f"Unexpected Discipline value: {disc}. Expected 'PID'.",
                level=ErrorLevels.WARNING,
            )
        is3d = plant_info.get("Is3D")
        if is3d is not None and is3d.lower() != "no":
            self.register_error(
                f"Unexpected Is3D value: {is3d}. Expected 'No'.",
                level=ErrorLevels.WARNING,
            )
        sch_ver = plant_info.get("SchemaVersion")
        if sch_ver[0:3] != "4.1":
            self.register_error(
                f"Unexpected SchemaVersion value: {sch_ver}. Expected '4.1'.",
                level=ErrorLevels.WARNING,
            )

        # Create date and time from PlantInformation
        the_date = tuple(int(i) for i in plant_info.get("Date").split("-"))
        raw_time = tuple(float(i) for i in plant_info.get("Time").split(":"))
        the_system = plant_info.get("OriginatingSystem")
        the_vendor = plant_info.get("OriginatingSystemVendor")
        the_version = plant_info.get("OriginatingSystemVersion")
        microseconds = int((raw_time[2] - int(raw_time[2])) * 1000000)
        the_time = (
            int(raw_time[0]),
            int(raw_time[1]),
            int(raw_time[2]),
            microseconds,
        )
        date_time = datetime.datetime(*(the_date + the_time))

        # Compose metadata
        if len(self.metadata_parsers) > 1:
            self.register_error(
                f"Found {len(self.metadata_parsers)} MetaData elements in PlantModel, "
                "expected at most 1. Using the first one.",
                level=ErrorLevels.WARNING,
            )
        elif len(self.metadata_parsers) == 0:
            metadata = None
        else:
            self.metadata_parser = self.metadata_parsers[0]
            metadata = self.metadata_parser.compositional_pass()

        # Compose equipment as tagged_plant_items
        tagged_plant_items = []
        for equipment_parser in self.equipment_parsers:
            tagged_plant_items.append(equipment_parser.compositional_pass())

        # Compose piping network systems
        piping_network_systems = []
        for pns_parser in self.pnsystem_parsers:
            pns = pns_parser.compositional_pass()
            if pns is not None:
                piping_network_systems.append(pns)

        # Compose actuating systems
        actuating_systems = []
        for actuating_system_parser in self.actuating_system_parsers:
            asystem = actuating_system_parser.compositional_pass()
            if asystem is not None:
                actuating_systems.append(asystem)

        # Compose process signal generating systems
        process_signal_generating_systems = []
        for (
            process_signal_generating_system_parser
        ) in self.process_signal_generating_system_parsers:
            psgs = process_signal_generating_system_parser.compositional_pass()
            if psgs is not None:
                process_signal_generating_systems.append(psgs)

        # Compose process instrumentation functions
        process_instrumentation_functions = []
        for (
            process_instrumentation_function_parser
        ) in self.process_instrumentation_function_parsers:
            pif = process_instrumentation_function_parser.compositional_pass()
            if pif is not None:
                process_instrumentation_functions.append(pif)

        # Compose instrumentation loop functions
        instrumentation_loop_functions = []
        for instrumentation_loop_function_parser in self.instrumentation_loop_function_parsers:
            ilf = instrumentation_loop_function_parser.compositional_pass()
            if ilf is not None:
                instrumentation_loop_functions.append(ilf)

        # Create the conceptual model
        conceptual_model = dexpiModel.ConceptualModel(
            metaData=metadata,
            taggedPlantItems=filter_none(tagged_plant_items),
            pipingNetworkSystems=filter_none(piping_network_systems),
            actuatingSystems=filter_none(actuating_systems),
            processSignalGeneratingSystems=filter_none(process_signal_generating_systems),
            processInstrumentationFunctions=filter_none(process_instrumentation_functions),
            instrumentationLoopFunctions=filter_none(instrumentation_loop_functions),
        )

        # Compose shape catalogue if available
        shape_catalogue = []
        for shape_catalogue_parser in self.shape_catalogue_parsers:
            sc = shape_catalogue_parser.compositional_pass()
            if sc is not None:
                shape_catalogue.append(sc)

        # Create the DEXPI model
        dexpi_model = dexpiModel.DexpiModel(
            conceptualModel=conceptual_model,
            exportDateTime=date_time,
            originatingSystemName=the_system,
            originatingSystemVendorName=the_vendor,
            originatingSystemVersion=the_version,
            shapeCatalogues=shape_catalogue,
        )

        self.dexpi_model = dexpi_model

        return dexpi_model

    def drawing_pass(self) -> dexpiModel.DexpiModel | None:
        """Perform the drawing pass for the DEXPI model.

        This method collects all graphical representations from equipment parsers, piping networks,
        and other components, and adds them to the diagram. It first calls the drawing_pass method
        on all submodules, then explicitly collects and organizes the graphical results.

        The graphical representations from various components (equipment, piping, etc.) are
        collected and added to the diagram's groups list if a diagram was created during the
        compositional pass.
        """

        # Get the diagram from the drawing parser
        if self.dexpi_model is None:
            self.register_error(
                "No dexpi model is initiated. Skipping diagram drawing pass.",
                level=ErrorLevels.WARNING,
            )
            return

        # Compose diagram
        if len(self.drawing_parsers) > 1:
            self.register_error(
                f"Found {len(self.drawing_parsers)} Drawing elements in PlantModel, "
                "expected at most 1. Using the first one.",
                level=ErrorLevels.WARNING,
            )
        elif len(self.drawing_parsers) == 0:
            return None
        drawing_parser = self.drawing_parsers[0]

        diagram = drawing_parser.drawing_pass()

        # Check if diagram was not none, then proceed to add graphical elements
        if diagram is not None:
            # Process all equipment graphical representations
            for equipment_parser in self.equipment_parsers:
                equip_graphic = equipment_parser.drawing_pass()
                if equip_graphic is not None:
                    diagram.groups.append(equip_graphic)

            # Process piping network system graphical representations
            for pnsystem_parser in self.pnsystem_parsers:
                pns_graphic = pnsystem_parser.drawing_pass()
                if pns_graphic is not None:
                    diagram.groups.append(pns_graphic)

            # Process actuating system graphical representations
            for actuating_system_parser in self.actuating_system_parsers:
                as_graphic = actuating_system_parser.drawing_pass()
                if as_graphic is not None:
                    diagram.groups.append(as_graphic)

            # Process process instrumentation function graphical representations
            for pif_parser in self.process_instrumentation_function_parsers:
                pif_graphic = pif_parser.drawing_pass()
                if pif_graphic is not None:
                    diagram.groups.append(pif_graphic)

            # Process process signal generating system graphical representations
            for psgs_parser in self.process_signal_generating_system_parsers:
                psgs_graphic = psgs_parser.drawing_pass()
                if psgs_graphic is not None:
                    diagram.groups.append(psgs_graphic)

            # Process instrumentation loop function graphical representations
            # No drawing object for ILF

            # Update DEXPI object in Diagram
            diagram.represents = self.dexpi_model.conceptualModel

            # Assign the diagram to the dexpi_model
            self.dexpi_model.diagram = diagram
