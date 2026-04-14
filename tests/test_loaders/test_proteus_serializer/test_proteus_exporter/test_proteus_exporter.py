"""Tests for the top-level ProteusExporter class methods."""

import io
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from pydexpi.dexpi_classes.pydantic_classes import DexpiModel
from pydexpi.loaders.proteus_serializer.proteus_exporter.proteus_exporter import ProteusExporter


class TestProteusExporter:
    """Tests for the ProteusExporter class."""

    @pytest.fixture()
    def exporter(self) -> ProteusExporter:
        """Fixture to create a ProteusExporter instance.

        Returns
        -------
        ProteusExporter
            A ProteusExporter instance.
        """
        return ProteusExporter()

    @pytest.fixture()
    def simple_dexpi_model(self, simple_dexpi_model_factory) -> DexpiModel:
        """Fixture to create a simple DexpiModel instance.

        Returns
        -------
        DexpiModel
            A simple DexpiModel instance.
        """
        return simple_dexpi_model_factory()

    def test_export_xml_element(
        self, exporter: ProteusExporter, simple_dexpi_model: DexpiModel
    ) -> None:
        """Test that export_xml_element returns an XML element.

        Parameters
        ----------
        exporter : ProteusExporter
            The ProteusExporter instance.
        simple_dexpi_model : DexpiModel
            A simple DexpiModel instance.
        """
        xml_element = exporter.export_xml_element(simple_dexpi_model)

        assert isinstance(xml_element, ET.Element)
        assert xml_element.tag == "PlantModel"
        assert exporter.context is not None

    def test_export_xml_as_bytes(
        self, exporter: ProteusExporter, simple_dexpi_model: DexpiModel
    ) -> None:
        """Test that export_xml_as_bytes returns bytes.

        Parameters
        ----------
        exporter : ProteusExporter
            The ProteusExporter instance.
        simple_dexpi_model : DexpiModel
            A simple DexpiModel instance.
        """
        xml_bytes = exporter.export_xml_as_bytes(simple_dexpi_model)

        assert isinstance(xml_bytes, bytes)
        assert xml_bytes.startswith(b"<?xml")
        assert b"PlantModel" in xml_bytes
        # Verify it's valid XML by parsing it
        ET.fromstring(xml_bytes)

    def test_export_xml_as_bytes_pretty_formatted(
        self, exporter: ProteusExporter, simple_dexpi_model: DexpiModel
    ) -> None:
        """Test that export_xml_as_bytes returns pretty-formatted XML.

        Parameters
        ----------
        exporter : ProteusExporter
            The ProteusExporter instance.
        simple_dexpi_model : DexpiModel
            A simple DexpiModel instance.
        """
        xml_bytes = exporter.export_xml_as_bytes(simple_dexpi_model)

        # Check for indentation (pretty formatting)
        xml_str = xml_bytes.decode("utf-8")
        assert "  " in xml_str  # Contains indentation

    def test_export_xml_to_stream(
        self, exporter: ProteusExporter, simple_dexpi_model: DexpiModel
    ) -> None:
        """Test that export_xml_to_stream writes XML to a stream.

        Parameters
        ----------
        exporter : ProteusExporter
            The ProteusExporter instance.
        simple_dexpi_model : DexpiModel
            A simple DexpiModel instance.
        """
        stream = io.BytesIO()
        exporter.export_xml_to_stream(simple_dexpi_model, stream)

        # Get the content from the stream
        stream.seek(0)
        xml_bytes = stream.read()

        assert isinstance(xml_bytes, bytes)
        assert xml_bytes.startswith(b"<?xml")
        assert b"PlantModel" in xml_bytes
        # Verify it's valid XML by parsing it
        ET.fromstring(xml_bytes)

    def test_export_xml_to_stream_multiple_writes(
        self, exporter: ProteusExporter, simple_dexpi_model: DexpiModel
    ) -> None:
        """Test that export_xml_to_stream can be called multiple times.

        Parameters
        ----------
        exporter : ProteusExporter
            The ProteusExporter instance.
        simple_dexpi_model : DexpiModel
            A simple DexpiModel instance.
        """
        stream1 = io.BytesIO()
        stream2 = io.BytesIO()

        exporter.export_xml_to_stream(simple_dexpi_model, stream1)
        exporter.export_xml_to_stream(simple_dexpi_model, stream2)

        stream1.seek(0)
        stream2.seek(0)

        xml_bytes1 = stream1.read()
        xml_bytes2 = stream2.read()

        # Both should be valid and identical
        assert xml_bytes1 == xml_bytes2
        assert b"PlantModel" in xml_bytes1

    def test_export_xml_file(
        self, exporter: ProteusExporter, simple_dexpi_model: DexpiModel, tmp_path: Path
    ) -> None:
        """Test that export_xml_file writes XML to a file.

        Parameters
        ----------
        exporter : ProteusExporter
            The ProteusExporter instance.
        simple_dexpi_model : DexpiModel
            A simple DexpiModel instance.
        tmp_path : Path
            Temporary directory path provided by pytest.
        """
        output_file = tmp_path / "test_output.xml"
        exporter.export_xml_file(simple_dexpi_model, output_file)

        assert output_file.exists()

        # Read and verify the file content
        with open(output_file, "rb") as f:
            xml_bytes = f.read()

        assert xml_bytes.startswith(b"<?xml")
        assert b"PlantModel" in xml_bytes
        # Verify it's valid XML by parsing it
        ET.fromstring(xml_bytes)

    def test_export_xml_as_bytes_consistency(
        self, exporter: ProteusExporter, simple_dexpi_model: DexpiModel
    ) -> None:
        """Test that export_xml_as_bytes produces consistent output.

        Parameters
        ----------
        exporter : ProteusExporter
            The ProteusExporter instance.
        simple_dexpi_model : DexpiModel
            A simple DexpiModel instance.
        """
        xml_bytes1 = exporter.export_xml_as_bytes(simple_dexpi_model)
        xml_bytes2 = exporter.export_xml_as_bytes(simple_dexpi_model)

        assert xml_bytes1 == xml_bytes2

    def test_export_xml_to_stream_vs_as_bytes(
        self, exporter: ProteusExporter, simple_dexpi_model: DexpiModel
    ) -> None:
        """Test that export_xml_to_stream produces same output as export_xml_as_bytes.

        Parameters
        ----------
        exporter : ProteusExporter
            The ProteusExporter instance.
        simple_dexpi_model : DexpiModel
            A simple DexpiModel instance.
        """
        # Get bytes directly
        xml_bytes = exporter.export_xml_as_bytes(simple_dexpi_model)

        # Get bytes via stream
        stream = io.BytesIO()
        exporter.export_xml_to_stream(simple_dexpi_model, stream)
        stream.seek(0)
        stream_bytes = stream.read()

        assert xml_bytes == stream_bytes

    def test_export_xml_file_vs_as_bytes(
        self, exporter: ProteusExporter, simple_dexpi_model: DexpiModel, tmp_path: Path
    ) -> None:
        """Test that export_xml_file produces same output as export_xml_as_bytes.

        Parameters
        ----------
        exporter : ProteusExporter
            The ProteusExporter instance.
        simple_dexpi_model : DexpiModel
            A simple DexpiModel instance.
        tmp_path : Path
            Temporary directory path provided by pytest.
        """
        # Get bytes directly
        xml_bytes = exporter.export_xml_as_bytes(simple_dexpi_model)

        # Get bytes via file
        output_file = tmp_path / "test_output.xml"
        exporter.export_xml_file(simple_dexpi_model, output_file)

        with open(output_file, "rb") as f:
            file_bytes = f.read()

        assert xml_bytes == file_bytes

    def test_exporter_with_override_export_info(self, simple_dexpi_model: DexpiModel) -> None:
        """Test that override_export_info flag is passed correctly.

        Parameters
        ----------
        simple_dexpi_model : DexpiModel
            A simple DexpiModel instance.
        """
        exporter = ProteusExporter(override_export_info=True)
        xml_bytes = exporter.export_xml_as_bytes(simple_dexpi_model)

        assert isinstance(xml_bytes, bytes)
        assert b"PlantModel" in xml_bytes

    def test_exporter_with_override_proteus_id(self, simple_dexpi_model: DexpiModel) -> None:
        """Test that override_proteus_id flag is passed correctly.

        Parameters
        ----------
        simple_dexpi_model : DexpiModel
            A simple DexpiModel instance.
        """
        exporter = ProteusExporter(override_proteus_id=True)
        xml_bytes = exporter.export_xml_as_bytes(simple_dexpi_model)

        assert isinstance(xml_bytes, bytes)
        assert b"PlantModel" in xml_bytes
        assert exporter.context is not None
        assert exporter.context.override_proteus_id is True

    def test_export_xml_as_bytes_not_pretty(
        self, exporter: ProteusExporter, simple_dexpi_model: DexpiModel
    ) -> None:
        """Test that export_xml_as_bytes with pretty=False produces compact XML.

        Parameters
        ----------
        exporter : ProteusExporter
            The ProteusExporter instance.
        simple_dexpi_model : DexpiModel
            A simple DexpiModel instance.
        """
        xml_bytes = exporter.export_xml_as_bytes(simple_dexpi_model, pretty=False)

        assert isinstance(xml_bytes, bytes)
        assert xml_bytes.startswith(b"<?xml")
        assert b"PlantModel" in xml_bytes
        # Verify it's valid XML by parsing it
        ET.fromstring(xml_bytes)

        # Check that it's compact (no multi-space indentation)
        xml_str = xml_bytes.decode("utf-8")
        # Should not contain double-space indentation patterns
        assert "  <" not in xml_str or xml_str.count("  <") < 5  # Allow minimal spacing

    def test_export_xml_as_bytes_pretty_vs_not_pretty(
        self, exporter: ProteusExporter, simple_dexpi_model: DexpiModel
    ) -> None:
        """Test that pretty and non-pretty outputs are different.

        Parameters
        ----------
        exporter : ProteusExporter
            The ProteusExporter instance.
        simple_dexpi_model : DexpiModel
            A simple DexpiModel instance.
        """
        pretty_bytes = exporter.export_xml_as_bytes(simple_dexpi_model, pretty=True)
        compact_bytes = exporter.export_xml_as_bytes(simple_dexpi_model, pretty=False)

        # They should be different
        assert pretty_bytes != compact_bytes

        # Pretty version should be longer due to whitespace
        assert len(pretty_bytes) > len(compact_bytes)

        # Both should be valid XML
        ET.fromstring(pretty_bytes)
        ET.fromstring(compact_bytes)

    def test_export_xml_to_stream_not_pretty(
        self, exporter: ProteusExporter, simple_dexpi_model: DexpiModel
    ) -> None:
        """Test that export_xml_to_stream with pretty=False produces compact XML.

        Parameters
        ----------
        exporter : ProteusExporter
            The ProteusExporter instance.
        simple_dexpi_model : DexpiModel
            A simple DexpiModel instance.
        """
        stream = io.BytesIO()
        exporter.export_xml_to_stream(simple_dexpi_model, stream, pretty=False)

        stream.seek(0)
        xml_bytes = stream.read()

        assert isinstance(xml_bytes, bytes)
        assert xml_bytes.startswith(b"<?xml")
        assert b"PlantModel" in xml_bytes
        # Verify it's valid XML by parsing it
        ET.fromstring(xml_bytes)

        # Check that it's compact
        xml_str = xml_bytes.decode("utf-8")
        assert "  <" not in xml_str or xml_str.count("  <") < 5

    def test_export_xml_to_stream_pretty_parameter(
        self, exporter: ProteusExporter, simple_dexpi_model: DexpiModel
    ) -> None:
        """Test that export_xml_to_stream respects the pretty parameter.

        Parameters
        ----------
        exporter : ProteusExporter
            The ProteusExporter instance.
        simple_dexpi_model : DexpiModel
            A simple DexpiModel instance.
        """
        pretty_stream = io.BytesIO()
        compact_stream = io.BytesIO()

        exporter.export_xml_to_stream(simple_dexpi_model, pretty_stream, pretty=True)
        exporter.export_xml_to_stream(simple_dexpi_model, compact_stream, pretty=False)

        pretty_stream.seek(0)
        compact_stream.seek(0)

        pretty_bytes = pretty_stream.read()
        compact_bytes = compact_stream.read()

        # They should be different
        assert pretty_bytes != compact_bytes
        assert len(pretty_bytes) > len(compact_bytes)

        # Both should be valid XML
        ET.fromstring(pretty_bytes)
        ET.fromstring(compact_bytes)

    def test_export_xml_file_not_pretty(
        self, exporter: ProteusExporter, simple_dexpi_model: DexpiModel, tmp_path: Path
    ) -> None:
        """Test that export_xml_file with pretty=False produces compact XML.

        Parameters
        ----------
        exporter : ProteusExporter
            The ProteusExporter instance.
        simple_dexpi_model : DexpiModel
            A simple DexpiModel instance.
        tmp_path : Path
            Temporary directory path provided by pytest.
        """
        output_file = tmp_path / "test_output_compact.xml"
        exporter.export_xml_file(simple_dexpi_model, output_file, pretty=False)

        assert output_file.exists()

        with open(output_file, "rb") as f:
            xml_bytes = f.read()

        assert xml_bytes.startswith(b"<?xml")
        assert b"PlantModel" in xml_bytes
        # Verify it's valid XML by parsing it
        ET.fromstring(xml_bytes)

        # Check that it's compact
        xml_str = xml_bytes.decode("utf-8")
        assert "  <" not in xml_str or xml_str.count("  <") < 5

    def test_export_xml_file_pretty_parameter(
        self, exporter: ProteusExporter, simple_dexpi_model: DexpiModel, tmp_path: Path
    ) -> None:
        """Test that export_xml_file respects the pretty parameter.

        Parameters
        ----------
        exporter : ProteusExporter
            The ProteusExporter instance.
        simple_dexpi_model : DexpiModel
            A simple DexpiModel instance.
        tmp_path : Path
            Temporary directory path provided by pytest.
        """
        pretty_file = tmp_path / "test_pretty.xml"
        compact_file = tmp_path / "test_compact.xml"

        exporter.export_xml_file(simple_dexpi_model, pretty_file, pretty=True)
        exporter.export_xml_file(simple_dexpi_model, compact_file, pretty=False)

        with open(pretty_file, "rb") as f:
            pretty_bytes = f.read()

        with open(compact_file, "rb") as f:
            compact_bytes = f.read()

        # They should be different
        assert pretty_bytes != compact_bytes
        assert len(pretty_bytes) > len(compact_bytes)

        # Both should be valid XML
        ET.fromstring(pretty_bytes)
        ET.fromstring(compact_bytes)
