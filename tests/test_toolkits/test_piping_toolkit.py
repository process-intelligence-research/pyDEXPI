import copy

import pytest

from pydexpi.dexpi_classes import piping
from pydexpi.toolkits import piping_toolkit as pt


def test_segment_ends_in_connection(simple_pns_factory):
    """Test evaluating if a segment ends in a connection."""
    segment = simple_pns_factory()
    assert pt.segment_ends_in_connection(segment) is False
    assert pt.segment_ends_in_connection(segment, as_source=True) is True


def test_segments_are_connected(simple_pns_factory):
    """Test evaluating if two segments are connected"""
    segment = simple_pns_factory()
    second_segment = simple_pns_factory()  # use factory to get a new instance
    assert pt.segments_are_connected(segment, second_segment) is False
    pt.connect_piping_network_segment(
        second_segment, segment.items[-1], connector_node_index=1, as_source=True
    )
    assert (
        pt.piping_network_segment_validity_check(second_segment)[0] == pt.PipingValidityCode.VALID
    )
    assert pt.segments_are_connected(segment, second_segment) is True


def test_connect_piping_network_segment(simple_pns_factory):
    """Test the reconnecting of a piping network segment. Depends on validity
    check"""
    segment = simple_pns_factory()
    new_destination_1 = piping.BallValve(nodes=[piping.PipingNode() for i in range(2)])
    new_destination_2 = copy.deepcopy(new_destination_1)
    # Cant reconnect segment that ends in an Item
    with pytest.raises(ValueError):
        pt.connect_piping_network_segment(segment, new_destination_1, connector_node_index=0)
    # Try normal reconnection
    pt.connect_piping_network_segment(
        segment, new_destination_1, connector_node_index=1, as_source=True
    )
    assert pt.piping_network_segment_validity_check(segment)[0] == pt.PipingValidityCode.VALID
    # Reconnection not possible unless force reconnect is set to True
    with pytest.raises(pt.DexpiConnectionException):
        pt.connect_piping_network_segment(
            segment,
            new_destination_2,
            connector_node_index=1,
            as_source=True,
        )
    pt.connect_piping_network_segment(
        segment,
        new_destination_2,
        connector_node_index=1,
        as_source=True,
        force_reconnect=True,
    )
    assert pt.piping_network_segment_validity_check(segment)[0] == pt.PipingValidityCode.VALID
    # Reconnection to 1, but without a node this time
    pt.connect_piping_network_segment(
        segment,
        new_destination_2,
        as_source=True,
        force_reconnect=True,
    )
    assert pt.piping_network_segment_validity_check(segment)[0] == pt.PipingValidityCode.VALID


def test_construct_new_segment():
    """Construct simple piping network segment with three pipes and valves and
    see if some of the connections are implemented correctly.

    """
    valves = [piping.BallValve(nodes=[piping.PipingNode() for i in range(2)]) for j in range(3)]
    pipes = [piping.Pipe() for i in range(3)]
    segment = pt.construct_new_segment(
        valves,
        pipes,
        target_connector_item=valves[-1],
        target_connector_node_index=1,
    )
    valves_use_items = [
        piping.BallValve(nodes=[piping.PipingNode() for i in range(2)]) for j in range(3)
    ]
    pipes_use_items = [piping.Pipe() for i in range(3)]
    segment_use_items = pt.construct_new_segment(
        valves_use_items,
        pipes_use_items,
        target_connector_item=valves_use_items[-1],
        connectivity_convention=pt.PipingConnectionConvention.USE_ITEMS,
    )
    # See if the second pipe has the right destination
    assert segment.connections[1].targetItem == segment.items[1]
    assert segment.connections[1].targetNode == segment.items[1].nodes[0]
    # See if the second pipe has the right source
    assert segment_use_items.connections[1].sourceItem == segment_use_items.items[0]
    assert segment_use_items.connections[1].sourceNode is None
    # See if the final pipe has the right destination
    assert segment.connections[-1].targetItem == segment.items[-1]
    assert segment.connections[-1].targetNode == segment.items[-1].nodes[0]
    assert segment_use_items.connections[-1].targetItem == segment_use_items.items[-1]
    assert segment_use_items.connections[-1].targetNode is None

    # See if the segment references the right object as destination
    assert segment.targetItem == valves[-1]
    assert segment.targetNode == valves[-1].nodes[1]
    assert segment_use_items.targetItem == valves_use_items[-1]
    assert segment_use_items.targetNode is None


