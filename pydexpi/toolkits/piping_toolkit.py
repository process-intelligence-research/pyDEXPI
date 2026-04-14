"""
Dexpi Piping Toolkit
--------------------
This module contains functions and tools to manipulate the main piping
concepts of a dexpi model. This includes mainly manipulations of piping network
segments.

"""

import warnings
from collections.abc import Callable
from enum import Enum

from pydexpi.dexpi_classes import dexpiModel, piping
from pydexpi.toolkits.base_model_utils import get_data_attributes


class DexpiConnectionException(Exception):
    """Exception for dexpi piping, connection-related errors.

    Raised if a connection or reconnection is attempted that is invalid or may cause corrupt
    segments"""

    pass


class DexpiCorruptPipingSegmentException(Exception):
    """Exception raised if a segment is encountered that violates piping network segment convention."""

    pass


class PipingTraversalException(Exception):
    """Raised if an error occurs during traversal of connected piping components/items/segments."""

    pass


class PipingValidityCode(Enum):
    """
    Enumeration of validity codes for piping related objects.

    Parameters
    ----------
    VALID : int = 0
    INTERNAL_VIOLATION : int = 1
        Violation code for an internal violation in a pipingNetworkSegment.
        Examples are unconnected, loose pipes or items, interrupted segments.
    CONNECTION_CONVENTION_VIOLATION : int = 2
        Violation code if the connection convention regarding a
        pipingNetworkSegment and its pipingConnections is violated
    MULTIPLE_NODE_REFERENCE_VIOLATION : int = 3
        Violation of the convention that a node can only be referenced once
    """

    VALID = 0
    INTERNAL_VIOLATION = 1
    CONNECTION_CONVENTION_VIOLATION = 2
    MULTIPLE_NODE_REFERENCE_VIOLATION = 3


class PipingConnectionConvention(Enum):
    """Convention enumeration for creating connections for higher level piping
    tools where explicit assignment of source and target nodes/items becomes
    impractical.

    Parameters
    ----------
    IN_NODE_0_OUT_NODE_1 : int = 0
        Node with index 0 is used as main inlet, node with index one is main
        outlet
    USE_ITEMS : int = 1
        Use direct assignments to items
    """

    IN_NODE_0_OUT_NODE_1 = 0
    USE_ITEMS = 1


def segment_ends_in_connection(the_segment: piping.PipingNetworkSegment, as_source=False) -> bool:
    """Checks if a segment ends in a connection, as opposed to an item.

    Parameters
    ----------
    the_segment : PipingNetworkSegment
        The segment to be evaluated
    as_source : bool, optional
        Whether the segments source should be checked, by default False

    Returns
    -------
    bool
        True if the segment ends in a connection.
    """
    if not the_segment.connections:
        return False
    destination_item = the_segment.sourceItem if as_source else the_segment.targetItem
    return destination_item not in the_segment.items


def segments_are_connected(
    segment_a: piping.PipingNetworkSegment, segment_b: piping.PipingNetworkSegment
) -> bool:
    """Checks if two segments are connected by comparing their source and target items.

    Parameters
    ----------
    segment_a : PipingNetworkSegment
        The first segment to be checked.
    segment_b : PipingNetworkSegment
        The second segment to be checked.

    Returns
    -------
    bool
        True if the segments are connected, False otherwise.

    Raises
    ------
    ValueError
        If the two segments are the same, as they cannot be connected to themselves.
    """
    # Consistency check if the two segments are the same
    if segment_a == segment_b:
        raise ValueError("Segments are the same. Cannot check if they are connected.")
    # Check if any of the source or target items of one segment are present in the items of the other segment
    return (
        segment_a.sourceItem in segment_b.items
        or segment_a.targetItem in segment_b.items
        or segment_b.sourceItem in segment_a.items
        or segment_b.targetItem in segment_a.items
    )


def connect_piping_network_segment(
    piping_segment: piping.PipingNetworkSegment,
    connector_item: piping.PipingSourceItem | piping.PipingTargetItem,
    connector_node_index: int | None = None,
    as_source=False,
    force_reconnect=False,
) -> None:
    """
    Connects a piping network segment by inferring the pipe to reconnect.

    This is based on the assumption that a valid piping network segment has at
    most one unconnected incoming and at most one unconnected outflowing
    connection. Note that a valid piping network segment may end on a segment
    item like a valve, in which case there are no outgoing flow connections
    (same for input). In this case, a ValueError is raised. An Exception is also
    raised if the piping network segment is corrupted (i.e., has more than one
    inflowing or outflowing connection).

    Parameters
    ----------
    piping_segment : PipingNetworkSegment
        Piping segment to be reconnected.
    connector_item : Union[PipingSourceItem, PipingTargetItem]
        The connector object to which the segment will be connected.
        It can be either a PipingNode, PipingSourceItem, or PipingTargetItem.
    connector_node_index: int, optional
        Optionally, the index of the node of connector_item to be connected to,
        by default None
    as_source : bool, optional
        If True, the connection is established as source, else as target.
        Defaults to False.
    force_reconnect : bool, optional
        If False, raises an exception if the piping connection is already
        connected. Defaults to False.

    Returns
    -------
    None
        This function modifies the state of the piping segment and the
        connection but does not return any value.

    Raises
    ------
    DexpiConnectionException
        If the piping connection is already connected, and force_reconnect is
        False.
    ValueError
        If the piping network segment either has no unconnected output
        connection (or input connection if as_source) or has more than one such
        connections, in which case it is corrupted.
    DexpiCorruptPipingSegmentException
        If the segment to be connected is found to be corrupt
    """
    # Find last connection and item. Last item is None if its None alltogether
    # OR if it isnt among the segment items internally
    if piping_segment.connections:
        last_connection = find_final_connection(piping_segment, as_source=as_source)
        last_item = last_connection.sourceItem if as_source else last_connection.targetItem
        last_item = last_item if last_item in piping_segment.items else None

    # Manage case segment has no connection (is empty or consists of one item):
    else:
        last_connection = None
        if not piping_segment.items:
            last_item = None
        elif len(piping_segment.items) == 1:
            last_item = piping_segment.items[0]
        else:
            msg = (
                f"The segment {piping_segment} has multiple items but no "
                f"connections and may be corrupt"
            )
            raise DexpiCorruptPipingSegmentException(msg)

    # Determine if connection references an internal object, in which case a
    # a reconnection would be invalid and cause a corrupt segment
    if last_item is not None:
        msg = (
            f"Piping segment {piping_segment} references internal "
            f"object as {'source' if as_source else 'target'}. Reconnect "
            f"will cause corrupting the segment."
        )
        raise ValueError(msg)

    if connector_node_index is not None:
        connector_node = connector_item.nodes[connector_node_index]
    else:
        connector_node = None

    _connect_piping_connection(
        connector_item,
        last_connection,
        piping_segment,
        connector_node,
        as_source,
        force_reconnect,
    )


