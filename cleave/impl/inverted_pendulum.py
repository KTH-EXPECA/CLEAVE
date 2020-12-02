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
from multiprocessing import Event, Queue
from queue import Empty, Full

import numpy as np
import pymunk
from pymunk.vec2d import Vec2d

from ..api.controller import Controller
from ..api.plant import ActuatorVariable, SensorVariable, State
from ..api.util import PhyPropMapping

#: Gravity constants
G_CONST = Vec2d(0, -9.8)


def visualization_loop(input_q: Queue,
                       shutdown_event: Event,
                       window_w: int,
                       window_h: int,
                       caption: str,
                       ppm: float = 200.0) -> None:
    """
    Utility function that executes a Pyglet GUI loop to graphically visualize
    the inverted pendulum. Should always be called from a separate Process.

    Parameters
    ----------
    input_q
        Input queue which holds dictionaries describing the figures to be
        drawn on screen.
    shutdown_event
        Event to signal a shutdown of the Plant.
    window_w
        Window width.
    window_h
        Window height.
    caption
        Window caption.
    ppm
        Factor relating number of pixels per meter.

    Returns
    -------

    """
    import pyglet
    window = pyglet.window.Window(window_w, window_h,
                                  vsync=False,
                                  caption=caption)
    floor_offset = Vec2d(window_w / 2, 5)  # TODO fix magic number

    def on_draw(dt):
        # TODO: needs a timeout for shutdown
        while True:
            if shutdown_event.is_set():
                window.close()
                pyglet.app.exit()
                return

            try:
                coord_dict = input_q.get(block=True, timeout=0.01)
                break
            except Empty:
                continue

        window.clear()
        for shape in coord_dict['shapes']:
            raw_vertices = shape['vertices']
            angle = shape['angle']
            position = shape['position']
            # get vertices in world coordinates
            vertices = [Vec2d(v).rotated(angle) + position for v in
                        raw_vertices]

            # convert vertices to pixel coordinates
            points = []
            for v in vertices:
                v2 = (v * ppm) + floor_offset
                points.append(v2.x)
                points.append(v2.y)

            data = ('v2i', tuple(map(int, points)))
            pyglet.graphics.draw(len(vertices),
                                 pyglet.gl.GL_LINE_LOOP,
                                 data)

        for line in coord_dict['lines']:
            raw_vertices = line['vertices']
            radius = line['radius']
            vertices = [Vec2d(v) + (0, radius) for v in raw_vertices]

            # convert vertices to pixel coordinates
            points = []
            for v in vertices:
                v2 = (v * ppm) + floor_offset
                points.append(v2.x)
                points.append(v2.y)

            data = ('v2i', tuple(map(int, points)))
            pyglet.graphics.draw(len(vertices), pyglet.gl.GL_LINES, data)

    pyglet.clock.schedule_interval(on_draw, 1 / 60.0)
    pyglet.app.run()


class InvPendulumState(State):
    """
    Implementation of a discrete-time simulation of an inverted pendulum.
    """

    def __init__(self,
                 ground_friction: float = 0.1,
                 cart_mass: float = 0.5,
                 cart_dims: Vec2d = Vec2d(0.3, 0.2),
                 pend_com: float = 0.6,
                 pend_width: float = 0.1,
                 pend_mass: float = 0.2,
                 pend_moment: float = 0.001,  # TODO: calculate with pymunk?
                 ):
        """

        Parameters
        ----------
        ground_friction
            Friction factor to apply for the ground.
        cart_mass
            Mass of the pendulum cart in Kg.
        cart_dims
            Dimensions of the cart in meters.
        pend_com
            Center of mass for the pendulum arm.
        pend_width
            Width of the pendulum arm in meters.
        pend_mass
            Mass of the pendulum in Kg.
        pend_moment
            Moment of the pendulum.
        """
        super(InvPendulumState, self).__init__()
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

        # the angle should never exceed ~20 degrees
        self.angle = SensorVariable(self._pend_body.angle,
                                    sanity_check=
                                    lambda angle: np.abs(angle) < 0.34)

        self.ang_vel = SensorVariable(self._pend_body.angular_velocity)

    def advance(self, delta_t: float) -> None:
        # apply actuation
        force = self.force
        self._cart_body.apply_force_at_local_point(Vec2d(force, 0.0),
                                                   Vec2d(0, 0))

        # advance the world state
        self._space.step(delta_t)
        # angle_deg = np.degrees(self._pend_body.angle)

        # setup new world state
        self.position = self._cart_body.position.x
        self.speed = self._cart_body.velocity.x
        self.angle = self._pend_body.angle
        self.ang_vel = self._pend_body.angular_velocity


