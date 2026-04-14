"""Contains the modules of the Proteus XML exporter."""

import datetime
import tomllib
import xml.etree.ElementTree as ET

import pydexpi.toolkits.base_model_utils as bmu
from pydexpi.dexpi_classes import equipment
from pydexpi.dexpi_classes.pydantic_classes import (
    CustomAttributeOwner,
    DexpiBaseModel,
    DexpiDataTypeBaseModel,
    DexpiModel,
    Equipment,
    MetaData,
    Nozzle,
    NozzleOwner,
    TaggedPlantItem,
)
from pydexpi.loaders.proteus_serializer.proteus_exporter.core import (
    ExporterModule,
    ModuleContext,
)
from pydexpi.loaders.proteus_serializer.proteus_exporter.exporter_utils import (
    _attribute_mappings,
    add_association_elements,
    make_default_component_class_uri,
)


### GENERIC MODULES ###
class GenericAttributeExporter(ExporterModule):
    """Exporter module for handling GenericAttributes and CustomAttributes.

    This module exports the attributes of a DEXPI object into GenericAttribute XML elements.
    If the object has custom attributes, they are exported into a separate CustomAttributes element.

    Attributes
    ----------
    attribute_owner : DexpiBaseModel | DexpiDataTypeBaseModel
        The DEXPI object whose attributes are to be exported
    dexpi_attributes : ET.Element | None
        The XML element containing the GenericAttributes
    """

    def __init__(
        self,
        context: ModuleContext,
        attribute_owner: DexpiBaseModel | DexpiDataTypeBaseModel,
    ):
        """Initialize the GenericAttributeExporter.

        Parameters
        ----------
        attribute_owner : DexpiBaseModel | DexpiDataTypeBaseModel
            The DEXPI object whose attributes are to be exported
        context : ModuleContext
            The context for the exporter module, containing the element registry and other settings
        """
        super().__init__(context)
        self.attribute_owner = attribute_owner

        self.dexpi_attributes: ET.Element | None = None
        self.custom_attributes: ET.Element | None = None

    def compose_and_add_attributes(self, parent_element: ET.Element) -> None:
        """Utility method to compose and directly add attributes to a parent XML element.

        Also manages custom attributes if there are any.

        Parameters
        ----------
        parent_element : ET.Element
            The parent XML element to which attributes will be added
        """
        # Export generic attributes
        dexpi_attributes = self.compositional_pass()
        if dexpi_attributes is not None:
            parent_element.append(dexpi_attributes)

        # Export custom attributes
        custom_attributes = self.get_custom_attributes()
        if custom_attributes is not None:
            parent_element.append(custom_attributes)

    def compositional_pass(self) -> ET.Element | None:
        """Create and return the GenericAttributes element for the attribute owner.

        The method also creates the CustomAttributes element if applicable, which can be retrieved
        separately using `get_custom_attributes()`.

        Returns
        -------
        ET.Element | None
            The XML element containing the GenericAttributes. None if no generic attributes exist
        """
        # Make generic attributes and custom attributes
        self.dexpi_attributes = self._export_generic_attributes(self.attribute_owner)

        return self.dexpi_attributes

    def get_custom_attributes(self) -> ET.Element | None:
        """Get the CustomAttributes element if it exists.

        Returns
        -------
        ET.Element | None
            The CustomAttributes XML element or None if not created
        """
        if isinstance(self.attribute_owner, CustomAttributeOwner):
            self.custom_attributes = self._export_custom_attributes(self.attribute_owner)
        return self.custom_attributes

    def _export_generic_attributes(
        self, obj: DexpiBaseModel | DexpiDataTypeBaseModel
    ) -> ET.Element | None:
        """Export generic attributes as GenericAttribute elements.

        This method converts the attributes of the given DEXPI object into GenericAttribute XML
        elements based on predefined mappings or default formatting.

        Parameters
        ----------
        obj : DexpiBaseModel | DexpiDataTypeBaseModel
            The DEXPI object containing attributes to export
        """
        dexpi_attributes = ET.Element("GenericAttributes")
        dexpi_attributes.set("Set", "DexpiAttributes")

        data_attributes = bmu.get_data_attributes(obj)
        for field_name, field_value in data_attributes.items():
            if field_value is None:
                continue
            attribute_element = ET.SubElement(dexpi_attributes, "GenericAttribute")
            attribute_type = type(field_value).__name__

            # Retrieve name and uri from mapping if available, else use default formatting
            proteus_nomencl_mapping = _attribute_mappings.get(field_name)
            if proteus_nomencl_mapping:
                attribute_name = proteus_nomencl_mapping["name"]
                attribute_uri = proteus_nomencl_mapping["uri"]
            else:
                attribute_name = self._convert_to_assignment_class(field_name)
                attribute_uri = f"http://sandbox.dexpi.org/rdl/{attribute_name}"

            if isinstance(field_value, DexpiDataTypeBaseModel):
                attribute_element.set("Name", attribute_name)
                attribute_element.set("AttributeURI", attribute_uri)

                try:
                    attribute_num_value = field_value.value
                    num_value_format = type(attribute_num_value).__name__.lower()
                    num_value_format = self._primitive_data_type_mapping(num_value_format)
                    attribute_unit = field_value.unit.name

                    attribute_element.set("Format", num_value_format)
                    attribute_element.set("Value", str(attribute_num_value))
                    attribute_element.set("Units", attribute_unit)
                    attribute_element.set(
                        "UnitsURI", ""
                    )  # TODO: include unit URIs from a central registry

                # Case: Null object (e.g. NullablePressure): Dont add further attributes
                except AttributeError:
                    pass

            else:
                # Case: Basic data type
                attribute_type = self._primitive_data_type_mapping(attribute_type)

                attribute_element.set("Name", attribute_name)
                attribute_element.set("AttributeURI", attribute_uri)
                if field_value is not None:
                    attribute_element.set("Format", attribute_type)
                    attribute_element.set("Value", str(field_value))

        # Return none if no attributes were added
        no_attrs = len(dexpi_attributes)
        if no_attrs == 0:
            return None

        dexpi_attributes.set("Number", str(no_attrs))

        return dexpi_attributes

    def _export_custom_attributes(self, obj: CustomAttributeOwner) -> ET.Element | None:
        """Export custom attributes as CustomAttribute elements.

        This method converts any custom attributes of the given DEXPI object into GenericAttribute
        XML elements in a CustomAttributes container.

        Parameters
        ----------
        obj : CustomAttributeOwner
            The DEXPI object containing attributes to export

        Returns
        -------
        ET.Element | None
            The XML element containing CustomAttributes or None if no custom attributes exist
        """
        if not obj.customAttributes:
            return None

        custom_attributes = ET.Element("GenericAttributes")
        custom_attributes.set("Set", "CustomAttributes")

        for custom_attr in obj.customAttributes:
            # Retrieve the details of the custom attribute wrapper class
            attribute_element = ET.SubElement(custom_attributes, "GenericAttribute")
            attribute_name = custom_attr.attributeName
            attribute_uri = custom_attr.attributeURI
            attribute_type = type(custom_attr).__name__

            # Manage the custom attribute value, which can be a basic type or a
            # DexpiDataTypeBaseModel
            attribute_value = custom_attr.value
            if isinstance(attribute_value, DexpiDataTypeBaseModel):
                attribute_element.set("Name", attribute_name)
                attribute_element.set("AttributeURI", attribute_uri)
                attribute_element.set("Type", type(attribute_value).__name__)

                # Normal case: Not the null object (e.g. Pressure)
                try:
                    attribute_num_value = attribute_value.value
                    num_value_format = type(attribute_num_value).__name__.lower()
                    num_value_format = self._primitive_data_type_mapping(num_value_format)
                    attribute_unit = attribute_value.unit.name

                    attribute_element.set("Format", num_value_format)
                    attribute_element.set(
                        "TypeURI", ""
                    )  # TODO: include type URIs from a central registry
                    attribute_element.set("Value", str(attribute_num_value))
                    attribute_element.set("Units", attribute_unit)
                    attribute_element.set(
                        "UnitsURI", ""
                    )  # TODO: include unit URIs from a central registry

                # Case: Null object (e.g. NullPressure): Dont add further attributes
                except AttributeError:
                    pass

            else:
                # Case: Basic data type
                attribute_type = self._primitive_data_type_mapping(attribute_type)

                attribute_element.set("Name", attribute_name)
                attribute_element.set("AttributeURI", attribute_uri)
                if attribute_value is not None:
                    attribute_element.set("Format", attribute_type)
                    attribute_element.set("Value", str(attribute_value))

        custom_attributes.set("Number", str(len(custom_attributes)))
        return custom_attributes

    def _primitive_data_type_mapping(self, data_type_name: str) -> str:
        """Map a Python primitive data type to its corresponding XML Format and Type.

        Parameters
        ----------
        value : Any
            The value whose type is to be mapped

        Returns
        -------
        tuple[str, str]
            A tuple containing the XML Format and Type as strings
        """
        if data_type_name == "str":
            return "string"
        elif data_type_name == "bool":
            return "boolean"
        elif data_type_name == "int":
            return "integer"
        elif data_type_name == "float":
            return "double"
        else:
            return "string"  # Default fallback

    def _convert_to_assignment_class(self, field_name: str) -> str:
        """Convert a field name to DEXPI assignment class format.

        Eg. "lineNumber" -> "LineNumberAssignmentClass"

        Parameters
        ----------
        field_name : str
            The original field name

        Returns
        -------
        str
            The Proteus assignment class name
        """
        result = field_name[0].capitalize() + field_name[1:] + "AssignmentClass"
        return result


