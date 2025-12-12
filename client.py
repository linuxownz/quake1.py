#client.py 

from enum import Enum
import io
import net_defs
import gl_model
import protocol

class lightstyle_t():
    def __init__(self):
        self.length = 0
        self.map = ''
        self.average = 0
        self.peak = 0

class scoreboard_t():
    def __init__(self):
        self.name = ''
        self.entertime = 0.0
        self.frags = 0
        self.colors = 0
        self.translations = []

class cshift_t():
    def __init__(self):
        self.destcolor = [0, 0, 0]
        self.percent = 0

CSHIFT_CONTENTS = 0
CSHIFT_DAMAGE   = 1
CSHIFT_BONUS    = 2
CSHIFT_POWERUP  = 3
NUM_CSHIFTS     = 4

NAME_LENGTH  =   64

SIGNONS = 4
MAX_DLIGHTS = 64

class dlight_t():
    def __init__(self):
        self.origin = [0, 0, 0]
        self.radius = 0
        self.die = 0
        self.decay = 0
        self.minlight = 0
        self.key = 0
        self.color = [0, 0, 0]

MAX_BEAMS = 32

class beam_t():
    def __init__(self):
        self.entity = 0
        self.model : gl_model.qmodel_t = None
        self.endtime = 0
        self.start = [0, 0, 0]
        self.end   = [0, 0, 0]

MAX_MAPSTRING = 2048
MAX_DEMOS     = 8
MAX_DEMONAME  = 16

class cactive_t(Enum):
    ca_dedicated = 0
    ca_disconnected = 1
    ca_connected = 2

class client_static_t():
    def __init__(self):
        self.state : cactive_t = cactive_t.ca_disconnected
        self.spawnparms = ''

        self.demonum = 0
        self.demos = []

        self.demorecording = False
        self.demoplayback = False
        self.demopaused = False

        self.timedemo = False
        self.forcetrack = 0
        self.demofile: io.FileIO = None
        
        self.td_lastframe  = 0
        self.td_startframe = 0
        self.td_starttime = 0.0

        self.signon = 0
        self.netcon: net_defs.qsocket_t = None

        self.message = bytearray()

class client_state_t():
    def __init__(self):
        self.movemessages = 0
        self.cmd : protocol.usercmd_t = None

        self.stats = []
        self.items = 0
        self.item_gettime = []
        self.faceanumtime = 0

        self.cshifts      : List[cshift_t] = []
        self.prev_cshifts : List[cshift_t] = []

        self.mviewangles  = [[0, 0, 0], [0, 0, 0]]
        self.viewangles   = []
        self.mvelocity    = [[0, 0, 0], [0, 0, 0]]
        self.velocity     = []

        self.punchangle   = []

        self.idealpitch = 0.0
        self.pitchvel = 0.0
        self.nodrift = False
        self.driftmove = 0.0
        self.laststop = 0.0

        self.viewheight = 0.0
        self.crouch = 0.0

        self.paused = False
        self.onground = False
        self.inwater = False

        self.intermission = 0
        self.completed_time = 0

        self.mtime = []
        self.time = 0.0

        self.oldtime = 0.0

        self.last_received_message = 0.0

        self.model_precache : List[gl_model.qmodel_t] = []
        self.sound_precache : List[q_sound.sfx_s]     = []

        self.mapname = ''
        self.levelname = ''
        self.viewentity = 0
        self.maxclients = 0
        self.gametype = 0

        self.worldmodel  : gl_model.qmodel_t = None
        self.free_efrags : render.efrags_t   = None

        self.num_efrags = 0
        self.num_entities = 0
        self.num_statics = 0

        self.viewent : unknown.entity_t = None

        self.cdtrack = 0
        self.looptrace = 0


        self.scores : scoreboard_t = None

        self.protocol = 0
        self.protocolflags = 0



