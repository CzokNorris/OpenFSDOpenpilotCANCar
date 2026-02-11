#!/usr/bin/env python3
"""Test script to send CAN messages through the cereal messaging system."""
import time
import argparse
from cereal import messaging


def send_can_message(address: int, data: bytes, bus: int = 0):
  """Send a single CAN message through cereal messaging."""
  pm = messaging.PubMaster(['can'])

  # Create the CAN message
  can_msg = messaging.new_message('can', 1)
  can_msg.can[0].address = address
  can_msg.can[0].dat = data
  can_msg.can[0].src = bus

  pm.send('can', can_msg)
  print(f"Sent: Bus:{bus} Addr:0x{address:03X} Data:[{' '.join(f'{b:02X}' for b in data)}]")


def main():
  parser = argparse.ArgumentParser(description='Send CAN messages through cereal')
  parser.add_argument('message', nargs='?', default='123#1122334455667788',
                      help='CAN message in format ADDR#DATA (hex), e.g., 123#1122334455667788')
  parser.add_argument('--bus', '-b', type=int, default=0, help='CAN bus number (default: 0)')
  parser.add_argument('--loop', '-l', action='store_true', help='Send continuously at 10Hz')
  args = parser.parse_args()

  # Parse the message
  try:
    addr_str, data_str = args.message.split('#')
    address = int(addr_str, 16)
    data = bytes.fromhex(data_str)
  except ValueError as e:
    print(f"Error parsing message: {e}")
    print("Format: ADDR#DATA (hex), e.g., 123#1122334455667788")
    return 1

  print(f"Sending CAN message to bus {args.bus}...")

  if args.loop:
    print("Press Ctrl+C to stop")
    try:
      while True:
        send_can_message(address, data, args.bus)
        time.sleep(0.1)  # 10Hz
    except KeyboardInterrupt:
      print("\nStopped")
  else:
    send_can_message(address, data, args.bus)

  return 0


if __name__ == '__main__':
  exit(main())
