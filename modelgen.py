#modelgen.py

from enum import Enum

ALIAS_VERSION = 6
ALIAS_ONSEAM = 0x0020
DT_FACES_FRONT = 0x0010

# Magic number: little-endian "IDPO" (0x4f504449)
IDPOLYHEADER = (ord('O') << 24) + (ord('P') << 16) + (ord('D') << 8) + ord('I')

class synctype_t(Enum):
    ST_SYNC = 0
    ST_RAND = 1

class aliasframetype_t(Enum):
    ALIAS_SINGLE = 0
    ALIAS_GROUP = 1

class aliasskintype_t(Enum):
    ALIAS_SKIN_SINGLE = 0
    ALIAS_SKIN_GROUP  = 1

class mdl_t():
    def __init__(self):
        self.ident = 0
        self.version = 0
        self.scale = [0, 0, 0]
        self.scale_origin = [0, 0, 0]
        self.boundingradius = 0.0
        self.eyeposition = [0, 0, 0]
        self.numskins = 0
        self.skinwidth = 0
        self.skinheight = 0
        self.numverts = 0
        self.numframes = 0
        self.synctype : synctype_t = synctype_t.ST_SYNC
        self.flags = 0
        self.size = 0.0

class stvert_t():
    def __init__(self):
        self.onseam = 0
        self.s = 0
        self.t = 0

class dtriangle_t():
    def __init__(self):
        self.facesfront = 0
        self.vertindex = [0, 0, 0]

class trivertx_t():
    def __init__(self):
        self.v = [0, 0, 0]
        self.lightnormalindex = 0

class daliasframe_t:
    def __init__(self):
        self.bboxmin = trivertx_t() # trivertx_t
        self.bboxmax = trivertx_t() # trivertx_t
        self.name = ""              # str (16 chars)

class daliasgroup_t:
    def __init__(self):
        self.numframes = 0          # int
        self.bboxmin = trivertx_t() # trivertx_t
        self.bboxmax = trivertx_t() # trivertx_t

class daliasskingroup_t:
    def __init__(self):
        self.numskins = 0           # int

class daliasinterval_t:
    def __init__(self):
        self.interval = 0.0         # float

class daliasskininterval_t:
    def __init__(self):
        self.interval = 0.0         # float

class daliasframetype_t:
    def __init__(self):
        self.type = 0               # aliasframetype_t (enum/int)

class daliasskintype_t:
    def __init__(self):
        self.type = 0               # aliasskintype_t (enum/int)