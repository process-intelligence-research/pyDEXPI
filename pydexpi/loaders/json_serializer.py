"""
JSON Loader module for DEXPI model serialization and deserialization.

This module provides functionality to serialize DEXPI models to JSON format
and deserialize JSON data back into DEXPI model objects. It includes classes
for encoding models to dictionaries and decoding dictionaries to models.
"""

import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import IO, Any

import pydexpi.toolkits.base_model_utils as bmt
from pydexpi.dexpi_classes.pydantic_classes import DexpiBaseModel, DexpiDataTypeBaseModel
from pydexpi.loaders.serializer import Serializer
from pydexpi.toolkits.base_model_utils import (
    attribute_is_required,
    get_composition_attributes,
    get_data_attributes,
    get_reference_attributes,
    get_reference_attributes_from_class,
)


class IncompletePassError(Exception):
    """Custom exception for incomplete parsing passes in the DictToDexpiDecoder."""

    pass


class JsonSerializer(Serializer):
    """
    JSON implementation of the Serializer interface for DEXPI models.

    This class provides methods to save DEXPI models to JSON files and load
    DEXPI models from JSON files. It handles the conversion between DEXPI model
    objects and JSON-serializable dictionaries.
    """

    def __init__(self) -> None:
        """Initialize a new JSONLoader by constructing encoder and decoder objects as attributes."""
        super().__init__()
        self.encoder = DexpiToDictEncoder()
        self.decoder = DictToDexpiDecoder()

    def save(
        self, model: DexpiBaseModel, dir_path: str | Path, filename: str, indent: int = 4
    ) -> None:
        """
        Save a DEXPI model to a JSON file.

        Parameters
        ----------
        model : DexpiBaseModel
            The DEXPI model to save
        dir_path : str or Path
            Directory path where the file will be saved
        filename : str
            Name of the file without extension
        indent : int, optional
            Number of spaces for indentation in the JSON file, by default 4

        Returns
        -------
        None
        """
        # Add json ending if not explicitly given
        if not filename.endswith(".json"):
            filename = f"{filename}.json"

        path = Path(dir_path) / filename
        with open(path, "w", encoding="utf-8") as file:
            json.dump(self.model_to_dict(model), file, indent=indent, ensure_ascii=False)

    def load(self, dir_path: str | Path, filename: str) -> DexpiBaseModel:
        """
        Load a DEXPI model from a JSON file.

        Parameters
        ----------
        dir_path : str or Path
            Directory path where the file is located
        filename : str
            Name of the file without extension

        Returns
        -------
        DexpiBaseModel
            The loaded DEXPI model

        Raises
        ------
        FileNotFoundError
            If the specified file does not exist
        """
        # Add json ending if not explicitly given
        if not filename.endswith(".json"):
            filename = f"{filename}.json"

        path = Path(dir_path) / filename
        if not path.exists():
            raise FileNotFoundError(f"File {path} does not exist.")

        with open(path, encoding="utf-8") as file:
            data = json.load(file)
        return self.dict_to_model(data, external_refs={})

    def export_to_bytes(self, model: DexpiBaseModel, indent: int = 4) -> bytes:
        """
        Export a DEXPI model to JSON bytes.

        Parameters
        ----------
        model : DexpiBaseModel
            The DEXPI model to export
        indent : int, optional
            Number of spaces for indentation in the JSON, by default 4

        Returns
        -------
        bytes
            The exported JSON as bytes
        """
        json_string = json.dumps(self.model_to_dict(model), indent=indent, ensure_ascii=False)
        return json_string.encode("utf-8")

    def export_to_stream(self, model: DexpiBaseModel, stream: IO[bytes], indent: int = 4) -> None:
        """
        Export a DEXPI model to a JSON byte stream.

        Parameters
        ----------
        model : DexpiBaseModel
            The DEXPI model to export
        stream : IO[bytes]
            The output stream to write the JSON to
        indent : int, optional
            Number of spaces for indentation in the JSON, by default 4

        Returns
        -------
        None
        """
        json_bytes = self.export_to_bytes(model, indent=indent)
        stream.write(json_bytes)

    def load_from_bytes(self, json_bytes: bytes) -> DexpiBaseModel:
        """
        Load a DEXPI model from JSON bytes.

        Parameters
        ----------
        json_bytes : bytes
            The JSON content as bytes to load

        Returns
        -------
        DexpiBaseModel
            The loaded DEXPI model
        """
        json_string = json_bytes.decode("utf-8")
        data = json.loads(json_string)
        return self.dict_to_model(data, external_refs={})

    def load_from_stream(self, stream: IO[bytes]) -> DexpiBaseModel:
        """
        Load a DEXPI model from a JSON byte stream.

        Parameters
        ----------
        stream : IO[bytes]
            A readable binary stream containing JSON content

        Returns
        -------
        DexpiBaseModel
            The loaded DEXPI model
        """
        json_bytes = stream.read()
        return self.load_from_bytes(json_bytes)

    def load_from_string(self, json_string: str) -> DexpiBaseModel:
        """
        Load a DEXPI model from a JSON string.

        Parameters
        ----------
        json_string : str
            The JSON content as a string to load

        Returns
        -------
        DexpiBaseModel
            The loaded DEXPI model
        """
        data = json.loads(json_string)
        return self.dict_to_model(data, external_refs={})

    def model_to_dict(self, model: DexpiBaseModel) -> dict:
        """
        Convert a DEXPI model to a JSON serializable dictionary.

        Parameters
        ----------
        model : DexpiBaseModel
            The DEXPI model to convert

        Returns
        -------
        dict
            A dictionary representation of the DEXPI model
        """
        return self.encoder.dexpi_element_to_dict(model)

    def dict_to_model(self, data: dict, external_refs: dict = None) -> DexpiBaseModel:
        """
        Convert a dictionary to a DEXPI model.

        Parameters
        ----------
        data : dict
            Dictionary representation of the DEXPI model
        external_refs : dict, optional
            Dictionary of external references, by default None

        Returns
        -------
        DexpiBaseModel
            The created DEXPI model
        """
        return self.decoder.dict_to_dexpi_element(data, external_refs)