def construct_new_segment(
    segment_items: list[piping.PipingNetworkSegmentItem],
    segment_connections: list[piping.PipingConnection],
    source_connector_item: piping.PipingSourceItem | piping.PipingTargetItem = None,
    target_connector_item: piping.PipingSourceItem | piping.PipingTargetItem = None,
    source_connector_node_index: int = None,
    target_connector_node_index: int = None,
    connectivity_convention: PipingConnectionConvention = PipingConnectionConvention.IN_NODE_0_OUT_NODE_1,
    **segment_kwargs,
) -> piping.PipingNetworkSegment:
    """Constructs a new segment from the segment_items and segment_connections
    passed.

    Segment items and connections need to be in the order they occurr in the
    segment. The shape at the beginning and end of the segment is inferred by
    the source and target object specified. If no Source is given or the source
    is external, the segment starts with a pipe. Same pattern for target.
    However, in this case, the lengths of the passed objects need to match
    accordingly. Warnings printed in case the type of the source and target dont
    match the specified convention

    Parameters
    ----------
    segment_items : list[PipingNetworkSegmentItem]
        The items of the segments that are to be included in order of
        occurrence.
    segment_connections : list[PipingConnection]
        The connections of the segments that are to be included in order of
        occurrence.
    connectivity_convention : PipingConnectionConvention
        The convention to be applied when stringing together the connections and
        items.
    source_connector_item : Union[PipingSourceItem, PipingTargetItem], optional
        The item to be specified as source, can be first element of the
        segment, in which case no first connection is assigned, by default None.
    target_connector_item : Union[PipingSourceItem, PipingTargetItem], optional
        The item to be specified as target, can be last element of the
        segment, in which case no final connection is assigned, by default None.
    source_connector_node_index : int, optional
        The index to the node to be specified as source in the source item,
        by default None.
    target_connector_node_index : int, optional
        The index to the node to be specified as target in the target item,
        by default None.
    **segment_kwargs:
        The additional quargs to be passed on to the constructor of the segment.

    Returns
    -------
    PipingNetworkSegment
        The new piping network segment created

    Raises
    ------
    ValueError
        Raised if the arguments are invalid, such as if an internal item is
        referenced as source or target or if the lengthes of the items and
        connections dont line up with regards to the source and target passed.
    """
    # First, screen for invalid sources
    invalid_sources = segment_items[1:]
    if source_connector_item in invalid_sources:
        msg = f"Cant assign source item to member item {source_connector_item} except the first one"
        raise ValueError(msg)
    invalid_targets = segment_items[:-1]
    if target_connector_item in invalid_targets:
        msg = f"Cant assign target item to member item {target_connector_item} except the final one"
        raise ValueError(msg)

    if connectivity_convention == PipingConnectionConvention.IN_NODE_0_OUT_NODE_1:
        if source_connector_node_index != 0 and source_connector_item is not None:
            warnings.warn(
                "With convention IN_NODE_0_OUT_NODE_1, the correct source node index should be 0"
            )
        if target_connector_node_index != 1 and target_connector_item is not None:
            warnings.warn(
                "With convention IN_NODE_0_OUT_NODE_1, the correct target node index should be 1"
            )

    # Assign nodes
    if source_connector_item is not None and source_connector_node_index is not None:
        source_connector_node = source_connector_item.nodes[source_connector_node_index]
    elif source_connector_node_index is not None:
        msg = "Cannot pass a source outside connector node index without a source connector item"
        raise ValueError(msg)
    else:
        source_connector_node = None

    if target_connector_item is not None and target_connector_node_index is not None:
        target_connector_node = target_connector_item.nodes[target_connector_node_index]
    elif target_connector_node_index is not None:
        msg = "Cannot pass a target outside connector node index without a target connector item"
        raise ValueError(msg)
    else:
        target_connector_node = None

    # Examine source and target connector object and append to segment kwargs.
    # Warnings issued in case the type of the source and target dont match the
    # specified convention
    for type_string, outside_connector_item, outside_connector_node in zip(
        ["source", "target"],
        [source_connector_item, target_connector_item],
        [source_connector_node, target_connector_node],
    ):
        warn = False

        if outside_connector_item is not None:
            if (
                connectivity_convention == PipingConnectionConvention.IN_NODE_0_OUT_NODE_1
                and outside_connector_node is None
            ):
                warn = True
            kwargs_key = type_string + "Item"
            segment_kwargs[kwargs_key] = outside_connector_item
        if outside_connector_node is not None:
            if connectivity_convention == PipingConnectionConvention.USE_ITEMS:
                warn = True
            kwargs_key = type_string + "Node"
            segment_kwargs[kwargs_key] = outside_connector_node

        if warn:
            warnings.warn(
                f"The {type_string} connection specified via the arguments "
                f"violates the indicated convention "
                f"{connectivity_convention}"
            )

    # Check if source and target are internals
    source_is_internal = source_connector_item in segment_items
    target_is_internal = target_connector_item in segment_items
    if segment_items:
        if source_is_internal and source_connector_item != segment_items[0]:
            msg = f"Specified source {source_connector_item} in the segment, but not the first element of segment_items"
            raise ValueError(msg)
        if target_is_internal and target_connector_item != segment_items[-1]:
            msg = f"Specified source {source_connector_item} in the segment, but not the first element of segment_items"
            raise ValueError(msg)

    if source_is_internal and target_is_internal:
        if len(segment_items) != len(segment_connections) + 1:
            msg = (
                "With both source and target internal, the number of "
                "items needs to be one more than the connections"
            )
            raise ValueError(msg)
    elif source_is_internal ^ target_is_internal:
        if len(segment_items) != len(segment_connections):
            msg = (
                "With either the source or target internal, the "
                "number of connections needs to equal the number of items"
            )
            raise ValueError(msg)
    elif (not source_is_internal) and (not target_is_internal):
        if len(segment_items) + 1 != len(segment_connections):
            msg = (
                "With both source and target not internal, the number "
                "of items needs to be one less than the connections"
            )
            raise ValueError(msg)

    # Connect each connection of the segment
    for index, connection in enumerate(segment_connections):
        item_index = index - 1 if source_is_internal else index
        # Connect source of connection
        if index == 0 and not source_is_internal:
            _connect_piping_connection(
                source_connector_item,
                piping_connection=connection,
                connector_node=source_connector_node,
                as_source=True,
            )
        else:
            source_item = segment_items[item_index - 1]
            if connectivity_convention == PipingConnectionConvention.IN_NODE_0_OUT_NODE_1:
                source_node = source_item.nodes[1]
            elif connectivity_convention == PipingConnectionConvention.USE_ITEMS:
                source_node = None
            _connect_piping_connection(
                source_item,
                piping_connection=connection,
                connector_node=source_node,
                as_source=True,
            )

        # Connect target of connection
        if index == len(segment_connections) - 1 and not target_is_internal:
            _connect_piping_connection(
                target_connector_item,
                piping_connection=connection,
                connector_node=target_connector_node,
            )
        else:
            target_item = segment_items[item_index]
            if connectivity_convention == PipingConnectionConvention.IN_NODE_0_OUT_NODE_1:
                target_node = target_item.nodes[0]
            elif connectivity_convention == PipingConnectionConvention.USE_ITEMS:
                target_node = None
            _connect_piping_connection(
                target_item,
                piping_connection=connection,
                connector_node=target_node,
            )

    # Create the piping network segment and returns it
    new_segment = piping.PipingNetworkSegment(
        items=segment_items, connections=segment_connections, **segment_kwargs
    )
    return new_segment


