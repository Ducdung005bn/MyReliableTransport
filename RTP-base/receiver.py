import argparse
import socket
import sys
from utils import PacketHeader, compute_checksum

def parse_packet(packet_bytes):
    # TODO: split the packet into packet header and its message  
    pkt_header = PacketHeader(packet_bytes[:16])
    msg = packet_bytes[16:16 + pkt_header.length]

    print(f"Type: {pkt_header.type}")
    print(f"Message: {msg}")

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
    print(f"==================================== Sending ACK with seq = {seq_num}")

def receiver(receiver_ip, receiver_port, window_size):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((receiver_ip, receiver_port))

    expected_seq = 0
    buffer = {}  # Buffer for out-of-order packets
    received_data = []  # List for storing in-order received data

    while True:
        # Receive a packet (header and message) from the sender
        packet, address = s.recvfrom(2048) 
        pkt_header, msg = parse_packet(packet)
        seq = pkt_header.seq_num

        if not is_valid_checksum(pkt_header, msg):
            print("Checksum mismatch. Dropping packet.")
            continue

        if pkt_header.type == 0:  # START
            print("START packet was received.")
            expected_seq += 1
            send_ack(s, expected_seq, address)
            continue

        if pkt_header.type == 1:  # END
            print("END packet was received.")
            expected_seq += 1
            send_ack(s, expected_seq, address)

        # Check if the sequence number is out of the receiver's window
        if seq >= expected_seq + window_size:  # If packet is out of window, drop it
            print(f"Packet with seq = {seq} is out of window. Dropping packet.")
            continue  # Skip further processing for this packet

        # Buffer the packet if it's not already in the buffer
        if seq not in buffer:
            buffer[seq] = msg

        if seq == expected_seq + window_size - 1:
            consecutive_seq = expected_seq
            while consecutive_seq in buffer:  # Check if the next expected packet is in the buffer
                consecutive_seq += 1  # Keep moving forward while we have the next expected packet

            highest_seq = consecutive_seq - 1

            # If there is a consecutive sequence starting from expected_seq
            if highest_seq >= expected_seq:
                # Remove in-order packets from buffer and add them to the received_data list
                for seq_num in range(expected_seq, highest_seq + 1):
                    received_data.append(buffer.pop(seq_num))  

                # Send an ACK for the next expected sequence number
                expected_seq = highest_seq + 1
                send_ack(s, expected_seq, address)  


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("receiver_ip", help="The IP address of the host that receiver is running on")
    parser.add_argument("receiver_port", type=int, help="The port number on which receiver is listening")
    parser.add_argument("window_size", type=int, help="Maximum number of outstanding packets")
    args = parser.parse_args()

    receiver(args.receiver_ip, args.receiver_port, args.window_size)

if __name__ == "__main__":
    main()

