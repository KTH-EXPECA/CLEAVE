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
import functools
import math
import warnings
from typing import Mapping, Sequence, Tuple

import numpy as np
import pyglet
import pymunk
from drawille import Canvas
from pymunk.vec2d import Vec2d

from ..base.backend.controller import Controller
from ..base.client import ActuatorVariable, SensorVariable, State
from ..base.util import PhyPropType, nanos2seconds

#: Gravity constants
G_CONST = Vec2d(0, -9.8)


def _draw_poly(canvas: Canvas, verts: Sequence[Vec2d]):
    start_v = verts
    end_v = verts[1:] + verts[0]
    for v1, v2 in zip(start_v, end_v):
        # canvas.set(*v1)
        x_points = np.arange(v1.x, v2.x).astype('int32')
        y_points = np.arange(v1.y, v2.y).astype('int32')

        for x, y in zip(x_points, y_points):
            canvas.set(int(x), int(y))
        canvas.set(*v2)


class InvPendulumState(State):
    PYGLET_CAPTION = 'Inverted Pendulum Simulator'

    def __init__(self,
                 upd_freq_hz: int,
                 screen_w: int = 1000,
                 screen_h: int = 700,
                 ground_friction: float = 0.1,
                 cart_mass: float = 0.5,
                 cart_dims: Vec2d = Vec2d(0.3, 0.2),
                 pend_com: float = 0.6,
                 pend_width: float = 0.1,
                 pend_mass: float = 0.2,
                 pend_moment: float = 0.001,  # TODO: calculate with pymunk?
                 draw_color: Tuple[int, int, int, int] = (200, 200, 200, 200),
                 pixels_per_meter: float = 200.0,
                 ):
        super(InvPendulumState, self).__init__(update_freq_hz=upd_freq_hz)
        # set up state
        # window for visualization:
        self._window = pyglet.window.Window(screen_w, screen_h,
                                            vsync=False,
                                            caption=self.PYGLET_CAPTION)
        self._ppm = pixels_per_meter

        # actuated and sensor variables
        self.force = ActuatorVariable(persistent=False, default=0.0)
        self.position = SensorVariable()
        self.speed = SensorVariable()
        self.angle = SensorVariable()
        self.ang_vel = SensorVariable()

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

        # set up drawing stuff

        self._floor_offset = Vec2d(screen_w / 2, 5)  # TODO fix magic number

        # TODO: fix these magic numbers
        label_x = pyglet.text.Label(text='', font_size=18, color=draw_color,
                                    x=10, y=screen_h - 28)
        label_ang = pyglet.text.Label(text='', font_size=18, color=draw_color,
                                      x=10, y=screen_h - 58)
        label_force = pyglet.text.Label(text='', font_size=18, color=draw_color,
                                        x=10, y=screen_h - 88)
        label_time = pyglet.text.Label(text='', font_size=18, color=draw_color,
                                       x=10, y=screen_h - 118)

        self._labels = {'x'    : label_x,
                        'angle': label_ang,
                        'force': label_force,
                        'time' : label_time}
        self._window.on_draw = functools.partial(
            InvPendulumState._draw_window, self)

    @staticmethod
    def _draw_body(body: pymunk.Body,
                   ppm: float,
                   offset: Vec2d = Vec2d(0, 0)) -> None:
        """
        Helper method to draw bodies using closed polygons.

        Parameters
        ----------
        body
            pymunk.Body to be drawn on screen.
        ppm
            Pixels per meter factor.
        offset
            Offset vector from the origin.


        """

        for shape in body.shapes:
            if isinstance(shape, pymunk.Circle):
                warnings.warn('_draw_body is not implemented for Circles.')
            elif isinstance(shape, pymunk.Poly):
                # get vertices in world coordinates
                vertices = [v.rotated(body.angle) + body.position for v in
                            shape.get_vertices()]

                # convert vertices to pixel coordinates
                points = []
                for v in vertices:
                    v2 = (v * ppm) + offset
                    points.append(v2.x)
                    points.append(v2.y)

                data = ('v2i', tuple(map(int, points)))
                pyglet.graphics.draw(len(vertices),
                                     pyglet.gl.GL_LINE_LOOP,
                                     data)

    @staticmethod
    def _draw_line(segment: pymunk.Segment,
                   ppm: float,
                   offset: Vec2d = Vec2d(0, 0)):
        """
        Helper method to draw line segments.

        Parameters
        ----------
        segment
            Line segment to be drawn.
        ppm
            Pixels per meter factor.
        offset
            Offset vector from the origin.

        """

        vertices = [v + (0, segment.radius) for v in (segment.a, segment.b)]

        # convert vertices to pixel coordinates
        points = []
        for v in vertices:
            v2 = (v * ppm) + offset
            points.append(v2.x)
            points.append(v2.y)

        data = ('v2i', tuple(map(int, points)))
        pyglet.graphics.draw(len(vertices), pyglet.gl.GL_LINES, data)

    def _draw_window(self) -> None:
        """
        Internal utility function which handles visualization of the space.
        """

        self._window.clear()
        self._draw_body(self._cart_body, self._ppm, self._floor_offset)
        self._draw_body(self._pend_body, self._ppm, self._floor_offset)
        self._draw_line(self._ground, self._ppm, self._floor_offset)

        for _, label in self._labels.items():
            label.draw()

    def _pyglet_tick(self):
        """
        Manually advance the pyglet event loop in sync with our simulation.
        """
        pyglet.clock.tick()

        self._window.switch_to()
        self._window.dispatch_events()
        self._window.dispatch_event('on_draw')
        self._window.flip()

    def advance(self) -> None:
        # apply actuation
        force = self.force

        self._cart_body.apply_force_at_local_point(Vec2d(force, 0.0),
                                                   Vec2d(0, 0))

        # advance the world state
        # delta T is received as nanoseconds, turn into seconds
        deltaT = nanos2seconds(self.get_delta_t_ns())
        self._space.step(deltaT)

        # update labels before drawing
        self._labels['x'].text = f'Cart X: {self._cart_body.position[0]:0.3f} m'
        # TODO: fix magic number
        self._labels['angle'].text = f'Pendulum Angle: ' \
                                     f'{self._pend_body.angle * 57.2958:0.3f}' \
                                     f' degrees'

        self._labels['force'].text = f'Force: {math.fabs(force):0.1f} ' \
                                     f'newtons'
        self._labels['time'].text = f'DeltaT: {deltaT:f} s'

        # tick pyglet to draw screen
        self._pyglet_tick()

        # setup new world state
        self.position = self._cart_body.position.x
        self.speed = self._cart_body.velocity.x
        self.angle = self._pend_body.angle
        self.ang_vel = self._pend_body.angular_velocity

        # return {
        #     'position': self._cart_body.position.x,
        #     'speed'   : self._cart_body.velocity.x,
        #     'angle'   : self._pend_body.angle,
        #     'ang_vel' : self._pend_body.angular_velocity
        # }


