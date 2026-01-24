#quakedef.py

from enum import Enum
from dataclasses import dataclass, field

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

# bspfile CONTENTS_SOLID = -2

LMBLOCK_WIDTH = 128
LMBLOCK_HEIGHT = 128

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

# --- Constants ---
EF_BRIGHTFIELD     = 1
EF_MUZZLEFLASH     = 2
EF_BRIGHTLIGHT     = 4
EF_DIMLIGHT        = 8
EF_QEX_QUADLIGHT   = 16
EF_QEX_PENTALIGHT  = 32
EF_QEX_CANDLELIGHT = 64


# --- Classes ---

class dmodel_t:
    def __init__(self):
        self.mins = [0,0,0]
        self.maxs = [0,0,0]
        self.origin = [0,0,0]
        self.headnode = [0,0,0,0]
        self.visleafs = 0
        self.firstface = 0
        self.numfaces = 0

class mvertex_t():
    def __init__(self, position):
        self.position : list[float] = position

SIDE_FRONT = 0
SIDE_BACK  = 1
SIDE_ON    = 2

class mplane_t():
    def __init__(self, normal, dist, _type, signbits):
        self.normal : list[float] = normal
        self.dist = dist
        self.type = _type
        self.signbits = signbits
        self.pad = b'\x00\x00'
        self.unpack_string = '<3f f B B 2B'

class texchain_t(Enum):
    chain_world = 0
    chain_model = 1

class texture_t():
    def __init__(self, name, width, height, shift = 0,
                gltexture = None, fullbright = None,
                warpimage = None, update_warp = False,
                texturechains: list['msurface_t'] = None, # Use string for forward ref
                anim_total = 0, anim_min = 0, anim_max = 0,
                anim_next = None, alternate_anims = None):
        self.name = name
        self.width = width
        self.height = height
        self.shift = shift
        self.gltexture = gltexture
        self.fullbright = fullbright
        self.warpimage = warpimage
        self.update_warp = update_warp
        self.texturechains = texturechains if texturechains is not None else []
        self.anim_total = anim_total
        self.anim_min = anim_min
        self.anim_max = anim_max
        self.anim_next = anim_next
        self.alternate_anims = alternate_anims

SURF_PLANEBACK      = 2
SURF_DRAWSKY        = 4
SURF_DRAWSPRITE     = 8
SURF_DRAWTURB       = 0x10
SURF_DRAWTILED      = 0x20
SURF_DRAWBACKGROUND = 0x40
SURF_UNDERWATER     = 0x80
SURF_NOTEXTURE      = 0x100
SURF_DRAWFENCE      = 0x200
SURF_DRAWLAVA       = 0x400
SURF_DRAWSLIME      = 0x800
SURF_DRAWTELE       = 0x1000
SURF_DRAWWATER      = 0x2000

class medge_t():
    def __init__(self):
        self.v = []
        self.cachededgeoffset = 0

class mtexinfo_t():
    def __init__(self):
        self.vecs = [[0., 0., 0., 0.], [0., 0., 0., 0.]]
        self.texture : Optional[texture_t] = None
        self.flags = 0

VERTEXSIZE = 7

class glpoly_t():
    def __init__(self):
        self.next  : Optional['glpoly_t'] = None
        self.chain : Optional['glpoly_t'] = None
        self.numverts = 0
        self.verts = [] # Initialize empty, built in GL_BuildPolygon

class msurface_t():
    def __init__(self):
        self.visframe = 0
        self.mins = [0, 0, 0]
        self.maxs = [0, 0, 0]
        self.plane : Optional[mplane_t] = None
        self.flags = 0
        self.firstedge = 0
        self.numedges = 0
        self.texturemins = [0, 0]
        self.extents = [0, 0]
        self.light_s = 0
        self.light_t = 0
        self.polys : Optional[glpoly_t] = None
        self.texturechain : Optional['msurface_t'] = None
        self.texinfo : Optional[mtexinfo_t] = None
        self.styles = [0, 0, 0, 0]
        self.lightofs = -1
        self.lightmap_texture = 0

class mnode_t():
    def __init__(self):
        self.contents = 0             # 0 or greater for nodes
        self.parent = None            # Set by Mod_SetParent
        self.plane = None             # Pointer to mplane_t
        self.children = [None, None]  # Set to Node or Leaf objects by Mod_SetParent
        self.mins = [0, 0, 0]
        self.maxs = [0, 0, 0]
        self.firstface = 0
        self.numfaces = 0

class mleaf_t():
    def __init__(self):
        self.contents = -1            # Negative for leaves (e.g., CONTENTS_SOLID)
        self.parent = None            # Set by Mod_SetParent
        self.mins = [0, 0, 0]
        self.maxs = [0, 0, 0]
        self.firstmarksurface = 0
        self.nummarksurface = 0
        self.visofs = 0               # Offset into visdata for PVS
        self.ambient_sound_levels = [0, 0, 0, 0]


