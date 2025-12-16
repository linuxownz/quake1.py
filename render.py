#render.py 

import protocol
import gl_model

MAXCLIPPLANES = 11

TOP_RANGE = 16
BOTTOM_RANGE = 96

class entity_t():
    def __init__(self):
        self.forcelink = False
        self.update_type = 0
        self.baseline : protocol.entity_state_t = protocol.entity_state_t()
        self.msgtime = 0.0
        self.msg_origins = [ [0, 0, 0], [0, 0, 0]]
        self.origin = [0, 0, 0]
        self.msg_angles = [ [0, 0, 0], [0, 0, 0]]
        self.angles = [0, 0, 0]
        self.model : gl_model.qmodel_t = None
        self.efrag : efrag_t = None # will this cause circular dep or undef
        self.frame = 0
        self.syncbase = 0.0
        self.colormap = bytearray()
        self.effects = 0
        self.skinnum = 0
        self.visframe = 0

        self.dlightframe = 0
        self.dlightbits  = 0

        self.topnode : gl_model.mnode_t = None
        self.alpha = 0
        self.scale = 0
        self.lerpflags = 0
        self.lerpstart = 0
        self.lerptime = 0
        self.lerpfinish = 0
        self.previouspose = 0
        self.currentpose = 0
        self.movelerpstart = 0
        self.previousorigin = [0, 0, 0]
        self.currentorigin = [0, 0, 0]
        self.previousangles = [0, 0, 0]
        self.currentangles = [0, 0, 0]
        







class efrag_t():
    def __init__(self):
        self.leafnext : efrag_t = None
        self.entity : entity_t = None

LERP_MOVESTEP   = ( 1 << 0 )
LERP_RESETANIM  = ( 1 << 1 )
LERP_RESETANIM2 = ( 1 << 2 )
LERP_RESETMOVE  = ( 1 << 3 )
LERP_FINISH     = ( 1 << 4 )

