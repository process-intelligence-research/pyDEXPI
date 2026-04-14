import datetime
import xml.etree.ElementTree as ET

import pytest

from pydexpi.dexpi_classes.pydantic_classes import (
    Chamber,
    CustomPressureAbsoluteAttribute,
    CustomStringAttribute,
    Equipment,
    MetaData,
    Nozzle,
    NullPressureAbsolute,
    PressureAbsolute,
    PressureAbsoluteUnit,
    Pump,
    VolumeFlowRate,
    VolumeFlowRateUnit,
)
from pydexpi.loaders.proteus_serializer.proteus_exporter.core import (
    ElementRegistry,
    ModuleContext,
)
from pydexpi.loaders.proteus_serializer.proteus_exporter.exporter_modules import (
    EquipmentExporter,
    GenericAttributeExporter,
    MetaDataExporter,
    NozzleExporter,
    PlantModelExporter,
)


@pytest.fixture()
def module_context() -> ModuleContext:
    """Fixture to create a ModuleContext for testing."""
    return ModuleContext(element_registry=ElementRegistry(), override_proteus_id=False)


class TestGenericAttributeExporter:
    """
    Tests for GenericAttributeExporter internals.

    This test class organizes unit tests that exercise primitive type mapping and
    the creation of GenericAttribute elements for both primitive values and
    DexpiDataTypeBaseModel-like objects.
    """

    @pytest.fixture()
    def _simple_owner(self) -> Pump:
        """
        Minimal owner object used for initializing the exporter.

        Returns
        -------
        Pump
            A simple owner instance.
        """

        my_pump = Pump(
            # Standard attributes
            tagName="TestPump",
            designVolumeFlowRate=VolumeFlowRate(
                unit=VolumeFlowRateUnit.MetreCubedPerHour, value=100.0
            ),
            differentialPressure=NullPressureAbsolute(),
            # Custom attributes
            customAttributes=[
                # Normal DexpiDataTypeBaseModel-like attribute
                CustomPressureAbsoluteAttribute(
                    value=PressureAbsolute(unit=PressureAbsoluteUnit.Bar, value=1.5),
                    attributeURI="TestURI",
                    attributeName="CustomPressure",
                ),
                # Normal primitive attribute
                CustomStringAttribute(
                    value="TestString",
                    attributeURI="TestURI",
                    attributeName="CustomString",
                ),
                # Edge case: Custom Attribute with Null Object
                CustomPressureAbsoluteAttribute(
                    value=NullPressureAbsolute(),
                    attributeURI="TestURI",
                    attributeName="CustomPressureNull",
                ),
            ],
        )

        return my_pump

    def test_compositional_pass(self, _simple_owner, module_context) -> None:
        """Test that the top level compositional pass works without error."""
        exporter = GenericAttributeExporter(module_context, _simple_owner)
        generic_attrs = exporter.compositional_pass()
        assert len(generic_attrs) == 3  # 3 standard
        assert generic_attrs.get("Number") == "3"

    def test_get_custom_attributes(self, _simple_owner, module_context) -> None:
        """Test that custom attributes are correctly extracted."""
        exporter = GenericAttributeExporter(module_context, _simple_owner)
        _ = exporter.compositional_pass()
        custom_attrs = exporter.get_custom_attributes()
        assert len(custom_attrs) == 3  # 3 custom attributes
        assert custom_attrs.get("Number") == "3"

    def test_compose_and_get(self, _simple_owner, module_context) -> None:
        """Test that compositional pass and get_custom_attributes work together."""
        exporter = GenericAttributeExporter(module_context, _simple_owner)
        parent_element = ET.Element("Parent")
        exporter.compose_and_add_attributes(parent_element)

        # Get generic attribute set
        attribute_sets = parent_element.findall("GenericAttributes")
        attribute_sets = [
            attr_set for attr_set in attribute_sets if attr_set.get("Set") == "DexpiAttributes"
        ]

        assert len(attribute_sets) == 1  # One DexpiAttributes element
        generic_attrs = attribute_sets[0].findall("GenericAttribute")
        assert len(generic_attrs) == 3
        assert attribute_sets[0].get("Number") == "3"

        # Get custom attribute set
        custom_attr_sets = parent_element.findall("GenericAttributes")
        custom_attr_sets = [
            attr_set for attr_set in custom_attr_sets if attr_set.get("Set") == "CustomAttributes"
        ]
        assert len(custom_attr_sets) == 1  # One CustomAttributes element
        custom_attrs = custom_attr_sets[0].findall("GenericAttribute")
        assert len(custom_attrs) == 3  # 3 custom attributes
        assert custom_attr_sets[0].get("Number") == "3"

    def test_compose_and_get_no_custom(self, _simple_owner, module_context) -> None:
        """Test that compositional pass and get_custom_attributes work together."""
        # Remove custom attributes
        _simple_owner.customAttributes = []

        exporter = GenericAttributeExporter(module_context, _simple_owner)
        parent_element = ET.Element("Parent")
        exporter.compose_and_add_attributes(parent_element)

        # Get generic attribute set
        attribute_sets = parent_element.findall("GenericAttributes")
        attribute_sets = [
            attr_set for attr_set in attribute_sets if attr_set.get("Set") == "DexpiAttributes"
        ]

        assert len(attribute_sets) == 1  # One DexpiAttributes element
        generic_attrs = attribute_sets[0].findall("GenericAttribute")
        assert len(generic_attrs) == 3

        # Get custom attribute set
        custom_attr_sets = parent_element.findall("GenericAttributes")
        custom_attr_sets = [
            attr_set for attr_set in custom_attr_sets if attr_set.get("Set") == "CustomAttributes"
        ]
        assert len(custom_attr_sets) == 0  # No CustomAttributes element

    def test_export_generic_attributes(self, _simple_owner, module_context) -> None:
        """
        Test that export_generic_attributes correctly creates XML elements for standard attributes.

        Parameters
        ----------
        self : TestGenericAttributeExporter
            The test instance.
        _simple_owner : Pump
            A simple owner instance.
        """
        exporter = GenericAttributeExporter(module_context, _simple_owner)

        generic_attr_elements = exporter._export_generic_attributes(_simple_owner)

        # There should be 3.
        assert len(generic_attr_elements) == 3
        assert generic_attr_elements.get("Number") == "3"

        # Check the DesignVolumeFlowRate attribute
        design_flow_elem = next(
            (elem for elem in generic_attr_elements if elem.get("Name") == "DesignVolumeFlowRate"),
            None,
        )
        assert design_flow_elem is not None
        assert design_flow_elem.tag == "GenericAttribute"
        assert (
            design_flow_elem.get("AttributeURI")
            == "http://sandbox.dexpi.org/rdl/DesignVolumeFlowRate"
        )
        assert design_flow_elem.get("Format") == "double"
        assert design_flow_elem.get("Value") == "100.0"
        assert design_flow_elem.get("Units") == "MetreCubedPerHour"
        assert design_flow_elem.get("UnitsURI") == ""

        # Check the TagName attribute
        tag_name_elem = next(
            (
                elem
                for elem in generic_attr_elements
                if elem.get("Name") == "TagNameAssignmentClass"
            ),
            None,
        )
        assert tag_name_elem is not None
        assert tag_name_elem.tag == "GenericAttribute"
        assert (
            tag_name_elem.get("AttributeURI")
            == "http://sandbox.dexpi.org/rdl/TagNameAssignmentClass"
        )
        assert tag_name_elem.get("Format") == "string"
        assert tag_name_elem.get("Value") == "TestPump"
        assert tag_name_elem.get("Units") is None

        # Check the DifferentialPressure attribute
        diff_pressure_elem = next(
            (
                elem
                for elem in generic_attr_elements
                if elem.get("Name") == "DifferentialPressureAssignmentClass"
            ),
            None,
        )
        assert diff_pressure_elem is not None
        assert diff_pressure_elem.tag == "GenericAttribute"
        assert (
            diff_pressure_elem.get("AttributeURI")
            == "http://sandbox.dexpi.org/rdl/DifferentialPressureAssignmentClass"
        )
        assert diff_pressure_elem.get("Name") == "DifferentialPressureAssignmentClass"
        assert "Format" not in diff_pressure_elem.attrib
        assert "Value" not in diff_pressure_elem.attrib
        assert "Units" not in diff_pressure_elem.attrib
        assert "UnitsURI" not in diff_pressure_elem.attrib

    def test_export_custom_attributes(self, _simple_owner, module_context) -> None:
        """
        Test that export_custom_attributes correctly creates XML elements for custom attributes.

        Parameters
        ----------
        self : TestGenericAttributeExporter
            The test instance.
        _simple_owner : Pump
            A simple owner instance.
        """
        exporter = GenericAttributeExporter(module_context, _simple_owner)

        custom_attr_elements = exporter._export_custom_attributes(_simple_owner)

        # There should three child elements for the custom attributes
        assert len(custom_attr_elements) == 3
        assert custom_attr_elements.get("Number") == "3"

        # Test for the custom pressure attribute
        pressure_attr_elem = next(
            (elem for elem in custom_attr_elements if elem.get("Name") == "CustomPressure"),
            None,
        )

        assert pressure_attr_elem.tag == "GenericAttribute"
        assert pressure_attr_elem.get("Name") == "CustomPressure"
        assert pressure_attr_elem.get("AttributeURI") == "TestURI"
        assert pressure_attr_elem.get("Format") == "double"
        assert pressure_attr_elem.get("Type") == "PressureAbsolute"
        assert pressure_attr_elem.get("Value") == "1.5"
        assert pressure_attr_elem.get("Units") == "Bar"

        # Test for the custom string attribute
        string_attr_elem = next(
            (elem for elem in custom_attr_elements if elem.get("Name") == "CustomString"),
            None,
        )
        assert string_attr_elem.tag == "GenericAttribute"
        assert string_attr_elem.get("Name") == "CustomString"
        assert string_attr_elem.get("AttributeURI") == "TestURI"
        assert string_attr_elem.get("Format") == "string"
        assert string_attr_elem.get("Value") == "TestString"

        # Test for the custom attribute with Null value
        null_attr_elem = next(
            (elem for elem in custom_attr_elements if elem.get("Name") == "CustomPressureNull"),
            None,
        )
        assert null_attr_elem.tag == "GenericAttribute"
        assert null_attr_elem.get("Name") == "CustomPressureNull"
        assert null_attr_elem.get("AttributeURI") == "TestURI"
        assert null_attr_elem.get("Type") == "NullPressureAbsolute"
        assert "Format" not in null_attr_elem.attrib
        assert "Value" not in null_attr_elem.attrib
        assert "Units" not in null_attr_elem.attrib

    def test_primitive_data_type_mapping(self, _simple_owner, module_context) -> None:
        """
        Test mapping of primitive Python type names to Proteus XML formats.

        Parameters
        ----------
        self : TestGenericAttributeExporter
            The test instance.
        """
        exporter = GenericAttributeExporter(module_context, _simple_owner)

        assert exporter._primitive_data_type_mapping("str") == "string"
        assert exporter._primitive_data_type_mapping("bool") == "boolean"
        assert exporter._primitive_data_type_mapping("int") == "integer"
        assert exporter._primitive_data_type_mapping("float") == "double"
        # Unknown types should fall back to string
        assert exporter._primitive_data_type_mapping("customtype") == "string"


