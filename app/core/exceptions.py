from typing import List, Any, Optional


class DataIntegrityViolation(Exception):
    """
    Exception raised when an operation is not permitted because it would interfere with data integrity.

    Args:
        message (str): Error message to indicate the reason of the exception
        dependent_objects (List[Any], optional): A list of dependent objects whose integrity would be violated by the operation. Default is None
    """

    def __init__(
        self,
        message: str,
        dependent_objects: Optional[List[Any]] = None,
    ):
        self.message = message
        self.dependent_objects = dependent_objects
