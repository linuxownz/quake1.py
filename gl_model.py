# gl_model.py

from enum import Enum
from typing import Optional # Required for Optional type hints


import sys_sdl_unix

# --- Constants ---
EF_BRIGHTFIELD     = 1
EF_MUZZLEFLASH     = 2
EF_BRIGHTLIGHT     = 4
EF_DIMLIGHT        = 8
EF_QEX_QUADLIGHT   = 16
EF_QEX_PENTALIGHT  = 32
EF_QEX_CANDLELIGHT = 64


# --- Classes ---
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
        self.lightofs = -1 # Added this to match bspfile.py
        self.lightmap_texture = 0 # GPU handle for lightmap

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


MAX_MOD_KNOWN = 2048
mod_known : list[qmodel_t] = [None] * MAX_MOD_KNOWN
mod_numknown = 0

r_notexture_mip = None
r_notexture_mip2 = None


# --- Verbs ---

def GL_BuildPolygon(model, face):
    tex = face.texinfo
    poly = glpoly_t()

    verts = []
    mins = [99999, 99999]
    maxs = [-99999, -99999]

    # 1. Gather verts and find texture boundaries
    for i in range(face.numedges):
        e_idx = model.surfedges[face.firstedge + i]
        v_idx = model.edges[e_idx].v[0] if e_idx >= 0 else model.edges[-e_idx].v[1]
        v = model.vertexes[v_idx].position
        verts.append(v)

        for j in range(2):
            val = (v[0] * tex.vecs[j][0] + v[1] * tex.vecs[j][1] +
                   v[2] * tex.vecs[j][2] + tex.vecs[j][3])
            if val < mins[j]: mins[j] = val
            if val > maxs[j]: maxs[j] = val

    # 2. Store lightmap extents
    face.texturemins = [int(mins[0] // 16), int(mins[1] // 16)]
    face.extents = [int(maxs[0] // 16) - int(mins[0] // 16),
                    int(maxs[1] // 16) - int(mins[1] // 16)]

    # 3. Build 7-float vertex array [x, y, z, s1, t1, s2, t2]
    poly.numverts = len(verts)
    for v in verts:
        # Texture coordinates
        s1 = (v[0] * tex.vecs[0][0] + v[1] * tex.vecs[0][1] +
              v[2] * tex.vecs[0][2] + tex.vecs[0][3]) / tex.texture.width
        t1 = (v[0] * tex.vecs[1][0] + v[1] * tex.vecs[1][1] +
              v[2] * tex.vecs[1][2] + tex.vecs[1][3]) / tex.texture.height

        # Lightmap coordinates (Normalized 0.0 to 1.0 for the patch texture)
        s2 = (v[0] * tex.vecs[0][0] + v[1] * tex.vecs[0][1] +
              v[2] * tex.vecs[0][2] + tex.vecs[0][3])
        s2 = (s2 - face.texturemins[0] * 16 + 8) / ((face.extents[0] + 1) * 16)

        t2 = (v[0] * tex.vecs[1][0] + v[1] * tex.vecs[1][1] +
              v[2] * tex.vecs[1][2] + tex.vecs[1][3])
        t2 = (t2 - face.texturemins[1] * 16 + 8) / ((face.extents[1] + 1) * 16)

        poly.verts.append([v[0], v[1], v[2], s1, t1, s2, t2])

    face.polys = poly

def Mod_SetTextureChain(model):
    for tex in model.textures:
        tex.texturechains = []

    for face in model.faces:
        if not face.texinfo or not face.texinfo.texture:
            continue
        face.texinfo.texture.texturechains.append(face)



def Mod_Init():
    """Initializes the model loading subsystem."""
    global r_notexture_mip

    # Create a dummy texture to use when a real one is missing
    # This prevents the engine from crashing on bad texture lookups
    r_notexture_mip = texture_t("notexture", 16, 16)

    # In a full engine, we would also clear the model list here
    print("Model Subsystem Initialized.")


def Mod_FindName(name):
    global mod_numknown
    if not name:
        sys_sdl_unix.Sys_Error('Mod_FindName: name is None')

    for i in range( mod_numknown ):
        mod = mod_known[i]
        if mod.name == name:
            break

    if i == mod_numknown:
        if mod_numknown == MAX_MOD_KNOWN:
            sys_sdl_unix.Sys_Error('mod_numknown == MAX_MOD_KNOWN')
        mod.name = name
        mod.needload = True
        mod_numknown += 1


def Mod_ForName(name, crash):
    mod = Mod_FindName(name)
    return Mod_LoadModel(mod, crash)