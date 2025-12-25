#bspfile.py 

import struct
import gl_model

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
PLANE_Y = 1
PLANE_Z = 2
PLANE_ANYX = 3
PLANE_ANYY = 4
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


def Mod_LoadTextures(model, lump_data):
    # 1. Read the number of textures (First 4 bytes of the lump)
    num_textures = struct.unpack('<i', lump_data[:4])[0]
    
    # 2. Get the array of offsets to each miptex_t
    # Offset array starts at byte 4 and has num_textures entries
    offsets = struct.unpack(f'<{num_textures}i', lump_data[4:4 + (num_textures * 4)])
    
    model.textures = []

    for i in range(num_textures):
        if offsets[i] == -1: # Handle empty/null texture slots
            model.textures.append(r_notexture_mip)
            continue
            
        # 3. Jump to the start of the miptex_t header
        base = offsets[i]
        
        # miptex_t header is 40 bytes: 
        # 16 (name) + 4 (width) + 4 (height) + 16 (4 mip offsets)
        header = struct.unpack('<16sII4I', lump_data[base : base + 40])
        
        name = header[0].split(b'\0')[0].decode('ascii')
        width = header[1]
        height = header[2]
        mip_offsets = header[3:] # The offsets to the 8-bit pixel data
        
        # 4. Extract the raw 8-bit pixels for the first MIP level
        # The first mip offset is relative to the start of the miptex_t header
        pixel_start = base + mip_offsets[0]
        pixel_end = pixel_start + (width * height)
        pixel_data = lump_data[pixel_start : pixel_end]
        
        import gl_texmgr
        # 5. Determine flags and call your TexMgr
        flags = gl_texmgr.TEXPREF_MIPMAP
        if name.startswith('{'):
            flags |= gl_texmgr.TEXPREF_ALPHA
        if name.startswith('*'):
            flags |= gl_texmgr.TEXPREF_WARPIMAGE
            
        # Create the engine texture_t (the Noun)
        tx = gl_texmgr.texture_t(name, width, height)
        
        # Load into OpenGL (returns a gltexture_t handle)
        tx.gltexture = gl_texmgr.TexMgr_LoadImage(
            model, name, width, height, 
            gl_texmgr.srcformat.SRC_INDEXED, 
            pixel_data, '', 0, flags
        )
        
        model.textures.append(tx)

# bspfile.py

def Mod_LoadVertexes(model, lump_data):
    # Each vertex is 3 floats (x, y, z) = 12 bytes
    count = len(lump_data) // 12
    model.vertexes = []
    
    for i in range(count):
        # Unpack 3 little-endian floats
        coords = struct.unpack('<3f', lump_data[i*12 : i*12 + 12])
        # Use the mvertex_t noun from gl_model
        model.vertexes.append(gl_model.mvertex_t(list(coords)))

def Mod_LoadPlanes(model, lump_data):
    # Each plane is 3 floats (normal), 1 float (dist), 1 int (type) = 20 bytes
    count = len(lump_data) // 20
    model.planes = []
    
    for i in range(count):
        data = struct.unpack('<3ffI', lump_data[i*20 : i*20 + 20])
        # normal_x, normal_y, normal_z, dist, type
        # In Quake, planes also have signbits for fast testing, 
        # but for now, we'll stick to the basics.
        plane = gl_model.mplane_t(list(data[0:3]), data[3], data[4], 0)
        model.planes.append(plane)

def Mod_LoadEdges(model, lump_data):
    # Each edge is 2 unsigned shorts (vertex indices) = 4 bytes
    count = len(lump_data) // 4
    model.edges = []
    
    for i in range(count):
        # Unpack two 16-bit unsigned integers
        v_indices = struct.unpack('<HH', lump_data[i*4 : i*4 + 4])
        
        # Create the medge_t noun (ensure this matches your gl_model definition)
        edge = gl_model.medge_t()
        edge.v = [v_indices[0], v_indices[1]]
        model.edges.append(edge)

def Mod_LoadSurfedges(model, lump_data):
    # Each surfedge is 1 signed 32-bit integer = 4 bytes
    count = len(lump_data) // 4
    # Surfedges are just a flat list of integers
    model.surfedges = struct.unpack(f'<{count}i', lump_data)

