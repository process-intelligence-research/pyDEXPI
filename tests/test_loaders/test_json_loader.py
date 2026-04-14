import datetime
from collections.abc import Callable

import networkx as nx
import pytest

from pydexpi.dexpi_classes.pydantic_classes import DexpiModel, PipingNetworkSegment
from pydexpi.loaders.graph_loader import GraphLoader
from pydexpi.loaders.json_serializer import JsonSerializer


def _node_match_ignore_proteus_id(n1: dict, n2: dict) -> bool:
    """Compare nodes ignoring proteusId field."""
    n1_filtered = {k: v for k, v in n1.items() if k != "proteusId"}
    n2_filtered = {k: v for k, v in n2.items() if k != "proteusId"}
    return n1_filtered == n2_filtered


def _edge_match_ignore_proteus_id(e1: dict, e2: dict) -> bool:
    """Compare edges ignoring proteusId field."""
    e1_filtered = {k: v for k, v in e1.items() if k != "proteusId"}
    e2_filtered = {k: v for k, v in e2.items() if k != "proteusId"}
    return e1_filtered == e2_filtered


def test_json_loader_dict_simple_pns(simple_pns_factory: Callable[[], PipingNetworkSegment]):
    """Test if the JSONLoader can convert a simple PNS to dict and back."""

    json_loader = JsonSerializer()
    simple_pns = simple_pns_factory()

    # Convert PNS to dict
    pns_dict = json_loader.model_to_dict(simple_pns)

    # Convert dict back to PNS
    reconstructed_pns = json_loader.dict_to_model(pns_dict)

    # Check if the original and reconstructed PNS have equal features
    assert len(simple_pns.items) == len(reconstructed_pns.items)
    assert len(simple_pns.connections) == len(reconstructed_pns.connections)
    assert simple_pns.items[0].nodes[0].id == reconstructed_pns.items[0].nodes[0].id

    # Compare via identity, which references the object ids
    assert simple_pns.connections[1].sourceItem == reconstructed_pns.connections[1].sourceItem
    assert simple_pns.connections[1].targetItem == reconstructed_pns.connections[1].targetItem
    assert simple_pns.connections[1].sourceNode == reconstructed_pns.connections[1].sourceNode


def test_json_loader_on_full_model(loaded_example_dexpi: DexpiModel):
    """Test if the JSONLoader can convert a full Dexpi model to dict and back."""

    json_loader = JsonSerializer()

    # Convert Dexpi model to dict
    json_dict = json_loader.model_to_dict(loaded_example_dexpi)

    # Convert dict back to Dexpi model
    reconstructed_model = json_loader.dict_to_model(json_dict)

    # Compare via graph export
    gr_loader = GraphLoader()
    orig_graph = gr_loader.dexpi_to_graph(loaded_example_dexpi)
    recon_graph = gr_loader.dexpi_to_graph(reconstructed_model)

    # Check if the original and reconstructed graphs are isomorphic (ignoring proteusId)
    is_isomorphic = nx.is_isomorphic(
        orig_graph,
        recon_graph,
        node_match=_node_match_ignore_proteus_id,
        edge_match=_edge_match_ignore_proteus_id,
    )
    assert is_isomorphic, "The original and reconstructed graphs are not isomorphic."

    # Check via the json export. It should be the same as the original dict.
    reconstructed_json_dict = json_loader.model_to_dict(reconstructed_model)
    assert json_dict == reconstructed_json_dict, (
        "The original and reconstructed JSON dicts do not match."
    )


