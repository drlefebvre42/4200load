import argparse
import socket
import struct
import threading
import sys
import logging
import time
import urllib.request, urllib.error, urllib.parse
ENCODING = 'utf-8'

def get_args(argv=None):
    #parse arguments and send to main function

    parser = argparse.ArgumentParser(description="ANONSERVER")
    parser.add_argument('-p', type=int, required=True, help='Port')
    parser.add_argument('-l', type=str, required=True, help='logFile')
    parser.add_argument('-w', type=str, required=True, help='website')
    args = parser.parse_args()
    log_file = args.l
    server_port = args.p
    website = args.w
    return server_port, log_file, website

def handshake(sock):
    #perform handshake with client

    #receive first packet
    data, addr = sock.recvfrom(1024)
    recvData, recvPayload = struct.unpack('!IIII', data[:16]), data[16:]
    logging.info(f"RECV: Sequence: {recvData[0]} Acknowlegment: {recvData[1]} Flags: ACK: N SYN: Y FIN: N")

    #send packet
    sendData = createPacket(sequence_number = 100, ack_number = recvData[0] + 1, ack = 'Y', syn = 'Y', fin = 'N', payload = b"")
    logging.info(f"SEND: Sequence: {100} Acknowlegment: {recvData[0] + 1} Flags: ACK: Y SYN: Y FIN: N")
    send_packet(sock, sendData, addr)

    #recieve second packet, handshake complete
    data, addr = sock.recvfrom(1024)
    recvData, recvPayload = struct.unpack('!IIII', data[:16]), data[16:]
    logging.info(f"RECV: Sequence: {recvData[0]} Acknowlegment: {recvData[1]} Flags: ACK: Y SYN: N FIN: N")
    print("Handshake Complete")
    logging.info(f"HANDSHAKE COMPLETE")

    return recvData[0], recvData[1], recvData[2], recvPayload, addr
    
    
    
def get_bit(num, i):
    #returns true if bit is 1, false if bit is 0

    return (num & (1 << i)) != 0

def print_bits(num):
    #prints number in 32 bit binary form

    print("{0:032b}".format(num))

def clear_bit(num, i):
    #sets selected bit to 0

    mask = ~(1 << i)
    return (num & mask)

def update_bit(num, i, bit):
    #updates selected bit based on user choice

    mask = ~(1 << i)
    return (num & mask) | (bit << i)

def createPacket(**kwargs):
    #creates packet to send to client

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
    data += struct.pack('!I', len(payload)) + payload
    
    return data

def send_packet(sock, data, server_addr):
    #sends packet to client

    sock.sendto(data, server_addr)

def downloadWebPage(webpage):
    #read contents of webpage and store in variable

    response = urllib.request.urlopen(webpage)
    webContent = response.read()
    
    return webContent

def sendFile(sock, s_n, a_n, flags, webContent, addr):
    #send file to client one piece at a time

    #open file we created in main function and send to client
    f = open('savedPage.html', 'rb')
    data = f.read(512)

    while(data):
        
        #send piece
        send_data = createPacket(sequence_number = a_n, ack_number = s_n + 1, ack = 'Y', syn = 'N', fin = "N", payload = data)
        if(sock.sendto(send_data, addr)):
            logging.info(f"SEND: Sequence: {a_n} Acknowlegment: {s_n + 1} Flags: ACK: Y SYN: N FIN: N")

            #receive acknowlegement that previous piece was received
            data, addr = sock.recvfrom(512)
            recvData, recvPayload = struct.unpack('!IIII', data[:16]), data[16:]
            s_n = recvData[0]
            a_n = recvData[1]
            flags = recvData[2]
            logging.info(f"RECV: Sequence: {recvData[0]} Acknowlegment: {recvData[1]} Flags: ACK: Y SYN: N FIN: N")
            data = f.read(512)

    print("Data Sent")
    #send fin packet to client
    send_data = createPacket(sequence_number = a_n, ack_number = s_n + 1, ack = 'N', syn = 'N', fin = 'Y', payload = b'')
    logging.info(f"SEND: Sequence: {a_n} Acknowlegment: {s_n + 1} Flags: ACK: N SYN: N FIN: Y")
    sock.sendto(send_data, addr)

    #receive fin packet from client
    data, addr = sock.recvfrom(512)
    recvData, recvPayload = struct.unpack('!IIII', data[:16]), data[16:]
    logging.info(f"RECV: Sequence: {recvData[0]} Acknowlegment: {recvData[1]} Flags: ACK: N SYN: N FIN: Y")
    flags = recvData[2]
    
    if(get_bit(flags, 0)):
        f.close()



    

if __name__=='__main__':
    #parse arguments, store into variables
    port, log_location, website = get_args(sys.argv[1:])
    print("Port: {}, Log location: {}, Website: {}".format(port, log_location, website))

    #logging configuration
    logging.basicConfig(filename=log_location, filemode='w', format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s', level=logging.INFO)
    logging.info("Starting ANONSERVER")
    logging.info(f"Server Port = {port}, Logfile = {log_location}, website = {website}")

    #store webpage into a file
    webpage = "http://" + website
    webContent = downloadWebPage(webpage)
    f = open('savedPage.html', 'wb')
    f.write(webContent)
    f.close()
    
    #grab host IP address
    IP = socket.gethostbyname(socket.gethostname())
    print(IP)
    SERVER_ADDR = (IP, port)

    #create and bind socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(SERVER_ADDR)

    while True:

        #perform handshake
        s_n, a_n, flags, payload, addr = handshake(sock)

        #Send the file to the client
        sendFile(sock, s_n, a_n, flags, webContent, addr)