def construct_new_segment_already_connected(
    segment_items: list[piping.PipingNetworkSegmentItem],
    segment_connections: list[piping.PipingConnection],
    source_node_index: int | None = None,
    target_node_index: int | None = None,
    **segment_kwargs,
) -> piping.PipingNetworkSegment:
    """Constructs a new piping network segment from already connected items and connections.

    Items and connections are first ordered according to their connectivity. If the connections are
    invalid, ValueErrors are raised by the sort_connected_items_and_connections function.

    Parameters
    ----------
    segment_items : list[piping.PipingNetworkSegmentItem]
        The list of items that are part of the segment.
    segment_connections : list[piping.PipingConnection]
        The list of connections that are part of the segment.
    source_node_index : int|None, optional
        The index of the source node in the source item. Only used if the target item is internal,
        by default None.
    target_node_index : int|None, optional
        The index of the target node in the target item. Only used if the target item is internal,
        by default None.

    Returns
    -------
    piping.PipingNetworkSegment
        The newly constructed piping network segment.

    Raises
    ------
    ValueError
        If the items and connections are not connected in a valid way.
    """

    # First, order the segment connections and items
    sorted_items, sorted_connections = sort_connected_items_and_connections(
        segment_items, segment_connections
    )

    # Create the piping network segment
    if sorted_connections:
        source_item = sorted_connections[0].sourceItem
        target_item = sorted_connections[-1].targetItem
    else:
        # In this case, there should only be one item in the segment
        if len(sorted_items) != 1:
            raise ValueError("No connections and more than one item in the segment.")
        source_item = sorted_items[0]
        target_item = sorted_items[0]
    new_segment = piping.PipingNetworkSegment(
        items=sorted_items,
        connections=sorted_connections,
        sourceItem=source_item,
        targetItem=target_item,
        **segment_kwargs,
    )

    # Assign segment source and target nodes: These are the same as the source and target nodes of
    # the first and last connection, unless these are nodes in internal items. In that case, assign
    # the nodes according to the piping convention:
    if source_item in new_segment.items:
        if source_node_index is not None:
            new_segment.sourceNode = source_item.nodes[source_node_index]
        else:
            pass  # No assignment needs to be done, as the source node is already None
    else:
        if source_node_index is not None:
            raise ValueError(
                "Source node index is not None, but node already inferred from connection."
            )
        new_segment.sourceNode = sorted_connections[0].sourceNode

    if target_item in new_segment.items:
        if target_node_index is not None:
            new_segment.targetNode = target_item.nodes[1]
        else:
            pass  # No assignment needs to be done, as the target node is already None
    else:
        if target_node_index is not None:
            raise ValueError(
                "Target node index is not None, but node already inferred from connection."
            )
        new_segment.targetNode = sorted_connections[-1].targetNode

    return new_segment


