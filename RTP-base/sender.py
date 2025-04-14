import argparse
import socket
import struct
import sys

from utils import PacketHeader, compute_checksum

def split_message(message, max_packet_size):
     # TODO: Divide the message into chunks according to max_packet_size
    chunks = [message[i:i + max_packet_size] for i in range(0, len(message), max_packet_size)]
    return chunks

def create_packet(seq_num, data, packet_type):
    # TODO: Create packet
    if isinstance(data, str):
        data = data.encode()  #Convert data into bytes
    pkt_header = PacketHeader(type=packet_type, seq_num=seq_num, length=len(data))
    pkt_header.checksum = compute_checksum(pkt_header / data)
    return pkt_header / data #This helps combine package header and data to create a complete package

def wait_for_ack(socket, timeout=0.5):
    #TODO: Wait for the ACK from the receiver. If time's out, return None
    try:
        socket.settimeout(timeout)
        data, _ = socket.recvfrom(1024) #data: be received from socket; _: IP and port of the receiver
        ack_seq_num = struct.unpack("!I", data[:4])[0] #unpack data and use [0] to take ack_seq_num 
        return ack_seq_num
    except socket.timeout:
        print("Timeout waiting for ACK.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

    

def retransmit(s, window_start, window_end, chunks, seq_num, receiver_ip, receiver_port):
    for i in range(window_start, window_end):
        packet = create_packet(seq_num + i - window_start, chunks[i], packet_type=2)
        s.sendto(bytes(packet), (receiver_ip, receiver_port))
    print("Retransmitting due to timeout")

def send_control_packet(s, seq_num, receiver_ip, receiver_port, packet_type, data, label):
    """TODO: Send start/end message."""
    packet = create_packet(seq_num, data, packet_type=packet_type)
    s.sendto(bytes(packet), (receiver_ip, receiver_port))

    if label == "START":
        print(f"Sender sent {label} packet with seq =", seq_num)
        ack = wait_for_ack(s, timeout=None)  # Blocking wait
    else:
        print(f"Sender sent {label} packet with seq =", seq_num, "waiting for ACK (max 500ms)...")
        ack = wait_for_ack(s, timeout=0.5)

    if ack is not None:
        print(f"ACK received for {label} packet: {ack}")
    else:
        print(f"No ACK for {label} packet.")

def sender(receiver_ip, receiver_port, window_size):
    # TODO: Open socket to send message 
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # TODO: Send start packet
    send_control_packet(s, 0, receiver_ip, receiver_port, packet_type=0, data="START", label="START")

    # TODO: Enter the message to be sent
    if sys.stdin.isatty():
        message = input("Enter the message to send: ") # If it is entered from the command line
    else:
        message = sys.stdin.read() # If it is entered from a file
    max_packet_size = 1472  
    chunks = split_message(message, max_packet_size) # Split the message into chunks
    
    # TODO: initialize values 
    seq_num = 1 #because the seq_num for START packet is 0
    window_start = 0
    window_end = min(window_size, len(chunks)) # the maximum chunks to be sent

    while window_start < len(chunks):
        for i in range(window_start, window_end):
            packet = create_packet(seq_num + i - window_start, chunks[i], packet_type=2)
            s.sendto(bytes(packet), (receiver_ip, receiver_port))

        ack = wait_for_ack(s)
        if ack is None:
            retransmit(s, window_start, window_end, chunks, seq_num, receiver_ip, receiver_port)
        else:
            print(f"ACK was received with sequence number: {ack}")
            if ack >= seq_num:
                window_start = ack
                seq_num = ack
                window_end = min(window_start + window_size, len(chunks))

    send_control_packet(s, seq_num, receiver_ip, receiver_port, packet_type=1, data="END", label="END")
    s.close()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "receiver_ip", help="The IP address of the host that receiver is running on"
    )
    parser.add_argument(
        "receiver_port", type=int, help="The port number on which receiver is listening"
    )
    parser.add_argument(
        "window_size", type=int, help="Maximum number of outstanding packets"
    )
    args = parser.parse_args()

    sender(args.receiver_ip, args.receiver_port, args.window_size)

if __name__ == "__main__":
    main()  

