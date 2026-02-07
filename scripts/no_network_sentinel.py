#!/usr/bin/env python3
import socket
import sys


def main() -> int:
    targets = [("1.1.1.1", 443), ("8.8.8.8", 53)]
    for host, port in targets:
        try:
            sock = socket.create_connection((host, port), timeout=1)
        except OSError:
            continue
        else:
            sock.close()
            print(f"Network connectivity detected to {host}:{port}")
            return 1
    print("No network connectivity detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