def insert_item_to_segment(
    the_segment: piping.PipingNetworkSegment,
    position: int | piping.PipingNetworkSegmentItem,
    the_item: piping.PipingNetworkSegmentItem,
    the_connection: piping.PipingConnection,
    item_target_node_index: int = None,
    item_source_node_index: int = None,
    insert_before: bool = False,
) -> None:
    """Inserts a piping item and a piping connection into a piping segment
    before or after a member connection. Intended for segments that are fully
    connected.

    Parameters
    ----------
    the_segment : pipingNetworkSegment
        The segment into which an item and a connection are to be inserted.
    position : Union[int, PipingNetworkSegmentItem]
        Position before or after whicht the insertion happens. Can either be the
        existing item object or the integer index of the item.
    the_connection : PipingConnection
        The connection to be inserted.
    the_item : PipingNetworkSegmentItem
        The item to be inserted
    item_target_node_index : int, optional
        The target node index of the_item to be used for target connection if desired.
        By default None.
    item_source_node_index : int, optional
        The source node index of the_item to be used for source connection if desired.
        By default None.
    insert_before : bool, optional
        If the objects are inserted before the item object, else after.
        By default False.

    Returns
    -------
    None: the_segment is manipulated in place.

    Raises
    ------
    ValueError
        If the arguments passed are not appropriately associated, e.g. if the
        source and target nodes are out of bounds or the position
        object isnt associated to the segment.
    """
    # Some consistency checks on passed arguments
    # Validity check if item not already in the segment
    if the_item in the_segment.items:
        msg = f"Item {the_item} is already member of {the_segment}."
        raise ValueError(msg)
    # Validity check if connection not already in the segment
    if the_connection in the_segment.items:
        msg = f"Connection {the_connection} is already member of {the_segment}."
        raise ValueError(msg)

    for node_index in [item_source_node_index, item_target_node_index]:
        if node_index is not None and node_index >= len(the_item.nodes):
            msg = f"Index {node_index} out of bounds for nodes of item {the_item}"
            raise ValueError(msg)
    # Validity check if the position is in fact a member of the segment if it
    # is a segment item
    if isinstance(position, piping.PipingNetworkSegmentItem) and position not in the_segment.items:
        msg = f"Piping item {position} not associated to segment  {the_segment}."
        raise ValueError(msg)

    # Manage assignemnt of item index and the actual item depending on the type
    # specified in the position argument
    if isinstance(position, piping.PipingNetworkSegmentItem):
        item_at_position = position
        item_index = the_segment.items.index(position)
    else:
        if the_segment.items:
            item_at_position = the_segment.items[position]
        elif position == 0:
            item_at_position = None
        else:
            msg = f"Segment {the_segment} has no items, so position index {position} is invalid."
        item_index = position

    # Find connection at position
    connection_at_position = None
    insertion_at_segment_end = False
    # Manage case of a single pipe segment:
    if not the_segment.items and the_segment.connections:
        connection_at_position = the_segment.connections[0]
    # Otherwise, find connection that currently connects to item at position for later reconnection
    elif the_segment.items:
        for connection in the_segment.connections:
            connection_enditem = connection.targetItem if insert_before else connection.sourceItem
            if connection_enditem == item_at_position:
                connection_at_position = connection
                break
    # Case of a segment without items or connections
    else:
        connection_at_position = None

    # If no connection at position is found, this means we are inserting at segment end or the segment is corrupt
    if connection_at_position is None:
        if (insert_before and item_index == 0) or (
            not insert_before and item_index == len(the_segment.items)
        ):
            insertion_at_segment_end = True
        else:
            msg = (
                f"No connection found connecting to the item {item_at_position} at given position "
                f"and item is not at the end. Segment {the_segment} may be corrupt."
            )
            raise DexpiCorruptPipingSegmentException(msg)

    if insert_before:
        # Connect the_item with the_connection
        the_connection.sourceItem = the_item
        if item_source_node_index is not None:
            the_connection.sourceNode = the_item.nodes[item_source_node_index]
        else:
            the_connection.sourceNode = None

        if not insertion_at_segment_end:
            # Connect piping target to the original target of the obj_at_position
            the_connection.targetNode = connection_at_position.targetNode
            the_connection.targetItem = connection_at_position.targetItem
            # Reconnect the connection_at_position target
            connection_at_position.targetItem = the_item
            if item_target_node_index is not None:
                connection_at_position.targetNode = the_item.nodes[item_target_node_index]
            else:
                connection_at_position.targetNode = None
            # Define connection index for insertion of new objects
            connection_index = the_segment.connections.index(connection_at_position) + 1
        else:
            # Connect piping target to the previous source of the segment
            the_connection.targetNode = the_segment.sourceNode
            the_connection.targetItem = the_segment.sourceItem
            # Reconnect the segment source (=target of the item as per Dexpi convention)
            the_segment.sourceItem = the_item
            if item_target_node_index is not None:
                the_segment.sourceNode = the_item.nodes[item_target_node_index]
            else:
                the_segment.sourceNode = None
            connection_index = 0
    else:
        # Connect the_item with the_connection
        the_connection.targetItem = the_item
        if item_target_node_index is not None:
            the_connection.targetNode = the_item.nodes[item_target_node_index]
        else:
            the_connection.targetNode = None
        if not insertion_at_segment_end:
            # Connect piping source to the original source of the obj_at_position
            the_connection.sourceNode = connection_at_position.sourceNode
            the_connection.sourceItem = connection_at_position.sourceItem
            # Reconnect the piping_obj source
            connection_at_position.sourceItem = the_item
            if item_source_node_index is not None:
                connection_at_position.sourceNode = the_item.nodes[item_source_node_index]
            else:
                connection_at_position.sourceNode = None

            # Define connection index for insertion of new objects
            connection_index = the_segment.connections.index(connection_at_position)
            item_index += 1
        else:
            # Connect piping source to the previous target of the segment
            the_connection.sourceNode = the_segment.targetNode
            the_connection.sourceItem = the_segment.targetItem
            # Reconnect the segment target (=source of the item as per Dexpi convention)
            the_segment.targetItem = the_item
            if item_source_node_index is not None:
                the_segment.targetNode = the_item.nodes[item_source_node_index]
            else:
                the_segment.targetNode = None
            connection_index = len(the_segment.connections)

    # Insert the objects
    the_segment.connections.insert(connection_index, the_connection)
    the_segment.items.insert(item_index, the_item)


def append_item_to_unconnected_segment(
    the_segment: piping.PipingNetworkSegment,
    the_item: piping.PipingNetworkSegmentItem,
    node_index_for_connection: int = None,
    node_index_segment_end: int = None,
    insert_before: bool = False,
) -> None:
    """Appends a piping network segment item to a free piping network segment.

    Parameters
    ----------
    the_segment : PipingNetworkSegment
        The segment to be appended to.
    the_item : PipingNetworkSegmentItem
        The item to be appended.
    node_index_for_connection : int, optional
        The node of the item that should be used for connection, if desired.
        If segment is empty, this node becomes the opposite segment end to
        node_index_segment_end, by default None.
    node_index_segment_end : int, optional
        The node of the item that is used as the new segment end.
        If none, item is used as reference directly, by default None.
    insert_before : bool, optional
        If the item should be appended at the beginning of the segment,
        otherwise the end, by default False. (If segment is empty,
        insert_before=True switches the role of the node indexes)

    Returns
    -------
    None: the_segment is manipulated in place.

    Raises
    ------
    ValueError:
        If connection already in the segment

    ValueError:
        If segment isnt unconnected or not suitable to append an item in that
        position, or if the node is not associated th the object.

    ValueError:
        If a second_node_single_item is passed for segments with items already
        in them

    """
    # Validity check if item not already in the segment
    if the_item in the_segment.items:
        msg = f"Item {the_item} is already member of {the_segment}."
        raise ValueError(msg)

    # Validity check if the segment is unconnected
    if insert_before:
        if the_segment.sourceItem is not None:
            msg = (
                f"Segment {the_segment} has a source and isn't unconnected. "
                f"Consider using insert_item_to_segment instead"
            )
            raise ValueError(msg)
    else:
        if the_segment.targetItem is not None:
            msg = (
                f"Segment {the_segment} has a target and isn't unconnected. "
                f"Consider using insert_item_to_segment instead"
            )
            raise ValueError(msg)

    # Find last connection and item. Last item is found as the segment endpoint
    # with segment items as candidates, which returns None if its None
    # alltogether OR if it isnt among the segment items internally
    # (the latter requires the segment connection check above)
    if the_segment.connections:
        last_connection = find_final_connection(the_segment, as_source=insert_before)
        last_item = last_connection.sourceItem if insert_before else last_connection.targetItem
        last_item = last_item if last_item in the_segment.items else None

    # Manage case segment has no connection (is empty or consists of one item):
    else:
        last_connection = None
        if not the_segment.items:
            last_item = None
        elif len(the_segment.items) == 1:
            last_item = the_segment.items[0]
        else:
            msg = (
                f"The segment {the_segment} has multiple items but no "
                f"connections and may be corrupt"
            )
            raise DexpiCorruptPipingSegmentException(msg)

    # Validity check if final object is a connection and can be appended
    if last_item is not None:
        raise ValueError(
            f"Final object in segment {the_segment} is an item. Cannot add new item {the_item}"
        )

    # Determine connectors
    internal_connector_item = the_item
    if node_index_for_connection is not None:
        internal_connector_node = the_item.nodes[node_index_for_connection]
    else:
        internal_connector_node = None
    segment_connector_item = the_item
    if node_index_segment_end is not None:
        segment_connector_node = the_item.nodes[node_index_segment_end]
    else:
        segment_connector_node = None

    if last_connection is not None:
        _connect_piping_connection(
            internal_connector_item,
            piping_connection=last_connection,
            connector_node=internal_connector_node,
            as_source=insert_before,
        )
    # Case segment has no connection and needs the other end reconnected to the item too.
    else:
        _connect_piping_connection(
            segment_connector_item,
            piping_segment=the_segment,
            connector_node=segment_connector_node,
            as_source=not insert_before,
        )

    _connect_piping_connection(
        segment_connector_item,
        piping_segment=the_segment,
        connector_node=segment_connector_node,
        as_source=insert_before,
    )

    if insert_before:
        the_segment.items.insert(0, the_item)
    else:
        the_segment.items.append(the_item)


