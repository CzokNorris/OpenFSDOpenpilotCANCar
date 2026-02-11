#!/bin/bash
# Launch script for CANabstractCAR with 125 kbps CAN bus speed

set -e

# Set CAN speed for panda
export CAN_SPEED_KBPS=125

echo "========================================"
echo "CANabstractCAR Launch Script"
echo "CAN Speed: ${CAN_SPEED_KBPS} kbps"
echo "========================================"

# Launch openpilot
exec ./launch_openpilot.sh "$@"
