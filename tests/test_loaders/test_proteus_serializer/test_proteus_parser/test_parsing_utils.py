"""Tests for the parsing_utils module of the proteus serializer."""

from unittest.mock import Mock

import pytest

from pydexpi.dexpi_classes.pydantic_classes import DexpiBaseModel
from pydexpi.loaders.proteus_serializer.proteus_parser.core import ErrorLevels, ParserModule
from pydexpi.loaders.proteus_serializer.proteus_parser.parsing_utils import (
    ErrorTemplates,
    add_by_inferring_type,
    filter_none,
    is_associated_with,
    redirect_errors_to_registry,
)


class TestErrorTemplates:
    """Test the ErrorTemplates class and its static methods."""

    def test_id_not_found(self) -> None:
        """Test the id_not_found error template."""
        element_name = "TestElement"
        message, level = ErrorTemplates.id_not_found(element_name)

        expected_message = f"ID not found for element '{element_name}'. Element Skipped."
        assert message == expected_message
        assert level == ErrorLevels.ERROR

    def test_skip_pass(self) -> None:
        """Test the skip_pass error template."""
        pass_name = "reference"
        element_name = "TestElement"
        message, level = ErrorTemplates.skip_pass(pass_name, element_name)

        expected_message = (
            f"'{pass_name}' pass skipped for element '{element_name}' due to error in previous "
            f"pass. Element Skipped."
        )
        assert message == expected_message
        assert level == ErrorLevels.INFO

    def test_assoc_adding_error(self) -> None:
        """Test the assoc_adding_error error template."""
        element_name = "TestElement"
        associated_obj_id = "AssocObj123"
        message, level = ErrorTemplates.assoc_adding_error(element_name, associated_obj_id)

        expected_message = (
            f"Object {associated_obj_id} could not be added as reference to {element_name}."
        )
        assert message == expected_message
        assert level == ErrorLevels.ERROR

    def test_no_assoc_ctrl(self) -> None:
        """Test the no_assoc_ctrl error template."""
        element_name = "TestElement"
        associated_obj_id = "AssocObj123"
        message, level = ErrorTemplates.no_assoc_ctrl(element_name, associated_obj_id)

        expected_message = (
            f"Association of {element_name} with {associated_obj_id} is missing in control pass. "
            f"Attempt adding association."
        )
        assert message == expected_message
        assert level == ErrorLevels.WARNING

    def test_assoc_added_ctrl_normal(self) -> None:
        """Test the assoc_added_ctrl error template with normal order."""
        element_name = "TestElement"
        associated_obj_id = "AssocObj123"
        field_name = "test_field"
        message, level = ErrorTemplates.assoc_added_ctrl(
            element_name, associated_obj_id, field_name
        )

        expected_message = (
            f"Association of {element_name} with {associated_obj_id} added in control pass to "
            f"field {field_name}."
        )
        assert message == expected_message
        assert level == ErrorLevels.INFO

    def test_assoc_added_ctrl_reverse(self) -> None:
        """Test the assoc_added_ctrl error template with reverse order."""
        element_name = "TestElement"
        associated_obj_id = "AssocObj123"
        field_name = "test_field"
        message, level = ErrorTemplates.assoc_added_ctrl(
            element_name, associated_obj_id, field_name, reverse=True
        )

        expected_message = (
            f"Association of {element_name} with {associated_obj_id} added in control pass in "
            f"reverse order to field {field_name}."
        )
        assert message == expected_message
        assert level == ErrorLevels.INFO

    def test_assoc_not_added_ctrl(self) -> None:
        """Test the assoc_not_added_ctrl error template."""
        element_name = "TestElement"
        associated_obj_id = "AssocObj123"
        message, level = ErrorTemplates.assoc_not_added_ctrl(element_name, associated_obj_id)

        expected_message = (
            f"Association of {element_name} with {associated_obj_id} could not be added in control "
            f"pass."
        )
        assert message == expected_message
        assert level == ErrorLevels.ERROR

    def test_inval_assoc_type(self) -> None:
        """Test the inval_assoc_type error template."""
        element_name = "TestElement"
        assoc_type = "InvalidType"
        message, level = ErrorTemplates.inval_assoc_type(element_name, assoc_type)

        expected_message = (
            f"Invalid association type '{assoc_type}' for {element_name}. Association skipped."
        )
        assert message == expected_message
        assert level == ErrorLevels.ERROR


class MockAssociatedModel(DexpiBaseModel):
    """Another mock DEXPI model for association testing."""

    description: str | None = None


class MockAssociatedModel2(DexpiBaseModel):
    """Another mock DEXPI model for association testing."""

    description: str | None = None


