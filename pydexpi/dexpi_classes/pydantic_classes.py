"""This module contains the custom base models for all dexpi pydantic models.
Depending on the type, a DEXPI class is either a regular DexpiBaseModel or a DexpiDataTypeBaseModel.
Singleton classes also inherit from the DexpiSingletonBaseModel."""

from __future__ import annotations

import uuid
from abc import ABC
from datetime import datetime
from enum import StrEnum
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field


class DexpiBaseModel(ABC, BaseModel):
    """Base Model for the classes created for the dexpi data model, containing some overarching functionality"""

    # Model configurations
    model_config = ConfigDict(validate_assignment=True)

    # Object ID, defaults to a uuid if not specified
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # Field to store proteus id if available
    proteusId: str | None = Field(None)

    # Hash function
    def __hash__(self):
        """Computes object hash from id and type."""
        # Return hash value based on both id and type
        return hash((self.id, type(self)))

    # Override copy methods that assigns a new id if called
    def __copy__(self):
        new_object = super().__copy__()
        new_object.id = str(uuid.uuid4())
        return new_object

    def __deepcopy__(self, *args, **kwargs):
        new_object = super().__deepcopy__(*args, **kwargs)
        new_object.id = str(uuid.uuid4())
        return new_object

    # Override str to get more comprehensible string message
    def __str__(self):
        return str(type(self)) + " ID: " + self.id


class DexpiDataTypeBaseModel(ABC, BaseModel):
    """Base Model for the data type classes created for the dexpi data model, containing some overarching functionality"""

    # Model congigurations
    model_config = ConfigDict(validate_assignment=True)

    # Hash function. Get hash value from all model fields with model type and return combined hash
    def __hash__(self):
        """Computes object hash from combined hash of all model fields and the type."""
        # Return the combined hash of all model fields
        return hash(
            tuple(hash(getattr(self, field)) for field in self.__class__.model_fields)
            + (type(self),)
        )

    def __eq__(self, other):
        """Check equality based on field values"""
        if not isinstance(other, DexpiDataTypeBaseModel):
            return False
        # Compare all fields as dictionaries for precise equality
        return self.model_dump() == other.model_dump()


class DexpiSingletonBaseModel(BaseModel):
    """
    Base class for the Singleton Classes of DEXPI, i.e. the Null classes for
    the data types.
    """

    # Class-level attribute to store the singleton instance
    _instance: ClassVar[DexpiSingletonBaseModel | None] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = object.__new__(cls, *args, **kwargs)
        return cls._instance


class ConceptualModel(DexpiBaseModel):
    """The conceptual content of a DexpiModel, i.e., engineering information independent from its graphical representation."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/conceptualModel.py"

    # Compositional attributes:
    actuatingSystems: list[ActuatingSystem] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )
    instrumentationLoopFunctions: list[InstrumentationLoopFunction] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )
    metaData: MetaData | None = Field(None, json_schema_extra={"attribute_category": "composition"})
    pipingNetworkSystems: list[PipingNetworkSystem] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )
    plantStructureItems: list[PlantStructureItem] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )
    processInstrumentationFunctions: list[ProcessInstrumentationFunction] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )
    processSignalGeneratingSystems: list[ProcessSignalGeneratingSystem] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )
    taggedPlantItems: list[TaggedPlantItem] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )


class DexpiModel(DexpiBaseModel):
    """An entire DEXPI model. A DexpiModel is the root of the composition hierarchy."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/dexpiModel.py"

    # Compositional attributes:
    conceptualModel: ConceptualModel | None = Field(
        None, json_schema_extra={"attribute_category": "composition"}
    )
    diagram: Diagram | None = Field(None, json_schema_extra={"attribute_category": "composition"})
    shapeCatalogues: list[ShapeCatalogue] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    exportDateTime: datetime | None = Field(None, json_schema_extra={"attribute_category": "data"})
    originatingSystemName: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    originatingSystemVendorName: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    originatingSystemVersion: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class IndustrialComplexParentStructure(DexpiBaseModel):
    """A PlantStructureItem that is a suitable ParentStructure of an IndustrialComplex."""

    uri: ClassVar[str] = (
        "https://pyDEXPI.org/schemas/pydexpi_1_3/industrialComplexParentStructure.py"
    )


class PlantAreaLocatedStructure(DexpiBaseModel):
    """A structure that can be located in an PlantArea."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/plantAreaLocatedStructure.py"

    # Reference attributes:
    plantArea: PlantArea | None = Field(None, json_schema_extra={"attribute_category": "reference"})


class PlantSectionParentStructure(DexpiBaseModel):
    """A PlantStructureItem that is a suitable ParentStructure of a PlantSection."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/plantSectionParentStructure.py"


class PlantSystemLocatedStructure(DexpiBaseModel):
    """A structure that can be located in a PlantSystem."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/plantSystemLocatedStructure.py"

    # Reference attributes:
    plantSystem: PlantSystem | None = Field(
        None, json_schema_extra={"attribute_category": "reference"}
    )


class PlantTrainLocatedStructure(DexpiBaseModel):
    """A structure that can be located in a PlantTrain."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/plantTrainLocatedStructure.py"

    # Reference attributes:
    plantTrain: PlantTrain | None = Field(
        None, json_schema_extra={"attribute_category": "reference"}
    )


class ProcessPlantParentStructure(DexpiBaseModel):
    """A PlantStructureItem that is a suitable ParentStructure of a ProcessPlant."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/processPlantParentStructure.py"


class TechnicalItem(
    PlantAreaLocatedStructure, PlantSystemLocatedStructure, PlantTrainLocatedStructure
):
    """An item at the lowest level of the plant structure."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/technicalItem.py"

    # Reference attributes:
    parentStructure: TechnicalItemParentStructure | None = Field(
        None, json_schema_extra={"attribute_category": "reference"}
    )


class TechnicalItemParentStructure(DexpiBaseModel):
    """A PlantStructureItem that is a suitable ParentStructure of a TechnicalItem."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/technicalItemParentStructure.py"


class ChamberOwner(DexpiBaseModel):
    """An object that can have chambers."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/chamberOwner.py"

    # Compositional attributes:
    chambers: list[Chamber] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )


class NozzleOwner(DexpiBaseModel):
    """An object that can have nozzles."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nozzleOwner.py"

    # Compositional attributes:
    nozzles: list[Nozzle] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )


class PipingConnection(DexpiBaseModel):
    """An elementary connection between two piping items."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/pipingConnection.py"

    # Reference attributes:
    sourceItem: PipingSourceItem | None = Field(
        None, json_schema_extra={"attribute_category": "reference"}
    )
    sourceNode: PipingNode | None = Field(
        None, json_schema_extra={"attribute_category": "reference"}
    )
    targetItem: PipingTargetItem | None = Field(
        None, json_schema_extra={"attribute_category": "reference"}
    )
    targetNode: PipingNode | None = Field(
        None, json_schema_extra={"attribute_category": "reference"}
    )


class PipingNetworkSegmentItem(DexpiBaseModel):
    """An item that can be part of a PipingNetworkSegment."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/pipingNetworkSegmentItem.py"


class PipingNodeOwner(DexpiBaseModel):
    """An object that can have PipingNodes."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/pipingNodeOwner.py"

    # Compositional attributes:
    nodes: list[PipingNode] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )


class PipingSourceItem(DexpiBaseModel):
    """An item that can be the source of a PipingConnection (attribute SourceItem) or a PipingNetworkSegment (attribute SourceItem)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/pipingSourceItem.py"


class PipingTargetItem(DexpiBaseModel):
    """An item that can be the target of a PipingConnection (attribute TargetItem) or a PipingNetworkSegment (attribute TargetItem)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/pipingTargetItem.py"


class ActuatingElectricalLocation(DexpiBaseModel):
    """An object suitable as the ActuatingElectricalLocation of an ActuatingElectricalFunction."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/actuatingElectricalLocation.py"


class SensingLocation(DexpiBaseModel):
    """An object than can act as a SensingLocation of a ProcessSignalGeneratingFunction."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/sensingLocation.py"


class SignalConveyingFunctionSource(DexpiBaseModel):
    """An object than can act as the Source of a SignalConveyingFunction."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/signalConveyingFunctionSource.py"


class SignalConveyingFunctionTarget(DexpiBaseModel):
    """An object than can act as the Target of a SignalConveyingFunction."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/signalConveyingFunctionTarget.py"


class CustomAttribute(DexpiBaseModel):
    """A custom attribute."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customAttribute.py"

    # Data attributes:
    attributeName: str = Field(..., json_schema_extra={"attribute_category": "data"})
    attributeURI: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    value: Any = Field(..., json_schema_extra={"attribute_category": "data"})


class CustomAttributeOwner(DexpiBaseModel):
    """An object that can have custom attributes."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customAttributeOwner.py"

    # Compositional attributes:
    customAttributes: list[CustomAttribute] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )


class CustomElectricalFrequencyAttribute(CustomAttribute):
    """A custom attribute with Value type NullableElectricalFrequency."""

    uri: ClassVar[str] = (
        "https://pyDEXPI.org/schemas/pydexpi_1_3/customElectricalFrequencyAttribute.py"
    )

    # Data attributes:
    value: NullableElectricalFrequency = Field(
        ..., json_schema_extra={"attribute_category": "data"}
    )


class CustomForceAttribute(CustomAttribute):
    """A custom attribute with Value type NullableForce."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customForceAttribute.py"

    # Data attributes:
    value: NullableForce = Field(..., json_schema_extra={"attribute_category": "data"})


class CustomHeatTransferCoefficientAttribute(CustomAttribute):
    """A custom attribute with Value type NullableHeatTransferCoefficient."""

    uri: ClassVar[str] = (
        "https://pyDEXPI.org/schemas/pydexpi_1_3/customHeatTransferCoefficientAttribute.py"
    )

    # Data attributes:
    value: NullableHeatTransferCoefficient = Field(
        ..., json_schema_extra={"attribute_category": "data"}
    )


class CustomIntegerAttribute(CustomAttribute):
    """A custom attribute with Value type NullableInteger."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customIntegerAttribute.py"

    # Data attributes:
    value: int | None = Field(None, json_schema_extra={"attribute_category": "data"})


class CustomLengthAttribute(CustomAttribute):
    """A custom attribute with Value type NullableLength."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customLengthAttribute.py"

    # Data attributes:
    value: NullableLength = Field(..., json_schema_extra={"attribute_category": "data"})


class CustomMassAttribute(CustomAttribute):
    """A custom attribute with Value type NullableMass."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customMassAttribute.py"

    # Data attributes:
    value: NullableMass = Field(..., json_schema_extra={"attribute_category": "data"})


class CustomMassFlowRateAttribute(CustomAttribute):
    """A custom attribute with Value type NullableMassFlowRate."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customMassFlowRateAttribute.py"

    # Data attributes:
    value: NullableMassFlowRate = Field(..., json_schema_extra={"attribute_category": "data"})


class CustomMultiLanguageStringAttribute(CustomAttribute):
    """A custom attribute with Value type MultiLanguageString."""

    uri: ClassVar[str] = (
        "https://pyDEXPI.org/schemas/pydexpi_1_3/customMultiLanguageStringAttribute.py"
    )

    # Data attributes:
    value: MultiLanguageString = Field(..., json_schema_extra={"attribute_category": "data"})


class CustomNumberPerTimeIntervalAttribute(CustomAttribute):
    """A custom attribute with Value type NullableNumberPerTimeInterval."""

    uri: ClassVar[str] = (
        "https://pyDEXPI.org/schemas/pydexpi_1_3/customNumberPerTimeIntervalAttribute.py"
    )

    # Data attributes:
    value: NullableNumberPerTimeInterval = Field(
        ..., json_schema_extra={"attribute_category": "data"}
    )


class CustomObject(DexpiBaseModel):
    """The abstract base class of all custom classes."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customObject.py"

    # Data attributes:
    typeName: str = Field(..., json_schema_extra={"attribute_category": "data"})
    typeURI: str | None = Field(None, json_schema_extra={"attribute_category": "data"})


class CustomPercentageAttribute(CustomAttribute):
    """A custom attribute with Value type NullablePercentage."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customPercentageAttribute.py"

    # Data attributes:
    value: NullablePercentage = Field(..., json_schema_extra={"attribute_category": "data"})


class CustomPowerAttribute(CustomAttribute):
    """A custom attribute with Value type NullablePower."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customPowerAttribute.py"

    # Data attributes:
    value: NullablePower = Field(..., json_schema_extra={"attribute_category": "data"})


class CustomPressureAbsoluteAttribute(CustomAttribute):
    """A custom attribute with Value type NullablePressureAbsolute."""

    uri: ClassVar[str] = (
        "https://pyDEXPI.org/schemas/pydexpi_1_3/customPressureAbsoluteAttribute.py"
    )

    # Data attributes:
    value: NullablePressureAbsolute = Field(..., json_schema_extra={"attribute_category": "data"})


class CustomPressureGaugeAttribute(CustomAttribute):
    """A custom attribute with Value type NullablePressureGauge."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customPressureGaugeAttribute.py"

    # Data attributes:
    value: NullablePressureGauge = Field(..., json_schema_extra={"attribute_category": "data"})


class CustomRotationalFrequencyAttribute(CustomAttribute):
    """A custom attribute with Value type NullableRotationalFrequency."""

    uri: ClassVar[str] = (
        "https://pyDEXPI.org/schemas/pydexpi_1_3/customRotationalFrequencyAttribute.py"
    )

    # Data attributes:
    value: NullableRotationalFrequency = Field(
        ..., json_schema_extra={"attribute_category": "data"}
    )


class CustomStringAttribute(CustomAttribute):
    """A custom attribute with Value type NullableString."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customStringAttribute.py"

    # Data attributes:
    value: str | None = Field(None, json_schema_extra={"attribute_category": "data"})


class CustomTemperatureAttribute(CustomAttribute):
    """A custom attribute with Value type NullableTemperature."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customTemperatureAttribute.py"

    # Data attributes:
    value: NullableTemperature = Field(..., json_schema_extra={"attribute_category": "data"})


class CustomVoltageAttribute(CustomAttribute):
    """A custom attribute with Value type NullableVoltage."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customVoltageAttribute.py"

    # Data attributes:
    value: NullableVoltage = Field(..., json_schema_extra={"attribute_category": "data"})


class CustomVolumeAttribute(CustomAttribute):
    """A custom attribute with Value type NullableVolume."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customVolumeAttribute.py"

    # Data attributes:
    value: NullableVolume = Field(..., json_schema_extra={"attribute_category": "data"})


class CustomVolumeFlowRateAttribute(CustomAttribute):
    """A custom attribute with Value type NullableVolumeFlowRate."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customVolumeFlowRateAttribute.py"

    # Data attributes:
    value: NullableVolumeFlowRate = Field(..., json_schema_extra={"attribute_category": "data"})


class ChamberFunctionClassification(StrEnum):
    # Literals:
    NULL = "null"
    Cooling = "cooling"
    Heating = "heating"
    Processing = "processing"
    Tempering = "tempering"


class CompositionBreakClassification(StrEnum):
    # Literals:
    NULL = "null"
    CompositionBreak = "composition break"
    NoCompositionBreak = "no composition break"


class ConfidentialityClassification(StrEnum):
    # Literals:
    NULL = "null"
    ConfidentialInformation = "confidential"
    NonConfidentialInformation = "not confidential"


class DetonationProofArtefactClassification(StrEnum):
    # Literals:
    NULL = "null"
    DetonationProofArtefact = "detonation-proof artefact"
    NonDetonationProofArtefact = "non detonation-proof artefact"


class ExplosionProofArtefactClassification(StrEnum):
    # Literals:
    NULL = "null"
    ExplosionProofArtefact = "explosion-proof artefact"
    NonExplosionProofArtefact = "non explosion-proof artefact"


class FailActionClassification(StrEnum):
    # Literals:
    NULL = "null"
    FailClose = "fail close"
    FailOpen = "fail open"
    FailRetainPosition = "fail retain position"


class FireResistantArtefactClassification(StrEnum):
    # Literals:
    NULL = "null"
    FireResistantArtefact = "fire-resistant artefact"
    NonFireResistantArtefact = "non fire-resistant artefact"


class GmpRelevanceClassification(StrEnum):
    # Literals:
    NULL = "null"
    GmpRelevantFunction = "GMP relevant"
    NonGmpRelevantFunction = "not GMP relevant"


class GuaranteedSupplyFunctionClassification(StrEnum):
    # Literals:
    NULL = "null"
    GuaranteedSupplyFunction = "guaranteed supply"
    NonGuaranteedSupplyFunction = "no guaranteed supply"


class HeatTracingTypeClassification(StrEnum):
    # Literals:
    NULL = "null"
    ElectricalHeatTracingSystem = "electrical heat tracing system"
    HeatTracingSystem = "heat tracing system"
    NoHeatTracingSystem = "no heat tracing system"
    SteamHeatTracingSystem = "steam heat tracing system"
    TubularHeatTracingSystem = "tubular heat tracing system"


class InsulationBreakClassification(StrEnum):
    # Literals:
    NULL = "null"
    InsulationBreak = "inulation break"
    NoInsulationBreak = "no insulation break"


class JacketedPipeClassification(StrEnum):
    # Literals:
    NULL = "null"
    JacketedPipe = "jacketed"
    UnjacketedPipe = "not jacketed"


class LocationClassification(StrEnum):
    # Literals:
    NULL = "null"
    CentralLocation = "central"
    ControlPanel = "panel"
    Field = "field"


class NominalDiameterBreakClassification(StrEnum):
    # Literals:
    NULL = "null"
    NoNominalDiameterBreak = "no nominal diameter break"
    NominalDiameterBreak = "nominal diameter break"


