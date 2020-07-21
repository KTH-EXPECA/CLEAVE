from threading import Condition
from typing import Any, Optional, Union

PhyPropType = Union[int, float, bytes, bool]


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
        timeout seconds, after which a TimeoutError is raised if no value was
        made available within that time.

        Parameters
        ----------
        timeout
            Number of seconds to block for. If None, blocks indefinitely.

        Returns
        -------
        Any
            The stored value.

        """
        with self._cond:
            try:
                while not self._has_value:
                    if not self._cond.wait(timeout=timeout):
                        raise TimeoutError()
                return self._value
            finally:
                self._value = None
                self._has_value = False
