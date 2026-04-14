import os

import networkx as nx
import pytest

from pydexpi.loaders import proteus_serializer
from pydexpi.loaders.graph_loader import GraphAbstractor, GraphLoader


@pytest.fixture
def dexpi_model():
    """Fixture to load the DEXPI model for testing."""
    dexpi_file = os.path.join("data")
    file_name = "C01V04-VER.EX01.xml"

    serializer = proteus_serializer.ProteusSerializer()
    return serializer.load(dexpi_file, file_name)


@pytest.fixture
def graph_loader(dexpi_model):
    """Fixture to create a GraphLoader and parse the DEXPI model into a graph."""
    loader = GraphLoader()
    loader.dexpi_to_graph(dexpi_model)
    return loader


@pytest.fixture
def graph_abstractor(graph_loader: GraphLoader):
    """Fixture to create a GraphAbstractor from the GraphLoader's plant graph."""
    return GraphAbstractor(plant_graph=graph_loader.plant_graph)


def test_complete_graph_structure(graph_loader: GraphLoader):
    """Test that the complete graph has the expected number of nodes and edges."""
    actual_nodes = graph_loader.plant_graph.number_of_nodes()
    actual_edges = graph_loader.plant_graph.number_of_edges()

    expected_nodes = 214  # Includes all DexpiBaseModel instances
    expected_edges = 376  # Includes edges

    assert actual_nodes == expected_nodes, (
        f"Complete graph should have {expected_nodes} nodes but has {actual_nodes}"
    )
    assert actual_edges == expected_edges, (
        f"Complete graph should have {expected_edges} edges but has {actual_edges}"
    )

    print(f"Complete graph: {actual_nodes} nodes, {actual_edges} edges")


def test_build_complete_graph(graph_abstractor: GraphAbstractor):
    """Test that build_complete_graph returns a copy with structural nodes removed."""
    complete_graph = GraphAbstractor.build_complete_graph(graph_abstractor.plant_graph)

    actual_nodes = complete_graph.number_of_nodes()
    actual_edges = complete_graph.number_of_edges()

    # Should have same structure as conceptual/process graphs (structural nodes removed)
    expected_nodes = 212  # All nodes except ConceptualModel and MetaData
    expected_edges = 348  # Edges without structural node connections

    assert actual_nodes == expected_nodes, (
        f"Built complete graph should have {expected_nodes} nodes but has {actual_nodes}"
    )
    assert actual_edges == expected_edges, (
        f"Built complete graph should have {expected_edges} edges but has {actual_edges}"
    )

    # Verify it's a deep copy (modifications don't affect original)
    original_node_count = graph_abstractor.plant_graph.number_of_nodes()
    temp_abstractor = GraphAbstractor(plant_graph=complete_graph)
    temp_abstractor.remove_nodes_by_label("Equipment")
    assert graph_abstractor.plant_graph.number_of_nodes() == original_node_count, (
        "Modifying built graph should not affect the original graph"
    )

    print(f"Built complete graph: {actual_nodes} nodes, {actual_edges} edges")


def test_conceptual_graph_structure(graph_abstractor: GraphAbstractor):
    """Test that the conceptual graph has the expected number of nodes and edges."""
    conceptual_graph = GraphAbstractor.build_conceptual_graph(graph_abstractor.plant_graph)

    actual_nodes = conceptual_graph.number_of_nodes()
    actual_edges = conceptual_graph.number_of_edges()

    expected_nodes = 36
    expected_edges = 39

    assert actual_nodes == expected_nodes, (
        f"Conceptual graph should have {expected_nodes} nodes but has {actual_nodes}"
    )
    assert actual_edges == expected_edges, (
        f"Conceptual graph should have {expected_edges} edges but has {actual_edges}"
    )

    print(f"Conceptual graph: {actual_nodes} nodes, {actual_edges} edges")


def test_process_graph_structure(graph_abstractor: GraphAbstractor):
    """Test that the process graph has the expected number of nodes and edges."""
    process_graph = GraphAbstractor.build_process_graph(graph_abstractor.plant_graph)

    actual_nodes = process_graph.number_of_nodes()
    actual_edges = process_graph.number_of_edges()

    expected_nodes = 66
    expected_edges = 78

    assert actual_nodes == expected_nodes, (
        f"Process graph should have {expected_nodes} nodes but has {actual_nodes}"
    )
    assert actual_edges == expected_edges, (
        f"Process graph should have {expected_edges} edges but has {actual_edges}"
    )

    print(f"Process graph: {actual_nodes} nodes, {actual_edges} edges")


def test_embed_shape_usage_position(graph_loader: GraphLoader):
    """Test that embed_shape_usage with Position mode adds x/y to some nodes."""
    stats = graph_loader.embed_shape_usage(shape_usage_mode="position")

    assert stats["processed"] == stats["embedded"] + stats["skipped"]
    assert stats["embedded"] > 0, "Expected at least one node with ShapeUsage embedded"

    # Verify that embedded nodes actually have x and y attributes
    nodes_with_xy = [
        n for n, d in graph_loader.plant_graph.nodes(data=True) if "x" in d and "y" in d
    ]
    assert len(nodes_with_xy) == stats["embedded"]


def test_embed_shape_usage_full(graph_loader: GraphLoader):
    """Test that embed_shape_usage with default ShapeUsage mode adds extended attrs."""
    stats = graph_loader.embed_shape_usage(shape_usage_mode="shapeusage")

    assert stats["processed"] == stats["embedded"] + stats["skipped"]
    assert stats["embedded"] > 0, "Expected at least one node with ShapeUsage embedded"

    # At least one embedded node should have rotation and scale attributes
    nodes_with_rotation = [
        n for n, d in graph_loader.plant_graph.nodes(data=True) if "rotation" in d
    ]
    assert len(nodes_with_rotation) > 0


def test_export_graphs_to_graphml(graph_loader: GraphLoader, tmp_path):
    """Test exporting complete, conceptual, and process graphs to GraphML files."""
    # Embed shape usage (position only) into the complete graph via GraphLoader
    graph_loader.embed_shape_usage(shape_usage_mode="position")

    # Build abstracted graphs from the position-enriched graph
    complete_graph = GraphAbstractor.build_complete_graph(graph_loader.plant_graph)
    conceptual_graph = GraphAbstractor.build_conceptual_graph(graph_loader.plant_graph)
    process_graph = GraphAbstractor.build_process_graph(graph_loader.plant_graph)

    graphs = {
        "complete_graph": complete_graph,
        "conceptual_graph": conceptual_graph,
        "process_graph": process_graph,
    }

    for name, graph in graphs.items():
        output_path = tmp_path / f"{name}.graphml"
        nx.write_graphml(graph, str(output_path), named_key_ids=True)
        assert output_path.exists(), f"GraphML file {output_path} was not created"
