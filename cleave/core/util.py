from queue import Empty
from threading import Condition
from typing import Any, Mapping, Optional, Union

#: Type of properties that can be handled by sensors and actuators.
PhyPropType = Union[int, float, bool]  # eventually extend to array types
PhyPropMapping = Mapping[str, PhyPropType]


#: This module contains miscellaneous utilities.


class SingleElementQ:
    """
    Utility class to hold a single variable in a thread-safe manner.
    Subsequent calls to put() without calling pop() will overwrite the stored
    variable. Conversely, pop() always returns the LATEST value for the
    stored variable.
    """

    def __init__(self):
        self._value = None
        self._has_value = False
        self._cond = Condition()

    def put(self, value: Any) -> None:
        """
        Thread-safely store a value. Overwrites any previously stored value.

        Parameters
        ----------
        value
            The value to store in this container.

        """
        with self._cond:
            self._value = value
            self._has_value = True
            self._cond.notify()

    def pop(self, timeout: Optional[float] = None) -> Any:
        """
        Pop the latest value for the stored variable. If timeout is None (the
        default), block until a value is available. Otherwise, block for up to
        timeout seconds, after which an Empty exception is raised if no value
        was made available within that time.

        Parameters
        ----------
        timeout
            Number of seconds to block for. If None, blocks indefinitely.

        Returns
        -------
        Any
            The stored value.

        Raises
        ------
        Empty
            If timeout is not None and no value is available when it runs out.

        """
        with self._cond:
            try:
                while not self._has_value:
                    if not self._cond.wait(timeout=timeout):
                        raise Empty()
                return self._value
            finally:
                self._value = None
                self._has_value = False

    def pop_nowait(self) -> Any:
        """
        Pops the latest value for the stored variable without waiting. If no
        value has been set yet, raises an Empty exception.

        Returns
        -------
        Any
            Latest value for the stored variable.

        Raises
        ------
        Empty
            If no value for the stored variable exists.

        """
        with self._cond:
            try:
                if not self._has_value:
                    raise Empty()
                else:
                    return self._value
            finally:
                self._value = None
                self._has_value = False