def test_load_save_json(loaded_example_dexpi: DexpiModel, tmp_path: str):
    """Test if the JSONLoader can save and load a Dexpi model correctly."""

    json_loader = JsonSerializer()

    # Save the dict to a file
    json_loader.save(loaded_example_dexpi, tmp_path, "test_model.json")

    # Load the dict from the file
    reconstructed_model = json_loader.load(tmp_path, "test_model.json")

    # Compare via graph export
    gr_loader = GraphLoader()
    orig_graph = gr_loader.dexpi_to_graph(loaded_example_dexpi)
    recon_graph = gr_loader.dexpi_to_graph(reconstructed_model)

    # Check if the original and reconstructed graphs are isomorphic (ignoring proteusId)
    is_isomorphic = nx.is_isomorphic(
        orig_graph,
        recon_graph,
        node_match=_node_match_ignore_proteus_id,
        edge_match=_edge_match_ignore_proteus_id,
    )
    assert is_isomorphic, "The original and reconstructed graphs are not isomorphic."

    # Test for non-existent file ending
    json_loader.save(loaded_example_dexpi, tmp_path, "test_model2")

    # Load the dict from the file and check that no error is raised
    _ = json_loader.load(tmp_path, "test_model2.json")
    _ = json_loader.load(tmp_path, "test_model2")

    # Test loadin a non-existent file
    with pytest.raises(FileNotFoundError):
        json_loader.load(tmp_path, "non_existent_file.json")


def test_load_save_datetime(tmp_path: str):
    """Test if the JSONLoader can save and load a Dexpi model with datetime correctly."""

    basic_model = DexpiModel(exportDateTime=datetime.datetime(2025, 1, 1, 12, 0, 0))
    json_loader = JsonSerializer()
    # Save the dict to a file
    json_loader.save(basic_model, tmp_path, "test_datetime.json")
    # Load the dict from the file
    reconstructed_model = json_loader.load(tmp_path, "test_datetime.json")
    assert basic_model.exportDateTime == reconstructed_model.exportDateTime
    assert isinstance(reconstructed_model.exportDateTime, datetime.datetime)


def test_export_to_bytes(loaded_example_dexpi: DexpiModel):
    """Test if the JSONLoader can export a model to bytes."""
    json_loader = JsonSerializer()

    # Export to bytes
    json_bytes = json_loader.export_to_bytes(loaded_example_dexpi)

    assert isinstance(json_bytes, bytes)
    assert b"uri" in json_bytes
    assert b"composition" in json_bytes


def test_export_to_bytes_with_indent(simple_dexpi_model_factory: Callable[[], DexpiModel]):
    """Test export_to_bytes with different indentation levels."""
    json_loader = JsonSerializer()
    model = simple_dexpi_model_factory()

    # Export with default indentation
    bytes_indent_4 = json_loader.export_to_bytes(model, indent=4)

    # Export with no indentation
    bytes_indent_none = json_loader.export_to_bytes(model, indent=None)

    # Indented version should be longer
    assert len(bytes_indent_4) > len(bytes_indent_none)

    # Both should be valid bytes
    assert isinstance(bytes_indent_4, bytes)
    assert isinstance(bytes_indent_none, bytes)


def test_export_to_stream(loaded_example_dexpi: DexpiModel):
    """Test if the JSONLoader can export a model to a byte stream."""
    import io

    json_loader = JsonSerializer()
    stream = io.BytesIO()

    # Export to stream
    json_loader.export_to_stream(loaded_example_dexpi, stream)

    # Read from stream
    stream.seek(0)
    json_bytes = stream.read()

    assert isinstance(json_bytes, bytes)
    assert b"uri" in json_bytes
    assert b"composition" in json_bytes


def test_export_to_stream_with_indent(simple_dexpi_model_factory: Callable[[], DexpiModel]):
    """Test export_to_stream with different indentation levels."""
    import io

    json_loader = JsonSerializer()
    model = simple_dexpi_model_factory()

    stream_indent_4 = io.BytesIO()
    stream_indent_none = io.BytesIO()

    # Export with different indentations
    json_loader.export_to_stream(model, stream_indent_4, indent=4)
    json_loader.export_to_stream(model, stream_indent_none, indent=None)

    stream_indent_4.seek(0)
    stream_indent_none.seek(0)

    bytes_indent_4 = stream_indent_4.read()
    bytes_indent_none = stream_indent_none.read()

    # Indented version should be longer
    assert len(bytes_indent_4) > len(bytes_indent_none)