class TestMetaDataExporter:
    """
    Tests for MetaDataExporter functionality.

    This test class exercises the MetaDataExporter's ability to export MetaData objects
    to XML format, including proper handling of IDs, ComponentClass attributes, and
    integration with GenericAttributeExporter for custom attributes.
    """

    @pytest.fixture
    def simple_metadata(self) -> MetaData:
        """
        Create a simple MetaData object for testing.

        Returns
        -------
        MetaData
            A MetaData object with basic attributes.
        """
        return MetaData(
            proteusId="MetaData-1",
            approvalDateRepresentation="2023-10-01",
            customAttributes=[
                CustomStringAttribute(
                    value="Example",
                    attributeURI="http://example.com/attr",
                    attributeName="ExampleAttr",
                )
            ],
        )

    def test_compositional_pass_basic(
        self, module_context: ModuleContext, simple_metadata: MetaData
    ) -> None:
        """
        Test basic export functionality of MetaDataExporter.

        Parameters
        ----------
        module_context : ModuleContext
            The module context for the test.
        simple_metadata : MetaData
            Simple MetaData object to export.
        """
        exporter = MetaDataExporter(module_context, simple_metadata)
        metadata_elem = exporter.compositional_pass()

        # Check element tag and attributes
        assert metadata_elem.tag == "MetaData"
        assert metadata_elem.get("ID") == "MetaData-1"
        assert metadata_elem.get("ComponentClass") == "MetaData"

        # Check that the element was registered
        registered_elem = module_context.element_registry.get_element(simple_metadata.id)
        assert registered_elem is not None
        assert registered_elem is metadata_elem

    def test_compositional_pass_uses_proteus_id(
        self, module_context: ModuleContext, simple_metadata: MetaData
    ) -> None:
        """
        Test that proteusId is used when available.

        Parameters
        ----------
        module_context : ModuleContext
            The module context for the test.
        simple_metadata : MetaData
            MetaData object with proteusId.
        """
        simple_metadata.proteusId = "CustomProteus-1"

        exporter = MetaDataExporter(module_context, simple_metadata)
        metadata_elem = exporter.compositional_pass()

        assert metadata_elem.get("ID") == "CustomProteus-1"

    def test_compositional_pass_fallback_to_id(
        self, module_context: ModuleContext, simple_metadata: MetaData
    ) -> None:
        """
        Test that id is used when proteusId is None.

        Parameters
        ----------
        module_context : ModuleContext
            The module context for the test.
        simple_metadata : MetaData
            MetaData object without proteusId.

        """
        metadata_no_proteus_id = simple_metadata
        metadata_no_proteus_id.proteusId = None
        exporter = MetaDataExporter(module_context, metadata_no_proteus_id)
        metadata_elem = exporter.compositional_pass()

        assert metadata_elem.get("ID") == f"MetaData-{metadata_no_proteus_id.id}"

    def test_empty_metadata(self, module_context: ModuleContext) -> None:
        """
        Test export of minimal MetaData object.

        Parameters
        ----------
        module_context : ModuleContext
            The module context for the test.
        """
        minimal_metadata = MetaData(proteusId="MinimalMeta")

        exporter = MetaDataExporter(module_context, minimal_metadata)
        metadata_elem = exporter.compositional_pass()

        assert metadata_elem.tag == "MetaData"
        assert metadata_elem.get("ID") == "MinimalMeta"
        assert metadata_elem.get("ComponentClass") == "MetaData"

        # Should still have DexpiAttributes (even if empty)
        dexpi_attrs = metadata_elem.find("DexpiAttributes")
        assert dexpi_attrs is None

        # Should not have CustomAttributes
        custom_attrs = metadata_elem.find("CustomAttributes")
        assert custom_attrs is None


