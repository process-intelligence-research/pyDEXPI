"""Core classes for the Proteus XML exporter.

This module defines the basic framework for exporting pydexpi modules to Proteus XML format.
The parsing framework is designed to be modular, allowing for clear separation of exporter logic,
mainly by element type. The exporter operates in several passes to ensure proper handling of
composition and references:
- During initialization, each module builds and registers its submodules internally.
- The compositional pass handles the export of objects and their direct subelements.
- The reference pass resolves references between objects and establishes the necessary associations.

Because there is less requirement for customizability, this framework does not rely on dependency
inversion and an external factory, unlike the parser framework."""

import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from dataclasses import dataclass

from pydexpi.dexpi_classes.pydantic_classes import DexpiBaseModel


class ElementRegistry:
    """Registry to keep track of XML elements by their IDs."""

    def __init__(self):
        self._registry: dict[str, ET.Element] = {}

    def register_element(self, dexpi_id: str, element: ET.Element) -> None:
        """Register an XML element with its ID.

        Parameters
        ----------
        dexpi_id : str
            The ID of the XML element
        element : ET.Element
            The XML element to register
        """
        self._registry[dexpi_id] = element

    def get_element(self, dexpi_id: str) -> ET.Element | None:
        """Retrieve an XML element by its dexpi ID.

        Parameters
        ----------
        dexpi_id : str
            The ID of the XML element to retrieve

        Returns
        -------
        ET.Element | None
            The XML element if found, else None
        """
        return self._registry.get(dexpi_id)


@dataclass
class ModuleContext:
    element_registry: ElementRegistry
    override_proteus_id: bool


class ExporterModule(ABC):
    """Abstract base class for XML exporter modules.

    This class defines the interface for modules that handle the export of DEXPI objects to
    Proteus XML elements.
    """

    def __init__(self, module_context: ModuleContext) -> None:
        """Initialize the exporter module.

        Parameters
        ----------
        module_context : ModuleContext
            The context for the exporter module, containing the element registry and other settings
        """
        self.module_context = module_context
        self.submodules: list[ExporterModule] = []

    @abstractmethod
    def compositional_pass(self) -> ET.Element:
        """Export a DEXPI object to an XML element.

        Parameters
        ----------
        obj : DexpiBaseModel
            The DEXPI object to export

        Returns
        -------
        ET.Element
            The XML element representing the object
        """
        pass

    def reference_pass(self) -> None:
        """Perform the reference pass of exporting.

        This method handles the resolution of object references during the second pass of
        serialization. Implementation optional, as some modules may not require a reference pass.

        By default, calls the `reference_pass` method of all submodules.
        """
        for submodule in self.submodules:
            submodule.reference_pass()

    def register_submodule(self, submodule: "ExporterModule") -> None:
        """Register a submodule for the current module.

        This method allows the module to keep track of its submodules, which can be used
        during the compositional, reference, and control passes.

        Parameters
        ----------
        submodule : ExporterModule
            The submodule to register
        """
        self.submodules.append(submodule)

    def register_submodule_list(self, submodules: list["ExporterModule"]) -> None:
        """Register a list of submodules.

        Parameters
        ----------
        submodules : list[ExporterModule]
            The list of submodules to register
        """
        for submodule in submodules:
            self.register_submodule(submodule)

    def register_object(self, dexpi_id: str, element: ET.Element) -> None:
        """Register an XML element with its dexpi ID in the registry.

        Parameters
        ----------
        dexpi_id : str
            The ID of the XML element
        element : ET.Element
            The XML element to register
        """
        self.module_context.element_registry.register_element(dexpi_id, element)

    def get_object_from_registry(self, dexpi_id: str) -> ET.Element | None:
        """Retrieve an XML element by its dexpi ID from the registry.

        Parameters
        ----------
        dexpi_id : str
            The ID of the XML element to retrieve

        Returns
        -------
        ET.Element | None
            The XML element if found, else None
        """
        return self.module_context.element_registry.get_element(dexpi_id)

    def make_id_attribute(self, dexpi_object: DexpiBaseModel) -> str:
        """Create the ID attribute for a DEXPI object.

        Parameters
        ----------
        dexpi_object : DexpiBaseModel
            The DEXPI object to create the ID attribute for

        Returns
        -------
        str
            The ID attribute string, or an empty string if not overriding Proteus IDs
        """
        if not self.module_context.override_proteus_id and dexpi_object.proteusId is not None:
            return dexpi_object.proteusId
        else:
            return f"{type(dexpi_object).__name__}-{dexpi_object.id}"
