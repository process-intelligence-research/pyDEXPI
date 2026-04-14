"""Tests for the ProteusSerializer class top-level methods."""

import io
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from pydexpi.dexpi_classes.pydantic_classes import DexpiModel
from pydexpi.loaders.proteus_serializer import ProteusSerializer
from pydexpi.loaders.proteus_serializer.proteus_parser.core import ErrorRegistry


class TestProteusSerializer:
    """Tests for the ProteusSerializer class."""

    @pytest.fixture()
    def serializer(self) -> ProteusSerializer:
        """Fixture to create a ProteusSerializer instance.

        Returns
        -------
        ProteusSerializer
            A ProteusSerializer instance.
        """
        return ProteusSerializer()

    @pytest.fixture()
    def simple_dexpi_model(self, simple_dexpi_model_factory) -> DexpiModel:
        """Fixture to create a simple DexpiModel instance.

        Returns
        -------
        DexpiModel
            A simple DexpiModel instance.
        """
        return simple_dexpi_model_factory()

    def test_initialization(self) -> None:
        """Test ProteusSerializer initialization."""
        serializer = ProteusSerializer()

        assert serializer.proteus_loader is not None
        assert serializer.proteus_exporter is not None

    def test_initialization_with_override_flags(self) -> None:
        """Test ProteusSerializer initialization with override flags."""
        serializer = ProteusSerializer(override_proteus_id=True, override_export_info=True)

        assert serializer.proteus_exporter.override_proteus_id is True
        assert serializer.proteus_exporter.override_export_info is True

    def test_save_and_load(
        self, serializer: ProteusSerializer, simple_dexpi_model: DexpiModel
    ) -> None:
        """Test save and load round-trip.

        Parameters
        ----------
        serializer : ProteusSerializer
            The ProteusSerializer instance.
        simple_dexpi_model : DexpiModel
            A simple DexpiModel instance.
        """
        with TemporaryDirectory() as tmpdir:
            dir_path = Path(tmpdir)
            filename = "test_model.xml"

            # Save the model
            serializer.save(simple_dexpi_model, dir_path, filename)

            # Verify file was created
            file_path = dir_path / filename
            assert file_path.exists()

            # Load the model back
            loaded_model = serializer.load(dir_path, filename)

            # Verify it's a DexpiModel
            assert isinstance(loaded_model, DexpiModel)
            assert loaded_model.originatingSystemName == simple_dexpi_model.originatingSystemName

    def test_save_without_xml_extension(
        self, serializer: ProteusSerializer, simple_dexpi_model: DexpiModel
    ) -> None:
        """Test save automatically adds .xml extension.

        Parameters
        ----------
        serializer : ProteusSerializer
            The ProteusSerializer instance.
        simple_dexpi_model : DexpiModel
            A simple DexpiModel instance.
        """
        with TemporaryDirectory() as tmpdir:
            dir_path = Path(tmpdir)
            filename = "test_model"  # No .xml extension

            serializer.save(simple_dexpi_model, dir_path, filename)

            # Verify file with .xml extension exists
            file_path = dir_path / "test_model.xml"
            assert file_path.exists()

    def test_save_with_pretty_parameter(
        self, serializer: ProteusSerializer, simple_dexpi_model: DexpiModel
    ) -> None:
        """Test save with pretty parameter.

        Parameters
        ----------
        serializer : ProteusSerializer
            The ProteusSerializer instance.
        simple_dexpi_model : DexpiModel
            A simple DexpiModel instance.
        """
        with TemporaryDirectory() as tmpdir:
            dir_path = Path(tmpdir)

            # Save with pretty=True
            serializer.save(simple_dexpi_model, dir_path, "pretty.xml", pretty=True)

            # Save with pretty=False
            serializer.save(simple_dexpi_model, dir_path, "compact.xml", pretty=False)

            pretty_file = dir_path / "pretty.xml"
            compact_file = dir_path / "compact.xml"

            assert pretty_file.exists()
            assert compact_file.exists()

            # Pretty file should be larger due to whitespace
            assert pretty_file.stat().st_size > compact_file.stat().st_size

    def test_load_without_xml_extension(
        self, serializer: ProteusSerializer, simple_dexpi_model: DexpiModel
    ) -> None:
        """Test load automatically adds .xml extension.

        Parameters
        ----------
        serializer : ProteusSerializer
            The ProteusSerializer instance.
        simple_dexpi_model : DexpiModel
            A simple DexpiModel instance.
        """
        with TemporaryDirectory() as tmpdir:
            dir_path = Path(tmpdir)

            # Save with extension
            serializer.save(simple_dexpi_model, dir_path, "test_model.xml")

            # Load without extension
            loaded_model = serializer.load(dir_path, "test_model")

            assert isinstance(loaded_model, DexpiModel)

    def test_export_to_bytes(
        self, serializer: ProteusSerializer, simple_dexpi_model: DexpiModel
    ) -> None:
        """Test export_to_bytes method.

        Parameters
        ----------
        serializer : ProteusSerializer
            The ProteusSerializer instance.
        simple_dexpi_model : DexpiModel
            A simple DexpiModel instance.
        """
        xml_bytes = serializer.export_to_bytes(simple_dexpi_model)

        assert isinstance(xml_bytes, bytes)
        assert xml_bytes.startswith(b"<?xml")
        assert b"PlantModel" in xml_bytes

    def test_export_to_bytes_pretty_parameter(
        self, serializer: ProteusSerializer, simple_dexpi_model: DexpiModel
    ) -> None:
        """Test export_to_bytes with pretty parameter.

        Parameters
        ----------
        serializer : ProteusSerializer
            The ProteusSerializer instance.
        simple_dexpi_model : DexpiModel
            A simple DexpiModel instance.
        """
        pretty_bytes = serializer.export_to_bytes(simple_dexpi_model, pretty=True)
        compact_bytes = serializer.export_to_bytes(simple_dexpi_model, pretty=False)

        # Pretty version should be longer
        assert len(pretty_bytes) > len(compact_bytes)

        # Both should be valid
        assert pretty_bytes.startswith(b"<?xml")
        assert compact_bytes.startswith(b"<?xml")

    def test_export_to_stream(
        self, serializer: ProteusSerializer, simple_dexpi_model: DexpiModel
    ) -> None:
        """Test export_to_stream method.

        Parameters
        ----------
        serializer : ProteusSerializer
            The ProteusSerializer instance.
        simple_dexpi_model : DexpiModel
            A simple DexpiModel instance.
        """
        stream = io.BytesIO()
        serializer.export_to_stream(simple_dexpi_model, stream)

        stream.seek(0)
        xml_bytes = stream.read()

        assert isinstance(xml_bytes, bytes)
        assert xml_bytes.startswith(b"<?xml")
        assert b"PlantModel" in xml_bytes

    def test_export_to_stream_pretty_parameter(
        self, serializer: ProteusSerializer, simple_dexpi_model: DexpiModel
    ) -> None:
        """Test export_to_stream with pretty parameter.

        Parameters
        ----------
        serializer : ProteusSerializer
            The ProteusSerializer instance.
        simple_dexpi_model : DexpiModel
            A simple DexpiModel instance.
        """
        pretty_stream = io.BytesIO()
        compact_stream = io.BytesIO()

        serializer.export_to_stream(simple_dexpi_model, pretty_stream, pretty=True)
        serializer.export_to_stream(simple_dexpi_model, compact_stream, pretty=False)

        pretty_stream.seek(0)
        compact_stream.seek(0)

        pretty_bytes = pretty_stream.read()
        compact_bytes = compact_stream.read()

        # Pretty version should be longer
        assert len(pretty_bytes) > len(compact_bytes)

    def test_load_from_bytes(
        self, serializer: ProteusSerializer, simple_dexpi_model: DexpiModel
    ) -> None:
        """Test load_from_bytes method.

        Parameters
        ----------
        serializer : ProteusSerializer
            The ProteusSerializer instance.
        simple_dexpi_model : DexpiModel
            A simple DexpiModel instance.
        """
        # Export to bytes
        xml_bytes = serializer.export_to_bytes(simple_dexpi_model)

        # Load from bytes
        loaded_model = serializer.load_from_bytes(xml_bytes)

        assert isinstance(loaded_model, DexpiModel)
        assert loaded_model.originatingSystemName == simple_dexpi_model.originatingSystemName

    def test_load_from_stream(
        self, serializer: ProteusSerializer, simple_dexpi_model: DexpiModel
    ) -> None:
        """Test load_from_stream method.

        Parameters
        ----------
        serializer : ProteusSerializer
            The ProteusSerializer instance.
        simple_dexpi_model : DexpiModel
            A simple DexpiModel instance.
        """
        # Export to stream
        export_stream = io.BytesIO()
        serializer.export_to_stream(simple_dexpi_model, export_stream)

        # Load from stream
        export_stream.seek(0)
        loaded_model = serializer.load_from_stream(export_stream)

        assert isinstance(loaded_model, DexpiModel)
        assert loaded_model.originatingSystemName == simple_dexpi_model.originatingSystemName

    def test_load_from_string(
        self, serializer: ProteusSerializer, simple_dexpi_model: DexpiModel
    ) -> None:
        """Test load_from_string method.

        Parameters
        ----------
        serializer : ProteusSerializer
            The ProteusSerializer instance.
        simple_dexpi_model : DexpiModel
            A simple DexpiModel instance.
        """
        # Export to bytes and convert to string
        xml_bytes = serializer.export_to_bytes(simple_dexpi_model)
        xml_string = xml_bytes.decode("utf-8")

        # Load from string
        loaded_model = serializer.load_from_string(xml_string)

        assert isinstance(loaded_model, DexpiModel)
        assert loaded_model.originatingSystemName == simple_dexpi_model.originatingSystemName

    def test_round_trip_bytes(
        self, serializer: ProteusSerializer, simple_dexpi_model: DexpiModel
    ) -> None:
        """Test export to bytes and load from bytes round-trip.

        Parameters
        ----------
        serializer : ProteusSerializer
            The ProteusSerializer instance.
        simple_dexpi_model : DexpiModel
            A simple DexpiModel instance.
        """
        # Export to bytes
        xml_bytes = serializer.export_to_bytes(simple_dexpi_model)

        # Load from bytes
        loaded_model = serializer.load_from_bytes(xml_bytes)

        # Export again
        xml_bytes2 = serializer.export_to_bytes(loaded_model)

        # Should produce similar results (content-wise)
        assert isinstance(xml_bytes2, bytes)
        assert b"PlantModel" in xml_bytes2

    def test_round_trip_stream(
        self, serializer: ProteusSerializer, simple_dexpi_model: DexpiModel
    ) -> None:
        """Test export to stream and load from stream round-trip.

        Parameters
        ----------
        serializer : ProteusSerializer
            The ProteusSerializer instance.
        simple_dexpi_model : DexpiModel
            A simple DexpiModel instance.
        """
        # Export to stream
        stream1 = io.BytesIO()
        serializer.export_to_stream(simple_dexpi_model, stream1)

        # Load from stream
        stream1.seek(0)
        loaded_model = serializer.load_from_stream(stream1)

        # Export again to stream
        stream2 = io.BytesIO()
        serializer.export_to_stream(loaded_model, stream2)

        stream2.seek(0)
        xml_bytes2 = stream2.read()

        # Should produce valid XML
        assert isinstance(xml_bytes2, bytes)
        assert b"PlantModel" in xml_bytes2

    def test_get_loading_errors(self, serializer: ProteusSerializer) -> None:
        """Test get_loading_errors method.

        Parameters
        ----------
        serializer : ProteusSerializer
            The ProteusSerializer instance.
        """
        # Before loading, should return None
        error_registry = serializer.get_loading_errors()
        assert error_registry is None

        # After loading, should return ErrorRegistry
        serializer.load("data", "C01V04-VER.EX01")
        error_registry = serializer.get_loading_errors()

        assert isinstance(error_registry, ErrorRegistry)

    def test_consistency_across_methods(
        self, serializer: ProteusSerializer, simple_dexpi_model: DexpiModel
    ) -> None:
        """Test that all export methods produce consistent output.

        Parameters
        ----------
        serializer : ProteusSerializer
            The ProteusSerializer instance.
        simple_dexpi_model : DexpiModel
            A simple DexpiModel instance.
        """
        # Export using different methods
        bytes_output = serializer.export_to_bytes(simple_dexpi_model)

        stream_output = io.BytesIO()
        serializer.export_to_stream(simple_dexpi_model, stream_output)
        stream_output.seek(0)
        stream_bytes = stream_output.read()

        with TemporaryDirectory() as tmpdir:
            dir_path = Path(tmpdir)
            serializer.save(simple_dexpi_model, dir_path, "test.xml")
            with open(dir_path / "test.xml", "rb") as f:
                file_bytes = f.read()

        # All should produce the same output
        assert bytes_output == stream_bytes
        assert bytes_output == file_bytes

    def test_consistency_across_load_methods(
        self, serializer: ProteusSerializer, simple_dexpi_model: DexpiModel
    ) -> None:
        """Test that all load methods produce consistent results.

        Parameters
        ----------
        serializer : ProteusSerializer
            The ProteusSerializer instance.
        simple_dexpi_model : DexpiModel
            A simple DexpiModel instance.
        """
        # Export to bytes
        xml_bytes = serializer.export_to_bytes(simple_dexpi_model)
        xml_string = xml_bytes.decode("utf-8")

        # Load using different methods
        model_from_bytes = serializer.load_from_bytes(xml_bytes)
        model_from_string = serializer.load_from_string(xml_string)

        stream = io.BytesIO(xml_bytes)
        model_from_stream = serializer.load_from_stream(stream)

        # All should produce DexpiModel instances with same system name
        assert model_from_bytes.originatingSystemName == simple_dexpi_model.originatingSystemName
        assert model_from_string.originatingSystemName == simple_dexpi_model.originatingSystemName
        assert model_from_stream.originatingSystemName == simple_dexpi_model.originatingSystemName