class MockDexpiModel(DexpiBaseModel):
    """Mock DEXPI model for testing purposes."""

    name: str | None = None
    value: int | None = None
    items: list[str] | None = None
    other_model: MockAssociatedModel | None = None
    model_list: list[MockAssociatedModel2] | None = None


class MockIncompatibleModel(DexpiBaseModel):
    """A mock model that's incompatible with MockDexpiModel fields."""

    incompatible_field: str = "incompatible"


class TestAddByInferringType:
    """Test the add_by_inferring_type function."""

    def test_add_to_none_field_success(self) -> None:
        """Test successfully adding to a None field."""
        container = MockDexpiModel()
        to_add = MockAssociatedModel(description="test")

        # Initially other_model should be None
        assert container.other_model is None

        field_name = add_by_inferring_type(to_add, container)

        # The function should find a suitable field and return its name
        assert field_name == "other_model"
        # Since we can't predict which field it chooses, just verify one was set
        assert container.other_model is not None or container.model_list is not None

    def test_add_to_list_field_success(self) -> None:
        """Test successfully adding to a list field."""
        container = MockDexpiModel(model_list=[])
        to_add = MockAssociatedModel2(description="test")

        field_name = add_by_inferring_type(to_add, container)

        # The function should find a suitable field and add the item
        assert field_name == "model_list"
        # Verify the item was added to one of the compatible fields
        assert to_add in container.model_list

    def test_add_to_existing_list_field(self) -> None:
        """Test adding to an existing list with items."""
        existing_item = MockAssociatedModel2(description="existing")
        container = MockDexpiModel(model_list=[existing_item])
        to_add = MockAssociatedModel2(description="new")

        field_name = add_by_inferring_type(to_add, container)

        # The function should find a suitable field
        assert field_name is not None
        # The existing item should still be there
        assert existing_item in container.model_list
        # The new item should be added somewhere
        assert to_add in container.model_list

    def test_no_suitable_field_raises_error(self) -> None:
        """Test that ValueError is raised when no suitable field is found."""
        # Create a model with all fields filled
        first_model = MockAssociatedModel(description="existing")
        container = MockDexpiModel(
            name="test",
            value=42,
            items=["item1"],
            other_model=first_model,
            model_list=[MockAssociatedModel2(description="existing_list_item")],
        )

        # Try to add something that doesn't fit anywhere - incompatible type
        to_add = MockIncompatibleModel(incompatible_field="test")

        with pytest.raises(ValueError, match="No suitable field found"):
            add_by_inferring_type(to_add, container)

        # Assert initial state is unchanged
        assert container.other_model == first_model

    def test_validation_error_handling(self) -> None:
        """Test that ValidationError is handled gracefully."""
        container = MockDexpiModel()

        # Create an object that should work with the container
        to_add = MockAssociatedModel(description="test")

        # This should work despite potential validation errors
        field_name = add_by_inferring_type(to_add, container)
        assert field_name is not None


class TestIsAssociatedWith:
    """Test the is_associated_with function."""

    def test_direct_association(self) -> None:
        """Test detection of direct association."""
        member = MockAssociatedModel(description="member")
        container = MockDexpiModel(other_model=member)

        assert is_associated_with(member, container) is True

    def test_list_association(self) -> None:
        """Test detection of association in a list."""
        member = MockAssociatedModel2(description="member")
        other_member = MockAssociatedModel2(description="other")
        container = MockDexpiModel(model_list=[other_member, member])

        assert is_associated_with(member, container) is True

    def test_no_association(self) -> None:
        """Test when there is no association."""
        member = MockAssociatedModel(description="member")
        other_member = MockAssociatedModel(description="other")
        container = MockDexpiModel(other_model=other_member)

        assert is_associated_with(member, container) is False

    def test_empty_container(self) -> None:
        """Test with empty container."""
        member = MockAssociatedModel(description="member")
        container = MockDexpiModel()

        assert is_associated_with(member, container) is False

    def test_empty_list_field(self) -> None:
        """Test with empty list field."""
        member = MockAssociatedModel(description="member")
        container = MockDexpiModel(model_list=[])

        assert is_associated_with(member, container) is False

    def test_none_fields_ignored(self) -> None:
        """Test that None fields are handled properly."""
        member = MockAssociatedModel(description="member")
        container = MockDexpiModel(other_model=None, model_list=None)

        assert is_associated_with(member, container) is False