class qmodel_t:
    def __init__(self):
        # General model info
        self.name = ""            # The filename (e.g., "maps/e1m1.bsp")
        self.type = 0               # modtype_t: mod_brush (0), mod_sprite (1), mod_alias (2)
        self.numframes = 0
        self.flags = 0

        # Bounding box for Culling
        self.mins = [0.0, 0.0, 0.0]
        self.maxs = [0.0, 0.0, 0.0]
        self.radius = 0.0

        # --- Brush (BSP) Specific Data ---
        # These correspond to the Lumps in the BSP file
        self.planes = []          # List of dplane_t
        self.leafs = []           # List of dleaf_t
        self.nodes = []           # List of dnode_t
        self.clipnodes = []       # List of dclipnode_t
        self.vertexes = []        # List of mvertex_t (x, y, z)
        self.faces = []           # List of msurface_t
        self.textures = []        # List of texture_t (mipmaps)
        self.texinfo = []         # List of mtexinfo_t
        self.edges = []           # List of medge_t
        self.surfedges = []       # List of int (indices into edges)

        # Counters for the above
        self.numplanes = 0
        self.numleafs = 0
        self.numnodes = 0
        self.numclipnodes = 0
        self.numvertexes = 0
        self.numfaces = 0
        self.numtextures = 0
        self.numtexinfo = 0
        self.numedges = 0
        self.numsurfedges = 0

        # Visibility and Lighting
        self.visdata = None       # The decompressed PVS (Potentially Visible Set)
        self.lightdata = None     # The raw lightmap data

        # Submodels (used for moving parts like doors/elevators)
        self.submodels = []       # List of dmodel_t
        self.numsubmodels = 0

        # Sync/Loading metadata
        self.needload = False     # For async loading if implemented
        self.submodels = []       # List of dmodel_t (Submodel info)
        self.numsubmodels = 0


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
    def __init__(self, destcolor, percent):
        self.destcolor = destcolor
        self.percent = percent

CSHIFT_CONTENTS = 0
CSHIFT_DAMAGE   = 1
CSHIFT_BONUS    = 2
CSHIFT_POWERUP  = 3
NUM_CSHIFTS     = 4

NAME_LENGTH  =   64

SIGNONS = 4
MAX_DLIGHTS = 64

MAX_TEMP_ENTITIES   = 256     #johnfitz -- was 64
MAX_STATIC_ENTITIES = 4096    #ericw -- was 512  #johnfitz -- was 128
MAX_VISEDICTS       = 4096    # larger, now we support BSP2



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
        self.netcon: qsocket_t = None

        self.message = bytearray()

class client_state_t():
    def __init__(self):
        self.movemessages = 0
        self.cmd : protocol.usercmd_t = None

        self.stats = []
        self.items = 0
        self.item_gettime = []
        self.faceanumtime = 0

        self.cshifts      : list[cshift_t] = []
        self.prev_cshifts : list[cshift_t] = []

        self.mviewangles  = [[0, 0, 0], [0, 0, 0]]
        self.viewangles   = [0, 0, 0]
        self.mvelocity    = [[0, 0, 0], [0, 0, 0]]
        self.velocity     = [0, 0, 0]

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

        self.model_precache : list[qmodel_t] = []
        self.sound_precache : list[sfx_s]    = []

        self.mapname = ''
        self.levelname = ''
        self.viewentity = 0
        self.maxclients = 0
        self.gametype = 0

        self.worldmodel  : qmodel_t = None
        self.free_efrags : efrags_t   = None

        self.num_efrags = 0
        self.num_entities = 0
        self.num_statics = 0

        self.viewent : entity_t = None

        self.cdtrack = 0
        self.looptrace = 0


        self.scores : scoreboard_t = None

        self.protocol = 0
        self.protocolflags = 0

class modtype_t(Enum):
    mod_brush = 0
    mod_sprite = 1
    mod_alias = 2


# quakedef.py

@dataclass
class vrect_t:
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0

class refdef_t:
    def __init__(self):
        # Subwindow in video for refresh
        self.vrect = vrect_t()
        self.aliasvrect = vrect_t()

        # Right & bottom screen coords
        self.vrectright = 0
        self.vrectbottom = 0
        self.aliasvrectright = 0
        self.aliasvrectbottom = 0

        # Floating-point boundaries for clamping and edge lists
        self.vrectrightedge = 0.0
        self.fvrectx = 0.0
        self.fvrecty = 0.0
        self.fvrectx_adj = 0.0
        self.fvrecty_adj = 0.0

        # Fixed-point shifted values (Original Quake software optimization)
        # Note: In Python, we might not need these for an OpenGL renderer,
        # but they are kept here for structural parity.
        self.vrect_x_adj_shift20 = 0
        self.vrectright_adj_shift20 = 0

        self.fvrectright_adj = 0.0
        self.fvrectbottom_adj = 0.0
        self.fvrectright = 0.0
        self.fvrectbottom = 0.0

        # Field of View
        # 2.0 = 90 degrees
        self.horizontalFieldOfView = 2.0
        self.xOrigin = 0.5
        self.yOrigin = 0.5

        # Camera Position and Orientation
        self.vieworg = [0.0, 0.0, 0.0]     # vec3_t (x, y, z)
        self.viewangles = [0.0, 0.0, 0.0]  # vec3_t (pitch, yaw, roll)

        self.fov_x = 0.0
        self.fov_y = 0.0

        self.ambientlight = 0
