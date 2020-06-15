#  Copyright (c) 2020.  Copyright 2020 KTH Royal Institute of Technology
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may not use this project except in compliance with the License. A copy of the license is included in the LICENSE file.
#
#  Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

import matplotlib.pyplot as plt
import numpy as np
import math
import time
import scipy.signal
from numpy import linalg as LA
from scipy.integrate import odeint
from numpy.linalg import matrix_rank
import socket
from environment import Environment
from numba import jit
import line_profiler
profile = line_profiler.LineProfiler()
import atexit  #Activate to profile
atexit.register(profile.print_stats) #Activate to profile

M = 0.5  # Mass of the cart (kg)
m = 0.2  # Mass of the inverted pendulum (kg)
I = 0.006  # Moment of inertia of the inverted pendulum (kg-m^2)
l = 0.3  # Length of the pendulum (m)
bc = 0.1  # Coefficient of friction for the cart
bp = 0.012  # Coefficient of friction for the pendulum
g = 9.81  # Acceleration due to gravity (m/s^2)
ml = m * l
ml2 = ml * ml
I_ml2 = I + ml2
M_m = M + m

UDP_LOCAL_IP_ADDRESS = "192.168.2.2"
UDP_SERVICE_IP_ADDRESS = "192.168.2.5"
SENSOR_UDP_PORT_NO = 6789
EDGE_UDP_PORT_NO = 6790


@jit(nopython=True)
def compute_x1(F, W, v, omega, sin_val, cos_val):
    return (F + (ml * l * cos_val ** 2 / I_ml2 - 1) * W - bc * v - ml * sin_val * omega * omega + ml2 * g * sin_val * cos_val / I_ml2 - ml * bp * cos_val * omega / I_ml2) / (M + m - ml2 * cos_val ** 2 / I_ml2)

@jit(nopython=True)
def compute_x2(F, W, v, omega, sin_val, cos_val):
     return (ml * cos_val * F / M_m + M * l * cos_val * W / M_m - bp * omega + ml * g * sin_val - ml2 * omega * omega * sin_val * cos_val / M_m - ml * bc * v * cos_val / M_m) / (I_ml2 - ml2 * cos_val ** 2 / M_m)

def nonlinearSystemDynamics(x, t, u, w):
    F = u  # Horizontal force on the pendulum
    W = w  # Horizontal wind force on the pendulum (in a direction opposite to the motion of the pendulum)
    p = x[0]  # Position of the cart
    v = x[1]  # Linear velocity of the cart
    theta = x[2]  # Angular position of the pendulum
    omega = x[3]  # Angular velocity of the pendulum
    cos_val = math.cos(theta)
    sin_val = math.sin(theta)

    der_x = np.zeros(4, dtype='float64')
    der_x[0] = x[1]
    der_x[1] = compute_x1(F, W, v, omega, sin_val, cos_val)
    der_x[2] = x[3]
    der_x[3] = compute_x2(F, W, v, omega, sin_val, cos_val)
    return der_x

def call_u_linear(x0, xRef):
    clientSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    message = str(x0) + ' ' + str(xRef)
    # print('Message = ', message)
    message = bytearray(message, encoding='UTF-8')
    clientSock.sendto(message, (UDP_SERVICE_IP_ADDRESS, EDGE_UDP_PORT_NO))

    serverSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    serverSock.bind((UDP_LOCAL_IP_ADDRESS, SENSOR_UDP_PORT_NO))
    data, addr = serverSock.recvfrom(65536)
    values = data.decode('UTF-8')[2:-2]
    u = float(values)
    # print('Values = ', values, 'u = ', u)
    return u

def simulate_non_linear(Ts):
    phi0 = 30 * np.pi / 180
    X0 = np.array([0, 0, phi0, 0])  # initial state

    t0 = 0
    tf = 50
    t = np.arange(t0, tf + Ts, Ts)
    state_dim = (4, len(t))

    xRef = 5.0

    # Store system trajectory and control input
    Xsim = np.zeros(state_dim)
    Xsim[:, 0] = X0
    input_dim = (1, len(t))

    U = np.zeros(input_dim)

    # Realized disturbance
    w = 0.0
    # Simulate the state-feedback and feed forward controller with nonlinear continuous-time model
    # of the inverted pendulum
    for i in range(len(t) - 1):
        ts = [t[i], t[i + 1]]
        #U[:,i] = -L.dot(X0) + lr*xRef
        U[:, i] = call_u_linear(X0, xRef)
        cur_time = time.time()
        Y = odeint(nonlinearSystemDynamics, X0, ts, args=(U[:, i], w))
        X0 = Y[1]
        Xsim[:, i + 1] = X0

        print('Time = ', time.time() - cur_time)

    # Plot system trajectory and control input
    # plt.figure(3)
    # plt.subplot(2, 1, 1)
    # plt.plot(t, xRefVec, 'r--', linewidth=3, label='Reference Position')
    # plt.plot(t, Xsim[0, :], 'b', linewidth=3, label='Cart Position')
    # plt.xlim(t0, tf)
    # plt.ylabel(r'$x~(m)$')
    # plt.legend(loc='best')
    # plt.title('State trajectory of inverted pendulum under state-feedback controller', pad=30, fontsize=16,
    #           color='blue')
    # plt.subplot(2, 1, 2)
    #
    # plt.plot(t, thetaRefVec, 'r--', linewidth=3, label='Reference Angle')
    # plt.plot(t, Xsim[2, :] * (180 / np.pi), 'b', linewidth=3, label='Pendulum Angle')
    # plt.xlim(t0, tf)
    # plt.xlabel(r'$t~(s)$')
    # plt.ylabel(r'$\theta~(^{\circ})$')
    # plt.legend(loc='best')
    # plt.show()
    #
    # plt.figure(4)
    # plt.plot(t, U[0, :], 'b', linewidth=3, label='Control Input')
    # plt.xlim(t0, tf)
    # plt.xlabel(r'$t~(s)$')
    # plt.ylabel(r'$F~(N)$')
    # plt.legend(loc='best')
    # plt.title('Control input under state-feeback and reference feed-forward controller', pad=30, fontsize=16,
    #           color='blue')
    # plt.show()

if __name__ == '__main__':
    simulate_non_linear(Ts = 0.0005)
