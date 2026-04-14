"""Tests for the core module of the proteus serializer."""

import xml.etree.ElementTree as ET
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import Mock

import pytest

from pydexpi.dexpi_classes.pydantic_classes import DexpiBaseModel, DexpiModel
from pydexpi.loaders.proteus_serializer.proteus_parser.core import (
    ErrorLevels,
    ErrorRegistry,
    ErrorRegistryEntry,
    InternalParserError,
    ModuleContext,
    ObjectRegistry,
    ParserModule,
    ProteusLoader,
)


class TestInternalParserError:
    """Test the InternalParserError exception class."""

    def test_creation(self) -> None:
        """Test creating an InternalParserError."""
        error = InternalParserError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)


class TestErrorLevels:
    """Test the ErrorLevels enumeration."""

    def test_all_levels_exist(self) -> None:
        """Test that all expected error levels exist."""
        assert ErrorLevels.INFO.value == "info"
        assert ErrorLevels.WARNING.value == "warning"
        assert ErrorLevels.ERROR.value == "error"
        assert ErrorLevels.CRITICAL.value == "critical"

    def test_enum_comparison(self) -> None:
        """Test that enum values can be compared."""
        assert ErrorLevels.INFO == ErrorLevels.INFO
        assert ErrorLevels.INFO != ErrorLevels.ERROR


class TestErrorRegistryEntry:
    """Test the ErrorRegistryEntry dataclass."""

    def test_minimal_entry(self) -> None:
        """Test creating an entry with minimal parameters."""
        entry = ErrorRegistryEntry(message="Test message", level=ErrorLevels.WARNING)
        assert entry.message == "Test message"
        assert entry.level == ErrorLevels.WARNING
        assert entry.proteus_id is None
        assert entry.exception is None

    def test_full_entry(self) -> None:
        """Test creating an entry with all parameters."""
        exception = ValueError("Test exception")
        entry = ErrorRegistryEntry(
            message="Test message",
            level=ErrorLevels.ERROR,
            proteus_id="test-id-123",
            exception=exception,
        )
        assert entry.message == "Test message"
        assert entry.level == ErrorLevels.ERROR
        assert entry.proteus_id == "test-id-123"
        assert entry.exception == exception


class TestErrorRegistry:
    """Test the ErrorRegistry class."""

    def test_initialization(self) -> None:
        """Test that ErrorRegistry initializes with empty error list."""
        registry = ErrorRegistry()
        assert registry.errors == []

    def test_register_error(self) -> None:
        """Test registering a normal error."""
        registry = ErrorRegistry()
        entry = ErrorRegistryEntry(
            message="Test error", level=ErrorLevels.WARNING, proteus_id="test-id"
        )

        registry.register_error(entry)

        assert len(registry.errors) == 1
        assert registry.errors[0] == entry

    def test_register_internal_parser_error(self) -> None:
        """Test that InternalParserError is reraised."""
        registry = ErrorRegistry()
        internal_error = InternalParserError("Internal error")
        entry = ErrorRegistryEntry(
            message="Internal error occurred", level=ErrorLevels.CRITICAL, exception=internal_error
        )

        with pytest.raises(InternalParserError, match="Internal error"):
            registry.register_error(entry)

        # Error should still be registered
        assert len(registry.errors) == 1

    def test_get_errors_all(self) -> None:
        """Test getting all errors without filter."""
        registry = ErrorRegistry()
        entries = [
            ErrorRegistryEntry("Info message", ErrorLevels.INFO),
            ErrorRegistryEntry("Warning message", ErrorLevels.WARNING),
            ErrorRegistryEntry("Error message", ErrorLevels.ERROR),
        ]

        for entry in entries:
            registry.register_error(entry)

        all_errors = registry.get_errors()
        assert len(all_errors) == 3
        assert all_errors == entries

    def test_get_errors_filtered(self) -> None:
        """Test getting errors filtered by level."""
        registry = ErrorRegistry()
        entries = [
            ErrorRegistryEntry("Info message", ErrorLevels.INFO),
            ErrorRegistryEntry("Warning message", ErrorLevels.WARNING),
            ErrorRegistryEntry("Error message", ErrorLevels.ERROR),
            ErrorRegistryEntry("Critical message", ErrorLevels.CRITICAL),
        ]

        for entry in entries:
            registry.register_error(entry)

        # Test filtering for ERROR and CRITICAL
        filtered_errors = registry.get_errors([ErrorLevels.ERROR, ErrorLevels.CRITICAL])
        assert len(filtered_errors) == 2
        assert all(
            error.level in [ErrorLevels.ERROR, ErrorLevels.CRITICAL] for error in filtered_errors
        )

    def test_get_errors_empty_filter(self) -> None:
        """Test getting errors with empty filter list."""
        registry = ErrorRegistry()
        entry = ErrorRegistryEntry("Test message", ErrorLevels.INFO)
        registry.register_error(entry)

        filtered_errors = registry.get_errors([])
        assert len(filtered_errors) == 0


