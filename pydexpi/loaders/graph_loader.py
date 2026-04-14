import json
from copy import deepcopy
from enum import Enum
from typing import Literal

import networkx as nx
from networkx import MultiDiGraph

import pydexpi.toolkits.base_model_utils as bmt
import pydexpi.toolkits.equipment_toolkit as et
import pydexpi.toolkits.model_toolkit as mt
from pydexpi.dexpi_classes.pydantic_classes import (
    DexpiBaseModel,
    DexpiDataTypeBaseModel,
    DexpiModel,
    RepresentationGroup,
    RepresentationTypeGroup,
    ShapeUsage,
)


class GraphLoader:
    """Loads a DEXPI model instance into a NetworkX MultiDiGraph."""

    def dexpi_to_graph(self, dexpi_model: DexpiModel) -> MultiDiGraph:
        """
        Parse a pyDEXPI model into a NetworkX graph representation.

        Parameters
        ----------
        dexpi_model : DexpiModel
            The pyDEXPI model to be parsed into a NetworkX graph.

        Returns
        -------
        MultiDiGraph
            The parsed NetworkX graph representation of the pyDEXPI model.
        """
        # Reset plant graph and set dexpi model
        self.plant_graph = MultiDiGraph()
        self.plant_model = dexpi_model

        # Call and return parse to plant
        return self.parse_dexpi_to_graph(dexpi_model)

    def graph_to_dexpi(self, plant_graph: MultiDiGraph) -> DexpiModel:
        """Parsing the example graph back to pyDEXPI is not supported yet."""
        raise NotImplementedError

    def validate_graph_format(self, plant_graph):
        """Validate a graph against the graph format.

        This method is not yet implemented. The ``plant_graph`` parameter is
        accepted to define the public API and will be used to perform
        validation in a future implementation.
        """
        _ = plant_graph  # parameter is currently unused; kept for future validation logic
        raise NotImplementedError

    def parse_dexpi_to_graph(self, dexpi_model: DexpiModel) -> nx.MultiDiGraph:
        """Parse a DEXPI model into a NetworkX multigraph.

        Parameters
        ----------
        dexpi_model : DexpiModel
            The DEXPI model to parse. Must contain a ``conceptualModel`` attribute.

        Returns
        -------
        nx.MultiDiGraph
            Nodes are DEXPI instances; edges are labelled ``"composition"`` or
            ``"reference"``.

        Notes
        -----
        Updates ``self.plant_model`` and ``self.plant_graph`` as a side effect.
        All ``DexpiBaseModel`` instances are included.
        """
        dexpi_graph = nx.MultiDiGraph()

        # Collect all DexpiBaseModel instances
        all_instances = mt.get_all_instances_in_model(dexpi_model.conceptualModel, None)
        all_instances = [i for i in all_instances if isinstance(i, DexpiBaseModel)]

        # First pass: add nodes with attributes
        self._add_nodes(dexpi_graph, all_instances)

        # Second pass: add edges from composition and reference attributes
        self._add_edges(dexpi_graph, all_instances)

        self.plant_model = dexpi_model
        self.plant_graph = dexpi_graph

        return dexpi_graph

    def _clean_unit(self, unit_str: str) -> str:
        """
        Convert unit string to standard format.

        Takes a unit string, splits it by periods, removes any parts containing
        the word 'Unit', and strips and joins the remaining parts into a single string.

        Parameters
        ----------
        unit_str : str
            The unit string to be cleaned.

        Returns
        -------
        str
            The cleaned unit string in standard format.
        """
        parts = unit_str.split(".")
        parts = [part for part in parts if "Unit" not in part]
        parts = [part.strip() for part in parts]
        value_unit = " ".join(parts)

        return value_unit

    def _add_nodes(self, dexpi_graph: nx.MultiDiGraph, instances: list) -> None:
        """Add nodes with attributes to the graph for each DEXPI instance.

        Iterates over all instances and builds a node attribute dictionary from
        data attributes, class metadata, and optional proteusId. Complex types
        (``DexpiDataTypeBaseModel``, ``Enum``, ``dict``, ``list``) are serialised
        to GraphML-compatible values.

        Parameters
        ----------
        dexpi_graph : nx.MultiDiGraph
            The graph to add nodes to.
        instances : list
            List of ``DexpiBaseModel`` instances to add as nodes.
        """
        for instance in instances:
            data = bmt.get_data_attributes(instance)
            node_attrs = {}
            for attr_name, attr in data.items():
                if isinstance(attr, DexpiDataTypeBaseModel):
                    if hasattr(attr, "value") and hasattr(attr, "unit"):
                        node_attrs[attr_name] = f"{attr.value} {self._clean_unit(attr.unit)}"
                    else:
                        node_attrs[attr_name] = json.dumps(attr.model_dump())
                elif isinstance(attr, Enum):
                    node_attrs[attr_name] = attr.value
                elif isinstance(attr, (dict | list)):
                    node_attrs[attr_name] = json.dumps(attr)
                elif attr is not None:
                    node_attrs[attr_name] = attr

            node_attrs["labels"] = ":".join(
                [cls.__name__ for cls in bmt.get_inheritance_from_dexpi_class(type(instance))]
            )

            if hasattr(instance, "proteusId") and instance.proteusId is not None:
                node_attrs["proteusId"] = instance.proteusId

            node_attrs["label"] = instance.__class__.__name__

            if instance.__class__.__doc__:
                node_attrs["label_description"] = instance.__class__.__doc__.strip()

            dexpi_graph.add_node(instance.id, **node_attrs)

    def _add_edges(self, dexpi_graph: nx.MultiDiGraph, instances: list) -> None:
        """Add composition and reference edges to the graph for each DEXPI instance.

        Iterates over all instances and creates directed edges for both
        composition attributes (structural containment) and reference attributes
        (cross-references between plant items).

        Parameters
        ----------
        dexpi_graph : nx.MultiDiGraph
            The graph to add edges to.
        instances : list
            List of ``DexpiBaseModel`` instances whose relationships are encoded
            as edges.
        """
        for instance in instances:
            for edge_label, get_attrs in [
                ("composition", bmt.get_composition_attributes),
                ("reference", bmt.get_reference_attributes),
            ]:
                for attr_name, attr_field in get_attrs(instance).items():
                    if isinstance(attr_field, DexpiBaseModel):
                        dexpi_graph.add_edge(
                            instance.id, attr_field.id, label=edge_label, attr_name=attr_name
                        )
                    elif isinstance(attr_field, list):
                        for i in attr_field:
                            dexpi_graph.add_edge(
                                instance.id, i.id, label=edge_label, attr_name=attr_name
                            )
                    elif attr_field is None:
                        pass
                    else:
                        raise TypeError(
                            f"Unexpected attribute field type {type(attr_field)!r} for "
                            f"attribute '{attr_name}' in instance {getattr(instance, 'id', '<no id>')}"
                        )

    def _find_shape_usage_in_groups(self, groups: list) -> ShapeUsage | None:
        """Recursively search for ShapeUsage in groups.

        Parameters
        ----------
        groups : list
            A list of group objects to search through.

        Returns
        -------
        ShapeUsage | None
            The first ShapeUsage found, or None if no ShapeUsage is found.
        """
        for group in groups:
            # Check if this is a RepresentationTypeGroup (Static, Symbol, etc.) with elements
            if isinstance(group, RepresentationTypeGroup) and hasattr(group, "elements"):
                for element in group.elements:
                    if isinstance(element, ShapeUsage):
                        return element

            # Recursively check nested groups in RepresentationGroup or other group types
            if hasattr(group, "groups"):
                shape_usage = self._find_shape_usage_in_groups(group.groups)
                if shape_usage:
                    return shape_usage

        return None

    def _search_for_representation(
        self, groups: list, target_instance: DexpiBaseModel
    ) -> ShapeUsage | None:
        """Search for RepresentationGroup representing the target instance.

        Recursively traverses a list of groups to find a RepresentationGroup
        whose 'represents' attribute matches the target_instance. Once found,
        delegates to _find_shape_usage_in_groups to locate the ShapeUsage within
        that group. Also traverses non-RepresentationGroup groups that contain
        nested groups.

        Parameters
        ----------
        groups : list
            A list of group objects to search through. May contain
            RepresentationGroup instances or other group types with nested
            'groups' attributes.
        target_instance : DexpiBaseModel
            The DEXPI instance to find representation for.

        Returns
        -------
        ShapeUsage | None
            The first ShapeUsage found within the matching RepresentationGroup,
            or None if no matching representation or ShapeUsage is found.
        """
        for group in groups:
            if isinstance(group, RepresentationGroup):
                # Check if this RepresentationGroup represents our target
                if hasattr(group, "represents") and group.represents == target_instance:
                    # Found the representation, now find ShapeUsage
                    if hasattr(group, "groups"):
                        return self._find_shape_usage_in_groups(group.groups)

                # Recursively search nested RepresentationGroups
                if hasattr(group, "groups"):
                    result = self._search_for_representation(group.groups, target_instance)
                    if result:
                        return result

            # Also check Static groups and other group types that might contain nested structures
            elif hasattr(group, "groups"):
                result = self._search_for_representation(group.groups, target_instance)
                if result:
                    return result

        return None

    def get_shape_usage(
        self, node_id: str, mode: Literal["shapeusage", "position"] = "shapeusage"
    ) -> dict | None:
        """Extract ShapeUsage information for a given node.

        This function finds the RepresentationGroup associated with a DEXPI object (identified by
        node_id), extracts ShapeUsage information from the graphical representation, and returns
        it as a dictionary of attributes.

        The function searches through the model's diagram structure, looking for RepresentationGroups
        that represent the specified DEXPI object, then extracts ShapeUsage data from Static groups.

        Parameters
        ----------
        node_id : str
            The DEXPI ID of the node to extract ShapeUsage information for.
        mode : Literal["shapeusage", "position"], default="shapeusage"
            Controls which shape usage information to return:
            - ``"position"``: Only return position information as 'x' and 'y' attributes
            - ``"shapeusage"``: Return all shape usage information except shape_id (default)

        Returns
        -------
        dict | None
            A dictionary containing ShapeUsage attributes if found. Depending on mode:
            - position mode: Returns only 'x' and 'y' coordinates
            - shapeusage mode: Returns all attributes except shape_id:
              - shape_name: str - Name of the shape being used
              - position_x: float - X coordinate position
              - position_y: float - Y coordinate position
              - rotation: float - Rotation angle in radians
              - scale_x: float - Horizontal scale factor
              - scale_y: float - Vertical scale factor
              - is_mirrored: bool - Whether the shape is mirrored
              - symbol_registration_number: str | None - Shape's registration number if available
            Returns None if no ShapeUsage is found for this node.

        Examples
        --------
        >>> # Extract shape usage for a specific equipment node
        >>> shape_attrs = loader.get_shape_usage("equipment_123")
        >>> if shape_attrs:
        >>>     print(f"Shape: {shape_attrs['shape_name']}")
        >>>     print(f"Position: ({shape_attrs['position_x']}, {shape_attrs['position_y']})")

        >>> # Extract only position information
        >>> position_attrs = loader.get_shape_usage("equipment_123", mode="position")
        >>> if position_attrs:
        >>>     print(f"Position: ({position_attrs['x']}, {position_attrs['y']})")
        """

        # Check if node exists in graph
        if node_id not in self.plant_graph.nodes:
            return None

        # Search through the diagram structure
        if not hasattr(self.plant_model, "diagram") or self.plant_model.diagram is None:
            return None

        # Get all instances to find the actual object for this node_id
        all_instances = mt.get_all_instances_in_model(self.plant_model.conceptualModel, None)
        target_instance = None
        for instance in all_instances:
            if isinstance(instance, DexpiBaseModel) and instance.id == node_id:
                target_instance = instance
                break

        if target_instance is None:
            return None

        # Start search from diagram groups
        shape_usage = None
        if hasattr(self.plant_model.diagram, "groups"):
            shape_usage = self._search_for_representation(
                self.plant_model.diagram.groups, target_instance
            )

        # Extract attributes if ShapeUsage found
        if shape_usage is None:
            return None

        # Build attributes dictionary based on mode
        if mode == "position":
            # Only return position as 'x' and 'y'
            attrs = {
                "x": shape_usage.position.x,
                "y": shape_usage.position.y,
            }
        else:  # mode == "shapeusage" or any other value
            # Return all shape usage information except shape_id
            attrs = {
                "x": shape_usage.position.x,
                "y": shape_usage.position.y,
                "rotation": shape_usage.rotation,
                "scale_x": shape_usage.scaleX,
                "scale_y": shape_usage.scaleY,
                "is_mirrored": shape_usage.isMirrored,
            }

            # Add shape information (but exclude shape_id)
            if hasattr(shape_usage, "shape") and shape_usage.shape:
                if hasattr(shape_usage.shape, "name") and shape_usage.shape.name is not None:
                    attrs["shape_name"] = shape_usage.shape.name
                if (
                    hasattr(shape_usage.shape, "symbolRegistrationNumber")
                    and shape_usage.shape.symbolRegistrationNumber is not None
                ):
                    attrs["symbol_registration_number"] = shape_usage.shape.symbolRegistrationNumber

        # Filter out any None values to ensure GraphML compatibility
        attrs = {k: v for k, v in attrs.items() if v is not None}

        return attrs

    def embed_shape_usage(
        self,
        shape_usage_mode: Literal["shapeusage", "position"] = "shapeusage",
    ) -> dict[str, int]:
        """Embed ShapeUsage information as node attributes for all nodes in the graph.

        This method iterates through all nodes in the graph and embeds ShapeUsage information
        (position, rotation, scale, shape name, etc.) as node attributes.

        Parameters
        ----------
        shape_usage_mode : Literal["shapeusage", "position"], default="shapeusage"
            Controls which shape usage information to embed:
            - ``"position"``: Only embed position information as 'x' and 'y' attributes
            - ``"shapeusage"``: Embed all shape usage information except shape_id (default)

        Returns
        -------
        dict[str, int]
            A dictionary with statistics about the embedding operation:
            - "processed": Total number of nodes processed
            - "embedded": Number of nodes that had ShapeUsage successfully embedded
            - "skipped": Number of nodes skipped (no ShapeUsage found)

        """
        # Process all nodes
        nodes_to_process = list(self.plant_graph.nodes())

        # Statistics
        processed = 0
        embedded = 0
        skipped = 0

        # Process each node
        for node_id in nodes_to_process:
            # Skip if node was removed (e.g., during graph transformations)
            if node_id not in self.plant_graph.nodes:
                continue

            processed += 1

            # Get shape usage for this node
            shape_attrs = self.get_shape_usage(node_id, mode=shape_usage_mode)

            if shape_attrs:
                # Embed the shape attributes into the node
                self.plant_graph.nodes[node_id].update(shape_attrs)
                embedded += 1
            else:
                skipped += 1

        return {
            "processed": processed,
            "embedded": embedded,
            "skipped": skipped,
        }