def test_construct_new_segment_already_connected():
    """Test constructing a new segment with items that are already connected."""
    # Create test components
    valves = [piping.BallValve(nodes=[piping.PipingNode() for i in range(2)]) for j in range(3)]
    pipes = [piping.Pipe() for i in range(3)]

    # Pre-connect components using nodes
    pipes[0].sourceItem = valves[0]
    pipes[0].sourceNode = valves[0].nodes[1]
    pipes[0].targetItem = valves[1]
    pipes[0].targetNode = valves[1].nodes[0]

    pipes[1].sourceItem = valves[1]
    pipes[1].sourceNode = valves[1].nodes[1]
    pipes[1].targetItem = valves[2]
    pipes[1].targetNode = valves[2].nodes[0]

    # Test with USE_NODES convention
    segment = pt.construct_new_segment_already_connected(
        valves,
        pipes[:2],  # Only use first two pipes
        target_connector_item=valves[-1],
        target_connector_node_index=1,
    )

    # Verify connections are preserved
    assert segment.connections[0].sourceItem == valves[0]
    assert segment.connections[0].sourceNode == valves[0].nodes[1]
    assert segment.connections[0].targetItem == valves[1]
    assert segment.connections[0].targetNode == valves[1].nodes[0]

    assert segment.connections[1].sourceItem == valves[1]
    assert segment.connections[1].sourceNode == valves[1].nodes[1]
    assert segment.connections[1].targetItem == valves[2]
    assert segment.connections[1].targetNode == valves[2].nodes[0]

    # Test with USE_ITEMS convention
    valves_use_items = [piping.BallValve() for j in range(3)]
    pipes_use_items = [piping.Pipe() for i in range(3)]

    # Pre-connect components without nodes
    pipes_use_items[0].sourceItem = valves_use_items[0]
    pipes_use_items[0].targetItem = valves_use_items[1]

    pipes_use_items[1].sourceItem = valves_use_items[1]
    pipes_use_items[1].targetItem = valves_use_items[2]

    segment_use_items = pt.construct_new_segment_already_connected(
        valves_use_items,
        pipes_use_items[:2],
        target_connector_item=valves_use_items[-1],
        connectivity_convention=pt.PipingConnectionConvention.USE_ITEMS,
    )

    # Verify USE_ITEMS connections
    assert segment_use_items.connections[0].sourceItem == valves_use_items[0]
    assert segment_use_items.connections[0].sourceNode is None
    assert segment_use_items.connections[0].targetItem == valves_use_items[1]
    assert segment_use_items.connections[0].targetNode is None

    # Test error cases
    # Case 1: Disconnected items
    bad_pipes = copy.deepcopy(pipes[:2])
    bad_pipes[1].targetItem = None
    with pytest.raises(ValueError):
        pt.construct_new_segment_already_connected(
            valves,
            bad_pipes,
            target_connector_item=valves[-1],
        )

    # Case 2: Wrong connection order
    bad_pipes = copy.deepcopy(pipes[:2])
    bad_pipes[0].sourceItem = valves[1]
    bad_pipes[0].targetItem = valves[2]
    with pytest.raises(ValueError):
        pt.construct_new_segment_already_connected(
            valves,
            bad_pipes,
            target_connector_item=valves[-1],
        )