### EQUIPMENT MODULES ###
class NozzleExporter(ExporterModule):
    """Exporter for Nozzle objects into Nozzle XML structure.

    Attributes
    ----------
    nozzle_object : Nozzle
        The Nozzle object to export
    generic_attribute_exporter : GenericAttributeExporter
        The exporter module for handling generic attributes
    """

    def __init__(self, context: ModuleContext, nozzle_object: Nozzle) -> None:
        """Initialize the NozzleExporter.

        Parameters
        ----------
        context : ModuleContext
            The context for the exporter module, containing the element registry and other settings
        nozzle_object : Nozzle
            The Nozzle object to export
        nozzle_element : ET.Element | None
            The XML element representing the Nozzle
        """
        super().__init__(context)
        self.nozzle_object = nozzle_object
        self.nozzle_element = None

        self.generic_attribute_exporter = GenericAttributeExporter(context, nozzle_object)

    def compositional_pass(self) -> ET.Element:
        """Export Nozzle to an XML element.

        Compose the generic attributes and register the Nozzle element.

        Parameters
        ----------
        obj : Nozzle
            The Nozzle object to export

        Returns
        -------
        ET.Element
            The XML element representing the Nozzle
        """
        nozzle_elem = ET.Element("Nozzle")
        proteus_id = self.make_id_attribute(self.nozzle_object)
        nozzle_elem.set("ID", proteus_id)
        nozzle_elem.set("ComponentClass", "Nozzle")
        nozzle_elem.set("ComponentClassURI", "http://data.posccaesar.org/rdl/RDS415214")

        # Parse and add generic attributes
        self.generic_attribute_exporter.compose_and_add_attributes(nozzle_elem)

        # Register the Nozzle element
        self.nozzle_element = nozzle_elem
        self.register_object(self.nozzle_object.id, nozzle_elem)

        return nozzle_elem

    def reference_pass(self):
        """Perform the reference pass for the Nozzle.

        Adds the reference to the associated Chamber if it exists."""
        # Make chamber references
        associated_chamber = self.nozzle_object.chamber
        if associated_chamber:
            chamber_elem = self.get_object_from_registry(associated_chamber.id)
            add_association_elements(
                self.nozzle_element, chamber_elem, "is located in", "is the location of"
            )


