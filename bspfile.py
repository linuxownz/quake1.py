#bspfile.py 

MAXLIGHTMAPS = 4

MAX_MAP_HULLS        = 4        
MAX_MAP_MODELS       = 256      
MAX_MAP_BRUSHES      = 4096     
MAX_MAP_ENTITIES     = 1024     
MAX_MAP_ENTSTRING    = 65536    
MAX_MAP_PLANES       = 32767    
MAX_MAP_NODES        = 32767
MAX_MAP_CLIPNODES    = 32767    
MAX_MAP_VERTS        = 65535    
MAX_MAP_FACES        = 65535    
MAX_MAP_MARKSURFACES = 65535
MAX_MAP_TEXINFO      = 4096
MAX_MAP_EDGES        = 256000
MAX_MAP_SURFEDGES    = 512000
MAX_MAP_TEXTURES     = 512
MAX_MAP_MIPTEX       = 0x200000
MAX_MAP_LIGHTING     = 0x100000
MAX_MAP_VISIBILITY   = 0x100000
MAX_MAP_PORTALS      = 65536

MAX_KEY   =  32
MAX_VALUE =  1024

BSPVERSION =  29

BSP2VERSION_2PSB = ((ord('B') << 24) | (ord('S') << 16) | (ord('P') << 8)  | ord('2'))
BSP2VERSION_BSP2 = ((ord('B') << 0)  | (ord('S') << 8)  | (ord('P') << 16) | (ord('2')<<24))

class lump_t():
    def __init__(self, fileofs, filelen):
        self.fileofs = fileofs
        self.filelen = filelen

LUMP_ENTITIES    = 0   
LUMP_PLANES      = 1   
LUMP_TEXTURES    = 2   
LUMP_VERTEXES    = 3   
LUMP_VISIBILITY  = 4   
LUMP_NODES       = 5   
LUMP_TEXINFO     = 6   
LUMP_FACES       = 7   
LUMP_LIGHTING    = 8   
LUMP_CLIPNODES   = 9   
LUMP_LEAFS       = 10  
LUMP_MARKSURFACES = 11
LUMP_EDGES       = 12  
LUMP_SURFEDGES   = 13  
LUMP_MODELS      = 14  

HEADER_LUMPS     = 15  

MIPLEVELS = 4

PLANE_X = 0
PLANE_X = 1
PLANE_Z = 2
PLANE_ANYX = 3
PLANE_ANYX = 4
PLANE_ANYZ = 5

CONTENTS_EMPTY    = -1
CONTENTS_SOLID    = -2
CONTENTS_WATER    = -3
CONTENTS_SLIME    = -4
CONTENTS_LAVA     = -5
CONTENTS_SKY      = -6
CONTENTS_ORIGIN   = -7      
CONTENTS_CLIP     = -8      

CONTENTS_CURRENT_0    = -9
CONTENTS_CURRENT_90   = -10
CONTENTS_CURRENT_180  = -11
CONTENTS_CURRENT_270  = -12
CONTENTS_CURRENT_UP   = -13
CONTENTS_CURRENT_DOWN = -14

TEX_SPECIAL = 1
TEX_MISSING = 2

AMBIENT_WATER = 0 
AMBIENT_SKY   = 1
AMBIENT_SLIME = 2
AMBIENT_LAVA  = 3

NUM_AMBIENTS  = 4

class dmodel_t():
    def __init__(self):
        self.mins   = [0, 0, 0]
        self.maxs   = [0, 0, 0]
        self.origin = [0, 0, 0]
        self.headnode = [0 for _ in range(MAX_MAP_HULLS)]
        self.visleafs = 0
        self.firstface = 0
        self.numfaces = 0

class dheader_t():
    def __init__(self):
        self.version = 0
        self.lumps : list[lump_t] = [lump_t() for _ in range(HEADER_LUMPS)]

class dmiptexlump_t():
    def __init__(self):
        self.nummiptex = 0
        self.dataofs   = [0, 0, 0, 0]

class miptex_t():
    def __init__(self):
        self.name = ''
        self.width = 0
        self.height = 0
        self.offsets = [0 for _ in range(MIPLEVELS)]

class dvertex_t():
    def __init__(self):
        self.point = [0., 0., 0.,]


class dplane_t():
    def __init__(self):
        self.normal = [0., 0., 0. ]
        self.dist   = 0.0
        self.type   = 0

class dsnode_t():
    def __init__(self):
        self.planenum = 0    
        self.children = [0, 0]
        self.mins     = [0, 0, 0]
        self.maxs     = [0, 0, 0]
        self.firstface = 0
        self.numfaces  = 0

class dl1node_t():
    def __init__(self):
        self.planenum = 0    
        self.children = [0, 0]
        self.mins     = [0, 0, 0]
        self.maxs     = [0, 0, 0]
        self.firstface = 0
        self.numfaces  = 0

class dl2node_t():
    def __init__(self):
        self.planenum = 0    
        self.children = [0, 0]
        self.mins     = [0, 0, 0]
        self.maxs     = [0, 0, 0]
        self.firstface = 0
        self.numfaces  = 0


class dsclipnode_t():
    def __init__(self):
        self.planenum = 0    
        self.children = [0, 0]
 
class dlclipnode_t():
    def __init__(self):
        self.planenum = 0    
        self.children = [0, 0]
 
class texinfo_t():
    def __init__(self):
        self.vecs = [[0, 0, 0, 0], [0, 0, 0, 0]]
        self.miptex = 0
        self.flags = 0

class dsedge_t():
    def __init__(self):
        self.v = [0, 0]

class dledge_t():
    def __init__(self):
        self.v = [0, 0]
 
class dsface_t():
    def __init__(self):
        self.planenum = 0
        self.side = 0
        self.firstedge = 0
        self.numedges = 0
        self.texinfo = 0

        self.styles = bytearray(MAXLIGHTMAPS)
        self.lightofs = 0

class dlface_t():
    def __init__(self):
        self.planenum = 0
        self.side = 0
        self.firstedge = 0
        self.numedges = 0
        self.texinfo = 0

        self.styles = bytearray(MAXLIGHTMAPS)
 
class dsleaf_t():
    def __init__(self):
        self.contents = 0
        self.visofs = 0

        self.mins = [0, 0, 0]
        self.maxs = [0, 0, 0]

        self.firstmarksurface = 0
        self.nummarksurface = 0

        self.ambient_level = bytearray(NUM_AMBIENTS)

class dl1leaf_t():
    def __init__(self):
        self.contents = 0
        self.visofs = 0

        self.mins = [0, 0, 0]
        self.maxs = [0, 0, 0]

        self.firstmarksurface = 0
        self.nummarksurface = 0

        self.ambient_level = bytearray(NUM_AMBIENTS)

class dl2leaf_t():
    def __init__(self):
        self.contents = 0
        self.visofs = 0

        self.mins = [0, 0, 0]
        self.maxs = [0, 0, 0]

        self.firstmarksurface = 0
        self.nummarksurface = 0

        self.ambient_level = bytearray(NUM_AMBIENTS)