def test_insert_item_to_segment(simple_pns_factory):
    """Test inserting an item to a simple piping network segment"""
    segment = simple_pns_factory()
    # Insert an item into an empty segment
    new_item = piping.BallValve(nodes=[piping.PipingNode() for i in range(2)])
    new_connection = piping.Pipe()
    the_segment = piping.PipingNetworkSegment()
    pt.insert_item_to_segment(
        the_segment,
        0,
        new_item,
        new_connection,
        item_target_node_index=0,
        item_source_node_index=1,
        insert_before=True,
    )
    assert pt.piping_network_segment_validity_check(the_segment)[0] == pt.PipingValidityCode.VALID
    new_item = piping.FlowInPipeOffPageConnector()
    new_connection = piping.Pipe()
    the_segment = piping.PipingNetworkSegment()
    pt.insert_item_to_segment(the_segment, 0, new_item, new_connection, insert_before=True)
    assert pt.piping_network_segment_validity_check(the_segment)[0] == pt.PipingValidityCode.VALID
    new_item = piping.FlowInPipeOffPageConnector()
    # Insert an item into a segment with just one item
    new_item = piping.BallValve(nodes=[piping.PipingNode() for i in range(2)])
    new_connection = piping.Pipe()
    the_segment = piping.PipingNetworkSegment()
    pt.append_item_to_unconnected_segment(the_segment, piping.BallValve())
    pt.insert_item_to_segment(
        the_segment,
        0,
        new_item,
        new_connection,
        item_target_node_index=0,
        item_source_node_index=1,
        insert_before=True,
    )
    assert pt.piping_network_segment_validity_check(the_segment)[0] == pt.PipingValidityCode.VALID
    # Insert an item into a segment with just one connection
    new_item = piping.BallValve(nodes=[piping.PipingNode() for i in range(2)])
    new_connection = piping.Pipe()
    the_segment = piping.PipingNetworkSegment()
    pt.append_connection_to_unconnected_segment(the_segment, piping.Pipe())
    pt.insert_item_to_segment(
        the_segment,
        0,
        new_item,
        new_connection,
        item_target_node_index=0,
        item_source_node_index=1,
    )
    assert pt.piping_network_segment_validity_check(the_segment)[0] == pt.PipingValidityCode.VALID
    # Try inserting after a connection not yet in the segment
    with pytest.raises(ValueError):
        pt.insert_item_to_segment(
            segment,
            copy.deepcopy(new_item),
            new_item,
            new_connection,
            item_target_node_index=0,
            item_source_node_index=1,
        )
    # Try inserting in some different positions
    pt.insert_item_to_segment(
        segment,
        1,
        new_item,
        new_connection,
        item_target_node_index=0,
        item_source_node_index=1,
        insert_before=True,
    )
    assert pt.piping_network_segment_validity_check(segment)[0] == pt.PipingValidityCode.VALID
    pt.insert_item_to_segment(segment, -2, copy.deepcopy(new_item), copy.deepcopy(new_connection))
    assert pt.piping_network_segment_validity_check(segment)[0] == pt.PipingValidityCode.VALID
    pt.insert_item_to_segment(
        segment,
        new_item,
        copy.deepcopy(new_item),
        copy.deepcopy(new_connection),
        item_target_node_index=0,
        item_source_node_index=1,
    )
    assert pt.piping_network_segment_validity_check(segment)[0] == pt.PipingValidityCode.VALID
    # Try adding objects that are already part of the segment
    with pytest.raises(ValueError):
        pt.insert_item_to_segment(
            segment,
            1,
            new_item,
            new_connection,
            item_target_node_index=0,
            item_source_node_index=1,
        )
    # Try adding items to some invalid segments
    invalid_segment = simple_pns_factory()
    del invalid_segment.connections[1]
    new_item = piping.BallValve()
    new_connection = piping.Pipe()
    with pytest.raises(pt.DexpiCorruptPipingSegmentException):
        pt.insert_item_to_segment(invalid_segment, 1, new_item, new_connection, insert_before=True)


def test_append_item_to_unconnected_segment(simple_pns_factory):
    """Test appending an item to a simple piping network segment"""
    segment = simple_pns_factory()
    # Append an item to an empty segment
    new_item = piping.BallValve(nodes=[piping.PipingNode() for i in range(2)])
    new_segment = piping.PipingNetworkSegment()
    pt.append_item_to_unconnected_segment(new_segment, new_item, 1)
    assert pt.piping_network_segment_validity_check(segment)[0] == pt.PipingValidityCode.VALID
    # Try appending an internal item, which is not allowed
    with pytest.raises(ValueError):
        pt.append_item_to_unconnected_segment(segment, segment.items[0], 1, insert_before=True)
    # Try appending a pipe at an end that already has a pipe
    new_item = piping.BallValve(nodes=[piping.PipingNode() for i in range(2)])
    with pytest.raises(ValueError):
        pt.append_item_to_unconnected_segment(segment, new_item, 0)
    # Append an item normally and see if the resulting segment is valid
    pt.append_item_to_unconnected_segment(segment, new_item, 1, 0, insert_before=True)
    assert pt.piping_network_segment_validity_check(segment)[0] == pt.PipingValidityCode.VALID


