# bspfile.py

import struct
import gl_model
import quakedef

# --- Constants ---
MAXLIGHTMAPS = 4
HEADER_LUMPS = 15
BSPVERSION   = 29

MAX_MAP_HULLS       = 4
MAX_MAP_MODELS      = 256
MAX_MAP_BRUSHES     = 4096
MAX_MAP_ENTITIES    = 1024
MAX_MAP_ENTSTRING   = 65536
MAX_MAP_PLANES      = 32767
MAX_MAP_NODES       = 32767
MAX_MAP_CLIPNODES   = 32767
MAX_MAP_VERTS       = 65535
MAX_MAP_FACES       = 65535
MAX_MAP_MARKSURFACES=  65535
MAX_MAP_TEXINFO     = 4096
MAX_MAP_EDGES       = 256000
MAX_MAP_SURFEDGES   = 512000
MAX_MAP_TEXTURES    = 512
MAX_MAP_MIPTEX      = 0x200000
MAX_MAP_LIGHTING    = 0x100000
MAX_MAP_VISIBILITY  = 0x100000
MAX_MAP_PORTALS     = 65536

MAX_KEY = 32
MAX_VALUE = 1024

# Lump Indices
LUMP_ENTITIES     = 0
LUMP_PLANES       = 1
LUMP_TEXTURES     = 2
LUMP_VERTEXES     = 3
LUMP_VISIBILITY   = 4
LUMP_NODES        = 5
LUMP_TEXINFO      = 6
LUMP_FACES        = 7
LUMP_LIGHTING     = 8
LUMP_CLIPNODES    = 9
LUMP_LEAFS        = 10
LUMP_MARKSURFACES = 11
LUMP_EDGES        = 12
LUMP_SURFEDGES    = 13
LUMP_MODELS       = 14

NUM_AMBIENTS      = 4


CONTENTS_EMPTY         = -1
CONTENTS_SOLID         = -2
CONTENTS_WATER         = -3
CONTENTS_SLIME         = -4
CONTENTS_LAVA          = -5
CONTENTS_SKY           = -6
CONTENTS_ORIGIN        = -7
CONTENTS_CLIP          = -8

CONTENTS_CURRENT_0     = -9
CONTENTS_CURRENT_90    = -10
CONTENTS_CURRENT_180   = -11
CONTENTS_CURRENT_270   = -12
CONTENTS_CURRENT_UP    = -13
CONTENTS_CURRENT_DOWN  = -14

PLANE_X       = 0
PLANE_Y       = 1
PLANE_Z       = 2

PLANE_ANYX    = 3
PLANE_ANYY    = 4
PLANE_ANYZ    = 5



class lump_t:
    def __init__(self, fileofs, filelen):
        self.fileofs = fileofs
        self.filelen = filelen

# --- Core Loader ---

