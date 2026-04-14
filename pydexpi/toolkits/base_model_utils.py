"""This module contains utility functions for pydexpi base models. Becasue these
are the common parents to the pydexpi classes, these are basic, overarching
functionalities for all dexpi classes."""

from enum import Enum

from pydantic_core import PydanticUndefined

from pydexpi import dexpi_classes
from pydexpi.dexpi_classes.dexpiBaseModels import DexpiBaseModel, DexpiDataTypeBaseModel


def get_composition_attributes(dexpi_object: DexpiBaseModel) -> dict:
    """
    Retrieve attributes from a DEXPI object with the 'composition' attribute category.

    Parameters
    ----------
    dexpi_object : DexpiBaseModel
        An instance of a DEXPI model from which composition attributes are extracted.

    Returns
    -------
    dict
        A dictionary where the keys are field names and the values are the corresponding
        field values with the '"composition"' category."""
    return _get_attributes_with_category(dexpi_object, "composition")


def get_reference_attributes(dexpi_object: DexpiBaseModel) -> dict:
    """
    Retrieve attributes from a DEXPI object with the 'reference' attribute category.

    Parameters
    ----------
    dexpi_object : DexpiBaseModel
        An instance of a DEXPI model from which reference attributes are extracted.

    Returns
    -------
    dict
        A dictionary where the keys are field names and the values are the corresponding
        field values with the '"reference"' category."""
    return _get_attributes_with_category(dexpi_object, "reference")


def get_data_attributes(dexpi_object: DexpiBaseModel) -> dict:
    """
    Retrieve attributes from a DEXPI object with the 'data' attribute category.

    Parameters
    ----------
    dexpi_object : DexpiBaseModel
        An instance of a DEXPI model from which data attributes are extracted.

    Returns
    -------
    dict
        A dictionary where the keys are field names and the values are the corresponding
        field values with the '"data"' category."""
    return _get_attributes_with_category(dexpi_object, "data")


def _get_attributes_with_category(
    dexpi_object: DexpiBaseModel | DexpiDataTypeBaseModel, category: str
) -> dict:
    """
    Retrieve a dictionary of field names and their values from a dexpi_object
    based on the attribute_category annotation in the 'json_schema_extra'.

    This function iterates over the fields of the given dexpi_object,
    checks the 'json_schema_extra' metadata for a key '"attribute_category"',
    and includes the field in the output dictionary if its value matches the
    provided attribute category.

    Parameters
    ----------
    dexpi_object : DexpiBaseModel | DexpiDataTypeBaseModel
        A pydexpi object from which attributes are extracted.
    category : str
        The value of the '"attribute_category"' to filter the fields by.

    Returns
    -------
    dict
        A dictionary where the keys are field names and the values are the
        corresponding field values from the model, filtered by the given
        annotation.
    """

    attribute_dict = {}
    for fld_name, field in dexpi_object.__class__.model_fields.items():
        if field.json_schema_extra is not None:
            if "attribute_category" in field.json_schema_extra:
                if field.json_schema_extra["attribute_category"] == category:
                    attribute_dict[fld_name] = getattr(dexpi_object, fld_name)
    return attribute_dict


def get_composition_attributes_from_class(
    dexpi_class: type[DexpiBaseModel | DexpiDataTypeBaseModel],
) -> set[str]:
    """Return names of composition attributes for a DEXPI class.

    Parameters
    ----------
    dexpi_class : type[DexpiBaseModel | DexpiDataTypeBaseModel]
        The class to inspect.

    Returns
    -------
    set[str]
        Set of field names categorized as composition attributes.
    """
    return _get_attribute_names_with_category_from_class(dexpi_class, "composition")


def get_reference_attributes_from_class(
    dexpi_class: type[DexpiBaseModel | DexpiDataTypeBaseModel],
) -> set[str]:
    """Return names of reference attributes for a DEXPI class.

    Parameters
    ----------
    dexpi_class : type[DexpiBaseModel | DexpiDataTypeBaseModel]
        The class to inspect.

    Returns
    -------
    set[str]
        Set of field names categorized as reference attributes.
    """
    return _get_attribute_names_with_category_from_class(dexpi_class, "reference")


def get_data_attributes_from_class(
    dexpi_class: type[DexpiBaseModel | DexpiDataTypeBaseModel],
) -> set[str]:
    """Return names of data attributes for a DEXPI class.

    Parameters
    ----------
    dexpi_class : type[DexpiBaseModel | DexpiDataTypeBaseModel]
        The class to inspect.

    Returns
    -------
    set[str]
        Set of field names categorized as data attributes.
    """
    return _get_attribute_names_with_category_from_class(dexpi_class, "data")


