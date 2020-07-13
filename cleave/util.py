from typing import Union


class RegisteredSensorWarning(Warning):
    pass


class UnregisteredPropertyWarning(Warning):
    pass


class IncompatibleFrequenciesError(Exception):
    pass


class MissingPropertyError(Exception):
    pass


PhyPropType = Union[int, float, bytes, bool]
