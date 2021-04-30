from socket import *
import struct
import argparse
import logging
import sys
import select



def get_args(argv=None):
    #parse arguments and send back to main function

    parser = argparse.ArgumentParser(description="ANONCLIENT")
    parser.add_argument('-s', type=str, required=True, help='Server IP')
    parser.add_argument('-p', type=int, required=True, help='Port')
    parser.add_argument('-l', type=str, required=True, help='logFile')
    parser.add_argument('-f', type=str, required=True, help='file to save webpage')
    args = parser.parse_args()
    server_ip = args.s
    server_port = args.p
    log_file = args.l
    saveFile = args.f    
    return server_ip, server_port, log_file, saveFile

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

def send_packet(sock, data, server_addr):
    #send packet to server
    sock.sendto(data, server_addr)

def handshake(sock):
    #initiate handshake

    #send first packet
    send_data = createPacket(sequence_number = 12345, ack_number = 0, ack = 'N', syn = 'Y', fin = 'N', payload = b"")
    logging.info(f"SEND: Sequence: {12345} Acknowlegment: {0} Flags: ACK: N SYN: Y FIN: N")
    send_packet(sock, send_data, SERVER_ADDR)

    #receive packet
    data, addr = sock.recvfrom(1024)
    recvData, recvPayload = struct.unpack('!IIII', data[:16]), data[16:]
    logging.info(f"RECV: Sequence: {recvData[0]} Acknowlegment: {recvData[1]} Flags: ACK: Y SYN: Y FIN: N")
    send_data = createPacket(sequence_number = recvData[1], ack_number = recvData[0] + 1, ack = 'Y', syn = 'N', fin = 'N', payload = b"")

    #send second packet, handshake complete
    logging.info(f"SEND: Sequence: {recvData[1]} Acknowlegment: {recvData[0] + 1} Flags: ACK: Y SYN: N FIN: N")
    send_packet(sock, send_data, SERVER_ADDR)
    logging.info(f"HANDSHAKE COMPLETE")
    return recvData[0], recvData[1], recvData[2], recvPayload

def recvFile(sock, saveFile):
    #receives file from server one piece at a time and saves it to a file

    #open file to save to
    file = open(saveFile, 'wb')

    #recieve first piece
    data, addr = sock.recvfrom(561)
    recvData, recvPayload = struct.unpack('!IIII', data[:16]), data[16:]
    s_n = recvData[0]
    a_n = recvData[1]
    flags = recvData[2]
    bytesR = recvData[3]
    logging.info(f"RECV: Sequence: {s_n} Acknowlegment: {a_n} Flags: ACK: Y SYN: Y FIN: N")
    
    while(recvPayload):
        
        file.write(recvPayload)

        #send ack that packet was received
        send_data = createPacket(sequence_number = a_n, ack_number = s_n + bytesR , ack = 'Y', syn = 'N', fin = 'N', payload = b'')
        logging.info(f"SEND: Sequence: {a_n} Acknowlegment: {s_n + bytesR} Flags: ACK: Y SYN: N FIN: N")
        send_packet(sock, send_data, addr)

        #Receive next piece
        data, addr = sock.recvfrom(1024)
        recvData, recvPayload = struct.unpack('!IIII', data[:16]), data[16:]
        s_n = recvData[0]
        a_n = recvData[1]
        flags = recvData[2]
        bytesR = recvData[3]
        logging.info(f"RECV: Sequence: {s_n} Acknowlegment: {a_n} Flags: ACK: Y SYN: Y FIN: N")

        if(flags == 1):

            #send fin packet
            send_data = createPacket(sequence_number = a_n, ack_number = s_n + bytesR , ack = 'Y', syn = 'N', fin = 'Y', payload = b'')
            logging.info(f"SEND: Sequence: {a_n} Acknowlegment: {s_n + bytesR} Flags: ACK: Y SYN: N FIN: Y")
            sock.sendto(send_data, addr)

            #close socket and file
            sock.close()
            file.close()
            print("Downloaded file")
    return recvData




if __name__=='__main__':
    #parse arguments 
    server_ip, server_port, log_location, saveFile = get_args(sys.argv[1:])
    print("Server IP: {}, Port: {}, Log location: {}".format(server_ip, server_port, log_location))
    
    #logging configuration
    logging.basicConfig(filename=log_location, filemode='w', format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s', level=logging.INFO)
    logging.info(f'Starting ANONCLIENT')
    logging.info(f"Remote Server IP = {server_ip}, Remote Server Port = {server_port}, Logfile = {log_location}, saveFile = {saveFile}")
    
    #assign IP and port
    IP = server_ip
    port = server_port
    SERVER_ADDR = (IP, port)

    #create socket
    sock = socket(AF_INET, SOCK_DGRAM)
    
    send_data = createPacket(sequence_number = 12345, ack_number = 0, ack = 'N', syn = 'Y', fin = 'N', payload = b"Hello")
    send_packet(sock, send_data, SERVER_ADDR)

    data, addr = sock.recvfrom(1024)
    recvData, recvPayload = struct.unpack('!IIII', data[:16]), data[16:]
    recvPayload = recvPayload.decode()
    print(recvPayload)

    SERVER_ADDR = (recvPayload, port)
    #initiate handshake
    s_n, a_n, flags, payload = handshake(sock)

    #begin receiving file
    recvData = recvFile(sock, saveFile)


    








