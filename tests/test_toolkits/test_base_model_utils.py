"""This test module contains tests for the base_model_utils module"""

from enum import Enum

import pytest
from pydantic import BaseModel, Field

from pydexpi.dexpi_classes.dexpiBaseModels import DexpiBaseModel
from pydexpi.dexpi_classes.pydantic_classes import (
    ActuatingElectricalLocation,
    ActuatingSystem,
    Equipment,
    PipingNetworkSegment,
    SensingLocation,
)
from pydexpi.toolkits import base_model_utils as bmt


# Abstract mock classes for testing purposes
class AbstractMockItem(DexpiBaseModel):
    """Abstract mock item for testing attribute categorization.

    This class provides a minimal structure for testing DEXPI base model
    utilities without the complexity of real DEXPI classes.

    Attributes
    ----------
    uri : str
        The URI identifier for this mock item.
    """

    uri: str = "https://pyDEXPI.org/schemas/abstract/mockItem.py"


class AbstractMockTestModel(DexpiBaseModel):
    """Abstract mock model for testing base_model_utils functions.

    This class contains various types of attributes (composition, data, and reference)
    to test the attribute categorization functionality in the base_model_utils module.

    Attributes
    ----------
    uri : str
        The URI identifier for this mock model.
    items : list[AbstractMockItem]
        Compositional attribute containing a list of mock items.
    required_field1 : str
        Required data attribute for testing.
    required_field2 : AbstractMockItem
        Required reference attribute for testing.
    required_field3 : int
        Required field without category specification.
    optional_field1 : float | None
        Optional data attribute for testing.
    optional_field2 : AbstractMockItem | None
        Optional reference attribute for testing.
    optional_field3 : str | None
        Optional field without category specification.
    reference1 : AbstractMockItem | None
        First reference attribute for testing.
    reference2 : AbstractMockItem | None
        Second reference attribute for testing.
    """

    uri: str = "https://pyDEXPI.org/schemas/abstract/mockTestModel.py"

    # Compositional attributes:
    items: list[AbstractMockItem] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )
    other_items: list[AbstractMockItem] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )

    # Data attributes:
    required_field1: str = Field(..., json_schema_extra={"attribute_category": "data"})
    required_field2: AbstractMockItem = Field(
        ..., json_schema_extra={"attribute_category": "reference"}
    )
    required_field3: int
    optional_field1: float | None = Field(None, json_schema_extra={"attribute_category": "data"})
    optional_field2: AbstractMockItem | None = Field(
        None, json_schema_extra={"attribute_category": "reference"}
    )
    optional_field3: str | None = None

    # Reference attributes:
    reference1: AbstractMockItem | None = Field(
        None, json_schema_extra={"attribute_category": "reference"}
    )
    reference2: AbstractMockItem | None = Field(
        None, json_schema_extra={"attribute_category": "reference"}
    )


class InheritedMockTestModel(AbstractMockTestModel):
    """Inherited mock model to test attribute categorization in subclasses.

    This class inherits from AbstractMockTestModel and adds additional attributes
    to verify that the base_model_utils functions correctly handle inherited fields.

    Attributes
    ----------
    additional_items : list[AbstractMockItem]
        Additional compositional attribute for testing inheritance.
    additional_data : str | None
        Additional data attribute for testing inheritance.
    additional_reference : AbstractMockItem | None
        Additional reference attribute for testing inheritance.
    """

    additional_items: list[AbstractMockItem] = Field(
        default_factory=list, json_schema_extra={"attribute_category": "composition"}
    )


@pytest.fixture
def mock_test_object_factory():
    """Factory function for creating mock test objects.

    Returns
    -------
    callable
        A factory function that creates AbstractMockTestModel instances.
    """

    def _create_mock_test_object() -> AbstractMockTestModel:
        """Create a mock test object with the expected attributes.

        Returns
        -------
        AbstractMockTestModel
            A mock test object instance.
        """
        return AbstractMockTestModel(
            required_field1="Test String",
            required_field2=AbstractMockItem(),
            required_field3=42,
        )

    return _create_mock_test_object


