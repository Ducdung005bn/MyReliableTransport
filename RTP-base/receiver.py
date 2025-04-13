import argparse
import socket
import sys
from utils import PacketHeader, compute_checksum


def parse_packet(packet_bytes):
    pkt_header = PacketHeader(packet_bytes[:16])
    msg = packet_bytes[16:16 + pkt_header.length]
    return pkt_header, msg


def is_valid_checksum(pkt_header, msg):
    received_checksum = pkt_header.checksum
    pkt_header.checksum = 0
    return received_checksum == compute_checksum(pkt_header / msg)


def send_ack(s, seq_num, address):
    ack_header = PacketHeader(type=3, seq_num=seq_num, length=0, checksum=0)
    ack_header.checksum = compute_checksum(ack_header / b"")
    s.sendto(bytes(ack_header / b""), address)


def receiver(receiver_ip, receiver_port, window_size):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((receiver_ip, receiver_port))

    expected_seq = 0
    buffer = {}
    received_data = []
    connection_started = False

    while True:
        packet, address = s.recvfrom(2048)
        pkt_header, msg = parse_packet(packet)

        if not is_valid_checksum(pkt_header, msg):
            print("Checksum mismatch. Dropping packet.")
            continue

        if pkt_header.type == 0:  # START
            if not connection_started:
                print("START received.")
                connection_started = True
                send_ack(s, pkt_header.seq_num + 1, address)
            continue

        if not connection_started:
            print("Ignoring DATA before START.")
            continue

        if pkt_header.type == 2:  # DATA
            seq = pkt_header.seq_num
            if seq >= expected_seq + window_size:
                print(f"Packet {seq} out of window. Dropped.")
                continue

            if seq < expected_seq:
                send_ack(s, expected_seq, address)
                continue

            buffer[seq] = msg
            while expected_seq in buffer:
                received_data.append(buffer.pop(expected_seq))
                expected_seq += 1

            send_ack(s, expected_seq, address)

        elif pkt_header.type == 1:  # END
            print("END received. Sending final ACK.")
            send_ack(s, pkt_header.seq_num + 1, address)
            break

    # Output received data
    sys.stdout.buffer.write(b"".join(received_data))
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