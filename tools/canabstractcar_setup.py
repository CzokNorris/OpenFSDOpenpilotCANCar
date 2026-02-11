#!/usr/bin/env python3
"""
CANabstractCAR Panda Setup Script

This script configures the panda CAN bus speed for CANabstractCAR.
Run this BEFORE launching openpilot when using CANabstractCAR.

Usage:
  python tools/canabstractcar_setup.py

The script will:
  1. Connect to the panda
  2. Set CAN bus 0 (CAN1) speed to 125 kbps
  3. Set safety mode to allOutput for testing
  4. Verify the configuration

NOTE: The panda speed setting may be reset when pandad starts.
For persistent 125kbps operation, you may need to modify pandad
or use a custom launch script.
"""

import sys
import time

try:
  from panda import Panda
except ImportError:
  print("Error: panda module not found. Make sure you're in the openpilot venv.")
  sys.exit(1)

try:
  from opendbc.car.structs import CarParams
except ImportError:
  CarParams = None

# Import the CAN speed from the car port
try:
  from opendbc.car.canabstractcar.values import CAN_SPEED_KBPS
except ImportError:
  CAN_SPEED_KBPS = 125  # Fallback value


def setup_canabstractcar():
  """Configure panda for CANabstractCAR (125 kbps CAN bus)."""
  print("CANabstractCAR Panda Setup")
  print("=" * 40)
  print(f"Target CAN speed: {CAN_SPEED_KBPS} kbps")
  print()

  # Find and connect to panda
  print("Searching for panda...")
  pandas = Panda.list()

  if not pandas:
    print("Error: No panda found! Make sure the panda is connected.")
    return False

  print(f"Found {len(pandas)} panda(s): {pandas}")

  for serial in pandas:
    print(f"\nConfiguring panda {serial}...")
    try:
      p = Panda(serial, claim=True, disable_checks=True)

      # Set CAN bus 0 (CAN1) to 125 kbps for CANabstractCAR
      print(f"  Setting CAN bus 0 to {CAN_SPEED_KBPS} kbps...")
      p.set_can_speed_kbps(0, CAN_SPEED_KBPS)

      # Also set bus 1 and 2 in case they're used
      print(f"  Setting CAN bus 1 to {CAN_SPEED_KBPS} kbps...")
      p.set_can_speed_kbps(1, CAN_SPEED_KBPS)
      print(f"  Setting CAN bus 2 to {CAN_SPEED_KBPS} kbps...")
      p.set_can_speed_kbps(2, CAN_SPEED_KBPS)

      # Set safety mode to allOutput for testing (allows all CAN messages)
      print("  Setting safety mode to allOutput for testing...")
      if CarParams:
        p.set_safety_mode(CarParams.SafetyModel.allOutput)
      else:
        p.set_safety_mode(17)  # SAFETY_ALLOUTPUT = 17

      # Give it a moment to apply
      time.sleep(0.1)

      # Verify by getting CAN health
      can_health = p.can_health()
      if can_health and len(can_health) > 0:
        for bus_idx, health in enumerate(can_health):
          reported_speed = health.get('can_speed', 'unknown')
          print(f"  CAN bus {bus_idx} speed reported: {reported_speed} kbps")

          if reported_speed == CAN_SPEED_KBPS:
            print(f"    ✓ Bus {bus_idx} configured correctly!")
          elif reported_speed == 'unknown':
            print(f"    ? Could not verify bus {bus_idx}")
          else:
            print(f"    ⚠ Warning: Expected {CAN_SPEED_KBPS} kbps but got {reported_speed} kbps")
      else:
        print("  ✓ CAN speed set (could not verify)")

      # Get current safety mode
      health = p.health()
      if health:
        safety_mode = health.get('safety_mode', 'unknown')
        print(f"  Safety mode: {safety_mode}")

      p.close()
      print(f"  ✓ Panda {serial} configured successfully")

    except Exception as e:
      print(f"  ✗ Error configuring panda {serial}: {e}")
      import traceback
      traceback.print_exc()
      return False

  print()
  print("=" * 40)
  print("Setup complete!")
  print()
  print("IMPORTANT: pandad may reset the CAN speed when it starts.")
  print("For testing, you can run this script in a loop:")
  print("  while true; do python tools/canabstractcar_setup.py; sleep 1; done")
  print()
  print("Or launch openpilot immediately after running this script.")
  return True


if __name__ == "__main__":
  success = setup_canabstractcar()
  sys.exit(0 if success else 1)