class GraphAbstractor:
    """Abstracts a NetworkX MultiDiGraph into a simplified MultiDiGraph."""

    def __init__(self, plant_graph: MultiDiGraph | None = None) -> None:
        """Initialize a new instance of GraphAbstractor.

        Parameters
        ----------
        plant_graph : MultiDiGraph or None, default=None
            The MultiDiGraph to abstract. If None, an empty MultiDiGraph is created.
        """
        self.plant_graph = plant_graph if plant_graph is not None else MultiDiGraph()

    def get_nodes_by_label(self, label: str) -> list[str]:
        """
        Get node IDs that have a specific label in their label attribute.

        Parameters
        ----------
        label : str
            The label to search for in node attributes (case-insensitive exact match).
            Checks both 'label' (single value) and 'labels' (colon-separated inheritance chain).

        Returns
        -------
        list[str]
            A list of node IDs that match the label criteria.

        Examples
        --------
        >>> # Get all equipment nodes
        >>> equipment_nodes = loader.get_nodes_by_label("Equipment")
        >>> # Get all Pipe nodes (won't match PipeOffPageConnector)
        >>> pipe_nodes = loader.get_nodes_by_label("Pipe")
        """
        matching_nodes = []

        for node_id, node_data in self.plant_graph.nodes(data=True):
            # Check 'label' attribute (single class name)
            node_label = node_data.get("label", "")
            if isinstance(node_label, str) and node_label.lower() == label.lower():
                matching_nodes.append(node_id)
                continue

            # Check 'labels' attribute (colon-separated inheritance chain)
            node_labels = node_data.get("labels", "")
            if isinstance(node_labels, str) and node_labels:
                # Split by colon and check for exact match in any of the labels
                labels_list = node_labels.split(":")
                if any(lbl.lower() == label.lower() for lbl in labels_list):
                    matching_nodes.append(node_id)

        return matching_nodes

    def collapse_node_to_edge(
        self,
        node_id: str,
        inherit_attributes: bool = False,
        inherit_connections: bool = False,
    ) -> None:
        """
        Collapse a node into an edge by removing it and creating an edge between predecessor and successor.

        This operation only works for nodes with exactly 1 incoming edge and 1 outgoing edge (1-to-1 connection).
        The node is removed and a direct connection (edge) is created between the predecessor and successor.
        Optionally, the collapsed node's attributes can be inherited by the new edge, and the original edge
        attributes can be preserved.

        Parameters
        ----------
        node_id : str
            The ID of the node to collapse.
        inherit_attributes : bool, default=False
            If True, transfer the node's attributes to the newly created edge as edge attributes.
            The node's ID will be included as an attribute.
        inherit_connections : bool, default=False
            If True, preserve and merge the original edge attributes from both incoming and outgoing edges.
            If False, only create a basic edge without preserving edge attributes.

        Raises
        ------
        ValueError
            If the node is not found in the graph, or if the node doesn't have exactly 1 incoming
            and 1 outgoing edge.

        Examples
        --------
        >>> # Collapse node to edge without inheritance
        >>> loader.collapse_node_to_edge("node_123")

        >>> # Collapse node to edge with node attributes inherited
        >>> loader.collapse_node_to_edge("node_123", inherit_attributes=True)

        >>> # Collapse node to edge with both node attributes and edge connections inherited
        >>> loader.collapse_node_to_edge("node_123", inherit_attributes=True, inherit_connections=True)
        """
        if node_id not in self.plant_graph.nodes:
            raise ValueError(f"Node {node_id} not found in graph")

        # Get all incoming edges (predecessors)
        in_edges = list(self.plant_graph.in_edges(node_id, keys=True, data=True))
        # Get all outgoing edges (successors)
        out_edges = list(self.plant_graph.out_edges(node_id, keys=True, data=True))

        # Check if we have exactly 1-to-1 connection
        if len(in_edges) != 1 or len(out_edges) != 1:
            raise ValueError(
                f"Node {node_id} must have exactly 1 incoming and 1 outgoing edge. "
                f"Found {len(in_edges)} incoming and {len(out_edges)} outgoing edges."
            )

        # Get the single incoming and outgoing edges
        pred_node = in_edges[0][0]
        in_data = in_edges[0][3]
        succ_node = out_edges[0][1]
        out_data = out_edges[0][3]

        # Prepare edge attributes
        new_edge_attrs = {}

        # Get the node's label attribute to use as the edge label
        node_label = self.plant_graph.nodes[node_id].get("label", "")
        if node_label:
            new_edge_attrs["label"] = node_label

        # Inherit node attributes if requested
        if inherit_attributes:
            node_attrs = dict(self.plant_graph.nodes[node_id])
            # Add the node_id as an attribute to track the collapsed node
            node_attrs["collapsed_node_id"] = node_id
            new_edge_attrs.update(node_attrs)

        # Preserve original edge attributes if requested
        if inherit_connections:
            # Combine in_data and out_data, with out_data taking precedence
            new_edge_attrs.update(in_data)
            new_edge_attrs.update(out_data)

        # Add the new edge between predecessor and successor
        # Use the removed node_id as the edge key
        self.plant_graph.add_edge(pred_node, succ_node, key=node_id, **new_edge_attrs)

        # Remove any parallel edges between these nodes
        self._remove_parallel_edges(pred_node, succ_node, exclude_key=node_id)

        # Remove the node (this also removes all connected edges)
        self.plant_graph.remove_node(node_id)

    def collapse_node_to_node(
        self,
        node_id: str,
        to_node_id: str,
        inherit_attributes: bool = False,
        inherit_connections: bool = False,
    ) -> None:
        """
        Collapse a node into another target node by merging their connections and attributes.

        This operation removes the source node and optionally transfers its edges and attributes
        to the target node. All edges connected to the source node can be redirected to the target node.

        Parameters
        ----------
        node_id : str
            The ID of the node to collapse (source node that will be removed).
        to_node_id : str
            The ID of the target node that will absorb the connections and optionally attributes.
        inherit_attributes : bool, default=False
            If True, transfer the source node's attributes to the target node.
            Attributes from the target node take precedence in case of conflicts.
        inherit_connections : bool, default=False
            If True, redirect all edges from the source node to the target node.
            If False, edges are simply removed with the source node.

        Examples
        --------
        >>> # Collapse node to another node (just remove without inheriting)
        >>> loader.collapse_node_to_node("node_123", "node_456")

        >>> # Collapse node with both attributes and connections
        >>> loader.collapse_node_to_node("node_123", "node_456", inherit_attributes=True, inherit_connections=True)

        >>> # Collapse node without inheriting connections (just remove)
        >>> loader.collapse_node_to_node("node_123", "node_456", inherit_connections=False)
        """
        if node_id not in self.plant_graph.nodes:
            raise ValueError(f"Node {node_id} not found in graph")

        if to_node_id not in self.plant_graph.nodes:
            raise ValueError(f"Target node {to_node_id} not found in graph")

        if node_id == to_node_id:
            raise ValueError("Source and target nodes cannot be the same")

        # Inherit attributes if requested
        if inherit_attributes:
            # Get source node attributes
            source_attrs = dict(self.plant_graph.nodes[node_id])
            # Get target node attributes
            target_attrs = dict(self.plant_graph.nodes[to_node_id])

            # Merge attributes: target attributes take precedence
            merged_attrs = {**source_attrs, **target_attrs}

            # Add metadata about the collapsed node
            if "collapsed_from" in merged_attrs:
                # Handle multiple collapses - store as comma-separated string for GraphML compatibility
                existing = merged_attrs["collapsed_from"]
                if isinstance(existing, str):
                    # Convert existing string to list, add new node_id, then back to string
                    node_ids = existing.split(",") + [node_id]
                    merged_attrs["collapsed_from"] = ",".join(node_ids)
                else:
                    # If it's already some other type, convert to string
                    merged_attrs["collapsed_from"] = f"{existing},{node_id}"
            else:
                merged_attrs["collapsed_from"] = node_id

            # Update target node with merged attributes
            self.plant_graph.nodes[to_node_id].update(merged_attrs)

        # Redirect connections if requested
        if inherit_connections:
            # Redirect all incoming edges from source to target
            in_edges = list(self.plant_graph.in_edges(node_id, keys=True, data=True))
            for pred_node, _, key, edge_data in in_edges:
                if pred_node != to_node_id:  # Avoid self-loops unless they existed
                    self.plant_graph.add_edge(pred_node, to_node_id, key=key, **edge_data)

            # Redirect all outgoing edges from source to target
            out_edges = list(self.plant_graph.out_edges(node_id, keys=True, data=True))
            for _, succ_node, key, edge_data in out_edges:
                if succ_node != to_node_id:  # Avoid self-loops unless they existed
                    self.plant_graph.add_edge(to_node_id, succ_node, key=key, **edge_data)

        # Remove the source node (this also removes all its connected edges)
        self.plant_graph.remove_node(node_id)

    def remove_nodes_by_label(self, label: str | list[str], stitch: bool = False) -> int:
        """
        Remove all nodes that have a specific label or labels in their label attribute.

        Parameters
        ----------
        label : str or list[str]
            Single label (str) or list of labels to search for in node attributes
            (case-insensitive substring match). All nodes containing any of these
            labels will be removed.
        stitch : bool, default=False
            If True, nodes with exactly 2 connected edges (incoming + outgoing) will be
            stitched by creating a direct edge between their neighbors before removal.
            Edge type priority for stitching: other > reference > composition.

        Returns
        -------
        int
            The number of nodes removed.

        Examples
        --------
        >>> # Remove all piping nodes (single label)
        >>> count = loader.remove_nodes_by_label("PipingNode")
        >>> print(f"Removed {count} piping nodes")

        >>> # Remove multiple types of nodes at once
        >>> count = loader.remove_nodes_by_label(["PipingNode", "Equipment"])
        >>> print(f"Removed {count} nodes")

        >>> # Remove nodes and stitch their connections
        >>> count = loader.remove_nodes_by_label("PipingNode", stitch=True)
        >>> print(f"Removed and stitched {count} nodes")
        """
        # Normalize label to a list
        if isinstance(label, str):
            labels_list = [label]
        else:
            labels_list = label

        # Collect all nodes to remove
        nodes_to_remove = set()
        for lbl in labels_list:
            matching_nodes = self.get_nodes_by_label(lbl)
            nodes_to_remove.update(matching_nodes)

        # Remove each node
        for node_id in nodes_to_remove:
            if node_id not in self.plant_graph.nodes:
                continue

            # If stitch is enabled, try to stitch nodes with exactly 2 edges
            if stitch:
                in_edges = list(self.plant_graph.in_edges(node_id, keys=True, data=True))
                out_edges = list(self.plant_graph.out_edges(node_id, keys=True, data=True))

                total_edges = len(in_edges) + len(out_edges)

                # Only stitch if node has exactly 2 connected edges
                if total_edges == 2:
                    # Collect all edges with their directions
                    all_edges = []
                    for source, target, key, data in in_edges:
                        all_edges.append(("in", source, target, key, data))
                    for source, target, key, data in out_edges:
                        all_edges.append(("out", source, target, key, data))

                    # Prioritize edges: other > reference > composition
                    def edge_priority(edge):
                        _, _, _, _, data = edge
                        edge_label = data.get("label", "").lower()
                        if edge_label == "composition":
                            return 0
                        elif edge_label == "reference":
                            return 1
                        else:
                            return 2  # other

                    # Sort edges by priority (highest first)
                    sorted_edges = sorted(all_edges, key=edge_priority, reverse=True)

                    # Take the highest priority edge for stitching
                    primary_edge = sorted_edges[0]
                    other_edge = sorted_edges[1]

                    direction1, source1, target1, key1, data1 = primary_edge
                    direction2, source2, target2, key2, data2 = other_edge

                    # Determine the neighbors to stitch
                    if direction1 == "in" and direction2 == "in":
                        # Both incoming: stitch source1 -> source2
                        neighbor1, neighbor2 = source1, source2
                    elif direction1 == "in" and direction2 == "out":
                        # in and out: stitch source1 -> target2
                        neighbor1, neighbor2 = source1, target2
                    elif direction1 == "out" and direction2 == "in":
                        # out and in: stitch source2 -> target1
                        neighbor1, neighbor2 = source2, target1
                    else:  # both outgoing
                        # Both outgoing: stitch target1 -> target2
                        neighbor1, neighbor2 = target2, target1

                    # Create new edge with attributes from the primary edge
                    new_edge_attrs = dict(data1)
                    new_edge_attrs["stitched_from"] = node_id

                    # Add the stitching edge
                    self.plant_graph.add_edge(neighbor1, neighbor2, key=node_id, **new_edge_attrs)

            # Remove the node
            self.plant_graph.remove_node(node_id)

        return len(nodes_to_remove)

    def collapse_node_to_edge_by_label(
        self,
        label: str,
        inherit_attributes: bool = False,
        inherit_connections: bool = False,
    ) -> int:
        """
        Collapse nodes with a specific label to edges.

        This method finds all nodes matching the given label and collapses each one to an edge.
        It handles two cases:
        1. Standard 1-to-1 connection (1 incoming, 1 outgoing edge)
        2. Special case with 0 incoming and 2 outgoing edges, where attr_name determines direction.
           Supports both "sourceItem"/"targetItem" and "source"/"target" attribute name patterns.

        Parameters
        ----------
        label : str
            The label to search for in node attributes (case-insensitive substring match).
            All nodes containing this label will be collapsed to edges if they meet the criteria.
        inherit_attributes : bool, default=False
            If True, transfer the collapsed node's attributes to the newly created edge.
            The node's ID will be included as an attribute.
        inherit_connections : bool, default=False
            If True, preserve and merge the original edge attributes from both incoming and outgoing edges.
            If False, only create a basic edge without preserving edge attributes.

        Returns
        -------
        int
            The number of nodes successfully collapsed to edges.

        Examples
        --------
        >>> # Collapse all PipingNode nodes to edges (just remove without inheritance)
        >>> count = loader.collapse_node_to_edge_by_label("PipingNode")
        >>> print(f"Collapsed {count} nodes to edges")

        >>> # Collapse with node attributes inherited
        >>> count = loader.collapse_node_to_edge_by_label("PipingNode", inherit_attributes=True)

        >>> # Collapse with both node attributes and edge connections inherited
        >>> count = loader.collapse_node_to_edge_by_label("PipingNode", inherit_attributes=True, inherit_connections=True)
        """
        # Get all nodes with the specified label
        nodes_to_collapse = self.get_nodes_by_label(label)
        collapsed_count = 0

        for node_id in nodes_to_collapse:
            # Skip if node was already removed (e.g., as part of a previous collapse)
            if node_id not in self.plant_graph.nodes:
                continue

            # Get incoming and outgoing edges
            in_edges = list(self.plant_graph.in_edges(node_id, keys=True, data=True))
            out_edges = list(self.plant_graph.out_edges(node_id, keys=True, data=True))

            # Case 1: Standard 1-to-1 connection
            if len(in_edges) == 1 and len(out_edges) == 1:
                self.collapse_node_to_edge(
                    node_id,
                    inherit_attributes=inherit_attributes,
                    inherit_connections=inherit_connections,
                )
                collapsed_count += 1

            # Case 2: Special case - 0 incoming, 2 outgoing edges
            elif len(in_edges) >= 0 and len(out_edges) >= 2:
                # Find sourceItem and targetItem based on attr_name
                source_node = None
                target_node = None
                source_edge_data = None
                target_edge_data = None

                for _, succ_node, key, edge_data in out_edges:
                    attr_name = edge_data.get("attr_name", "")
                    # Check for both sourceItem/targetItem and source/target patterns
                    if attr_name in ("sourceItem", "source"):
                        source_node = succ_node
                        source_edge_data = edge_data
                    elif attr_name in ("targetItem", "target"):
                        target_node = succ_node
                        target_edge_data = edge_data

                # Only proceed if we found both source and target
                if source_node is not None and target_node is not None:
                    # Prepare edge attributes
                    new_edge_attrs = {}

                    # Get the node's label attribute to use as the edge label
                    node_label = self.plant_graph.nodes[node_id].get("label", "")
                    if node_label:
                        new_edge_attrs["label"] = node_label

                    # Inherit node attributes if requested
                    if inherit_attributes:
                        node_attrs = dict(self.plant_graph.nodes[node_id])
                        node_attrs["collapsed_node_id"] = node_id
                        new_edge_attrs.update(node_attrs)

                    # Preserve original edge attributes if requested
                    if inherit_connections:
                        # Merge source and target edge data, target takes precedence
                        if source_edge_data:
                            new_edge_attrs.update(source_edge_data)
                        if target_edge_data:
                            new_edge_attrs.update(target_edge_data)

                    # Create edge from sourceItem to targetItem
                    self.plant_graph.add_edge(
                        source_node, target_node, key=node_id, **new_edge_attrs
                    )

                    # Remove any parallel edges between these nodes
                    self._remove_parallel_edges(source_node, target_node, exclude_key=node_id)

                    # Remove the collapsed node
                    self.plant_graph.remove_node(node_id)
                    collapsed_count += 1

            # Case 3: Node with only 1 connected edge - just remove it
            elif len(in_edges) + len(out_edges) == 1:
                # Simply remove the node (impossible to create an edge with only 1 connection)
                self.plant_graph.remove_node(node_id)
                collapsed_count += 1

        return collapsed_count

    def collapse_node_to_node_by_label(
        self,
        label: str,
        target_labels: str | list[str] | None = None,
        inherit_attributes: bool = False,
        inherit_connections: bool = False,
    ) -> int:
        """
        Collapse nodes with a specific label to connected nodes that match target labels.

        This method finds all nodes matching the given label and collapses each one to its
        connected nodes (either successors or predecessors) that match any of the target labels
        and are connected by composition edges. If target_labels is None, all composition-connected
        nodes are considered as targets. The attributes and connections of the collapsed node can
        optionally be inherited by the target nodes.

        The target label matching checks both the 'label' attribute (single value) and 'labels'
        attribute (colon-separated values like "BallValve:OperatedValve:PipingComponent").

        Parameters
        ----------
        label : str
            The label to search for in node attributes (case-insensitive substring match).
            All nodes containing this label will be collapsed.
        target_labels : str, list[str], or None, default=None
            Single label (str) or list of node labels to match for target nodes. Nodes will be
            collapsed to connected nodes (either successors or predecessors) that have labels
            matching the provided label(s). Matching is done against both 'label' and 'labels'
            attributes. If None, collapse to all composition-connected nodes regardless of their labels.
        inherit_attributes : bool, default=False
            If True, transfer the collapsed node's attributes to the target nodes.
            Attributes from the target nodes take precedence in case of conflicts.
        inherit_connections : bool, default=False
            If True, redirect all edges from the collapsed node to the target node.
            If False, edges are simply removed with the collapsed node.

        Returns
        -------
        int
            The number of nodes successfully collapsed.

        Examples
        --------
        >>> # Collapse to a single target label (string)
        >>> count = loader.collapse_node_to_node_by_label("ProcessInstrument", target_labels="Equipment")
        >>> print(f"Collapsed {count} nodes")

        >>> # Collapse all ProcessInstrument nodes to connected Equipment or Actuator nodes
        >>> count = loader.collapse_node_to_node_by_label("ProcessInstrument", target_labels=["Equipment", "Actuator"])
        >>> print(f"Collapsed {count} nodes")

        >>> # Collapse to all composition-connected nodes (no label filtering)
        >>> count = loader.collapse_node_to_node_by_label("ProcessInstrument", target_labels=None)

        >>> # Collapse to specific labels with both attributes and connections inherited
        >>> count = loader.collapse_node_to_node_by_label(
        ...     "ProcessInstrument",
        ...     target_labels=["Equipment"],
        ...     inherit_attributes=True,
        ...     inherit_connections=True
        ... )

        >>> # Collapse without inheriting connections (just remove nodes)
        >>> count = loader.collapse_node_to_node_by_label(
        ...     "ProcessInstrument",
        ...     target_labels="Equipment",
        ...     inherit_connections=False
        ... )
        """
        # Normalize target_labels to a list
        if target_labels is None:
            target_labels_list = None
        elif isinstance(target_labels, str):
            target_labels_list = [target_labels]
        else:
            target_labels_list = target_labels

        # Get all nodes with the specified label
        nodes_to_collapse = self.get_nodes_by_label(label)
        collapsed_count = 0

        for node_id in nodes_to_collapse:
            # Skip if node was already removed (e.g., as part of a previous collapse)
            if node_id not in self.plant_graph.nodes:
                continue

            # Get all composition edges (both incoming and outgoing)
            in_edges = list(self.plant_graph.in_edges(node_id, keys=True, data=True))
            out_edges = list(self.plant_graph.out_edges(node_id, keys=True, data=True))

            # Filter for composition edges
            composition_in_edges = [
                (source, target, key, data) for source, target, key, data in in_edges
            ]
            composition_out_edges = [
                (source, target, key, data) for source, target, key, data in out_edges
            ]

            # Collect potential target nodes from both directions
            target_node_ids = []

            # From predecessors
            for source, _, _, _ in composition_in_edges:
                if source in self.plant_graph.nodes:
                    if target_labels_list is None:
                        target_node_ids.append(source)
                    else:
                        # Check if the node matches any of the target labels
                        if self._node_matches_any_label(source, target_labels_list):
                            target_node_ids.append(source)

            # From successors
            for _, target, _, _ in composition_out_edges:
                if target in self.plant_graph.nodes:
                    if target_labels_list is None:
                        target_node_ids.append(target)
                    else:
                        # Check if the node matches any of the target labels
                        if self._node_matches_any_label(target, target_labels_list):
                            target_node_ids.append(target)

            # Remove duplicates while preserving order
            target_node_ids = list(dict.fromkeys(target_node_ids))

            # Collapse to all matching target nodes (can be one or more)
            if len(target_node_ids) >= 1:
                # First, inherit attributes to ALL target nodes if requested
                if inherit_attributes:
                    source_attrs = dict(self.plant_graph.nodes[node_id])
                    for target_node_id in target_node_ids:
                        if target_node_id == node_id:
                            continue  # Skip if target is the same as source

                        if target_node_id not in self.plant_graph.nodes:
                            continue  # Skip if target node doesn't exist

                        # Get target node attributes
                        target_attrs = dict(self.plant_graph.nodes[target_node_id])

                        # Merge attributes: target attributes take precedence
                        merged_attrs = {**source_attrs, **target_attrs}

                        # Add metadata about the collapsed node
                        if "collapsed_from" in merged_attrs:
                            existing = merged_attrs["collapsed_from"]
                            if isinstance(existing, str):
                                node_ids = existing.split(",") + [node_id]
                                merged_attrs["collapsed_from"] = ",".join(node_ids)
                            else:
                                merged_attrs["collapsed_from"] = f"{existing},{node_id}"
                        else:
                            merged_attrs["collapsed_from"] = node_id

                        # Update target node with merged attributes
                        self.plant_graph.nodes[target_node_id].update(merged_attrs)

                # Then, redirect connections to ALL target nodes if requested
                if inherit_connections:
                    in_edges = list(self.plant_graph.in_edges(node_id, keys=True, data=True))
                    out_edges = list(self.plant_graph.out_edges(node_id, keys=True, data=True))

                    for target_node_id in target_node_ids:
                        if target_node_id == node_id:
                            continue  # Skip if target is the same as source

                        if target_node_id not in self.plant_graph.nodes:
                            continue  # Skip if target node doesn't exist

                        # Redirect all incoming edges from source to this target
                        for pred_node, _, key, edge_data in in_edges:
                            if pred_node != target_node_id:  # Avoid self-loops unless they existed
                                self.plant_graph.add_edge(
                                    pred_node, target_node_id, key=key, **edge_data
                                )

                        # Redirect all outgoing edges from source to this target
                        for _, succ_node, key, edge_data in out_edges:
                            if succ_node != target_node_id:  # Avoid self-loops unless they existed
                                self.plant_graph.add_edge(
                                    target_node_id, succ_node, key=key, **edge_data
                                )

                # Finally, remove the source node
                self.plant_graph.remove_node(node_id)
                collapsed_count += 1

        return collapsed_count

    def _node_matches_any_label(self, node_id: str, target_labels: list[str]) -> bool:
        """
        Check if a node matches any of the target labels.

        This method checks both the 'label' attribute (single value) and 'labels' attribute
        (colon-separated values) to determine if any target label matches.

        Parameters
        ----------
        node_id : str
            The ID of the node to check.
        target_labels : list[str]
            List of labels to match against.

        Returns
        -------
        bool
            True if the node matches any target label, False otherwise.
        """
        if node_id not in self.plant_graph.nodes:
            return False

        node_data = self.plant_graph.nodes[node_id]

        # Check 'label' attribute (single value)
        node_label = node_data.get("label", "")
        if isinstance(node_label, str):
            if any(tl.lower() in node_label.lower() for tl in target_labels):
                return True

        # Check 'labels' attribute (colon-separated values)
        node_labels = node_data.get("labels", "")
        if isinstance(node_labels, str) and node_labels:
            # Split by colon and check each label
            labels_list = node_labels.split(":")
            for label_item in labels_list:
                if any(tl.lower() in label_item.lower() for tl in target_labels):
                    return True

        return False

    def _remove_parallel_edges(self, source_node: str, target_node: str, exclude_key: str) -> None:
        """
        Remove parallel edges between two nodes (in both directions).

        This helper method removes all edges between source_node and target_node
        (in both directions) except the one with the specified exclude_key.

        Parameters
        ----------
        source_node : str
            The source node of the main edge.
        target_node : str
            The target node of the main edge.
        exclude_key : str
            The edge key to exclude from removal (typically the newly created edge).
        """
        edges_to_remove = []

        # Remove parallel edges in the same direction (source_node -> target_node)
        if self.plant_graph.has_edge(source_node, target_node):
            for key in self.plant_graph[source_node][target_node]:
                if key != exclude_key:  # Don't remove the edge we want to keep
                    edges_to_remove.append((source_node, target_node, key))

        # Remove parallel edges in the opposite direction (target_node -> source_node)
        if self.plant_graph.has_edge(target_node, source_node):
            for key in self.plant_graph[target_node][source_node]:
                edges_to_remove.append((target_node, source_node, key))

        # Remove all identified parallel edges
        for edge in edges_to_remove:
            self.plant_graph.remove_edge(*edge)

    @staticmethod
    def build_complete_graph(plant_graph: MultiDiGraph) -> MultiDiGraph:
        """Builds a complete graph from the plant graph with minimal abstractions.

        This method creates a deep copy of the plant graph and only removes structural
        and metadata nodes (ConceptualModel and MetaData) which are typically not needed
        for analysis. All other nodes and their connections are preserved.

        Parameters
        ----------
        plant_graph : MultiDiGraph
            The input plant graph to process.

        Returns
        -------
        MultiDiGraph
            The processed complete graph.
        """
        complete_loader = GraphAbstractor(
            plant_graph=deepcopy(plant_graph),
        )

        # Remove structural and metadata nodes
        complete_loader.remove_nodes_by_label(["ConceptualModel", "MetaData"])

        return complete_loader.plant_graph

    @staticmethod
    def build_process_graph(plant_graph: MultiDiGraph) -> MultiDiGraph:
        """Builds the process graph from the plant graph by filtering relevant nodes and edges.

        Parameters
        ----------
        plant_graph : MultiDiGraph
            The input plant graph to process.

        Returns
        -------
        MultiDiGraph
            The processed process graph.
        """
        process_loader = GraphAbstractor(
            plant_graph=deepcopy(plant_graph),
        )

        # Remove structural and metadata nodes
        process_loader.remove_nodes_by_label(["ConceptualModel", "MetaData"])

        # Collapse PipingSystem
        process_loader.remove_nodes_by_label("PipingNode")
        process_loader.collapse_node_to_node_by_label(
            label="PipingNetworkSystem",
            target_labels="PipingNetworkSegment",
            inherit_attributes=True,
            inherit_connections=False,
        )
        process_loader.collapse_node_to_node_by_label(
            label="PipingNetworkSegment",
            target_labels=[
                "PipingComponent",
                "PipeOffPageConnector",
                "PropertyBrake",
                "PipingConnection",
            ],
            inherit_attributes=True,
            inherit_connections=False,
        )

        process_loader.collapse_node_to_edge_by_label(
            label="Pipe",
            inherit_attributes=True,
            inherit_connections=False,
        )

        process_loader.collapse_node_to_edge_by_label(
            label="DirectPipingConnection",
            inherit_attributes=True,
            inherit_connections=False,
        )

        # Collapse Equipment
        # No Equipment Collapsing

        # Collapse Instrumentation
        process_loader.collapse_node_to_node_by_label(
            label="ControlledActuator",
            target_labels="ActuatingSystem",
            inherit_attributes=True,
            inherit_connections=False,
        )

        process_loader.collapse_node_to_node_by_label(
            label="ActuatingSystem",
            target_labels="ActuatingFunction",
            inherit_attributes=True,
            inherit_connections=True,
        )

        process_loader.collapse_node_to_node_by_label(
            label="InstrumentationLoopFunction",
            target_labels="ProcessInstrumentationFunction",
            inherit_attributes=True,
            inherit_connections=False,
        )

        process_loader.collapse_node_to_edge_by_label(
            label="MeasuringLineFunction",
            inherit_attributes=True,
            inherit_connections=False,
        )

        process_loader.collapse_node_to_edge_by_label(
            label="OperatedValveReference",
            inherit_attributes=True,
            inherit_connections=False,
        )

        process_loader.collapse_node_to_edge_by_label(
            label="SignalConveyingFunction",
            inherit_attributes=True,
            inherit_connections=False,
        )

        return process_loader.plant_graph

    @staticmethod
    def build_conceptual_graph(plant_graph: MultiDiGraph) -> MultiDiGraph:
        """Builds the conceptual graph from the plant graph by filtering relevant nodes and edges.

        Parameters
        ----------
        plant_graph : MultiDiGraph
            The input plant graph to process.

        Returns
        -------
        MultiDiGraph
            The processed conceptual graph.
        """
        conceptual_loader = GraphAbstractor(
            plant_graph=deepcopy(plant_graph),
        )

        # Remove structural and metadata nodes
        conceptual_loader.remove_nodes_by_label(["ConceptualModel", "MetaData"])

        # Collapse PipingSystem
        conceptual_loader.remove_nodes_by_label("PipingNode")
        conceptual_loader.collapse_node_to_node_by_label(
            label="PipingNetworkSystem",
            target_labels="PipingNetworkSegment",
            inherit_attributes=True,
            inherit_connections=False,
        )
        conceptual_loader.collapse_node_to_node_by_label(
            label="PipingNetworkSegment",
            target_labels=[
                "PipingComponent",
                "PipeOffPageConnector",
                "PropertyBrake",
                "PipingConnection",
            ],
            inherit_attributes=True,
            inherit_connections=False,
        )

        conceptual_loader.collapse_node_to_edge_by_label(
            label="Pipe",
            inherit_attributes=True,
            inherit_connections=False,
        )

        conceptual_loader.collapse_node_to_edge_by_label(
            label="DirectPipingConnection",
            inherit_attributes=True,
            inherit_connections=False,
        )

        # Collapse Equipment
        conceptual_loader.remove_nodes_by_label(
            label=[class_type.__name__ for class_type in et.get_equipment_internal_classes()]
        )
        conceptual_loader.remove_nodes_by_label("Nozzle", stitch=True)

        # Collapse Instrumentation
        conceptual_loader.collapse_node_to_node_by_label(
            label="ControlledActuator",
            target_labels="ActuatingSystem",
            inherit_attributes=True,
            inherit_connections=False,
        )

        conceptual_loader.collapse_node_to_node_by_label(
            label="ActuatingSystem",
            target_labels="ActuatingFunction",
            inherit_attributes=True,
            inherit_connections=True,
        )

        conceptual_loader.collapse_node_to_node_by_label(
            label="InstrumentationLoopFunction",
            target_labels="ProcessInstrumentationFunction",
            inherit_attributes=True,
            inherit_connections=False,
        )

        conceptual_loader.collapse_node_to_edge_by_label(
            label="MeasuringLineFunction",
            inherit_attributes=True,
            inherit_connections=False,
        )

        conceptual_loader.collapse_node_to_edge_by_label(
            label="OperatedValveReference",
            inherit_attributes=True,
            inherit_connections=False,
        )

        conceptual_loader.collapse_node_to_edge_by_label(
            label="SignalConveyingFunction",
            inherit_attributes=True,
            inherit_connections=False,
        )

        return conceptual_loader.plant_graph
