#glquake.py

from enum import Enum

import gl_model
#import gl_texmgr
import quakedef

GL_UNUSED_TEXTURE     = ~0
ALIAS_BASE_SIZE_RATIO = ( 1.0 / 11.0 )
MAX_LBM_HEIGHT        = 480
TILE_SIZE             = 128
SKYSHIFT              = 7
SKYSIZE               = ( 1 << SKYSHIFT )
SKYMASK               = ( SKYSIZE - 1 )

BACKFACE_EPSILON      = 0.01
CONSOLE_RESPAM_TIME   = 3

class devstats_t:
    def __init__(self):
        self.packetsize = 0
        self.edicts     = 0
        self.visedicts  = 0
        self.efrags     = 0
        self.tempents   = 0
        self.beams      = 0
        self.dlights    = 0

class overflowtimes_t:
    def __init__(self):
        self.packetsize = 0.0
        self.efrags = 0.0
        self.beams  = 0.0
        self.varstring = 0.0


class surfcache_t:
    def __init__(self):
        self.next  : surfcache_t = None
        self.owner : surfcache_t = None

        self.lightadj = [0 for i in range(quakedef.MAXLIGHTMAPS)]
        self.dlight = 0
        self.size = 0
        self.width = 0
        self.height = 0
        self.mipscale = 0.0
        self.texture : gl_model.texture_t = None

        self.data = [ b'\x00' * 4]

class drawsurf_t:
    def __init__(self):
        self.surfdat = bytearray()
        self.rowbytes = 0
        self.surf : gl_model.msurface_t = None
        self.lightadj = [0 for i in range(bspfile.MAXLIGHTMAPS)]
        self.texture : gl_model.texture_t = None
        self.surfmip = 0
        self.surfwidth = 0
        self.surtheight = 0

class ptype_t(Enum):
    pt_static   = 0
    pt_grav     = 1
    pt_slowgrav = 2
    pt_fire     = 3
    pt_explode  = 4
    pt_explode2 = 5
    pt_blob     = 6
    pt_blob2    = 7


class particle_t:
    def __init__(self):
        self.org = [0, 0, 0]
        self.color = 0.0
        self.next : particle_t = None
        self.vel = [0, 0, 0]
        self.ramp = 0.0
        self.die = 0.0
        self.type : ptype_t = ptype_t.pt_static

OFFSET_BMODEL = 1
OFFSET_NONE   = 0
OFFSET_DECAL  = -1
OFFSET_FOG    = -2
OFFSET_SHOWTRIS = -3

GL_UNSIGNED_INT_10_10_10_2 = 0x8036

GL_COMBINE_EXT       = 0x8570
GL_COMBINE_RGB_EXT   = 0x8571
GL_COMBINE_ALPHA_EXT = 0x8572
GL_RGB_SCALE_EXT     = 0x8573
GL_CONSTANT_EXT      = 0x8576
GL_PRIMARY_COLOR_EXT = 0x8577
GL_PREVIOUS_EXT      = 0x8578
GL_SOURCE0_RGB_EXT   = 0x8580
GL_SOURCE1_RGB_EXT   = 0x8581
GL_SOURCE0_ALPHA_EXT = 0x8588
GL_SOURCE1_ALPHA_EXT = 0x8589

class devstats_t:
    def __init__(self):
        self.packetsize = 0
        self.edicts = 0
        self.videdicts = 0
        self.efrags = 0
        self.tempents = 0
        self.beams = 0
        self.dlights = 0

class overflowtimes_t:
    def __init__(self):
        self.packetsize = 0.0
        self.efrags = 0.0
        self.beams = 0.0
        self.varstring = 0.0

CONSOLE_RESPAM_TIME = 3

LMBLOCK_WIDTH  = 256
LMBLOCK_HEIGHT = 256

class glRect_t:
    def __init__(self):
        self.l = 0
        self.t = 0
        self.w = 0
        self.h = 0

class lightmap_s:
    def __init__(self):
        self.texture : gl_texmgr.gltexture_t = None
        self.polys   : gl_model.glpoly_t     = None
        self.modified = False
        self.rectchange : glRect_t = glRect_t()

        self.data : bytes = bytearray(4 * LMBLOCK_WIDTH * LMBLOCK_HEIGHT)

class glsl_attrib_binding_t:
    def __init__(self, name, attrib):
        self.name = name
        self.attrib = attrib