class TestNozzleExporter:
    """
    Tests for NozzleExporter functionality.

    Covers structure, ID selection, association creation, and registration behavior.

    Fixtures
    --------
    simple_nozzle : Nozzle
        Provides a simple Nozzle instance for testing.
    """

    @pytest.fixture
    def simple_nozzle(self) -> Nozzle:
        """
        Provide a simple Nozzle with an attribute to ensure DexpiAttributes are emitted.

        Returns
        -------
        Nozzle
            A minimal nozzle instance with subTagName set.
        """
        # Rely on model defaults for id; ensure at least one mapped attribute is present
        return Nozzle(subTagName="N1")

    def test_compositional_pass_structure(
        self, module_context: ModuleContext, simple_nozzle: Nozzle
    ) -> None:
        """
        Ensure NozzleExporter produces correct element structure and generic attributes.

        Parameters
        ----------
        module_context : ModuleContext
            The module context for the test.
        simple_nozzle : Nozzle
            Nozzle instance with at least one mapped attribute.
        """
        exporter = NozzleExporter(module_context, simple_nozzle)
        nozzle_elem = exporter.compositional_pass()

        assert nozzle_elem.tag == "Nozzle"
        assert nozzle_elem.get("ComponentClass") == "Nozzle"
        # Default URI should be set by helper
        assert nozzle_elem.get("ComponentClassURI") == "http://data.posccaesar.org/rdl/RDS415214"

        # Generic attributes exist and include SubTagName
        dexpi_attrs = nozzle_elem.find("GenericAttributes")
        assert dexpi_attrs is not None
        ga = next(
            (
                g
                for g in dexpi_attrs.findall("GenericAttribute")
                if g.get("Name") == "SubTagNameAssignmentClass"
            ),
            None,
        )
        assert ga is not None
        assert ga.get("AttributeURI") == "http://sandbox.dexpi.org/rdl/SubTagNameAssignmentClass"
        assert ga.get("Format") == "string"
        assert ga.get("Value") == "N1"

        # Assert nozzle was registered
        registered_elem = module_context.element_registry.get_element(simple_nozzle.id)
        assert registered_elem is not None

    def test_id_prefers_proteus_id(
        self,
        module_context: ModuleContext,
        simple_nozzle: Nozzle,
    ) -> None:
        """
        Verify element ID uses proteus_id when present.

        Parameters
        ----------
        module_context : ModuleContext
            The module context for the test.
        simple_nozzle : Nozzle
            Nozzle instance to export.
        """
        simple_nozzle.proteusId = "Prot-1"

        exporter = NozzleExporter(module_context, simple_nozzle)
        nozzle_elem = exporter.compositional_pass()

        assert nozzle_elem.get("ID") == "Prot-1"

    def test_reference_pass_adds_associations(
        self, module_context: ModuleContext, simple_nozzle: Nozzle
    ) -> None:
        """
        Ensure reference_pass adds bidirectional Association elements with chamber.

        Parameters
        ----------
        module_context : ModuleContext
            The module context for the test.
        simple_nozzle : Nozzle
            Nozzle fixture to test on.
        """
        # Prepare a registered chamber element
        dummy_chamber = Chamber(id="Chamber-1")
        chamber_elem = ET.Element("Equipment")
        chamber_elem.set("ID", "Chamber-1")
        module_context.element_registry.register_element("Chamber-1", chamber_elem)

        # Nozzle referencing the chamber by id
        simple_nozzle.chamber = dummy_chamber

        exporter = NozzleExporter(module_context, simple_nozzle)
        nozzle_elem = exporter.compositional_pass()
        exporter.reference_pass()

        # Check association on nozzle -> chamber
        assoc_nozzle = next(
            (a for a in nozzle_elem.findall("Association") if a.get("Type") == "is located in"),
            None,
        )
        assert assoc_nozzle is not None
        assert assoc_nozzle.get("ItemID") == "Chamber-1"

        # Check reciprocal association on chamber -> nozzle
        assoc_chamber = next(
            (
                a
                for a in chamber_elem.findall("Association")
                if a.get("Type") == "is the location of"
            ),
            None,
        )
        assert assoc_chamber is not None
        assert assoc_chamber.get("ItemID") == nozzle_elem.get("ID")


