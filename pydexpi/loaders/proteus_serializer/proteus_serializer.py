from pathlib import Path
from typing import IO

from pydexpi.dexpi_classes.pydantic_classes import DexpiModel
from pydexpi.loaders.proteus_serializer.proteus_exporter.proteus_exporter import ProteusExporter
from pydexpi.loaders.proteus_serializer.proteus_parser import (
    ParserFactory,
    ParserFactoryProtocol,
    ProteusLoader,
)
from pydexpi.loaders.proteus_serializer.proteus_parser.core import ErrorRegistry
from pydexpi.loaders.serializer import Serializer


class ProteusSerializer(Serializer):
    """Main class for the Proteus Serializer that implements the Serializer interface."""

    def __init__(
        self,
        parser_factory: ParserFactoryProtocol = None,
        override_proteus_id: bool = False,
        override_export_info: bool = False,
    ):
        """Initialize the ProteusSerializer with a parser factory.

        Parameters
        ----------
        parser_factory : ParserFactoryProtocol, optional
            A factory to create parsers for the ProteusLoader. If not provided, a default
            ParserFactory instance will be used.
        override_proteus_id : bool, optional
            Whether to override the Proteus ID in the exported XML, by default False
        override_export_info : bool, optional
            Whether to override export information in the PlantInformation element, by default False
        """

        parser_factory = parser_factory or ParserFactory()
        self.proteus_loader = ProteusLoader(parser_factory)
        self.proteus_exporter = ProteusExporter(
            override_export_info=override_export_info, override_proteus_id=override_proteus_id
        )

    def save(self, model: DexpiModel, dir_path: Path, filename: str, pretty: bool = True) -> None:
        """Saves a DEXPI model to a file using the ProteusExporter.

        Parameters
        ----------
        model : DexpiModel
            The DEXPI model to save.
        dir_path : Path
            The directory path where the file should be saved.
        filename : str
            The name of the file to save (will add .xml extension if not present).
        pretty : bool, optional
            Whether to pretty-format the XML, by default True
        """
        if not filename.endswith(".xml"):
            filename += ".xml"
        path = Path(dir_path) / filename

        self.proteus_exporter.export_xml_file(model, path, pretty=pretty)

    def load(self, dir_path: Path, filename: str) -> DexpiModel:
        """Loads a DEXPI model from a file using the ProteusLoader.

        Parameters
        ----------
        dir_path : Path
            The directory path where the file is located.
        filename : str
            The name of the file to load.

        Returns
        -------
        DexpiModel
            The loaded DEXPI model.
        """
        if not filename.endswith(".xml"):
            filename += ".xml"
        path = Path(dir_path) / filename

        return self.proteus_loader.load_xml_file(path)

    def load_from_bytes(self, xml_bytes: bytes) -> DexpiModel:
        """Loads a DEXPI model from bytes.

        Parameters
        ----------
        xml_bytes : bytes
            The XML content as bytes to load.

        Returns
        -------
        DexpiModel
            The loaded DEXPI model.
        """
        return self.proteus_loader.load_xml_as_bytes(xml_bytes)

    def load_from_stream(self, stream: IO[bytes]) -> DexpiModel:
        """Loads a DEXPI model from a byte stream.

        Parameters
        ----------
        stream : IO[bytes]
            A readable binary stream containing XML content.

        Returns
        -------
        DexpiModel
            The loaded DEXPI model.
        """
        return self.proteus_loader.load_xml_from_stream(stream)

    def load_from_string(self, xml_string: str) -> DexpiModel:
        """Loads a DEXPI model from an XML string.

        Parameters
        ----------
        xml_string : str
            The XML content as a string to load.

        Returns
        -------
        DexpiModel
            The loaded DEXPI model.
        """
        return self.proteus_loader.load_xmlstring(xml_string)

    def export_to_bytes(self, model: DexpiModel, pretty: bool = True) -> bytes:
        """Exports a DEXPI model to bytes.

        Parameters
        ----------
        model : DexpiModel
            The DEXPI model to export.
        pretty : bool, optional
            Whether to pretty-format the XML, by default True

        Returns
        -------
        bytes
            The exported Proteus XML as bytes.
        """
        return self.proteus_exporter.export_xml_as_bytes(model, pretty=pretty)

    def export_to_stream(self, model: DexpiModel, stream: IO[bytes], pretty: bool = True) -> None:
        """Exports a DEXPI model to a byte stream.

        Parameters
        ----------
        model : DexpiModel
            The DEXPI model to export.
        stream : IO[bytes]
            The output stream to write the XML to.
        pretty : bool, optional
            Whether to pretty-format the XML, by default True
        """
        self.proteus_exporter.export_xml_to_stream(model, stream, pretty=pretty)

    def get_loading_errors(self) -> ErrorRegistry:
        """Returns the error registry containing any errors encountered during loading.

        Returns
        -------
        ErrorRegistry
            The error registry with loading errors.
        """
        return self.proteus_loader.get_error_registry()