class EquipmentExporter(ExporterModule):
    """Exporter for Equipment objects into Equipment XML structure.

    Attributes
    ----------
    equipment_object : Equipment
        The Equipment object to export
    equipment_element : ET.Element | None
        The XML element representing the Equipment
    generic_attribute_exporter : GenericAttributeExporter
        The exporter module for handling generic attributes
    nozzle_exporters : list[NozzleExporter]
        List of NozzleExporter instances for the equipment's nozzles
    subequipment_exporters : list[EquipmentExporter]
        List of EquipmentExporter instances for the equipment's subequipments
    """

    def __init__(self, context: ModuleContext, equipment_object: TaggedPlantItem) -> None:
        """Initialize the EquipmentExporter.

        Parameters
        ----------
        context : ModuleContext
            The context for the exporter module, containing the element registry and other settings
        equipment_object : Equipment
            The Equipment object to export
        """
        super().__init__(context)
        self.equipment_object = equipment_object
        self.equipment_element = None

        self.generic_attribute_exporter = GenericAttributeExporter(context, equipment_object)

        # Initialize Nozzle exporters for all nozzles in the equipment
        self.nozzle_exporters: list[NozzleExporter] = []
        if isinstance(equipment_object, NozzleOwner) and equipment_object.nozzles:
            for nozzle in equipment_object.nozzles:
                nozzle_exporter = NozzleExporter(context, nozzle)
                self.nozzle_exporters.append(nozzle_exporter)
            self.register_submodule_list(self.nozzle_exporters)

        # Initialize subequipment exporters:
        self.subequipment_exporters: list[EquipmentExporter] = []
        compositional_attrs = bmu.get_composition_attributes(equipment_object)
        for field_name, field_value in compositional_attrs.items():
            if field_name == "nozzles":
                continue  # Nozzles are handled separately
            elif isinstance(field_value, list):
                for item in field_value:
                    if hasattr(equipment, type(item).__name__):
                        subeq_exporter = EquipmentExporter(context, item)
                        self.subequipment_exporters.append(subeq_exporter)
            elif isinstance(field_value, Equipment):
                subeq_exporter = EquipmentExporter(context, field_value)
                self.subequipment_exporters.append(subeq_exporter)

    def compositional_pass(self) -> ET.Element:
        """Export Equipment to an XML element.

        Compose the generic attributes, export nozzles, and register the Equipment element.

        Parameters
        ----------
        obj : Equipment
            The Equipment object to export

        Returns
        -------
        ET.Element
            The XML element representing the Equipment
        """
        equipment_elem = ET.Element("Equipment")
        proteus_id = self.make_id_attribute(self.equipment_object)
        equipment_elem.set("ID", proteus_id)
        equipment_elem.set("ComponentClass", type(self.equipment_object).__name__)
        equipment_elem.set(*make_default_component_class_uri(type(self.equipment_object).__name__))

        # Parse and add generic attributes
        self.generic_attribute_exporter.compose_and_add_attributes(equipment_elem)

        # Export and add nozzles as child elements
        for nozzle_exporter in self.nozzle_exporters:
            nozzle_elem = nozzle_exporter.compositional_pass()
            equipment_elem.append(nozzle_elem)

        # Export and add subequipments as child elements
        for subeq_exporter in self.subequipment_exporters:
            subeq_elem = subeq_exporter.compositional_pass()
            equipment_elem.append(subeq_elem)

        # Register the Equipment element
        self.register_object(self.equipment_object.id, equipment_elem)

        return equipment_elem


