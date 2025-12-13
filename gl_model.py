#gl_model.py 

from enum import Enum

import cvar
import _cmd
import console

EF_BRIGHTFIELD     = 1 
EF_MUZZLEFLASH     = 2
EF_BRIGHTLIGHT     = 4
EF_DIMLIGHT        = 8
EF_QEX_QUADLIGHT   = 16
EF_QEX_PENTALIGHT  = 32
EF_QEX_CANDLELIGHT = 64

class mvertex_t():
    def __init__(self, position):
        self.position : List[float] = position

SIDE_FRONT = 0
SIDE_BACK  = 1
SIDE_ON    = 2

class mplane_t():
    def __init__(self, normal, dist, _type, signbits):
        self.normal : List[float] = normal
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
                texturechains: List[msurface_s] = [], 
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
        self.texturechains = texturechains
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
SURF_NOTEXTURE      = 0x100 #johnfitz
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
        self.texture : texture_t = None

VERTEXSIZE = 7

class glpoly_t():
    def __init__(self):
        self.next  : glpoly_t = None
        self.chain : glpoly_t = None
        self.numverts = 0
        self.verts = [
            [0, 0, 0, 0, 0, 0, 0], 
            [0, 0, 0, 0, 0, 0, 0], 
            [0, 0, 0, 0, 0, 0, 0], 
            [0, 0, 0, 0, 0, 0, 0]
        ]

class msurface_t():
    def __init__(self):
        self.visframe = 0
        self.mins = [0, 0, 0]
        self.maxs = [0, 0, 0]

        self.plane : mplane_t = None
        self.flags = 0

        self.firstedge = 0
        self.numedges = 0

        self.texturemins = [0, 0]
        self.extents = [0, 0]

        self.light_s = 0
        self.light_t = 0

        self.polys : glpoly_t = None
        self.texturechain : msurface_t = None

        self.texinfo : mtexinfo_t = None
        self.vbo_firstvert = 0

        self.dlightframe = 0

        self.dlightbits = [] # client.MAX_DLIGHTS

class qmodel_t():
    def __init__(self):
        raise NotImplementedError
        pass

loadmodel : qmodel_t  = None
loadname = ''

mod_novis = None
mod_novis_capacity = 0

mod_decompressed = None
mod_decompressed_capacity = 0

MAX_MOD_KNOWN = 2048

mod_known : List[qmodel_t] = []
mod_unknown = 0

r_notexture_mip  : texture_t = None
r_notexture_mip2 : texture_t = None

def Mod_Print():
    console.Con_SafePrintf('Cached models\n')

    for i in range(mod_numknown):
        console.Con_SavePrintf(f'{mod_known.cache.data} : {mod}')

    console.Con_Printf(f'{mod_unknown} models')
    


def Mod_Init():
    global r_notexture_mip
    global r_notexture_mip2

    gl_subdivide_size = {'name': 'gl_subdivide_size', 'value': '128', 'flags': cvar.CVAR_ARCHIVE}
    external_ents     = {'name': 'external_ents',     'value': '1', 'flags': cvar.CVAR_ARCHIVE}
    external_vis      = {'name': 'external_vis',      'value': '1', 'flags': cvar.CVAR_ARCHIVE}
    external_textures = {'name': 'external_textures', 'value': '1', 'flags': cvar.CVAR_ARCHIVE}

    cvar.Cvar_RegisterVariable(gl_subdivide_size)
    cvar.Cvar_RegisterVariable(external_ents)
    cvar.Cvar_RegisterVariable(external_vis)
    cvar.Cvar_RegisterVariable(external_textures)

    _cmd.Cmd_AddCommand('mcache', Mod_Print)

    r_notexture_mip  = texture_t('notexture',  32, 32)
    r_notexture_mip2 = texture_t('notexture2', 32, 32)

