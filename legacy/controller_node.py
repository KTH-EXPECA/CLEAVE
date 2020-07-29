import csv
import math
import numpy as np

import pyglet
import pymunk

from time import sleep
from multiprocessing import Process, Manager, Value, Array, Queue
import socket
import argparse


SCREEN_HEIGHT = 700
window = pyglet.window.Window(1000, SCREEN_HEIGHT, vsync=False, caption='Inverted Pendulum Simulator')

# setup the space
space = pymunk.Space(threaded = True)
space.gravity = 0, -9.8

fil = pymunk.ShapeFilter(group=1)

# ground
ground = pymunk.Segment(space.static_body, (-4, -0.1), (4, -0.1), 0.1)
ground.friction = 0.1
ground.filter = fil
space.add(ground)

# cart
cart_mass = 0.5
cart_size = 0.3, 0.2
cart_moment = pymunk.moment_for_box(cart_mass, cart_size)
cart_body = pymunk.Body(mass=cart_mass, moment=cart_moment)
cart_body.position = 0.0, cart_size[1] / 2
cart_shape = pymunk.Poly.create_box(cart_body, cart_size)
cart_shape.friction = ground.friction
space.add(cart_body, cart_shape)

# pendulum
pend_length = 0.6  # to center of mass
pend_size = 0.1, pend_length * 2  # to get CoM at 0.6 m
pend_mass = 0.2
pend_moment = 0.001
pend_body = pymunk.Body(mass=pend_mass, moment=pend_moment)
pend_body.position = cart_body.position[0], cart_body.position[1] + cart_size[1] / 2 + pend_length
pend_shape = pymunk.Poly.create_box(pend_body, pend_size)
pend_shape.filter = fil
space.add(pend_body, pend_shape)

# joint
joint = pymunk.constraint.PivotJoint(cart_body, pend_body, cart_body.position + (0, cart_size[1] / 2))
joint.collide_bodies = False
space.add(joint)

response_deq = Queue()

print(f"cart mass = {cart_body.mass:0.1f} kg")
print(f"pendulum mass = {pend_body.mass:0.1f} kg, pendulum moment = {pend_body.moment:0.3f} kg*m^2")

## Parameters of the pendulum; usually determined a priori by modeling
K = [-57.38901804, -36.24133932, 118.51380879, 28.97241832]
Nbar = -57.25
state = Array('d', [0, 0, 0, 0])

# simulation stuff
force = 0.0
MAX_FORCE = 25
DT = 1 / 60.0
ref = Value('d', 0.0)

# drawing stuff
# pixels per meter
PPM = 200.0

color = (200, 200, 200, 200)
label_x = pyglet.text.Label(text='', font_size=18, color=color, x=10, y=SCREEN_HEIGHT - 28)
label_ang = pyglet.text.Label(text='', font_size=18, color=color, x=10, y=SCREEN_HEIGHT - 58)
label_force = pyglet.text.Label(text='', font_size=18, color=color, x=10, y=SCREEN_HEIGHT - 88)
label_time = pyglet.text.Label(text='', font_size=18, color=color, x=10, y=SCREEN_HEIGHT - 118)


labels = [label_x, label_ang, label_force, label_time]

# data recorder so we can compare our results to our predictions
currtime = 0.0


def draw_body(offset, body):
    '''Draws the inverted pendulum for GUI
    ;;;Args: offset: 2-D position of the cart
    body: bodies including the pendulum and card
    '''

    for shape in body.shapes:
        if isinstance(shape, pymunk.Circle):
            # TODO
            pass
        elif isinstance(shape, pymunk.Poly):
            # get vertices in world coordinates
            vertices = [v.rotated(body.angle) + body.position for v in shape.get_vertices()]

            # convert vertices to pixel coordinates
            points = []
            for v in vertices:
                points.append(int(v[0] * PPM) + offset[0])
                points.append(int(v[1] * PPM) + offset[1])

            data = ('v2i', tuple(points))
            pyglet.graphics.draw(len(vertices), pyglet.gl.GL_LINE_LOOP, data)


