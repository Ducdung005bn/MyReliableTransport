import argparse
import socket
import struct

from utils import PacketHeader, compute_checksum


    #TODO: Divide the message into chunks according to max_packet_size.
def split_message(message, max_packet_size):
    chunks = [message[i:i + max_packet_size] for i in range(0, len(message), max_packet_size)]
    return chunks


    #TODO: Create packet
def create_packet(seq_num, data, packet_type):
    if isinstance(data, str):
        data = data.encode()
    pkt_header = PacketHeader(type=packet_type, seq_num=seq_num, length=len(data))
    pkt_header.checksum = compute_checksum(pkt_header / data)
    return pkt_header / data


    #TODO: Wait for the ACK from the receiver. If time's out, return None. 
def wait_for_ack(socket, timeout=0.5):
    try:
        socket.settimeout(timeout)
        data, _ = socket.recvfrom(1024) #data: be received from socket; _: IP and port of the receiver
        ack_seq_num = struct.unpack("!I", data[:4])[0] #unpack data and use [0] to take ack_seq_num 
        return ack_seq_num
    except socket.timeout:
        return None
    

    #TODO: Retransmit when timeout happens.
def retransmit(s, window_start, window_end, chunks, seq_num, receiver_ip, receiver_port):
    for i in range(window_start, window_end):
        packet = create_packet(seq_num + i - window_start, chunks[i], packet_type=2)
        s.sendto(bytes(packet), (receiver_ip, receiver_port))
        seq_num += 1
    print("Retransmitting due to timeout")


    #TODO: Send start/end message.
def send_control_packet(s, seq_num, receiver_ip, receiver_port, packet_type, data, label):
    packet = create_packet(seq_num, data, packet_type=packet_type)
    s.sendto(bytes(packet), (receiver_ip, receiver_port))

    if label == "START":
        print(f"Sent {label} packet (ACK optional).")
        ack = wait_for_ack(s, timeout=None)  # Blocking wait
    else:
        print(f"Sent {label} packet, waiting for ACK (max 500ms)...")
        ack = wait_for_ack(s, timeout=0.5)

    if ack is not None:
        print(f"ACK received for {label} packet: {ack}")
    else:
        print(f"No ACK for {label} packet.")


    #TODO: Open socket and send message from sys.stdin.
def sender(receiver_ip, receiver_port, window_size):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    send_control_packet(s, 0, receiver_ip, receiver_port, packet_type=0, data="START", label="START")

    message = input("Enter the message to send: ")
    max_packet_size = 1472  
    chunks = split_message(message, max_packet_size)
    
    seq_num = 1 #because the seq_num for START packet is 0
    window_start = 0
    window_end = min(window_size, len(chunks)) #window_size: the maximum chunks to be sent

    while window_start < len(chunks):
        for i in range(window_start, window_end):
            packet = create_packet(seq_num + i - window_start, chunks[i], packet_type=2)
            s.sendto(bytes(packet), (receiver_ip, receiver_port))

        ack = wait_for_ack(s)
        if ack is None:
            retransmit(s, window_start, window_end, chunks, seq_num, receiver_ip, receiver_port)
        else:
            print(f"ACK received for packet {ack}")
            # Sliding window
            while window_start < len(chunks) and ack >= seq_num:
                window_start += 1
                seq_num += 1
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