class DexpiToDictEncoder:
    """
    Encoder class for converting DEXPI models to JSON-serializable dictionaries.

    This class contains static methods to convert DEXPI model objects
    and their attributes to dictionaries that can be serialized to JSON.
    """

    @staticmethod
    def dexpi_element_to_dict(element: DexpiBaseModel | DexpiDataTypeBaseModel) -> dict:
        """
        Convert a DEXPI model element to a JSON serializable dictionary.

        Parameters
        ----------
        element : DexpiBaseModel or DexpiDataTypeBaseModel
            The element to convert

        Returns
        -------
        dict
            A dictionary representation of the element
        """

        # Get all attributes of the element by type
        raw_comp_attributes = get_composition_attributes(element)
        raw_reference_attributes = get_reference_attributes(element)
        raw_data_attributes = get_data_attributes(element)

        # Initialize dictionaries to hold the unpacked attributes for later constructor kwargs use
        comp_attribute_dict = {}
        reference_attribute_dict = {}
        data_attribute_dict = {}

        # Package composition attributes. This is done recursively with dexpi_element_to_dict
        # to ensure that nested elements are also converted to dictionaries.
        for attr, attr_val in raw_comp_attributes.items():
            comp_attribute_dict[attr] = _call_on_list_or_object_or_none(
                DexpiToDictEncoder.dexpi_element_to_dict, attr_val
            )

        # Package reference attributes. For reference attributes, we only store the IDs.
        for attr, attr_val in raw_reference_attributes.items():
            reference_attribute_dict[attr] = _call_on_list_or_object_or_none(
                lambda x: x.id, attr_val
            )

        # Package data attributes with package_data_attribute.
        for attr, attr_val in raw_data_attributes.items():
            data_attribute_dict[attr] = _call_on_list_or_object_or_none(
                DexpiToDictEncoder.package_data_attribute, attr_val
            )

        # Combine all attributes into a single dictionary. Add the type of the element and the ID if
        # it exists.
        element_dict = {"uri": element.uri}
        if isinstance(element, DexpiBaseModel):
            element_dict["id"] = element.id
        if comp_attribute_dict:
            element_dict["composition"] = comp_attribute_dict
        if reference_attribute_dict:
            element_dict["reference"] = reference_attribute_dict
        if data_attribute_dict:
            element_dict["data"] = data_attribute_dict

        return element_dict

    @staticmethod
    def package_data_attribute(
        attribute_val: DexpiDataTypeBaseModel | str | int | float | datetime,
    ) -> dict | str | int | float:
        """
        Unpack a data attribute to a JSON serializable format.

        Uses the correct method to convert the attribute value based on its type. If it is a DEXPI
        DataTypeBaseModel, it will be converted to a dictionary using dexpi_element_to_dict.
        Primitive types (str, int, float) are returned as is, and datetime objects are converted to
        strings.

        Parameters
        ----------
        attribute_val : DexpiDataTypeBaseModel or str or int or float or datetime
            The attribute value to package

        Returns
        -------
        dict or str or int or float
            JSON serializable representation of the attribute

        Raises
        ------
        TypeError
            If the attribute has an unsupported data type
        """
        if isinstance(attribute_val, DexpiDataTypeBaseModel):
            return DexpiToDictEncoder.dexpi_element_to_dict(attribute_val)
        elif isinstance(attribute_val, str | int | float):
            return attribute_val
        elif isinstance(attribute_val, datetime):
            return str(attribute_val)
        else:
            raise TypeError(f"Unsupported data type: {type(attribute_val)}")