class InvPendulumStateWithViz(InvPendulumState):
    """
    Implementation of a discrete-time simulation of an inverted pendulum,
    with a graphical visualization using Pyglet.
    """

    def __init__(self,
                 ground_friction: float = 0.1,
                 cart_mass: float = 0.5,
                 cart_dims: Vec2d = Vec2d(0.3, 0.2),
                 pend_com: float = 0.6,
                 pend_width: float = 0.1,
                 pend_mass: float = 0.2,
                 pend_moment: float = 0.001,  # TODO: calculate with pymunk?
                 window_w: int = 1000,
                 window_h: int = 700,
                 caption: str = 'Inverted Pendulum Simulation',
                 ppm: float = 200.0
                 ):
        """

        Parameters
        ----------
        ground_friction
            Friction factor to apply for the ground.
        cart_mass
            Mass of the pendulum cart in Kg.
        cart_dims
            Dimensions of the cart in meters.
        pend_com
            Center of mass for the pendulum arm.
        pend_width
            Width of the pendulum arm in meters.
        pend_mass
            Mass of the pendulum in Kg.
        pend_moment
            Moment of the pendulum.
        """
        from multiprocessing.context import Process

        super(InvPendulumStateWithViz, self).__init__(
            ground_friction=ground_friction,
            cart_mass=cart_mass,
            cart_dims=cart_dims,
            pend_com=pend_com,
            pend_width=pend_width,
            pend_mass=pend_mass,
            pend_moment=pend_moment,
        )

        self._coord_q = Queue(maxsize=1)
        self._shutdown_event = Event()

        self._draw_proc = Process(target=visualization_loop,
                                  kwargs=dict(
                                      input_q=self._coord_q,
                                      shutdown_event=self._shutdown_event,
                                      window_w=window_w,
                                      window_h=window_h,
                                      caption=caption,
                                      ppm=ppm,
                                  ))

    def initialize(self) -> None:
        super(InvPendulumStateWithViz, self).initialize()
        self._shutdown_event.clear()
        self._draw_proc.start()

    def shutdown(self) -> None:
        super(InvPendulumStateWithViz, self).shutdown()
        self._shutdown_event.set()
        self._draw_proc.join(timeout=10)  # TODO magic num

    def advance(self, delta_t: float) -> None:
        super(InvPendulumStateWithViz, self).advance(delta_t)

        # after advancing, send things to drawing loop
        shapes = []
        for body in (self._cart_body, self._pend_body):
            shapes += [{
                'vertices': [(v.x, v.y) for v in shape.get_vertices()],
                'angle'   : body.angle,
                'position': (body.position.x, body.position.y),
            } for shape in body.shapes]

        lines = []
        for line in (self._ground,):
            lines += [{
                'radius'  : line.radius,
                'vertices': ((line.a.x, line.a.y), (line.b.x, line.b.y)),
            }]

        coord_dict = {
            'shapes': shapes,
            'lines' : lines
        }

        try:
            self._coord_q.put_nowait(coord_dict)
        except Full:
            pass


class InvPendulumController(Controller):
    """
    Proportional-differential controller for the Inverted Pendulum.
    """

    #: Pendulum parameters
    K = [-57.38901804, -36.24133932, 118.51380879, 28.97241832]
    NBAR = -57.25

    def __init__(self, ref: float = 0.0, max_force: float = 25):
        """

        Parameters
        ----------
        ref:
            Position on the X-axis around which to balance the pendulum.
        max_force
            Maximum force, in Newtons, allowed to apply to the pendulum.
        """
        super(InvPendulumController, self).__init__()
        self._count = 0
        self._ref = ref
        self._max_force = max_force

    def process(self, sensor_values: PhyPropMapping) -> PhyPropMapping:
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
