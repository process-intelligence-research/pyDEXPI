"""Tests for the equipment_toolkit module."""

from pydexpi.toolkits import equipment_toolkit as et


def test_get_equipment_internal_classes() -> None:
    """Test that equipment internals are returned as class types."""
    expected_internal_names = [
        "AgitatorRotor",
        "BriquettingRoller",
        "Chamber",
        "ColumnInternalsArrangement",
        "ColumnPackingsArrangement",
        "ColumnSection",
        "ColumnTraysArrangement",
        "CoolingTowerRotor",
        "CrusherElement",
        "Displacer",
        "DryingChamber",
        "FilterUnit",
        "FilteringCentrifugeDrum",
        "GearBox",
        "GrindingElement",
        "HeatExchangerRotor",
        "Impeller",
        "MixingElementAssembly",
        "MotorAsComponent",
        "PelletizerDisc",
        "Screw",
        "SedimentalCentrifugeDrum",
        "SieveElement",
        "SprayNozzle",
        "SubTaggedColumnSection",
        "TubeBundle",
    ]

    result = et.get_equipment_internal_classes()

    assert isinstance(result, list)
    assert all(isinstance(class_type, type) for class_type in result)
    assert [class_type.__name__ for class_type in result] == expected_internal_names