class TestObjectRegistry:
    """Test the ObjectRegistry class."""

    def test_initialization(self) -> None:
        """Test that ObjectRegistry initializes with empty objects dict."""
        registry = ObjectRegistry()
        assert registry.objects == {}

    def test_register_and_get_object(self) -> None:
        """Test registering and retrieving an object."""
        registry = ObjectRegistry()
        test_object = {"test": "data"}
        proteus_id = "test-id-123"

        registry.register_object(proteus_id, test_object)

        retrieved = registry.get_object(proteus_id)
        assert retrieved == test_object

    def test_get_nonexistent_object(self) -> None:
        """Test getting an object that doesn't exist."""
        registry = ObjectRegistry()

        retrieved = registry.get_object("nonexistent-id")
        assert retrieved is None

    def test_register_multiple_objects(self) -> None:
        """Test registering multiple objects."""
        registry = ObjectRegistry()
        objects = {
            "id1": {"data": "object1"},
            "id2": {"data": "object2"},
            "id3": {"data": "object3"},
        }

        for proteus_id, obj in objects.items():
            registry.register_object(proteus_id, obj)

        for proteus_id, expected_obj in objects.items():
            retrieved = registry.get_object(proteus_id)
            assert retrieved == expected_obj

    def test_overwrite_object(self) -> None:
        """Test overwriting an existing object."""
        registry = ObjectRegistry()
        proteus_id = "test-id"

        registry.register_object(proteus_id, {"version": 1})
        registry.register_object(proteus_id, {"version": 2})

        retrieved = registry.get_object(proteus_id)
        assert retrieved == {"version": 2}


