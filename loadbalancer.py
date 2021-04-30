import argparse
import socket
import struct
import threading
import sys
import logging
import time
import subprocess
#import schedule
#import os

def get_args(argv=None):
    #parse arguments and send to main function

    parser = argparse.ArgumentParser(description="LOADBALANCER")
    parser.add_argument('-s', type=str, required=True, help='file containing IP addresses')
    parser.add_argument('-p', type=int, required=True, help='Port')
    parser.add_argument('-l', type=str, required=True, help='Log File')
    args = parser.parse_args()
    serverIpFile = args.s
    server_port = args.p
    log_file = args.l
    return serverIpFile, server_port, log_file

def send_packet(sock, data, server_addr):
    #send packet to server
    sock.sendto(data, server_addr)

def createPacket(**kwargs):
    #create packet to send to server

    num = 0
    s_n = kwargs['sequence_number']
    a_n = kwargs['ack_number']
    payload = kwargs['payload']
    if(kwargs['ack'] == 'Y'):
        num = update_bit(num, 2, 1)
    if(kwargs['syn'] == 'Y'):
        num = update_bit(num, 1, 1)
    if(kwargs['fin'] == 'Y'):
        num = update_bit(num, 0, 1)
    data = struct.pack('!I', s_n)
    data += struct.pack('!I', a_n)
    data += struct.pack('!I', num)
    data += struct.pack('I', len(payload)) + payload

    return data

def get_bit(num, i):
    #returns true if bit is 1, false if bit is 0
    return (num & (1 << i)) != 0

def print_bits(num):
    #prints number in 32 bit binary form
    print("{0:032b}".format(num))

def clear_bit(num, i):
    #converts bit to 0
    mask = ~(1 << i)
    return (num & mask)

def update_bit(num, i, bit):
    #update bit based on user choice
    mask = ~(1 << i)
    return (num & mask) | (bit << i)

def pingServers(ip1, ip2, ip3): 
    result = subprocess.run(["ping", ip1, "-c", "3"], capture_output=True, text=True)
    #print("stdout:", result.stdout)

    output = result.stdout
    output_string = output.split()
    #print(output_string)

    loss1 = output_string[-10].split('%')
    loss1 = loss1[0]
    delay1 = output_string[-6].split('m')
    delay1 = delay1[0]
    """ print("Loss = ", loss1)
    print("Delay = ", delay1) """

    loss1 = int(loss1)
    delay1 = int(delay1)

    preference1 = (0.75*loss1) + (0.25 * delay1)
    print("Preference 1: ", preference1)   

    result = subprocess.run(["ping", ip2, "-c", "3"], capture_output=True, text=True)
    #print("stdout:", result.stdout)

    output = result.stdout
    output_string = output.split()
    #print(output_string)

    loss1 = output_string[-10].split('%')
    loss1 = loss1[0]
    delay1 = output_string[-6].split('m')
    delay1 = delay1[0]
    """ print("Loss = ", loss1)
    print("Delay = ", delay1) """

    loss1 = int(loss1)
    delay1 = int(delay1)

    preference2 = (0.75*loss1) + (0.25 * delay1)
    print("Preference 2: ", preference2) 

    result = subprocess.run(["ping", ip3, "-c", "3"], capture_output=True, text=True)
    #print("stdout:", result.stdout)

    output = result.stdout
    output_string = output.split()
    #print(output_string)

    loss1 = output_string[-10].split('%')
    loss1 = loss1[0]
    delay1 = output_string[-6].split('m')
    delay1 = delay1[0]
    """ print("Loss = ", loss1)
    print("Delay = ", delay1) """

    loss1 = int(loss1)
    delay1 = int(delay1)

    preference3 = (0.75*loss1) + (0.25 * delay1)
    print("Preference 3: ", preference3)

    if(preference1 < preference2):
        if(preference1 < preference3):
            return ip1, preference1
        else:
            return ip3, preference3
    else:
        if(preference2 < preference3):
            return ip2, preference2
        else:
            return ip3,preference3
    

if __name__=='__main__':

    serverIpFile, serverPort, logFile = get_args(sys.argv[1:])
    IP = socket.gethostbyname(socket.gethostname())
    print(IP)
    PORT = serverPort
    SERVER_ADDR = (IP, PORT)

    logging.basicConfig(filename=logFile, filemode='w', format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s', level=logging.INFO)
    logging.info("STARTING LOADBALANCER")
    logging.info(f"Server IP File = {serverIpFile}, Port = {PORT}, Log Location = {logFile} ")

    with open(serverIpFile) as reader:
        IP1 = reader.readline().strip()
        IP2 = reader.readline().strip()
        IP3 = reader.readline().strip()
    


    while(True):
        SERVER_IP, preference = pingServers(IP1, IP2, IP3)
        


        print(f"Connecting client to: {SERVER_IP}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(SERVER_ADDR)

        data, addr = sock.recvfrom(1024)
        recvData, recvPayload = struct.unpack('!IIII', data[:16]), data[16:]
        logging.info(f"Request from {addr[0]}. Redirecting to {SERVER_IP}, Preference: {preference} ")
        SERVER_IP = SERVER_IP.encode()
        send_data = createPacket(sequence_number = 0, ack_number = 0, ack = 'N', syn = 'N', fin = 'N', payload = SERVER_IP)
        send_packet(sock, send_data, addr)

    