def test_append_connection_to_unconnected_segment(simple_pns_factory):
    """Test appending a connection to a simple piping network segment"""
    segment = simple_pns_factory()
    # Append a connection to an empty segment
    new_connection = piping.Pipe()
    new_segment = piping.PipingNetworkSegment()
    pt.append_connection_to_unconnected_segment(new_segment, new_connection, 1)
    assert pt.piping_network_segment_validity_check(segment)[0] == pt.PipingValidityCode.VALID
    # Try appending an internal connection, which is not allowed
    with pytest.raises(ValueError):
        pt.append_connection_to_unconnected_segment(segment, segment.connections[0], 1)
    # Try appending a pipe at an end that already has a pipe
    with pytest.raises(ValueError):
        pt.append_connection_to_unconnected_segment(segment, piping.Pipe(), 0, insert_before=True)
    # Append a pipe normally and see if the resulting segment is valid
    pt.append_connection_to_unconnected_segment(segment, piping.Pipe(), 1)
    assert pt.piping_network_segment_validity_check(segment)[0] == pt.PipingValidityCode.VALID


def test_find_final_connection(simple_pns_factory):
    """Test if the final (first) connection can be found on the simple pns"""
    segment = simple_pns_factory()
    final_connection = pt.find_final_connection(segment)
    first_connection = pt.find_final_connection(segment, as_source=True)
    assert final_connection == segment.connections[-1]
    assert first_connection == segment.connections[0]

    # Damage pns to see if this is handled
    segment.targetNode = None
    segment.targetItem = None
    with pytest.raises(pt.DexpiCorruptPipingSegmentException):
        pt.find_final_connection(segment)


def test_get_unconnected_piping_segments(simple_conceptual_model_factory):
    """Construct a simple Conceptual model and see if unconnected connections
    are identified"""
    model = simple_conceptual_model_factory()
    outlets = pt.get_unconnected_piping_segments(model)
    inlets = pt.get_unconnected_piping_segments(model, as_source=True)
    assert len(outlets) == 1
    assert len(inlets) == 1
    assert outlets[0] == model.pipingNetworkSystems[1].segments[0]
    assert inlets[0] == model.pipingNetworkSystems[0].segments[0]