def append_connection_to_unconnected_segment(
    the_segment: piping.PipingNetworkSegment,
    the_connection: piping.PipingConnection,
    node_index_for_connection: int = None,
    insert_before: bool = False,
) -> None:
    """Appends a connection object to a free piping network segment.

    Parameters
    ----------
    the_segment : PipingNetworkSegment
        The segment to be appended to.
    the_connection : PipingConnection
        The connection to be appended.
    node_index_for_connection : int, optional
        The node index of the final item in the segment that should be used for
        connection if desired, by default None.
    insert_before : bool, optional
        If the connection should be appended at the beginning of the segment,
        otherwise the end, by default False.

    Returns
    -------
    None: the_segment is manipulated in place.

    Raises
    ------
    ValueError:
        If connection already in the segment

    ValueError:
        If segment isnt unconnected or not suitable to append a connection in
        that position, or if the node is not associated th the object.

    """
    # Validity check if connection not already in the segment
    if the_connection in the_segment.connections:
        msg = f"Connection {the_connection} is already member of {the_segment}."
        raise ValueError(msg)
    # Find last connection and item. Last item is found as the segment endpoint
    # with segment items as candidates, which returns None if its None
    # alltogether OR if it isnt among the segment items internally
    if the_segment.connections:
        last_connection = find_final_connection(the_segment, as_source=insert_before)
        last_item = last_connection.sourceItem if insert_before else last_connection.targetItem
        last_item = last_item if last_item in the_segment.items else None

    # Manage case segment has no connection (is empty or consists of one item):
    else:
        last_connection = None
        if not the_segment.items:
            last_item = None
        elif len(the_segment.items) == 1:
            last_item = the_segment.items[0]
        else:
            msg = (
                f"The segment {the_segment} has multiple items but no "
                f"connections and may be corrupt"
            )
            raise DexpiCorruptPipingSegmentException(msg)

    # Validity check if the segment is unconnected and ends in an item
    if last_item is None and the_segment.items:
        msg = (
            f"Final object in segment {the_segment} is a connection or "
            f"outside of the segment (meaning it's already connected)."
            f"In both cases: Can't add connection {the_connection}"
        )
        raise ValueError(msg)
    connector_item = last_item
    if node_index_for_connection is not None and last_item is not None:
        connector_node = last_item.nodes[node_index_for_connection]
    else:
        connector_node = None

    # Connect
    if insert_before:
        _connect_piping_connection(
            connector_item,
            the_connection,
            connector_node=connector_node,
            as_source=False,
        )
        the_segment.connections.insert(0, the_connection)
        the_segment.sourceNode = the_connection.sourceNode
        the_segment.sourceItem = the_connection.sourceItem
    else:
        _connect_piping_connection(
            connector_item,
            the_connection,
            connector_node=connector_node,
            as_source=True,
        )
        the_segment.connections.append(the_connection)
        the_segment.targetNode = the_connection.targetNode
        the_segment.targetItem = the_connection.targetItem


def find_final_connection(
    the_segment: piping.PipingNetworkSegment, as_source: bool = False
) -> piping.PipingConnection:
    """Finds the first or last connection object in the_segment. It does so by
    comparing the source and target objects of the segment and the connections.
    Note that in a valid segment, these should be the first or final connection.
    However, this method includes some validity checks, so it is recommended to
    use this instead.

    Parameters
    ----------
    the_segment : pipingNetworkSegment
        The segment whose final connection is to befound.
    as_source : bool, optional
        If the first connection should be found, else last, by default False.

    Returns
    -------
    pipingConnection
        The first or last connection.

    Raises
    ------
    DexpiCorruptPipingSegmentException
        If no connection with the same source and target info as the segment is
        found.
    """
    if not the_segment.connections:
        raise ValueError(f"Segment {the_segment} doesn't have any connections")
    final_connection = None
    # Find the connection with the same source/target info as segment
    for connection in the_segment.connections:
        if as_source:
            if connection.sourceItem is the_segment.sourceItem:
                final_connection = connection
        else:
            if connection.targetItem is the_segment.targetItem:
                final_connection = connection
    # Raise exception if None was found
    if final_connection is None:
        msg = (
            f"Piping segment {the_segment} has no connections with the same "
            f"{'source' if as_source else 'target'} and may be corrupt."
        )
        raise DexpiCorruptPipingSegmentException(msg)

    final_connection_index = the_segment.connections.index(final_connection)
    what_index_should_be = 0 if as_source else len(the_segment.connections) - 1
    if final_connection_index != what_index_should_be:
        msg = (
            f"The final connection found in segment {the_segment} is not in the"
            f"correct position {'0' if as_source else '-1'}."
        )
        raise DexpiCorruptPipingSegmentException(msg)

    return final_connection


