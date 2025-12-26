#client.py

from enum import Enum

class kbutton_t:
    def __init__(self):
        self.state = 0  # bit 0 = down, bit 1 = stayed down

# Global button instances
in_forward = kbutton_t()
in_back    = kbutton_t()

in_strafe_left  = kbutton_t() # Was 'in_left'
in_strafe_right = kbutton_t() # Was 'in_right'

# Rotation buttons
in_turn_left    = kbutton_t()
in_turn_right   = kbutton_t()
in_pitch_up     = kbutton_t()
in_pitch_down   = kbutton_t()