def draw_ground(offset):
    '''Draws the inverted pendulum for GUI
    ;;;Args: offset: 2-D position of the cart
    '''

    vertices = [v + (0, ground.radius) for v in (ground.a, ground.b)]

    # convert vertices to pixel coordinates
    points = []
    for v in vertices:
        points.append(int(v[0] * PPM) + offset[0])
        points.append(int(v[1] * PPM) + offset[1])

    data = ('v2i', tuple(points))
    pyglet.graphics.draw(len(vertices), pyglet.gl.GL_LINES, data)


@window.event
def on_draw():
    '''Wrapper function to draw the ground, cart and pendulum
    '''
    window.clear()

    # center view x around 0
    offset = (500, 5)
    draw_body(offset, cart_body)
    draw_body(offset, pend_body)
    draw_ground(offset)

    for label in labels:
        label.draw()

UDP_LOCAL_IP_ADDRESS = "127.0.0.1"
UDP_EDGE_IP_ADDRESS = "127.0.0.1"
SENSOR_UDP_PORT_NO = 6789
EDGE_UDP_PORT_NO = 6790

import time

def receive_force_process(state, ref, response_deq, delay):
    """Computes the amount of force to be applied. Also applies some delay
    Args: state: current state of the system
    ref: current x-axis position of the cart
    response_deq: queue with all the responses
    delay: any additional delay for experiments
    """

    clientSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    serverSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    serverSock.bind((UDP_LOCAL_IP_ADDRESS, SENSOR_UDP_PORT_NO))

    while True:
        message = str(state[0]) + ' ' + str(state[1]) + ' ' + str(state[2]) + ' ' + str(state[3]) + ' ' +\
                                       str(ref.value) + ' ' + str(time.time())
        message = bytearray(message, encoding='UTF-8')
        clientSock.sendto(message, (UDP_EDGE_IP_ADDRESS, EDGE_UDP_PORT_NO))

        data, addr = serverSock.recvfrom(65536)
        values = data.decode('UTF-8')
        u = float(values)
        sleep(delay)
        response_deq.put(u, True)

def compute_force_process(state, ref, response_deq, delay):
    """Computes the amount of force to be applied. Also applies some delay.
    This controller uses linear feedback delay. Used only for the process-based method.
    Args: state: current state of the system
    ref: current x-axis position of the cart
    response_deq: queue with all the responses
    delay: any additional delay for experiments
    """

    while True:
        cur_time = time.time()
        sleep(delay)
        gain = K[0] * state[0] + K[1] * state[1] + K[2] * state[2] + K[3] * state[3]
        force = ref.value * Nbar - gain
        print(state[0], state[1], state[2], state[3], ref.value)

        # kill our motors if we go past our linearized acceptable angles
        if math.fabs(pend_body.angle) > 0.35:
            force = 0.0

        # cap our maximum force so it doesn't go crazy
        if math.fabs(force) > MAX_FORCE:
            force = math.copysign(MAX_FORCE, force)

        sleep(delay)
        response_deq.put(force)
        print('time (ms) = ', (time.time() - cur_time) * 1000, 'force = ', force)


def simulate(_):
    """Runs the actual simulation and updates plant state.
    Simulation involves actual updating of time, and current state,
     and then applying force as a response
     """

    # ensure we get a consistent simulation step - ignore the input dt value
    #asyncio.sleep(0.3)
    dt = DT

    # simulate the world
    # NOTE: using substeps will mess up gains
    space.step(dt)

    global currtime
    currtime += dt

    # calculate our gain based on the current state
    # apply force to cart center of mass
    state[0] = cart_body.position[0]
    state[1] = cart_body.velocity[0]
    state[2] = pend_body.angle
    state[3] = pend_body.angular_velocity

    response_step()
    #print(state[0], state[1], state[2], state[3], currtime)