def test_get_composition_attributes(mock_test_object_factory):
    """Test function to retrieve composition attributes.

    Parameters
    ----------
    mock_test_object_factory : callable
        Factory function for creating mock test objects.
    """
    # Define the expected set of composition attributes based on our mock model
    attributes = bmt.get_composition_attributes(mock_test_object_factory())
    # Check if all composition attributes were found
    comp_attrs = {"items", "other_items"}
    assert set(attributes) == comp_attrs


def test_get_reference_attributes(mock_test_object_factory):
    """Test function to retrieve reference attributes.

    Parameters
    ----------
    mock_test_object_factory : callable
        Factory function for creating mock test objects.
    """
    attributes = bmt.get_reference_attributes(mock_test_object_factory())
    # Define the expected set of reference attributes based on our mock model
    ref_attrs = {"required_field2", "optional_field2", "reference1", "reference2"}
    # Check if all reference attributes were found
    assert set(attributes) == ref_attrs


def test_get_data_attributes(mock_test_object_factory):
    """Test function to retrieve data attributes.

    Parameters
    ----------
    mock_test_object_factory : callable
        Factory function for creating mock test objects.
    """
    attributes = bmt.get_data_attributes(mock_test_object_factory())
    # Define the expected set of data attributes based on our mock model
    data_attrs = {"required_field1", "optional_field1"}
    # Check if all data attributes were found
    assert set(attributes) == data_attrs


def test_get_attributes_with_category(mock_test_object_factory):
    """Test the function get_attributes_with_category.

    This test is mostly covered by implementation functions with data, composition, and reference,
    but provides additional coverage for edge cases.

    Parameters
    ----------
    mock_test_object_factory : callable
        Factory function for creating mock test objects.
    """
    assert bmt._get_attributes_with_category(mock_test_object_factory(), "data")
    assert not bmt._get_attributes_with_category(mock_test_object_factory(), "something else")


def test_get_composition_attributes_from_class():
    """Test retrieval of composition attribute names from the class (schema-level)."""
    assert bmt.get_composition_attributes_from_class(AbstractMockTestModel) == {
        "items",
        "other_items",
    }


def test_get_reference_attributes_from_class():
    """Test retrieval of reference attribute names from the class (schema-level)."""
    assert bmt.get_reference_attributes_from_class(AbstractMockTestModel) == {
        "required_field2",
        "optional_field2",
        "reference1",
        "reference2",
    }


def test_get_data_attributes_from_class():
    """Test retrieval of data attribute names from the class (schema-level)."""
    assert bmt.get_data_attributes_from_class(AbstractMockTestModel) == {
        "required_field1",
        "optional_field1",
    }


def test_get_dexpi_class() -> None:
    """Test the function get_dexpi_class using mock classes.

    Since we're using mock classes, this test verifies that the function
    can handle class name resolution for the expected DEXPI class names.
    """
    # Test with mock classes that should exist
    try:
        # These should work with real classes if available
        from pydexpi.dexpi_classes.pydantic_classes import (
            ActuatingSystem,
            Equipment,
            PipingNetworkSegment,
        )

        assert bmt.get_dexpi_class("PipingNetworkSegment") == PipingNetworkSegment
        assert bmt.get_dexpi_class("Equipment") == Equipment
        assert bmt.get_dexpi_class("ActuatingSystem") == ActuatingSystem
    except ImportError:
        # If real classes don't exist, test with our mock classes
        pass

    # Test that non-existent classes raise AttributeError
    with pytest.raises(AttributeError):
        bmt.get_dexpi_class("NonExistentClass")


def test_get_dexpi_class_from_uri() -> None:
    pns = PipingNetworkSegment()
    assert bmt.get_dexpi_class_from_uri(pns.uri) == PipingNetworkSegment

    equipment = Equipment()
    assert bmt.get_dexpi_class_from_uri(equipment.uri) == Equipment

    actuating_system = ActuatingSystem()
    assert bmt.get_dexpi_class_from_uri(actuating_system.uri) == ActuatingSystem

    with pytest.raises(AttributeError):
        bmt.get_dexpi_class_from_uri("http://example.com/NonExistentClass")


