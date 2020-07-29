import numpy as np
import math
import time
import scipy.signal
from numpy import linalg as LA
from scipy.integrate import odeint
from numpy.linalg import matrix_rank
import socket

UDP_LOCAL_IP_ADDRESS = "127.0.0.1"
UDP_EDGE_IP_ADDRESS = "127.0.0.1"
SENSOR_UDP_PORT_NO = 6789
EDGE_UDP_PORT_NO = 6790


serverSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
serverSock.bind((UDP_LOCAL_IP_ADDRESS, EDGE_UDP_PORT_NO))

K = [-57.38901804, -36.24133932, 118.51380879, 28.97241832]
Nbar = -57.25


def parse_data(a):
    new_a = [0] * 6
    count = 0
    for x in a:
        try:
            new_a[count] = float(x)
            count += 1
        except ValueError:
            pass
    return new_a

clientSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
while True:
    data, addr = serverSock.recvfrom(65536)
    cur_time = time.time()
    print(data)
    values = data.decode('UTF-8')
    values = values.split(' ')
    state = parse_data(values)
    gain =  K[0] * state[0] + K[1] * state[1] + K[2] * state[2] + K[3] * state[3]
    force = state[4] * Nbar - gain
    ack_Message = bytearray(str(force), encoding='UTF-8')
    clientSock.sendto(ack_Message, (UDP_EDGE_IP_ADDRESS, SENSOR_UDP_PORT_NO))

    #print(ack_Message)