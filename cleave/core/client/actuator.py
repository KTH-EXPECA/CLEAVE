#  Copyright (c) 2020 KTH Royal Institute of Technology
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
from typing import Collection, Sequence, Set

import numpy as np

from ..recordable import NamedRecordable, Recordable, Recorder
from ..logging import Logger
from ...api.plant import Actuator
from ...api.util import PhyPropMapping


class RegisteredActuatorWarning(Warning):
    pass


class UnregisteredPropertyWarning(Warning):
    pass


class ActuatorArray(Recordable):
    """
    Internal utility class to manage a collection of Actuators attached to a
    Plant.
    """

    def __init__(self, actuators: Collection[Actuator]):
        super(ActuatorArray, self).__init__()
        self._log = Logger()
        self._actuators = dict()
        for actuator in actuators:
            if actuator.actuated_property_name in self._actuators:
                self._log.warn(
                    f'Replacing already registered sensor for property '
                    f'{actuator.actuated_property_name}'
                )

            self._actuators[actuator.actuated_property_name] = actuator

        # set up underlying recorder
        record_fields = ['plant_seq']
        opt_record_fields = {}
        for prop in self._actuators.keys():
            record_fields.append(f'{prop}_value')
            opt_record_fields[f'{prop}_target'] = np.nan

        self._records = NamedRecordable(
            name=self.__class__.__name__,
            record_fields=record_fields,
            opt_record_fields=opt_record_fields
        )

    def apply_actuation_inputs(self,
                               plant_cycle: int,
                               input_values: PhyPropMapping) -> PhyPropMapping:
        """
        Applies the desired actuation values to the internal actuators.

        Parameters
        ----------
        plant_cycle:
            The current plant cycle.
        input_values
            Mapping from property names to desired actuation values.

        Returns
        -------
        PhyPropMapping
            A mapping from actuated property names to output values from the
            corresponding actuators.

        """

        for prop, value in input_values.items():
            try:
                self._actuators[prop].set_value(value)
            except KeyError:
                self._log.warn(
                    f'Got actuation input for unregistered '
                    f'property {prop}!',
                    UnregisteredPropertyWarning
                )
                continue
        # record inputs and outputs
        record = {
            'plant_seq': plant_cycle,
        }
        act_values = {}

        for prop, act in self._actuators.items():
            actuation = act.get_actuation()
            act_values[prop] = actuation
            record[f'{prop}_value'] = actuation
            record[f'{prop}_target'] = input_values.get(prop)

        self._records.push_record(**record)

        return act_values

    @property
    def recorders(self) -> Set[Recorder]:
        return self._records.recorders

    @property
    def record_fields(self) -> Sequence[str]:
        return self._records.record_fields
