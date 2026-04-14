"""Utility functions for DEXPI equipment classes."""

import inspect

from pydexpi.dexpi_classes import equipment as equipment_module
from pydexpi.dexpi_classes.dexpiBaseModels import DexpiBaseModel


def get_equipment_internal_classes() -> list[type[DexpiBaseModel]]:
    """Return all equipment internal component classes.

    Equipment internals are classes that:

    1. Inherit from ``CustomAttributeOwner`` (directly or indirectly)
    2. Do NOT inherit from ``TaggedPlantItem``
    3. Are NOT specialised subtypes of a named sub-component class — i.e. none
       of their direct base classes carries a ``subTagName`` field.
    4. Exclude ``Nozzle`` explicitly.

    Returns
    -------
    list[type[DexpiBaseModel]]
        Sorted list of equipment internal component class objects.
    """
    equipment_internals: list[type[DexpiBaseModel]] = []

    for _, obj in inspect.getmembers(equipment_module, inspect.isclass):
        if obj.__module__ != "pydexpi.dexpi_classes.pydantic_classes":
            continue

        if not hasattr(obj, "uri"):
            continue

        mro_names = [base.__name__ for base in obj.__mro__]

        parent_has_subtag = any(
            "subTagName" in getattr(base, "model_fields", {}) for base in obj.__bases__
        )

        if (
            "CustomAttributeOwner" in mro_names
            and "TaggedPlantItem" not in mro_names
            and not parent_has_subtag
            and obj.__name__ != "Nozzle"
        ):
            equipment_internals.append(obj)

    return sorted(equipment_internals, key=lambda class_type: class_type.__name__)