class NominalDiameterStandardClassification(StrEnum):
    # Literals:
    NULL = "null"
    Din2448ObjectDn100 = "DN 100 (DIN 2448)"
    Din2448ObjectDn125 = "DN 125 (DIN 2448)"
    Din2448ObjectDn15 = "DN 15 (DIN 2448)"
    Din2448ObjectDn150 = "DN 150 (DIN 2448)"
    Din2448ObjectDn20 = "DN 20 (DIN 2448)"
    Din2448ObjectDn200 = "DN 200 (DIN 2448)"
    Din2448ObjectDn25 = "DN 25 (DIN 2448)"
    Din2448ObjectDn32 = "DN 32 (DIN 2448)"
    Din2448ObjectDn40 = "DN 40 (DIN 2448)"
    Din2448ObjectDn50 = "DN 50 (DIN 2448)"
    Din2448ObjectDn65 = "DN 65 (DIN 2448)"
    Din2448ObjectDn80 = "DN 80 (DIN 2448)"
    Iso6708ObjectDn100 = "DN 100 (ISO 6708)"
    Iso6708ObjectDn1000 = "DN 1000 (ISO 6708)"
    Iso6708ObjectDn1200 = "DN 1200 (ISO 6708)"
    Iso6708ObjectDn125 = "DN 125 (ISO 6708)"
    Iso6708ObjectDn1400 = "DN 1400 (ISO 6708)"
    Iso6708ObjectDn15 = "DN 15 (ISO 6708)"
    Iso6708ObjectDn150 = "DN 150 (ISO 6708)"
    Iso6708ObjectDn1600 = "DN 1600 (ISO 6708)"
    Iso6708ObjectDn20 = "DN 20 (ISO 6708)"
    Iso6708ObjectDn200 = "DN 200 (ISO 6708)"
    Iso6708ObjectDn25 = "DN 25 (ISO 6708)"
    Iso6708ObjectDn250 = "DN 250 (ISO 6708)"
    Iso6708ObjectDn300 = "DN 300 (ISO 6708)"
    Iso6708ObjectDn32 = "DN 32 (ISO 6708)"
    Iso6708ObjectDn350 = "DN 350 (ISO 6708)"
    Iso6708ObjectDn40 = "DN 40 (ISO 6708)"
    Iso6708ObjectDn400 = "DN 400 (ISO 6708)"
    Iso6708ObjectDn450 = "DN 450 (ISO 6708)"
    Iso6708ObjectDn50 = "DN 50 (ISO 6708)"
    Iso6708ObjectDn500 = "DN 500 (ISO 6708)"
    Iso6708ObjectDn600 = "DN 600 (ISO 6708)"
    Iso6708ObjectDn65 = "DN 65 (ISO 6708)"
    Iso6708ObjectDn700 = "DN 700 (ISO 6708)"
    Iso6708ObjectDn80 = "DN 80 (ISO 6708)"
    Iso6708ObjectDn800 = "DN 800 (ISO 6708)"
    Iso6708ObjectDn900 = "DN 900 (ISO 6708)"
    Nps1_s_2Artefact = "NPS 1/2"
    Nps1_s_4Artefact = "NPS 1/4"
    Nps10Artefact = "NPS 10"
    Nps12Artefact = "NPS 12"
    Nps14Artefact = "NPS 14"
    Nps16Artefact = "NPS 16"
    Nps18Artefact = "NPS 18"
    Nps1Artefact = "NPS 1"
    Nps1_1_s_2Artefact = "NPS 1 1/2"
    Nps1_1_s_4Artefact = "NPS 1 1/4"
    Nps20Artefact = "NPS 20"
    Nps24Artefact = "NPS 24"
    Nps2Artefact = "NPS 2"
    Nps2_1_s_2Artefact = "NPS 2 1/2"
    Nps3_s_4Artefact = "NPS 3/4"
    Nps30Artefact = "NPS 30"
    Nps36Artefact = "NPS 36"
    Nps3Artefact = "NPS 3"
    Nps3_1_s_2Artefact = "NPS 3 1/2"
    Nps42Artefact = "NPS 42"
    Nps48Artefact = "NPS 48"
    Nps4Artefact = "NPS 4"
    Nps54Artefact = "NPS 54"
    Nps5Artefact = "NPS 5"
    Nps60Artefact = "NPS 60"
    Nps6Artefact = "NPS 6"
    Nps8Artefact = "NPS 8"


class NominalPressureStandardClassification(StrEnum):
    # Literals:
    NULL = "null"
    Class10000PsiArtefact = "Class 10000 psi"
    Class1000KpaArtefact = "Class 1000 kpa"
    Class125LbsArtefact = "Class 125 lbs"
    Class15000PsiArtefact = "Class 15000 psi"
    Class1500LbsArtefact = "Class 1500 lbs"
    Class150LbsArtefact = "Class 150 lbs"
    Class16BarArtefact = "Class 16 bar"
    Class20000PsiArtefact = "Class 20000 psi"
    Class2000PsiArtefact = "Class 2000 psi"
    Class2500LbsArtefact = "Class 2500 lbs"
    Class250PsiArtefact = "Class 250 psi"
    Class3000PsiArtefact = "Class 3000 psi"
    Class300LbsArtefact = "Class 300 lbs"
    Class300PsiArtefact = "Class 300 psi"
    Class315BarArtefact = "Class 315 bar"
    Class345BarArtefact = "Class 345 bar"
    Class350BarArtefact = "Class 350 bar"
    Class4000PsiArtefact = "Class 4000 psi"
    Class400LbsArtefact = "Class 400 lbs"
    Class4500LbsArtefact = "Class 4500 lbs"
    Class4500PsiArtefact = "Class 4500 psi"
    Class5000PsiArtefact = "Class 5000 psi"
    Class50BarArtefact = "Class 50 bar"
    Class517BarArtefact = "Class 517 bar"
    Class6000PsiArtefact = "Class 6000 psi"
    Class600LbsArtefact = "Class 600 lbs"
    Class690BarArtefact = "Class 690 bar"
    Class800LbsArtefact = "Class 800 lbs"
    Class800PsiArtefact = "Class 800 psi"
    Class850KpaArtefact = "Class 850 kpa"
    Class9000LbsArtefact = "Class 9000 lbs"
    Class900LbsArtefact = "Class 900 lbs"
    En1333Pn100Artefact = "PN 100 (EN 1333)"
    En1333Pn10Artefact = "PN 10 (EN 1333)"
    En1333Pn160Artefact = "PN 160 (EN 1333)"
    En1333Pn16Artefact = "PN 16 (EN 1333)"
    En1333Pn2_c_5Artefact = "PN 2,5 (EN 1333)"
    En1333Pn250Artefact = "PN 250 (EN 1333)"
    En1333Pn25Artefact = "PN 25 (EN 1333)"
    En1333Pn320Artefact = "PN 320 (EN 1333)"
    En1333Pn400Artefact = "PN 400 (EN 1333)"
    En1333Pn40Artefact = "PN 40 (EN 1333)"
    En1333Pn63Artefact = "PN 63 (EN 1333)"
    En1333Pn6Artefact = "PN 6 (EN 1333)"


class NumberOfPortsClassification(StrEnum):
    # Literals:
    NULL = "null"
    FourPortValve = "4 port valve"
    ThreePortValve = "3 port valve"
    TwoPortValve = "2 port valve"


class OnHoldClassification(StrEnum):
    # Literals:
    NULL = "null"
    NotOnHold = "not on hold"
    OnHold = "on hold"


class OperationClassification(StrEnum):
    # Literals:
    NULL = "null"
    ContinuousOperation = "continuous operation"
    IntermittentOperation = "intermittent operation"


class PipingClassArtefactClassification(StrEnum):
    # Literals:
    NULL = "null"
    NonPipingClassArtefact = "non-piping-class artefact"
    PipingClassArtefact = "piping class artefact"


class PipingClassBreakClassification(StrEnum):
    # Literals:
    NULL = "null"
    NoPipingClassBreak = "no piping class break"
    PipingClassBreak = "piping class break"


class PipingNetworkSegmentFlowClassification(StrEnum):
    # Literals:
    NULL = "null"
    DualFlowPipingNetworkSegment = "dual flow"
    SingleFlowPipingNetworkSegment = "single flow"


class PipingNetworkSegmentSlopeClassification(StrEnum):
    # Literals:
    NULL = "null"
    SlopedPipingNetworkSegment = "sloped"
    UnslopedPipingNetworkSegment = "not sloped"


class PortStatusClassification(StrEnum):
    # Literals:
    NULL = "null"
    StatusHighHighHighPort = "HHH"
    StatusHighHighPort = "HH"
    StatusHighPort = "H"
    StatusLowLowLowPort = "LLL"
    StatusLowLowPort = "LL"
    StatusLowPort = "L"


class PrimarySecondaryPipingNetworkSegmentClassification(StrEnum):
    # Literals:
    NULL = "null"
    PrimaryPipingNetworkSegment = "primary segment"
    SecondaryPipingNetworkSegment = "secondary segment"


class QualityRelevanceClassification(StrEnum):
    # Literals:
    NULL = "null"
    NonQualityRelevantFunction = "not quality relevant"
    QualityRelevantFunction = "quality relevant"


class SignalConveyingTypeClassification(StrEnum):
    # Literals:
    NULL = "null"
    CapillarySignalConveying = "capillary"
    ConductedRadiationSignalConveying = "conducted radiation"
    ElectricalSignalConveying = "electrical"
    HydraulicSignalConveying = "hydraulic"
    PneumaticSignalConveying = "pneumatic"


class SiphonClassification(StrEnum):
    # Literals:
    NULL = "null"
    NoSiphon = "no siphon"
    Siphon = "siphon"


class AreaUnit(StrEnum):
    # Literals:
    CentimetreSquared = "cm2"
    FootSquared = "ft2"
    InchSquared = "in2"
    MetreSquared = "m2"
    MillimetreSquared = "mm2"
    YardSquared = "yd2"


class ElectricalFrequencyUnit(StrEnum):
    # Literals:
    Hertz = "Hz"
    Kilohertz = "kHz"
    Megahertz = "MHz"


class ForceUnit(StrEnum):
    # Literals:
    Kilonewton = "kN"
    Newton = "N"


class HeatTransferCoefficientUnit(StrEnum):
    # Literals:
    KilowattPerMetreSquaredKelvin = "kW/(m2·K)"
    WattPerMetreSquaredKelvin = "W/(m2·K)"


class LengthUnit(StrEnum):
    # Literals:
    Centimetre = "cm"
    Foot = "ft"
    Inch = "in"
    Kilometre = "km"
    Metre = "m"
    Micrometre = "µm"
    Millimetre = "mm"
    Nanometre = "nm"


class MassFlowRateUnit(StrEnum):
    # Literals:
    KilogramPerHour = "kg/h"
    KilogramPerMinute = "kg/min"
    KilogramPerSecond = "kg/s"
    PoundMassPerHour = "lb/h"
    PoundMassPerMinute = "lb/min"
    PoundMassPerSecond = "lb/s"


class MassUnit(StrEnum):
    # Literals:
    Gram = "g"
    Kilogram = "kg"
    PoundMass = "lb"
    Tonne = "t"


class NumberPerTimeIntervalUnit(StrEnum):
    # Literals:
    ReciprocalMinute = "min-1"
    ReciprocalSecond = "s-1"


class PercentageUnit(StrEnum):
    # Literals:
    Percent = "???"


class PowerUnit(StrEnum):
    # Literals:
    Kilowatt = "kW"
    Megawatt = "MW"
    Watt = "W"


class PressureAbsoluteUnit(StrEnum):
    # Literals:
    Bar = "bar"
    Kilopascal = "kPa"
    Megapascal = "MPa"
    Millibar = "mbar"
    Pascal = "Pa"
    PoundForcePerInchSquared = "lbf/in2"


class PressureGaugeUnit(StrEnum):
    # Literals:
    Bar = "bar"
    Kilopascal = "kPa"
    Megapascal = "MPa"
    Millibar = "mbar"
    Pascal = "Pa"
    PoundForcePerInchSquared = "lbf/in2"


class RotationalFrequencyUnit(StrEnum):
    # Literals:
    ReciprocalMinute = "min-1"
    ReciprocalSecond = "s-1"


class TemperatureUnit(StrEnum):
    # Literals:
    DegreeCelsius = "°C"
    DegreeFahrenheit = "°F"
    Kelvin = "K"


class VoltageUnit(StrEnum):
    # Literals:
    Kilovolt = "kV"
    Megavolt = "MV"
    Volt = "V"


class VolumeFlowRateUnit(StrEnum):
    # Literals:
    FootCubedPerHour = "ft3/h"
    FootCubedPerMinute = "ft3/min"
    LitrePerSecond = "l/s"
    MetreCubedPerDay = "m3/d"
    MetreCubedPerHour = "m3/h"
    MetreCubedPerMinute = "m3/min"
    MetreCubedPerSecond = "m3/s"


class VolumeUnit(StrEnum):
    # Literals:
    CentimetreCubed = "cm3"
    DecimetreCubed = "dm3"
    FootCubed = "ft3"
    Litre = "l"
    MetreCubed = "m3"
    UsFluidOunce = "fl oz (US)"
    UsGallon = "gal (US)"


class NullableArea(DexpiDataTypeBaseModel):
    """NullableArea is a simple physical quantity type for the dimension L2. NullableArea is abstract and has two concrete subtypes:
            - an Area is an actual value for a physical quantity with a numerical value and a unit of measurement;
    - a NullArea is a null value that explicitly indicates the absence of an actual physical quantity."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nullableArea.py"


class NullableForce(DexpiDataTypeBaseModel):
    """NullableForce is a simple physical quantity type for the dimension LMT-2. NullableForce is abstract and has two concrete subtypes:
            - a Force is an actual value for a physical quantity with a numerical value and a unit of measurement;
    - a NullForce is a null value that explicitly indicates the absence of an actual physical quantity."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nullableForce.py"


class NullableFrequency(DexpiDataTypeBaseModel):
    """NullableFrequency is an application-dependent physical quantity type for the dimension T-1. It has 3 subtypes for different application areas."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nullableFrequency.py"


class NullableHeatTransferCoefficient(DexpiDataTypeBaseModel):
    """NullableHeatTransferCoefficient is a simple physical quantity type for the dimension MT-3Θ. NullableHeatTransferCoefficient is abstract and has two concrete subtypes:
            - a HeatTransferCoefficient is an actual value for a physical quantity with a numerical value and a unit of measurement;
    - a NullHeatTransferCoefficient is a null value that explicitly indicates the absence of an actual physical quantity."""

    uri: ClassVar[str] = (
        "https://pyDEXPI.org/schemas/pydexpi_1_3/nullableHeatTransferCoefficient.py"
    )


class NullableLength(DexpiDataTypeBaseModel):
    """NullableLength is a simple physical quantity type for the dimension L. NullableLength is abstract and has two concrete subtypes:
            - a Length is an actual value for a physical quantity with a numerical value and a unit of measurement;
    - a NullLength is a null value that explicitly indicates the absence of an actual physical quantity."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nullableLength.py"


class NullableMass(DexpiDataTypeBaseModel):
    """NullableMass is a simple physical quantity type for the dimension M. NullableMass is abstract and has two concrete subtypes:
            - a Mass is an actual value for a physical quantity with a numerical value and a unit of measurement;
    - a NullMass is a null value that explicitly indicates the absence of an actual physical quantity."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nullableMass.py"


class NullableMassFlowRate(DexpiDataTypeBaseModel):
    """NullableMassFlowRate is a simple physical quantity type for the dimension MT-1. NullableMassFlowRate is abstract and has two concrete subtypes:
            - a MassFlowRate is an actual value for a physical quantity with a numerical value and a unit of measurement;
    - a NullMassFlowRate is a null value that explicitly indicates the absence of an actual physical quantity."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nullableMassFlowRate.py"


class NullableNumberPerTimeInterval(NullableFrequency):
    """A physical quantity of dimension T-1 (inherited from NullableFrequency) for the application type number per time interval. NullableNumberPerTimeInterval is abstract and has two concrete subtypes:
            - a NumberPerTimeInterval is an actual value for a physical quantity with a numerical value and a unit of measurement;
    - a NullNumberPerTimeInterval is a null value that explicitly indicates the absence of an actual physical quantity."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nullableNumberPerTimeInterval.py"


class NullablePercentage(DexpiDataTypeBaseModel):
    """A quantity given as a percentage. Although percentage is not a physical quantity type in the strict sense, it is modeled using the same pattern as for simple physical quantity types. NullablePercentage is abstract and has two concrete subtypes:
            - a Percentage is an actual value for a quantity with a numerical value and a unit of measurement;
    - a NullPercentage is a null value that explicitly indicates the absence of an actual quantity."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nullablePercentage.py"


class NullablePower(DexpiDataTypeBaseModel):
    """NullablePower is a simple physical quantity type for the dimension L2MT-3. NullablePower is abstract and has two concrete subtypes:
            - a Power is an actual value for a physical quantity with a numerical value and a unit of measurement;
    - a NullPower is a null value that explicitly indicates the absence of an actual physical quantity."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nullablePower.py"


class NullablePressure(DexpiDataTypeBaseModel):
    """NullablePressure is an application-dependent physical quantity type for the dimension L-1MT-2. It has 2 subtypes for different application areas."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nullablePressure.py"


class NullablePressureAbsolute(NullablePressure):
    """A physical quantity of dimension L-1MT-2 (inherited from NullablePressure) for the application type absolute pressure. A pressure absolute is a pressure relative to a perfect vacuum. This data type is also used for the difference between two pressures other than atmospheric pressure. NullablePressureAbsolute is abstract and has two concrete subtypes:
            - a PressureAbsolute is an actual value for a physical quantity with a numerical value and a unit of measurement;
    - a NullPressureAbsolute is a null value that explicitly indicates the absence of an actual physical quantity."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nullablePressureAbsolute.py"


class NullablePressureGauge(NullablePressure):
    """A physical quantity of dimension L-1MT-2 (inherited from NullablePressure) for the application type pressure gauge. A pressure gauge is a pressure relative to atmospheric pressure. NullablePressureGauge is abstract and has two concrete subtypes:
            - a PressureGauge is an actual value for a physical quantity with a numerical value and a unit of measurement;
    - a NullPressureGauge is a null value that explicitly indicates the absence of an actual physical quantity."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nullablePressureGauge.py"


class NullableRotationalFrequency(NullableFrequency):
    """A physical quantity of dimension T-1 (inherited from NullableFrequency) for the application type rotational frequency. NullableRotationalFrequency is abstract and has two concrete subtypes:
            - a RotationalFrequency is an actual value for a physical quantity with a numerical value and a unit of measurement;
    - a NullRotationalFrequency is a null value that explicitly indicates the absence of an actual physical quantity."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nullableRotationalFrequency.py"


class NullableTemperature(DexpiDataTypeBaseModel):
    """NullableTemperature is a simple physical quantity type for the dimension Θ. NullableTemperature is abstract and has two concrete subtypes:
            - a Temperature is an actual value for a physical quantity with a numerical value and a unit of measurement;
    - a NullTemperature is a null value that explicitly indicates the absence of an actual physical quantity."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nullableTemperature.py"


class NullableVoltage(DexpiDataTypeBaseModel):
    """NullableVoltage is a simple physical quantity type for the dimension L2MT-3I-1. NullableVoltage is abstract and has two concrete subtypes:
            - a Voltage is an actual value for a physical quantity with a numerical value and a unit of measurement;
    - a NullVoltage is a null value that explicitly indicates the absence of an actual physical quantity."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nullableVoltage.py"


class NullableVolume(DexpiDataTypeBaseModel):
    """NullableVolume is a simple physical quantity type for the dimension L3. NullableVolume is abstract and has two concrete subtypes:
            - a Volume is an actual value for a physical quantity with a numerical value and a unit of measurement;
    - a NullVolume is a null value that explicitly indicates the absence of an actual physical quantity."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nullableVolume.py"


class NullableVolumeFlowRate(DexpiDataTypeBaseModel):
    """NullableVolumeFlowRate is a simple physical quantity type for the dimension L3T-1. NullableVolumeFlowRate is abstract and has two concrete subtypes:
            - a VolumeFlowRate is an actual value for a physical quantity with a numerical value and a unit of measurement;
    - a NullVolumeFlowRate is a null value that explicitly indicates the absence of an actual physical quantity."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nullableVolumeFlowRate.py"


class NumberPerTimeInterval(NullableNumberPerTimeInterval):
    """An actual value for a physical quantity of type NullableNumberPerTimeInterval, i.e., a physical quantity that has a numerical value and a unit of measurement."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/numberPerTimeInterval.py"

    # Data attributes:
    unit: NumberPerTimeIntervalUnit = Field(..., json_schema_extra={"attribute_category": "data"})
    value: float = Field(..., json_schema_extra={"attribute_category": "data"})