def test_attribute_is_required() -> None:
    """Test the function attribute_is_required."""
    assert bmt.attribute_is_required(AbstractMockTestModel, "required_field1")
    assert bmt.attribute_is_required(AbstractMockTestModel, "required_field2")
    assert bmt.attribute_is_required(AbstractMockTestModel, "required_field3")

    assert not bmt.attribute_is_required(AbstractMockTestModel, "optional_field1")
    assert not bmt.attribute_is_required(AbstractMockTestModel, "optional_field2")
    assert not bmt.attribute_is_required(AbstractMockTestModel, "optional_field3")


def test_attribute_is_required_inherited() -> None:
    """Test the function attribute_is_required for inherited classes."""
    assert bmt.attribute_is_required(InheritedMockTestModel, "required_field1")
    assert bmt.attribute_is_required(InheritedMockTestModel, "required_field2")
    assert bmt.attribute_is_required(InheritedMockTestModel, "required_field3")

    assert not bmt.attribute_is_required(InheritedMockTestModel, "optional_field1")
    assert not bmt.attribute_is_required(InheritedMockTestModel, "optional_field2")
    assert not bmt.attribute_is_required(InheritedMockTestModel, "optional_field3")

    # Test additional attributes in the inherited class
    assert bmt.attribute_is_required(InheritedMockTestModel, "additional_items")


def test_resolve_enum_member():
    """Test resolve_enum_member for both int and str input."""

    class Color(Enum):
        RED = "red"
        GREEN = "green"
        BLUE = "blue"

    # By index (int)
    assert bmt.resolve_enum_member(Color, 0) == Color.RED
    assert bmt.resolve_enum_member(Color, 1) == Color.GREEN
    assert bmt.resolve_enum_member(Color, 2) == Color.BLUE

    # By string (name)
    assert bmt.resolve_enum_member(Color, "red") == Color.RED
    assert bmt.resolve_enum_member(Color, "green") == Color.GREEN
    assert bmt.resolve_enum_member(Color, "blue") == Color.BLUE

    # By string (value as string)
    with pytest.raises(ValueError):
        bmt.resolve_enum_member(Color, "NOT_A_COLOR")

    # By int as string
    assert bmt.resolve_enum_member(Color, "0") == Color.RED
    assert bmt.resolve_enum_member(Color, "1") == Color.GREEN
    assert bmt.resolve_enum_member(Color, "2") == Color.BLUE

    # Out of range index
    with pytest.raises(IndexError):
        bmt.resolve_enum_member(Color, 10)


def test_get_inheritance_from_dexpi_class() -> None:
    """Test get_inheritance_from_dexpi_class returns correct class hierarchy."""
    labels = bmt.get_inheritance_from_dexpi_class(PipingNetworkSegment)

    # The result should be a list of types
    assert isinstance(labels, list)
    assert all(isinstance(label, type) for label in labels)

    # The class itself should be present
    assert PipingNetworkSegment in labels
    assert ActuatingElectricalLocation in labels
    assert SensingLocation in labels

    # Base sentinel classes should not be present
    assert DexpiBaseModel not in labels
    assert BaseModel not in labels
    from abc import ABC
    assert ABC not in labels

    # Test with another class to verify parent classes are included
    equipment_labels = bmt.get_inheritance_from_dexpi_class(Equipment)
    assert Equipment in equipment_labels

    # Test with the mock class defined in this test module
    mock_labels = bmt.get_inheritance_from_dexpi_class(AbstractMockTestModel)
    assert AbstractMockTestModel in mock_labels

    # Test that an inherited mock class includes both child and parent class names
    inherited_labels = bmt.get_inheritance_from_dexpi_class(InheritedMockTestModel)
    assert InheritedMockTestModel in inherited_labels
    assert AbstractMockTestModel in inherited_labels

