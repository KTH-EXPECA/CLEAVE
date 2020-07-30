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
import functools
from typing import Dict, Tuple

import pyglet
import pymunk
from pymunk.vec2d import Vec2d

from ..base.plant import State
from ...util import PhyPropType

#: Gravity constants
G_CONST = Vec2d(0, -9.8)

#: Pendulum parameters
K = [-57.38901804, -36.24133932, 118.51380879, 28.97241832]
NBAR = -57.25


class InvPendulumState(State):
    PYGLET_CAPTION = 'Inverted Pendulum Simulator'

    def __init__(self,
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
        # set up state
        # window for visualization:
        self._window = pyglet.window.Window(screen_w, screen_h,
                                            vsync=False,
                                            caption=self.PYGLET_CAPTION)
        self._ppm = pixels_per_meter

        # space
        self._space = pymunk.Space(threaded=True)
        self._space.gravity = G_CONST

        # populate space
        # ground
        filt = pymunk.ShapeFilter(group=1)
        self._ground = pymunk.Segment(self._space.static_body,
                                (-4, -0.1),
                                (4, -0.1), 0.1)  # TODO remove magic numbers

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

        self._labels = [label_x, label_ang, label_force, label_time]
        self._window.on_draw = functools.partial(
            InvPendulumState._draw_window, self)

    def _draw_window(self) -> None:
        """
        Internal utility function which handles visualization of the space.
        """

        self._window.clear()

        # get cart and pendulum vertices
        # ground is done apart since it's a line as opposed to a convex figure
        vertices = [v.rotated(self._cart_body.angle) + self._cart_body.position
                    for v in self._cart_shape.get_vertices()] + \
                   [v.rotated(self._pend_body.angle) + self._pend_body.position
                    for v in self._pend_shape.get_vertices()]

        # convert vertices to pixel coordinates and draw
        points = []
        for v in vertices:
            points.append(int(v.x * self._ppm) + self._floor_offset.x)
            points.append(int(v.x * self._ppm) + self._floor_offset.y)

        data = ('v2i', tuple(points))
        pyglet.graphics.draw(len(vertices), pyglet.gl.GL_LINE_LOOP, data)

        # ground
        vertices = [v + (0, self._ground.radius)
                    for v in (self._ground.a, self._ground.b)]

        # convert vertices to pixel coordinates and draw
        points = []
        for v in vertices:
            points.append(int(v.x * self._ppm) + self._floor_offset.x)
            points.append(int(v.x * self._ppm) + self._floor_offset.y)

        data = ('v2i', tuple(points))
        pyglet.graphics.draw(len(vertices), pyglet.gl.GL_LINES, data)


        for label in self._labels:
            label.draw()

    def advance(self,
                last_ts_ns: int,
                act_values: Dict[str, PhyPropType]) -> Dict[str, PhyPropType]:
        # apply actuation
        force = act_values.get('force', 0)
        self._cart_body.apply_force_at_local_point(Vec2d(force, 0.0),
                                                   Vec2d(0, 0))

        # advance the world state
        # delta T is received as nanoseconds, turn into seconds
        self._space.step(InvPendulumState.calculate_dt(last_ts_ns))

        # return new world state
        return {
            'position': self._cart_body.position.x,
            'speed'   : self._cart_body.velocity.x,
            'angle'   : self._pend_body.angle,
            'ang_vel' : self._pend_body.angular_velocity
        }