def Mod_LoadModel(model, buffer):
    """The main entry point for parsing a BSP file into the model object."""
    lumps = []
    # Header is 4-byte version + 15 pairs of (offset, len)
    for i in range(HEADER_LUMPS):
        ofs, size = struct.unpack('<ii', buffer[4 + i*8 : 12 + i*8])
        lumps.append(lump_t(ofs, size))

    # Helper to get raw data for a lump
    def get_lump(idx):
        l = lumps[idx]
        return buffer[l.fileofs : l.fileofs + l.l.filelen]

    # 1. Geometry Data
    Mod_LoadVertexes(model, buffer[lumps[LUMP_VERTEXES].fileofs : lumps[LUMP_VERTEXES].fileofs + lumps[LUMP_VERTEXES].filelen])
    Mod_LoadPlanes(model, buffer[lumps[LUMP_PLANES].fileofs : lumps[LUMP_PLANES].fileofs + lumps[LUMP_PLANES].filelen])
    Mod_LoadTextures(model, buffer[lumps[LUMP_TEXTURES].fileofs : lumps[LUMP_TEXTURES].fileofs + lumps[LUMP_TEXTURES].filelen])
    Mod_LoadTexinfo(model, buffer[lumps[LUMP_TEXINFO].fileofs : lumps[LUMP_TEXINFO].fileofs + lumps[LUMP_TEXINFO].filelen])
    Mod_LoadEdges(model, buffer[lumps[LUMP_EDGES].fileofs : lumps[LUMP_EDGES].fileofs + lumps[LUMP_EDGES].filelen])
    Mod_LoadSurfedges(model, buffer[lumps[LUMP_SURFEDGES].fileofs : lumps[LUMP_SURFEDGES].fileofs + lumps[LUMP_SURFEDGES].filelen])
    Mod_LoadFaces(model, buffer[lumps[LUMP_FACES].fileofs : lumps[LUMP_FACES].fileofs + lumps[LUMP_FACES].filelen])

    # 2. Topology / Tree Data
    Mod_LoadNodes(model, buffer[lumps[LUMP_NODES].fileofs : lumps[LUMP_NODES].fileofs + lumps[LUMP_NODES].filelen])
    Mod_LoadLeafs(model, buffer[lumps[LUMP_LEAFS].fileofs : lumps[LUMP_LEAFS].fileofs + lumps[LUMP_LEAFS].filelen])
    Mod_LoadMarksurfaces(model, buffer[lumps[LUMP_MARKSURFACES].fileofs : lumps[LUMP_MARKSURFACES].fileofs + lumps[LUMP_MARKSURFACES].filelen])
    Mod_LoadSubmodels(model, buffer[lumps[LUMP_MODELS].fileofs : lumps[LUMP_MODELS].fileofs + lumps[LUMP_MODELS].filelen])

    # 3. Raw Data Bulks (Lighting & Vis)
    model.lightdata = buffer[lumps[LUMP_LIGHTING].fileofs : lumps[LUMP_LIGHTING].fileofs + lumps[LUMP_LIGHTING].filelen]
    model.visdata = buffer[lumps[LUMP_VISIBILITY].fileofs : lumps[LUMP_VISIBILITY].fileofs + lumps[LUMP_VISIBILITY].filelen]

    # 4. Finalize the BSP Tree (Linking indices to objects)
    # The first submodel is always the main map (headnode for hull 0)
    Mod_SetParent(model, model.nodes[model.submodels[0].headnode[0]], None)

    print(f"BSP Parser: {model.name} data structures populated.")

# --- Lump Parsers ---

def Mod_LoadVertexes(model, lump_data):
    count = len(lump_data) // 12
    model.vertexes = []
    for i in range(count):
        coords = struct.unpack('<3f', lump_data[i*12 : i*12 + 12])
        model.vertexes.append(quakedef.mvertex_t(list(coords)))

def Mod_LoadPlanes(model, lump_data):
    count = len(lump_data) // 20
    model.planes = []
    for i in range(count):
        data = struct.unpack('<3ffI', lump_data[i*20 : i*20 + 20])
        model.planes.append(quakedef.mplane_t(list(data[0:3]), data[3], data[4], 0))

def Mod_LoadTextures(model, lump_data):
    num_textures = struct.unpack('<i', lump_data[:4])[0]
    offsets = struct.unpack(f'<{num_textures}i', lump_data[4:4 + (num_textures * 4)])
    model.textures = []
    import gl_texmgr
    for i in range(num_textures):
        if offsets[i] == -1:
            gl_model.textures.append(gl_model.r_notexture_mip)
            continue
        base = offsets[i]
        header = struct.unpack('<16sII4I', lump_data[base : base + 40])
        name = header[0].split(b'\0')[0].decode('ascii')
        width, height = header[1], header[2]
        pixel_data = lump_data[base + header[3] : base + header[3] + (width * height)]

        tx = quakedef.texture_t(name, width, height)
        tx.gltexture = gl_texmgr.TexMgr_LoadImage(model, name, width, height, gl_texmgr.srcformat.SRC_INDEXED, pixel_data, '', 0, gl_texmgr.TEXPREF_MIPMAP)
        model.textures.append(tx)

