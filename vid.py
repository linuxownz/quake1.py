#vid.py 

from enum import Enum

VID_CBITS = 6
VID_GRADES = ( 1 << VID_CBITS )

GAMMA_MAX = 3.0

class modestate_t(Enum):
    MS_UNINIT     = 0
    MS_WINDOWED   = 1
    MS_FULLSCREEN = 2

# pixel_t : bytes = b'\x00'

class vrect_t:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.width = 0
        self.height = 0
        self.next = None

class viddef_t:
    def __init__(self):
        self.buffer : bytes = None
        self.colormap: bytes = None
        self.colormap16 = 0
        self.fullbright = 0
        self.rowbytes = 0
        self.width = 0
        self.height = 0
        self.aspect = 0.0
        self.numpages = 0
        self.recalc_refdef = False
        self.conbuffer : bytes = None
        self.conrowbytes = 0
        self.conwidth = 0
        self.conheight = 0
        self.maxwarpwidth = 0
        self.maxwarpheight = 0
        self.direct: bytes = None