class DictToDexpiDecoder:
    """
    Decoder class for converting dictionaries to DEXPI model objects.

    This class handles the reconstruction of DEXPI model objects from
    dictionary representations, including resolving object references.
    """

    def __init__(self) -> None:
        """Initialize a new decoder with an empty object registry.

        This registry is used to keep track of objects created during the
        compositional pass, allowing for reference resolution in the
        reference pass."""
        self.object_registry = {}

    def dict_to_dexpi_element(self, data: dict, external_refs: dict = None) -> DexpiBaseModel:
        """
        Convert a dictionary to a DEXPI model element.

        This is done in two passes:
        1. Compositional pass: Create the DEXPI model objects and their attributes and resolve
           compositional and data dependencies.
        2. Reference pass: Once all objects are created, resolve reference relationships by
           retrieving referenced objects from the object registry.

        Parameters
        ----------
        data : dict
            Dictionary representation of the DEXPI model
        external_refs : dict, optional
            Dictionary of external references, by default None

        Returns
        -------
        DexpiBaseModel
            The reconstructed DEXPI model
        """
        # Reset and set the object registry
        self.object_registry = external_refs if external_refs else {}

        all_objects_parsed_flag = False
        while not all_objects_parsed_flag:
            # Set the flag to true at the start of the loop. If any object couldn't be parsed due
            # to missing dependencies, it will be set to false again and a new pass will be made.
            curr_obj_len = len(self.object_registry)
            try:
                the_object = self._compositional_pass(data)
                all_objects_parsed_flag = True
            except IncompletePassError:
                next_obj_len = len(self.object_registry)
                if next_obj_len == curr_obj_len:
                    raise RuntimeError(
                        "Stalled parsing process: No new objects were created in the last pass."
                    )

        # Call reference pass
        self._reference_pass(data)

        return the_object

    def _compositional_pass(self, data: dict) -> DexpiBaseModel | None:
        """Recursively convert dictionaries to nested DEXPI model elements.

        This method handles the creation of DEXPI model objects including
        their composition and data attributes but not references.

        Parameters
        ----------
        data : dict
            Dictionary representation of the DEXPI model

        Returns
        -------
        DexpiBaseModel
            The constructed DEXPI model without resolved references
        """
        # If the object has been created successfully already, return it from the registry
        object_id = data.get("id")
        if object_id and object_id in self.object_registry:
            return self.object_registry[object_id]

        ### COMPOSITIONAL PASS ###
        # Retrieve the model class from the Dexpi classes
        model_uri = data.get("uri")
        model_class = bmt.get_dexpi_class_from_uri(model_uri)

        raw_comp_attrs = data.get("composition", {})

        # Prepare the composition attributes for the model
        comp_attr_args = {}
        incomplete_pass_occurred = False
        for attr, attr_val in raw_comp_attrs.items():
            if attr_val is None:
                comp_attr_args[attr] = None
            elif isinstance(attr_val, list):
                comp_attr_args[attr] = []
                for item in attr_val:
                    try:
                        comp_attr_args[attr].append(self._compositional_pass(item))
                    except IncompletePassError:
                        incomplete_pass_occurred = True
            else:
                try:
                    comp_attr_args[attr] = self._compositional_pass(attr_val)
                except IncompletePassError:
                    incomplete_pass_occurred = True

        if incomplete_pass_occurred:
            raise IncompletePassError(
                "Incomplete pass due to unresolved compositional dependencies."
            )

        # Prepare the data attributes for the model

        raw_data_attrs = data.get("data", {})

        data_attr_args = {}
        for attr, attr_val in raw_data_attrs.items():
            if isinstance(attr_val, list):
                data_attr_args[attr] = [self._unpack_data_attribute(item) for item in attr_val]
            else:
                data_attr_args[attr] = self._unpack_data_attribute(attr_val)

        # Construct the new object with the model class and attributes by stacking the arguments
        model_id = data.get("id")
        model_args = {"id": model_id} if model_id else {}
        model_args.update(comp_attr_args)
        model_args.update(data_attr_args)

        ### REQUIRED REFERENCE PASS ###
        # Retrieve the model class from the Dexpi classes
        raw_reference_attrs = data.get("reference", {})

        reference_fields = get_reference_attributes_from_class(model_class)
        required_reference_fields = {
            field for field in reference_fields if bmt.attribute_is_required(model_class, field)
        }

        for attr, attr_val in raw_reference_attrs.items():
            # Skip non-required references, as they will be handled in the reference pass
            if attr not in required_reference_fields:
                continue

            try:
                resolved_refs = _call_on_list_or_object_or_none(
                    self.object_registry.__getitem__, attr_val
                )
                model_args[attr] = resolved_refs
            except KeyError:
                # If a referenced object is not found, it means it hasn't been created yet.
                # Set the flag to false to indicate that another pass is needed.
                self.all_objects_parsed_flag = False
                raise IncompletePassError(
                    f"Referenced object with ID {attr_val} not found in registry."
                )

        # Create an instance of the model class with the arguments
        new_object = model_class(**model_args)

        # Register the new object in the object registry for the reference pass if there is an ID
        # If there isn't, then the object cannot be referenced, so it doesn't need to be registered.
        if model_id is not None:
            self.object_registry[new_object.id] = new_object

        return new_object

    def _unpack_data_attribute(self, attribute_val: dict | str | int | float) -> Any:
        """
        Unpack data attributes from a dictionary to the appropriate type.

        Parameters
        ----------
        attribute_val : dict or str or int or float
            The attribute value to unpack

        Returns
        -------
        Any
            The unpacked value, either a DEXPI model or primitive type
        """

        # If data type base model, unpack as a DexpiBaseModel element
        if isinstance(attribute_val, dict):
            return self._compositional_pass(attribute_val)
        # Else, return as is if it's a primitive type
        else:
            return attribute_val

    def _reference_pass(self, data: dict) -> None:
        """
        Resolve remaining, optional references in the data dictionary.

        This method resolves object references using the object registry
        after all objects have been created in the compositional pass.

        Parameters
        ----------
        data : dict
            Dictionary representation of the DEXPI model

        Returns
        -------
        None
        """

        # Retrieve the model class from the Dexpi classes
        object_id = data.get("id")

        the_object = self.object_registry.get(object_id)

        raw_reference_attrs = data.get("reference", {})

        for attr, attr_val in raw_reference_attrs.items():
            # Skip required references, as they were handled in the compositional pass
            if attribute_is_required(the_object.__class__, attr):
                continue
            resolved_refs = _call_on_list_or_object_or_none(
                self.object_registry.__getitem__, attr_val
            )
            setattr(the_object, attr, resolved_refs)

        # Call on all composition in the hierarchy
        raw_comp_attrs = data.get("composition", {})

        for attr, attr_val in raw_comp_attrs.items():
            _call_on_list_or_object_or_none(self._reference_pass, attr_val)


def _call_on_list_or_object_or_none(func: Callable, obj: Any) -> Any:
    """
    Call a function on an object, list of objects, or return None if the object is None.

    This helper function provides a unified interface for applying a function to
    either a single object or a list of objects, handling None values appropriately.

    Parameters
    ----------
    func : Callable
        The function to call on the object.
    obj : Any
        The object to process, which can be a list, a single object, or None.

    Returns
    -------
    Any
        The result of the function call on the object, a list of results if the input
        was a list, or None if the input was None.
    """
    if obj is None:
        return None
    elif isinstance(obj, list):
        return [func(item) for item in obj]
    else:
        return func(obj)