def response_step():
    """Applies force as directed by the other process.
    We utilize only the LAST response in the queue. If queue is empty, just apply a force of 0
    """

    global force
    force = 0
    while response_deq.empty() is False:
        force = response_deq.get()

    cart_body.apply_force_at_local_point((force, 0.0), (0, 0))

def update_state_label(_):
    """Prints the numbers on the figure
    Args: _ : current time """

    label_x.text = f'Cart X: {cart_body.position[0]:0.3f} m'
    label_ang.text = f'Pendulum Angle: {pend_body.angle * 57.2958:0.3f} degrees'
    label_force.text = f'Force: {force:0.1f} newtons'
    label_time.text = f'Time: {currtime:0.3f} s'

def update_reference(_, newref):
    """Prints the numbers on the figure
    Args: _ : current time,
     newref: New position of the cart along X axis
     """
    global ref
    ref.value = newref

def socket_technique(delay):
    """Wrapper function to run socket-based controller.
    Works using two separate processes. Process P1 runs the actual simulation.
    Process P2 sends the current state to the controller using a socket, and receives the response.
    P2 places the received response on a queue (response_deq). P1 pops element from
    response_deq to periodically respond and update state. ref is the current position
    of the cart on X-axis. To test its working, we then update the ref value and check if our
    controller can balance the pendulum.
    Args: delay: Additional delay to add for testing
    """
    state[0] = cart_body.position[0]
    state[1] = cart_body.velocity[0]
    state[2] = pend_body.angle
    state[3] = pend_body.angular_velocity
    delay = delay / 1000.0

    force_process = Process(target=receive_force_process, args=(state, ref, response_deq, delay))
    force_process.start()

    pyglet.clock.schedule_interval(simulate, DT)
    pyglet.clock.schedule_interval(update_state_label, 0.25)

    # schedule some small movements by updating our reference
    pyglet.clock.schedule_once(update_reference, 1, 0.1)
    pyglet.clock.schedule_once(update_reference, 5, 0.2)
    pyglet.clock.schedule_once(update_reference, 7, 0.1)
    pyglet.clock.schedule_once(update_reference, 10, 0.0)
    pyglet.clock.schedule_once(update_reference, 12, 0.1)

    pyglet.app.run()
    force_process.kill()

def process_technique(delay):
    """Wrapper function to run process-based controller.
    Works using two separate processes. Process P1 runs the actual simulation.
    Process P2 computes the response using linear feedback control.
    P2 places the computed response on a queue (response_deq). P1 pops element from
    response_deq to periodically respond and update state. ref is the current position
    of the cart on X-axis. To test its working, we then update the ref value and check if our
    controller can balance the pendulum.
    Args: delay: Additional delay to add for testing
    """
    state[0] = cart_body.position[0]
    state[1] = cart_body.velocity[0]
    state[2] = pend_body.angle
    state[3] = pend_body.angular_velocity
    delay = delay / 1000.0 #convert from ms to s

    force_process = Process(target=compute_force_process, args=(state, ref, response_deq, delay))
    force_process.start()

    pyglet.clock.schedule_interval(simulate, DT)
    pyglet.clock.schedule_interval(update_state_label, 0.25)

    # schedule some small movements by updating our reference
    pyglet.clock.schedule_once(update_reference, 1, 0.1)
    pyglet.clock.schedule_once(update_reference, 7, 0.1)
    pyglet.clock.schedule_once(update_reference, 12, 0.0)
    pyglet.clock.schedule_once(update_reference, 17, 0.2)
    pyglet.clock.schedule_once(update_reference, 5, 0.0)

    pyglet.app.run()
    force_process.kill()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Control an inverted pendulum')
    parser.add_argument('-m', '--method', metavar='method [socket|process]', default='socket',
                        type=str, dest='method')
    parser.add_argument('-d', '--delay', metavar='delay', default=0.0, type=float, dest='delay',
                        help = 'Additional delay to add for experiments in milliseconds')

    args = parser.parse_args()
    if args.method.lower() == 'socket':
        socket_technique(args.delay)
    elif args.method.lower() == 'process':
        process_technique(args.delay)
# close the output file
