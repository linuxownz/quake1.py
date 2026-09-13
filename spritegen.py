#spritegen.py

from enum import IntEnum


class Synctype(IntEnum):
    ST_SYNC = 0
    ST_RAND = 1

class AliasFrameType(IntEnum):
    ALIAS_SINGLE = 0
    ALIAS_GROUP = 1

class AliasSkinType(IntEnum):
    SKIN_SINGLE = 0
    SKIN_GROUP = 1

class SpriteType(IntEnum):
    VP_PARALLEL_UPRIGHT = 0
    FACING_UPRIGHT = 1
    VP_PARALLEL = 2
    ORIENTED = 3
    VP_PARALLEL_ORIENTED = 4

class SpriteFrameType(IntEnum):
    SPR_SINGLE = 0
    SPR_GROUP = 1
    SPR_ANGLED = 2

# Magic numbers
IDPOLYHEADER = (ord('O') << 24) + (ord('P') << 16) + (ord('D') << 8) + ord('I')
IDSPRITEHEADER = (ord('P') << 24) + (ord('S') << 16) + (ord('D') << 8) + ord('I')

class daliasframetype_t:
    def __init__(self):
        # Default to the Enum value
        self.type = AliasFrameType.ALIAS_SINGLE

class daliasskintype_t:
    def __init__(self):
        self.type = AliasSkinType.SKIN_SINGLE

class dsprite_t:
    def __init__(self):
        self.ident = IDSPRITEHEADER
        self.version = 1
        self.type = SpriteType.VP_PARALLEL
        self.boundingradius = 0.0
        self.width = 0
        self.height = 0
        self.numframes = 0
        self.beamlength = 0.0
        self.synctype = Synctype.ST_SYNC