def get_unconnected_piping_segments(
    conceptual_model: dexpiModel.ConceptualModel, as_source=False
) -> list[piping.PipingNetworkSegment]:
    """
    Returns a list of unconnected piping segments ending in a connection in the conceptual model.

    Parameters
    ----------
    conceptual_model : ConceptualModel
        The model to be analyzed.
    as_source : bool, optional
        Whether to look for unconnected sources or targets in piping segments.
        Defaults to False.

    Returns
    -------
    list[PipingNetworkSegment]
        The list of identified unconnected segments.
    """
    unconnected_segments = []
    for piping_network_system in conceptual_model.pipingNetworkSystems:
        for piping_network_segment in piping_network_system.segments:
            if as_source:
                if piping_network_segment.sourceItem is None:
                    unconnected_segments.append(piping_network_segment)
            else:
                if piping_network_segment.targetItem is None:
                    unconnected_segments.append(piping_network_segment)

    return unconnected_segments


def traverse_items_and_connections(
    all_items: list[piping.PipingNetworkSegmentItem],
    all_connections: list[piping.PipingConnection],
    start_element: piping.PipingNetworkSegmentItem | piping.PipingConnection,
    end_condition: piping.PipingNetworkSegmentItem
    | piping.PipingConnection
    | Callable[[piping.PipingNetworkSegmentItem | piping.PipingConnection], bool],
    reverse=False,
) -> list[piping.PipingNetworkSegmentItem | piping.PipingConnection]:
    """
    Traverses piping items and connections until the end condition is met.

    The traversal is done in a depth-first manner, starting from the specified start element.
    Branching decisions are inferred from the order of the connections in the list of all connections.
    Branches that start with connections that are higher in the list are traversed first.
    The traversal can be done in reverse order by setting the reverse parameter to True.

    Parameters
    ----------
    all_items : list[piping.PipingNetworkSegmentItem]
        List of all items in the piping network segment.
    all_connections : list[piping.PipingConnection]
        List of all connections in the piping network segment.
    start_element : piping.PipingNetworkSegmentItem|piping.PipingConnection
        The element from which to start the traversal.
    end_condition : piping.PipingNetworkSegmentItem|piping.PipingConnection|
                    Callable[[piping.PipingNetworkSegmentItem|piping.PipingConnection], bool]
        The condition that determines when to stop the traversal. This can be a specific element to
        be encountered or a callable function for more complex end conditions.
    reverse : bool, optional
        Whether to traverse in reverse order. Defaults to False.

    Returns
    -------
    list[piping.PipingNetworkSegmentItem|piping.PipingConnection]
        A list of traversed elements.

    Raises
    ------
    PipingTraversalException
        If a circle is encountered or if the traversal cannot continue due to invalid connections.
    """

    # Initialize the traversal
    traversed_elements: list[piping.PipingNetworkSegmentItem | piping.PipingConnection] = [
        start_element
    ]

    # Determine if the start element is a connection or an item
    if isinstance(start_element, piping.PipingNetworkSegmentItem):
        last_was_connection = False
        current_item = start_element
        current_connection = None
    elif isinstance(start_element, piping.PipingConnection):
        last_was_connection = True
        current_item = None
        current_connection = start_element
    else:
        raise TypeError(
            "start_element must be either a PipingNetworkSegmentItem or a PipingConnection"
        )

    # Check if the end condition is a callable function or a specific item/connection.
    # If it's a specific item/connection, create a function to check for equality.
    if isinstance(end_condition, piping.PipingNetworkSegmentItem | piping.PipingConnection):
        end_element = end_condition

        def end_condition_func(
            element: piping.PipingNetworkSegmentItem | piping.PipingConnection,
        ) -> bool:
            return element == end_element

        end_condition = end_condition_func

    if end_condition(start_element):
        return traversed_elements

    # Begin the traversal loop
    while True:
        # Case: Next is an item (if last_was_connection is True)
        if last_was_connection:
            # Get next item
            next_item = (
                current_connection.targetItem if not reverse else current_connection.sourceItem
            )

            # Check if the next item is invalid for further traversal
            if next_item is None:
                msg = f"The connection has no {'source' if reverse else 'target'} item. Cannot traverse further."
                raise PipingTraversalException(msg)
            if next_item not in all_items:
                msg = "The target item is not in the list of all items. Cannot traverse further."
                raise PipingTraversalException(msg)
            if next_item in traversed_elements:
                msg = "Circle encountered: The target item has already been traversed. Cannot traverse further."
                raise PipingTraversalException(msg)

            # Append the next item to the traversed elements
            traversed_elements.append(next_item)
            current_item = next_item
            last_was_connection = False

            # Check if the end condition is met. If so, break the loop.
            if end_condition(current_item):
                break

        else:
            # Find all connections originating from the current item
            next_connections = []
            for connection in all_connections:
                connection_item = connection.sourceItem if not reverse else connection.targetItem
                if connection_item == current_item:
                    next_connections.append(connection)

            # If no connections are found, traversal cannot continue
            if not next_connections:
                msg = "The item has no source connections. Cannot traverse further."
                raise PipingTraversalException(msg)

            # If multiple connections are found, handle branching
            elif len(next_connections) > 1:
                branch_traversal = None

                # Attempt to traverse each branch until a valid path is found
                for connection in next_connections:
                    try:
                        # Filter out already traversed items and connections
                        remaining_items = [
                            item for item in all_items if item not in traversed_elements
                        ]
                        remaining_connections = [
                            con for con in all_connections if con not in traversed_elements
                        ]

                        # Recursively traverse the branch
                        branch_traversal = traverse_items_and_connections(
                            remaining_items, remaining_connections, connection, end_condition
                        )
                        # Stop if a valid branch is found
                        break

                    except PipingTraversalException:
                        continue

                # If a valid branch is found, append it to the traversed elements. Otherwise, raise
                # an exception.
                if branch_traversal is not None:
                    return traversed_elements + branch_traversal
                else:
                    msg = "No valid branch found. Cannot traverse further."
                    raise PipingTraversalException(msg)

            # If only one connection is found, continue traversal
            else:
                next_connection = next_connections[0]

                # Check for circular references
                if next_connection in traversed_elements:
                    msg = "Circle encountered: The connection has already been traversed. Cannot traverse further."
                    raise PipingTraversalException(msg)

            # Append the next connection to the traversed elements
            traversed_elements.append(next_connection)
            current_connection = next_connection
            last_was_connection = True

            # Check if the end condition is met. If so, break the loop.
            if end_condition(current_connection):
                break

    # Return the list of traversed elements
    return traversed_elements


