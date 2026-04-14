"""Utility functions for parsing and error handling in the inbuilt Loader Modules."""

from functools import wraps

from pydantic import ValidationError

from pydexpi.dexpi_classes.pydantic_classes import DexpiBaseModel
from pydexpi.loaders.proteus_serializer.proteus_parser.core import ErrorLevels, ParserModule


class ErrorTemplates:
    """Class to hold error message templates for the ProteusLoader."""

    @staticmethod
    def id_not_found(element_name: str) -> tuple[str, ErrorLevels]:
        """Returns an error message template for when an ID is not found."""
        return f"ID not found for element '{element_name}'. Element Skipped.", ErrorLevels.ERROR

    @staticmethod
    def skip_pass(pass_name: str, element_name: str) -> tuple[str, ErrorLevels]:
        """Returns an error message template for skipping a pass."""
        return (
            f"'{pass_name}' pass skipped for element '{element_name}' due to error in previous "
            f"pass. Element Skipped.",
            ErrorLevels.INFO,
        )

    @staticmethod
    def assoc_adding_error(element_name: str, associated_obj_id: str) -> tuple[str, ErrorLevels]:
        """Returns an error message template for when an association cannot be added."""
        return (
            f"Object {associated_obj_id} could not be added as reference to {element_name}.",
            ErrorLevels.ERROR,
        )

    @staticmethod
    def no_assoc_ctrl(element_name: str, associated_obj_id: str) -> tuple[str, ErrorLevels]:
        """Returns an error message template for when an association is missing in control pass."""
        return (
            f"Association of {element_name} with {associated_obj_id} is missing in control pass. "
            f"Attempt adding association.",
            ErrorLevels.WARNING,
        )

    @staticmethod
    def assoc_added_ctrl(
        element_name: str, associated_obj_id: str, field_name: str, reverse: bool = False
    ) -> tuple[str, ErrorLevels]:
        """Returns an error message template for when an association is added in control pass."""
        if reverse:
            messg = (
                f"Association of {element_name} with {associated_obj_id} added in control pass in "
                f"reverse order to field {field_name}.",
                ErrorLevels.INFO,
            )
        else:
            messg = (
                f"Association of {element_name} with {associated_obj_id} added in control pass to "
                f"field {field_name}.",
                ErrorLevels.INFO,
            )
        return messg

    @staticmethod
    def assoc_not_added_ctrl(element_name: str, associated_obj_id: str) -> tuple[str, ErrorLevels]:
        """Returns error message template for when an association is not added in control pass."""
        return (
            f"Association of {element_name} with {associated_obj_id} could not be added in control "
            f"pass.",
            ErrorLevels.ERROR,
        )

    @staticmethod
    def inval_assoc_type(element_name: str, assoc_type: str) -> tuple[str, ErrorLevels]:
        """Returns an error message template for when an association type is invalid."""
        return (
            f"Invalid association type '{assoc_type}' for {element_name}. Association skipped.",
            ErrorLevels.ERROR,
        )


def add_by_inferring_type(to_be_added: DexpiBaseModel, to_be_added_to: DexpiBaseModel):
    """Adds an attribute to a class by inferring the correct type.

    Tries to set all attributes or add them to existing lists in that field. Returns the name of
    the field found. Ignores suitable fields that are already set to a non-None value.

    Parameters
    ----------
    to_be_added : DexpiBaseModel
        The object to be added.
    to_be_added_to : DexpiBaseModel
        The object to which the `to_be_added` object should be added.

    Returns
    -------
    str
        The name of the field in `to_be_added_to` where `to_be_added`
        was successfully added.

    Raises
    ------
    ValueError
        If no suitable, None field is found in `to_be_added_to` for `to_be_added`.
    """
    field_found = False
    found_field = None
    for field in to_be_added_to.__class__.model_fields:
        try:
            curr_value = getattr(to_be_added_to, field)
            if curr_value is None:
                setattr(to_be_added_to, field, to_be_added)
                field_found = True
                found_field = field
                break

        except (ValidationError, AttributeError):
            pass
        try:
            new_list = list(getattr(to_be_added_to, field))
            new_list.append(to_be_added)
            setattr(to_be_added_to, field, new_list)
            field_found = True
            found_field = field
            break

        except (ValidationError, TypeError):
            pass

    if not field_found:
        raise ValueError(f"No suitable field found in {to_be_added_to} for {to_be_added}")

    return found_field


def is_associated_with(member: DexpiBaseModel, container: DexpiBaseModel) -> bool:
    """Checks if the object is already associated with the given object.

    Parameters
    ----------
    member : DexpiBaseModel
        The object to check for association.
    container : DexpiBaseModel
        The object to check against for association.

    Returns
    -------
    bool
        True if the member is associated with the container, False otherwise.
    """
    for field in container.__class__.model_fields:
        if isinstance(getattr(container, field), list):
            if member in getattr(container, field):
                return True
        elif getattr(container, field) == member:
            return True
    return False


def filter_none(items: list) -> list:
    """Filters out None values from a list.

    Parameters
    ----------
    items : list
        The list of items to filter.

    Returns
    -------
    list
        A new list containing only non-None items.
    """
    return [item for item in items if item is not None]


def redirect_errors_to_registry(func):
    """Create a decorator to redirect exceptions to the error registry and return None."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if not args:
                raise ValueError(
                    "The first argument 'self' must be an instance of LoaderModule. "
                    "Decorator can only be used on methods of LoaderModule"
                )
            if not isinstance(args[0], ParserModule):
                raise ValueError(
                    "The first argument 'self' must be an instance of LoaderModule. "
                    "Decorator can only be used on methods of LoaderModule"
                )
            self = args[0]
            message = (
                f"Error in parsing step {func.__name__} in {self.__class__.__name__}: {str(e)}"
            )
            self.register_error(
                message=message,
                level=ErrorLevels.ERROR,
                exception=e,
            )
            return None

    return wrapper
