"""
Dexpi Model Toolkit
--------------------
This module contains functions and tools that concern overall of an overall
dexpi model/conceptual model.

"""

from collections.abc import Callable
from typing import Any, get_origin, get_type_hints

import pydexpi.toolkits.base_model_utils as bmu
from pydexpi.dexpi_classes.customization import CustomAttributeOwner
from pydexpi.dexpi_classes.dexpiBaseModels import DexpiBaseModel
from pydexpi.dexpi_classes.dexpiModel import ConceptualModel, DexpiModel


def combine_dexpi_models(models: list[DexpiModel], **kwargs) -> DexpiModel:
    """This function combines the contents of a list of dexpi models and returns
    a new model with its contents.

    The combination is performed on all list attributes of the conceptual model.
    The meta data attribute and the data attributes of the dexpi model can be
    passed in via kwargs.

    Parameters
    ----------
    models : list[DexpiModel]
        The list of dexpi models to be combined.

    Returns
    -------
    DexpiModel
        The combined dexpi model.

    Raises
    ------
    NotImplementedError
        Combining diagram information is not yet implemented. If any model
        has diagram or shapeCatalog attributes that are not None, Error is
        raised.
    """

    for dexpi_model in models:
        for i in [dexpi_model.diagram, dexpi_model.shapeCatalogues]:
            if i not in [None, []]:
                msg = "Dexpi toolkit does not yet support manipulating diagram information."
                raise NotImplementedError(msg)

    # Retrieve and combine list attributes
    new_model_args = kwargs
    for attr_name, typ in get_type_hints(ConceptualModel).items():
        if get_origin(typ) is list:
            attrs = [getattr(model.conceptualModel, attr_name) for model in models]
            new_model_args[attr_name] = [
                item for model_attr_list in attrs for item in model_attr_list
            ]
        else:
            pass

    new_conceptual_model = ConceptualModel(**new_model_args)

    return DexpiModel(conceptualModel=new_conceptual_model, **new_model_args)


def import_model_contents_into_model(
    target_model: DexpiModel, import_models: list[DexpiModel]
) -> None:
    """Imports the contents of passed models into target model. Conceptually
    similar to combine_dexpi_models, but the target_model is manipulated in
    place and its other, non-list attributes are preserved.

    Parameters
    ----------
    target_model : DexpiModel
        The model that is manipulated in place and that the other models are
        imported into.
    import_models : list[DexpiModel]
        The models that are to be imported to the target.

    Raises
    ------
    NotImplementedError
        Combining diagram information is not yet implemented. If any model
        has diagram or shapeCatalog attributes that are not None, Error is
        raised.
    """
    for dexpi_model in import_models:
        for i in [dexpi_model.diagram, dexpi_model.shapeCatalogues]:
            if i not in [None, []]:
                msg = "Dexpi toolkit does not yet support manipulating diagram information."
                raise NotImplementedError(msg)

    for attr_name, typ in get_type_hints(ConceptualModel).items():
        if get_origin(typ) is list:
            attrs = [getattr(model.conceptualModel, attr_name) for model in import_models]
            new_attrs = [item for model_attr_list in attrs for item in model_attr_list]

            # Append new attributes
            getattr(target_model.conceptualModel, attr_name).extend(new_attrs)


def get_all_instances_in_model(
    the_model: DexpiBaseModel, dexpi_classes: tuple[DexpiBaseModel] | None = None
) -> list[DexpiBaseModel]:
    """
    Recursively discover and collect all instances of specified classes within a model.

    This function traverses the attributes of the provided model object, recursively inspecting
    its attributes and sub-attributes to find all instances of the specified classes. The function
    returns a list of all discovered instances.

    Parameters
    ----------
    the_model : DexpiBaseModel
        The root model object to inspect.
    dexpi_classes : class or tuple of classes, optional
        A tuple of class types to discover within the model. Only instances of these classes will be collected.
        If None, all objects are collected.

    Returns
    -------
    list
        A list of all discovered instances of the specified classes within the model.
    """

    def discover_instances(obj, discovered_instances: tuple) -> list[DexpiBaseModel]:
        """
        Recursively get all compositional attributes of a Python object.

        Parameters
        ----------
        obj : object
            The object to inspect.
        discovered_instances : tuple or any
            The set that keeps track of the discovered instances.

        Returns
        -------
        discovered_instances : list
            Returns the set with discovered instances.
        """

        if dexpi_classes is None:
            if obj not in discovered_instances:
                discovered_instances.append(obj)
        elif isinstance(obj, dexpi_classes) and obj not in discovered_instances:
            discovered_instances.append(obj)

        # Get all compositional attributes
        attrs = bmu.get_composition_attributes(obj)

        for attr_value in attrs.values():
            if isinstance(attr_value, DexpiBaseModel):
                discovered_instances = discover_instances(attr_value, discovered_instances)
            elif isinstance(attr_value, list):
                for element in attr_value:
                    discovered_instances = discover_instances(element, discovered_instances)

        return discovered_instances

    discovered_instances = []
    return discover_instances(the_model, discovered_instances)