def sort_connected_items_and_connections(
    items: list[piping.PipingNetworkSegmentItem], connections: list[piping.PipingConnection]
) -> tuple[list[piping.PipingNetworkSegmentItem], list[piping.PipingConnection]]:
    """
    Sorts the items and connections of a piping network segment in the order of occurrence.

    Parameters
    ----------
    items : list[piping.PipingNetworkSegmentItem]
        The list of items to be sorted.
    connections : list[piping.PipingConnection]
        The list of connections to be sorted.

    Returns
    -------
    tuple[list[piping.PipingNetworkSegmentItem], list[piping.PipingConnection]]
        A tuple containing the sorted items and connections.

    Raises
    ------
    ValueError
        If the segment is not validly connected, such as having multiple starting points
        or disconnected elements.
    """
    # Find the starting element (either an item or a connection)
    start_element = None
    for connection in connections:
        if connection.sourceItem not in items:
            if start_element is None:
                start_element = connection
            else:
                raise ValueError(
                    "Multiple connections found with no source item. Segment is not validly connected."
                )
    if start_element is None:
        for item in items:
            if item not in [connection.targetItem for connection in connections]:
                if start_element is None:
                    start_element = item
                else:
                    raise ValueError(
                        "Multiple items found that are not referenced by any connection. "
                        "Segment is not validly connected."
                    )

    if start_element is None:
        raise ValueError("No valid starting element found. Segment is not validly connected.")

    # Find end element (either an item or a connection)
    end_element = None
    for connection in connections:
        if connection.targetItem not in items:
            if end_element is None:
                end_element = connection
            else:
                raise ValueError(
                    "Multiple connections found with no target item. Segment is not validly connected."
                )
    if end_element is None:
        for item in items:
            if item not in [connection.sourceItem for connection in connections]:
                if end_element is None:
                    end_element = item
                else:
                    raise ValueError(
                        "Multiple items found that are not referenced as a source by any connection. "
                        "Segment is not validly connected."
                    )

    if end_element is None:
        raise ValueError("No valid ending element found. Segment is not validly connected.")

    # Traverse the segment to determine the order of items and connections
    try:
        traversed_elements = traverse_items_and_connections(
            items, connections, start_element, end_element
        )
    except PipingTraversalException as e:
        raise ValueError(f"Traversal failed: {e}")

    # Separate the traversed elements into items and connections
    ordered_items = [
        element
        for element in traversed_elements
        if isinstance(element, piping.PipingNetworkSegmentItem)
    ]
    ordered_connections = [
        element for element in traversed_elements if isinstance(element, piping.PipingConnection)
    ]

    if len(ordered_items) != len(items):
        raise ValueError("Not all items were visited in the segment.")
    if len(ordered_connections) != len(connections):
        raise ValueError("Not all connections were visited in the segment.")

    return ordered_items, ordered_connections


def sort_segment_items_and_connections(the_segment: piping.PipingNetworkSegment) -> None:
    """
    Sorts the connections and items of the segment in the order of occurrence along the segment.

    The first connection and item are determined by the source and target item of the segment. The
    connections and items are then sorted in place.

    Parameters
    ----------
    the_segment : pipingNetworkSegment
        The segment to be sorted.

    Returns
    -------
    None: the_segment is manipulated in place.
    """
    # Sort connections and items in order of occurrence along the segment.
    try:
        items, connections = sort_connected_items_and_connections(
            the_segment.items, the_segment.connections
        )
    except ValueError as e:
        raise DexpiCorruptPipingSegmentException(
            f"Segment {the_segment} is not validly connected. {e}"
        )
    the_segment.connections = connections
    the_segment.items = items


def piping_network_segment_validity_check(
    the_segment: piping.PipingNetworkSegment,
) -> tuple[PipingValidityCode, str]:
    """
    Performs a consistency check on the pipingNetworkSegment.

    Returns an appropriate PipingValidityCode Enum type. Internally, this is done by going
    along all items and connections to see if they form a valid chain.

    Parameters
    ----------
    the_system : pipingNetworkSegment
        The piping network segment to be checked for consistency.

    Returns
    -------
    (PipingValidityCode, str)
        An Enum type indicating the validity status of the piping network
        segment. msg contains the corresponding error message.
    """

    visited_items = []
    visited_connections = []

    # First, go through connections to find the first connection of the segment.
    # This should have the same source spec as the PNS (at least, this is our
    # interpretation of the proteus spec. Adjust in future if otherwise)
    first_connection = None
    first_is_found = False
    for connection in the_segment.connections:
        # Find the first connection in the segment
        if the_segment.sourceItem == connection.sourceItem:
            first_connection = connection
            if not first_is_found:
                first_is_found = True
            else:
                msg = (
                    "At least two pipes in this segment have the same "
                    "piping input as the parent segment, should be one."
                )
                return (PipingValidityCode.INTERNAL_VIOLATION, msg)
    if first_connection is None and the_segment.connections:
        msg = "No piping connection found with the same piping input as the parent segment"
        return (PipingValidityCode.CONNECTION_CONVENTION_VIOLATION, msg)
    current_connection = first_connection
    visited_connections.append(current_connection)
    # Find the first item as source of the first pipe. Is none if the source
    # is outside the segment
    first_item = the_segment.sourceItem if the_segment.sourceItem in the_segment.items else None
    if first_item is not None:
        visited_items.append(first_item)
        current_item = first_item

    # Iterate along the pns one connection and item at a time to find all
    # connected segment members
    while True:
        # Find current connections destination
        current_item = current_connection.targetItem
        # Check if the end of the segment is reached, and finish. The
        # destination could be none, which is a valid case only at the end of
        # the segment
        if current_item is None and the_segment.targetItem is not None:
            msg = f"No destination to pipe {current_connection} referenced "
            return (PipingValidityCode.INTERNAL_VIOLATION, msg)
        if current_item in visited_items:
            msg = f"Item {current_item} referenced as destination twice inone segment"
            return (PipingValidityCode.INTERNAL_VIOLATION, msg)
        if current_item is not None:
            visited_items.append(current_item)
        if the_segment.targetItem == current_item:
            break
        # Otherwise, find the next connection. Return internal violation if none
        # found
        for connection in the_segment.connections:
            connection_found = False
            if connection.sourceItem == current_item:
                current_connection = connection
                visited_connections.append(current_connection)
                connection_found = True
                break
        if not connection_found:
            if len(visited_connections) != len(the_segment.connections):
                msg = (
                    "Piping network segment is interrupted, last connected "
                    "pipe does and not share the same destination as the segment and not all connections are visited"
                )
                return (PipingValidityCode.INTERNAL_VIOLATION, msg)
            else:
                msg = (
                    "Final pipe does not share its destination item with the piping network segment"
                )
                return (PipingValidityCode.CONNECTION_CONVENTION_VIOLATION, msg)

    # Check if there are connections or pipes in the segment that werent
    # visited, in which case it is corrupt
    if len(visited_connections) < len(the_segment.connections):
        msg = "Not all connections in the segment were visited"
        return (PipingValidityCode.INTERNAL_VIOLATION, msg)
    if len(visited_items) < len(the_segment.items):
        msg = "Not all items in the segment were visited"
        return (PipingValidityCode.INTERNAL_VIOLATION, msg)

    # Check if the order of the connections and items is the order of occurrence
    for segment_connection, visited_connection in zip(the_segment.connections, visited_connections):
        if segment_connection != visited_connection:
            msg = "Segment connections not in right order"
            return (PipingValidityCode.INTERNAL_VIOLATION, msg)
    for segment_item, visited_item in zip(the_segment.items, visited_items):
        if segment_item != visited_item:
            msg = "Segment item not in right order"
            return (PipingValidityCode.INTERNAL_VIOLATION, msg)

    # Investigate if all nodes referenced are also part of the respective item
    elements_to_examine = [the_segment]
    elements_to_examine.extend(visited_connections)
    for element in elements_to_examine:
        for item, node, type_str in zip(
            [element.sourceItem, element.targetItem],
            [element.sourceNode, element.targetNode],
            ["source", "target"],
        ):
            if item is None and node is not None:
                msg = f"{element} has a {type_str} node but no {type_str} item"
                return (PipingValidityCode.INTERNAL_VIOLATION, msg)
            if item is not None and node is not None:
                if node not in item.nodes:
                    msg = f"{element} {type_str} node not a member of its {type_str} item"
                    return (PipingValidityCode.INTERNAL_VIOLATION, msg)

    # If no violation was encountered above, the segment is valid
    return (PipingValidityCode.VALID, "Segment valid")


