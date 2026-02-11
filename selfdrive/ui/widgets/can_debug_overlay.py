"""CAN Debug Overlay Widget for displaying raw CAN messages in the UI."""
import time
import pyray as rl
from collections import deque
from cereal import messaging
from openpilot.common.params import Params
from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.system.ui.widgets import Widget

# Configuration
MAX_MESSAGES = 20  # Maximum number of messages to display
MESSAGE_TIMEOUT = 2.0  # Seconds before a message is considered stale
OVERLAY_ALPHA = 128  # 50% transparency (0-255)
BACKGROUND_COLOR = rl.Color(0, 0, 0, OVERLAY_ALPHA)
TEXT_COLOR = rl.Color(255, 255, 255, 255)
STALE_TEXT_COLOR = rl.Color(150, 150, 150, 255)
ERROR_TEXT_COLOR = rl.Color(255, 100, 100, 255)
HEADER_COLOR = rl.Color(100, 200, 255, 255)
FONT_SIZE = 22
LINE_HEIGHT = 26
PADDING = 10


class CANMessage:
  """Represents a single CAN message with metadata."""
  def __init__(self, address: int, data: bytes, bus: int, timestamp: float):
    self.address = address
    self.data = data
    self.bus = bus
    self.timestamp = timestamp
    self.checksum_valid = True  # Will be set by caller if checksum validation is done

  def format_data(self) -> str:
    """Format the data bytes as hex string."""
    return ' '.join(f'{b:02X}' for b in self.data)

  def is_stale(self, current_time: float) -> bool:
    """Check if this message is stale (not received recently)."""
    return (current_time - self.timestamp) > MESSAGE_TIMEOUT


class CANDebugOverlay(Widget):
  """
  Overlay widget that displays raw CAN messages.
  Shows in the bottom-right corner when UI Debug Mode is active.
  """

  def __init__(self):
    super().__init__()
    self._params = Params()
    self._font = gui_app.font(FontWeight.MEDIUM)
    self._font_bold = gui_app.font(FontWeight.BOLD)

    # CAN message storage - keyed by (bus, address) for deduplication
    self._messages: dict[tuple[int, int], CANMessage] = {}
    self._message_order: deque[tuple[int, int]] = deque(maxlen=MAX_MESSAGES * 2)

    # CAN socket
    self._can_sock = None
    self._debug_enabled = False
    self._last_param_check = 0.0

  def _check_debug_enabled(self) -> bool:
    """Check if debug mode is enabled (cached check every 0.5s)."""
    current_time = time.monotonic()
    if current_time - self._last_param_check > 0.5:
      self._debug_enabled = self._params.get_bool("ShowDebugInfo")
      self._last_param_check = current_time

      # Initialize or cleanup CAN socket based on debug state
      if self._debug_enabled and self._can_sock is None:
        self._can_sock = messaging.sub_sock('can', conflate=True, timeout=0)
      elif not self._debug_enabled and self._can_sock is not None:
        self._can_sock = None
        self._messages.clear()
        self._message_order.clear()

    return self._debug_enabled

  def _update_messages(self):
    """Poll for new CAN messages and update the display list."""
    if self._can_sock is None:
      return

    # Non-blocking receive of CAN messages
    try:
      msgs = messaging.drain_sock(self._can_sock)
      current_time = time.monotonic()

      for msg in msgs:
        if msg.which() == 'can':
          for can_msg in msg.can:
            key = (can_msg.src, can_msg.address)

            # Update or add the message
            msg_data = bytes(can_msg.dat)
            self._messages[key] = CANMessage(
              address=can_msg.address,
              data=msg_data,
              bus=can_msg.src,
              timestamp=current_time
            )

            # Print to terminal for debugging
            data_hex = ' '.join(f'{b:02X}' for b in msg_data)
            print(f"[CAN] Bus:{can_msg.src} Addr:0x{can_msg.address:03X} Data:[{data_hex}]", flush=True)

            # Track message order for display
            if key in self._message_order:
              self._message_order.remove(key)
            self._message_order.append(key)

      # Remove stale messages
      stale_keys = [k for k, m in self._messages.items() if m.is_stale(current_time)]
      for key in stale_keys:
        del self._messages[key]
        if key in self._message_order:
          self._message_order.remove(key)

    except Exception:
      pass  # Silently handle any messaging errors

  def _render(self, rect: rl.Rectangle):
    """Render the CAN debug overlay."""
    if not self._check_debug_enabled():
      return

    # Update messages from CAN bus
    self._update_messages()

    # Debug: print message count periodically
    if len(self._messages) > 0:
      print(f"[CAN Overlay] Rendering {len(self._messages)} messages", flush=True)

    # Calculate overlay size (1/4 of screen, bottom-right)
    overlay_width = rect.width / 4
    overlay_height = rect.height / 4
    overlay_x = rect.x + rect.width - overlay_width - PADDING
    overlay_y = rect.y + rect.height - overlay_height - PADDING

    overlay_rect = rl.Rectangle(overlay_x, overlay_y, overlay_width, overlay_height)

    # Draw semi-transparent background
    rl.draw_rectangle_rec(overlay_rect, BACKGROUND_COLOR)
    rl.draw_rectangle_lines_ex(overlay_rect, 1, rl.Color(100, 100, 100, OVERLAY_ALPHA))

    # Draw header
    header_text = "CAN Debug"
    header_y = overlay_y + PADDING
    rl.draw_text_ex(self._font_bold, header_text, rl.Vector2(overlay_x + PADDING, header_y), FONT_SIZE, 0, HEADER_COLOR)

    # Draw column headers
    col_header_y = header_y + LINE_HEIGHT
    rl.draw_text_ex(self._font, "Bus  Addr     Data", rl.Vector2(overlay_x + PADDING, col_header_y), FONT_SIZE - 2, 0, HEADER_COLOR)

    # Draw messages
    current_time = time.monotonic()
    y_offset = col_header_y + LINE_HEIGHT
    max_y = overlay_y + overlay_height - PADDING

    # Get recent messages in order
    recent_keys = list(self._message_order)[-MAX_MESSAGES:]

    for key in reversed(recent_keys):
      if y_offset >= max_y:
        break

      if key not in self._messages:
        continue

      msg = self._messages[key]

      # Format the message line
      line = f"{msg.bus:2d}   0x{msg.address:03X}  {msg.format_data()}"

      # Choose color based on state
      if msg.is_stale(current_time):
        color = STALE_TEXT_COLOR
      elif not msg.checksum_valid:
        color = ERROR_TEXT_COLOR
      else:
        color = TEXT_COLOR

      # Draw the message
      rl.draw_text_ex(self._font, line, rl.Vector2(overlay_x + PADDING, y_offset), FONT_SIZE - 2, 0, color)
      y_offset += LINE_HEIGHT - 4

    # Draw message count
    count_text = f"Messages: {len(self._messages)}"
    rl.draw_text_ex(self._font, count_text, rl.Vector2(overlay_x + overlay_width - 120, header_y), FONT_SIZE - 4, 0, STALE_TEXT_COLOR)
