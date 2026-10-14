#server.py

from enum import Enum

import common
import net_defs
import progs
import protocol
import quakedef

#import common

NUM_PING_TIMES = 16
NUM_SPAWN_PARMS = 16


MAX_SIGNON_BUFFERS = 256

MOVETYPE_NONE         = 0
MOVETYPE_ANGLENOCLIP  = 1
MOVETYPE_ANGLECLIP    = 2
MOVETYPE_WALK         = 3
MOVETYPE_STEP         = 4
MOVETYPE_FLY          = 5
MOVETYPE_TOSS         = 6
MOVETYPE_PUSH         = 7
MOVETYPE_NOCLIP       = 8
MOVETYPE_FLYMISSILE   = 9
MOVETYPE_BOUNCE       = 10
MOVETYPE_GIB          = 11

SOLID_NOT             = 0
SOLID_TRIGGER         = 1
SOLID_BBOX            = 2
SOLID_SLIDEBOX        = 3
SOLID_BSP             = 4

DEAD_NO               = 0
DEAD_DYING            = 1
DEAD_DEAD             = 2

DAMAGE_NO             = 0
DAMAGE_YES            = 1
DAMAGE_AIM            = 2

FL_FLY                = 1
FL_SWIM               = 2
FL_CONVEYOR           = 4
FL_CLIENT             = 8
FL_INWATER            = 16
FL_MONSTER            = 32
FL_GODMODE            = 64
FL_NOTARGET           = 128
FL_ITEM               = 256
FL_ONGROUND           = 512
FL_PARTIALGROUND      = 1024
FL_WATERJUMP          = 2048
FL_JUMPRELEASED       = 4096

EF_BRIGHTFIELD        = 1
EF_MUZZLEFLASH        = 2
EF_BRIGHTLIGHT        = 4
EF_DIMLIGHT           = 8

SPAWNFLAG_NOT_EASY        = 256
SPAWNFLAG_NOT_MEDIUM      = 512
SPAWNFLAG_NOT_HARD        = 1024
SPAWNFLAG_NOT_DEATHMATCH  = 2048

class sendsignon_e(Enum):
    PRESPAWN_DONE = 0
    PRESPAWN_FLUSH = 1
    PRESPAWN_SIGNONBUFS = 2
    PRESPAWN_SIGNONMSG = 3

class client_t:
    def __init__(self):
        self.active = False
        self.spawned = False
        self.dropasap = False

        self.sendsignon: sendsignon_e = sendsignon_e.PRESPAWN_DONE
        self.signonidx = 0

        self.last_message = 0.0

        self.netconnection: net_defs.qsocket_t = None

        self.cmd: protocol.usercmd_t = protocol.usercmd_t()
        self.wishdir: list[float] = [0.0, 0.0, 0.0]

        # Allocate message buffer for unreliable client commands
        self.msgbuf = bytearray(quakedef.MAX_MSGLEN)
        self.message = common.sizebuf_s()
        #common.SZ_Init(self.message, self.msgbuf, len(self.msgbuf))

        self.edict: progs.edict_t = None
        self.edict_index = 0

        self.name = ""
        self.colors = 0

        self.ping_times: list[float] = [0.0] * NUM_PING_TIMES
        self.num_pings = 0

        self.spawn_parms: list[float] = [0.0] * NUM_SPAWN_PARMS

        self.old_frags = 0
class server_static_t:
    def __init__(self):
        self.maxclients = 0
        self.maxclientslimit = 0
        self.clients : list[client_t] = []
        self.serverflags = 0
        self.changelevel_issued = False


class server_state_t(Enum):
    ss_loading = 0
    ss_active  = 1

class server_t:
    def __init__(self):
        #from common import  sizebuf_s
        import common
        self.active = False
        self.paused = False
        self.loadgame = False
        self.nomonsters = False

        self.time:float = 0.0
        self.lastcheck = 0
        self.lastchecktime = 0
        self.name = ''
        self.modelname = ''

        self.worldmodel: quakedef.qmodel_t = None
        self.model_precache : list[str] = ['' for i in range(quakedef.MAX_MODELS)]
        self.models: list[quakedef.qmodel_t] = [quakedef.qmodel_t for i in range (quakedef.MAX_MODELS)]

        self.sound_precache : list[str] = ['' for i in range(quakedef.MAX_SOUNDS)]
        self.lightstyles : list[str] = ['' for i in range(quakedef.MAX_LIGHTSTYLES)]

        self.num_edicts = 0
        self.max_edicts = 0

        self.edicts : list[progs.edict_t] = []

        self.state : server_state_t = server_state_t.ss_loading

        self.datagram : common.sizebuf_s = common.sizebuf_s()
        self.datagram_buf = bytearray(quakedef.MAX_DATAGRAM)

        self.reliable_datagram : common.sizebuf_s = common.sizebuf_s()
        self.reliable_datagram_buf = bytearray(quakedef.MAX_DATAGRAM)

        self.signon : common.sizebuf_s = common.sizebuf_s()
        self.num_signon_buffers = 0
        self.signon_buffers : list[common.sizebuf_s] = [common.sizebuf_s() for i in range(MAX_SIGNON_BUFFERS)]

        self.protocol = 0
        self.protocolflags = 0