def add_system_attributes_to_segment(
    the_system: piping.PipingNetworkSystem,
) -> piping.PipingNetworkSystem:
    """
    Adds the attributes of the piping network system to the segment if they are not
    already set.

    Parameters
    ----------
    the_system : PipingNetworkSystem
        The piping network system whose segments are to be updated.

    Returns
    -------
    PipingNetworkSystem
        The updated piping network system.
    """
    # Get all data attributes from the system
    system_attrs = get_data_attributes(the_system)
    # Get attribute names from the first segment (all segments have same attributes)
    if not the_system.segments:
        return the_system
    segment_attr_names = get_data_attributes(the_system.segments[0]).keys()
    # Only consider attributes present in both
    common_attr_names = set(system_attrs.keys()) & set(segment_attr_names)
    for segment in the_system.segments:
        for attr_name in common_attr_names:
            seg_value = getattr(segment, attr_name)
            sys_value = system_attrs[attr_name]
            if seg_value is None and sys_value is not None:
                setattr(segment, attr_name, sys_value)
    return the_system


def _connect_piping_connection(
    connector_item: piping.PipingSourceItem | piping.PipingTargetItem,
    piping_connection: piping.PipingConnection | None = None,
    piping_segment: piping.PipingNetworkSegment | None = None,
    connector_node: piping.PipingNode | None = None,
    as_source: bool = False,
    force_reconnect: bool = False,
) -> None:
    """
    Connects the pipe to the target connector object.

    If the connector object is a PipingNode, the connection is implemented via
    node connection. Otherwise, a connection via Source or TargetItem is
    attempted. Raises an error if the piping connection is already connected
    unless `force_reconnect` is True.

    Parameters
    ----------
    connector_item : Union[PipingSourceItem, PipingTargetItem]
        The item to which the pipe will be connected.
    piping_connection : PipingConnection, optional
        The piping connection to be reconnected. If not passed, then
        reconnection only performed on the segment
    piping_segment : PipingNetworkSegment, optional
        Applies the reconnection to the piping segment too if passed along.
    connector_node: PipingNode, optional
        Optionally, the node of connector_item to be connected to. Must be a
        member of connector_item
    as_source : bool, optional
        If True, the connection is established as source, else as target.
        Defaults to False.
    force_reconnect : bool, optional
        If False, raises an exception if the piping connection is already
        connected. Defaults to False.

    Returns
    -------
    None
        This function modifies the state of the piping connection but does
        not return any value.

    Raises
    ------
    ConnectionException
        If the piping connection is already connected, and `force_reconnect`
        is False.
    ValueError
        If the piping_connection and piping_segment are found to be faulty or
        do not fit together, or if the optional connector_node is not associated to the connector_item
    """
    if connector_item is None and connector_node is not None:
        msg = "Cannot have a node without an item for connections."
        raise ValueError(msg)
    if connector_node is not None:
        if connector_node not in connector_item.nodes:
            msg = f"Piping node {connector_node} not associated to item {connector_item}"
            raise ValueError(msg)

    def raise_exception_if_connection_conflict(connection_object, as_source) -> None:
        """Raise a DexpiConnectionException if the object is already connected"""
        if as_source and (
            connection_object.sourceNode is not None or connection_object.sourceItem is not None
        ):
            raise DexpiConnectionException(
                f"{type(connection_object)} object: {connection_object} already has a source."
            )
        elif not as_source and (
            connection_object.targetNode is not None or connection_object.targetItem is not None
        ):
            raise DexpiConnectionException(
                f"{type(connection_object)} object: {connection_object} already has a target."
            )

    def reconnect_connection_object(conntection_object, item, node, as_source) -> None:
        """Set the source/target connector to the item and node specified"""
        if as_source:
            conntection_object.sourceNode = None
            conntection_object.sourceItem = None
            conntection_object.sourceItem = item
            if connector_node is not None:
                conntection_object.sourceNode = node

        else:
            conntection_object.targetNode = None
            conntection_object.targetItem = None
            conntection_object.targetItem = item
            if connector_node is not None:
                conntection_object.targetNode = node

    if piping_segment is not None and piping_connection is not None:
        final_segment_connection = find_final_connection(piping_segment, as_source=as_source)
        if final_segment_connection != piping_connection:
            msg = f"{piping_connection} is not the final connection of {piping_segment}"
            raise ValueError(msg)

    # check if connection already exists.
    if not force_reconnect:
        if piping_connection is not None:
            raise_exception_if_connection_conflict(piping_connection, as_source)
        if piping_segment is not None:
            raise_exception_if_connection_conflict(piping_segment, as_source)

    # Perform reconnection
    if piping_connection is not None:
        reconnect_connection_object(piping_connection, connector_item, connector_node, as_source)
    if piping_segment is not None:
        reconnect_connection_object(piping_segment, connector_item, connector_node, as_source)