### MODEL-LEVEL EXPORTERS ###
class MetaDataExporter(ExporterModule):
    """Exporter for pyDEXPI Metadata objects into MetaData XML structure.

    Attributes
    ----------
    metadata_object : MetaData
        The MetaData object to export
    generic_attribute_exporter : GenericAttributeExporter
        The exporter module for handling generic attributes
    """

    def __init__(self, context: ModuleContext, metadata_object: MetaData) -> None:
        """Initialize the MetaDataExporter.

        Parameters
        ----------
        context : ModuleContext
            The context for the exporter module, containing the element registry and other settings
        metadata_object : MetaData
            The MetaData object to export
        """
        super().__init__(context)
        self.metadata_object = metadata_object

        self.generic_attribute_exporter = GenericAttributeExporter(context, metadata_object)

    def compositional_pass(self) -> ET.Element:
        """Export MetaData to an XML element.

        Compose the generic attributes and register the MetaData element.

        Parameters
        ----------
        obj : MetaData
            The MetaData object to export

        Returns
        -------
        ET.Element
            The XML element representing the MetaData
        """
        metadata_elem = ET.Element("MetaData")
        proteus_id = self.make_id_attribute(self.metadata_object)
        metadata_elem.set("ID", proteus_id)
        metadata_elem.set("ComponentClass", "MetaData")
        metadata_elem.set(*make_default_component_class_uri("MetaData"))

        # Parse and add generic attributes
        self.generic_attribute_exporter.compose_and_add_attributes(metadata_elem)

        # Register the MetaData element
        self.register_object(self.metadata_object.id, metadata_elem)

        return metadata_elem