class TestModuleContext:
    """Test the ModuleContext class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.error_registry = ErrorRegistry()
        self.object_registry = ObjectRegistry()

    def test_initialization(self) -> None:
        """Test ModuleContext initialization."""
        self.setUp()
        context = ModuleContext(
            element_stack=["root", "child"],
            id_stack=["root-id", "child-id"],
            error_registry=self.error_registry,
            object_registry=self.object_registry,
        )

        assert context.element_stack == ["root", "child"]
        assert context.id_stack == ["root-id", "child-id"]
        assert context.error_registry == self.error_registry
        assert context.object_registry == self.object_registry

    def test_get_updated_context(self) -> None:
        """Test creating updated context with new element."""
        self.setUp()
        context = ModuleContext(
            element_stack=["root"],
            id_stack=["root-id"],
            error_registry=self.error_registry,
            object_registry=self.object_registry,
        )

        # Create XML element with ID
        element = ET.Element("child")
        element.set("ID", "child-id")

        updated_context = context.get_updated_context(element)

        assert updated_context.element_stack == ["root", "child"]
        assert updated_context.id_stack == ["root-id", "child-id"]
        assert updated_context.error_registry == self.error_registry
        assert updated_context.object_registry == self.object_registry

    def test_get_updated_context_no_id(self) -> None:
        """Test creating updated context with element that has no ID."""
        self.setUp()
        context = ModuleContext(
            element_stack=["root"],
            id_stack=["root-id"],
            error_registry=self.error_registry,
            object_registry=self.object_registry,
        )

        element = ET.Element("child")  # No ID attribute

        updated_context = context.get_updated_context(element)

        assert updated_context.element_stack == ["root", "child"]
        assert updated_context.id_stack == ["root-id", None]

    def test_get_last_id_success(self) -> None:
        """Test getting the last non-None ID from stack."""
        self.setUp()
        context = ModuleContext(
            element_stack=["root", "child", "grandchild"],
            id_stack=["root-id", "child-id", None],
            error_registry=self.error_registry,
            object_registry=self.object_registry,
        )

        last_id = context.get_last_id()
        assert last_id == "child-id"

    def test_get_last_id_all_none(self) -> None:
        """Test getting last ID when all IDs are None."""
        self.setUp()
        context = ModuleContext(
            element_stack=["root", "child"],
            id_stack=[None, None],
            error_registry=self.error_registry,
            object_registry=self.object_registry,
        )

        with pytest.raises(ValueError, match="ID stack is empty or contains only None values"):
            context.get_last_id()

    def test_get_last_id_empty_stack(self) -> None:
        """Test getting last ID when stack is empty."""
        self.setUp()
        context = ModuleContext(
            element_stack=[],
            id_stack=[],
            error_registry=self.error_registry,
            object_registry=self.object_registry,
        )

        with pytest.raises(ValueError, match="ID stack is empty or contains only None values"):
            context.get_last_id()

    def test_register_error_with_explicit_id(self) -> None:
        """Test registering error with explicit proteus_id."""
        self.setUp()
        context = ModuleContext(
            element_stack=["root"],
            id_stack=["root-id"],
            error_registry=self.error_registry,
            object_registry=self.object_registry,
        )

        context.register_error("Test error", ErrorLevels.WARNING, proteus_id="explicit-id")

        errors = self.error_registry.get_errors()
        assert len(errors) == 1
        assert errors[0].proteus_id == "explicit-id"

    def test_register_error_with_inferred_id(self) -> None:
        """Test registering error with ID inferred from context."""
        self.setUp()
        context = ModuleContext(
            element_stack=["root", "child"],
            id_stack=["root-id", "child-id"],
            error_registry=self.error_registry,
            object_registry=self.object_registry,
        )

        context.register_error("Test error", ErrorLevels.WARNING)

        errors = self.error_registry.get_errors()
        assert len(errors) == 1
        assert errors[0].proteus_id == "child-id"

    def test_register_error_no_id_available(self) -> None:
        """Test registering error when no ID is available."""
        self.setUp()
        context = ModuleContext(
            element_stack=["root"],
            id_stack=[None],
            error_registry=self.error_registry,
            object_registry=self.object_registry,
        )

        context.register_error("Test error", ErrorLevels.WARNING)

        errors = self.error_registry.get_errors()
        assert len(errors) == 1
        assert errors[0].proteus_id is None


class ConcreteParserModule(ParserModule):
    """Concrete implementation of ParserModule for testing."""

    def __init__(self, context: ModuleContext, return_value: str = "test_result") -> None:
        """Initialize concrete parser module.

        Parameters
        ----------
        context : ModuleContext
            The module context
        return_value : str, optional
            Value to return from compositional_pass, by default "test_result"
        """
        super().__init__(context)
        self.return_value = return_value

    def compositional_pass(self) -> str:
        """Return test result from compositional pass.

        Returns
        -------
        str
            Test result value
        """
        return self.return_value


class TestParserModule:
    """Test the ParserModule abstract base class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.error_registry = ErrorRegistry()
        self.object_registry = ObjectRegistry()
        self.context = ModuleContext(
            element_stack=["root"],
            id_stack=["root-id"],
            error_registry=self.error_registry,
            object_registry=self.object_registry,
        )

    def test_initialization(self) -> None:
        """Test ParserModule initialization."""
        self.setUp()
        module = ConcreteParserModule(self.context)

        assert module.context == self.context
        assert module.submodules == []

    def test_compositional_pass(self) -> None:
        """Test compositional pass method."""
        self.setUp()
        module = ConcreteParserModule(self.context, "custom_result")

        result = module.compositional_pass()
        assert result == "custom_result"

    def test_reference_pass_no_submodules(self) -> None:
        """Test reference pass with no submodules."""
        self.setUp()
        module = ConcreteParserModule(self.context)

        # Should not raise any exceptions
        module.reference_pass()

    def test_reference_pass_with_submodules(self) -> None:
        """Test reference pass with submodules."""
        self.setUp()
        module = ConcreteParserModule(self.context)

        # Create mock submodules
        submodule1 = Mock(spec=ParserModule)
        submodule2 = Mock(spec=ParserModule)

        module.register_submodule(submodule1)
        module.register_submodule(submodule2)

        module.reference_pass()

        submodule1.reference_pass.assert_called_once()
        submodule2.reference_pass.assert_called_once()

    def test_control_pass_with_submodules(self) -> None:
        """Test control pass with submodules."""
        self.setUp()
        module = ConcreteParserModule(self.context)

        # Create mock submodules
        submodule1 = Mock(spec=ParserModule)
        submodule2 = Mock(spec=ParserModule)

        module.register_submodule(submodule1)
        module.register_submodule(submodule2)

        module.control_pass()

        submodule1.control_pass.assert_called_once()
        submodule2.control_pass.assert_called_once()

    def test_register_submodule(self) -> None:
        """Test registering a single submodule."""
        self.setUp()
        module = ConcreteParserModule(self.context)
        submodule = ConcreteParserModule(self.context)

        module.register_submodule(submodule)

        assert len(module.submodules) == 1
        assert module.submodules[0] == submodule

    def test_register_submodule_list(self) -> None:
        """Test registering multiple submodules at once."""
        self.setUp()
        module = ConcreteParserModule(self.context)
        submodules = [
            ConcreteParserModule(self.context),
            ConcreteParserModule(self.context),
            ConcreteParserModule(self.context),
        ]

        module.register_submodule_list(submodules)

        assert len(module.submodules) == 3
        assert module.submodules == submodules

    def test_register_error(self) -> None:
        """Test registering an error through the module."""
        self.setUp()
        module = ConcreteParserModule(self.context)

        module.register_error("Module error", ErrorLevels.ERROR)

        errors = self.error_registry.get_errors()
        assert len(errors) == 1
        assert errors[0].message == "Module error"
        assert errors[0].level == ErrorLevels.ERROR

    def test_register_object(self) -> None:
        """Test registering an object through the module."""
        self.setUp()
        module = ConcreteParserModule(self.context)
        test_object = Mock(spec=DexpiBaseModel)

        module.register_object("test-id", test_object)

        retrieved = self.object_registry.get_object("test-id")
        assert retrieved == test_object

    def test_get_object_from_registry(self) -> None:
        """Test getting an object from registry through the module."""
        self.setUp()
        module = ConcreteParserModule(self.context)
        test_object = Mock(spec=DexpiBaseModel)

        self.object_registry.register_object("test-id", test_object)

        retrieved = module.get_object_from_registry("test-id")
        assert retrieved == test_object

    def test_get_nonexistent_object_from_registry(self) -> None:
        """Test getting nonexistent object returns None."""
        self.setUp()
        module = ConcreteParserModule(self.context)

        retrieved = module.get_object_from_registry("nonexistent-id")
        assert retrieved is None


