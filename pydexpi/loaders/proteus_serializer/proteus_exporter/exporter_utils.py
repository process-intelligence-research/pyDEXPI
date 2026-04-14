"""Utility functions for exporting to Proteus XML format."""

import xml.etree.ElementTree as ET


def make_default_component_class_uri(component_class: str) -> tuple[str, str]:
    """Generate a default component class URI.

    Parameters
    ----------
    component_class : str
        The component class name.

    Returns
    -------
    str
        The generated URI.
    """
    base_uri = "http://sandbox.dexpi.org/rdl/"
    return "ComponentClassURI", f"{base_uri}{component_class}"


def add_association_elements(
    source_element: ET.Element,
    target_element: ET.Element,
    source_assoc_type: str,
    target_assoc_type: str,
) -> None:
    """Create and add complementary Association XML elements to source and target.

    Parameters
    ----------
    source_element : ET.Element
        The source XML element.
    target_element : ET.Element
        The target XML element.
    source_assoc_type : str
        The source association type.
    target_assoc_type : str
        The target association type.

    Returns
    -------
    ET.Element
        The created Association XML element.
    """
    source_assoc_elem = ET.SubElement(source_element, "Association")
    source_assoc_elem.set("Type", source_assoc_type)
    source_assoc_elem.set("ItemID", target_element.get("ID"))

    target_assoc_elem = ET.SubElement(target_element, "Association")
    target_assoc_elem.set("Type", target_assoc_type)
    target_assoc_elem.set("ItemID", source_element.get("ID"))


