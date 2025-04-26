import argparse
import socket
import sys
from utils import PacketHeader, compute_checksum

def parse_packet(packet_bytes):
    # TODO: split the packet into packet header and its message  
    pkt_header = PacketHeader(packet_bytes[:16])
    msg = packet_bytes[16:16 + pkt_header.length]

    return pkt_header, msg

def is_valid_checksum(pkt_header, msg):
    # TODO: whether the checksum is valid or not
    received_checksum = pkt_header.checksum
    pkt_header.checksum = 0
    return received_checksum == compute_checksum(pkt_header / msg)

def send_ack(s, seq_num, address):
    # TODO: send the acknowledge with a specific seq_num to the suitable address
    ack_header = PacketHeader(type=3, seq_num=seq_num, length=0, checksum=0)
    ack_header.checksum = compute_checksum(ack_header / b"")
    s.sendto(bytes(ack_header / b""), address)
    #print(f"==================================== Sending ACK with seq = {seq_num}")

def receiver(receiver_ip, receiver_port, window_size):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((receiver_ip, receiver_port))

    buffer = {}  # Buffer for out-of-order or in-order packets

    while True:
        packet, address = s.recvfrom(2048)
        pkt_header, msg = parse_packet(packet)

        if not is_valid_checksum(pkt_header, msg):
            #print(f"Checksum mismatch. Dropping packet with sequence {pkt_header.seq_num}")
            continue

        if pkt_header.type == 0:  # START packet
            #print("\nSTART packet was received.")
            send_ack(s, pkt_header.seq_num, address)

        elif pkt_header.type == 2:  # DATA packet

            if pkt_header.seq_num not in buffer:
                buffer[pkt_header.seq_num] = msg
                #print(f"Buffered packet with seq = {pkt_header.seq_num}")
            # Send ACK
            send_ack(s, pkt_header.seq_num, address)

        elif pkt_header.type == 1:  # END packet
            #print("END packet was received.")
            send_ack(s, pkt_header.seq_num, address)
            break

    # Output all collected data
    for seq_num in sorted(buffer):
        sys.stdout.buffer.write(buffer[seq_num])
    sys.stdout.flush()



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("receiver_ip", help="The IP address of the host that receiver is running on")
    parser.add_argument("receiver_port", type=int, help="The port number on which receiver is listening")
    parser.add_argument("window_size", type=int, help="Maximum number of outstanding packets")
    args = parser.parse_args()

    receiver(args.receiver_ip, args.receiver_port, args.window_size)

if __name__ == "__main__":
    main()