class TestProteusLoader:
    """Test the ProteusLoader class."""

    def test_initialization(self) -> None:
        """Test ProteusLoader initialization."""
        factory = Mock()
        loader = ProteusLoader(factory)

        assert loader.parser_factory == factory
        assert loader.error_registry is None
        assert loader.object_registry is None

    def test_reset_registries(self) -> None:
        """Test resetting registries creates new instances."""
        factory = Mock()
        loader = ProteusLoader(factory)

        loader.reset_registries()

        assert isinstance(loader.error_registry, ErrorRegistry)
        assert isinstance(loader.object_registry, ObjectRegistry)
        assert loader.error_registry.errors == []
        assert loader.object_registry.objects == {}

    def test_load_xmlstring_success(self) -> None:
        """Test successful XML string loading."""
        # Create mock factory and parser
        factory = Mock()
        parser = Mock()
        expected_model = Mock(spec=DexpiModel)

        factory.make_plant_model_parser.return_value = parser
        parser.compositional_pass.return_value = expected_model

        loader = ProteusLoader(factory)

        xml_string = "<root><PlantModel></PlantModel></root>"
        result = loader.load_xmlstring(xml_string)

        # Verify the loading sequence
        factory.make_plant_model_parser.assert_called_once()
        parser.compositional_pass.assert_called_once()
        parser.reference_pass.assert_called_once()
        parser.control_pass.assert_called_once()

        assert result == expected_model
        assert isinstance(loader.error_registry, ErrorRegistry)
        assert isinstance(loader.object_registry, ObjectRegistry)

    def test_load_xmlstring_invalid_xml(self) -> None:
        """Test loading invalid XML string raises exception."""
        factory = Mock()
        loader = ProteusLoader(factory)

        invalid_xml = "<root><unclosed>"

        with pytest.raises(ET.ParseError):
            loader.load_xmlstring(invalid_xml)

    def test_load_xml_file_success(self) -> None:
        """Test successful XML file loading."""
        # Create mock factory and parser
        factory = Mock()
        parser = Mock()
        expected_model = Mock(spec=DexpiModel)

        factory.make_plant_model_parser.return_value = parser
        parser.compositional_pass.return_value = expected_model

        loader = ProteusLoader(factory)

        # Create temporary XML file
        xml_content = "<root><PlantModel></PlantModel></root>"

        with NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as tmp_file:
            tmp_file.write(xml_content)
            tmp_file_path = Path(tmp_file.name)

        try:
            result = loader.load_xml_file(tmp_file_path)

            # Verify the loading sequence
            factory.make_plant_model_parser.assert_called_once()
            parser.compositional_pass.assert_called_once()
            parser.reference_pass.assert_called_once()
            parser.control_pass.assert_called_once()

            assert result == expected_model
        finally:
            tmp_file_path.unlink()  # Clean up temp file

    def test_load_xml_file_nonexistent(self) -> None:
        """Test loading nonexistent file raises exception."""
        factory = Mock()
        loader = ProteusLoader(factory)

        nonexistent_path = Path("nonexistent_file.xml")

        with pytest.raises(FileNotFoundError):
            loader.load_xml_file(nonexistent_path)

    def test_get_error_registry(self) -> None:
        """Test getting error registry."""
        factory = Mock()
        loader = ProteusLoader(factory)

        loader.reset_registries()
        error_registry = loader.get_error_registry()

        assert error_registry == loader.error_registry
        assert isinstance(error_registry, ErrorRegistry)

    def test_get_error_registry_before_reset(self) -> None:
        """Test getting error registry before reset returns None."""
        factory = Mock()
        loader = ProteusLoader(factory)

        error_registry = loader.get_error_registry()
        assert error_registry is None

    def test_context_creation_in_load_xmlstring(self) -> None:
        """Test that proper context is created during XML string loading."""
        factory = Mock()
        parser = Mock()
        expected_model = Mock(spec=DexpiModel)

        factory.make_plant_model_parser.return_value = parser
        parser.compositional_pass.return_value = expected_model

        loader = ProteusLoader(factory)

        xml_string = "<TestRoot><PlantModel></PlantModel></TestRoot>"
        loader.load_xmlstring(xml_string)

        # Check that factory was called with correct context
        call_args = factory.make_plant_model_parser.call_args
        context = call_args[0][0]  # First argument
        element = call_args[0][1]  # Second argument

        assert isinstance(context, ModuleContext)
        assert context.element_stack == ["TestRoot"]
        assert context.id_stack == [None]
        assert isinstance(context.error_registry, ErrorRegistry)
        assert isinstance(context.object_registry, ObjectRegistry)
        assert element.tag == "TestRoot"

    def test_load_xml_as_bytes_success(self) -> None:
        """Test successful loading from bytes."""
        factory = Mock()
        parser = Mock()
        expected_model = Mock(spec=DexpiModel)

        factory.make_plant_model_parser.return_value = parser
        parser.compositional_pass.return_value = expected_model

        loader = ProteusLoader(factory)

        xml_bytes = b"<root><PlantModel></PlantModel></root>"
        result = loader.load_xml_as_bytes(xml_bytes)

        # Verify the loading sequence
        factory.make_plant_model_parser.assert_called_once()
        parser.compositional_pass.assert_called_once()
        parser.reference_pass.assert_called_once()
        parser.control_pass.assert_called_once()
        parser.drawing_pass.assert_called_once()
        parser.drawing_reference_pass.assert_called_once()

        assert result == expected_model
        assert isinstance(loader.error_registry, ErrorRegistry)
        assert isinstance(loader.object_registry, ObjectRegistry)

    def test_load_xml_as_bytes_with_encoding(self) -> None:
        """Test loading bytes with UTF-8 encoding."""
        factory = Mock()
        parser = Mock()
        expected_model = Mock(spec=DexpiModel)

        factory.make_plant_model_parser.return_value = parser
        parser.compositional_pass.return_value = expected_model

        loader = ProteusLoader(factory)

        # XML with special characters
        xml_bytes = b'<?xml version="1.0" encoding="UTF-8"?><root><PlantModel></PlantModel></root>'
        result = loader.load_xml_as_bytes(xml_bytes)

        assert result == expected_model

    def test_load_xml_as_bytes_invalid_xml(self) -> None:
        """Test loading invalid XML bytes raises exception."""
        factory = Mock()
        loader = ProteusLoader(factory)

        invalid_xml_bytes = b"<root><unclosed>"

        with pytest.raises(ET.ParseError):
            loader.load_xml_as_bytes(invalid_xml_bytes)

    def test_load_xml_from_stream_success(self) -> None:
        """Test successful loading from byte stream."""
        import io

        factory = Mock()
        parser = Mock()
        expected_model = Mock(spec=DexpiModel)

        factory.make_plant_model_parser.return_value = parser
        parser.compositional_pass.return_value = expected_model

        loader = ProteusLoader(factory)

        xml_content = b"<root><PlantModel></PlantModel></root>"
        stream = io.BytesIO(xml_content)

        result = loader.load_xml_from_stream(stream)

        # Verify the loading sequence
        factory.make_plant_model_parser.assert_called_once()
        parser.compositional_pass.assert_called_once()
        parser.reference_pass.assert_called_once()
        parser.control_pass.assert_called_once()
        parser.drawing_pass.assert_called_once()
        parser.drawing_reference_pass.assert_called_once()

        assert result == expected_model
        assert isinstance(loader.error_registry, ErrorRegistry)
        assert isinstance(loader.object_registry, ObjectRegistry)

    def test_load_xml_from_stream_multiple_reads(self) -> None:
        """Test loading from stream can be called multiple times."""
        import io

        factory = Mock()
        parser = Mock()
        expected_model = Mock(spec=DexpiModel)

        factory.make_plant_model_parser.return_value = parser
        parser.compositional_pass.return_value = expected_model

        loader = ProteusLoader(factory)

        xml_content = b"<root><PlantModel></PlantModel></root>"

        # First load
        stream1 = io.BytesIO(xml_content)
        result1 = loader.load_xml_from_stream(stream1)

        # Second load
        stream2 = io.BytesIO(xml_content)
        result2 = loader.load_xml_from_stream(stream2)

        assert result1 == expected_model
        assert result2 == expected_model
        assert factory.make_plant_model_parser.call_count == 2

    def test_load_xml_from_stream_invalid_xml(self) -> None:
        """Test loading invalid XML from stream raises exception."""
        import io

        factory = Mock()
        loader = ProteusLoader(factory)

        invalid_xml = b"<root><unclosed>"
        stream = io.BytesIO(invalid_xml)

        with pytest.raises(ET.ParseError):
            loader.load_xml_from_stream(stream)

    def test_load_xml_as_bytes_vs_xmlstring_consistency(self) -> None:
        """Test that load_xml_as_bytes produces same result as load_xmlstring."""
        factory = Mock()
        parser = Mock()
        expected_model = Mock(spec=DexpiModel)

        factory.make_plant_model_parser.return_value = parser
        parser.compositional_pass.return_value = expected_model

        loader = ProteusLoader(factory)

        xml_string = "<root><PlantModel></PlantModel></root>"
        xml_bytes = xml_string.encode("utf-8")

        result_from_string = loader.load_xmlstring(xml_string)
        result_from_bytes = loader.load_xml_as_bytes(xml_bytes)

        assert result_from_string == expected_model
        assert result_from_bytes == expected_model

    def test_load_xml_from_stream_vs_as_bytes_consistency(self) -> None:
        """Test that load_xml_from_stream produces same result as load_xml_as_bytes."""
        import io

        factory = Mock()
        parser = Mock()
        expected_model = Mock(spec=DexpiModel)

        factory.make_plant_model_parser.return_value = parser
        parser.compositional_pass.return_value = expected_model

        loader = ProteusLoader(factory)

        xml_bytes = b"<root><PlantModel></PlantModel></root>"

        result_from_bytes = loader.load_xml_as_bytes(xml_bytes)

        stream = io.BytesIO(xml_bytes)
        result_from_stream = loader.load_xml_from_stream(stream)

        assert result_from_bytes == expected_model
        assert result_from_stream == expected_model