def test_traverse_items_and_connections():
    """Test traversing through connected items and connections."""
    # Create test components
    items = [piping.BallValve(nodes=[piping.PipingNode() for i in range(2)]) for _ in range(2)]
    connections = [piping.Pipe() for _ in range(5)]
    items.append(piping.PipeTee(nodes=[piping.PipingNode() for i in range(3)]))

    # Connect components
    connections[0].targetItem = items[0]
    connections[0].targetNode = items[0].nodes[0]

    connections[1].sourceItem = items[0]
    connections[1].sourceNode = items[0].nodes[1]
    connections[1].targetItem = items[1]
    connections[1].targetNode = items[1].nodes[0]

    connections[2].sourceItem = items[1]
    connections[2].sourceNode = items[1].nodes[1]
    connections[2].targetItem = items[2]
    connections[2].targetNode = items[2].nodes[0]

    connections[3].sourceItem = items[2]
    connections[3].sourceNode = items[2].nodes[1]

    connections[4].sourceItem = items[2]
    connections[4].sourceNode = items[2].nodes[2]

    traversal = pt.traverse_items_and_connections(
        items, connections, connections[0], lambda x: x == connections[4]
    )
    # Check if the traversal is correct
    assert traversal == [
        connections[0],
        items[0],
        connections[1],
        items[1],
        connections[2],
        items[2],
        connections[4],
    ]

    # Check if the traversal is correct in reverse order
    traversal = pt.traverse_items_and_connections(
        items, connections, connections[4], lambda x: x == connections[0], reverse=True
    )
    assert traversal == [
        connections[4],
        items[2],
        connections[2],
        items[1],
        connections[1],
        items[0],
        connections[0],
    ]

    # Check traversing from an item
    traversal = pt.traverse_items_and_connections(
        items, connections, items[0], lambda x: x == connections[4]
    )
    assert traversal == [
        items[0],
        connections[1],
        items[1],
        connections[2],
        items[2],
        connections[4],
    ]

    # Check traversing from an item in reverse order
    traversal = pt.traverse_items_and_connections(
        items, connections, items[2], lambda x: x == connections[0], reverse=True
    )
    assert traversal == [
        items[2],
        connections[2],
        items[1],
        connections[1],
        items[0],
        connections[0],
    ]

    # Check specifying a connection directly as end condition
    traversal = pt.traverse_items_and_connections(items, connections, items[0], connections[4])
    assert traversal == [
        items[0],
        connections[1],
        items[1],
        connections[2],
        items[2],
        connections[4],
    ]

    # Some more edge cases
    # Case 1: Traversing a single item
    single_item = piping.BallValve(nodes=[piping.PipingNode() for i in range(2)])
    traversal = pt.traverse_items_and_connections(
        [single_item], [], single_item, lambda x: x == single_item
    )
    assert traversal == [single_item]

    # Case 2: Traversing a single connection
    single_connection = piping.Pipe()
    traversal = pt.traverse_items_and_connections(
        [], [single_connection], single_connection, lambda x: x == single_connection
    )
    assert traversal == [single_connection]

    # Case 3: A little more complex end condition
    def end_condition(x):
        if isinstance(x, piping.PipingConnection):
            if x.targetItem not in items:
                return True
        return False

    traversal = pt.traverse_items_and_connections(items, connections, connections[0], end_condition)
    assert traversal == [
        connections[0],
        items[0],
        connections[1],
        items[1],
        connections[2],
        items[2],
        connections[3],
    ]

    # Test error cases
    # Case 1: Empty items list
    with pytest.raises(pt.PipingTraversalException):
        list(
            pt.traverse_items_and_connections(
                [], connections, connections[0], lambda x: x == connections[4]
            )
        )

    # Case 2: Empty connections list
    with pytest.raises(pt.PipingTraversalException):
        list(
            pt.traverse_items_and_connections(
                items, [], connections[0], lambda x: x == connections[4]
            )
        )

    # Case 3: Starting element not in lists
    extra_connection = piping.Pipe()
    with pytest.raises(pt.PipingTraversalException):
        list(
            pt.traverse_items_and_connections(
                items, connections, extra_connection, lambda x: x == connections[4]
            )
        )

    # Case 4: Target condition never met
    with pytest.raises(pt.PipingTraversalException):
        list(pt.traverse_items_and_connections(items, connections, connections[0], lambda x: False))

    # Case 5: Disconnected items
    bad_connections = copy.deepcopy(connections)
    bad_connections[2].targetItem = None
    with pytest.raises(pt.PipingTraversalException):
        list(
            pt.traverse_items_and_connections(
                items, bad_connections, connections[0], lambda x: x == connections[4]
            )
        )

    # Case 6: Loop in connections
    loop_connections = copy.deepcopy(connections)
    loop_connections[3].targetItem = items[0]
    loop_connections[3].targetNode = items[0].nodes[0]
    with pytest.raises(pt.PipingTraversalException):
        list(
            pt.traverse_items_and_connections(
                items, loop_connections, connections[0], lambda x: x == connections[4]
            )
        )

    # Case 7: Multiple paths to same destination
    fork_connections = copy.deepcopy(connections)
    fork_connections[3].targetItem = items[2]
    fork_connections[3].targetNode = items[2].nodes[0]
    with pytest.raises(pt.PipingTraversalException):
        list(
            pt.traverse_items_and_connections(
                items, fork_connections, connections[0], lambda x: x == connections[4]
            )
        )