class Percentage(NullablePercentage):
    """An actual value for a physical quantity of type NullablePercentage, i.e., a physical quantity that has a numerical value and a unit of measurement."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/percentage.py"

    # Data attributes:
    unit: PercentageUnit = Field(..., json_schema_extra={"attribute_category": "data"})
    value: float = Field(..., json_schema_extra={"attribute_category": "data"})


class Power(NullablePower):
    """An actual value for a physical quantity of type NullablePower, i.e., a physical quantity that has a numerical value and a unit of measurement."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/power.py"

    # Data attributes:
    unit: PowerUnit = Field(..., json_schema_extra={"attribute_category": "data"})
    value: float = Field(..., json_schema_extra={"attribute_category": "data"})


class PressureAbsolute(NullablePressureAbsolute):
    """An actual value for a physical quantity of type NullablePressureAbsolute, i.e., a physical quantity that has a numerical value and a unit of measurement."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/pressureAbsolute.py"

    # Data attributes:
    unit: PressureAbsoluteUnit = Field(..., json_schema_extra={"attribute_category": "data"})
    value: float = Field(..., json_schema_extra={"attribute_category": "data"})


class PressureGauge(NullablePressureGauge):
    """An actual value for a physical quantity of type NullablePressureGauge, i.e., a physical quantity that has a numerical value and a unit of measurement."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/pressureGauge.py"

    # Data attributes:
    unit: PressureGaugeUnit = Field(..., json_schema_extra={"attribute_category": "data"})
    value: float = Field(..., json_schema_extra={"attribute_category": "data"})


class RotationalFrequency(NullableRotationalFrequency):
    """An actual value for a physical quantity of type NullableRotationalFrequency, i.e., a physical quantity that has a numerical value and a unit of measurement."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/rotationalFrequency.py"

    # Data attributes:
    unit: RotationalFrequencyUnit = Field(..., json_schema_extra={"attribute_category": "data"})
    value: float = Field(..., json_schema_extra={"attribute_category": "data"})


class Temperature(NullableTemperature):
    """An actual value for a physical quantity of type NullableTemperature, i.e., a physical quantity that has a numerical value and a unit of measurement."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/temperature.py"

    # Data attributes:
    unit: TemperatureUnit = Field(..., json_schema_extra={"attribute_category": "data"})
    value: float = Field(..., json_schema_extra={"attribute_category": "data"})


class Voltage(NullableVoltage):
    """An actual value for a physical quantity of type NullableVoltage, i.e., a physical quantity that has a numerical value and a unit of measurement."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/voltage.py"

    # Data attributes:
    unit: VoltageUnit = Field(..., json_schema_extra={"attribute_category": "data"})
    value: float = Field(..., json_schema_extra={"attribute_category": "data"})


class Volume(NullableVolume):
    """An actual value for a physical quantity of type NullableVolume, i.e., a physical quantity that has a numerical value and a unit of measurement."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/volume.py"

    # Data attributes:
    unit: VolumeUnit = Field(..., json_schema_extra={"attribute_category": "data"})
    value: float = Field(..., json_schema_extra={"attribute_category": "data"})


class VolumeFlowRate(NullableVolumeFlowRate):
    """An actual value for a physical quantity of type NullableVolumeFlowRate, i.e., a physical quantity that has a numerical value and a unit of measurement."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/volumeFlowRate.py"

    # Data attributes:
    unit: VolumeFlowRateUnit = Field(..., json_schema_extra={"attribute_category": "data"})
    value: float = Field(..., json_schema_extra={"attribute_category": "data"})


class AttributeRepresentationType(StrEnum):
    # Literals:
    Value = "Value"
    Units = "Units"
    ValueAndUnits = "ValueAndUnits"


class DashStyle(StrEnum):
    # Literals:
    Solid = "Solid"
    Dot = "Dot"
    Dash = "Dash"
    LongDash = "LongDash"
    LongDashShortDash = "LongDashShortDash"
    ShortDash = "ShortDash"
    LongDashShortDashShortDash = "LongDashShortDashShortDash"
    DashShortDash = "DashShortDash"


class FillStyle(StrEnum):
    # Literals:
    Solid = "Solid"
    Transparent = "Transparent"
    Hatch = "Hatch"


class TextAlignment(StrEnum):
    # Literals:
    LeftTop = "LeftTop"
    LeftCenter = "LeftCenter"
    LeftBottom = "LeftBottom"
    CenterTop = "CenterTop"
    CenterCenter = "CenterCenter"
    CenterBottom = "CenterBottom"
    RightTop = "RightTop"
    RightCenter = "RightCenter"
    RightBottom = "RightBottom"


class Color(DexpiDataTypeBaseModel):
    """A color.
    Color is based on the RGB color model (e.g., see Wikipedia for an overview). For each channel red, green, and blue, Color has an attribute R, G, and B that gives the intensity of the channel. Intensities are given as values of UnsignedByte, i.e., integers in the range [0, 255]."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/color.py"

    # Data attributes:
    b: int = Field(..., json_schema_extra={"attribute_category": "data"})
    g: int = Field(..., json_schema_extra={"attribute_category": "data"})
    r: int = Field(..., json_schema_extra={"attribute_category": "data"})


class Point(DexpiDataTypeBaseModel):
    """A point in the X-Y-plane."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/point.py"

    # Data attributes:
    x: float = Field(..., json_schema_extra={"attribute_category": "data"})
    y: float = Field(..., json_schema_extra={"attribute_category": "data"})


class Stroke(DexpiDataTypeBaseModel):
    """A stroke defines the visual appearance of a line."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/stroke.py"

    # Data attributes:
    color: Color = Field(..., json_schema_extra={"attribute_category": "data"})
    dashStyle: DashStyle = Field(..., json_schema_extra={"attribute_category": "data"})
    width: float = Field(..., json_schema_extra={"attribute_category": "data"})


class GraphicalElement(DexpiBaseModel):
    """A graphical element."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/graphicalElement.py"


class GraphicalPrimitive(GraphicalElement):
    """A primitive graphical element."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/graphicalPrimitive.py"


class GraphicsGroup(DexpiBaseModel):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/graphicsGroup.py"


class NodePosition(DexpiBaseModel):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/nodePosition.py"

    # Data attributes:
    position: Point = Field(..., json_schema_extra={"attribute_category": "data"})


class PipingNodePosition(NodePosition):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/pipingNodePosition.py"

    # Reference attributes:
    node: PipingNode | None = Field(None, json_schema_extra={"attribute_category": "reference"})


class PolyLine(GraphicalPrimitive):
    """A curve that consists of one or more chained straight sections."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/polyLine.py"

    # Data attributes:
    points: list[Point] = Field(..., json_schema_extra={"attribute_category": "data"})
    stroke: Stroke = Field(..., json_schema_extra={"attribute_category": "data"})


class Polygon(GraphicalPrimitive):
    """A figure that is delimited by a closed chain of three or more straight sections."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/polygon.py"

    # Data attributes:
    fillStyle: FillStyle = Field(..., json_schema_extra={"attribute_category": "data"})
    points: list[Point] = Field(..., json_schema_extra={"attribute_category": "data"})
    stroke: Stroke = Field(..., json_schema_extra={"attribute_category": "data"})


class RepresentationGroup(GraphicsGroup):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/representationGroup.py"

    # Compositional attributes:
    groups: list[GraphicsGroup] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )
    nodePositions: list[NodePosition] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )

    # Reference attributes:
    represents: DexpiBaseModel = Field(..., json_schema_extra={"attribute_category": "reference"})


class RepresentationTypeGroup(GraphicsGroup):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/representationTypeGroup.py"

    # Compositional attributes:
    elements: list[GraphicalElement] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )


class Shape(DexpiBaseModel):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/shape.py"

    # Compositional attributes:
    primitives: list[GraphicalPrimitive] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    name: str = Field(..., json_schema_extra={"attribute_category": "data"})
    symbolRegistrationNumber: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class ShapeCatalogue(DexpiBaseModel):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/shapeCatalogue.py"

    # Compositional attributes:
    shapes: list[Shape] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    name: str = Field(..., json_schema_extra={"attribute_category": "data"})


class ShapeUsage(GraphicalElement):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/shapeUsage.py"

    # Data attributes:
    isMirrored: bool = Field(..., json_schema_extra={"attribute_category": "data"})
    position: Point = Field(..., json_schema_extra={"attribute_category": "data"})
    rotation: float = Field(..., json_schema_extra={"attribute_category": "data"})
    scaleX: float = Field(..., json_schema_extra={"attribute_category": "data"})
    scaleY: float = Field(..., json_schema_extra={"attribute_category": "data"})

    # Reference attributes:
    shape: Shape = Field(..., json_schema_extra={"attribute_category": "reference"})


class SignalOffPageConnectorShape(Shape):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/signalOffPageConnectorShape.py"


class Static(RepresentationTypeGroup):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/static.py"


class Symbol(RepresentationTypeGroup):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/symbol.py"


class SymbolShape(Shape):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/symbolShape.py"


class TaggedPlantItemShape(Shape):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/taggedPlantItemShape.py"


class Text(GraphicalPrimitive):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/text.py"

    # Compositional attributes:
    template: TextTemplate | None = Field(
        None, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    alignment: TextAlignment = Field(..., json_schema_extra={"attribute_category": "data"})
    color: Color = Field(..., json_schema_extra={"attribute_category": "data"})
    font: str = Field(..., json_schema_extra={"attribute_category": "data"})
    position: Point = Field(..., json_schema_extra={"attribute_category": "data"})
    rotation: float = Field(..., json_schema_extra={"attribute_category": "data"})
    size: float = Field(..., json_schema_extra={"attribute_category": "data"})
    text: str = Field(..., json_schema_extra={"attribute_category": "data"})


class TextTemplate(DexpiBaseModel):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/textTemplate.py"

    # Compositional attributes:
    fragments: list[TextTemplateFragment] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )


class TextTemplateFragment(DexpiBaseModel):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/textTemplateFragment.py"


class MultiLanguageString(DexpiDataTypeBaseModel):
    """A container for one or more SingleLanguageStrings. MultiLanguageString is used as the type of data attributes which have language-dependent string values: Each SingleLanguageString contains a NullableString Value and a Language tag."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/multiLanguageString.py"

    # Data attributes:
    singleLanguageStrings: list[SingleLanguageString] = Field(
        ..., json_schema_extra={"attribute_category": "data"}
    )


class SingleLanguageString(DexpiDataTypeBaseModel):
    """A SingleLanguageString contains a NullableString as its Value and a Language tag. SingleLanguageString is only used within MultiLanguageString. See the latter data type for more details."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/singleLanguageString.py"

    # Data attributes:
    language: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    value: str | None = Field(None, json_schema_extra={"attribute_category": "data"})


class MetaData(CustomAttributeOwner):
    """A container for meta data about a DexpiModel."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/metaData.py"

    # Data attributes:
    approvalDateRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    approvalDescription: MultiLanguageString | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    approverName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    archiveNumber: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    blockName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    blockNumber: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    checkerName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    confidentiality: ConfidentialityClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    creationDateRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    creatorName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    designerName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    drafterName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    drawingName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    drawingNumber: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    drawingSubTitle: MultiLanguageString | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    enterpriseIdentificationCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    enterpriseName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    fileName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    industrialComplexIdentificationCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    industrialComplexName: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    lastModificationDateRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    locationName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    plantAreaIdentificationCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    plantAreaName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    plantSectionIdentificationCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    plantSectionName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    plantSystemIdentificationCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    plantSystemName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    plantTrainIdentificationCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    plantTrainName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    processCellIdentificationCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    processCellName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    processPlantIdentificationCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    processPlantName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    projectName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    projectNumber: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    projectRangeNumber: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    replacedDrawing: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    responsibleDepartmentName: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    revisionNumber: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    sheetFormat: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    sheetNumber: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    siteIdentificationCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    siteName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    subProjectName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    subProjectNumber: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    totalNumberOfSheets: int | None = Field(None, json_schema_extra={"attribute_category": "data"})
    unitIdentificationCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    unitName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})


class PlantStructureItem(CustomAttributeOwner):
    """Item of the plant break down structure."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/plantStructureItem.py"


class PlantSystem(PlantStructureItem):
    """A plant system."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/plantSystem.py"

    # Data attributes:
    plantSystemIdentificationCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    plantSystemName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})


class PlantTrain(PlantStructureItem):
    """A plant train."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/plantTrain.py"

    # Data attributes:
    plantTrainIdentificationCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    plantTrainName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})


class ProcessPlant(
    PlantAreaLocatedStructure,
    PlantSectionParentStructure,
    PlantStructureItem,
    TechnicalItemParentStructure,
):
    """A plant employed in carrying out chemical processes, including the required supporting processes (from http://data.posccaesar.org/rdl/RDS7151859)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/processPlant.py"

    # Data attributes:
    processPlantIdentificationCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    processPlantName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})

    # Reference attributes:
    parentStructure: ProcessPlantParentStructure | None = Field(
        None, json_schema_extra={"attribute_category": "reference"}
    )


class Site(
    IndustrialComplexParentStructure,
    PlantSectionParentStructure,
    PlantStructureItem,
    ProcessPlantParentStructure,
    TechnicalItemParentStructure,
):
    """A site as defined by ISA 95."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/site.py"

    # Data attributes:
    siteIdentificationCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    siteName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})

    # Reference attributes:
    parentStructure: Enterprise | None = Field(
        None, json_schema_extra={"attribute_category": "reference"}
    )


class AgitatorRotor(CustomAttributeOwner):
    """The machine component that is the rotating portion of an Agitator."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/agitatorRotor.py"

    # Data attributes:
    diameter: NullableLength | None = Field(None, json_schema_extra={"attribute_category": "data"})
    lengthToMountingFlange: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    materialOfConstructionCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    rotorType: str | None = Field(None, json_schema_extra={"attribute_category": "data"})

    # Reference attributes:
    chamber: Chamber | None = Field(None, json_schema_extra={"attribute_category": "reference"})


class BriquettingRoller(CustomAttributeOwner):
    """An element of an Agglomerator that compresses bulk material into briquettes."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/briquettingRoller.py"

    # Data attributes:
    diameter: NullableLength | None = Field(None, json_schema_extra={"attribute_category": "data"})
    materialOfConstructionCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    stageIdentifier: str | None = Field(None, json_schema_extra={"attribute_category": "data"})


class Chamber(CustomAttributeOwner):
    """A physical object that is an enclosed space (from http://data.posccaesar.org/rdl/RDS903151421)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/chamber.py"

    # Data attributes:
    chamberDescription: MultiLanguageString | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    chamberFunction: ChamberFunctionClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    chamberFunctionRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    height: NullableLength | None = Field(None, json_schema_extra={"attribute_category": "data"})
    insideDiameter: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    length: NullableLength | None = Field(None, json_schema_extra={"attribute_category": "data"})
    lowerLimitDesignPressure: NullablePressureGauge | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    lowerLimitDesignTemperature: NullableTemperature | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    materialOfConstructionCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    nominalDiameter: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    nominalDiameterTypeRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    subTagName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    upperLimitDesignPressure: NullablePressureGauge | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    upperLimitDesignTemperature: NullableTemperature | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    width: NullableLength | None = Field(None, json_schema_extra={"attribute_category": "data"})


class ColumnInternalsArrangement(CustomAttributeOwner):
    """The internals of a column, e.g., trays or packings."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/columnInternalsArrangement.py"


class ColumnPackingsArrangement(ColumnInternalsArrangement):
    """The packings of a column."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/columnPackingsArrangement.py"

    # Data attributes:
    height: NullableLength | None = Field(None, json_schema_extra={"attribute_category": "data"})
    materialOfConstructionCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    numberOfPackings: int | None = Field(None, json_schema_extra={"attribute_category": "data"})
    packingType: str | None = Field(None, json_schema_extra={"attribute_category": "data"})


class ColumnSection(CustomAttributeOwner):
    """A column section."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/columnSection.py"

    # Compositional attributes:
    internals: ColumnInternalsArrangement | None = Field(
        None, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    height: NullableLength | None = Field(None, json_schema_extra={"attribute_category": "data"})
    insideDiameter: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class ColumnTraysArrangement(ColumnInternalsArrangement):
    """The trays of a column."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/columnTraysArrangement.py"

    # Data attributes:
    materialOfConstructionCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    numberOfTrays: int | None = Field(None, json_schema_extra={"attribute_category": "data"})
    trayType: str | None = Field(None, json_schema_extra={"attribute_category": "data"})


class CoolingTowerRotor(CustomAttributeOwner):
    """A rotor of a cooling tower."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/coolingTowerRotor.py"

    # Data attributes:
    diameter: NullableLength | None = Field(None, json_schema_extra={"attribute_category": "data"})
    materialOfConstructionCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )

    # Reference attributes:
    chamber: Chamber | None = Field(None, json_schema_extra={"attribute_category": "reference"})


class CrusherElement(CustomAttributeOwner):
    """A functional component of a Crusher."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/crusherElement.py"

    # Data attributes:
    crusherElementType: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    materialOfConstructionCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    stageIdentifier: str | None = Field(None, json_schema_extra={"attribute_category": "data"})


class Displacer(CustomAttributeOwner):
    """An object that has the purpose of displacing a fluid."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/displacer.py"

    # Data attributes:
    materialOfConstructionCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    stageIdentifier: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    volumePerStroke: NullableVolume | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )

    # Reference attributes:
    chamber: Chamber | None = Field(None, json_schema_extra={"attribute_category": "reference"})


class DryingChamber(CustomAttributeOwner):
    """A device that is a chamber, fixed or portable, for drying used as a component of an apparatus or a machine."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/dryingChamber.py"

    # Data attributes:
    designVolumeFlowRate: NullableVolumeFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    materialOfConstructionCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    subTagName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})

    # Reference attributes:
    chamber: Chamber | None = Field(None, json_schema_extra={"attribute_category": "reference"})


class FilterUnit(CustomAttributeOwner):
    """The filtering unit as part of a filter."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/filterUnit.py"

    # Data attributes:
    efficiency: NullablePercentage | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    filterArea: NullableArea | None = Field(None, json_schema_extra={"attribute_category": "data"})
    lowerLimitAllowableSolidsConcentration: NullablePercentage | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    lowerLimitPermeableParticleDiameter: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    materialOfConstructionCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    numberOfFilterElements: int | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    upperLimitAllowableSolidsConcentration: NullablePercentage | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    upperLimitPermeableParticleDiameter: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )

    # Reference attributes:
    chamber: Chamber | None = Field(None, json_schema_extra={"attribute_category": "reference"})


class FilteringCentrifugeDrum(CustomAttributeOwner):
    """A drum being a component of a FilteringCentrifuge."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/filteringCentrifugeDrum.py"

    # Data attributes:
    diameter: NullableLength | None = Field(None, json_schema_extra={"attribute_category": "data"})
    materialOfConstructionCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )

    # Reference attributes:
    chamber: Chamber | None = Field(None, json_schema_extra={"attribute_category": "reference"})


class GearBox(CustomAttributeOwner):
    """An artefact that consists of a gear casing with an arrangement of two or more gear-wheels transmitting rotating motion from the input shaft to the output shaft."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/gearBox.py"

    # Data attributes:
    designInletPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designInletRotationalFrequency: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designOutletPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designOutletRotationalFrequency: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    subTagName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})


