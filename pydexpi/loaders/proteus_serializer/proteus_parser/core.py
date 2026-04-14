"""Core module for the framework of loading the Proteus XML format.

The proteus loading is built as a modular framework. This allows for easy
extension and customization of the loading process. This may be necessary for differently structured
or incorrectly structured Proteus XML files.

The core component of the framework is the `LoaderModule` class. This abstract base class defines
the module interface for loading specific XML elements. Each module is responsible for
handling a specific XML element type and how the data of its contained modules is integrated.
Note that the loader module is responsible for calling the compositional and reference passes of its
submodules at the appropriate time. All created objects are registered in the central
`ObjectRegistry` for later reference resolution, and errors are collected in the central
`ErrorRegistry`.

The loading process consists of three main passes:
1. **Compositional Pass**: creates the object and all compositional relationships between them.
2. **Reference Pass**: Resolves all remaining references between objects. This is done after
   all objects have been created, allowing for a complete view of the object graph.
3. **Control Pass**: Checks the consistency of duplicate information, e.g. object associations.

To facilitate modularity, the loader modules are instantiated by a `ParserFactory`, which is
responsible for creating the appropriate loader module based on the XML element type and plugging
it into parent parsers during construction.

Loading is orchestrated by the `ProteusLoader` class, which uses the `ParserFactory` to create the
top-level model parser for a Proteus XML. It can be used to load XML strings or files.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import IO, Any, Protocol
from xml.etree.ElementTree import Element

from defusedxml import ElementTree as ET

from pydexpi.dexpi_classes.pydantic_classes import DexpiBaseModel, DexpiModel


class InternalParserError(Exception):
    """Custom exception for internal parser errors.

    This exception is raised when an error occurs during the parsing process that is not
    directly related to the XML structure or data, but rather to the internal logic of the parser.

    If this exception is raised, it indicates a bug in the parser code that needs to be fixed, and
    should therefore not be caught by the parser.
    """


class ErrorLevels(Enum):
    """Enumeration of error severity levels for the Proteus serializer.

    This enum defines the different levels of errors that can occur
    during the parsing and serialization process.

    Levels:
    - INFO: Informational messages. Non-critical for logging.
    - WARNING: Indicates a potential issue or inconsistency, but no loss of DEXPI data.
    - ERROR: Indicates an error that causes a local loss of DEXPI data, due to missing data or
             malformed XML element.
    - CRITICAL: Indicates a severe error that prevents loading the model entirely.
    """

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ErrorRegistryEntry:
    """Data class representing an error entry in the error registry.

    Parameters
    ----------
    message : str
        Human-readable error message
    level : ErrorLevels
        Severity level of the error
    proteus_id : str or None, optional
        Proteus element ID associated with the error if available, by default None
    exception : Exception or None, optional
        The exception that caused the error, if applicable, by default None
    """

    message: str
    level: ErrorLevels
    proteus_id: str | None = None
    exception: Exception | None = None


class ErrorRegistry:
    """Registry for collecting and managing errors during serialization.

    This class provides a centralized way to collect, store, and retrieve
    errors that occur during the parsing and serialization process.
    """

    def __init__(self) -> None:
        """Initialize an empty error registry."""
        self.errors = []

    def register_error(self, error: ErrorRegistryEntry) -> None:
        """Register a new error in the registry.

        This method enables centralized error registration. It keeps track of all errors and
        centrally handles InternalParserErrors, which are automatically reraised.

        Parameters
        ----------
        error : ErrorRegistryEntry
            The error entry to register
        """
        self.errors.append(error)
        if isinstance(error.exception, InternalParserError):
            # If the error is an InternalParserError, it should not be caught by the parser.
            raise error.exception

    def get_errors(self, levels: list[ErrorLevels] = None) -> list[ErrorRegistryEntry]:
        """Retrieve all registered errors.

        Parameters
        ----------
        levels : list[ErrorLevels] or None, optional
            If provided, filter errors by their severity level. If None, return all errors.
            Defaults to None.

        Returns
        -------
        list[ErrorRegistryEntry]
            List of all error entries in the registry
        """
        if levels is None:
            return self.errors
        else:
            return [error for error in self.errors if error.level in levels]


class ObjectRegistry:
    """Registry for managing objects created during serialization.

    This class provides a way to store and retrieve objects by their Proteus IDs, enabling reference
    resolution during deserialization.
    """

    def __init__(self) -> None:
        """Initialize an empty object registry."""
        self.objects = {}

    def register_object(self, proteus_id: str, obj: Any) -> None:
        """Register an object in the registry with its Proteus ID.

        Parameters
        ----------
        proteus_id : str
            The Proteus ID to associate with the object
        obj : Any
            The object to register
        """
        self.objects[proteus_id] = obj

    def get_object(self, proteus_id: str) -> Any | None:
        """Retrieve an object by its Proteus ID.

        Parameters
        ----------
        proteus_id : str
            The Proteus ID of the object to retrieve

        Returns
        -------
        Any
            The object associated with the ID, or None if not found
        """
        return self.objects.get(proteus_id)


@dataclass
class ModuleContext:
    """Data class representing the context for a module.

    This class encapsulates the necessary context information for a loader module,
    including the element stack, factory dispatcher, error registry, and object registry.

    Parameters
    ----------
    element_stack : list[str]
        Stack of XML element tags representing the current parsing context.
    id_stack : list[str]
        Stack of Proteus IDs for the current parsing context.
    error_registry : ErrorRegistry
        Registry for collecting errors during loading
    object_registry : ObjectRegistry
        Registry for managing created objects during loading
    """

    element_stack: list[str]
    id_stack: list[str]
    error_registry: ErrorRegistry
    object_registry: ObjectRegistry

    def get_updated_context(self, element: Element) -> "ModuleContext":
        """Create a new ModuleContext with the current element and ID appended to the stacks.

        Parameters
        ----------
        element : Element
            The XML element being processed

        Returns
        -------
        ModuleContext
            A new ModuleContext instance with updated element and ID stacks.
        """
        return ModuleContext(
            element_stack=self.element_stack + [element.tag],
            id_stack=self.id_stack + [element.get("ID", None)],
            error_registry=self.error_registry,
            object_registry=self.object_registry,
        )

    def get_last_id(self) -> str | None:
        """Get the last ID in the ID stack that isn't None.

        Returns
        -------
        str | None
            The last ID in the stack, or None if the stack is empty.
        """
        for id in reversed(self.id_stack):
            if id is not None:
                return id
        raise ValueError("ID stack is empty or contains only None values.")

    def register_error(
        self, message: str, level: ErrorLevels, proteus_id: str = None, exception: Exception = None
    ) -> None:
        """Register an error with the error registry.

        Parameters
        ----------
        message : str
            Human-readable error message describing the issue
        level : ErrorLevels
            The severity level of the error
        proteus_id : str
            Optional ID associated with the Proteus element that caused the error. If not provided,
            the last ID from the context's ID stack is used.
        exception : Exception
            Optional exception instance related to the error
        """
        if proteus_id is None:
            try:
                proteus_id = self.get_last_id()
            except ValueError:
                proteus_id = None
        new_error = ErrorRegistryEntry(
            message=message,
            level=level,
            proteus_id=proteus_id,
            exception=exception,
        )
        self.error_registry.register_error(new_error)


class ParserModule(ABC):
    """Abstract base class for XML element loader modules.

    This class defines the interface for modules that handle the loading and processing of specific
    XML elements during deserialization. Also includes some utilities for handling the context.

    Attributes
    ----------
    context : ModuleContext
        The context containing the ID-, and element stack, error-, and object registry.
    """

    def __init__(
        self,
        context: ModuleContext,
    ) -> None:
        """Initialize a loader module.

        Parameters
        ----------
        context : ModuleContext
            The context containing the ID-, and element stack, error-, and object registry.
        """
        self.context = context
        self.submodules: list[ParserModule] = []

    @abstractmethod
    def compositional_pass(self) -> Any:
        """Perform the compositional pass of loading.

        This method handles the creation of objects and their compositional relationships during the
        first pass of deserialization.

        Returns
        -------
        Any
            The created object or result of the compositional pass
        """

    def reference_pass(self) -> None:
        """Perform the reference pass of loading.

        This method handles the resolution of object references during the second pass of
        deserialization. Implementation optional, as some modules may not require a reference pass.

        By default, calls the `reference_pass` method of all submodules.
        """
        for submodule in self.submodules:
            submodule.reference_pass()

    def control_pass(self) -> None:
        """This, final pass of the loading process checks the consistency of duplicate info.

        Some information is stored redundantly in the XML file, e.g. object associations. This pass
        checks that the duplicate information is consistent/tries to use the reduntant information
        to fill in missing information.

        By default, this method calls the `control_pass` method of all submodules.
        """
        for submodule in self.submodules:
            submodule.control_pass()

    def drawing_pass(self) -> Any:
        """Perform the drawing pass of loading.

        This method handles the extraction and processing of graphical information during the
        drawing pass of deserialization. Implementation optional, as some modules may not require a
        drawing pass.

        By default, calls the `drawing_pass` method of all submodules.

        Returns
        -------
        Graphics
            The created Graphics object or result of the drawing pass
        """
        for submodule in self.submodules:
            submodule.drawing_pass()

    def drawing_reference_pass(self) -> None:
        """Perform the drawing reference pass to resolve graphical references.

        This method handles the resolution of graphical references during the drawing reference
        pass of deserialization. Implementation optional, as some modules may not require a drawing
        reference pass.

        By default, calls the `drawing_reference_pass` method of all submodules.
        """
        for submodule in self.submodules:
            submodule.drawing_reference_pass()

    def register_submodule(self, submodule: "ParserModule") -> None:
        """Register a submodule for the current module.

        This method allows the module to keep track of its submodules, which can be used
        during the compositional, reference, and control passes.

        Parameters
        ----------
        submodule : ParserModule
            The submodule to register
        """
        self.submodules.append(submodule)

    def register_submodule_list(self, submodules: list["ParserModule"]) -> None:
        """Register a list of submodules for the current module.

        This method allows the module to register multiple submodules at once.

        Parameters
        ----------
        submodules : list[ParserModule]
            The list of submodules to register
        """
        for submodule in submodules:
            self.register_submodule(submodule)

    def register_error(
        self, message: str, level: ErrorLevels, proteus_id: str = None, exception: Exception = None
    ) -> None:
        """Register an error with the error registry.

        This method allows subclasses to register errors that occur during
        the loading process. It should be called whenever an error is encountered.

        Parameters
        ----------
        message : str
            Human-readable error message describing the issue
        level : ErrorLevels
            The severity level of the error
        proteus_id : str
            Optional ID associated with the Proteus element that caused the error. If not provided,
            the last ID from the context's ID stack is used.
        exception : Exception
            Optional exception instance related to the error
        """
        self.context.register_error(
            message=message,
            level=level,
            proteus_id=proteus_id,
            exception=exception,
        )

    def register_object(self, proteus_id: str, obj: DexpiBaseModel) -> None:
        """Register an object with the object registry.

        This method allows subclasses to register objects that are created during the loading
        process. It should be called whenever a new object is instantiated. That way, the object can
        be referenced later during the reference pass.

        Parameters
        ----------
        proteus_id : str
            The Proteus ID to associate with the object, used as key for later retrieval.
        obj : Any
            The object to register

        """
        self.context.object_registry.register_object(proteus_id=proteus_id, obj=obj)

    def get_object_from_registry(self, proteus_id: str) -> DexpiBaseModel | None:
        """Retrieve an object from the object registry by its Proteus ID.

        This method allows subclasses to access objects that have been registered
        during the loading process.

        Parameters
        ----------
        proteus_id : str
            The Proteus ID of the object to retrieve

        Returns
        -------
        DexpiBaseModel | None
            The object associated with the ID, or None if not found
        """
        return self.context.object_registry.get_object(proteus_id)


class PlantModelParserProtocol(Protocol):
    """Protocol for a parser that handles the entire plant model.

    This protocol defines the interface for a parser that processes the top-level plant model
    in a Proteus XML file. It includes methods for the compositional, reference, and control passes.
    """

    def compositional_pass(self) -> DexpiModel:
        """Perform the compositional pass of loading the plant model.

        Returns
        -------
        DexpiModel
            The created DEXPI model object
        """

    def reference_pass(self) -> None:
        """Perform the reference pass of loading the plant model to resolve references."""

    def control_pass(self) -> None:
        """Perform the control pass of loading the plant model to validate consistency."""

    def drawing_pass(self) -> None:
        """Perform the drawing pass of loading the plant model to extract graphical information."""

    def drawing_reference_pass(self) -> None:
        """Perform the drawing reference pass to resolve graphical references."""


class ParserFactoryProtocol(Protocol):
    """Protocol for a factory that creates parser modules for Proteus XML elements.

    This protocol defines the interface for creating parser modules based on the XML element type.
    It allows for flexible and modular parsing of different Proteus XML structures.
    """

    def make_plant_model_parser(
        self, context: ModuleContext, element: Element
    ) -> PlantModelParserProtocol:
        """Create a PlantModelParser for the given XML element and context.

        Parameters
        ----------
        context : ModuleContext
            The context in which the parser operates
        element : Element
            The XML element to parse


        Returns
        -------
        PlantModelParser
            An instance of PlantModelParser for the given element and context
        """


class ProteusLoader:
    """Main loader class for processing Proteus XML files.

    This class coordinates the loading process by calling the parser factory to create a top-level
    model parser
    """

    def __init__(self, parser_factory: ParserFactoryProtocol) -> None:
        """Initialize the Proteus loader.

        Parameters
        ----------
        parser_factory : ParserFactoryProtocol
            Factory for creating the set-up plant model parser
        """
        self.parser_factory = parser_factory
        self.error_registry = None
        self.object_registry = None

    def load_xmlstring(self, xml_string: str) -> DexpiModel:
        """Load and process an XML string.

        This method performs a three-pass loading process:
        1. Compositional pass: Creates objects and their composition relationships
        2. Reference pass: Resolves object references
        3. Control pass: Validates and finalizes the model
        4. Drawing pass: Extracts graphical information
        5. Drawing reference pass: Resolves graphical references

        Parameters
        ----------
        xml_string : str
            The XML content to parse and load

        Returns
        -------
        DexpiModel
            The loaded DEXPI model object
        """
        # Make a new error registry and object registry
        self.reset_registries()

        # Make a root context element for the xml
        root_element = ET.fromstring(xml_string)
        root_id = None
        root_context = ModuleContext(
            element_stack=[root_element.tag],
            id_stack=[root_id],
            error_registry=self.error_registry,
            object_registry=self.object_registry,
        )
        plant_model_parser = self.parser_factory.make_plant_model_parser(root_context, root_element)
        depxi_model = plant_model_parser.compositional_pass()
        plant_model_parser.reference_pass()
        plant_model_parser.control_pass()
        plant_model_parser.drawing_pass()
        plant_model_parser.drawing_reference_pass()

        return depxi_model

    def load_xml_as_bytes(self, xml_bytes: bytes) -> DexpiModel:
        """Load and process XML from bytes.

        This method performs a multi-pass loading process:
        1. Compositional pass: Creates objects and their composition relationships
        2. Reference pass: Resolves object references
        3. Control pass: Validates and finalizes the model
        4. Drawing pass: Extracts graphical information
        5. Drawing reference pass: Resolves graphical references

        Parameters
        ----------
        xml_bytes : bytes
            The XML content as bytes to parse and load

        Returns
        -------
        DexpiModel
            The loaded DEXPI model object
        """
        xml_string = xml_bytes.decode("utf-8")
        return self.load_xmlstring(xml_string)

    def load_xml_from_stream(self, stream: IO[bytes]) -> DexpiModel:
        """Load and process XML from a byte stream.

        This method performs a multi-pass loading process:
        1. Compositional pass: Creates objects and their composition relationships
        2. Reference pass: Resolves object references
        3. Control pass: Validates and finalizes the model
        4. Drawing pass: Extracts graphical information
        5. Drawing reference pass: Resolves graphical references

        Parameters
        ----------
        stream : IO[bytes]
            A readable binary stream containing XML content

        Returns
        -------
        DexpiModel
            The loaded DEXPI model object
        """
        xml_bytes = stream.read()
        return self.load_xml_as_bytes(xml_bytes)

    def load_xml_file(self, xml_file: Path) -> Any:
        """Load and process an XML file.

        This method performs a two-pass loading process:
        1. Compositional pass: Creates objects and their composition relationships
        2. Reference pass: Resolves object references
        3. Control pass: Validates and finalizes the model
        4. Drawing pass: Extracts graphical information
        5. Drawing reference pass: Resolves graphical references

        Parameters
        ----------
        xml_file : Path
            The path to the XML file to parse and load

        Returns
        -------
        Any
            The loaded DEXPI model object
        """
        with open(xml_file) as file:
            xml_string = file.read()

        return self.load_xmlstring(xml_string)

    def get_error_registry(self) -> ErrorRegistry:
        """Get the error registry containing any errors from the loading process.

        Returns
        -------
        ErrorRegistry
            The error registry with collected errors
        """
        return self.error_registry

    def reset_registries(self) -> None:
        """Reset the error and object registries to empty instances for a new loading process."""
        self.error_registry = ErrorRegistry()
        self.object_registry = ObjectRegistry()
