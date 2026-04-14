"""Module containing the top-level ProteusExporter class."""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import IO
from xml.dom import minidom

from pydexpi.dexpi_classes.pydantic_classes import DexpiModel
from pydexpi.loaders.proteus_serializer.proteus_exporter.core import ElementRegistry, ModuleContext
from pydexpi.loaders.proteus_serializer.proteus_exporter.exporter_modules import PlantModelExporter


class ProteusExporter:
    """Class for exporting DEXPI models to Proteus XML format.

    This class provides methods to export a DEXPI model to an XML element or directly to an XML
    file. Keeps the last ElementRegistry used for exporting for later reference.

    Attributes
    ----------
    context : ModuleContext | None
        The module context used by all modules during export.
    """

    def __init__(self, override_export_info: bool = False, override_proteus_id: bool = False):
        """Initialize the ProteusExporter.

        Parameters
        ----------
        override_export_info : bool, optional
            Whether to override export information in the PlantInformation element,
            by default False
        override_proteus_id : bool, optional
            Whether to override the Proteus ID in the exported XML, by default False
        """
        self.context = None
        self.override_export_info = override_export_info
        self.override_proteus_id = override_proteus_id

    def export_xml_element(self, dexpi_model: DexpiModel) -> ET.Element:
        """Export the given DEXPI model to a Proteus XML element.

        Parameters
        ----------
        dexpi_model : DexpiModel
            The DEXPI model to export.

        Returns
        -------
        str
            The exported Proteus XML string.
        """
        element_registry = ElementRegistry()
        self.context = ModuleContext(
            element_registry=element_registry, override_proteus_id=self.override_proteus_id
        )
        plant_model_exporter = PlantModelExporter(
            self.context,
            dexpi_model,
            override_export_info=self.override_export_info,
        )

        plant_model_xml = plant_model_exporter.compositional_pass()
        plant_model_exporter.reference_pass()

        return plant_model_xml

    def export_xml_as_bytes(self, dexpi_model: DexpiModel, pretty: bool = True) -> bytes:
        """Export the given DEXPI model to a Proteus XML as bytes.

        Parameters
        ----------
        dexpi_model : DexpiModel
            The DEXPI model to export.
        pretty : bool, optional
            Whether to pretty-format the XML, by default True

        Returns
        -------
        bytes
            The exported Proteus XML as bytes.
        """
        xml_element = self.export_xml_element(dexpi_model)
        raw_bytes = ET.tostring(xml_element, encoding="utf-8", xml_declaration=True)
        if pretty:
            try:
                pretty_bytes = minidom.parseString(raw_bytes).toprettyxml(
                    indent="  ", encoding="utf-8"
                )
            except Exception:
                pretty_bytes = raw_bytes
            return pretty_bytes
        return raw_bytes

    def export_xml_to_stream(
        self, dexpi_model: DexpiModel, stream: IO[bytes], pretty: bool = True
    ) -> None:
        """Export the given DEXPI model to a Proteus XML and write it to a stream.

        Parameters
        ----------
        dexpi_model : DexpiModel
            The DEXPI model to export.
        stream : IO[bytes]
            The output stream to write the XML to.
        pretty : bool, optional
            Whether to pretty-format the XML, by default True
        """
        dexpi_bytes = self.export_xml_as_bytes(dexpi_model, pretty=pretty)
        stream.write(dexpi_bytes)

    def export_xml_file(self, dexpi_model, path: Path, pretty: bool = True) -> None:
        """Export the given DEXPI model to a Proteus XML file.

        Parameters
        ----------
        dexpi_model : DexpiModel
            The DEXPI model to export.
        path : Path
            The path to the output XML file.
        pretty : bool, optional
            Whether to pretty-format the XML, by default True
        """
        dexpi_bytes = self.export_xml_as_bytes(dexpi_model, pretty=pretty)
        with open(path, "wb") as f:
            f.write(dexpi_bytes)