def Mod_LoadTexinfo(model, lump_data):
    # Each texinfo is 8 floats (vecs) + 2 ints (miptex, flags) = 40 bytes
    count = len(lump_data) // 40
    model.texinfo = []
    
    for i in range(count):
        # 4 floats for S vector, 4 floats for T vector, 1 int miptex, 1 int flags
        data = struct.unpack('<4f4fII', lump_data[i*40 : i*40 + 40])
        
        info = gl_model.mtexinfo_t()
        info.vecs = [list(data[0:4]), list(data[4:8])]
        
        # Link to the actual texture object we loaded in Mod_LoadTextures
        mip_idx = data[8]
        if mip_idx < len(model.textures):
            info.texture = model.textures[mip_idx]
        else:
            info.texture = gl_model.r_notexture_mip
            
        info.flags = data[9]
        model.texinfo.append(info)

# bspfile.py

def Mod_LoadModel(model, buffer):
    # ... previous header unpacking code ...
    lumps = []
    for i in range(HEADER_LUMPS):
        ofs, size = struct.unpack('<ii', buffer[4 + i*8 : 12 + i*8])
        lumps.append(lump_t(ofs, size))

    # 1. Vertexes
    Mod_LoadVertexes(model, buffer[lumps[LUMP_VERTEXES].fileofs : lumps[LUMP_VERTEXES].fileofs + lumps[LUMP_VERTEXES].filelen])
    
    # 2. Textures (Always load textures before texinfo)
    Mod_LoadTextures(model, buffer[lumps[LUMP_TEXTURES].fileofs : lumps[LUMP_TEXTURES].fileofs + lumps[LUMP_TEXTURES].filelen])
    
    # 3. Texinfo
    Mod_LoadTexinfo(model, buffer[lumps[LUMP_TEXINFO].fileofs : lumps[LUMP_TEXINFO].fileofs + lumps[LUMP_TEXINFO].filelen])

    # 4. Planes
    Mod_LoadPlanes(model, buffer[lumps[LUMP_PLANES].fileofs : lumps[LUMP_PLANES].fileofs + lumps[LUMP_PLANES].filelen])

    # 5. Edges
    Mod_LoadEdges(model, buffer[lumps[LUMP_EDGES].fileofs : lumps[LUMP_EDGES].fileofs + lumps[LUMP_EDGES].filelen])

    # 6. Surfedges
    Mod_LoadSurfedges(model, buffer[lumps[LUMP_SURFEDGES].fileofs : lumps[LUMP_SURFEDGES].fileofs + lumps[LUMP_SURFEDGES].filelen])
    
    # 7. Faces (Add this call)
    f_lump = lumps[LUMP_FACES]
    Mod_LoadFaces(model, buffer[f_lump.fileofs : f_lump.fileofs + f_lump.filelen])

    # 8. Load the raw light data lump
    l_lump = lumps[LUMP_LIGHTING]
    model.lightdata = buffer[l_lump.fileofs : l_lump.fileofs + l_lump.filelen]

    # 9. Build Geometry and Lightmaps
    import r_brush
    for face in model.faces:
        gl_model.GL_BuildPolygon(model, face) # Generates the 7-component verts
        r_brush.R_BuildLightmap(model, face)  # Generates the lightmap textures

    # 10. Link texture chains for the renderer
    gl_model.Mod_SetTextureChain(model)
    
    print(f"Model {model.name} fully loaded with lighting and polygons.")

def Mod_LoadFaces(model, lump_data):
    # Each face is 20 bytes in standard Quake BSP
    count = len(lump_data) // 20
    model.faces = []
    
    for i in range(count):
        # planenum(short), side(short), firstedge(int), numedges(short), 
        # texinfo(short), styles(4 bytes), lightofs(int)
        data = struct.unpack('<h h i h h 4B i', lump_data[i*20 : i*20 + 20])
        
        face = gl_model.msurface_t()
        
        # Link Plane (handle side bit)
        planenum = data[0]
        side = data[1]
        face.plane = model.planes[planenum]
        face.flags = gl_model.SURF_PLANEBACK if side else 0
        
        # Edge details
        face.firstedge = data[2]
        face.numedges = data[3]
        
        # Link Texinfo
        texinfo_idx = data[4]
        face.texinfo = model.texinfo[texinfo_idx]
        
        # Lightmap details (we will use these later for lighting)
        face.styles = list(data[5:9])
        face.lightofs = data[9]
        
        model.faces.append(face)