def test_load_from_bytes(loaded_example_dexpi: DexpiModel):
    """Test if the JSONLoader can load a model from bytes."""
    json_loader = JsonSerializer()

    # Export to bytes
    json_bytes = json_loader.export_to_bytes(loaded_example_dexpi)

    # Load from bytes
    reconstructed_model = json_loader.load_from_bytes(json_bytes)

    # Compare via graph export
    gr_loader = GraphLoader()
    orig_graph = gr_loader.dexpi_to_graph(loaded_example_dexpi)
    recon_graph = gr_loader.dexpi_to_graph(reconstructed_model)

    # Check if the original and reconstructed graphs are isomorphic (ignoring proteusId)
    is_isomorphic = nx.is_isomorphic(
        orig_graph,
        recon_graph,
        node_match=_node_match_ignore_proteus_id,
        edge_match=_edge_match_ignore_proteus_id,
    )
    assert is_isomorphic, "The original and reconstructed graphs are not isomorphic."


def test_load_from_stream(loaded_example_dexpi: DexpiModel):
    """Test if the JSONLoader can load a model from a byte stream."""
    import io

    json_loader = JsonSerializer()

    # Export to stream
    export_stream = io.BytesIO()
    json_loader.export_to_stream(loaded_example_dexpi, export_stream)

    # Load from stream
    export_stream.seek(0)
    reconstructed_model = json_loader.load_from_stream(export_stream)

    # Compare via graph export
    gr_loader = GraphLoader()
    orig_graph = gr_loader.dexpi_to_graph(loaded_example_dexpi)
    recon_graph = gr_loader.dexpi_to_graph(reconstructed_model)

    # Check if the original and reconstructed graphs are isomorphic (ignoring proteusId)
    is_isomorphic = nx.is_isomorphic(
        orig_graph,
        recon_graph,
        node_match=_node_match_ignore_proteus_id,
        edge_match=_edge_match_ignore_proteus_id,
    )
    assert is_isomorphic, "The original and reconstructed graphs are not isomorphic."


def test_load_from_string(loaded_example_dexpi: DexpiModel):
    """Test if the JSONLoader can load a model from a JSON string."""
    json_loader = JsonSerializer()

    # Export to bytes and convert to string
    json_bytes = json_loader.export_to_bytes(loaded_example_dexpi)
    json_string = json_bytes.decode("utf-8")

    # Load from string
    reconstructed_model = json_loader.load_from_string(json_string)

    # Compare via graph export
    gr_loader = GraphLoader()
    orig_graph = gr_loader.dexpi_to_graph(loaded_example_dexpi)
    recon_graph = gr_loader.dexpi_to_graph(reconstructed_model)

    # Check if the original and reconstructed graphs are isomorphic (ignoring proteusId)
    is_isomorphic = nx.is_isomorphic(
        orig_graph,
        recon_graph,
        node_match=_node_match_ignore_proteus_id,
        edge_match=_edge_match_ignore_proteus_id,
    )
    assert is_isomorphic, "The original and reconstructed graphs are not isomorphic."


def test_round_trip_bytes(simple_dexpi_model_factory: Callable[[], DexpiModel]):
    """Test export to bytes and load from bytes round-trip."""
    json_loader = JsonSerializer()
    model = simple_dexpi_model_factory()

    # Export to bytes
    json_bytes = json_loader.export_to_bytes(model)

    # Load from bytes
    loaded_model = json_loader.load_from_bytes(json_bytes)

    # Export again
    json_bytes2 = json_loader.export_to_bytes(loaded_model)

    # Should produce the same output
    assert json_bytes == json_bytes2


def test_round_trip_stream(simple_dexpi_model_factory: Callable[[], DexpiModel]):
    """Test export to stream and load from stream round-trip."""
    import io

    json_loader = JsonSerializer()
    model = simple_dexpi_model_factory()

    # Export to stream
    stream1 = io.BytesIO()
    json_loader.export_to_stream(model, stream1)

    # Load from stream
    stream1.seek(0)
    loaded_model = json_loader.load_from_stream(stream1)

    # Export again to stream
    stream2 = io.BytesIO()
    json_loader.export_to_stream(loaded_model, stream2)

    stream1.seek(0)
    stream2.seek(0)

    # Should produce the same output
    assert stream1.read() == stream2.read()
