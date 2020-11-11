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
import math
from typing import Mapping

import numpy as np
import pymunk
from pymunk.vec2d import Vec2d

from ..core.backend.controller import Controller
from ..core.client import ActuatorVariable, SensorVariable, State
from ..core.util import PhyPropType

#: Gravity constants
G_CONST = Vec2d(0, -9.8)


class _SortVec2D(Vec2d):
    def __gt__(self, other):
        if self.x != other.x:
            return self.x > other.x
        else:
            return self.y > other.y

    def __lt__(self, other):
        if self.x != other.x:
            return self.x < other.x
        else:
            return self.y < other.y

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __ge__(self, other):
        return self > other or self == other

    def __le__(self, other):
        return self < other or self == other


class InvPendulumState(State):
    def __init__(self,
                 upd_freq_hz: int,
                 ground_friction: float = 0.1,
                 cart_mass: float = 0.5,
                 cart_dims: Vec2d = Vec2d(0.3, 0.2),
                 pend_com: float = 0.6,
                 pend_width: float = 0.1,
                 pend_mass: float = 0.2,
                 pend_moment: float = 0.001,  # TODO: calculate with pymunk?
                 ):
        # TODO: graphical visualization
        super(InvPendulumState, self).__init__(update_freq_hz=upd_freq_hz)
        # set up state

        # space
        self._space = pymunk.Space(threaded=True)
        self._space.gravity = G_CONST

        # populate space
        # ground
        filt = pymunk.ShapeFilter(group=1)
        self._ground = pymunk.Segment(self._space.static_body,
                                      (-4, -0.1),
                                      (4, -0.1),
                                      0.1)  # TODO remove magic numbers

        self._ground.friction = ground_friction
        self._ground.filter = filt
        self._space.add(self._ground)

        # cart
        cart_moment = pymunk.moment_for_box(cart_mass, cart_dims)
        self._cart_body = pymunk.Body(mass=cart_mass, moment=cart_moment)
        self._cart_body.position = (0.0, cart_dims.y / 2)
        self._cart_shape = pymunk.Poly.create_box(self._cart_body, cart_dims)
        self._cart_shape.friction = ground_friction
        self._space.add(self._cart_body, self._cart_shape)

        # pendulum arm and mass
        pend_dims = (pend_width, pend_com * 2)
        self._pend_body = pymunk.Body(mass=pend_mass, moment=pend_moment)
        self._pend_body.position = \
            (self._cart_body.position.x,
             self._cart_body.position.y + (cart_dims.y / 2) + pend_com)
        self._pend_shape = pymunk.Poly.create_box(self._pend_body, pend_dims)
        self._pend_shape.filter = filt
        self._space.add(self._pend_body, self._pend_shape)

        # joint
        _joint_pos = self._cart_body.position + Vec2d(0, cart_dims.y / 2)
        joint = pymunk.constraint.PivotJoint(self._cart_body, self._pend_body,
                                             _joint_pos)
        joint.collide_bodies = False
        self._space.add(joint)

        # actuated and sensor variables
        self.force = ActuatorVariable(0.0)
        self.position = SensorVariable(self._cart_body.position.x)
        self.speed = SensorVariable(self._cart_body.velocity.x)
        self.angle = SensorVariable(self._pend_body.angle)
        self.ang_vel = SensorVariable(self._pend_body.angular_velocity)

        # self._screen = Screen(size=(100, 100))
        #
        # # drawing rate
        # self._drawing_rate = upd_freq_hz // 5
        # self._update_count = 0

    def advance(self, delta_t: float) -> None:
        # apply actuation
        force = self.force
        self._cart_body.apply_force_at_local_point(Vec2d(force, 0.0),
                                                   Vec2d(0, 0))

        # advance the world state
        self._space.step(delta_t)
        angle_deg = np.degrees(self._pend_body.angle)

        # TODO: supportsfloat!
        # state_str = \
        #     f'Pos: {self._cart_body.position[0]:0.3f} m | ' \
        #     f'Angle: {angle_deg:0.3f} degrees | ' \
        #     f'Force: {math.fabs(force):0.1f} N | ' \
        #     f'DeltaT: {delta_t:f} s'
        #
        # print(f'\r{state_str}', end='\t' * 10)

        # setup new world state
        self.position = self._cart_body.position.x
        self.speed = self._cart_body.velocity.x
        self.angle = self._pend_body.angle
        self.ang_vel = self._pend_body.angular_velocity


class InvPendulumController(Controller):
    #: Pendulum parameters
    K = [-57.38901804, -36.24133932, 118.51380879, 28.97241832]
    NBAR = -57.25

    def __init__(self, ref: float = 0.0, max_force: float = 25):
        super(InvPendulumController, self).__init__()
        self._count = 0
        self._ref = ref
        self._max_force = max_force

    def process(self, sensor_values: Mapping[str, PhyPropType]) \
            -> Mapping[str, PhyPropType]:
        self._count = (self._count + 1) % 1000
        if self._count == 0:
            self._ref *= -1

        try:
            position = sensor_values['position']
            speed = sensor_values['speed']
            angle = sensor_values['angle']
            ang_vel = sensor_values['ang_vel']
        except KeyError:
            print(sensor_values)
            raise

        gain = (self.K[0] * position) + \
               (self.K[1] * speed) + \
               (self.K[2] * angle) + \
               (self.K[3] * ang_vel)
        force = self._ref * self.NBAR - gain

        # kill our motors if we go past our linearized acceptable
        # angles
        if math.fabs(angle) > 0.35:
            force = 0.0

        # cap our maximum force so it doesn't go crazy
        if math.fabs(force) > self._max_force:
            force = math.copysign(self._max_force, force)

        return {'force': force}