def _get_attribute_names_with_category_from_class(
    dexpi_class: type[DexpiBaseModel | DexpiDataTypeBaseModel], category: str
) -> set[str]:
    """Return the set of field names on a DEXPI (data type) class for a category.

    Parameters
    ----------
    dexpi_class : type[DexpiBaseModel | DexpiDataTypeBaseModel]
        The DEXPI model (or data type) class whose fields will be inspected.
    category : str
        Attribute category (e.g. ``"composition"``, ``"reference"``, ``"data"``) to filter by.

    Returns
    -------
    set[str]
        A set containing the names of all fields whose ``json_schema_extra['attribute_category']``
        equals the provided category.
    """
    names: set[str] = set()
    for fld_name, field in dexpi_class.model_fields.items():
        extra = field.json_schema_extra
        if extra and extra.get("attribute_category") == category:
            names.add(fld_name)
    return names


def get_dexpi_class(
    class_name: str,
) -> type[DexpiBaseModel]:  # TODO: should we remove this function?
    """
    Retrieve a DEXPI class by its name.

    Parameters
    ----------
    class_name : str
        The name of the DEXPI class to retrieve.

    Returns
    -------
    type[DexpiBaseModel]
        The DEXPI class with the given name.
    """
    for submodule_name in dir(dexpi_classes):
        # Get the submodule dynamically
        submodule = getattr(dexpi_classes, submodule_name)
        cls = getattr(submodule, class_name, None)
        if cls:
            return cls
    raise AttributeError(f"Class {class_name} not a DEXPI class.")


def get_dexpi_class_from_uri(uri: str) -> type[DexpiBaseModel]:
    """
    Retrieve a DEXPI class from its URI.

    Parameters
    ----------
    uri : str
        The URI of the DEXPI class to retrieve.

    Returns
    -------
    DexpiBaseModel
        The DEXPI class corresponding to the given URI.
    """
    for submodule_name in dir(dexpi_classes):
        submodule = getattr(dexpi_classes, submodule_name)
        for attr in dir(submodule):
            candidate = getattr(submodule, attr)
            if isinstance(candidate, type):
                cls_uri = getattr(candidate, "uri", None)
                if cls_uri == uri:
                    return candidate
    raise AttributeError(f"Class with uri {uri!r} not a DEXPI class.")


def attribute_is_required(dexpi_class: type[DexpiBaseModel], attribute_name: str) -> bool:
    """Check if an attribute of a DEXPI class is required.

    This method retrieves the field information for the specified attribute. If there is no
    default factory specified for the field, it is considered required.

    Parameters
    ----------
    dexpi_class : type[DexpiBaseModel]
        The DEXPI class to check.
    attribute_name : str
        The name of the attribute to check.

    Returns
    -------
    bool
        True if the attribute is required, False otherwise.
    """
    field_info = dexpi_class.model_fields.get(attribute_name)
    if field_info is None:
        raise AttributeError(
            f"Attribute {attribute_name} not found in class {dexpi_class.__name__}."
        )
    if field_info.default is PydanticUndefined:
        return True
    else:
        return False


def resolve_enum_member(enum_class: type[Enum], value: str | int) -> Enum:
    """Resolve an enum member from a string or integer value.

    This function attempts to convert the provided value to an integer and
    retrieve the corresponding enum member by index. If the conversion fails,
    it treats the value as a string and retrieves the enum member by name.

    Parameters
    ----------
    enum_class : type[Enum]
        The enumeration class to resolve the member from.
    value : str | int
        The value to resolve, either as a string (name) or integer (index).

    Returns
    -------
    Enum
        The resolved enum member.
    """
    try:
        integer_value = int(value)
        enum_members = list(enum_class)
        return enum_members[integer_value]
    except ValueError:
        return enum_class(value)


def get_inheritance_from_dexpi_class(source: type[DexpiBaseModel]) -> list[type]:
    """Get inheritance chain from a DexpiBaseModel class.

    This method extracts the inheritance hierarchy from a DexpiBaseModel class,
    returning the class types in the inheritance chain.

    Parameters
    ----------
    source : type[DexpiBaseModel]
        A DexpiBaseModel class (not an instance)

    Returns
    -------
    list[type]
        List of class types in the inheritance chain, excluding base classes
        like DexpiBaseModel, ABC, and BaseModel

    """
    class_hierarchy = []

    def _gather_base_classes(cls):
        """Recursively gather base classes until reaching pydexpi base models"""
        if cls.__name__ in ("DexpiBaseModel", "DexpiDataTypeBaseModel", "DexpiSingletonBaseModel"):
            return
        if cls not in class_hierarchy:
            class_hierarchy.append(cls)
        for base in cls.__bases__:
            _gather_base_classes(base)

    _gather_base_classes(source)
    return class_hierarchy

