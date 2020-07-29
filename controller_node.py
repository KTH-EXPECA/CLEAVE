import math
import time
import socket

UDP_LOCAL_IP_ADDRESS = "127.0.0.1"
UDP_EDGE_IP_ADDRESS = "127.0.0.1"
SENSOR_UDP_PORT_NO = 6789
EDGE_UDP_PORT_NO = 6790



## Parameters of the pendulum; usually determined a priori by modeling
K = [-57.38901804, -36.24133932, 118.51380879, 28.97241832]
Nbar = -57.25


def parse_data(a):
    '''Parses the message received as a string and converts them into floats
    Args: a: Message received as a list of strings
    Returns: state variables received as list of floats
    '''
    new_a = [0] * 6
    count = 0
    for x in a:
        try:
            new_a[count] = float(x)
            count += 1
        except ValueError:
            pass
    return new_a

if __name__ == "__main__":
    '''Receives current state and computes the amount of force to be applied.
    Sends it back using another socket.'''
    clientSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    serverSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    serverSock.bind((UDP_LOCAL_IP_ADDRESS, EDGE_UDP_PORT_NO))
    
    while True:
        data, addr = serverSock.recvfrom(65536)
        values = data.decode('UTF-8')
        values = values.split(' ')
        state = parse_data(values)
        gain =  K[0] * state[0] + K[1] * state[1] + K[2] * state[2] + K[3] * state[3]
        force = state[4] * Nbar - gain
        ack_Message = bytearray(str(force), encoding='UTF-8')
        clientSock.sendto(ack_Message, (UDP_EDGE_IP_ADDRESS, SENSOR_UDP_PORT_NO))

    #print(ack_Message)