class TestEquipmentExporter:
    """
    Tests for EquipmentExporter functionality.

    This test class exercises the EquipmentExporter's ability to export Equipment objects
    to XML format, including proper handling of nozzles, subequipment, IDs, and registration.

    Fixtures
    --------
    simple_equipment : Equipment
        Provides a basic Equipment instance for testing.
    equipment_with_nozzles : Pump
        Provides an Equipment instance with nozzles for testing.
    equipment_with_chamber : Equipment
        Provides an Equipment instance with a chamber for testing.
    """

    @pytest.fixture
    def simple_equipment(self) -> Equipment:
        """
        Create a simple Equipment object for testing.

        Returns
        -------
        Equipment
            A basic Equipment object with minimal attributes.
        """
        return Equipment(id="Equipment-1", tagName="E-101")

    @pytest.fixture
    def equipment_with_nozzles(self) -> Pump:
        """
        Create a Pump (Equipment subclass) with nozzles for testing.

        Returns
        -------
        Pump
            A Pump instance with nozzles attached.
        """
        nozzle1 = Nozzle(id="Nozzle-1", subTagName="N1")
        nozzle2 = Nozzle(id="Nozzle-2", subTagName="N2")

        return Pump(id="Pump-1", tagName="P-101", nozzles=[nozzle1, nozzle2])

    @pytest.fixture
    def equipment_with_chamber(self) -> Equipment:
        """
        Create an Equipment object with a chamber for testing.

        Returns
        -------
        Equipment
            An Equipment instance with a chamber attached.
        """
        chamber = Chamber(id="Chamber-1", tagName="C-101")
        return Equipment(id="Equipment-2", tagName="E-102", chambers=[chamber])

    def test_compositional_pass_basic_structure(
        self, module_context: ModuleContext, simple_equipment: Equipment
    ) -> None:
        """
        Test basic export functionality produces correct XML structure.

        Parameters
        ----------
        module_context : ModuleContext
            The module context for the test.
        simple_equipment : Equipment
            Simple Equipment object to export.
        """
        exporter = EquipmentExporter(module_context, simple_equipment)
        equipment_elem = exporter.compositional_pass()

        # Check basic XML structure
        assert equipment_elem.tag == "Equipment"
        assert equipment_elem.get("ID") == "Equipment-Equipment-1"
        assert equipment_elem.get("ComponentClass") == "Equipment"
        assert equipment_elem.get("ComponentClassURI") == "http://sandbox.dexpi.org/rdl/Equipment"

        # Check that equipment was registered
        registered_elem = module_context.element_registry.get_element(simple_equipment.id)
        assert registered_elem is not None
        assert registered_elem is equipment_elem

    def test_compositional_pass_with_nozzles(
        self, module_context: ModuleContext, equipment_with_nozzles: Pump
    ) -> None:
        """
        Test export of equipment with nozzles creates proper nozzle elements.

        Parameters
        ----------
        module_context : ModuleContext
            The module context for the test.
        equipment_with_nozzles : Pump
            Equipment object with nozzles to export.
        """
        exporter = EquipmentExporter(module_context, equipment_with_nozzles)
        equipment_elem = exporter.compositional_pass()

        # Check equipment structure
        assert equipment_elem.tag == "Equipment"
        assert equipment_elem.get("ID") == "Pump-Pump-1"
        assert equipment_elem.get("ComponentClass") == "Pump"

        # Check nozzles are exported as child elements
        nozzle_elems = equipment_elem.findall("Nozzle")
        assert len(nozzle_elems) == 2

        # Check first nozzle
        nozzle1 = next((n for n in nozzle_elems if n.get("ID") == "Nozzle-Nozzle-1"), None)
        assert nozzle1 is not None
        assert nozzle1.get("ComponentClass") == "Nozzle"

        # Check nozzle has GenericAttributes with SubTagName
        dexpi_attrs = nozzle1.find("GenericAttributes")

        assert dexpi_attrs is not None
        subtag_attr = next(
            (
                attr
                for attr in dexpi_attrs.findall("GenericAttribute")
                if attr.get("Name") == "SubTagNameAssignmentClass"
            ),
            None,
        )
        assert subtag_attr is not None
        assert subtag_attr.get("Value") == "N1"

        # Check that both nozzles are registered in registry
        assert module_context.element_registry.get_element("Nozzle-1") is not None
        assert module_context.element_registry.get_element("Nozzle-2") is not None

    def test_compositional_pass_with_chamber(
        self, module_context: ModuleContext, equipment_with_chamber: Equipment
    ) -> None:
        """
        Test export of equipment with chambers creates proper chamber elements.

        Parameters
        ----------
        module_context : ModuleContext
            The module context for the test.
        equipment_with_chamber : Equipment
            Equipment object with chambers to export.
        """
        exporter = EquipmentExporter(module_context, equipment_with_chamber)
        equipment_elem = exporter.compositional_pass()

        # Check equipment structure
        assert equipment_elem.tag == "Equipment"
        assert equipment_elem.get("ID") == "Equipment-Equipment-2"

        # Check chamber is exported as child element
        chamber_elems = equipment_elem.findall("Equipment")
        assert len(chamber_elems) == 1

        chamber_elem = chamber_elems[0]
        assert chamber_elem.get("ID") == "Chamber-Chamber-1"
        assert chamber_elem.get("ComponentClass") == "Chamber"

        # Check that chamber is registered in registry
        assert module_context.element_registry.get_element("Chamber-1") is not None

    def test_reference_pass_propagation(
        self, module_context: ModuleContext, equipment_with_nozzles: Pump
    ) -> None:
        """
        Test that reference_pass is properly called on all submodules.

        Parameters
        ----------
        module_context : ModuleContext
            The module context for the test.
        equipment_with_nozzles : Pump
            Equipment with nozzles for reference testing.
        """
        # Create a chamber and register it for nozzle association test
        chamber = Chamber(id="Chamber-Test")
        chamber_elem = ET.Element("Equipment")
        chamber_elem.set("ID", "Chamber-Test")
        module_context.element_registry.register_element("Chamber-Test", chamber_elem)

        # Associate first nozzle with chamber
        equipment_with_nozzles.nozzles[0].chamber = chamber

        exporter = EquipmentExporter(module_context, equipment_with_nozzles)
        _ = exporter.compositional_pass()

        # Call reference pass which should propagate to nozzle exporters
        exporter.reference_pass()

        # Check that association was created on first nozzle
        nozzle1_elem = module_context.element_registry.get_element("Nozzle-1")
        assert nozzle1_elem is not None

        assoc_elem = next(
            (a for a in nozzle1_elem.findall("Association") if a.get("Type") == "is located in"),
            None,
        )
        assert assoc_elem is not None
        assert assoc_elem.get("ItemID") == "Chamber-Test"

    def test_proteus_id_usage(
        self, module_context: ModuleContext, simple_equipment: Equipment
    ) -> None:
        """
        Test that proteusId is used when available instead of id.

        Parameters
        ----------
        module_context : ModuleContext
            The module context for the test.
        simple_equipment : Equipment
            Equipment object to test ID handling.
        """
        simple_equipment.proteusId = "ProteusEquip-1"

        exporter = EquipmentExporter(module_context, simple_equipment)
        equipment_elem = exporter.compositional_pass()

        # Element should use proteusId for XML ID
        assert equipment_elem.get("ID") == "ProteusEquip-1"

        # But registry should still use original id as key
        assert module_context.element_registry.get_element("Equipment-1") is equipment_elem

    def test_generic_attributes_integration(
        self, module_context: ModuleContext, simple_equipment: Equipment
    ) -> None:
        """
        Test that GenericAttributeExporter is properly integrated.

        Parameters
        ----------
        module_context : ModuleContext
            The module context for the test.
        simple_equipment : Equipment
            Equipment object with attributes to export.
        """
        exporter = EquipmentExporter(module_context, simple_equipment)
        equipment_elem = exporter.compositional_pass()

        # Should have DexpiAttributes for tagName
        dexpi_attrs = equipment_elem.find("GenericAttributes")
        assert dexpi_attrs is not None

        tag_name_attr = next(
            (
                attr
                for attr in dexpi_attrs.findall("GenericAttribute")
                if attr.get("Name") == "TagNameAssignmentClass"
            ),
            None,
        )
        assert tag_name_attr is not None
        assert tag_name_attr.get("Value") == "E-101"

    def test_empty_equipment(self, module_context: ModuleContext) -> None:
        """
        Test export of equipment with minimal attributes.

        Parameters
        ----------
        module_context : ModuleContext
            The module context for the test.
        """
        minimal_equipment = Equipment(id="Minimal-Equipment")

        exporter = EquipmentExporter(module_context, minimal_equipment)
        equipment_elem = exporter.compositional_pass()

        # Should still create valid XML structure
        assert equipment_elem.tag == "Equipment"
        assert equipment_elem.get("ID") == "Equipment-Minimal-Equipment"
        assert equipment_elem.get("ComponentClass") == "Equipment"

        # Should not have DexpiAttributes since no data attributes
        dexpi_attrs = equipment_elem.find("DexpiAttributes")
        assert dexpi_attrs is None

        # Should be registered
        assert module_context.element_registry.get_element("Minimal-Equipment") is equipment_elem

    def test_submodule_registration(
        self, module_context: ModuleContext, equipment_with_nozzles: Pump
    ) -> None:
        """
        Test that nozzle exporters are properly registered as submodules.

        Parameters
        ----------
        module_context : ModuleContext
            The module context for the test.
        equipment_with_nozzles : Pump
            Equipment with nozzles for submodule testing.
        """
        exporter = EquipmentExporter(module_context, equipment_with_nozzles)

        # Check that nozzle exporters were created and registered
        assert len(exporter.nozzle_exporters) == 2
        assert len(exporter.submodules) == 2  # All nozzle exporters should be in submodules

        # Verify they are NozzleExporter instances
        for nozzle_exporter in exporter.nozzle_exporters:
            assert isinstance(nozzle_exporter, NozzleExporter)
            assert nozzle_exporter in exporter.submodules

    def test_complex_equipment_hierarchy(self, module_context: ModuleContext) -> None:
        """
        Test export of equipment with both nozzles and chambers.

        Parameters
        ----------
        module_context : ModuleContext
            The module context for the test.
        """
        # Create complex equipment with nozzles and chambers
        nozzle = Nozzle(id="Complex-Nozzle", subTagName="N1")
        chamber = Chamber(id="Complex-Chamber", tagName="C-Complex")
        nozzle.chamber = chamber

        complex_equipment = Equipment(
            id="Complex-Equipment", tagName="E-Complex", nozzles=[nozzle], chambers=[chamber]
        )

        exporter = EquipmentExporter(module_context, complex_equipment)
        equipment_elem = exporter.compositional_pass()
        exporter.reference_pass()

        # Check main equipment
        assert equipment_elem.get("ID") == "Equipment-Complex-Equipment"

        # Check nozzle child element
        nozzle_elems = equipment_elem.findall("Nozzle")
        assert len(nozzle_elems) == 1

        nozzle_elem = nozzle_elems[0]
        assert nozzle_elem.get("ID") == "Nozzle-Complex-Nozzle"

        # Check chamber child element
        chamber_elems = equipment_elem.findall("Equipment")
        assert len(chamber_elems) == 1

        chamber_elem = chamber_elems[0]
        assert chamber_elem.get("ID") == "Chamber-Complex-Chamber"

        # Verify that the nozzle element references the chamber
        nozzle_assocs = nozzle_elem.findall("Association")
        assert len(nozzle_assocs) == 1

        nozzle_assoc = nozzle_assocs[0]
        assert nozzle_assoc.get("ItemID") == chamber_elem.get("ID")

        # Verify that the chamber element references the nozzle
        chamber_assocs = chamber_elem.findall("Association")
        assert len(chamber_assocs) == 1

        chamber_assoc = chamber_assocs[0]
        assert chamber_assoc.get("ItemID") == nozzle_elem.get("ID")