def test_sort_connected_items_and_connections():
    """Test sorting connections and items of a piping network segment."""

    # Test normal case starting with a connection
    # Create test items and connections
    def make_items_and_connections():
        items = [piping.BallValve(nodes=[piping.PipingNode() for i in range(2)]) for _ in range(3)]
        connections = [piping.Pipe() for _ in range(3)]
        # Set up connections in a shuffled order
        connections[0].sourceItem = items[1]
        connections[0].targetItem = items[2]
        connections[1].sourceItem = items[0]
        connections[1].targetItem = items[1]
        connections[2].sourceItem = None  # First connection has no source
        connections[2].targetItem = items[0]
        return items, connections

    items, connections = make_items_and_connections()

    # Sort connections and items
    sorted_items, sorted_connections = pt.sort_connected_items_and_connections(items, connections)

    # Check if sorting is correct
    assert sorted_connections[0] == connections[2]  # First connection (no source)
    assert sorted_connections[1] == connections[1]  # Middle connection
    assert sorted_connections[2] == connections[0]  # Last connection

    assert sorted_items[0] == items[0]  # First item
    assert sorted_items[1] == items[1]  # Middle item
    assert sorted_items[2] == items[2]  # Last item

    # Check if ordering again gives the same result
    sorted_items2, sorted_connections2 = pt.sort_connected_items_and_connections(
        sorted_items, sorted_connections
    )

    assert sorted_items2 == sorted_items
    assert sorted_connections2 == sorted_connections

    # Test normal case starting with an item
    # Add a source item to the first connection
    items, connections = make_items_and_connections()
    new_item = piping.BallValve(nodes=[piping.PipingNode() for i in range(2)])
    connections[2].sourceItem = new_item
    items.append(new_item)

    # Sort connections and items again
    sorted_items, sorted_connections = pt.sort_connected_items_and_connections(items, connections)

    # Check if sorting is correct
    assert sorted_connections[0] == connections[2]  # First connection (with source)
    assert sorted_connections[1] == connections[1]  # Middle connection
    assert sorted_connections[2] == connections[0]  # Last connection

    assert sorted_items[0] == new_item  # New item
    assert sorted_items[1] == items[0]  # First item
    assert sorted_items[2] == items[1]  # Middle item
    assert sorted_items[3] == items[2]  # Last item

    # Test error cases
    # Case 1: Multiple starting points
    items, bad_connections = make_items_and_connections()
    bad_connections[1].sourceItem = None
    with pytest.raises(ValueError):
        pt.sort_connected_items_and_connections(items, bad_connections)

    # Case 2: Disconnected elements
    items, bad_connections = make_items_and_connections()
    bad_connections[0].targetItem = None
    with pytest.raises(ValueError):
        pt.sort_connected_items_and_connections(items, bad_connections)

    # Case 3: Loop in connections
    items, loop_connections = make_items_and_connections()
    loop_connections[0].targetItem = items[0]
    with pytest.raises(ValueError):
        pt.sort_connected_items_and_connections(items, loop_connections)


def test_sort_segment_connections_and_items(simple_pns_factory):
    """Test sorting connections and items within a piping network segment."""
    shuffled_pns = simple_pns_factory()

    # Shuffle the lists (but keep the connections valid)
    original_items = copy.copy(shuffled_pns.items)
    original_connections = copy.copy(shuffled_pns.connections)

    if len(shuffled_pns.items) > 1:
        shuffled_pns.items.reverse()
    if len(shuffled_pns.connections) > 1:
        shuffled_pns.connections.reverse()

    # Sort the segment
    pt.sort_segment_items_and_connections(shuffled_pns)

    # Check if items and connections are in the original order
    assert shuffled_pns.items == original_items
    assert shuffled_pns.connections == original_connections

    # Verify that the segment is still valid after sorting
    assert pt.piping_network_segment_validity_check(shuffled_pns)[0] == pt.PipingValidityCode.VALID


