---
jupyter:
  jupytext:
    formats: ipynb,md
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.2'
      jupytext_version: 1.5.0
  kernelspec:
    display_name: Python 3
    language: python
    name: python3
---

```python
# Pole location of the original unstable system
import numpy as np
import math
import time
import cvxpy as cp
import scipy.signal
from numpy import linalg as LA
from scipy.integrate import odeint
from numpy.linalg import matrix_rank

M  = 0.5          # Mass of the cart (kg)
m  = 0.2          # Mass of the inverted pendulum (kg)
I  = 0.006        # Moment of inertia of the inverted pendulum (kg-m^2)
l  = 0.3          # Length of the pendulum (m)
bc = 0.1          # Coefficient of friction for the cart
bp = 0.012        # Coefficient of friction for the pendulum
g  = 9.81         # Acceleration due to gravity (m/s^2)
Ts = 0.1          # Sampling time (s)
v1 = (M + m)/(I*(M + m) + m*M*l**2)
v2 = (I + m*l**2)/(I*(M + m) + m*M*l**2)

# Ac matrix
a11  = 0 
a12  = 1 
a13  = 0 
a14  = 0
a21  = 0
a22  = -bc*v2
a23  = m**2*l**2*g*v2/(I+m*l**2)
a24  = -m*l*bp*v2/(I+m*l**2)
a31  = 0
a32  = 0
a33  = 0
a34  = 1
a41  = 0
a42  = -(m*l*bc*v1)/(m+M)
a43  = m*g*l*v1
a44  = -bp*v1        
Ac =np.array([[a11, a12, a13, a14],
              [a21, a22, a23, a24],
              [a31, a32, a33, a34],
              [a41, a42, a43, a44]])     

# Bc matrix       
Bc = np.array([
    [0],
    [v2],
    [0],
    [m*l*v1/(m+M)]
])

# Output matrices
Cc = np.array([[1.0, 0.0, 0.0, 0.0]])
#Cc = Cc[np.newaxis, :]

Dc = np.array([[0.0]])  
# Bwc matrix (disturbance matrix)      
Bwc = np.array([
    [0],
    [-(I*v2)/(I+m*l**2)],
    [0],
    [m*l*v1/(m+M)]
])

sys  = (Ac, Bc, Cc, Dc)

sysd = scipy.signal.cont2discrete(sys, Ts, method='zoh', alpha=None)
A   = sysd[0]
B   = sysd[1]
C   = sysd[2]
D   = sysd[3]

[nx, nu] = Bc.shape 

# Check actual and augmented (augmenting disturbance input) state-space model parameters
print("\n Discrete-time state space model of the inverted pendulum: \n A = \n", A)
print("\n B = \n", B)
print("\n C = \n", C)
print("\n D = \n", D)


# Check Reacability
W = np.zeros((nx,nx))
for i in range(nx):
    if i == 0:
        APoweri = np.eye(nx)
    else:
        APoweri = A**i
            
    W[:,i] = APoweri.dot(B)[:,0]
    


# number of states and number or inputs      

# Continuous-time system in state space (Disturbance is not included)


# Continuous-time system dynamics
def linearizedSystemDynamics(x,t,u,w):
    dxdt = Ac.dot(x) + Bc.dot(u) + Bwc.dot(w)
    return dxdt

openLoopPoles, _ = LA.eig(A)
print(" \n Open-loop poles are located at: ", openLoopPoles)

# Desired pole locations
p1    = 0.1 + 0.1j
p2    = 0.1 - 0.1j
p3    = 0.97 + 0.02j
p4    = 0.97 - 0.02j
poles = np.array([p1, p2, p3, p4])

# Pole-placement method
fsf   = scipy.signal.place_poles(A, B, poles, method='YT')
closedLoopPoles = fsf.computed_poles
print(" \n Closed-loop poles are located at: ", closedLoopPoles)

# Plot open-loop and closed-loop poles
# t1 = np.linspace(0, 2*np.pi, 401)
# plt.figure(figsize=(8, 8))
# plt.plot(np.cos(t1), np.sin(t1), 'k--', linewidth=2)  # unit circle
# plt.plot(openLoopPoles.real, openLoopPoles.imag,'ro',  markersize=16, label='open-loop poles')
# plt.plot(closedLoopPoles.real, closedLoopPoles.imag,'bx', markersize=16, label='closed-loop poles')
# plt.grid()
# plt.axis('image')
# plt.axis([-1.8, 1.8, -1.8, 1.8])
# plt.title('Pole zero plot of the inverted pendulum with and without state-feedback controller', pad = 30, fontsize =16, color = 'blue')
# plt.legend(bbox_to_anchor=(1.05, 1), loc=2, numpoints=1)

# Feedback gain by pole placement# Pole location of the original unstable system
L = fsf.gain_matrix
print(" \n Feedback gain =", L)

# feedforward gain of the controller
lr = 1/(np.dot(C, np.dot(LA.inv(np.identity(4) - A + B*L), B)))
print(" \n Feed-forward gain =", lr)

```

```python
import socket
from multiprocessing import Process, Value, Array
import ctypes

UDP_LOCAL_IP_ADDRESS = "192.168.2.5"
UDP_EDGE_IP_ADDRESS = "192.168.2.2"
SENSOR_UDP_PORT_NO = 6789
EDGE_UDP_PORT_NO = 6790
ARRAY_SIZE = 1500


def compute_u_linear():
    serverSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    serverSock.bind((UDP_LOCAL_IP_ADDRESS, EDGE_UDP_PORT_NO))
    while True:
        data, addr = serverSock.recvfrom(65536) #
        cur_time = time.time()
        values = data.decode('UTF-8')
        values = values.replace('[', '')
        values = values.replace(']', '')
        values = values.split(' ')
        
        print(values)
        values = [float(v) for v in values if v != '']
        u = -L.dot(values[0:4]) + lr*values[4]
        ack_Message = bytearray(str(u), encoding='UTF-8')
        clientSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print('Time taken = ', time.time() - cur_time)
        clientSock.sendto(ack_Message, (UDP_EDGE_IP_ADDRESS, SENSOR_UDP_PORT_NO))
        print(ack_Message)
compute_u_linear()
```

```python

```

```python

```

```python

```