class TestPlantModelExporter:
    """
    Tests for PlantModelExporter functionality.

    Validates structure creation, PlantInformation override behavior, submodule registration,
    and reference pass propagation through equipment and nozzles.

    Fixtures
    --------
    model_with_meta_and_pump : object
        Minimal DEXPI-like model with MetaData and a Pump.
    """

    @pytest.fixture
    def model_with_meta_and_pump(self) -> object:
        """
        Build a minimal Dexpi-like model object for testing.

        Returns
        -------
        object
            An object with the attributes required by PlantModelExporter.
        """
        meta = MetaData(id="Meta-1", proteusId="Meta-1")
        nozzle = Nozzle(id="Noz-1", proteusId="Noz-1", subTagName="N1")
        chamber = Chamber(id="Ch-1", proteusId="Ch-1", tagName="CH-101")
        pump = Pump(
            id="Pump-1", proteusId="Pump-1", tagName="P-101", nozzles=[nozzle], chambers=[chamber]
        )

        export_dt = datetime.datetime(2023, 10, 1, 15, 30, 0)

        conceptual_model = type(
            "CM",
            (),
            {"metaData": meta, "taggedPlantItems": [pump]},
        )()
        model = type(
            "Model",
            (),
            {
                "conceptualModel": conceptual_model,
                "originatingSystemName": "OrigSys",
                "originatingSystemVersion": "1.0",
                "originatingSystemVendorName": "VendorCo",
                "exportDateTime": export_dt,
            },
        )()
        # Link nozzle chamber for later association test
        pump.nozzles[0].chamber = chamber
        return model

    def test_compositional_pass_builds_plant_model(
        self, module_context: ModuleContext, model_with_meta_and_pump: object
    ) -> None:
        """
        Ensure compositional_pass creates PlantModel with PlantInformation, MetaData, and Equipment.

        Parameters
        ----------
        module_context : ModuleContext
            The module context for the test.
        model_with_meta_and_pump : object
            Minimal model with metadata and one pump.
        """
        exporter = PlantModelExporter(
            module_context, model_with_meta_and_pump, override_export_info=False
        )
        root = exporter.compositional_pass()

        assert root.tag == "PlantModel"

        # PlantInformation with provided values (override_export_info=False)
        pi = root.find("PlantInformation")
        assert pi is not None
        assert pi.get("OriginatingSystem") == "OrigSys"
        assert pi.get("OriginatingSystemVersion") == "1.0"
        assert pi.get("OriginatingSystemVendor") == "VendorCo"
        assert pi.get("Date") == "2023-10-01"
        assert pi.get("Time") == "15:30:00"

        # MetaData present
        md = root.find("MetaData")
        assert md is not None
        assert md.get("ComponentClass") == "MetaData"
        assert md.get("ID") == "Meta-1"

        # Equipment exported
        eqs = root.findall("Equipment")
        assert len(eqs) >= 1
        pump_elem = next((e for e in eqs if e.get("ID") == "Pump-1"), None)
        assert pump_elem is not None

        # Nozzle under equipment
        noz = pump_elem.find("Nozzle")
        assert noz is not None
        assert noz.get("ID") == "Noz-1"

    def test_plant_information_override_defaults(
        self, module_context: ModuleContext, model_with_meta_and_pump: object
    ) -> None:
        """
        Validate PlantInformation default fields when override_export_info=True.

        Parameters
        ----------
        module_context : ModuleContext
            The module context for the test.
        model_with_meta_and_pump : object
            Minimal model with metadata and one pump.
        """
        exporter = PlantModelExporter(
            module_context, model_with_meta_and_pump, override_export_info=True
        )
        root = exporter.compositional_pass()
        pi = root.find("PlantInformation")
        assert pi is not None

        # Fixed defaults
        assert pi.get("Application") == "Dexpi"
        assert pi.get("ApplicationVersion") == "1.3.1"
        assert pi.get("Discipline") == "PID"
        assert pi.get("Is3D") == "no"
        assert pi.get("SchemaVersion") == "4.1.1"
        assert pi.get("Units") == "mm"
        assert pi.get("OriginatingSystem") == "pyDEXPI"

        # Version is sourced from pyproject, just ensure it exists and is non-empty
        osv = pi.get("OriginatingSystemVersion")
        assert isinstance(osv, str) and len(osv) > 0

        # Vendor matches constant
        assert pi.get("OriginatingSystemVendor") == "Process Intelligence Research"

        # Date/time present and formatted
        assert pi.get("Date") is not None
        assert pi.get("Time") is not None

    def test_submodule_registration(
        self, module_context: ModuleContext, model_with_meta_and_pump: object
    ) -> None:
        """
        Ensure metadata and equipment exporters are registered as submodules.

        Parameters
        ----------
        module_context : ModuleContext
            The module context for the test.
        model_with_meta_and_pump : object
            Minimal model with metadata and one pump.
        """
        exporter = PlantModelExporter(
            module_context, model_with_meta_and_pump, override_export_info=False
        )

        # MetaData exporter should be present as submodule
        submods = exporter.submodules
        assert any(isinstance(sm, MetaDataExporter) for sm in submods)

        # Equipment exporter(s) should be present as submodules
        assert any(isinstance(sm, EquipmentExporter) for sm in submods)
        assert len([sm for sm in submods if isinstance(sm, EquipmentExporter)]) == 1

    def test_reference_pass_propagates_to_nozzles(
        self, module_context: ModuleContext, model_with_meta_and_pump: object
    ) -> None:
        """
        Verify reference_pass propagates to nozzle exporters creating associations.

        Parameters
        ----------
        module_context : ModuleContext
            The module context for the test.
        model_with_meta_and_pump : object
            Minimal model with metadata and one pump.
        """
        exporter = PlantModelExporter(
            module_context, model_with_meta_and_pump, override_export_info=False
        )
        _ = exporter.compositional_pass()

        # Run reference pass to add associations (nozzle -> chamber and reciprocal)
        exporter.reference_pass()

        # Find nozzle and chamber elements (should be registered by sub-exporters)
        nozzle_elem = module_context.element_registry.get_element("Noz-1")
        chamber_elem = module_context.element_registry.get_element("Ch-1")

        assert nozzle_elem is not None
        assert chamber_elem is not None

        # Nozzle should have association to chamber
        assoc_nozzle = next(
            (a for a in nozzle_elem.findall("Association") if a.get("Type") == "is located in"),
            None,
        )
        assert assoc_nozzle is not None
        assert assoc_nozzle.get("ItemID") == "Ch-1"

        # Chamber should have reciprocal association to nozzle
        assoc_chamber = next(
            (
                a
                for a in chamber_elem.findall("Association")
                if a.get("Type") == "is the location of"
            ),
            None,
        )
        assert assoc_chamber is not None
        assert assoc_chamber.get("ItemID") == nozzle_elem.get("ID")