# Define the mapping of model attributes to GenericAttribute XML format
# These mappings are based on the GenericAttributeParser's reverse transformation
_attribute_mappings = {
    # Basic Equipment-level attributes (high priority)
    "tagName": {
        "name": "TagNameAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/TagNameAssignmentClass",
        "format": "string",
    },
    "tagNamePrefix": {
        "name": "TagNamePrefixAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/TagNamePrefixAssignmentClass",
        "format": "string",
    },
    "tagNameSequenceNumber": {
        "name": "TagNameSequenceNumberAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/TagNameSequenceNumberAssignmentClass",
        "format": "string",
    },
    "tagNameSuffix": {
        "name": "TagNameSuffixAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/TagNameSuffixAssignmentClass",
        "format": "string",
    },
    # Nozzle-level attributes
    "subTagName": {
        "name": "SubTagNameAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/SubTagNameAssignmentClass",
        "format": "string",
    },
    # Design parameters (engineering critical)
    "designPressure": {
        "name": "DesignPressure",
        "uri": "http://sandbox.dexpi.org/rdl/DesignPressure",
        "format": "double",
    },
    "designTemperature": {
        "name": "DesignTemperature",
        "uri": "http://sandbox.dexpi.org/rdl/DesignTemperature",
        "format": "double",
    },
    "nominalDiameter": {
        "name": "NominalDiameter",
        "uri": "http://sandbox.dexpi.org/rdl/NominalDiameter",
        "format": "double",
    },
    # High-priority nominal diameter family (90+ instances each in C01V04)
    "nominalDiameterNumericalValueRepresentation": {
        "name": "NominalDiameterNumericalValueRepresentationAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/NominalDiameterNumericalValueRepresentationAssignmentClass",
        "format": "string",
    },
    "nominalDiameterRepresentation": {
        "name": "NominalDiameterRepresentationAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/NominalDiameterRepresentationAssignmentClass",
        "format": "string",
    },
    "nominalDiameterStandard": {
        "name": "NominalDiameterStandardSpecialization",
        "uri": "http://sandbox.dexpi.org/rdl/NominalDiameterStandardSpecialization",
        "format": "string",
    },
    "nominalDiameterTypeRepresentation": {
        "name": "NominalDiameterTypeRepresentationAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/NominalDiameterTypeRepresentationAssignmentClass",
        "format": "string",
    },
    # Piping attributes (very common in complex files)
    "lineNumber": {
        "name": "LineNumberAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/LineNumberAssignmentClass",
        "format": "string",
    },
    "fluidCode": {
        "name": "FluidCodeAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/FluidCodeAssignmentClass",
        "format": "string",
    },
    "pipingClassCode": {
        "name": "PipingClassCodeAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/PipingClassCodeAssignmentClass",
        "format": "string",
    },
    "materialOfConstructionCode": {
        "name": "MaterialOfConstructionCodeAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/MaterialOfConstructionCodeAssignmentClass",
        "format": "string",
    },
    # Instrumentation attributes (important for control systems)
    "instrumentationLoopFunctionNumber": {
        "name": "InstrumentationLoopFunctionNumberAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/InstrumentationLoopFunctionNumberAssignmentClass",
        "format": "string",
    },
    "processInstrumentationFunctionNumber": {
        "name": "ProcessInstrumentationFunctionNumberAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/ProcessInstrumentationFunctionNumberAssignmentClass",
        "format": "string",
    },
    "deviceTypeName": {
        "name": "DeviceTypeNameAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/DeviceTypeNameAssignmentClass",
        "format": "string",
    },
    # Instrumentation attributes (process control and measurement functions)
    "processInstrumentationFunctionCategory": {
        "name": "ProcessInstrumentationFunctionCategoryAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/ProcessInstrumentationFunctionCategoryAssignmentClass",
        "format": "string",
    },
    "processInstrumentationFunctions": {
        "name": "ProcessInstrumentationFunctionsAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/ProcessInstrumentationFunctionsAssignmentClass",
        "format": "string",
    },
    "actuatingSystemNumber": {
        "name": "ActuatingSystemNumberAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/ActuatingSystemNumberAssignmentClass",
        "format": "string",
    },
    "failAction": {
        "name": "FailActionSpecialization",
        "uri": "http://sandbox.dexpi.org/rdl/FailActionSpecialization",
        "format": "string",
    },
    "failActionRepresentation": {
        "name": "FailActionRepresentationAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/FailActionRepresentationAssignmentClass",
        "format": "string",
    },
    "processSignalGeneratingFunctionNumber": {
        "name": "ProcessSignalGeneratingFunctionNumberAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/ProcessSignalGeneratingFunctionNumberAssignmentClass",
        "format": "string",
    },
    "actuatingFunctionNumber": {
        "name": "ActuatingFunctionNumberAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/ActuatingFunctionNumberAssignmentClass",
        "format": "string",
    },
    # Design parameters (pressure and temperature limits)
    "lowerLimitDesignPressure": {
        "name": "LowerLimitDesignPressure",
        "uri": "http://sandbox.dexpi.org/rdl/LowerLimitDesignPressure",
        "format": "double",
    },
    "upperLimitDesignPressure": {
        "name": "UpperLimitDesignPressure",
        "uri": "http://sandbox.dexpi.org/rdl/UpperLimitDesignPressure",
        "format": "double",
    },
    "lowerLimitDesignTemperature": {
        "name": "LowerLimitDesignTemperature",
        "uri": "http://sandbox.dexpi.org/rdl/LowerLimitDesignTemperature",
        "format": "double",
    },
    "upperLimitDesignTemperature": {
        "name": "UpperLimitDesignTemperature",
        "uri": "http://sandbox.dexpi.org/rdl/UpperLimitDesignTemperature",
        "format": "double",
    },
    # Component identification and naming
    "pipingComponentName": {
        "name": "PipingComponentNameAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/PipingComponentNameAssignmentClass",
        "format": "string",
    },
    "symbolRegistrationNumber": {
        "name": "SymbolRegistrationNumberAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/SymbolRegistrationNumberAssignmentClass",
        "format": "string",
    },
    # Insulation and material properties
    "insulationThickness": {
        "name": "InsulationThickness",
        "uri": "http://sandbox.dexpi.org/rdl/InsulationThickness",
        "format": "double",
    },
    "insulationType": {
        "name": "InsulationTypeAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/InsulationTypeAssignmentClass",
        "format": "string",
    },
    # Equipment design parameters
    "designHeatFlowRate": {
        "name": "DesignHeatFlowRate",
        "uri": "http://sandbox.dexpi.org/rdl/DesignHeatFlowRate",
        "format": "double",
    },
    "designVolumeFlowRate": {
        "name": "DesignVolumeFlowRate",
        "uri": "http://sandbox.dexpi.org/rdl/DesignVolumeFlowRate",
        "format": "double",
    },
    # Location and project information
    "locationSpecialization": {
        "name": "LocationSpecialization",
        "uri": "http://sandbox.dexpi.org/rdl/LocationSpecialization",
        "format": "string",
    },
    "projectName": {
        "name": "ProjectNameAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/ProjectNameAssignmentClass",
        "format": "string",
    },
    "enterpriseIdentificationCode": {
        "name": "EnterpriseIdentificationCodeAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/EnterpriseIdentificationCodeAssignmentClass",
        "format": "string",
    },
    # Documentation and approval attributes
    "approvalDescription": {
        "name": "ApprovalDescriptionAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/ApprovalDescriptionAssignmentClass",
        "format": "string",
    },
    "drawingSubTitle": {
        "name": "DrawingSubTitleAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/DrawingSubTitleAssignmentClass",
        "format": "string",
    },
    # Equipment design specifications
    "designHeatTransferArea": {
        "name": "DesignHeatTransferArea",
        "uri": "http://sandbox.dexpi.org/rdl/DesignHeatTransferArea",
        "format": "double",
    },
    "designPressureHead": {
        "name": "DesignPressureHead",
        "uri": "http://sandbox.dexpi.org/rdl/DesignPressureHead",
        "format": "double",
    },
    "designRotationalSpeed": {
        "name": "DesignRotationalSpeed",
        "uri": "http://sandbox.dexpi.org/rdl/DesignRotationalSpeed",
        "format": "double",
    },
    "designShaftPower": {
        "name": "DesignShaftPower",
        "uri": "http://sandbox.dexpi.org/rdl/DesignShaftPower",
        "format": "double",
    },
    # Comprehensive documentation and metadata attributes
    "approvalDate": {
        "name": "ApprovalDateRepresentationAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/ApprovalDateRepresentationAssignmentClass",
        "format": "string",
    },
    "approverName": {
        "name": "ApproverNameAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/ApproverNameAssignmentClass",
        "format": "string",
    },
    "archiveNumber": {
        "name": "ArchiveNumberAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/ArchiveNumberAssignmentClass",
        "format": "string",
    },
    "blockName": {
        "name": "BlockNameAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/BlockNameAssignmentClass",
        "format": "string",
    },
    "blockNumber": {
        "name": "BlockNumberAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/BlockNumberAssignmentClass",
        "format": "string",
    },
    "checkerName": {
        "name": "CheckerNameAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/CheckerNameAssignmentClass",
        "format": "string",
    },
    "confidentialitySpecialization": {
        "name": "ConfidentialitySpecialization",
        "uri": "http://sandbox.dexpi.org/rdl/ConfidentialitySpecialization",
        "format": "string",
    },
    "creationDate": {
        "name": "CreationDateRepresentationAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/CreationDateRepresentationAssignmentClass",
        "format": "string",
    },
    "creatorName": {
        "name": "CreatorNameAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/CreatorNameAssignmentClass",
        "format": "string",
    },
    "designerName": {
        "name": "DesignerNameAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/DesignerNameAssignmentClass",
        "format": "string",
    },
    "drafterName": {
        "name": "DrafterNameAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/DrafterNameAssignmentClass",
        "format": "string",
    },
    "drawingName": {
        "name": "DrawingNameAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/DrawingNameAssignmentClass",
        "format": "string",
    },
    "drawingNumber": {
        "name": "DrawingNumberAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/DrawingNumberAssignmentClass",
        "format": "string",
    },
    "enterpriseName": {
        "name": "EnterpriseNameAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/EnterpriseNameAssignmentClass",
        "format": "string",
    },
    "fileName": {
        "name": "FileNameAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/FileNameAssignmentClass",
        "format": "string",
    },
    # Plant hierarchy and organization attributes
    "industrialComplexIdentificationCode": {
        "name": "IndustrialComplexIdentificationCodeAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/IndustrialComplexIdentificationCodeAssignmentClass",
        "format": "string",
    },
    "industrialComplexName": {
        "name": "IndustrialComplexNameAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/IndustrialComplexNameAssignmentClass",
        "format": "string",
    },
    "lastModificationDate": {
        "name": "LastModificationDateRepresentationAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/LastModificationDateRepresentationAssignmentClass",
        "format": "string",
    },
    "locationName": {
        "name": "LocationNameAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/LocationNameAssignmentClass",
        "format": "string",
    },
    "plantAreaIdentificationCode": {
        "name": "PlantAreaIdentificationCodeAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/PlantAreaIdentificationCodeAssignmentClass",
        "format": "string",
    },
    "areaIsa95Name": {
        "name": "AreaIsa95NameAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/AreaIsa95NameAssignmentClass",
        "format": "string",
    },
    "plantSectionIdentificationCode": {
        "name": "PlantSectionIdentificationCodeAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/PlantSectionIdentificationCodeAssignmentClass",
        "format": "string",
    },
    "plantSectionName": {
        "name": "PlantSectionNameAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/PlantSectionNameAssignmentClass",
        "format": "string",
    },
    "plantSystemIdentificationCode": {
        "name": "PlantSystemIdentificationCodeAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/PlantSystemIdentificationCodeAssignmentClass",
        "format": "string",
    },
    "plantSystemName": {
        "name": "PlantSystemNameAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/PlantSystemNameAssignmentClass",
        "format": "string",
    },
    "plantTrainIdentificationCode": {
        "name": "PlantTrainIdentificationCodeAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/PlantTrainIdentificationCodeAssignmentClass",
        "format": "string",
    },
    "plantTrainName": {
        "name": "PlantTrainNameAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/PlantTrainNameAssignmentClass",
        "format": "string",
    },
    "processCellIdentificationCode": {
        "name": "ProcessCellIdentificationCodeAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/ProcessCellIdentificationCodeAssignmentClass",
        "format": "string",
    },
    "processCellName": {
        "name": "ProcessCellNameAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/ProcessCellNameAssignmentClass",
        "format": "string",
    },
    "processPlantIdentificationCode": {
        "name": "ProcessPlantIdentificationCodeAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/ProcessPlantIdentificationCodeAssignmentClass",
        "format": "string",
    },
    "processPlantName": {
        "name": "ProcessPlantNameAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/ProcessPlantNameAssignmentClass",
        "format": "string",
    },
    # Project management attributes
    "projectNumber": {
        "name": "ProjectNumberAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/ProjectNumberAssignmentClass",
        "format": "string",
    },
    "projectRangeNumber": {
        "name": "ProjectRangeNumberAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/ProjectRangeNumberAssignmentClass",
        "format": "string",
    },
    "replacedDrawing": {
        "name": "ReplacedDrawingAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/ReplacedDrawingAssignmentClass",
        "format": "string",
    },
    "responsibleDepartmentName": {
        "name": "ResponsibleDepartmentNameAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/ResponsibleDepartmentNameAssignmentClass",
        "format": "string",
    },
    "revisionNumber": {
        "name": "RevisionNumberAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/RevisionNumberAssignmentClass",
        "format": "string",
    },
    "sheetFormat": {
        "name": "SheetFormatAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/SheetFormatAssignmentClass",
        "format": "string",
    },
    "sheetNumber": {
        "name": "SheetNumberAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/SheetNumberAssignmentClass",
        "format": "string",
    },
    "siteIdentificationCode": {
        "name": "SiteIdentificationCodeAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/SiteIdentificationCodeAssignmentClass",
        "format": "string",
    },
    "siteName": {
        "name": "SiteNameAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/SiteNameAssignmentClass",
        "format": "string",
    },
    "subProjectName": {
        "name": "SubProjectNameAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/SubProjectNameAssignmentClass",
        "format": "string",
    },
    "subProjectNumber": {
        "name": "SubProjectNumberAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/SubProjectNumberAssignmentClass",
        "format": "string",
    },
    "totalNumberOfSheets": {
        "name": "TotalNumberOfSheets",
        "uri": "http://sandbox.dexpi.org/rdl/TotalNumberOfSheets",
        "format": "integer",
    },
    "unitIdentificationCode": {
        "name": "UnitIdentificationCodeAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/UnitIdentificationCodeAssignmentClass",
        "format": "string",
    },
    "unitIsa95Name": {
        "name": "UnitIsa95NameAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/UnitIsa95NameAssignmentClass",
        "format": "string",
    },
    # Equipment-specific design parameters
    "positionNumber": {
        "name": "PositionNumberAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/PositionNumberAssignmentClass",
        "format": "string",
    },
    "setPressureHigh": {
        "name": "SetPressureHigh",
        "uri": "http://sandbox.dexpi.org/rdl/SetPressureHigh",
        "format": "double",
    },
    "plateHeight": {
        "name": "PlateHeight",
        "uri": "http://sandbox.dexpi.org/rdl/PlateHeight",
        "format": "double",
    },
    "plateWidth": {
        "name": "PlateWidth",
        "uri": "http://sandbox.dexpi.org/rdl/PlateWidth",
        "format": "double",
    },
    "tubeLength": {
        "name": "TubeLength",
        "uri": "http://sandbox.dexpi.org/rdl/TubeLength",
        "format": "double",
    },
    "tubeMaterialOfConstructionCode": {
        "name": "TubeMaterialOfConstructionCodeAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/TubeMaterialOfConstructionCodeAssignmentClass",
        "format": "string",
    },
    "cylinderLength": {
        "name": "CylinderLength",
        "uri": "http://sandbox.dexpi.org/rdl/CylinderLength",
        "format": "double",
    },
    "nominalCapacityVolume": {
        "name": "NominalCapacity(Volume)",
        "uri": "http://sandbox.dexpi.org/rdl/NominalCapacityVolume",
        "format": "double",
    },
    # Segment attributes (critical for piping systems)
    "segmentNumber": {
        "name": "SegmentNumberAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/SegmentNumberAssignmentClass",
        "format": "string",
    },
    "primarySecondaryPipingNetworkSegmentSpecialization": {
        "name": "PrimarySecondaryPipingNetworkSegmentSpecialization",
        "uri": "http://sandbox.dexpi.org/rdl/PrimarySecondaryPipingNetworkSegmentSpecialization",
        "format": "string",
    },
    "pipingComponentNumber": {
        "name": "PipingComponentNumberAssignmentClass",
        "uri": "http://sandbox.dexpi.org/rdl/PipingComponentNumberAssignmentClass",
        "format": "string",
    },
    # Additional mappings can be added here as needed
}