class GrindingElement(CustomAttributeOwner):
    """A functional component of a Grinder."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/grindingElement.py"

    # Data attributes:
    grindingElementType: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    materialOfConstructionCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    stageIdentifier: str | None = Field(None, json_schema_extra={"attribute_category": "data"})


class HeatExchangerRotor(CustomAttributeOwner):
    """A rotor as a component of a HeatExchanger."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/heatExchangerRotor.py"

    # Data attributes:
    materialOfConstructionCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )

    # Reference attributes:
    chamber: Chamber | None = Field(None, json_schema_extra={"attribute_category": "reference"})


class Impeller(CustomAttributeOwner):
    """An energy converter component that is an assembly of rotating vanes within an enclosure which is used to impart energy to or derive energy from a fluid through dynamic force (from http://data.posccaesar.org/rdl/RDS414539)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/impeller.py"

    # Data attributes:
    diameter: NullableLength | None = Field(None, json_schema_extra={"attribute_category": "data"})
    materialOfConstructionCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    stageIdentifier: str | None = Field(None, json_schema_extra={"attribute_category": "data"})

    # Reference attributes:
    chamber: Chamber | None = Field(None, json_schema_extra={"attribute_category": "reference"})


class MixingElementAssembly(CustomAttributeOwner):
    """Assembly of mixing elements as part of a mixer."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/mixingElementAssembly.py"

    # Data attributes:
    materialOfConstructionCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    numberOfMixingElements: int | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )

    # Reference attributes:
    chamber: Chamber | None = Field(None, json_schema_extra={"attribute_category": "reference"})


class MotorAsComponent(CustomAttributeOwner):
    """A driver that is powered by electricity or internal combustion and is used as component of an apparatus or of a machine."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/motorAsComponent.py"

    # Data attributes:
    nominalPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    nominalRotationalFrequency: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    subTagName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})


class Nozzle(
    ActuatingElectricalLocation,
    CustomAttributeOwner,
    PipingNodeOwner,
    PipingSourceItem,
    PipingTargetItem,
    SensingLocation,
):
    """A physical object that has a protruding part through which a stream of fluid is directed (from http://data.posccaesar.org/rdl/RDS415214)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nozzle.py"

    # Data attributes:
    nominalPressureNumericalValueRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    nominalPressureRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    nominalPressureStandard: NominalPressureStandardClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    nominalPressureTypeRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    subTagName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})

    # Reference attributes:
    chamber: Chamber | None = Field(None, json_schema_extra={"attribute_category": "reference"})


class PelletizerDisc(CustomAttributeOwner):
    """A rotating disc as a component of an Agglomerator."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/pelletizerDisc.py"

    # Data attributes:
    diameter: NullableLength | None = Field(None, json_schema_extra={"attribute_category": "data"})
    materialOfConstructionCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class Screw(CustomAttributeOwner):
    """A shaft with a helical shaped shaft design (from http://data.posccaesar.org/rdl/RDS7219994)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/screw.py"

    # Data attributes:
    diameter: NullableLength | None = Field(None, json_schema_extra={"attribute_category": "data"})
    materialOfConstructionCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    stageIdentifier: str | None = Field(None, json_schema_extra={"attribute_category": "data"})


class SedimentalCentrifugeDrum(CustomAttributeOwner):
    """A SedimentalCentrifugeDrum is a drum and a component of a SedimentalCentrifuge."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/sedimentalCentrifugeDrum.py"

    # Data attributes:
    diameter: NullableLength | None = Field(None, json_schema_extra={"attribute_category": "data"})
    materialOfConstructionCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )

    # Reference attributes:
    chamber: Chamber | None = Field(None, json_schema_extra={"attribute_category": "reference"})


class SieveElement(CustomAttributeOwner):
    """A screening unit that is a component of a sieve."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/sieveElement.py"

    # Data attributes:
    efficiency: NullablePercentage | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    materialOfConstructionCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    screeningArea: NullableArea | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    stageIdentifier: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    upperLimitPermeableParticleDiameter: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )

    # Reference attributes:
    chamber: Chamber | None = Field(None, json_schema_extra={"attribute_category": "reference"})


class SprayNozzle(CustomAttributeOwner):
    """A nozzle where liquid is introduced under pressure (from http://data.posccaesar.org/rdl/RDS5855670)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/sprayNozzle.py"

    # Data attributes:
    designVolumeFlowRate: NullableVolumeFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    subTagName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})

    # Reference attributes:
    chamber: Chamber | None = Field(None, json_schema_extra={"attribute_category": "reference"})


class SubTaggedColumnSection(ColumnSection):
    """A sub tagged column section."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/subTaggedColumnSection.py"

    # Data attributes:
    subTagName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})


class TaggedPlantItem(CustomAttributeOwner, TechnicalItem):
    """A fully tagged item in a plant."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/taggedPlantItem.py"

    # Data attributes:
    tagName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    tagNamePrefix: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    tagNameSequenceNumber: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    tagNameSuffix: str | None = Field(None, json_schema_extra={"attribute_category": "data"})


class TubeBundle(CustomAttributeOwner):
    """A bundle that consists of several tubes assembled together allowing multiple flow paths from a single source (from http://data.posccaesar.org/rdl/RDS415259)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/tubeBundle.py"

    # Data attributes:
    numberOfTubes: int | None = Field(None, json_schema_extra={"attribute_category": "data"})
    tubeLength: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    tubeMaterialOfConstructionCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    tubeNominalDiameterNumericalValueRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    tubeNominalDiameterRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    tubeNominalDiameterStandard: NominalDiameterStandardClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    tubeNominalDiameterTypeRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )

    # Reference attributes:
    chamber: Chamber | None = Field(None, json_schema_extra={"attribute_category": "reference"})


class DirectPipingConnection(PipingConnection):
    """A direct connection between two piping items, i.e. a connection that is not realized by a pipe."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/directPipingConnection.py"


class Pipe(CustomAttributeOwner, PipingConnection):
    """An elementary piece of piping, i.e., not interrupted by any item."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/pipe.py"


class PipeOffPageConnector(CustomAttributeOwner, PipingNetworkSegmentItem, PipingNodeOwner):
    """A connector that indicates that a piping network segment is continued elsewhere, either on the same PID or on another PID. Graphically, it is usually represented as an arrow."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/pipeOffPageConnector.py"

    # Compositional attributes:
    connectorReference: PipeOffPageConnectorReference | None = Field(
        None, json_schema_extra={"attribute_category": "composition"}
    )


class PipeOffPageConnectorReference(CustomAttributeOwner):
    """A reference to a PipeOffPageConnector."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/pipeOffPageConnectorReference.py"


class PipeOffPageConnectorReferenceByNumber(PipeOffPageConnectorReference):
    """A reference to a PipeOffPageConnector by drawing and connector number."""

    uri: ClassVar[str] = (
        "https://pyDEXPI.org/schemas/pydexpi_1_3/pipeOffPageConnectorReferenceByNumber.py"
    )

    # Data attributes:
    referencedConnectorNumber: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    referencedDrawingNumber: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class PipingComponent(
    CustomAttributeOwner,
    PipingNetworkSegmentItem,
    PipingNodeOwner,
    PipingSourceItem,
    PipingTargetItem,
    SensingLocation,
):
    """A piping component"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/pipingComponent.py"

    # Data attributes:
    fluidCode: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    onHold: OnHoldClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    pipingClassArtefact: PipingClassArtefactClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    pressureTestCircuitNumber: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class PipingNetworkSegment(ActuatingElectricalLocation, CustomAttributeOwner, SensingLocation):
    """The piping limited by a Node and a Break, Node and Connector,  two Nodes, two Breaks, two Connectors or a Break and a Connector. The last five providing there are no Breaks or Connectors in between. In the last three cases the Segment will coincide with a Piping Branch (from http://data.posccaesar.org/rdl/RDS267704)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/pipingNetworkSegment.py"

    # Compositional attributes:
    connections: list[PipingConnection] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )
    items: list[PipingNetworkSegmentItem] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    colorCode: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    flowDirection: PipingNetworkSegmentFlowClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    fluidCode: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    heatTracingType: HeatTracingTypeClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    heatTracingTypeRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    inclination: NullablePercentage | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    insulationThickness: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    insulationType: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    jacketedPipe: JacketedPipeClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    lowerLimitHeatTracingTemperature: NullableTemperature | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    nominalDiameterNumericalValueRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    nominalDiameterRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    nominalDiameterStandard: NominalDiameterStandardClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    nominalDiameterTypeRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    onHold: OnHoldClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    operatingTemperature: NullableTemperature | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    pipingClassCode: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    pressureTestCircuitNumber: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    primarySecondaryPipingNetworkSegment: (
        PrimarySecondaryPipingNetworkSegmentClassification | None
    ) = Field(None, json_schema_extra={"attribute_category": "data"})
    segmentNumber: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    siphon: SiphonClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    slope: PipingNetworkSegmentSlopeClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )

    # Reference attributes:
    sourceItem: PipingSourceItem | None = Field(
        None, json_schema_extra={"attribute_category": "reference"}
    )
    sourceNode: PipingNode | None = Field(
        None, json_schema_extra={"attribute_category": "reference"}
    )
    targetItem: PipingTargetItem | None = Field(
        None, json_schema_extra={"attribute_category": "reference"}
    )
    targetNode: PipingNode | None = Field(
        None, json_schema_extra={"attribute_category": "reference"}
    )


class PipingNetworkSystem(CustomAttributeOwner, TechnicalItem):
    """A fluid system of interconnected piping network branches limited by Unit Operation Inlet/Outlet and  Piping Network Terminators. In this context Piping includes e.g. plumbing and tubing (from http://data.posccaesar.org/rdl/RDS270359)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/pipingNetworkSystem.py"

    # Compositional attributes:
    segments: list[PipingNetworkSegment] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    fluidCode: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    heatTracingType: HeatTracingTypeClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    heatTracingTypeRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    insulationThickness: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    insulationType: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    jacketLineNumber: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    jacketedLineNumber: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    jacketedPipe: JacketedPipeClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    lineNumber: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    lowerLimitHeatTracingTemperature: NullableTemperature | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    nominalDiameterNumericalValueRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    nominalDiameterRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    nominalDiameterStandard: NominalDiameterStandardClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    nominalDiameterTypeRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    onHold: OnHoldClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    pipingClassCode: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    pipingNetworkSystemGroupNumber: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class PipingNode(CustomAttributeOwner):
    """A possible connection point for a PipingConnection."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/pipingNode.py"

    # Data attributes:
    nominalDiameterNumericalValueRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    nominalDiameterRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    nominalDiameterStandard: NominalDiameterStandardClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    nominalDiameterTypeRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class PropertyBreak(
    CustomAttributeOwner,
    PipingNetworkSegmentItem,
    PipingNodeOwner,
    PipingSourceItem,
    PipingTargetItem,
):
    """A symbol indicating a change in the piping properties."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/propertyBreak.py"

    # Data attributes:
    compositionBreak: CompositionBreakClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    insulationBreak: InsulationBreakClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    nominalDiameterBreak: NominalDiameterBreakClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    pipingClassBreak: PipingClassBreakClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class SafetyValveOrFitting(PipingComponent):
    """A safety valve or fitting."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/safetyValveOrFitting.py"

    # Data attributes:
    flowInPipingClassCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    flowOutPipingClassCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    locationRegistrationNumber: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    positionNumber: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    setPressureHigh: NullablePressureGauge | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    setPressureLow: NullablePressureGauge | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class SpringLoadedAngleGlobeSafetyValve(SafetyValveOrFitting):
    """A spring-loaded angle globe safety valve."""

    uri: ClassVar[str] = (
        "https://pyDEXPI.org/schemas/pydexpi_1_3/springLoadedAngleGlobeSafetyValve.py"
    )


class SpringLoadedGlobeSafetyValve(SafetyValveOrFitting):
    """A spring-loaded globe safety valve."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/springLoadedGlobeSafetyValve.py"


class ActuatingElectricalFunction(
    CustomAttributeOwner, SignalConveyingFunctionTarget, TechnicalItem
):
    """An actuation setting electrical function. It covers all types of electrical consumers, e.g., motors and heaters."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/actuatingElectricalFunction.py"

    # Data attributes:
    actuatingElectricalFunctionNumber: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )

    # Reference attributes:
    actuatingElectricalLocation: ActuatingElectricalLocation | None = Field(
        None, json_schema_extra={"attribute_category": "reference"}
    )
    systems: ActuatingElectricalSystem | None = Field(
        None, json_schema_extra={"attribute_category": "reference"}
    )


class ActuatingElectricalSystem(CustomAttributeOwner, TechnicalItem):
    """An assembly of artefacts that is designed to fulfill an ActuatingElectricalFunction."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/actuatingElectricalSystem.py"

    # Compositional attributes:
    customComponents: list[CustomActuatingElectricalSystemComponent] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )
    electronicFrequencyConverter: ElectronicFrequencyConverter | None = Field(
        None, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    actuatingElectricalSystemNumber: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    typicalInformation: str | None = Field(None, json_schema_extra={"attribute_category": "data"})


class ActuatingFunction(
    CustomAttributeOwner,
    SignalConveyingFunctionSource,
    SignalConveyingFunctionTarget,
    TechnicalItem,
):
    """A function for acting control structures relating to the process."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/actuatingFunction.py"

    # Data attributes:
    actuatingFunctionNumber: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )

    # Reference attributes:
    actuatingLocation: PipingNetworkSegment | None = Field(
        None, json_schema_extra={"attribute_category": "reference"}
    )
    systems: ActuatingSystem | None = Field(
        None, json_schema_extra={"attribute_category": "reference"}
    )


class ActuatingSystem(CustomAttributeOwner, TechnicalItem):
    """An assembly of artefacts that is designed to fulfill an ActuatingFunction."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/actuatingSystem.py"

    # Compositional attributes:
    controlledActuator: ControlledActuator | None = Field(
        None, json_schema_extra={"attribute_category": "composition"}
    )
    customComponents: list[CustomActuatingSystemComponent] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )
    operatedValveReference: OperatedValveReference | None = Field(
        None, json_schema_extra={"attribute_category": "composition"}
    )
    positioner: Positioner | None = Field(
        None, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    actuatingSystemNumber: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    typicalInformation: str | None = Field(None, json_schema_extra={"attribute_category": "data"})


class ControlledActuator(CustomAttributeOwner):
    """A transducer that is intended to convert energy (electric, mechanical, pneumatic or hydraulic) from an external source into kinetic energy (motion) in response to a signal or power input."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/controlledActuator.py"

    # Data attributes:
    deviceTypeName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    failAction: FailActionClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    failActionRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    subTagName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})


class CustomActuatingElectricalSystemComponent(CustomAttributeOwner, CustomObject):
    """A custom component of an ActuatingElectricalSystem, i.e., a component other than ."""

    uri: ClassVar[str] = (
        "https://pyDEXPI.org/schemas/pydexpi_1_3/customActuatingElectricalSystemComponent.py"
    )


class CustomActuatingSystemComponent(CustomAttributeOwner, CustomObject):
    """A custom component of an ActuatingSystem, i.e., a component other than a ControlledActuator, an OperatedValveReference,  or  a Positioner."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customActuatingSystemComponent.py"


class CustomProcessSignalGeneratingSystemComponent(CustomAttributeOwner, CustomObject):
    """A custom component of a ProcessSignalGeneratingSystem, i.e., a component other than a PrimaryElement  or  a Transmitter."""

    uri: ClassVar[str] = (
        "https://pyDEXPI.org/schemas/pydexpi_1_3/customProcessSignalGeneratingSystemComponent.py"
    )


class ElectronicFrequencyConverter(CustomAttributeOwner):
    """An electronic AC converter for changing the frequency"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/electronicFrequencyConverter.py"

    # Data attributes:
    subTagName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})


class InstrumentationLoopFunction(CustomAttributeOwner, TechnicalItem):
    """An identified collection of related ProcessInstrumentationFunctions that interact for a known purpose."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/instrumentationLoopFunction.py"

    # Data attributes:
    instrumentationLoopFunctionNumber: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )

    # Reference attributes:
    processInstrumentationFunctions: list[ProcessInstrumentationFunction] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "reference"}
    )


class OperatedValveReference(CustomAttributeOwner):
    """A reference to an OperatedValve."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/operatedValveReference.py"

    # Data attributes:
    subTagName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})

    # Reference attributes:
    valve: OperatedValve | None = Field(None, json_schema_extra={"attribute_category": "reference"})


class Positioner(CustomAttributeOwner):
    """A positioner."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/positioner.py"

    # Data attributes:
    deviceTypeName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    subTagName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})


class PrimaryElement(CustomAttributeOwner):
    """An artefact that converts the input variable into a signal suitable for measurement."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/primaryElement.py"

    # Data attributes:
    subTagName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})


class ProcessInstrumentationFunction(
    CustomAttributeOwner,
    SignalConveyingFunctionSource,
    SignalConveyingFunctionTarget,
    TechnicalItem,
):
    """A requirement for instrumentation and/or control structures relating to Process Engineering."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/processInstrumentationFunction.py"

    # Compositional attributes:
    actuatingElectricalFunctions: list[ActuatingElectricalFunction] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )
    actuatingFunctions: list[ActuatingFunction] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )
    processSignalGeneratingFunctions: list[ProcessSignalGeneratingFunction] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )
    signalConnectors: list[SignalOffPageConnector] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )
    signalConveyingFunctions: list[SignalConveyingFunction] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    deviceInformation: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    gmpRelevance: GmpRelevanceClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    guaranteedSupplyFunction: GuaranteedSupplyFunctionClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    location: LocationClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    panelIdentificationCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    processInstrumentationFunctionCategory: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    processInstrumentationFunctionModifier: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    processInstrumentationFunctionNumber: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    processInstrumentationFunctions: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    qualityRelevance: QualityRelevanceClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    safetyRelevanceClass: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    typicalInformation: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    vendorCompanyName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    votingSystemRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class ProcessSignalGeneratingFunction(
    CustomAttributeOwner, SignalConveyingFunctionSource, TechnicalItem
):
    """A function for instrumentation and/or control structures relating to Process Engineering"""

    uri: ClassVar[str] = (
        "https://pyDEXPI.org/schemas/pydexpi_1_3/processSignalGeneratingFunction.py"
    )

    # Data attributes:
    processSignalGeneratingFunctionNumber: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    sensorType: str | None = Field(None, json_schema_extra={"attribute_category": "data"})

    # Reference attributes:
    sensingLocation: SensingLocation | None = Field(
        None, json_schema_extra={"attribute_category": "reference"}
    )
    systems: ProcessSignalGeneratingSystem | None = Field(
        None, json_schema_extra={"attribute_category": "reference"}
    )


class ProcessSignalGeneratingSystem(CustomAttributeOwner, TechnicalItem):
    """An assembly of artefacts that is designed to fulfill one or more ProcessSignalGeneratingFunctions."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/processSignalGeneratingSystem.py"

    # Compositional attributes:
    customComponents: list[CustomProcessSignalGeneratingSystemComponent] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )
    primaryElement: PrimaryElement | None = Field(
        None, json_schema_extra={"attribute_category": "composition"}
    )
    transmitter: Transmitter | None = Field(
        None, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    processSignalGeneratingSystemNumber: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    typicalInformation: str | None = Field(None, json_schema_extra={"attribute_category": "data"})


class SignalConveyingFunction(CustomAttributeOwner):
    """A function for conveying a signal."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/signalConveyingFunction.py"

    # Data attributes:
    portStatus: PortStatusClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    signalConveyingType: SignalConveyingTypeClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    signalPointNumber: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    signalProcessControlFunctions: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )

    # Reference attributes:
    source: SignalConveyingFunctionSource | None = Field(
        None, json_schema_extra={"attribute_category": "reference"}
    )
    target: SignalConveyingFunctionTarget | None = Field(
        None, json_schema_extra={"attribute_category": "reference"}
    )


class SignalLineFunction(SignalConveyingFunction):
    """Information flow function for signals."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/signalLineFunction.py"


class SignalOffPageConnector(CustomAttributeOwner):
    """A signal connector that indicates that a SignalConveyingFunction is continued elsewhere, either on the same P&ID or on another P&ID. Graphically, it is usually represented as an arrow."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/signalOffPageConnector.py"

    # Compositional attributes:
    connectorReference: SignalOffPageConnectorReference | None = Field(
        None, json_schema_extra={"attribute_category": "composition"}
    )


class SignalOffPageConnectorReference(CustomAttributeOwner):
    """A reference to a SignalOffPageConnector."""

    uri: ClassVar[str] = (
        "https://pyDEXPI.org/schemas/pydexpi_1_3/signalOffPageConnectorReference.py"
    )


class SignalOffPageConnectorReferenceByNumber(SignalOffPageConnectorReference):
    """A reference to a SignalOffPageConnector by drawing and connector number."""

    uri: ClassVar[str] = (
        "https://pyDEXPI.org/schemas/pydexpi_1_3/signalOffPageConnectorReferenceByNumber.py"
    )

    # Data attributes:
    referencedConnectorNumber: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    referencedDrawingNumber: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class Transmitter(CustomAttributeOwner):
    """A detecting instrument that generates a process variable signal and converts it into an output signal."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/transmitter.py"

    # Data attributes:
    deviceTypeName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    subTagName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})