# Integration test to verify all components work together
class TestCoreIntegration:
    """Integration tests for core module components."""

    def test_full_workflow_simulation(self) -> None:
        """Test a complete workflow simulation with all core components."""
        # Create registries
        error_registry = ErrorRegistry()
        object_registry = ObjectRegistry()

        # Create context
        context = ModuleContext(
            element_stack=["root"],
            id_stack=["root-id"],
            error_registry=error_registry,
            object_registry=object_registry,
        )

        # Create parser module
        module = ConcreteParserModule(context)

        # Register some test objects
        test_obj1 = Mock(spec=DexpiBaseModel)
        test_obj2 = Mock(spec=DexpiBaseModel)

        module.register_object("obj1", test_obj1)
        module.register_object("obj2", test_obj2)

        # Register some errors
        module.register_error("Warning message", ErrorLevels.WARNING)
        module.register_error("Error message", ErrorLevels.ERROR, proteus_id="custom-id")

        # Verify objects are registered
        assert module.get_object_from_registry("obj1") == test_obj1
        assert module.get_object_from_registry("obj2") == test_obj2

        # Verify errors are registered
        errors = error_registry.get_errors()
        assert len(errors) == 2
        assert errors[0].level == ErrorLevels.WARNING
        assert errors[0].proteus_id == "root-id"  # Inferred from context
        assert errors[1].level == ErrorLevels.ERROR
        assert errors[1].proteus_id == "custom-id"  # Explicit ID

        # Test compositional pass
        result = module.compositional_pass()
        assert result == "test_result"

    def test_context_propagation(self) -> None:
        """Test that context is properly propagated through updates."""
        error_registry = ErrorRegistry()
        object_registry = ObjectRegistry()

        # Create initial context
        context = ModuleContext(
            element_stack=["root"],
            id_stack=["root-id"],
            error_registry=error_registry,
            object_registry=object_registry,
        )

        # Create XML elements to simulate hierarchy
        child_element = ET.Element("child")
        child_element.set("ID", "child-id")

        grandchild_element = ET.Element("grandchild")
        # No ID for grandchild

        # Update context through hierarchy
        child_context = context.get_updated_context(child_element)
        grandchild_context = child_context.get_updated_context(grandchild_element)

        # Verify context stack progression
        assert context.element_stack == ["root"]
        assert context.id_stack == ["root-id"]

        assert child_context.element_stack == ["root", "child"]
        assert child_context.id_stack == ["root-id", "child-id"]

        assert grandchild_context.element_stack == ["root", "child", "grandchild"]
        assert grandchild_context.id_stack == ["root-id", "child-id", None]

        # Verify shared registries
        assert child_context.error_registry == error_registry
        assert child_context.object_registry == object_registry
        assert grandchild_context.error_registry == error_registry
        assert grandchild_context.object_registry == object_registry

        # Test ID resolution at different levels
        assert context.get_last_id() == "root-id"
        assert child_context.get_last_id() == "child-id"
        assert grandchild_context.get_last_id() == "child-id"  # Should skip None