class InvPendulumStateNoPyglet(State):
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
        super(InvPendulumStateNoPyglet, self) \
            .__init__(update_freq_hz=upd_freq_hz)
        # set up state

        # actuated and sensor variables
        self.force = ActuatorVariable(persistent=False, default=0.0)
        self.position = SensorVariable()
        self.speed = SensorVariable()
        self.angle = SensorVariable()
        self.ang_vel = SensorVariable()

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

        # set up terminal drawing
        self._canvas = Canvas()

    def advance(self) -> None:
        # apply actuation
        force = self.force

        self._cart_body.apply_force_at_local_point(Vec2d(force, 0.0),
                                                   Vec2d(0, 0))

        # advance the world state
        # delta T is received as nanoseconds, turn into seconds
        deltaT = nanos2seconds(self.get_delta_t_ns())
        self._space.step(deltaT)

        state_str = \
            f'Pos: {self._cart_body.position[0]:0.3f} m | ' \
            f'Angle: {self._pend_body.angle * 57.2958:0.3f} degrees | ' \
            f'Force: {math.fabs(force):0.1f} N | ' \
            f'DeltaT: {deltaT:f} s'

        print(f'\r{state_str}', end='\t\t\t')

        # setup new world state
        self.position = self._cart_body.position.x
        self.speed = self._cart_body.velocity.x
        self.angle = self._pend_body.angle
        self.ang_vel = self._pend_body.angular_velocity

        # draw
        self._canvas.clear()
        _draw_poly(self._canvas, self._cart_shape.get_vertices())

        # return {
        #     'position': self._cart_body.position.x,
        #     'speed'   : self._cart_body.velocity.x,
        #     'angle'   : self._pend_body.angle,
        #     'ang_vel' : self._pend_body.angular_velocity
        # }


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

        gain = self.K[0] * position + self.K[1] * speed + \
               self.K[2] * angle + self.K[3] * ang_vel
        force = self._ref * self.NBAR - gain

        # kill our motors if we go past our linearized acceptable
        # angles
        if math.fabs(angle) > 0.35:
            force = 0.0

        # cap our maximum force so it doesn't go crazy
        if math.fabs(force) > self._max_force:
            force = math.copysign(self._max_force, force)

        return {'force': force}
