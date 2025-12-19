#quakedef.py 
VERSION = 1.09
GLQUAKE_VERSION = 1.00
D3DQUAKE_VERSION = 0.01
WINQUAKE_VERSION = 0.996
LINUX_VERSION = 1.30
X11_VERSION = 1.10
FITZQUAKE_VERSION = 0.85  #johnfitz
QUAKESPASM_VERSION = 0.97
QUAKESPASM_VER_PATCH = 0  # helper to print a string like 0.94.7

#ifndef = QUAKESPASM_VER_SUFFIX
QUAKESPASM_VER_SUFFIX = 0  # optional version suffix string literal like "-beta1"
#endif

# combined version string like "0.92.1-beta1"
QUAKESPASM_VER_STRING = str(QUAKESPASM_VERSION)  + "." + str(QUAKESPASM_VER_PATCH)  + ' ' + str(QUAKESPASM_VER_SUFFIX)
GAMENAME = "id1"  # directory to look in by default
BSP29_VALVE = 0  # enable Half-Life map support
# !!! if this is changed, it must be changed in d_ifacea.h too !!!
CACHE_SIZE = 32  # used to align key data structures
MINIMUM_MEMORY = 0x550000
MINIMUM_MEMORY_LEVELPAK = (MINIMUM_MEMORY + 0x100000)
MAX_NUM_ARGVS = 50

# up / down
PITCH = 0
# left / right
YAW = 1
# fall over

ROLL = 2
MAX_QPATH = 64  # max length of a quake game pathname
ON_EPSILON = 0.1  # point on plane side epsilon
DIST_EPSILON = (0.03125)  # 1/32 epsilon to keep floating point happy (moved from world.c)
MAX_MSGLEN = 64000  # max length of a reliable message //ericw -- was 32000
MAX_DATAGRAM = 64000  # max length of unreliable message //johnfitz -- was 1024
DATAGRAM_MTU = 1400  # johnfitz -- actual limit for unreliable messages to nonlocal clients

#
# per-level limits
#
MIN_EDICTS = 256  # johnfitz -- lowest allowed value for max_edicts cvar
MAX_EDICTS = 32000  # johnfitz -- highest allowed value for max_edicts cvar

# ents past 8192 can't play sounds in the standard protocol
MAX_LIGHTSTYLES = 64
MAX_MODELS = 2048  # johnfitz -- was 256
MAX_SOUNDS = 2048  # johnfitz -- was 256
SAVEGAME_COMMENT_LENGTH = 39
MAX_STYLESTRING = 64

#
# stats are integers communicated to the client by the server
#
MAX_CL_STATS = 32
STAT_HEALTH = 0
STAT_FRAGS = 1
STAT_WEAPON = 2
STAT_AMMO = 3
STAT_ARMOR = 4
STAT_WEAPONFRAME = 5
STAT_SHELLS = 6
STAT_NAILS = 7
STAT_ROCKETS = 8
STAT_CELLS = 9
STAT_ACTIVEWEAPON = 10
STAT_TOTALSECRETS = 11
STAT_TOTALMONSTERS = 12
STAT_SECRETS = 13  # bumped on client side by svc_foundsecret
STAT_MONSTERS = 14  # bumped by svc_killedmonster
# stock defines
#
IT_SHOTGUN = 1
IT_SUPER_SHOTGUN = 2
IT_NAILGUN = 4
IT_SUPER_NAILGUN = 8
IT_GRENADE_LAUNCHER = 16
IT_ROCKET_LAUNCHER = 32
IT_LIGHTNING = 64
IT_SUPER_LIGHTNING = 128
IT_SHELLS = 256
IT_NAILS = 512
IT_ROCKETS = 1024
IT_CELLS = 2048
IT_AXE = 4096
IT_ARMOR1 = 8192
IT_ARMOR2 = 16384
IT_ARMOR3 = 32768
IT_SUPERHEALTH = 65536
IT_KEY1 = 131072
IT_KEY2 = 262144
IT_INVISIBILITY = 524288
IT_INVULNERABILITY = 1048576
IT_SUIT = 2097152
IT_QUAD = 4194304
IT_SIGIL1 = (1<<28)
IT_SIGIL2 = (1<<29)
IT_SIGIL3 = (1<<30)
IT_SIGIL4 = (1<<31)
#===========================================
#rogue changed and added defines
RIT_SHELLS = 128
RIT_NAILS = 256
RIT_ROCKETS = 512
RIT_CELLS = 1024
RIT_AXE = 2048
RIT_LAVA_NAILGUN = 4096
RIT_LAVA_SUPER_NAILGUN = 8192
RIT_MULTI_GRENADE = 16384
RIT_MULTI_ROCKET = 32768
RIT_PLASMA_GUN = 65536
RIT_ARMOR1 = 8388608
RIT_ARMOR2 = 16777216
RIT_ARMOR3 = 33554432
RIT_LAVA_NAILS = 67108864
RIT_PLASMA_AMMO = 134217728
RIT_MULTI_ROCKETS = 268435456
RIT_SHIELD = 536870912
RIT_ANTIGRAV = 1073741824
RIT_SUPERHEALTH = 2147483648
#MED 01/04/97 added hipnotic defines
#===========================================
#hipnotic added defines
HIT_PROXIMITY_GUN_BIT = 16
HIT_MJOLNIR_BIT = 7
HIT_LASER_CANNON_BIT = 23
HIT_PROXIMITY_GUN = (1<<HIT_PROXIMITY_GUN_BIT)
HIT_MJOLNIR = (1<<HIT_MJOLNIR_BIT)
HIT_LASER_CANNON = (1<<HIT_LASER_CANNON_BIT)
HIT_WETSUIT = (1<<(23+2))
HIT_EMPATHY_SHIELDS = (1<<(23+3))
#===========================================
MAX_SCOREBOARD = 16
MAX_SCOREBOARDNAME = 32
SOUND_CHANNELS = 8

class quakeparms_t():
    def __init__(self):
        self.basedir = ''
        self.userdir = ''
        self.argc = 0
        self.argv = []
        #self.membase = 0
        #self.memsize = 0
        #self.numcpus = 1
        self.errstate = 0

# start of every frame, never reset
class filelist_item_t():
    def __init__(self):
        self.name = ''
        self.path_id = 0
        self.next : filelist_item_t = None