def test_piping_network_segment_validity_check(simple_pns_factory):
    """test some invalid piping network segments and their validity status. For
    this, use some invalid cases. Comparisons done via
    piping_toolkig.PipingValidityCode
    """

    def check_pns(segment: piping.PipingNetworkSegment):
        """Quick local namespace function for the
        piping_network_segment_validity_check"""
        return pt.piping_network_segment_validity_check(segment)

    # Case 1: Single pipe segment where pipe doesnt have the same source
    a_valve = piping.BallValve(nodes=[piping.PipingNode() for i in range(2)])
    invalid_segment = piping.PipingNetworkSegment(sourceItem=a_valve, connections=[piping.Pipe()])
    assert check_pns(invalid_segment)[0] == pt.PipingValidityCode.CONNECTION_CONVENTION_VIOLATION

    # Case 2: Segment where two pipes have the same source as pns
    invalid_segment = piping.PipingNetworkSegment(
        sourceItem=a_valve,
        connections=[piping.Pipe(sourceItem=a_valve) for i in range(2)],
    )
    assert check_pns(invalid_segment)[0] == pt.PipingValidityCode.INTERNAL_VIOLATION

    # Case 3: Segment where two pipes have the same target as pns
    invalid_segment = simple_pns_factory()  # new instance
    del invalid_segment.connections[1]
    assert check_pns(invalid_segment)[0] == pt.PipingValidityCode.INTERNAL_VIOLATION

    # Case 4: Add an unconnected item or connection
    invalid_segment = simple_pns_factory()
    invalid_segment.connections.append(piping.Pipe())
    assert check_pns(invalid_segment)[0] == pt.PipingValidityCode.INTERNAL_VIOLATION

    invalid_segment = simple_pns_factory()
    invalid_segment.items.append(piping.BallValve())
    assert check_pns(invalid_segment)[0] == pt.PipingValidityCode.INTERNAL_VIOLATION

    # Case 5: Order violation
    invalid_segment = simple_pns_factory()
    temp_item = invalid_segment.items[1]
    invalid_segment.items[1] = invalid_segment.items[0]
    invalid_segment.items[0] = temp_item
    assert check_pns(invalid_segment)[0] == pt.PipingValidityCode.INTERNAL_VIOLATION

    invalid_segment = simple_pns_factory()
    temp_connection = invalid_segment.connections[1]
    invalid_segment.connections[1] = invalid_segment.connections[0]
    invalid_segment.connections[0] = temp_connection
    assert check_pns(invalid_segment)[0] == pt.PipingValidityCode.INTERNAL_VIOLATION

    # Case 6: Node mismatch
    invalid_segment = simple_pns_factory()
    stray_node = piping.PipingNode()
    invalid_segment.connections[1].sourceNode = stray_node
    assert check_pns(invalid_segment)[0] == pt.PipingValidityCode.INTERNAL_VIOLATION
    invalid_segment = simple_pns_factory()
    invalid_segment.connections[1].targetItem = None
    assert check_pns(invalid_segment)[0] == pt.PipingValidityCode.INTERNAL_VIOLATION
    invalid_segment = simple_pns_factory()
    stray_node = piping.PipingNode()
    invalid_segment.targetNode = stray_node
    assert check_pns(invalid_segment)[0] == pt.PipingValidityCode.INTERNAL_VIOLATION

    # Final valid case
    assert check_pns(simple_pns_factory())[0] == pt.PipingValidityCode.VALID


def test_add_system_attributes_to_segment_sets_missing_values():
    # System has attributes, segments have same attributes set to None
    attrs = {"fluidCode": "W", "insulationType": "test", "pipingClassCode": "123"}
    system = piping.PipingNetworkSystem(
        **attrs, segments=[piping.PipingNetworkSegment() for _ in range(2)]
    )
    # Segments start with None
    for segment in system.segments:
        for k in attrs:
            assert getattr(segment, k) is None
    # Call function
    pt.add_system_attributes_to_segment(system)
    # After call, segments should have system values
    for segment in system.segments:
        for k, v in attrs.items():
            assert getattr(segment, k) == v


def test_add_system_attributes_to_segment_does_not_override_existing():
    attrs = {"fluidCode": "W", "insulationType": "test"}
    system = piping.PipingNetworkSystem(
        **attrs, segments=[piping.PipingNetworkSegment() for _ in range(2)]
    )
    # Set one segment attribute to a value
    system.segments[0].fluidCode = "X"
    pt.add_system_attributes_to_segment(system)
    # Should not override existing value
    assert system.segments[0].fluidCode == "X"
    # Should set missing values
    assert system.segments[0].insulationType == "test"
    assert system.segments[1].fluidCode == "W"
    assert system.segments[1].insulationType == "test"


def test_add_system_attributes_to_segment_empty_segments():
    attrs = {"fluidCode": "W"}
    system = piping.PipingNetworkSystem(**attrs)
    # Should not raise, should return system unchanged
    result = pt.add_system_attributes_to_segment(system)
    assert result is system