class PlantModelExporter(ExporterModule):
    """Exporter for the top-level PlantModel XML structure.

    This module orchestrates the export of the entire DEXPI model into the PlantModel XML format.
    It utilizes submodules for each major component type to handle their specific export logic.

    Attributes
    ----------
    metadata_exporter : MetaDataExporter
        Exporter for MetaData objects

    """

    def __init__(
        self,
        context: ModuleContext,
        dexpi_model: DexpiModel,
        override_export_info: bool = False,
    ) -> None:
        """Initialize the PlantModelExporter.

        Parameters
        ----------
        context : ModuleContext
            The context for the exporter module, containing the element registry and other settings
        dexpi_model : DexpiModel
            The DEXPI model to export
        override_export_info : bool, optional
            Whether to override export information in the PlantInformation element,
            by default False
        """
        super().__init__(context)
        self.dexpi_model = dexpi_model
        self.plant_model_element = None
        self.override_export_info = override_export_info

        if dexpi_model.conceptualModel.metaData:
            self.metadata_exporter = MetaDataExporter(context, dexpi_model.conceptualModel.metaData)
            self.register_submodule(self.metadata_exporter)

        self.equipment_exporters: list[EquipmentExporter] = []
        for tagged_plant_item in dexpi_model.conceptualModel.taggedPlantItems:
            equipment_exporter = EquipmentExporter(context, tagged_plant_item)
            self.equipment_exporters.append(equipment_exporter)
        self.register_submodule_list(self.equipment_exporters)

    def compositional_pass(self):
        """Export a DexpiModel to the PlantModel XML structure.

        Parameters
        ----------
        obj : Any
            The DEXPI model to export

        Returns
        -------
        ET.Element
            The PlantModel XML element
        """
        plant_model = ET.Element("PlantModel")

        # Add PlantInformation
        plant_info = self._make_plant_information()
        plant_model.append(plant_info)

        # Add MetaData if exists
        if self.metadata_exporter:
            meta_data = self.metadata_exporter.compositional_pass()
            plant_model.append(meta_data)

        # Export taggedPlantItems
        for eqpmt in self.equipment_exporters:
            plant_model.append(eqpmt.compositional_pass())

        return plant_model

    def _make_plant_information(self) -> ET.Element:
        """Create the PlantInformation XML element from the DEXPI model's plant information.

        Parameters
        ----------
        obj : Any
            The DEXPI model containing plant information

        Returns
        -------
        ET.Element
            The PlantInformation XML element
        """
        plant_info = ET.Element("PlantInformation")
        _ = ET.SubElement(plant_info, "UnitsOfMeasure")

        # Add fixed fields
        plant_info.set("Application", "Dexpi")
        plant_info.set("ApplicationVersion", "1.3.1")
        plant_info.set("Discipline", "PID")
        plant_info.set("Is3D", "no")
        plant_info.set("SchemaVersion", "4.1.1")
        plant_info.set("Units", "mm")

        # Set model specific attributes
        if self.override_export_info:
            plant_info.set("OriginatingSystem", "pyDEXPI")

            with open("pyproject.toml", "rb") as f:
                pyproject_data = tomllib.load(f)
                app_version = pyproject_data["project"]["version"]
            plant_info.set("OriginatingSystemVersion", app_version)
            plant_info.set("OriginatingSystemVendor", "Process Intelligence Research")

            today = datetime.date.today()
            plant_info.set("Date", today.isoformat())

            now = datetime.datetime.now().time()
            plant_info.set("Time", now.strftime("%H:%M:%S"))

        else:
            plant_info.set("OriginatingSystem", self.dexpi_model.originatingSystemName)
            plant_info.set("OriginatingSystemVersion", self.dexpi_model.originatingSystemVersion)
            plant_info.set("OriginatingSystemVendor", self.dexpi_model.originatingSystemVendorName)
            date_and_time = self.dexpi_model.exportDateTime
            the_date = date_and_time.date()
            the_time = date_and_time.time()
            plant_info.set("Date", the_date.isoformat())
            plant_info.set("Time", the_time.strftime("%H:%M:%S"))

        return plant_info
