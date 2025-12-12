#gl_texmgr.py 

from enum import Enum
from enum import Flag, auto

import cvar
import common

TEXPREF_NONE       = 0x0000                                                    
TEXPREF_MIPMAP     = 0x0001  # generate mipmaps TEXPREF_NEAREST and TEXPREF_LINEAR aren't supposed to be ORed with TEX_MIPMAP
TEXPREF_LINEAR     = 0x0002  # force linear
TEXPREF_NEAREST    = 0x0004  # force nearest
TEXPREF_ALPHA      = 0x0008  # allow alpha
TEXPREF_PAD        = 0x0010  # allow padding
TEXPREF_PERSIST    = 0x0020  # never free
TEXPREF_OVERWRITE  = 0x0040  # overwrite existing same-name texture
TEXPREF_NOPICMIP   = 0x0080  # always load full-sized
TEXPREF_FULLBRIGHT = 0x0100  # use fullbright mask palette
TEXPREF_NOBRIGHT   = 0x0200  # use nobright mask palette
TEXPREF_CONCHARS   = 0x0400  # use conchars palette
TEXPREF_WARPIMAGE  = 0x0800  # resize this texture when warpimagesize changes

class srcformat(Enum):
    SRC_INDEXED         = 0, 
    SRC_LIGHTMAP        = 1, 
    SRC_RGBA            = 2, 
    SRC_INDEXED_PALETTE = 3

class gltexture_t():
    def __init__(self):
        self.texnum = 0
        #self.next : gltexture_t = None
        self.owner : qmodel = None

        self.name = ''
        self.width = 0
        self.height = 0
        self.flags = 0

        self.source_file = ''
        self.source_offset = 0
        self.source_format: srcformat = 0
        self.source_width = 0
        self.source_height = 0
        self.source_crc = 0
        self.shirt = 0
        self.pants = 0

        self.visframe = 0


gl_solid_format = 3
gl_alpha_format = 4

gl_texturemode =        {'name':"gl_texturemode",        'value':"",  'flags':cvar.CVAR_ARCHIVE};
gl_texture_anisotropy = {'name':"gl_texture_anisotropy", 'value':"1", 'flags':cvar.CVAR_ARCHIVE};
gl_max_size =           {'name':"gl_max_size",           'value':"0", 'flags':cvar.CVAR_NONE};
gl_picmip =             {'name':"gl_picmip",             'value':"0", 'flags':cvar.CVAR_NONE};
gl_hardware_maxsize = 0;

MAX_GLTEXTURES = 4096
numgltextures = 0

active_gltextures : List[gltexture_t] = []
free_gltextures   : List[gltexture_t] = []

notexture   : gltexture_t = None
nulltexture : gltexture_t = None

def TexMgr_LoadPalette():
    f = COM_FOpenFile('gfx/palette.lmp')

    if f is None:
        Sys_Error('couldnt load gfx/palette.lmp')

def TexMgr_Init():
    global free_gltextures
    global active_gltextures 

    active_gltextures = []

    notexture_data   = bytes([159,91,83,255,0,0,0,255,0,0,0,255,159,91,83,255])
    nulltexture_data = bytes([127,191,255,255,0,0,0,255,0,0,0,255,127,191,255,255])

    for i in range(MAX_GLTEXTURES):
        free_gltextures.append(gltexture_t())

    numgltextures = 0

    TexMgr_LoadPalette()
        