def Mod_LoadTexinfo(model, lump_data):
    count = len(lump_data) // 40
    model.texinfo = []
    for i in range(count):
        data = struct.unpack('<4f4fII', lump_data[i*40 : i*40 + 40])
        info = quakedef.mtexinfo_t()
        info.vecs = [list(data[0:4]), list(data[4:8])]
        info.texture = model.textures[data[8]] if data[8] < len(model.textures) else gl_model.r_notexture_mip
        info.flags = data[9]
        model.texinfo.append(info)

def Mod_LoadFaces(model, lump_data):
    count = len(lump_data) // 20
    model.faces = []
    for i in range(count):
        data = struct.unpack('<hhihh4Bi', lump_data[i*20 : i*20 + 20])
        face = quakedef.msurface_t()
        face.plane = model.planes[data[0]]
        face.flags = quakedef.SURF_PLANEBACK if data[1] else 0
        face.firstedge, face.numedges, texinfo_idx = data[2], data[3], data[4]
        face.texinfo = model.texinfo[texinfo_idx]
        face.styles = list(data[5:9])
        face.lightofs = data[9]
        model.faces.append(face)

def Mod_LoadEdges(model, lump_data):
    count = len(lump_data) // 4
    model.edges = []
    for i in range(count):
        v_indices = struct.unpack('<HH', lump_data[i*4 : i*4 + 4])
        edge = quakedef.medge_t()
        edge.v = [v_indices[0], v_indices[1]]
        model.edges.append(edge)

def Mod_LoadSurfedges(model, lump_data):
    count = len(lump_data) // 4
    model.surfedges = struct.unpack(f'<{count}i', lump_data)

def Mod_LoadNodes(model, lump_data):
    count = len(lump_data) // 24
    model.nodes = []
    for i in range(count):
        data = struct.unpack('<I 2h 3h 3h H H', lump_data[i*24 : i*24 + 24])
        node = quakedef.mnode_t()
        node.plane = model.planes[data[0]]
        node.children = list(data[1:3]) # Indices stored for now
        node.mins, node.maxs = list(data[3:6]), list(data[6:9])
        node.firstface, node.numfaces = data[9], data[10]
        model.nodes.append(node)

def Mod_LoadLeafs(model, lump_data):
    count = len(lump_data) // 28
    model.leafs = []
    for i in range(count):
        data = struct.unpack('<ii 3h 3h HH 4B', lump_data[i*28 : i*28 + 28])
        leaf = quakedef.mleaf_t()
        leaf.contents, leaf.visofs = data[0], data[1]
        leaf.mins, leaf.maxs = list(data[2:5]), list(data[5:8])
        leaf.firstmarksurface, leaf.nummarksurface = data[8], data[9]
        model.leafs.append(leaf)

def Mod_LoadMarksurfaces(model, lump_data):
    count = len(lump_data) // 2
    model.marksurfaces = struct.unpack(f'<{count}H', lump_data)

def Mod_LoadSubmodels(model, lump_data):
    count = len(lump_data) // 64
    model.submodels = []
    for i in range(count):
        data = struct.unpack('<9f 4i 3i', lump_data[i*64 : i*64 + 64])
        sub = quakedef.dmodel_t() # Memory-struct for submodels
        sub.mins, sub.maxs, sub.origin = data[0:3], data[3:6], data[6:9]
        sub.headnode = list(data[9:13])
        sub.visleafs, sub.firstface, sub.numfaces = data[13], data[14], data[15]
        model.submodels.append(sub)

# --- Tree Linking ---

def Mod_SetParent(model, node, parent):
    """Recursively links the BSP tree indices into object references."""
    node.parent = parent
    if node.contents < 0: # It's a leaf
        return

    for i in range(2):
        child_idx = node.children[i]
        if child_idx >= 0: # Child is a Node
            child = model.nodes[child_idx]
            node.children[i] = child
            Mod_SetParent(model, child, node)
        else: # Child is a Leaf
            child = model.leafs[-1 - child_idx]
            node.children[i] = child
            child.parent = node