class TestFilterNone:
    """Test the filter_none function."""

    def test_filter_empty_list(self) -> None:
        """Test filtering an empty list."""
        result = filter_none([])
        assert result == []

    def test_filter_no_none_values(self) -> None:
        """Test filtering a list with no None values."""
        items = [1, 2, "test", True]
        result = filter_none(items)
        assert result == items

    def test_filter_all_none_values(self) -> None:
        """Test filtering a list with all None values."""
        items = [None, None, None]
        result = filter_none(items)
        assert result == []

    def test_filter_mixed_values(self) -> None:
        """Test filtering a list with mixed values."""
        items = [1, None, "test", None, 42, None, True]
        expected = [1, "test", 42, True]
        result = filter_none(items)
        assert result == expected

    def test_filter_preserves_order(self) -> None:
        """Test that filtering preserves the original order."""
        items = ["first", None, "second", None, "third"]
        expected = ["first", "second", "third"]
        result = filter_none(items)
        assert result == expected

    def test_filter_with_falsy_values(self) -> None:
        """Test that falsy values (but not None) are preserved."""
        items = [0, None, "", None, False, None, []]
        expected = [0, "", False, []]
        result = filter_none(items)
        assert result == expected


class MockLoaderModule(ParserModule):
    """Mock LoaderModule for testing the decorator."""

    def __init__(self) -> None:
        # Mock the context and register_error method
        self.context = Mock()
        self.register_error = Mock()

    def compositional_pass(self) -> None:
        """Mock implementation."""
        pass


class TestRedirectErrorsToRegistry:
    """Test the redirect_errors_to_registry decorator."""

    def test_successful_execution(self) -> None:
        """Test that successful function execution works normally."""

        @redirect_errors_to_registry
        def test_function(self, x: int, y: int) -> int:
            return x + y

        loader = MockLoaderModule()
        result = test_function(loader, 5, 3)

        assert result == 8
        loader.register_error.assert_not_called()

    def test_exception_redirected_to_registry(self) -> None:
        """Test that exceptions are redirected to the error registry."""
        test_exception = ValueError("Test error")

        @redirect_errors_to_registry
        def test_function(self, x: int) -> int:
            raise test_exception

        loader = MockLoaderModule()
        result = test_function(loader, 5)

        assert result is None
        loader.register_error.assert_called_once()

        # Check the arguments passed to register_error
        call_args = loader.register_error.call_args
        assert "Test error" in call_args.kwargs["message"]
        assert call_args.kwargs["level"] == ErrorLevels.ERROR
        assert call_args.kwargs["exception"] == test_exception

    def test_no_args_raises_error(self) -> None:
        """Test that decorator raises error when called with no arguments."""

        @redirect_errors_to_registry
        def test_function() -> None:
            raise ValueError("Should not reach here")

        with pytest.raises(ValueError, match="first argument 'self' must be an instance"):
            test_function()

    def test_wrong_self_type_raises_error(self) -> None:
        """Test that decorator raises error when self is not LoaderModule."""

        @redirect_errors_to_registry
        def test_function(self) -> None:
            raise ValueError("Should not reach here")

        wrong_self = "not_a_loader_module"

        with pytest.raises(ValueError, match="first argument 'self' must be an instance"):
            test_function(wrong_self)

    def test_message_formatting(self) -> None:
        """Test that error message is formatted correctly."""

        @redirect_errors_to_registry
        def test_parsing_step(self) -> None:
            raise KeyError("Missing key")

        loader = MockLoaderModule()
        loader.__class__.__name__ = "TestLoader"

        test_parsing_step(loader)

        call_args = loader.register_error.call_args
        message = call_args.kwargs["message"]

        assert "test_parsing_step" in message
        assert "TestLoader" in message
        assert "Missing key" in message

    def test_function_name_in_error_message(self) -> None:
        """Test that the function name appears in the error message."""

        @redirect_errors_to_registry
        def specific_parsing_function(self) -> None:
            raise IndexError("Index out of range")

        loader = MockLoaderModule()
        specific_parsing_function(loader)

        call_args = loader.register_error.call_args
        message = call_args.kwargs["message"]

        assert "specific_parsing_function" in message

    def test_kwargs_passed_through(self) -> None:
        """Test that keyword arguments are passed through correctly."""

        @redirect_errors_to_registry
        def test_function(self, x: int, y: int = 10, z: str = "default") -> str:
            return f"{x}-{y}-{z}"

        loader = MockLoaderModule()
        result = test_function(loader, 5, y=20, z="custom")

        assert result == "5-20-custom"

    def test_preserves_function_metadata(self) -> None:
        """Test that the decorator preserves function metadata."""

        @redirect_errors_to_registry
        def documented_function(self) -> int:
            """This function has documentation."""
            return 42

        # The @wraps decorator should preserve the original function's metadata
        assert documented_function.__name__ == "documented_function"
        assert "This function has documentation" in documented_function.__doc__