class CustomAreaAttribute(CustomAttribute):
    """A custom attribute with Value type NullableArea."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customAreaAttribute.py"

    # Data attributes:
    value: NullableArea = Field(..., json_schema_extra={"attribute_category": "data"})


class Area(NullableArea):
    """An actual value for a physical quantity of type NullableArea, i.e., a physical quantity that has a numerical value and a unit of measurement."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/area.py"

    # Data attributes:
    unit: AreaUnit = Field(..., json_schema_extra={"attribute_category": "data"})
    value: float = Field(..., json_schema_extra={"attribute_category": "data"})


class Force(NullableForce):
    """An actual value for a physical quantity of type NullableForce, i.e., a physical quantity that has a numerical value and a unit of measurement."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/force.py"

    # Data attributes:
    unit: ForceUnit = Field(..., json_schema_extra={"attribute_category": "data"})
    value: float = Field(..., json_schema_extra={"attribute_category": "data"})


class HeatTransferCoefficient(NullableHeatTransferCoefficient):
    """An actual value for a physical quantity of type NullableHeatTransferCoefficient, i.e., a physical quantity that has a numerical value and a unit of measurement."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/heatTransferCoefficient.py"

    # Data attributes:
    unit: HeatTransferCoefficientUnit = Field(..., json_schema_extra={"attribute_category": "data"})
    value: float = Field(..., json_schema_extra={"attribute_category": "data"})


class Length(NullableLength):
    """An actual value for a physical quantity of type NullableLength, i.e., a physical quantity that has a numerical value and a unit of measurement."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/length.py"

    # Data attributes:
    unit: LengthUnit = Field(..., json_schema_extra={"attribute_category": "data"})
    value: float = Field(..., json_schema_extra={"attribute_category": "data"})


class Mass(NullableMass):
    """An actual value for a physical quantity of type NullableMass, i.e., a physical quantity that has a numerical value and a unit of measurement."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/mass.py"

    # Data attributes:
    unit: MassUnit = Field(..., json_schema_extra={"attribute_category": "data"})
    value: float = Field(..., json_schema_extra={"attribute_category": "data"})


class MassFlowRate(NullableMassFlowRate):
    """An actual value for a physical quantity of type NullableMassFlowRate, i.e., a physical quantity that has a numerical value and a unit of measurement."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/massFlowRate.py"

    # Data attributes:
    unit: MassFlowRateUnit = Field(..., json_schema_extra={"attribute_category": "data"})
    value: float = Field(..., json_schema_extra={"attribute_category": "data"})


class NullArea(DexpiSingletonBaseModel, NullableArea):
    """A null value for a physical quantity of type NullableArea. The only instance of this singleton type is NULL_AREA."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nullArea.py"


class NullForce(DexpiSingletonBaseModel, NullableForce):
    """A null value for a physical quantity of type NullableForce. The only instance of this singleton type is NULL_FORCE."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nullForce.py"


class NullHeatTransferCoefficient(DexpiSingletonBaseModel, NullableHeatTransferCoefficient):
    """A null value for a physical quantity of type NullableHeatTransferCoefficient. The only instance of this singleton type is NULL_HEAT_TRANSFER_COEFFICIENT."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nullHeatTransferCoefficient.py"


class NullLength(DexpiSingletonBaseModel, NullableLength):
    """A null value for a physical quantity of type NullableLength. The only instance of this singleton type is NULL_LENGTH."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nullLength.py"


class NullMass(DexpiSingletonBaseModel, NullableMass):
    """A null value for a physical quantity of type NullableMass. The only instance of this singleton type is NULL_MASS."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nullMass.py"


class NullMassFlowRate(DexpiSingletonBaseModel, NullableMassFlowRate):
    """A null value for a physical quantity of type NullableMassFlowRate. The only instance of this singleton type is NULL_MASS_FLOW_RATE."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nullMassFlowRate.py"


class NullNumberPerTimeInterval(DexpiSingletonBaseModel, NullableNumberPerTimeInterval):
    """A null value for a physical quantity of application type NullableNumberPerTimeInterval. The only instance of this singleton type is NULL_NUMBER_PER_TIME_INTERVAL."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nullNumberPerTimeInterval.py"


class NullPercentage(DexpiSingletonBaseModel, NullablePercentage):
    """A null value for a physical quantity of type NullablePercentage. The only instance of this singleton type is NULL_PERCENTAGE."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nullPercentage.py"


class NullPower(DexpiSingletonBaseModel, NullablePower):
    """A null value for a physical quantity of type NullablePower. The only instance of this singleton type is NULL_POWER."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nullPower.py"


class NullPressureAbsolute(DexpiSingletonBaseModel, NullablePressureAbsolute):
    """A null value for a physical quantity of application type NullablePressureAbsolute. The only instance of this singleton type is NULL_PRESSURE_ABSOLUTE."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nullPressureAbsolute.py"


class NullPressureGauge(DexpiSingletonBaseModel, NullablePressureGauge):
    """A null value for a physical quantity of application type NullablePressureGauge. The only instance of this singleton type is NULL_PRESSURE_GAUGE."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nullPressureGauge.py"


class NullRotationalFrequency(DexpiSingletonBaseModel, NullableRotationalFrequency):
    """A null value for a physical quantity of application type NullableRotationalFrequency. The only instance of this singleton type is NULL_ROTATIONAL_FREQUENCY."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nullRotationalFrequency.py"


class NullTemperature(DexpiSingletonBaseModel, NullableTemperature):
    """A null value for a physical quantity of type NullableTemperature. The only instance of this singleton type is NULL_TEMPERATURE."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nullTemperature.py"


class NullVoltage(DexpiSingletonBaseModel, NullableVoltage):
    """A null value for a physical quantity of type NullableVoltage. The only instance of this singleton type is NULL_VOLTAGE."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nullVoltage.py"


class NullVolume(DexpiSingletonBaseModel, NullableVolume):
    """A null value for a physical quantity of type NullableVolume. The only instance of this singleton type is NULL_VOLUME."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nullVolume.py"


class NullVolumeFlowRate(DexpiSingletonBaseModel, NullableVolumeFlowRate):
    """A null value for a physical quantity of type NullableVolumeFlowRate. The only instance of this singleton type is NULL_VOLUME_FLOW_RATE."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nullVolumeFlowRate.py"


class NullableElectricalFrequency(NullableFrequency):
    """A physical quantity of dimension T-1 (inherited from NullableFrequency) for the application type electrical frequency. NullableElectricalFrequency is abstract and has two concrete subtypes:
            - an ElectricalFrequency is an actual value for a physical quantity with a numerical value and a unit of measurement;
    - a NullElectricalFrequency is a null value that explicitly indicates the absence of an actual physical quantity."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nullableElectricalFrequency.py"


class ActuatingElectricalFunctionShape(Shape):
    """"""

    uri: ClassVar[str] = (
        "https://pyDEXPI.org/schemas/pydexpi_1_4/actuatingElectricalFunctionShape.py"
    )


class ActuatingElectricalSystemComponentShape(Shape):
    """"""

    uri: ClassVar[str] = (
        "https://pyDEXPI.org/schemas/pydexpi_1_4/actuatingElectricalSystemComponentShape.py"
    )


class ActuatingElectricalSystemShape(Shape):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/actuatingElectricalSystemShape.py"


class ActuatingFunctionShape(Shape):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/actuatingFunctionShape.py"


class ActuatingSystemComponentShape(Shape):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/actuatingSystemComponentShape.py"


class ActuatingSystemShape(Shape):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/actuatingSystemShape.py"


class AttributeRepresentation(TextTemplateFragment):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/attributeRepresentation.py"

    # Data attributes:
    attributeName: str = Field(..., json_schema_extra={"attribute_category": "data"})
    type: AttributeRepresentationType = Field(..., json_schema_extra={"attribute_category": "data"})

    # Reference attributes:
    object: DexpiBaseModel = Field(..., json_schema_extra={"attribute_category": "reference"})


class Border(RepresentationTypeGroup):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/border.py"


class ConnectorLine(GraphicalPrimitive):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/connectorLine.py"

    # Data attributes:
    innerPoints: list[Point] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "data"}
    )
    stroke: Stroke = Field(..., json_schema_extra={"attribute_category": "data"})

    # Reference attributes:
    source: NodePosition | None = Field(None, json_schema_extra={"attribute_category": "reference"})
    target: NodePosition | None = Field(None, json_schema_extra={"attribute_category": "reference"})


class CustomSymbol(CustomObject, Symbol):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/customSymbol.py"


class Diagram(RepresentationGroup):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/diagram.py"

    # Data attributes:
    backgroundColor: Color = Field(..., json_schema_extra={"attribute_category": "data"})
    maxX: float = Field(..., json_schema_extra={"attribute_category": "data"})
    maxY: float = Field(..., json_schema_extra={"attribute_category": "data"})
    minX: float = Field(..., json_schema_extra={"attribute_category": "data"})
    minY: float = Field(..., json_schema_extra={"attribute_category": "data"})
    name: str = Field(..., json_schema_extra={"attribute_category": "data"})


class Ellipse(GraphicalPrimitive):
    """An ellipse."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/ellipse.py"

    # Data attributes:
    center: Point = Field(..., json_schema_extra={"attribute_category": "data"})
    fillStyle: FillStyle = Field(..., json_schema_extra={"attribute_category": "data"})
    horizontalSemiAxis: float = Field(..., json_schema_extra={"attribute_category": "data"})
    rotation: float = Field(..., json_schema_extra={"attribute_category": "data"})
    stroke: Stroke = Field(..., json_schema_extra={"attribute_category": "data"})
    verticalSemiAxis: float = Field(..., json_schema_extra={"attribute_category": "data"})


class EllipseArc(GraphicalPrimitive):
    """A segment of an ellipse."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/ellipseArc.py"

    # Data attributes:
    center: Point = Field(..., json_schema_extra={"attribute_category": "data"})
    endAngle: float = Field(..., json_schema_extra={"attribute_category": "data"})
    horizontalSemiAxis: float = Field(..., json_schema_extra={"attribute_category": "data"})
    rotation: float = Field(..., json_schema_extra={"attribute_category": "data"})
    startAngle: float = Field(..., json_schema_extra={"attribute_category": "data"})
    stroke: Stroke = Field(..., json_schema_extra={"attribute_category": "data"})
    verticalSemiAxis: float = Field(..., json_schema_extra={"attribute_category": "data"})


class InstrumentationLoopFunctionShape(Shape):
    """"""

    uri: ClassVar[str] = (
        "https://pyDEXPI.org/schemas/pydexpi_1_4/instrumentationLoopFunctionShape.py"
    )


class InstrumentationNodePosition(NodePosition):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/instrumentationNodePosition.py"


class InsulationSymbol(Symbol):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/insulationSymbol.py"


class InsulationSymbolShape(Shape):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/insulationSymbolShape.py"


class Label(RepresentationTypeGroup):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/label.py"


class LabelShape(Shape):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/labelShape.py"


class LiteralText(TextTemplateFragment):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/literalText.py"

    # Data attributes:
    text: str = Field(..., json_schema_extra={"attribute_category": "data"})


class MPRelevanceLabel(Label):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/mPRelevanceLabel.py"


class MeasuringSystemComponentShape(Shape):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/measuringSystemComponentShape.py"


class MeasuringSystemNumberLabel(Label):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/measuringSystemNumberLabel.py"


class MeasuringSystemShape(Shape):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/measuringSystemShape.py"


class NoteIdentifierLabel(Label):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/noteIdentifierLabel.py"


class NoteShape(Shape):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/noteShape.py"


class NoteTextLabel(Label):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/noteTextLabel.py"


class NozzleShape(Shape):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/nozzleShape.py"


class NozzleStandardLabel(Label):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/nozzleStandardLabel.py"


class OffPageConnectorDescriptionLabel(Label):
    """"""

    uri: ClassVar[str] = (
        "https://pyDEXPI.org/schemas/pydexpi_1_4/offPageConnectorDescriptionLabel.py"
    )


class OffPageConnectorNumberLabel(Label):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/offPageConnectorNumberLabel.py"


class PipeFlowArrow(Symbol):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/pipeFlowArrow.py"


class PipeFlowArrowShape(Shape):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/pipeFlowArrowShape.py"


class PipeOffPageConnectorShape(Shape):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/pipeOffPageConnectorShape.py"


class PipeSlopeSymbol(Symbol):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/pipeSlopeSymbol.py"


class PipeSlopeSymbolShape(Shape):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/pipeSlopeSymbolShape.py"


class PipingClassBreakLabel(Label):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/pipingClassBreakLabel.py"


class PipingComponentShape(Shape):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/pipingComponentShape.py"


class PipingNetworkSegmentLabel(Label):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/pipingNetworkSegmentLabel.py"


class PipingNetworkSystemLabel(Label):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/pipingNetworkSystemLabel.py"


class ProcessInstrumentationFunctionLabel(Label):
    """"""

    uri: ClassVar[str] = (
        "https://pyDEXPI.org/schemas/pydexpi_1_4/processInstrumentationFunctionLabel.py"
    )


class ProcessInstrumentationFunctionShape(Shape):
    """"""

    uri: ClassVar[str] = (
        "https://pyDEXPI.org/schemas/pydexpi_1_4/processInstrumentationFunctionShape.py"
    )


class ProcessSignalGeneratingFunctionShape(Shape):
    """"""

    uri: ClassVar[str] = (
        "https://pyDEXPI.org/schemas/pydexpi_1_4/processSignalGeneratingFunctionShape.py"
    )


class PropertyBreakShape(Shape):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/propertyBreakShape.py"


class QualityRelevanceLabel(Label):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/qualityRelevanceLabel.py"


class ReducerLabel(Label):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/reducerLabel.py"


class ReferencedPIDNumberLabel(Label):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/referencedPIDNumberLabel.py"


class SafetyRelevanceLabel(Label):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/safetyRelevanceLabel.py"


class SafetyValveOrFittingLabel(Label):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/safetyValveOrFittingLabel.py"


class SignalConveyingFunctionLabel(Label):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/signalConveyingFunctionLabel.py"


class SignalHighHighHighLabel(Label):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/signalHighHighHighLabel.py"


class SignalHighHighLabel(Label):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/signalHighHighLabel.py"


class SignalHighLabel(Label):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/signalHighLabel.py"


class SignalLowLabel(Label):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/signalLowLabel.py"


class SignalLowLowLabel(Label):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/signalLowLowLabel.py"


class SignalLowLowLowLabel(Label):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/signalLowLowLowLabel.py"


class TypicalInformationLabel(Label):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/typicalInformationLabel.py"


class ValveLabel(Label):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/valveLabel.py"


class VendorNameLabel(Label):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/vendorNameLabel.py"


class Enterprise(
    IndustrialComplexParentStructure,
    PlantSectionParentStructure,
    PlantStructureItem,
    ProcessPlantParentStructure,
    TechnicalItemParentStructure,
):
    """An enterprise as defined by ISA 95."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/enterprise.py"

    # Data attributes:
    enterpriseIdentificationCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    enterpriseName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})


class IndustrialComplex(
    PlantAreaLocatedStructure,
    PlantSectionParentStructure,
    PlantStructureItem,
    ProcessPlantParentStructure,
    TechnicalItemParentStructure,
):
    """An industrial complex as defined by ISO 10209:2012."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/industrialComplex.py"

    # Data attributes:
    industrialComplexIdentificationCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    industrialComplexName: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )

    # Reference attributes:
    parentStructure: IndustrialComplexParentStructure | None = Field(
        None, json_schema_extra={"attribute_category": "reference"}
    )


class PlantArea(PlantStructureItem):
    """An area as defined by ISA 95. The name PlantArea has been chosen to avoid confusion with the data type Area."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/plantArea.py"

    # Data attributes:
    plantAreaIdentificationCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    plantAreaName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})


class PlantSection(PlantAreaLocatedStructure, PlantStructureItem, TechnicalItemParentStructure):
    """A plant section as defined by ISO 10209:2012."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/plantSection.py"

    # Data attributes:
    plantSectionIdentificationCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    plantSectionName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})

    # Reference attributes:
    parentStructure: PlantSectionParentStructure | None = Field(
        None, json_schema_extra={"attribute_category": "reference"}
    )


