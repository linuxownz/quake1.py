#server.py

from enum import Enum
from enum import Flag, auto

import gl_model
import progs
import net_defs
import protocol

class sendsignon_e(Enum):
    PRESPAWN_DONE = 0
    PRESPAWN_FLUSH = 1
    PRESPAWN_SIGNONBUFS = 2
    PRESPAWN_SIGNONMSG = 3

class client_t():
    def __init__(self):
        self.active = False
        self.spawned = False
        self.dropasap = False

        self.sendsignon : sendsignon_e = sendsignon_e.PRESPAWN_DONE
        self.signonidx = 0

        self.last_message = 0.0

        self.netconnection:net_defs.qsocket_t = None

        self.cmd : protocol.usercmd_t = None
        self.wishdir: list[float] = [0., 0., 0.]

        self.message = bytearray()
        self.msgbug = bytearray()

        raise NotImplementedError
        self.edict = 0
        self.edict_index = 0 # <<<<<<<<<<<<<< need this as edict is a pointer

        self.name = ''
        self.colors = 0

        self.ping_times = []
        self.num_pings = 0

        self.spawn_parms : list[float]= []

        self.old_frags = 0


class server_static_t():
    def __init__(self):
        self.maxclients = 0
        self.maxclientslimit = 0
        self.clients : list[client_t]= []
        self.serverflags = 0
        self.changelevel_issued = False


class server_state_t(Enum):
    ss_loading = 0
    ss_active  = 1

class server_t():
    def __init__(self):
        self.active = False
        self.paused = False
        self.loadgame = False
        self.nomonsters = False

        self.time:float = 0.0
        self.lastcheck = 0
        self.lastchecktime = 0
        self.name = ''
        self.modelname = ''

        self.worldmodel: gl_model.qmodel_t = None
        self.model_precache = ''
        self.models: list[gl_model.qmodel_t] = []

        self.sound_precache = ''
        self.lightstyles = ''

        self.num_edicts = 0
        self.max_edicts = 0

        self.edicts : list[progs.edict_t] = []

        self.state : server.server_state_t = server_state_t.ss_loading

        self.datagram = bytearray()
        self.datagram_buf = bytearray()

        self.signon: bytearray = bytearray()
        self.num_signon_buffers = 0
        self.signon_buffers : list[bytearray] = []

        self.protocol = 0
        self.protocolflags = 0