def get_instances_with_condition(
    the_model: DexpiBaseModel,
    condition: Callable[[DexpiBaseModel], bool],
    dexpi_classes: tuple[DexpiBaseModel] | None = None,
) -> list[DexpiBaseModel]:
    """Retrieve all subinstances in a dexpi model that satisfy a specific condition.

    Recursively searches through the model's attributes and sub-attributes to find all instances
    that satisfy the given condition. The condition is specified as a callable that takes a
    DexpiBaseModel instance as an argument and returns a boolean value.

    Parameters
    ----------
    the_model : DexpiBaseModel
        The model to be searched.
    condition : Callable[[DexpiBaseModel], bool]
        The condition that the instances must satisfy.
    dexpi_classes : tuple, optional
        Can specify the classes if only certain class types are to be
        considered. If None, all are considered, by default None.

    Returns
    -------
    list
        List of discovered instances that satisfy the condition.
    """
    instances_with_condition = []

    # Discover all candidates in the model of the candidate classes
    all_candidates = get_all_instances_in_model(the_model, dexpi_classes)

    for candidate in all_candidates:
        if condition(candidate):
            instances_with_condition.append(candidate)

    return instances_with_condition


def get_instances_with_attribute(
    the_model: DexpiBaseModel,
    attribute_name: str,
    target_value: Any = object(),
    dexpi_classes: tuple[DexpiBaseModel] | None = None,
) -> list[DexpiBaseModel]:
    """Retrieve all subinstances in a dexpi model with a specific attribute.

    The dexpi model is searched recursively through compositional attributes
    of all levels. The attribute name is specified as a string. If the target_value is not
    specified, any value is permitted. If the target_value is specified, only instances with
    that value are returned. The dexpi_classes parameter can be used to specify the classes
    to be considered. If None, all classes are considered.

    Parameters
    ----------
    the_model : DexpiBaseModel
        The model to be searched.
    attribute_name : str
        The name of the attribute to be identified.
    target_value : Any, optional
        The value this attribute is supposed to have. If not specified any value is permitted.
    dexpi_classes : tuple, optional
        Can specify the classes if only certain class types are to be
        considered. If None, all are considered, by default None.

    Returns
    -------
    list
        List of discovered instances that have the attribute specified.
    """

    def has_matching_attribute(candidate: DexpiBaseModel) -> bool:
        # Try retrieving the attribute
        try:
            actual_value = getattr(candidate, attribute_name)
            return actual_value == target_value or type(target_value) is object
        except AttributeError:
            # If none found, look in the custom attributes
            if isinstance(candidate, CustomAttributeOwner):
                for custom_attribute in candidate.customAttributes:
                    if custom_attribute.attributeName == attribute_name:
                        actual_value = custom_attribute.value
                        return actual_value == target_value or type(target_value) is object
            return False

    instances_with_attribute = get_instances_with_condition(
        the_model, has_matching_attribute, dexpi_classes=dexpi_classes
    )

    return instances_with_attribute


def object_is_in_model(dexpi_model: DexpiModel, dexpi_object: DexpiBaseModel) -> bool:
    """Checks if the given dexpi_object is in some way a member of the given
    dexpi_model.

    Parameters
    ----------
    dexpi_model : DexpiModel
        The model to be searched for the object.
    dexpi_object : DexpiBaseModel
        The object to be searched for in the model.

    Returns
    -------
    bool
        True if object is found in the model, False otherwise
    """
    candidates = get_all_instances_in_model(dexpi_model, type(dexpi_object))
    if dexpi_object in candidates:
        return True
    else:
        return False