class AlternatingCurrentMotorAsComponent(MotorAsComponent):
    """An electric motor driven by alternating electric current that is used as a component of an apparatus or of a machine."""

    uri: ClassVar[str] = (
        "https://pyDEXPI.org/schemas/pydexpi_1_3/alternatingCurrentMotorAsComponent.py"
    )

    # Data attributes:
    alternatingCurrentFrequency: NullableElectricalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    nominalVoltage: NullableVoltage | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class CombustionEngineAsComponent(MotorAsComponent):
    """An engine intended to deliver power by means of burning fuels that is used as component of an apparatus or of a machine."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/combustionEngineAsComponent.py"

    # Data attributes:
    fuelType: str | None = Field(None, json_schema_extra={"attribute_category": "data"})


class DirectCurrentMotorAsComponent(MotorAsComponent):
    """An electric motor for operation by direct current that is used as component of an apparatus or of a machine."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/directCurrentMotorAsComponent.py"

    # Data attributes:
    nominalVoltage: NullableVoltage | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class Equipment(ChamberOwner, NozzleOwner, TaggedPlantItem):
    """An apparatus or machine."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/equipment.py"

    # Compositional attributes:
    dryingChambers: list[DryingChamber] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )
    gearBoxes: list[GearBox] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )
    motors: list[MotorAsComponent] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )
    sprayNozzles: list[SprayNozzle] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    equipmentDescription: MultiLanguageString | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class Extruder(Equipment):
    """A machine that has the capability of extruding (from http://data.15926.org/rdl/RDS394044551)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/extruder.py"

    # Data attributes:
    designMassFlowRate: NullableMassFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designRotationalSpeed: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designShaftPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class Fan(Equipment):
    """An object that is capable of delivering or exhausting volumes of vapour or gas at low differential pressure (from http://data.15926.org/rdl/RDS415169)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/fan.py"

    # Data attributes:
    designDifferentialPressure: NullablePressureAbsolute | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designRotationalSpeed: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designShaftPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designVolumeFlowRate: NullableVolumeFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class Feeder(Equipment):
    """A closed fluid transporter that is a gathering line tied into a trunk line (from http://data.15926.org/rdl/RDS300644)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/feeder.py"

    # Data attributes:
    designMassFlowRate: NullableMassFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designRotationalSpeed: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designShaftPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    upperLimitDesignParticleSize: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class Filter(Equipment):
    """An apparatus or machine that is capable of filtering (from http://data.15926.org/rdl/RDS300689)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/filter.py"


class GasFilter(Filter):
    """A filter that is specifically designed to filter a gas."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/gasFilter.py"

    # Compositional attributes:
    filterUnit: FilterUnit | None = Field(
        None, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    designCapacityVolumeFlowRate: NullableVolumeFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designRotationalSpeed: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designShaftPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    upperLimitAllowableDesignPressureDrop: NullablePressureAbsolute | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class HeatExchanger(Equipment):
    """An apparatus or machine that has the capability of heat exchanging (from http://data.15926.org/rdl/RDS304199)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/heatExchanger.py"

    # Data attributes:
    designHeatFlowRate: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designHeatTransferArea: NullableArea | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designHeatTransferCoefficient: NullableHeatTransferCoefficient | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )

    # Reference attributes:
    agitator: Agitator | None = Field(None, json_schema_extra={"attribute_category": "reference"})


class Heater(Equipment):
    """An apparatus or machine that has the capability of heating."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/heater.py"

    # Data attributes:
    designHeatFlowRate: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designMassFlowRate: NullableMassFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designOutletPressure: NullablePressureGauge | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designOutletTemperature: NullableTemperature | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designVolumeFlowRate: NullableVolumeFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class LiquidFilter(Filter):
    """A filter that is specifically designed to filter a liquid."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/liquidFilter.py"

    # Compositional attributes:
    filterUnit: FilterUnit | None = Field(
        None, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    designCapacityVolumeFlowRate: NullableVolumeFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designRotationalSpeed: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designShaftPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    upperLimitAllowableDesignPressureDrop: NullablePressureAbsolute | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class Mill(Equipment):
    """A physical object for grinding or pulverizing materials. Also a machine for shaping metal. In general a machine that manufactures by the continuous repetition of some simple action (from http://data.posccaesar.org/rdl/RDS11589220)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/mill.py"

    # Data attributes:
    designCapacityMassFlowRate: NullableMassFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designRotationalSpeed: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designShaftPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    lowerLimitDesignOutputParticleSize: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    upperLimitDesignInputParticleSize: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    upperLimitDesignOutputParticleSize: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class Mixer(Equipment):
    """An apparatus or machine that has the capability of mixing (from http://data.15926.org/rdl/RDS222370)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/mixer.py"

    # Compositional attributes:
    mixingElementAssemblies: list[MixingElementAssembly] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )


class MobileTransportSystem(Equipment):
    """A mobile system that is intended to transport, store or load/unload material."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/mobileTransportSystem.py"

    # Data attributes:
    upperLimitLoadCapacity: NullableMass | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    upperLimitVolumeCapacity: NullableVolume | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class Motor(Equipment):
    """A driver that is powered by electricity or internal combustion (from http://data.15926.org/rdl/RDS7191198)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/motor.py"

    # Data attributes:
    nominalPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    nominalRotationalFrequency: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class PackagingSystem(Equipment):
    """A system that is intended for the preparation of goods for transport, warehousing, logistics, sale, and end use (from http://data.15926.org/rdl/RDS2228725)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/packagingSystem.py"

    # Data attributes:
    designCapacityMassFlowRate: NullableMassFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designCapacityPackagingUnits: NullableNumberPerTimeInterval | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    packagingSystemType: str | None = Field(None, json_schema_extra={"attribute_category": "data"})


class PlateHeatExchanger(HeatExchanger):
    """A heat exchanger that uses metal plates to transfer heat between two fluids."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/plateHeatExchanger.py"

    # Data attributes:
    numberOfPlates: int | None = Field(None, json_schema_extra={"attribute_category": "data"})
    plateHeight: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    plateWidth: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class ProcessColumn(Equipment):
    """A vertical vessel intended to enable chemical reactions or physical processes utilising differences in density of fluids and/or forced flow of fluid (from http://data.posccaesar.org/rdl/RDS4316825224)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/processColumn.py"

    # Compositional attributes:
    columnSections: list[SubTaggedColumnSection] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    nominalCapacityVolume: NullableVolume | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class Pump(Equipment):
    """A machine that is capable of pumping but may require parts and subsystems for that capability."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/pump.py"

    # Data attributes:
    designPressureHead: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designVolumeFlowRate: NullableVolumeFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    differentialPressure: NullablePressureAbsolute | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class RadialFan(Fan):
    """A ‘fan’ with axial inlet and radial outlet (from http://data.posccaesar.org/rdl/RDS414089)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/radialFan.py"

    # Compositional attributes:
    impellers: list[Impeller] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )


class RailWaggon(MobileTransportSystem):
    """A non self driving vehicle and mobile transport system intended to ride on rails"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/railWaggon.py"


class ReciprocatingExtruder(Extruder):
    """An extruder that uses a piston in a batch process (from http://data.posccaesar.org/rdl/RDS412409911)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/reciprocatingExtruder.py"

    # Compositional attributes:
    displacers: list[Displacer] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )


class ReciprocatingPump(Pump):
    """A positive displacement pump which contains a displacing element intended to be moved in a reciprocating movement to exert pressure on a fluid, typically moving within a cylindrical space (from http://data.posccaesar.org/rdl/RDS416969)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/reciprocatingPump.py"

    # Compositional attributes:
    displacers: list[Displacer] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    designRotationalSpeed: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designShaftPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class RotaryMixer(Mixer):
    """A Mixer machine that mixes by means of rotating components."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/rotaryMixer.py"

    # Data attributes:
    designRotationalSpeed: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designShaftPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    upperLimitAllowableDesignPressureDrop: NullablePressureAbsolute | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class RotaryPump(Pump):
    """A positive displacement pump that consists of a chamber containing gears, cams, screws, vanes, plungers or similar elements actuated by relative rotation of the drive shaft or casing and which has no separate inlet and outlet valves (from http://data.posccaesar.org/rdl/RDS420749)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/rotaryPump.py"

    # Compositional attributes:
    displacers: list[Displacer] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    designRotationalSpeed: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designShaftPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class RotatingExtruder(Extruder):
    """An extruder that operates in a continuous process. Typically using a screw to build up pressure in the melt. It can incorporate a mixing stage with a forming stage (from http://data.posccaesar.org/rdl/RDS394045941)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/rotatingExtruder.py"

    # Compositional attributes:
    screws: list[Screw] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )


class Separator(Equipment):
    """A ‘device’ intended to separate different types of substances (from http://data.posccaesar.org/rdl/RDS2194378711)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/separator.py"

    # Data attributes:
    designVolumeFlowRate: NullableVolumeFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    efficiency: NullablePercentage | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    upperLimitAllowableDesignPressureDrop: NullablePressureAbsolute | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class Ship(MobileTransportSystem):
    """A watercraft and MobileTransportSystem that is a sea-going vessel of considerable size."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/ship.py"


class Sieve(Equipment):
    """A device that removes particles from a fluid when the fluid passes through or separates particles or molecules according to their size."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/sieve.py"

    # Compositional attributes:
    sieveElements: list[SieveElement] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    designMassFlowRate: NullableMassFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class SpiralHeatExchanger(HeatExchanger):
    """A HeatExchanger in which a pair of plates is formed into a spiral."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/spiralHeatExchanger.py"


class StaticMixer(Mixer):
    """A physical object that is intended to mix fluid by means of diverging the flow with static obstacles or by increasing locally the velocity."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/staticMixer.py"

    # Data attributes:
    upperLimitAllowableDesignPressureDrop: NullablePressureAbsolute | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class StationarySieve(Sieve):
    """A Sieve consisting of rakes or sieves, that, during operation, remains in a fixed position (from http://data.15926.org/rdl/RDS2226669)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/stationarySieve.py"


class StationaryTransportSystem(Equipment):
    """A transport system that is intended to transport, store or load/unload material and that, as a whole, remains in one place."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/stationaryTransportSystem.py"

    # Data attributes:
    designPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class SteamGenerator(Heater):
    """A boiler that is intended to generate steam (from http://data.posccaesar.org/rdl/RDS13306207)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/steamGenerator.py"


class TaggedColumnSection(ColumnSection, TaggedPlantItem):
    """A fully tagged column section."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/taggedColumnSection.py"


class ThinFilmEvaporator(HeatExchanger):
    """A HeatExchanger and evaporator for the purification of temperature-sensitive products by evaporation, where a thin film of the liquid product on the inner side of a vertical evaporation pipe is generated by a rotating wiper system."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/thinFilmEvaporator.py"

    # Compositional attributes:
    rotor: HeatExchangerRotor | None = Field(
        None, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    designPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designRotationalSpeed: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designShaftPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class TransportableContainer(MobileTransportSystem):
    """A ‘container’ that is a transportable, with strength suitable to withstand shipment, storage, and handling (from http://data.posccaesar.org/rdl/RDS22164402859)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/transportableContainer.py"


class Truck(MobileTransportSystem):
    """An automotive vehicle that is long, low and open intended for carrying goods by road (from http://data.posccaesar.org/rdl/RDS11524112)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/truck.py"


class TubularHeatExchanger(HeatExchanger):
    """An indirect contact heat exchanger that separates the hot and cold fluids by tubes (from http://data.posccaesar.org/rdl/RDS13971182)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/tubularHeatExchanger.py"

    # Compositional attributes:
    tubeBundle: TubeBundle | None = Field(
        None, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    temaStandardType: str | None = Field(None, json_schema_extra={"attribute_category": "data"})


class Turbine(Equipment):
    """An object that is a rotary mechanical device that extracts energy from a fluid flow and converts it into useful work (from http://data.15926.org/rdl/RDS313289)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/turbine.py"

    # Data attributes:
    designPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designRotationalFrequency: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class Vessel(Equipment):
    """A container intended for storage and/or processing of fluids or solids."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/vessel.py"

    # Data attributes:
    nominalCapacityVolume: NullableVolume | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )

    # Reference attributes:
    agitator: Agitator | None = Field(None, json_schema_extra={"attribute_category": "reference"})
    columnSections: list[TaggedColumnSection] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "reference"}
    )


class VibratingSieve(Sieve):
    """A Sieve where the product to be sieved is transported over the mesh by vibration of the latter (from http://data.15926.org/rdl/RDS2226670)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/vibratingSieve.py"

    # Data attributes:
    designPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class WasteGasEmitter(Equipment):
    """A physical object that is intended to release/emit waste gas from the process."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/wasteGasEmitter.py"

    # Data attributes:
    designVolumeFlowRate: NullableVolumeFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class Weigher(Equipment):
    """A functional object that is capable of weighing."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/weigher.py"

    # Data attributes:
    designMassFlowRate: NullableMassFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class BreatherValve(SafetyValveOrFitting):
    """A breather valve."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/breatherValve.py"


class CheckValve(PipingComponent):
    """A valve that permits fluid to flow in one direction only (from http://data.posccaesar.org/rdl/RDS292229)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/checkValve.py"

    # Data attributes:
    heatTracingType: HeatTracingTypeClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    heatTracingTypeRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    insulationThickness: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    insulationType: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    lowerLimitHeatTracingTemperature: NullableTemperature | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    pipingClassCode: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    pipingComponentName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    pipingComponentNumber: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class CustomCheckValve(CheckValve, CustomObject):
    """A custom CheckValve, i.e., a CheckValve that is not covered by any of the other subclasses of CheckValve (GlobeCheckValve or SwingCheckValve)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customCheckValve.py"


class CustomPipingComponent(CustomObject, PipingComponent):
    """A custom PipingComponent, i.e., a PipingComponent that is not covered by any of the other subclasses of PipingComponent (CheckValve, InlinePrimaryElement, OperatedValve, PipeFitting, or SafetyValveOrFitting)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customPipingComponent.py"

    # Data attributes:
    flowInPipingClassCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    flowOutPipingClassCode: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    heatTracingType: HeatTracingTypeClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    heatTracingTypeRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    insulationThickness: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    insulationType: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    locationRegistrationNumber: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    lowerLimitHeatTracingTemperature: NullableTemperature | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    numberOfPorts: NumberOfPortsClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    operation: OperationClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    pipingClassCode: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    pipingComponentName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    pipingComponentNumber: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    positionNumber: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    setPressureHigh: NullablePressureGauge | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    setPressureLow: NullablePressureGauge | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class CustomSafetyValveOrFitting(CustomObject, SafetyValveOrFitting):
    """A custom SafetyValveOrFitting, i.e., a SafetyValveOrFitting that is not covered by any of the other subclasses of SafetyValveOrFitting (BreatherValve, FlameArrestor, RuptureDisc, SpringLoadedAngleGlobeSafetyValve, or SpringLoadedGlobeSafetyValve)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customSafetyValveOrFitting.py"

    # Data attributes:
    detonationProofArtefact: DetonationProofArtefactClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    explosionProofArtefact: ExplosionProofArtefactClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    fireResistantArtefact: FireResistantArtefactClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class FlameArrestor(SafetyValveOrFitting):
    """An ‘arrestor’ which is a trap covering an opening, e.g of a ventilation system or a pipe, to prevent flames from entering the system (from http://data.posccaesar.org/rdl/RDS1325028651)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/flameArrestor.py"

    # Data attributes:
    detonationProofArtefact: DetonationProofArtefactClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    explosionProofArtefact: ExplosionProofArtefactClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    fireResistantArtefact: FireResistantArtefactClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class FlowInPipeOffPageConnector(PipeOffPageConnector, PipingSourceItem):
    """A pipe connector that indicates that a preceding part of a piping network segment is represented somewhere else, either on the same PID, or on some other PID."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/flowInPipeOffPageConnector.py"


class FlowOutPipeOffPageConnector(PipeOffPageConnector, PipingTargetItem):
    """A pipe connector that indicates that a subsequent part of a piping network segment is represented somewhere else, either on the same PID, or on some other PID."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/flowOutPipeOffPageConnector.py"


class GlobeCheckValve(CheckValve):
    """A globe chack valve."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/globeCheckValve.py"


class InlinePrimaryElement(PipingComponent):
    """An inline primary element."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/inlinePrimaryElement.py"

    # Data attributes:
    heatTracingType: HeatTracingTypeClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    heatTracingTypeRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    insulationThickness: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    insulationType: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    lowerLimitHeatTracingTemperature: NullableTemperature | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    pipingComponentName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    pipingComponentNumber: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class MassFlowMeasuringElement(InlinePrimaryElement):
    """A MASS FLOW MEASURING ELEMENT is a FLOW MEASURING ELEMENT that is used to measure MASS FLOW RATE."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/massFlowMeasuringElement.py"


class OperatedValve(PipingComponent):
    """A valve that includes an external means of operation. (E.g. handwheel / lever / actuator.) (from http://data.posccaesar.org/rdl/RDS11141590)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/operatedValve.py"

    # Data attributes:
    heatTracingType: HeatTracingTypeClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    heatTracingTypeRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    insulationThickness: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    insulationType: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    lowerLimitHeatTracingTemperature: NullableTemperature | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    numberOfPorts: NumberOfPortsClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    operation: OperationClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    pipingClassCode: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    pipingComponentName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    pipingComponentNumber: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class PipeFitting(PipingComponent):
    """A pipe fitting."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/pipeFitting.py"

    # Data attributes:
    heatTracingType: HeatTracingTypeClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    heatTracingTypeRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    insulationThickness: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    insulationType: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    lowerLimitHeatTracingTemperature: NullableTemperature | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    pipingClassCode: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    pipingComponentName: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    pipingComponentNumber: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class PipeFlangeSpacer(PipeFitting):
    """A ‘spacer’ and an ‘artefact’ that is intended to be inserted between two pipe flanged ends to provide the distance between the flanges required to insert a ‘pipe flange spade’ (from http://data.posccaesar.org/rdl/RDS472724)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/pipeFlangeSpacer.py"


class PipeFlangeSpade(PipeFitting):
    """A ‘line blind’ and an ‘artefact’ that is a circular plate with no central opening and holes to match mating flanged ends. It is also equipped with a handle (from http://data.posccaesar.org/rdl/RDS472679)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/pipeFlangeSpade.py"


class PipeOffPageConnectorObjectReference(PipeOffPageConnectorReference):
    """A reference to a PipeOffPageConnector by an association."""

    uri: ClassVar[str] = (
        "https://pyDEXPI.org/schemas/pydexpi_1_3/pipeOffPageConnectorObjectReference.py"
    )

    # Reference attributes:
    referencedConnector: PipeOffPageConnector | None = Field(
        None, json_schema_extra={"attribute_category": "reference"}
    )


class PipeReducer(PipeFitting):
    """An ‘artefact’ that has different nominal pipe size at the two ends, intended to connect pipes or piping components (from http://data.posccaesar.org/rdl/RDS416294)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/pipeReducer.py"


class PipeTee(PipeFitting):
    """An ‘artefact’ that has three piping ends in T-shape, including a branch at 90 degrees (from http://data.posccaesar.org/rdl/RDS427724)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/pipeTee.py"


class PlugValve(OperatedValve):
    """A rotary valve that has a quarter turn action in which the closure member is a cylindrical or tapered plug which operates by rotating on its axis and sealing against a downstream seat (from http://data.posccaesar.org/rdl/RDS421109)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/plugValve.py"


class PositiveDisplacementFlowMeter(InlinePrimaryElement):
    """A flow meter that measures the volumetric flow rate of a liquid or gas by separating the flow stream into known volumes and counting them over time (from http://data.posccaesar.org/rdl/RDS418094)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/positiveDisplacementFlowMeter.py"


class RestrictionOrifice(PipeFitting):
    """A RESTRICTION ORIFICE is an ORIFICE PLATE that is intended for use as a restrictor."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/restrictionOrifice.py"


class RuptureDisc(SafetyValveOrFitting):
    """A physical object that is designed to burst at a certain excess pressure. It is part of a rupture disc assembly (from http://data.posccaesar.org/rdl/RDS8372601)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/ruptureDisc.py"


class SightGlass(PipeFitting):
    """A physical object that is transparent and intended for viewing a vessel or piping system interior (from http://data.posccaesar.org/rdl/RDS648674)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/sightGlass.py"


class Silencer(PipeFitting):
    """A device intended to reduce a noise level (from http://data.posccaesar.org/rdl/RDS1049368591)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/silencer.py"


class SteamTrap(PipeFitting):
    """A trap that consists of a chamber into which condensed steam from steam pipes etc. is allowed to drain, and which automatically ejects it without permitting the escape of steam (from http://data.posccaesar.org/rdl/RDS5782388)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/steamTrap.py"


class StraightwayValve(OperatedValve):
    """A valve that is straight, i.e. the centerlines perpendicular to the ends are in-line with no offset (from http://data.posccaesar.org/rdl/RDS9390905)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/straightwayValve.py"


class Strainer(PipeFitting):
    """A mechanical separator that is separating solid particles from a fluid by passing the fluid through a wire mesh, screen or metal plates containing perforations or slits (from http://data.posccaesar.org/rdl/RDS422504)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/strainer.py"


class SwingCheckValve(CheckValve):
    """A check valve that is a check valve where the closure member is a disc which swings freely on a hinge and which opens automatically when flow is established and closes automatically when flow ceases or is reversed (from http://data.posccaesar.org/rdl/RDS610424)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/swingCheckValve.py"


class TurbineFlowMeter(InlinePrimaryElement):
    """A velocity flow meter that uses a multi bladed rotor to measure fluid flow rate in units of volumetric flow through a closed conduit (from http://data.posccaesar.org/rdl/RDS417914)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/turbineFlowMeter.py"


class VariableAreaFlowMeter(InlinePrimaryElement):
    """A flow meter consisting of a vertical tube with a conically shaped bore which widens to the top in which a solid body (float) is supported by the force exerted by the fluid stream (from http://data.posccaesar.org/rdl/RDS418229)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/variableAreaFlowMeter.py"


class VentilationDevice(PipeFitting):
    """A ‘device’ that allows gas or vapour to leave a container under excess pressure (from http://data.posccaesar.org/rdl/RDS1049335351)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/ventilationDevice.py"


class VenturiTube(InlinePrimaryElement):
    """A ‘measuring device’ that has a constriction with a relative long passage with a smooth coned entry and exit (from http://data.posccaesar.org/rdl/RDS648044)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/venturiTube.py"


class VolumeFlowMeasuringElement(InlinePrimaryElement):
    """A VOLUME FLOW MEASURING ELEMENT is a FLOW MEASURING ELEMENT that is used to measure VOLUME FLOW RATE."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/volumeFlowMeasuringElement.py"


class FlowDetector(ProcessSignalGeneratingSystem):
    """A detector that is intended to detect whether a fluid flow exists (from http://data.posccaesar.org/rdl/RDS1008719)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/flowDetector.py"


class FlowInSignalOffPageConnector(SignalConveyingFunctionSource, SignalOffPageConnector):
    """A signal connector that indicates that a preceding part of a signal conveying function is represented somewhere else, either on the same PID, or on some other PID."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/flowInSignalOffPageConnector.py"


class FlowOutSignalOffPageConnector(SignalConveyingFunctionTarget, SignalOffPageConnector):
    """A signal connector that indicates that a subsequent part of a signal conveying function is represented somewhere else, either on the same PID, or on some other PID."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/flowOutSignalOffPageConnector.py"


class InlinePrimaryElementReference(PrimaryElement):
    """A reference to an InlinePrimaryElement that is part of a PipingNetworkSegment."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/inlinePrimaryElementReference.py"

    # Reference attributes:
    inlinePrimaryElement: InlinePrimaryElement | None = Field(
        None, json_schema_extra={"attribute_category": "reference"}
    )


class MeasuringLineFunction(SignalConveyingFunction):
    """Information flow function for measured values."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/measuringLineFunction.py"


class OfflinePrimaryElement(PrimaryElement):
    """A PrimaryElement that is not part of a PipingNetworkSegment."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/offlinePrimaryElement.py"

    # Data attributes:
    connectionNominalDiameterNumericalValueRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    connectionNominalDiameterRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    connectionNominalDiameterStandard: NominalDiameterStandardClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    connectionNominalDiameterTypeRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    fluidCode: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    heatTracingType: HeatTracingTypeClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    heatTracingTypeRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    insulationThickness: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    insulationType: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    locationNominalDiameterNumericalValueRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    locationNominalDiameterRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    locationNominalDiameterStandard: NominalDiameterStandardClassification | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    locationNominalDiameterTypeRepresentation: str | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    lowerLimitHeatTracingTemperature: NullableTemperature | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class ProcessControlFunction(ProcessInstrumentationFunction):
    """A requirement for control structures relating to Process Engineering."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/processControlFunction.py"


class SignalOffPageConnectorObjectReference(SignalOffPageConnectorReference):
    """A reference to a SignalOffPageConnector by an association."""

    uri: ClassVar[str] = (
        "https://pyDEXPI.org/schemas/pydexpi_1_3/signalOffPageConnectorObjectReference.py"
    )

    # Reference attributes:
    referencedConnector: SignalOffPageConnector | None = Field(
        None, json_schema_extra={"attribute_category": "reference"}
    )


class ElectricalFrequency(NullableElectricalFrequency):
    """An actual value for a physical quantity of type NullableElectricalFrequency, i.e., a physical quantity that has a numerical value and a unit of measurement."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/electricalFrequency.py"

    # Data attributes:
    unit: ElectricalFrequencyUnit = Field(..., json_schema_extra={"attribute_category": "data"})
    value: float = Field(..., json_schema_extra={"attribute_category": "data"})


class NullElectricalFrequency(DexpiSingletonBaseModel, NullableElectricalFrequency):
    """A null value for a physical quantity of application type NullableElectricalFrequency. The only instance of this singleton type is NULL_ELECTRICAL_FREQUENCY."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/nullElectricalFrequency.py"


class ActuatingElectricalSystemNumberLabel(Label):
    """"""

    uri: ClassVar[str] = (
        "https://pyDEXPI.org/schemas/pydexpi_1_4/actuatingElectricalSystemNumberLabel.py"
    )


class ActuatingSystemNumberLabel(Label):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/actuatingSystemNumberLabel.py"


class CustomLabel(CustomObject, Label):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/customLabel.py"


class DeviceInformationLabel(Label):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/deviceInformationLabel.py"


class EquipmentBarLabel(Label):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/equipmentBarLabel.py"


class EquipmentTagNameLabel(Label):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/equipmentTagNameLabel.py"


class FailActionLabel(Label):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/failActionLabel.py"


class FittingLabel(Label):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/fittingLabel.py"


class InsulationBreakLabel(Label):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/insulationBreakLabel.py"


class InsulationLabel(Label):
    """"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_4/insulationLabel.py"


class Agglomerator(Equipment):
    """A machine that is capable of agglomerating. It is usually vertically aligned."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/agglomerator.py"

    # Data attributes:
    designLiquidFeedMassFlowRate: NullableMassFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designMassFlowRate: NullableMassFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designRotationalSpeed: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designShaftPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designSolidFeedMassFlowRate: NullableMassFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designVolumeFlowRate: NullableVolumeFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class Agitator(Equipment):
    """An Agitator is a dynamic mixer that stirs or shakes fluids by reaction force from moving vanes."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/agitator.py"

    # Compositional attributes:
    rotor: AgitatorRotor | None = Field(
        None, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    designRotationalSpeed: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designShaftPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class AirCoolingSystem(HeatExchanger):
    """A cooling system which uses air as the cooling medium (from http://data.posccaesar.org/rdl/RDS277379)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/airCoolingSystem.py"

    # Compositional attributes:
    rotor: HeatExchangerRotor | None = Field(
        None, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    designPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designRotationalSpeed: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designShaftPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class AlternatingCurrentMotor(Motor):
    """An electric motor driven by alternating electric current (from http://data.posccaesar.org/rdl/RDS472994)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/alternatingCurrentMotor.py"

    # Data attributes:
    alternatingCurrentFrequency: NullableElectricalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    nominalVoltage: NullableVoltage | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class AxialFan(Fan):
    """A fan where the flow is along axis of shaft and the pressure ratio is relatively low (from http://data.posccaesar.org/rdl/RDS414044)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/axialFan.py"

    # Compositional attributes:
    impellers: list[Impeller] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )


class BatchWeigher(Weigher):
    """A Weigher that is operating in batch mode."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/batchWeigher.py"

    # Data attributes:
    designCapacityWeighingQuantities: NullableNumberPerTimeInterval | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    upperLimitDesignLoad: NullableMass | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class Blower(Equipment):
    """A machine that is capable of blowing a medium volume flow."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/blower.py"

    # Data attributes:
    designDifferentialPressure: NullablePressureAbsolute | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designRotationalSpeed: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designShaftPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designVolumeFlowRate: NullableVolumeFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class Boiler(Heater):
    """A Heater that brings a liquid to its boiling point."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/boiler.py"


class Burner(Equipment):
    """A physical object that is intended to release thermal energy by burning a combustible mixture (from http://data.posccaesar.org/rdl/RDS284399)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/burner.py"

    # Data attributes:
    designPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class CentrifugalBlower(Blower):
    """A blower in which one ore more impellers accelerate the flow and where the main flow through the impeller is radial."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/centrifugalBlower.py"

    # Compositional attributes:
    impellers: list[Impeller] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )


class CentrifugalPump(Pump):
    """A dynamic pump utilizing impellers provided with vanes generating centrifugal force to achieve the required pressure head (from http://data.posccaesar.org/rdl/RDS416834)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/centrifugalPump.py"

    # Compositional attributes:
    impellers: list[Impeller] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    designRotationalSpeed: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designShaftPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class Centrifuge(Equipment):
    """A ‘separator’ and ‘machine’ that uses centrifugal force to separate phases of different densities (from http://data.posccaesar.org/rdl/RDS420974)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/centrifuge.py"

    # Data attributes:
    designRotationalSpeed: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designShaftPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designVolumeFlowRate: NullableVolumeFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class Chimney(WasteGasEmitter):
    """A WasteGasEmitter that is intended to transport waste gas to a high location in the atmosphere."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/chimney.py"


class CombustionEngine(Motor):
    """An engine intended to deliver power by means of burning fuels (from http://data.posccaesar.org/rdl/RDS1083734)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/combustionEngine.py"

    # Data attributes:
    fuelType: str | None = Field(None, json_schema_extra={"attribute_category": "data"})


class Compressor(Equipment):
    """A machine that has the capability of compressing a gas."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/compressor.py"

    # Data attributes:
    designVolumeFlowRate: NullableVolumeFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    differentialPressure: NullablePressureAbsolute | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class ContinuousWeigher(Weigher):
    """A Weigher that weighs a mass flow rate in continuous mode."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/continuousWeigher.py"

    # Data attributes:
    beltWidth: NullableLength | None = Field(None, json_schema_extra={"attribute_category": "data"})


class Conveyor(StationaryTransportSystem):
    """A machine that is capable of conveying material."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/conveyor.py"

    # Data attributes:
    conveyingDistance: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    conveyorType: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    designCapacityMassFlowRate: NullableMassFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designRotationalSpeed: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class CoolingTower(Equipment):
    """A cooler and an air cooled heat exchanger that is a tall structure through which air circulates by convection (from http://data.posccaesar.org/rdl/RDS14072341)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/coolingTower.py"

    # Data attributes:
    designHeatFlowRate: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designVolumeFlowRate: NullableVolumeFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class Crusher(Mill):
    """A mill that uses pressure or impact to reduce the particle size of solid materials (from http://data.posccaesar.org/rdl/RDS11589940)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/crusher.py"

    # Compositional attributes:
    crusherElements: list[CrusherElement] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )


class CustomAgglomerator(Agglomerator, CustomObject):
    """A custom Agglomerator, i.e., an Agglomerator that is not covered by any of the other subclasses of Agglomerator (ReciprocatingPressureAgglomerator, RotatingGrowthAgglomerator, or RotatingPressureAgglomerator)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customAgglomerator.py"

    # Compositional attributes:
    briquettingRollers: list[BriquettingRoller] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )
    displacers: list[Displacer] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )
    pelletizerDisc: PelletizerDisc | None = Field(
        None, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    lowerLimitDesignPressingForce: NullableForce | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    upperLimitDesignPressingForce: NullableForce | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class CustomBlower(Blower, CustomObject):
    """A custom Blower, i.e., a Blower that is not covered by any of the other subclasses of Blower (AxialBlower or CentrifugalBlower)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customBlower.py"

    # Compositional attributes:
    impellers: list[Impeller] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )


class CustomCentrifuge(Centrifuge, CustomObject):
    """A custom Centrifuge, i.e., a Centrifuge that is not covered by any of the other subclasses of Centrifuge (FilteringCentrifuge or SedimentalCentrifuge)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customCentrifuge.py"

    # Compositional attributes:
    filteringCentrifugeDrum: FilteringCentrifugeDrum | None = Field(
        None, json_schema_extra={"attribute_category": "composition"}
    )
    sedimentalCentrifugeDrum: SedimentalCentrifugeDrum | None = Field(
        None, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    efficiency: NullablePercentage | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    minimumParticleSize: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class CustomCompressor(Compressor, CustomObject):
    """A custom Compressor, i.e., a Compressor that is not covered by any of the other subclasses of Compressor (AirEjector, AxialCompressor, CentrifugalCompressor, ReciprocatingCompressor, or RotaryCompressor)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customCompressor.py"

    # Compositional attributes:
    displacers: list[Displacer] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )
    impellers: list[Impeller] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    designCapacityMotiveFluid: NullableVolumeFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designRotationalSpeed: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designShaftPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class CustomCoolingTower(CoolingTower, CustomObject):
    """A custom CoolingTower, i.e., a CoolingTower that is not covered by any of the other subclasses of CoolingTower (DryCoolingTower, SprayCooler, or WetCoolingTower)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customCoolingTower.py"

    # Compositional attributes:
    coolingTowerRotor: CoolingTowerRotor | None = Field(
        None, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    designRotationalSpeed: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designShaftPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designSprayFlowRate: NullableVolumeFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class CustomEquipment(CustomObject, Equipment):
    """A custom Equipment, i.e., an Equipment that is not covered by any of the other subclasses of Equipment."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customEquipment.py"


class CustomExtruder(CustomObject, Extruder):
    """A custom Extruder, i.e., an Extruder that is not covered by any of the other subclasses of Extruder (ReciprocatingExtruder or RotatingExtruder)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customExtruder.py"

    # Compositional attributes:
    displacers: list[Displacer] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )
    screws: list[Screw] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )


class CustomFan(CustomObject, Fan):
    """A custom Fan, i.e., a Fan that is not covered by any of the other subclasses of Fan (AxialFan or RadialFan)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customFan.py"

    # Compositional attributes:
    impellers: list[Impeller] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )


class CustomFilter(CustomObject, Filter):
    """A custom Filter, i.e., a Filter that is not covered by any of the other subclasses of Filter (GasFilter or LiquidFilter)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customFilter.py"

    # Compositional attributes:
    filterUnit: FilterUnit | None = Field(
        None, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    designCapacityVolumeFlowRate: NullableVolumeFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designRotationalSpeed: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designShaftPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    upperLimitAllowableDesignPressureDrop: NullablePressureAbsolute | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class CustomHeatExchanger(CustomObject, HeatExchanger):
    """A custom HeatExchanger, i.e., a HeatExchanger that is not covered by any of the other subclasses of HeatExchanger (AirCoolingSystem, ElectricHeater, PlateHeatExchanger, SpiralHeatExchanger, ThinFilmEvaporator, or TubularHeatExchanger)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customHeatExchanger.py"

    # Compositional attributes:
    rotor: HeatExchangerRotor | None = Field(
        None, json_schema_extra={"attribute_category": "composition"}
    )
    tubeBundle: TubeBundle | None = Field(
        None, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    designPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designRotationalSpeed: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designShaftPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    numberOfPlates: int | None = Field(None, json_schema_extra={"attribute_category": "data"})
    plateHeight: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    plateWidth: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    temaStandardType: str | None = Field(None, json_schema_extra={"attribute_category": "data"})


class CustomHeater(CustomObject, Heater):
    """A custom Heater, i.e., a Heater that is not covered by any of the other subclasses of Heater (Boiler, Furnace, or SteamGenerator)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customHeater.py"


class CustomMill(CustomObject, Mill):
    """A custom Mill, i.e., a Mill that is not covered by any of the other subclasses of Mill (Crusher or Grinder)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customMill.py"

    # Compositional attributes:
    crusherElements: list[CrusherElement] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )
    grindingElements: list[GrindingElement] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )


class CustomMixer(CustomObject, Mixer):
    """A custom Mixer, i.e., a Mixer that is not covered by any of the other subclasses of Mixer (Kneader, RotaryMixer, or StaticMixer)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customMixer.py"

    # Data attributes:
    designRotationalSpeed: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designShaftPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    upperLimitAllowableDesignPressureDrop: NullablePressureAbsolute | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class CustomMobileTransportSystem(CustomObject, MobileTransportSystem):
    """A custom MobileTransportSystem, i.e., a MobileTransportSystem that is not covered by any of the other subclasses of MobileTransportSystem (ForkliftTruck, RailWaggon, Ship, TransportableContainer, or Truck)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customMobileTransportSystem.py"

    # Data attributes:
    upperLimitDischargeHead: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class CustomMotor(CustomObject, Motor):
    """A custom Motor, i.e., a Motor that is not covered by any of the other subclasses of Motor (AlternatingCurrentMotor, CombustionEngine, or DirectCurrentMotor)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customMotor.py"

    # Data attributes:
    alternatingCurrentFrequency: NullableElectricalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    fuelType: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    nominalVoltage: NullableVoltage | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class CustomPump(CustomObject, Pump):
    """A custom Pump, i.e., a Pump that is not covered by any of the other subclasses of Pump (CentrifugalPump, EjectorPump, ReciprocatingPump, or RotaryPump)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customPump.py"

    # Compositional attributes:
    displacers: list[Displacer] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )
    impellers: list[Impeller] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    designCapacityMotiveFluid: NullableVolumeFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designRotationalSpeed: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designShaftPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class CustomSeparator(CustomObject, Separator):
    """A custom Separator, i.e., a Separator that is not covered by any of the other subclasses of Separator (ElectricalSeparator, GravitationalSeparator, MechanicalSeparator, or ScrubbingSeparator)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customSeparator.py"

    # Data attributes:
    designPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designRotationalSpeed: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class CustomSieve(CustomObject, Sieve):
    """A custom Sieve, i.e., a Sieve that is not covered by any of the other subclasses of Sieve (RevolvingSieve, StationarySieve, or VibratingSieve)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customSieve.py"

    # Data attributes:
    designPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designRotationalFrequency: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designShaftPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class CustomStationaryTransportSystem(CustomObject, StationaryTransportSystem):
    """A custom StationaryTransportSystem, i.e., a StationaryTransportSystem that is not covered by any of the other subclasses of StationaryTransportSystem (Conveyor, Lift, or LoadingUnloadingSystem)."""

    uri: ClassVar[str] = (
        "https://pyDEXPI.org/schemas/pydexpi_1_3/customStationaryTransportSystem.py"
    )

    # Data attributes:
    conveyingDistance: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    conveyorType: str | None = Field(None, json_schema_extra={"attribute_category": "data"})
    designCapacityMassFlowRate: NullableMassFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designRotationalSpeed: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    dischargeHead: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    upperLimitConveyingDistance: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    upperLimitDischargeHead: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    upperLimitLoadCapacity: NullableMass | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    upperLimitVolumeCapacity: NullableVolume | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class CustomTurbine(CustomObject, Turbine):
    """A custom Turbine, i.e., a Turbine that is not covered by any of the other subclasses of Turbine (GasTurbine or SteamTurbine)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customTurbine.py"

    # Data attributes:
    designInletMassFlow: NullableMassFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designInletVolumeFlow: NullableVolumeFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    fuelType: str | None = Field(None, json_schema_extra={"attribute_category": "data"})


class CustomVessel(CustomObject, Vessel):
    """A custom Vessel, i.e., a Vessel that is not covered by any of the other subclasses of Vessel (PressureVessel, Silo, or Tank)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customVessel.py"

    # Data attributes:
    cylinderLength: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class CustomWasteGasEmitter(CustomObject, WasteGasEmitter):
    """A custom WasteGasEmitter, i.e., a WasteGasEmitter that is not covered by any of the other subclasses of WasteGasEmitter (Chimney or Flare)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customWasteGasEmitter.py"


class CustomWeigher(CustomObject, Weigher):
    """A custom Weigher, i.e., a Weigher that is not covered by any of the other subclasses of Weigher (BatchWeigher or ContinuousWeigher)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customWeigher.py"

    # Data attributes:
    beltWidth: NullableLength | None = Field(None, json_schema_extra={"attribute_category": "data"})
    designCapacityWeighingQuantities: NullableNumberPerTimeInterval | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    upperLimitDesignLoad: NullableMass | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class DirectCurrentMotor(Motor):
    """An electric motor for operation by direct current (from http://data.posccaesar.org/rdl/RDS472949)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/directCurrentMotor.py"

    # Data attributes:
    nominalVoltage: NullableVoltage | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class DryCoolingTower(CoolingTower):
    """A CoolingTower that is an indirect contact heat exchanger where, by full utilization of dry surface coil sections, no direct contact (and no evaporation) occurs between air and water; hence the water is cooled totally by sensible heat transfer (from http://data.15926.org/rdl/RDS14072386)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/dryCoolingTower.py"

    # Compositional attributes:
    coolingTowerRotor: CoolingTowerRotor | None = Field(
        None, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    designRotationalSpeed: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designShaftPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class Dryer(Equipment):
    """An object that has the capability of drying (from http://data.15926.org/rdl/RDS1066939451)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/dryer.py"

    # Data attributes:
    designMassFlowRate: NullableMassFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designRotationalSpeed: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designShaftPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designVolumeFlowRate: NullableVolumeFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class EjectorPump(Pump):
    """A pump which uses pressurized gas or liquid passing through an ejector to transport liquid (from http://data.posccaesar.org/rdl/RDS860624)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/ejectorPump.py"

    # Data attributes:
    designCapacityMotiveFluid: NullableVolumeFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class ElectricGenerator(Equipment):
    """An electric rotating machine that transforms non-electric energy into electric energy (from http://data.posccaesar.org/rdl/RDS415709)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/electricGenerator.py"

    # Data attributes:
    designInletPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designInletRotationalFrequency: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designOutletPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designOutletVoltage: NullableVoltage | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class ElectricHeater(HeatExchanger):
    """A heater in which electric energy is converted into heat for useful purposes (from http://data.posccaesar.org/rdl/RDS14070475)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/electricHeater.py"

    # Compositional attributes:
    tubeBundle: TubeBundle | None = Field(
        None, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    designPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class ElectricalSeparator(Separator):
    """A separator that uses electromagnetic, magnetic or electrostatic forces to separate phases."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/electricalSeparator.py"

    # Data attributes:
    designPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class FilteringCentrifuge(Centrifuge):
    """A centrifuge intended to separate solids from liquids by centrifugal process based on particle size."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/filteringCentrifuge.py"

    # Compositional attributes:
    filteringCentrifugeDrum: FilteringCentrifugeDrum | None = Field(
        None, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    minimumParticleSize: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class Flare(WasteGasEmitter):
    """An artefact and waste gas emitter that is intended to burn waste gas in secure distance from the plant or platform."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/flare.py"


class ForkliftTruck(MobileTransportSystem):
    """A MobileTransportSystem and vehicle with power operated prongs that can be raised and lowered by will, for loading, transporting and unloading goods (from http://data.15926.org/rdl/RDS11590075)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/forkliftTruck.py"

    # Data attributes:
    upperLimitDischargeHead: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class Furnace(Heater):
    """A physical object that is intended to induce a reaction in a process fluid by heating it (from http://data.posccaesar.org/rdl/RDS441134)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/furnace.py"


class GasTurbine(Turbine):
    """A machine that is a rotary mechanical device extracting energy from a gas flow and converting it into useful work."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/gasTurbine.py"

    # Data attributes:
    fuelType: str | None = Field(None, json_schema_extra={"attribute_category": "data"})


class GravitationalSeparator(Separator):
    """A fluid separator that is based on the difference in specific gravity for the substances to be separated (from http://data.15926.org/rdl/RDS16042131)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/gravitationalSeparator.py"

    # Data attributes:
    designPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designRotationalSpeed: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class Grinder(Mill):
    """A Mill that has the capability of grinding,"""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/grinder.py"

    # Compositional attributes:
    grindingElements: list[GrindingElement] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )


class HeatedSurfaceDryer(Dryer):
    """A Dryer that dries a material by radiation and/or conduction caused by a heated surface (from http://data.15926.org/rdl/RDS2228449)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/heatedSurfaceDryer.py"

    # Data attributes:
    heatedSurfaceArea: NullableArea | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class Kneader(Mixer):
    """A machine that is capable of mixing and working into a uniform mass by, or as if by, folding, pressing, and stretching."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/kneader.py"

    # Data attributes:
    designRotationalSpeed: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designShaftPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    upperLimitAllowableDesignPressureDrop: NullablePressureAbsolute | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class Lift(StationaryTransportSystem):
    """A StationaryTransportSystem for transporting persons or things from one level to another (from http://data.posccaesar.org/rdl/RDS13601120)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/lift.py"

    # Data attributes:
    dischargeHead: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    upperLimitLoadCapacity: NullableMass | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    upperLimitVolumeCapacity: NullableVolume | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class LoadingUnloadingSystem(StationaryTransportSystem):
    """A transport system that is intended for loading and/or unloading products into/from vehicles, wagons or vessels (from http://data.posccaesar.org/rdl/RDS11525012)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/loadingUnloadingSystem.py"

    # Data attributes:
    upperLimitConveyingDistance: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    upperLimitDischargeHead: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    upperLimitLoadCapacity: NullableMass | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class MechanicalSeparator(Separator):
    """A fluid separator in which mechanical separation of fluids take place (from http://data.posccaesar.org/rdl/RDS279134)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/mechanicalSeparator.py"

    # Data attributes:
    designPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class PressureVessel(Vessel):
    """A vessel intended to withstand external and/or internal pressure (from http://data.posccaesar.org/rdl/RDS427229)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/pressureVessel.py"

    # Data attributes:
    cylinderLength: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class ReciprocatingCompressor(Compressor):
    """A positive displacement compressor in which forced reduction of gas volume takes place by the movement of a displacing element in a cylinder or enclosure (from http://data.posccaesar.org/rdl/RDS417284)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/reciprocatingCompressor.py"

    # Compositional attributes:
    displacers: list[Displacer] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    designRotationalSpeed: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designShaftPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class ReciprocatingPressureAgglomerator(Agglomerator):
    """An Agglomerator which uses pistons to produce pressure and to form material (from http://data.15926.org/rdl/RDS2228720)."""

    uri: ClassVar[str] = (
        "https://pyDEXPI.org/schemas/pydexpi_1_3/reciprocatingPressureAgglomerator.py"
    )

    # Compositional attributes:
    displacers: list[Displacer] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    lowerLimitDesignPressingForce: NullableForce | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    upperLimitDesignPressingForce: NullableForce | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class RevolvingSieve(Sieve):
    """A revolving sieve that intends to sift out finer from coarser parts."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/revolvingSieve.py"

    # Data attributes:
    designRotationalFrequency: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designShaftPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class RotaryCompressor(Compressor):
    """A positive displacement compressor in which compression displacement is effected by the positive action of rotating elements (from http://data.posccaesar.org/rdl/RDS435374)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/rotaryCompressor.py"

    # Compositional attributes:
    displacers: list[Displacer] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    designRotationalSpeed: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designShaftPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class RotatingGrowthAgglomerator(Agglomerator):
    """An agglomerator which uses a pelletizer disc to produce pellets."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/rotatingGrowthAgglomerator.py"

    # Compositional attributes:
    pelletizerDisc: PelletizerDisc | None = Field(
        None, json_schema_extra={"attribute_category": "composition"}
    )


class RotatingPressureAgglomerator(Agglomerator):
    """An agglomerator which uses briquetting rollers to produce pressure and to form material."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/rotatingPressureAgglomerator.py"

    # Compositional attributes:
    briquettingRollers: list[BriquettingRoller] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    lowerLimitDesignPressingForce: NullableForce | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    upperLimitDesignPressingForce: NullableForce | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class ScrubbingSeparator(Separator):
    """A separator that is intended to clean gas by washing the gas flow with water or with another liquid entering at the top of the vessel."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/scrubbingSeparator.py"


class SedimentalCentrifuge(Centrifuge):
    """A centrifuge that is intended to separate solids from liquids by a centrifugal process based on different densities."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/sedimentalCentrifuge.py"

    # Compositional attributes:
    sedimentalCentrifugeDrum: SedimentalCentrifugeDrum | None = Field(
        None, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    efficiency: NullablePercentage | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class Silo(Vessel):
    """A Vessel with a conical shape that is intended to store solids in bulk (from http://data.15926.org/rdl/RDS1022399)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/silo.py"


class SprayCooler(CoolingTower):
    """A CoolingTower that is based on spraying a coolant on a heated surface to be cooled."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/sprayCooler.py"

    # Data attributes:
    designSprayFlowRate: NullableVolumeFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class SteamTurbine(Turbine):
    """A turbine that is a heat engine in which energy of steam is transformed into kinetic energy by means of expansion through nozzles and the kinetic energy of the resulting jet is in turn converted into force doing work on rings of blading mounted on a rotating shaft (from http://data.posccaesar.org/rdl/RDS416744)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/steamTurbine.py"

    # Data attributes:
    designInletMassFlow: NullableMassFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designInletVolumeFlow: NullableVolumeFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class Tank(Vessel):
    """A vessel intended to contain fluid for storage. Typically a receiving or collecting function for further distribution. Typically with a vertical and cylindrical or square shape and a flat or conical bottom (from http://data.posccaesar.org/rdl/RDS445139)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/tank.py"

    # Data attributes:
    cylinderLength: NullableLength | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class WetCoolingTower(CoolingTower):
    """A CoolingTower that derives its primary cooling effect from the evaporation that takes place when air and water are brought into direct contact."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/wetCoolingTower.py"

    # Compositional attributes:
    coolingTowerRotor: CoolingTowerRotor | None = Field(
        None, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    designRotationalSpeed: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designShaftPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designSprayFlowRate: NullableVolumeFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class AngleBallValve(OperatedValve):
    """A valve that has valve ports which are not in-line and that has a ball closure member."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/angleBallValve.py"


class AngleGlobeValve(OperatedValve):
    """A globe valve that deviates from the in-line design, i.e. with a body shape designed to adjust the flow direction with a specified angle relative to the straight through-flow an in-line valve would have provided for (from http://data.posccaesar.org/rdl/RDS882944)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/angleGlobeValve.py"


class AnglePlugValve(OperatedValve):
    """A valve that has valve ports which are not in-line and that has a quarter turn action in which the closure member is a cylindrical or tapered plug which operates by rotating on its axis and sealing against a downstream seat."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/anglePlugValve.py"


class AngleValve(OperatedValve):
    """A valve that has valve ports which are not in-line (from http://data.posccaesar.org/rdl/RDS5789384)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/angleValve.py"


class BallValve(OperatedValve):
    """A rotary valve that has a ball closure member (from http://data.posccaesar.org/rdl/RDS416654)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/ballValve.py"


class BlindFlange(PipeFitting):
    """A pipe flange that is without a central opening and used to shut off a flanged pipe end (from http://data.posccaesar.org/rdl/RDS414719)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/blindFlange.py"


class ButterflyValve(OperatedValve):
    """A rotary valve that has a closure member of a disc type with a shaft parallel, or near parallel, to the plane of the disc, with an axis of rotation transverse to the flow direction (from http://data.posccaesar.org/rdl/RDS416609)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/butterflyValve.py"


class ClampedFlangeCoupling(PipeFitting):
    """A clamped flange coupling."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/clampedFlangeCoupling.py"


class Compensator(PipeFitting):
    """A device compensating for axial or radial movement between two elements that is connected (from http://data.posccaesar.org/rdl/RDS1280084541)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/compensator.py"


class ConicalStrainer(PipeFitting):
    """A strainer where the screen has a conical tubular shape (from http://data.posccaesar.org/rdl/RDS16044540)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/conicalStrainer.py"


class CustomInlinePrimaryElement(CustomObject, InlinePrimaryElement):
    """A custom InlinePrimaryElement, i.e., an InlinePrimaryElement that is not covered by any of the other subclasses of InlinePrimaryElement."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customInlinePrimaryElement.py"


class CustomOperatedValve(CustomObject, OperatedValve):
    """A custom OperatedValve, i.e., an OperatedValve that is not covered by any of the other subclasses of OperatedValve."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customOperatedValve.py"


class CustomPipeFitting(CustomObject, PipeFitting):
    """A custom PipeFitting, i.e., a PipeFitting that is not covered by any of the other subclasses of PipeFitting."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customPipeFitting.py"


class ElectromagneticFlowMeter(InlinePrimaryElement):
    """A velocity flow meter that is measuring flow rate of a conductive fluid running through a magnetic field by measuring the charge created when fluid interacting with the field (from http://data.posccaesar.org/rdl/RDS1009664)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/electromagneticFlowMeter.py"


class Flange(PipeFitting):
    """A physical object that is a projecting flat rim, plate,collar, or rib (from http://data.posccaesar.org/rdl/RDS13307654)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/flange.py"


class FlangedConnection(PipeFitting):
    """A flanged connection."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/flangedConnection.py"


class FlowMeasuringElement(InlinePrimaryElement):
    """A FLOW MEASURING ELEMENT is a MEASURING ELEMENT that is used to measure FLOW RATE."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/flowMeasuringElement.py"


class FlowNozzle(InlinePrimaryElement):
    """A nozzle with a smooth entry and a sharp exit (from http://data.posccaesar.org/rdl/RDS821024)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/flowNozzle.py"


class Funnel(PipeFitting):
    """A hollow cone with a tube extending from the smaller end and that is designed to catch and direct a downward flow (from http://data.posccaesar.org/rdl/RDS6689917)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/funnel.py"


class GateValve(OperatedValve):
    """A valve that is a valve where the closure member is a gate or disc with a linear motion parallel, or nearly parallel, to the plane of flat seats, which are transverse to the direction of flow (from http://data.posccaesar.org/rdl/RDS416519)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/gateValve.py"


class GlobeValve(OperatedValve):
    """A valve that is a valve where the closure member is a disc or piston operating with linear motion normal to the flat or shaped seat (from http://data.posccaesar.org/rdl/RDS416204)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/globeValve.py"


class Hose(PipeFitting):
    """A tubular which is flexible and capable of conveying liquids under pressure (from http://data.posccaesar.org/rdl/RDS302174)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/hose.py"


class IlluminatedSightGlass(PipeFitting):
    """An illuminated sight glass."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/illuminatedSightGlass.py"


class InLineMixer(PipeFitting):
    """A static mixer that is intended to be supported by connected equipment. Typically supported by piping (from http://data.posccaesar.org/rdl/RDS43167562195)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/inLineMixer.py"


class LineBlind(PipeFitting):
    """A functional unit used to blind off a process stream (from http://data.posccaesar.org/rdl/RDS280034)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/lineBlind.py"


class NeedleValve(OperatedValve):
    """A globe valve that has a closure member with the shape of a conical plug (needle) which closes into a small seat (from http://data.posccaesar.org/rdl/RDS421064)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/needleValve.py"


class Penetration(PipeFitting):
    """A device intended to provide a penetration (from http://data.posccaesar.org/rdl/RDS13068275)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/penetration.py"


class PipeCoupling(PipeFitting):
    """An ‘artefact’ that is a one-piece cylindrical section intended to join pipes and/or piping components (from http://data.posccaesar.org/rdl/RDS415664)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/pipeCoupling.py"


class AirEjector(Compressor):
    """An ejector intended to create vacuum using compressed air (from http://data.posccaesar.org/rdl/RDS5770157)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/airEjector.py"

    # Compositional attributes:
    impellers: list[Impeller] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    designCapacityMotiveFluid: NullableVolumeFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class AlternatingCurrentGenerator(ElectricGenerator):
    """An electric generator for the production of alternating current and voltage (from http://data.posccaesar.org/rdl/RDS873359)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/alternatingCurrentGenerator.py"

    # Data attributes:
    alternatingCurrentFrequency: NullableElectricalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class AxialBlower(Blower):
    """A blower in which the flow direction is parallel to the shaft (from http://data.posccaesar.org/rdl/RDS433259)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/axialBlower.py"

    # Compositional attributes:
    impellers: list[Impeller] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )


class AxialCompressor(Compressor):
    """A Compressor in which the gas is accelerated by the action of a bladed rotor and where the main flow is along the rotation axis of the rotor."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/axialCompressor.py"

    # Compositional attributes:
    impellers: list[Impeller] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    designRotationalSpeed: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designShaftPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class CentrifugalCompressor(Compressor):
    """A dynamic compressor in which one ore more impellers accelerate the gas and where the main flow through the impeller is radial (from http://data.posccaesar.org/rdl/RDS417194)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/centrifugalCompressor.py"

    # Compositional attributes:
    impellers: list[Impeller] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    designRotationalSpeed: NullableRotationalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    designShaftPower: NullablePower | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class ConvectionDryer(Dryer):
    """A Dryer that dries a material by bringing it in contact with a drying gas."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/convectionDryer.py"

    # Data attributes:
    airConsumption: NullableVolumeFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class CustomDryer(CustomObject, Dryer):
    """A custom Dryer, i.e., a Dryer that is not covered by any of the other subclasses of Dryer (ConvectionDryer or HeatedSurfaceDryer)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customDryer.py"

    # Data attributes:
    airConsumption: NullableVolumeFlowRate | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )
    heatedSurfaceArea: NullableArea | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class CustomElectricGenerator(CustomObject, ElectricGenerator):
    """A custom ElectricGenerator, i.e., an ElectricGenerator that is not covered by any of the other subclasses of ElectricGenerator (AlternatingCurrentGenerator or DirectCurrentGenerator)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/customElectricGenerator.py"

    # Data attributes:
    alternatingCurrentFrequency: NullableElectricalFrequency | None = Field(
        None, json_schema_extra={"attribute_category": "data"}
    )


class DirectCurrentGenerator(ElectricGenerator):
    """An ElectricGenerator and current generator for the production of direct current (DC)."""

    uri: ClassVar[str] = "https://pyDEXPI.org/schemas/pydexpi_1_3/directCurrentGenerator.py"
