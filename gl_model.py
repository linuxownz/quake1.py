#gl_model.py

import io
import math
import struct
import sys
from typing import Optional, Union

import bspfile
import common
import crc
import cvar
import gl_mesh
import gl_texmgr
import gl_warp
import host
import mathlib
import modelgen
import quakedef
import r_brush
import spritegen
import sv_main
import sys_sdl_unix
import wad
import zone

loadmodel: quakedef.qmodel_t = None
loadname:str = ''

mod_novis: bytearray = bytearray()
mod_novis_capacity: int = 0
mod_base: bytearray = bytearray()

mod_decompressed: bytearray = bytearray()
mod_decompressed_capacity: int = 0

MAX_MOD_KNOWN = 2048
mod_known: list[quakedef.qmodel_t] = [None] * MAX_MOD_KNOWN
mod_numknown:int = 0

r_notexture_mip: quakedef.texture_t  = None
r_notexture_mip2: quakedef.texture_t = None

MAXALIASTRIS = 4096
DSNODE_SIZE = 24
DL1NODE_SIZE = 32
DL2NODE_SIZE = 44
DSLEAF_SIZE = 28
DL1LEAF_SIZE = 32  # sizeof(dl1leaf_t): 32 bytes
DL2LEAF_SIZE = 44  # sizeof(dl2leaf_t): 44 bytes
DSCLIPNODE_SIZE = 8  # sizeof(dsclipnode_t): planenum (int32), children[2] (int16 x 2)
DLCLIPNODE_SIZE = 12  # sizeof(dlclipnode_t): planenum (int32), children[2] (int32 x 2)
DPLANE_SIZE = 20  # sizeof(dplane_t): normal (float x 3), dist (float), type (int32)
DMODEL_SIZE = 64  # sizeof(dmodel_t): 64 bytes
MAX_MAP_HULLS = 4


INT_SIZE = 4  # sizeof(int): 4 bytes

def Mod_Init():
    global cvar, _cmd, console
    global stverts, triangles, poseverts
    import _cmd
    import console
    import cvar

    # Texture coordinate vertex array: stvert_t stverts[MAXALIASVERTS]
    stverts = [
        modelgen.stvert_t() for _ in range(quakedef.MAXALIASVERTS)
    ]

    # Triangle topology array: mtriangle_t triangles[MAXALIASTRIS]
    triangles  = [
        quakedef.mtriangle_t() for _ in range(quakedef.MAXALIASTRIS)
    ]

    # Pose vertex buffer pointers: trivertx_t *poseverts[MAXALIASFRAMES]
    poseverts = [b""] * quakedef.MAXALIASFRAMES



    _cmd.Cmd_AddCommand('mcache', Mod_Print )

    cvar.Cvar_RegisterVariable({'name':'external_vis',      'value':'1', 'flags': cvar.CVAR_ARCHIVE})
    cvar.Cvar_RegisterVariable({'name':'external_textures', 'value':'1', 'flags': cvar.CVAR_ARCHIVE})
    cvar.Cvar_RegisterVariable({'name':'external_ents',     'value':'1', 'flags': cvar.CVAR_ARCHIVE})

    global r_notexture_mip, r_notexture_mip2
    r_notexture_mip = quakedef.texture_t("notexture", 32, 32)
    r_notexture_mip2 = quakedef.texture_t("notexture", 32, 32)

    print("Model Subsystem Initialized.")

def Mod_Extradata(mod: quakedef.qmodel_t):
    r = zone.Cache_Check(mod.cache)
    if r:
        return r

    Mod_LoadModel(mod, True)

    if not mod.cache.data:
        sys_sdl_unix.Sys_Error('Mod_Extradata: caching failed')

    return mod.cache.data




# --- Geometry Verbs ---

def GL_BuildPolygon(model: quakedef.qmodel_t, face):
    """Converts BSP face into a GL-friendly 7-float vertex array."""
    # This logic stays here because it is part of the GL frontend
    tex = face.texinfo
    # Assume glpoly_t is defined in quakedef or locally
    class glpoly_t:
        def __init__(self):
            self.numverts = 0
            self.verts = []

    poly = glpoly_t()
    verts = []
    mins = [99999, 99999]
    maxs = [-99999, -99999]

    for i in range(face.numedges):
        e_idx = model.surfedges[face.firstedge + i]
        v_idx = model.edges[e_idx].v[0] if e_idx >= 0 else model.edges[-e_idx].v[1]
        v = model.vertexes[v_idx].position
        verts.append(v)

        for j in range(2):
            val = (v[0] * tex.vecs[j][0] + v[1] * tex.vecs[j][1] +
                   v[2] * tex.vecs[j][2] + tex.vecs[j][3])
            mins[j] = min(mins[j], val)
            maxs[j] = max(maxs[j], val)

    face.texturemins = [int(mins[0] // 16), int(mins[1] // 16)]
    face.extents = [int(maxs[0] // 16) - int(mins[0] // 16),
                    int(maxs[1] // 16) - int(mins[1] // 16)]

    poly.numverts = len(verts)
    for v in verts:
        s1 = (v[0] * tex.vecs[0][0] + v[1] * tex.vecs[0][1] +
              v[2] * tex.vecs[0][2] + tex.vecs[0][3]) / tex.texture.width
        t1 = (v[0] * tex.vecs[1][0] + v[1] * tex.vecs[1][1] +
              v[2] * tex.vecs[1][2] + tex.vecs[1][3]) / tex.texture.height

        s2 = (v[0] * tex.vecs[0][0] + v[1] * tex.vecs[0][1] +
              v[2] * tex.vecs[0][2] + tex.vecs[0][3])
        s2 = (s2 - face.texturemins[0] * 16 + 8) / ((face.extents[0] + 1) * 16)

        t2 = (v[0] * tex.vecs[1][0] + v[1] * tex.vecs[1][1] +
              v[2] * tex.vecs[1][2] + tex.vecs[1][3])
        t2 = (t2 - face.texturemins[1] * 16 + 8) / ((face.extents[1] + 1) * 16)

        poly.verts.append([v[0], v[1], v[2], s1, t1, s2, t2])

    face.polys = poly

def Mod_SetTextureChain(model):
    """Links faces to textures for efficient batch rendering."""
    if not model.textures:
        return
    for tex in model.textures:
        tex.texturechains = []

    for face in model.faces:
        if not face.texinfo or not face.texinfo.texture:
            continue
        face.texinfo.texture.texturechains.append(face)


# --- System Management ---

def Mod_LoadModel(mod: quakedef.qmodel_t, crash: bool) -> quakedef.qmodel_t | None:
    global loadname, loadmodel

    # 1. Early exit if model is already loaded in memory
    if not mod.needload:
        if mod.type == quakedef.modtype_t.mod_alias:
            if zone.Cache_Check(mod.cache):
                return mod
        else:
            return mod

    # --- QUAKESPASM INLINE SUBMODEL CHECK (*1, *2, etc.) ---
    if mod.name and mod.name.startswith('*'):
        if loadmodel is None:
            host.Host_Error(f"Mod_LoadModel: submodel {mod.name} loaded with no world")

        sub_idx = int(mod.name[1:])
        if sub_idx < 0 or sub_idx >= loadmodel.numsubmodels:
            if crash:
                host.Host_Error(f"Mod_LoadModel: bad submodel number {mod.name}")
            return None

        # QuakeSpasm equivalent: *mod = loadmodel->submodels[sub_idx]
        # Copy the pre-parsed submodel object/dictionary into this slot
        sub = loadmodel.submodels[sub_idx]
        mod.__dict__.update(sub.__dict__)
        mod.needload = False
        return mod
    # --------------------------------------------------------

    buf = bytearray(1024)
    buf = common.COM_LoadStackFile(mod.name, buf, 1024, True)
    if not buf or len(buf) < 4:
        if crash:
            host.Host_Error(f"Mod_LoadModel: {mod.name} not found")
        # C parity: Reset slot on non-fatal load failure (memset(mod, 0, sizeof(*mod)))
        mod.name = ""
        mod.needload = True
        return None

    # 3. Setup global loading context
    loadname = common.COM_FileBase(mod.name)
    loadmodel = mod
    mod.needload = False

    # 4. Extract 32-bit little-endian magic header
    mod_type = struct.unpack("<I", buf[:4])[0]

    # 5. Dispatch to subtype loader
    if mod_type == modelgen.IDPOLYHEADER:
        Mod_LoadAliasModel(mod, buf)
    elif mod_type == spritegen.IDSPRITEHEADER:
        Mod_LoadSpriteModel(mod, buf)
    else:
        # Defaults to BSP brush model
        Mod_LoadBrushModel(mod, buf)

    return mod





def Mod_ForName(name: str, crash: bool = False):
    mod = Mod_FindName(name)
    return Mod_LoadModel(mod, crash)

def Mod_LoadWadFiles(mod: quakedef.qmodel_t) -> wad.wad_t | None:
    if not cvar.Cvar_GetCvar("external_textures").value:
        return None

    if mod.name != sv_main.sv.modelname:
        return None

    if not mod.entities:
        return None

    # Parse opening brace '{' of worldspawn entity
    data = common.COM_Parse(mod.entities)
    if not data or common.com_token != "{":
        return None

    while True:
        # 1. Parse Key token
        data = common.COM_Parse(data)
        if not data:
            return None

        if common.com_token == "}":
            break  # Reached end of worldspawn entity keys

        # Strip leading underscore and normalize key (e.g. "_wad" -> "wad")
        key = common.com_token.lstrip("_").rstrip().lower()

        # 2. Parse Value token (COM_ParseEx handles quoted values with spaces)
        data = common.COM_ParseEx(data)
        if not data:
            return None

        value = common.com_token

        # 3. Match 'wad' key name and delegate to WAD loader subsystem
        if key == "wad":
            return wad.W_LoadWadList(value)

    return None


def Mod_LoadWadTexture( mod: quakedef.qmodel_t, wads: wad.wad_t | None, name: str, out_pal: list[bool] | None = None, out_pixels: list[bytearray | None] | None = None,) -> quakedef.texture_t | None:

    if not wads or not name:
        return None

    # 1. W_GetLumpName(wads, name) -> returns raw byte lump from WAD chain
    lump = wad.W_GetLumpName(wads, name)
    if not lump or len(lump) < 40:  # sizeof(miptex_t) == 40
        return None

    # 2. Extract miptex_t header
    # char name[16], unsigned width, unsigned height, unsigned offsets[4]
    raw_name = lump[0:16].split(b"\x00", 1)[0].decode("ascii", errors="ignore")
    width, height = struct.unpack("<II", lump[16:24])
    offsets = struct.unpack("<IIII", lump[24:40])

    if (width & 15) or (height & 15):
        sys_sdl_unix.Sys_Error(
            f"Mod_LoadWadTexture: {raw_name} size ({width}x{height}) bad"
        )

    num_pixels = width * height
    total_pixels = num_pixels + (num_pixels // 4) + (num_pixels // 16) + (num_pixels // 64)

    if len(lump) < offsets[0] + total_pixels:
        return None

    # 3. Allocate texture_t structure
    tx = quakedef.texture_t()
    tx.name = raw_name
    tx.width = width
    tx.height = height

    for i in range(4):
        tx.offsets[i] = offsets[i]

    # Raw 8-bit palette indexed pixel buffer
    pixels = bytearray(lump[offsets[0] : offsets[0] + total_pixels])

    # 4. Out-pointer assignments matching C double pointers/flags
    if out_pal is not None:
        out_pal[0] = False  # Set palette mode status if needed by caller

    if out_pixels is not None:
        out_pixels[0] = pixels

    # 5. Call TexMgr with correct C signature order:
    # TexMgr_LoadTexture(mod, name, width, height, pixels, src_depth, flags)
    tx.gl_texturenum = gl_texmgr.TexMgr_LoadTexture(
        mod,
        tx.name,
        tx.width,
        tx.height,
        pixels,
        gl_texmgr.SRC_PALETTE,
        gl_texmgr.TEX_MIPMAP,
    )

    return tx

def Mod_CheckFullbrights(pixels: bytearray, count: int) -> bool:
    for i in range(count):
        if pixels[i] > 223:
            return True
    return False

def Mod_CheckFullbrightsValve(name: str, pixels: bytearray, count: int) -> bool:
    if name[0] == '~' or name[2] == '~' and name[0] == '+':
        return Mod_CheckFullbrights(pixels, count)
    return False

def Mod_LoadTextures(lump: quakedef.lump_t) -> None:
    """Quakespasm C-parity port for Mod_LoadTextures in gl_model.c"""
    global loadmodel, mod_base

    if not lump.filelen:
        loadmodel.numtextures = 0
        loadmodel.textures = []
        return

    lump_start = lump.fileofs

    if lump.filelen < 4:
        sys_sdl_unix.Sys_Error("Mod_LoadTextures: funny lump size")

    # dmiptexlump_t header
    nummiptex = struct.unpack_from("<i", mod_base, lump_start)[0]

    if nummiptex < 0:
        sys_sdl_unix.Sys_Error("Mod_LoadTextures: nummiptex < 0")

    loadmodel.numtextures = nummiptex
    loadmodel.textures = [None] * nummiptex

    # Parse each miptex in the lump
    for i in range(nummiptex):
        dataofs_ptr = lump_start + 4 + (i * 4)

        # Quakespasm bounds check
        if dataofs_ptr + 4 > lump_start + lump.filelen:
            sys_sdl_unix.Sys_Error("Mod_LoadTextures: bad lump size")

        dataofs = struct.unpack_from("<i", mod_base, dataofs_ptr)[0]

        if dataofs == -1:
            continue

        tx_ofs = lump_start + dataofs

        # Bounds check texture offset inside lump
        if tx_ofs < lump_start or tx_ofs + 40 > lump_start + lump.filelen:
            sys_sdl_unix.Sys_Error("Mod_LoadTextures: bad texture offset")

        # Unpack Quakespasm miptex_t / texture_t
        # char name[16], unsigned width, height, offsets[4]
        name_raw, width, height, o0, o1, o2, o3 = struct.unpack_from(
            "<16sIIIIII", mod_base, tx_ofs
        )

        if (width & 15) or (height & 15):
            sys_sdl_unix.Sys_Error(f"Texture {name_raw!r} is not 16 aligned")

        tx = quakedef.texture_t()
        tx.name = name_raw.decode("latin-1").split("\x00", 1)[0]
        tx.width = width
        tx.height = height
        tx.offsets = [o0, o1, o2, o3]

        # mip 0 pixels immediately follow the 40-byte miptex_t header
        pix_ofs = tx_ofs + 40
        pix_count = width * height
        pixel_data = bytes(mod_base[pix_ofs : pix_ofs + pix_count])

        # Quakespasm specific runtime field initializations
        tx.gl_texturenum = 0
        tx.fullbright_gl_texturenum = 0
        tx.flat_gl_texturenum = 0
        tx.anim_total = 0
        tx.anim_min = 0
        tx.anim_max = 0
        tx.anim_next = None
        tx.alternate_anims = None

        loadmodel.textures[i] = tx

        # Texture upload (C: Mod_LoadTextures, johnfitz section)
        if not sys_sdl_unix.isDedicated:
            if tx.name.lower().startswith("sky"):
                # sky textures are not uploaded here: Sky_LoadTexture lives in the sky module (not ported/seen yet)
                pass
            elif tx.name.startswith("*"):
                # warping texture
                texturename = f"{loadmodel.name}:{tx.name}"
                tx.gltexture = gl_texmgr.TexMgr_LoadImage(
                    loadmodel, texturename, tx.width, tx.height,
                    gl_texmgr.srcformat.SRC_INDEXED, pixel_data, loadmodel.name, pix_ofs,
                    gl_texmgr.TEXPREF_NOBRIGHT | gl_texmgr.TEXPREF_NOPICMIP)

                wsize = gl_warp.gl_warpimagesize or 128
                tx.warpimage = gl_texmgr.TexMgr_LoadImage(
                    loadmodel, f"{texturename}_warp", wsize, wsize,
                    gl_texmgr.srcformat.SRC_RGBA, bytes(wsize * wsize * 4), "", 0,
                    gl_texmgr.TEXPREF_NOBRIGHT | gl_texmgr.TEXPREF_NOPICMIP | gl_texmgr.TEXPREF_WARPIMAGE)
                tx.update_warp = True
            else:
                # regular texture
                extraflags = gl_texmgr.TEXPREF_ALPHA if tx.name.startswith("{") else 0
                texturename = f"{loadmodel.name}:{tx.name}"

                if Mod_CheckFullbrights(pixel_data, pix_count):
                    tx.gltexture = gl_texmgr.TexMgr_LoadImage(
                        loadmodel, texturename, tx.width, tx.height,
                        gl_texmgr.srcformat.SRC_INDEXED, pixel_data, loadmodel.name, pix_ofs,
                        gl_texmgr.TEXPREF_MIPMAP | gl_texmgr.TEXPREF_NOBRIGHT | extraflags)
                    tx.fullbright = gl_texmgr.TexMgr_LoadImage(
                        loadmodel, f"{loadmodel.name}:{tx.name}_glow", tx.width, tx.height,
                        gl_texmgr.srcformat.SRC_INDEXED, pixel_data, loadmodel.name, pix_ofs,
                        gl_texmgr.TEXPREF_MIPMAP | gl_texmgr.TEXPREF_FULLBRIGHT | extraflags)
                else:
                    tx.gltexture = gl_texmgr.TexMgr_LoadImage(
                        loadmodel, texturename, tx.width, tx.height,
                        gl_texmgr.srcformat.SRC_INDEXED, pixel_data, loadmodel.name, pix_ofs,
                        gl_texmgr.TEXPREF_MIPMAP | extraflags)

    # Quakespasm Animation Sequence Chaining (+0..+9, +a..+j)
    for i in range(nummiptex):
        tx = loadmodel.textures[i]
        if not tx or not tx.name.startswith("+"):
            continue

        if tx.anim_next is not None:
            continue  # Already processed in a chain

        anims = [None] * 10
        altanims = [None] * 10
        max_frame = 0
        altmax_frame = 0

        for j in range(nummiptex):
            tx2 = loadmodel.textures[j]
            if not tx2 or not tx2.name.startswith("+"):
                continue

            # Compare suffix name (everything after +X)
            if tx2.name[2:] != tx.name[2:]:
                continue

            c = tx2.name[1]
            if "0" <= c <= "9":
                num = ord(c) - ord("0")
                if num < 10:
                    anims[num] = tx2
                    if num > max_frame:
                        max_frame = num
            elif "a" <= c <= "j":
                num = ord(c) - ord("a")
                if num < 10:
                    altanims[num] = tx2
                    if num > altmax_frame:
                        altmax_frame = num

        # Link primary anims
        for j in range(max_frame + 1):
            if not anims[j]:
                sys_sdl_unix.Sys_Error(f"Missing frame {j} of {tx.name}")
            anims[j].anim_total = max_frame + 1
            anims[j].anim_min = j
            anims[j].anim_max = max_frame + 1
            anims[j].anim_next = anims[(j + 1) % (max_frame + 1)]

            if altmax_frame > 0:
                anims[j].alternate_anims = altanims[0]

        # Link alternate anims
        if altmax_frame > 0:
            for j in range(altmax_frame + 1):
                if not altanims[j]:
                    sys_sdl_unix.Sys_Error(f"Missing frame {j} of {tx.name}")
                altanims[j].anim_total = altmax_frame + 1
                altanims[j].anim_min = j
                altanims[j].anim_max = altmax_frame + 1
                altanims[j].anim_next = altanims[(j + 1) % (altmax_frame + 1)]
                altanims[j].alternate_anims = anims[0]


# Magic header "QLIT" in 32-bit little-endian integer format (0x54494C51)
IDLITHEADER = 0x54494C51  # b'QLIT'
LIT_VERSION = 1


def Mod_LoadLighting(lump: quakedef.lump_t) -> None:
    """QuakeSpasm Mod_LoadLighting: lightdata is always RGB (3 bytes/texel)."""
    global loadmodel, mod_base

    loadmodel.lightdata = None

    if not lump.filelen:
        return

    # Valve (v30) BSPs already carry RGB lighting in the lump
    if getattr(loadmodel, "bspversion", None) == BSPVERSION_VALVE:
        loadmodel.lightdata = bytearray(
            mod_base[lump.fileofs : lump.fileofs + lump.filelen]
        )
        return

    # External .lit file (QLIT header: 4 byte ident, 4 byte version, then RGB)
    map_base = loadmodel.name.rsplit(".", 1)[0]
    lit_data = common.COM_LoadHunkFile(f"{map_base}.lit", False)
    if lit_data and len(lit_data) > 8:
        ident, version = struct.unpack_from("<ii", lit_data, 0)
        if ident == IDLITHEADER and version == LIT_VERSION:
            rgb = bytearray(lit_data[8:])
            if len(rgb) >= lump.filelen * 3:
                loadmodel.lightdata = rgb
                return
            console.Con_Warning(f"{map_base}.lit has wrong size, ignoring\n")
        else:
            console.Con_Warning(f"{map_base}.lit has unknown header/version, ignoring\n")

    # Internal mono lump: expand each byte to R=G=B
    mono = bytes(mod_base[lump.fileofs : lump.fileofs + lump.filelen])
    rgb = bytearray(len(mono) * 3)
    rgb[0::3] = mono
    rgb[1::3] = mono
    rgb[2::3] = mono
    loadmodel.lightdata = rgb

def Mod_FindName(name: str) -> quakedef.qmodel_t:
    global mod_known, mod_numknown

    if not name:
        sys_sdl_unix.Sys_Error("Mod_FindName: null name")

    for i in range(mod_numknown):
        if mod_known[i].name == name:
            return mod_known[i]

    if mod_numknown == MAX_MOD_KNOWN:
        sys_sdl_unix.Sys_Error("mod_numknown == MAX_MOD_KNOWN")

    mod = quakedef.qmodel_t()
    mod.name = name
    mod.needload = True
    mod_known[mod_numknown] = mod
    mod_numknown += 1

    return mod




def Mod_LoadVisibility(l: quakedef.lump_t):
    loadmodel.viswarn = False
    if not l.filelen:
        loadmodel.visdata = None
        return

    loadmodel.visdata = bytearray(mod_base[l.fileofs : l.fileofs + l.filelen])



def Mod_LoadEntities(l: quakedef.lump_t) -> None:
    """Parses internal BSP entity lump or loads external .ent override file.

    C equivalent:
    void Mod_LoadEntities (lump_t *l) in gl_model.c
    """
    global loadmodel, mod_base

    _crc: int = 0

    # 1. Check if external .ent file loading is enabled via cvar
    if False and cvar.Cvar_VariableValue("external_ents"):  # TODO remove False after fix
        mark = zone.Hunk_LowMark()

        if l.filelen > 0:
            # Calculate CRC of the internal BSP entity lump (excluding trailing null byte if present)
            end_offset = l.fileofs + max(0, l.filelen - 1)
            data_slice = mod_base[l.fileofs : end_offset]
            _crc = crc.CRC_Block(data_slice, len(data_slice))

        basemapname = common.COM_StripExtension(loadmodel.name)
        entfilename = f"{basemapname}@{_crc:04x}.ent"

        console.Con_DPrintf(f"trying to load {entfilename}\n")

        # Safely handle COM_LoadHunkFile return value
        res = common.COM_LoadHunkFile(entfilename, True)
        if res is not None:
            ents, path_id = res
            if ents:
                # Reject external entity file if it comes from a lower-priority PAK/directory
                if path_id < getattr(loadmodel, 'path_id', 0):
                    zone.Hunk_FreeToLowMark(mark)
                else:
                    loadmodel.entities = ents
                    console.Con_DPrintf(f"Loaded external entity file {entfilename}\n")
                    return

    # 2. Fallback to internal BSP entity lump if no valid external .ent file was loaded
    if not l.filelen:
        loadmodel.entities = None
        return

    # Allocate hunk memory or copy bytearray slice for internal entities
    loadmodel.entities = bytearray(mod_base[l.fileofs : l.fileofs + l.filelen])



DVERTEX_SIZE = 12  # sizeof(dvertex_t)


def Mod_LoadVertexes(l: quakedef.lump_t) -> None:
    """Parses vertex array from BSP lump into internal model memory.

    C equivalent:
    static void Mod_LoadVertexes (lump_t *l) in gl_model.c
    """
    global loadmodel, mod_base

    # 1. Validate lump size alignment against sizeof(dvertex_t)
    if l.filelen % DVERTEX_SIZE != 0:
        sys_sdl_unix.Sys_Error(
            f"MOD_LoadBmodel: funny lump size in {loadmodel.name}"
        )

    count = l.filelen // DVERTEX_SIZE

    # 2. Allocate mvertex_t runtime structures array on the model
    # C parity: out = Hunk_AllocName(count * sizeof(*out), loadname);
    loadmodel.numvertexes = count
    loadmodel.vertexes = [quakedef.mvertex_t([0., 0., 0.]) for _ in range(count)]

    # 3. Parse and unpack binary float triples (<3f = LittleEndian Float x 3)
    offset = l.fileofs
    for i in range(count):
        x, y, z = struct.unpack("<fff", mod_base[offset : offset + DVERTEX_SIZE])

        # Assign unpacked floats to mvertex_t position array
        loadmodel.vertexes[i].position[0] = x
        loadmodel.vertexes[i].position[1] = y
        loadmodel.vertexes[i].position[2] = z

        offset += DVERTEX_SIZE


DSEDGE_SIZE = 4  # sizeof(dsedge_t): 2x uint16 (standard Quake BSP)
DLEDGE_SIZE = 8  # sizeof(dledge_t): 2x uint32 (BSP2 extended format)


def Mod_LoadEdges(l: quakedef.lump_t, bsp2: int) -> None:
    """Parses edge definitions from the BSP lump into internal model memory,
    supporting both standard 16-bit edges and BSP2 32-bit edge indices.

    C equivalent:
    static void Mod_LoadEdges (lump_t *l, int bsp2) in gl_model.c
    """
    global loadmodel, mod_base

    if bsp2:
        # BSP2 format: 32-bit vertex indices (2x uint32 = 8 bytes)
        if l.filelen % DLEDGE_SIZE != 0:
            sys_sdl_unix.Sys_Error(
                f"MOD_LoadBmodel: funny lump size in {loadmodel.name}"
            )

        count = l.filelen // DLEDGE_SIZE

        # Hunk_AllocName((count + 1) * sizeof(*out), loadname)
        # Allocate count + 1 items to preserve indexing parity with sentinel padding
        loadmodel.numedges = count
        loadmodel.edges = [quakedef.medge_t() for _ in range(count + 1)]

        offset = l.fileofs
        for i in range(count):
            v0, v1 = struct.unpack("<II", mod_base[offset : offset + DLEDGE_SIZE])
            loadmodel.edges[i].v[0] = v0
            loadmodel.edges[i].v[1] = v1
            offset += DLEDGE_SIZE

    else:
        # Standard Quake BSP: 16-bit vertex indices (2x uint16 = 4 bytes)
        if l.filelen % DSEDGE_SIZE != 0:
            sys_sdl_unix.Sys_Error(
                f"MOD_LoadBmodel: funny lump size in {loadmodel.name}"
            )

        count = l.filelen // DSEDGE_SIZE

        # Hunk_AllocName((count + 1) * sizeof(*out), loadname)
        loadmodel.numedges = count
        loadmodel.edges = [quakedef.medge_t() for _ in range(count + 1)]

        offset = l.fileofs
        for i in range(count):
            v0, v1 = struct.unpack("<HH", mod_base[offset : offset + DSEDGE_SIZE])
            loadmodel.edges[i].v[0] = v0
            loadmodel.edges[i].v[1] = v1
            offset += DSEDGE_SIZE



TEXINFO_SIZE = 40  # sizeof(texinfo_t): 8 floats (vecs) + 2 int32 (miptex, flags)

# Surface flags bitfield constants
TEX_SPECIAL = 1  # Sky / Slime / Lava / Water texture flag
TEX_MISSING = 2  # Flag set when texture lookup falls back to default


def Mod_LoadTexinfo(l: quakedef.lump_t) -> None:
    """Parses surface mapping vectors (S/T texture projection) and maps texture indices
    with FitzQuake missing texture fallback bounds-checking.

    C equivalent:
    static void Mod_LoadTexinfo (lump_t *l) in gl_model.c
    """
    global loadmodel, mod_base

    # 1. Validate lump size alignment
    if l.filelen % TEXINFO_SIZE != 0:
        sys_sdl_unix.Sys_Error(
            f"MOD_LoadBmodel: funny lump size in {loadmodel.name}"
        )

    count = l.filelen // TEXINFO_SIZE

    # 2. Allocate mtexinfo_t array
    # C parity: out = (mtexinfo_t *) Hunk_AllocName ( count*sizeof(*out), loadname);
    loadmodel.numtexinfo = count
    loadmodel.texinfo = [quakedef.mtexinfo_t() for _ in range(count)]

    missing = 0
    offset = l.fileofs

    for i in range(count):
        # Unpack 8 IEEE 754 floats and 2 signed/unsigned int32s (<8fII)
        data = struct.unpack("<8fII", mod_base[offset : offset + TEXINFO_SIZE])

        out = loadmodel.texinfo[i]

        # Extract texture projection vectors S (vecs[0]) and T (vecs[1])
        out.vecs[0][0] = data[0]
        out.vecs[0][1] = data[1]
        out.vecs[0][2] = data[2]
        out.vecs[0][3] = data[3]

        out.vecs[1][0] = data[4]
        out.vecs[1][1] = data[5]
        out.vecs[1][2] = data[6]
        out.vecs[1][3] = data[7]

        miptex = data[8]
        out.flags = data[9]

        # 3. FitzQuake rewrite logic for texture index validation
        if miptex >= (loadmodel.numtextures - 1) or not loadmodel.textures[miptex]:
            if out.flags & TEX_SPECIAL:
                out.texture = loadmodel.textures[loadmodel.numtextures - 1]
            else:
                out.texture = loadmodel.textures[loadmodel.numtextures - 2]

            out.flags |= TEX_MISSING
            missing += 1
        else:
            out.texture = loadmodel.textures[miptex]

        offset += TEXINFO_SIZE

    # 4. Report missing texture count in console
    if missing and loadmodel.numtextures > 1:
        console.Con_Printf(
            f"Mod_LoadTexinfo: {missing} texture(s) missing from BSP file\n"
        )

def CalcSurfaceExtents(s: quakedef.msurface_t) -> None:
    """Calculates S/T texture coordinate bounds, lightmap origin offsets (texturemins),
    and lightmap surface dimensions (extents) for a given surface.

    C equivalent:
    void CalcSurfaceExtents (msurface_t *s) in gl_model.c
    """
    global loadmodel

    mins = [float("inf"), float("inf")]
    maxs = [-float("inf"), -float("inf")]

    tex = s.texinfo

    # 1. Iterate over face edges and compute min/max S and T projections
    for i in range(s.numedges):
        e = loadmodel.surfedges[s.firstedge + i]
        if e >= 0:
            v = loadmodel.vertexes[loadmodel.edges[e].v[0]]
        else:
            v = loadmodel.vertexes[loadmodel.edges[-e].v[1]]

        for j in range(2):
            val = (
                (float(v.position[0]) * float(tex.vecs[j][0]))
                + (float(v.position[1]) * float(tex.vecs[j][1]))
                + (float(v.position[2]) * float(tex.vecs[j][2]))
                + float(tex.vecs[j][3])
            )

            if val < mins[j]:  # noqa: PLR1730
                mins[j] = val
            if val > maxs[j]:  # noqa: PLR1730
                maxs[j] = val

    # 2. Quantize projection bounds to 16-unit lightmap block boundaries
    bmins = [0, 0]
    bmaxs = [0, 0]

    for i in range(2):
        bmins[i] = math.floor(mins[i] / 16.0)
        bmaxs[i] = math.ceil(maxs[i] / 16.0)

        s.texturemins[i] = int(bmins[i] * 16)
        s.extents[i] = int((bmaxs[i] - bmins[i]) * 16)

        # Non-sky/fluid surfaces must never exceed 2000 units (128x128 lightmap sample grid)
        if not (tex.flags & TEX_SPECIAL):
            if s.extents[i] > 2000:
                sys_sdl_unix.Sys_Error("Bad surface extents")
            if s.extents[i] < 0:
                sys_sdl_unix.Sys_Error("Bad surface extents")


VERTEXSIZE = 7  # X, Y, Z, S, T, Light_S, Light_T


def Mod_PolyForUnlitSurface(fa: quakedef.msurface_t) -> None:
    """Generates an unlit OpenGL polygon (glpoly_t) structure for non-lightmapped
    surfaces (sky, liquid surfaces, untextured fallbacks).

    C equivalent:
    static void Mod_PolyForUnlitSurface (msurface_t *fa) in gl_model.c
    """
    global loadmodel

    numverts = fa.numedges

    # Determine texture coordinate scale factor
    if fa.flags & (quakedef.SURF_DRAWTURB | quakedef.SURF_DRAWSKY):
        texscale = 1.0 / 128.0  # Warp animation pattern repeats every 128 units
    else:
        texscale = 1.0 / 32.0  # Matches r_notexture_mip pattern size

    # Allocate glpoly_t instance with flat vertex array [numverts][VERTEXSIZE]
    poly = quakedef.glpoly_t()
    poly.next = None
    fa.polys = poly
    poly.numverts = numverts
    poly.verts = [[0.0] * VERTEXSIZE for _ in range(numverts)]

    texinfo = fa.texinfo

    for i in range(numverts):
        lindex = loadmodel.surfedges[fa.firstedge + i]
        if lindex > 0:
            vec = loadmodel.vertexes[loadmodel.edges[lindex].v[0]].position
        else:
            vec = loadmodel.vertexes[loadmodel.edges[-lindex].v[1]].position

        # Copy 3D world coordinates [X, Y, Z]
        poly.verts[i][0] = float(vec[0])
        poly.verts[i][1] = float(vec[1])
        poly.verts[i][2] = float(vec[2])

        # Compute texture S and T projection scaled by surface texture scale
        s_dot = (
            (float(vec[0]) * float(texinfo.vecs[0][0]))
            + (float(vec[1]) * float(texinfo.vecs[0][1]))
            + (float(vec[2]) * float(texinfo.vecs[0][2]))
            + float(texinfo.vecs[0][3])
        )

        t_dot = (
            (float(vec[0]) * float(texinfo.vecs[1][0]))
            + (float(vec[1]) * float(texinfo.vecs[1][1]))
            + (float(vec[2]) * float(texinfo.vecs[1][2]))
            + float(texinfo.vecs[1][3])
        )

        poly.verts[i][3] = s_dot * texscale  # S coordinate (index 3)
        poly.verts[i][4] = t_dot * texscale  # T coordinate (index 4)



def Mod_CalcSurfaceBounds(s: quakedef.msurface_t):
    s.mins[0] = s.mins[1] = s.mins[2] = float('inf')
    s.maxs[0] = s.maxs[1] = s.maxs[2] = float('-inf')

    for i in range(s.numedges):
        e = loadmodel.surfedges[s.firstedge + i]
        if e >= 0:
            v = loadmodel.vertexes[loadmodel.edges[e].v[0]]
        else:
            v = loadmodel.vertexes[loadmodel.edges[-e].v[1]]

        if (s.mins[0] > v.position[0]): s.mins[0] = v.position[0]  # noqa: PLR1730
        if (s.mins[1] > v.position[1]): s.mins[1] = v.position[1] # noqa: PLR1730
        if (s.mins[2] > v.position[2]): s.mins[2] = v.position[2] # noqa: PLR1730

        if (s.maxs[0] < v.position[0]): s.maxs[0] = v.position[0] # noqa: PLR1730
        if (s.maxs[1] < v.position[1]): s.maxs[1] = v.position[1] # noqa: PLR1730
        if (s.maxs[2] < v.position[2]): s.maxs[2] = v.position[2] # noqa: PLR1730





DSFACE_SIZE = 20  # sizeof(dsface_t): standard BSP face
DLFACE_SIZE = 56  # sizeof(dlface_t): BSP2 extended face

MAXLIGHTMAPS = 4

# Surface flags (single source of truth: quakedef)
SURF_PLANEBACK = quakedef.SURF_PLANEBACK
SURF_DRAWSKY = quakedef.SURF_DRAWSKY
SURF_DRAWTURB = quakedef.SURF_DRAWTURB
SURF_DRAWTILED = quakedef.SURF_DRAWTILED
SURF_DRAWWATER = quakedef.SURF_DRAWWATER
SURF_DRAWLAVA = quakedef.SURF_DRAWLAVA
SURF_DRAWSLIME = quakedef.SURF_DRAWSLIME
SURF_DRAWTELE = quakedef.SURF_DRAWTELE
SURF_DRAWFENCE = quakedef.SURF_DRAWFENCE
SURF_NOTEXTURE = quakedef.SURF_NOTEXTURE

# BSP Version constants
BSPVERSION_QUAKE64 = 30
BSPVERSION_VALVE = 29


def Mod_LoadFaces(l: quakedef.lump_t, bsp2: bool) -> None:
    """Parses surface faces from BSP lump, builds surface bounds/extents, maps lightmap
    sample offsets, and configures rendering flags (sky, liquids, fence, missing tex).

    C equivalent:
    static void Mod_LoadFaces (lump_t *l, qboolean bsp2) in gl_model.c
    """
    global loadmodel, mod_base

    if bsp2:
        if l.filelen % DLFACE_SIZE != 0:
            sys_sdl_unix.Sys_Error(
                f"MOD_LoadBmodel: funny lump size in {loadmodel.name}"
            )
        count = l.filelen // DLFACE_SIZE
    else:
        if l.filelen % DSFACE_SIZE != 0:
            sys_sdl_unix.Sys_Error(
                f"MOD_LoadBmodel: funny lump size in {loadmodel.name}"
            )
        count = l.filelen // DSFACE_SIZE

    # FitzQuake mapper warning check
    if count > 32767 and not bsp2:
        console.Con_DWarning(
            f"{count} faces exceeds standard limit of 32767.\n"
        )

    loadmodel.numsurfaces = count
    loadmodel.surfaces = [quakedef.msurface_t() for _ in range(count)]

    offset = l.fileofs

    for surfnum in range(count):
        out = loadmodel.surfaces[surfnum]

        if bsp2:
            # dlface_t: planenum(4), side(4), firstedge(4), numedges(4), texinfo(4), styles(4), lightofs(4)
            # Unpack: <iiiii4Bi (56 bytes)
            (
                planenum,
                side,
                firstedge,
                numedges,
                texinfon,
                s0,
                s1,
                s2,
                s3,
                lofs,
            ) = struct.unpack("<iiiii4Bi", mod_base[offset : offset + DLFACE_SIZE])
            out.styles = [s0, s1, s2, s3]
            offset += DLFACE_SIZE
        else:
            # dsface_t: planenum(2), side(2), firstedge(4), numedges(2), texinfo(2), styles(4), lightofs(4)
            # Unpack: <hhihh4Bi (20 bytes)
            (
                planenum,
                side,
                firstedge,
                numedges,
                texinfon,
                s0,
                s1,
                s2,
                s3,
                lofs,
            ) = struct.unpack("<hhihh4Bi", mod_base[offset : offset + DSFACE_SIZE])
            out.styles = [s0, s1, s2, s3]
            offset += DSFACE_SIZE

        out.firstedge = firstedge
        out.numedges = numedges
        out.flags = 0

        if out.numedges < 3:
            console.Con_Warning(
                f"surfnum {surfnum}: bad numedges {out.numedges}\n"
            )

        if side:
            out.flags |= SURF_PLANEBACK

        out.plane = loadmodel.planes[planenum]
        out.texinfo = loadmodel.texinfo[texinfon]

        CalcSurfaceExtents(out)
        Mod_CalcSurfaceBounds(out)

        # Lighting info processing
        if loadmodel.bspversion == BSPVERSION_QUAKE64:
            lofs //= 2  # Q64 samples are 16-bit instead of 8-bit

        if lofs == -1 or loadmodel.lightdata is None:
            out.samples = None
        elif (
            hasattr(loadmodel, "bspversion")
            and loadmodel.bspversion == BSPVERSION_VALVE
        ):
            out.samples = lofs  # Accounts for Valve RGB byte offset directly
        else:
            # FitzQuake .lit colored lightmap multiplier parity
            out.samples = lofs * 3

        tex_name = out.texinfo.texture.name

        # 1. Sky surfaces
        if tex_name[:3].lower() == "sky":
            out.flags |= SURF_DRAWSKY | SURF_DRAWTILED
            Mod_PolyForUnlitSurface(out)

        # 2. Turbulent liquid surfaces
        elif tex_name and tex_name[0] in ("*", "!"):
            out.flags |= SURF_DRAWTURB
            if out.texinfo.flags & TEX_SPECIAL:
                out.flags |= SURF_DRAWTILED
            elif out.samples is not None and not loadmodel.haslitwater:
                console.Con_DPrintf("Map has lit water\n")
                loadmodel.haslitwater = True

            # Special liquid types categorization
            if tex_name.startswith(("*lava", "!lava")):
                out.flags |= SURF_DRAWLAVA
            elif tex_name.startswith(("*slime", "!slime")):
                out.flags |= SURF_DRAWSLIME
            elif tex_name.startswith(("*tele", "!tele")):
                out.flags |= SURF_DRAWTELE
            else:
                out.flags |= SURF_DRAWWATER

            if out.flags & SURF_DRAWTILED:
                Mod_PolyForUnlitSurface(out)
                gl_warp.GL_SubdivideSurface(out)

        # 3. Fence textures
        elif tex_name and tex_name[0] == "{":
            out.flags |= SURF_DRAWFENCE

        # 4. Missing BSP textures
        elif out.texinfo.flags & TEX_MISSING:
            if out.samples is not None:
                out.flags |= SURF_NOTEXTURE
            else:
                out.flags |= SURF_NOTEXTURE | SURF_DRAWTILED
                Mod_PolyForUnlitSurface(out)


def Mod_SetParent(
    node: quakedef.mnode_t | quakedef.mleaf_t,
    parent: quakedef.mnode_t | None
) -> None:
    """Recursively assigns parent pointers through the BSP node tree down to leaves."""
    if node is None:
        return

    node.parent = parent

    # Leaf nodes (mleaf_t) do not have child branches
    if isinstance(node, quakedef.mleaf_t):
        return

    # Process child sub-trees/leaves
    if hasattr(node, "children"):
        if node.children[0]:
            Mod_SetParent(node.children[0], node)
        if node.children[1]:
            Mod_SetParent(node.children[1], node)


def Mod_LoadNodes_S(l: quakedef.lump_t) -> None:
    global loadmodel, mod_base

    # 1. Validate lump size alignment against sizeof(dsnode_t)
    if l.filelen % DSNODE_SIZE != 0:
        sys_sdl_unix.Sys_Error(
            f"MOD_LoadBmodel: funny lump size in {loadmodel.name}"
        )

    count = l.filelen // DSNODE_SIZE

    # FitzQuake mapper warning for exceeding standard limits
    if count > 32767:
        console.Con_DWarning(
            f"{count} nodes exceeds standard limit of 32767.\n"
        )

    loadmodel.numnodes = count
    loadmodel.nodes = [quakedef.mnode_t() for _ in range(count)]

    offset = l.fileofs

    for i in range(count):
        # Unpack dsnode_t struct layout (24 bytes):
        # planenum: int32 (4)
        # children[2]: uint16 x 2 (4)  -- read as unsigned short (<HH)
        # mins[3]: int16 x 3 (6)
        # maxs[3]: int16 x 3 (6)
        # firstface: uint16 (2)
        # numfaces: uint16 (2)
        # Format string: "<iHH6hHH"
        (
            planenum,
            child0,
            child1,
            min_x,
            min_y,
            min_z,
            max_x,
            max_y,
            max_z,
            firstface,
            numfaces,
        ) = struct.unpack("<iHH6hHH", mod_base[offset : offset + DSNODE_SIZE])

        out = loadmodel.nodes[i]

        # Populate bounding box (minmaxs array: [min_x, min_y, min_z, max_x, max_y, max_z])
        out.mins[0] = float(min_x)
        out.mins[1] = float(min_y)
        out.mins[2] = float(min_z)
        out.maxs[0] = float(max_x)
        out.maxs[1] = float(max_y)
        out.maxs[2] = float(max_z)

        # Plane pointer reference
        out.plane = loadmodel.planes[planenum]

        # Explicitly cast face indices as unsigned short
        out.firstsurface = firstface
        out.numsurfaces = numfaces

        # Process left and right child pointers
        raw_children = (child0, child1)
        for j in range(2):
            p = raw_children[j]

            if p < count:
                # Pointer to internal child node (mnode_t)
                out.children[j] = loadmodel.nodes[p]
            else:
                # Bitwise complement encoding for leaf nodes (~p / 65535 - p)
                leaf_idx = 65535 - p
                if leaf_idx < loadmodel.numleafs:
                    out.children[j] = loadmodel.leafs[leaf_idx]
                else:
                    console.Con_Printf(
                        f"Mod_LoadNodes: invalid leaf index {leaf_idx} "
                        f"(file has only {loadmodel.numleafs} leafs)\n"
                    )
                    # Map out-of-bounds leaf index to solid leaf 0
                    out.children[j] = loadmodel.leafs[0]

        offset += DSNODE_SIZE








def Mod_TouchModel(name: str) -> quakedef.qmodel_t:
    mod: quakedef.qmodel_t = Mod_FindName(name)

    if not mod.needload:  # noqa: RUF100, SIM101, SIM102
        if mod.type == quakedef.modtype_t.mod_alias:  # noqa: SIM102
            if zone.Cache_Check(mod.cache) is None:
                mod.needload = True

    return mod




def Mod_PointInLeaf(p, model):
    """
    Traverses the BSP tree to find the leaf containing point p.
    p: vec3_t [x, y, z]
    model: The loaded map model object
    """
    if not model or not hasattr(model, 'nodes'):
        # Equivalent to Sys_Error
        raise RuntimeError("Mod_PointInLeaf: bad model")

    # Start at the root node
    node = model.nodes[0]

    while True:
        # In Quake, contents < 0 indicates the node is actually a leaf
        # (e.g., CONTENTS_EMPTY, CONTENTS_SOLID, CONTENTS_WATER)
        if node.contents < 0:
            return node # This is our mleaf_t

        plane = node.plane

        # Calculate the distance of point p from the plane:
        # Ax + By + Cz - D = 0
        d = mathlib.DotProduct(p, plane.normal) - plane.dist

        if d > 0:
            # Point is "in front" of the plane
            node = node.children[0]
        else:
            # Point is "behind" or on the plane
            node = node.children[1]

def Mod_DecompressVis(in_bytes, model: quakedef.qmodel_t) -> bytearray:
    """C: byte *Mod_DecompressVis (byte *in, qmodel_t *model)

    in_bytes is the compressed PVS for one leaf, starting at that leaf's visofs
    (a view onto model.visdata), or None for 'no vis data: everything visible'.
    """
    global mod_decompressed, mod_decompressed_capacity

    row = (model.numleafs + 7) >> 3

    if row > mod_decompressed_capacity:
        mod_decompressed_capacity = row
        mod_decompressed = bytearray(row)

    if not in_bytes:
        for i in range(row):
            mod_decompressed[i] = 0xFF
        return mod_decompressed

    out = 0
    pos = 0
    n = len(in_bytes)

    while out < row:
        if pos >= n:
            # truncated data: treat the remainder as not visible
            for i in range(out, row):
                mod_decompressed[i] = 0
            break

        c = in_bytes[pos]
        if c:
            mod_decompressed[out] = c
            out += 1
            pos += 1
            continue

        # zero run: next byte is the run length
        run = in_bytes[pos + 1] if pos + 1 < n else 0
        pos += 2
        while run and out < row:
            mod_decompressed[out] = 0
            out += 1
            run -= 1

    return mod_decompressed


def Mod_LeafPVS(leaf: quakedef.mleaf_t, model: quakedef.qmodel_t) -> bytearray:
    # C: if (leaf == model->leafs) -- leaf 0 is the shared "solid" leaf
    if leaf is model.leafs[0]:
        return Mod_NoVisPVS(model)
    return Mod_DecompressVis(leaf.compressed_vis, model)

def Mod_NoVisPVS(model: quakedef.qmodel_t) -> bytearray:
    global mod_novis_capacity, mod_novis

    pvsbytes = ( model.numleafs + 7 ) >> 3
    if mod_novis is None or pvsbytes > mod_novis_capacity:
        mod_novis_capacity = pvsbytes
        mod_novis = bytearray( b'\xff' * mod_novis_capacity)
    return mod_novis

def Mod_ClearAll() -> None:
    global mod_known

    for mod in mod_known:
        if mod is None:
            continue

        mod.needload = True
        gl_texmgr.TexMgr_FreeTexturesForOwner(mod)

def Mod_ResetAll() -> None:
    global mod_known, mod_numknown

    gl_mesh.GLMesh_DeleteVertexBuffers()

    for i in range(mod_numknown):
        mod = mod_known[i]
        if mod is None:
            continue

        if not mod.needload:
            gl_texmgr.TexMgr_FreeTexturesForOwner(mod)

        mod_known[i] = quakedef.qmodel_t()

    mod_numknown = 0

def Mod_Print():
    import console
    console.Con_Printf('Cached models:\n')

    for i, mod in enumerate(mod_known):
        console.Con_Printf(f'{mod.name}')

    console.Con_Printf('{i} known images in cache')


def Mod_LoadNodes_L1(l: quakedef.lump_t) -> None:
    """Parses 32-bit BSP tree nodes (dl1node_t) and links child node/leaf pointers
    using 32-bit unsigned bitwise complement leaf indexing (~p / 0xFFFFFFFF - p).

    C equivalent:
    static void Mod_LoadNodes_L1 (lump_t *l) in gl_model.c
    """
    global loadmodel, mod_base

    # 1. Validate lump size alignment against sizeof(dl1node_t)
    if l.filelen % DL1NODE_SIZE != 0:
        sys_sdl_unix.Sys_Error(
            f"Mod_LoadNodes: funny lump size in {loadmodel.name}"
        )

    count = l.filelen // DL1NODE_SIZE

    loadmodel.numnodes = count
    loadmodel.nodes = [render.mnode_t() for _ in range(count)]

    offset = l.fileofs

    for i in range(count):
        # Unpack dl1node_t struct layout (32 bytes):
        # planenum: int32 (4)
        # children[2]: int32 x 2 (8)
        # mins[3]: int16 x 3 (6)
        # maxs[3]: int16 x 3 (6)
        # firstface: int32 (4)
        # numfaces: int32 (4)
        # Format string: "<iii6hii"
        (
            planenum,
            child0,
            child1,
            min_x,
            min_y,
            min_z,
            max_x,
            max_y,
            max_z,
            firstface,
            numfaces,
        ) = struct.unpack("<iii6hii", mod_base[offset : offset + DL1NODE_SIZE])

        out = loadmodel.nodes[i]

        # Populate bounding box (minmaxs array: [min_x, min_y, min_z, max_x, max_y, max_z])
        out.minmaxs[0] = float(min_x)
        out.minmaxs[1] = float(min_y)
        out.minmaxs[2] = float(min_z)
        out.minmaxs[3] = float(max_x)
        out.minmaxs[4] = float(max_y)
        out.minmaxs[5] = float(max_z)

        # Plane pointer reference
        out.plane = loadmodel.planes[planenum]

        # Surface range mapping
        out.firstsurface = firstface
        out.numsurfaces = numfaces

        # Process left and right 32-bit child pointers
        raw_children = (child0, child1)
        for j in range(2):
            p = raw_children[j]

            if p >= 0 and p < count:
                # Pointer to internal child node (mnode_t)
                out.children[j] = loadmodel.nodes[p]
            else:
                # Bitwise complement encoding for 32-bit leaf nodes (~p / 0xFFFFFFFF - p)
                leaf_idx = 0xFFFFFFFF - p
                if leaf_idx >= 0 and leaf_idx < loadmodel.numleafs:
                    out.children[j] = loadmodel.leafs[leaf_idx]
                else:
                    console.Con_Printf(
                        f"Mod_LoadNodes: invalid leaf index {leaf_idx} "
                        f"(file has only {loadmodel.numleafs} leafs)\n"
                    )
                    # Map out-of-bounds leaf index to solid leaf 0
                    out.children[j] = loadmodel.leafs[0]

        offset += DL1NODE_SIZE


def Mod_LoadNodes_L2(l: quakedef.lump_t) -> None:
    """Parses 32-bit floating-point BSP tree nodes (dl2node_t) and links child node/leaf
    pointers using 32-bit unsigned bitwise complement leaf indexing (~p / 0xFFFFFFFF - p).

    C equivalent:
    static void Mod_LoadNodes_L2 (lump_t *l) in gl_model.c
    """
    global loadmodel, mod_base

    # 1. Validate lump size alignment against sizeof(dl2node_t)
    if l.filelen % DL2NODE_SIZE != 0:
        sys_sdl_unix.Sys_Error(
            f"Mod_LoadNodes: funny lump size in {loadmodel.name}"
        )

    count = l.filelen // DL2NODE_SIZE

    loadmodel.numnodes = count
    loadmodel.nodes = [render.mnode_t() for _ in range(count)]

    offset = l.fileofs

    for i in range(count):
        # Unpack dl2node_t struct layout (44 bytes):
        # planenum: int32 (4)
        # children[2]: int32 x 2 (8)
        # mins[3]: float32 x 3 (12)
        # maxs[3]: float32 x 3 (12)
        # firstface: int32 (4)
        # numfaces: int32 (4)
        # Format string: "<iii6fii"
        (
            planenum,
            child0,
            child1,
            min_x,
            min_y,
            min_z,
            max_x,
            max_y,
            max_z,
            firstface,
            numfaces,
        ) = struct.unpack("<iii6fii", mod_base[offset : offset + DL2NODE_SIZE])

        out = loadmodel.nodes[i]

        # Populate bounding box with float values directly
        out.minmaxs[0] = min_x
        out.minmaxs[1] = min_y
        out.minmaxs[2] = min_z
        out.minmaxs[3] = max_x
        out.minmaxs[4] = max_y
        out.minmaxs[5] = max_z

        # Plane pointer reference
        out.plane = loadmodel.planes[planenum]

        # Surface range mapping
        out.firstsurface = firstface
        out.numsurfaces = numfaces

        # Process left and right 32-bit child pointers
        raw_children = (child0, child1)
        for j in range(2):
            p = raw_children[j]

            # Strict L2 node check: p > 0 (prevents node 0 root-looping recursion)
            if p > 0 and p < count:
                # Pointer to internal child node (mnode_t)
                out.children[j] = loadmodel.nodes[p]
            else:
                # Bitwise complement encoding for 32-bit leaf nodes (~p / 0xFFFFFFFF - p)
                leaf_idx = 0xFFFFFFFF - p
                if leaf_idx >= 0 and leaf_idx < loadmodel.numleafs:
                    out.children[j] = loadmodel.leafs[leaf_idx]
                else:
                    console.Con_Printf(
                        f"Mod_LoadNodes: invalid leaf index {leaf_idx} "
                        f"(file has only {loadmodel.numleafs} leafs)\n"
                    )
                    # Map out-of-bounds leaf index to solid leaf 0
                    out.children[j] = loadmodel.leafs[0]

        offset += DL2NODE_SIZE

def Mod_LoadNodes(l:quakedef.lump_t, bsp2: int):
    if bsp2 == 2:
        Mod_LoadNodes_L2(l)
    elif bsp2:
        Mod_LoadNodes_L1(l)
    else:
        Mod_LoadNodes_S(l)

    Mod_SetParent(loadmodel.nodes[0], None)


def Mod_ProcessLeafs_S(l: quakedef.lump_t) -> None:
    """Parses standard 28-byte BSP leaf structures (dsleaf_t) with FitzQuake's 32,767 leaf safety limit check.

    C equivalent:
    static void Mod_ProcessLeafs_S (dsleaf_t *in, int filelen) in gl_model.c
    """
    global loadmodel, mod_base

    # 1. Validate lump size alignment against sizeof(dsleaf_t)
    if l.filelen % DSLEAF_SIZE != 0:
        sys_sdl_unix.Sys_Error(
            f"Mod_ProcessLeafs: funny lump size in {loadmodel.name}"
        )

    count = l.filelen // DSLEAF_SIZE

    # johnfitz -- enforce 16-bit signed limit for standard BSP leaf counts
    if count > 32767:
        host.Host_Error(
            f"Mod_LoadLeafs: {count} leafs exceeds limit of 32767."
        )

    # Allocate mleaf_t array under quakedef
    loadmodel.numleafs = count
    loadmodel.leafs = [quakedef.mleaf_t() for _ in range(count)]

    offset = l.fileofs

    for i in range(count):
        # Unpack dsleaf_t struct layout (28 bytes):
        # contents: int32 (4)
        # visofs: int32 (4)
        # mins[3]: int16 x 3 (6)
        # maxs[3]: int16 x 3 (6)
        # firstmarksurface: uint16 (2)
        # nummarksurfaces: uint16 (2)
        # ambient_level[4]: uint8 x 4 (4)
        (
            contents,
            visofs,
            min_x,
            min_y,
            min_z,
            max_x,
            max_y,
            max_z,
            firstmarksurface,
            nummarksurfaces,
            amb0,
            amb1,
            amb2,
            amb3,
        ) = struct.unpack("<ii6hHH4B", mod_base[offset : offset + DSLEAF_SIZE])

        out = loadmodel.leafs[i]

        out.minmaxs[0] = float(min_x)
        out.minmaxs[1] = float(min_y)
        out.minmaxs[2] = float(min_z)
        out.minmaxs[3] = float(max_x)
        out.minmaxs[4] = float(max_y)
        out.minmaxs[5] = float(max_z)

        out.contents = contents

        out.firstmarksurface_index = firstmarksurface
        out.nummarksurfaces = nummarksurfaces
        if loadmodel.marksurfaces:
            out.firstmarksurface = loadmodel.marksurfaces[firstmarksurface:]
        else:
            out.firstmarksurface = []

        if visofs == -1:
            out.compressed_vis = None
        else:
            out.compressed_vis = (memoryview(loadmodel.visdata)[visofs:] if loadmodel.visdata else None)  # zero-copy view, like C's pointer

        out.efrags = None

        out.ambient_sound_level = [amb0, amb1, amb2, amb3]

        offset += DSLEAF_SIZE

def Mod_LoadLeafs_S(l: quakedef.lump_t) -> None:
    """Parses standard 28-byte BSP leaf structures (dsleaf_t) into quakedef.mleaf_t instances.

    C equivalent:
    static void Mod_LoadLeafs_S (lump_t *l) in gl_model.c
    """
    global loadmodel, mod_base

    # 1. Validate lump size alignment against sizeof(dsleaf_t)
    if l.filelen % DSLEAF_SIZE != 0:
        sys_sdl_unix.Sys_Error(
            f"Mod_LoadLeafs: funny lump size in {loadmodel.name}"
        )

    count = l.filelen // DSLEAF_SIZE

    # Allocate mleaf_t array under quakedef
    loadmodel.numleafs = count
    loadmodel.leafs = [quakedef.mleaf_t() for _ in range(count)]

    offset = l.fileofs

    for i in range(count):
        # Unpack dsleaf_t struct layout (28 bytes):
        # contents: int32 (4)
        # visofs: int32 (4)
        # mins[3]: int16 x 3 (6)
        # maxs[3]: int16 x 3 (6)
        # firstmarksurface: uint16 (2)
        # nummarksurfaces: uint16 (2)
        # ambient_level[4]: uint8 x 4 (4)
        # Format string: "<ii6hHH4B"
        (
            contents,
            visofs,
            min_x,
            min_y,
            min_z,
            max_x,
            max_y,
            max_z,
            firstmarksurface,
            nummarksurfaces,
            amb0,
            amb1,
            amb2,
            amb3,
        ) = struct.unpack("<ii6hHH4B", mod_base[offset : offset + DSLEAF_SIZE])

        out = loadmodel.leafs[i]

        # Populate minmaxs array [min_x, min_y, min_z, max_x, max_y, max_z]
        out.minmaxs[0] = float(min_x)
        out.minmaxs[1] = float(min_y)
        out.minmaxs[2] = float(min_z)
        out.minmaxs[3] = float(max_x)
        out.minmaxs[4] = float(max_y)
        out.minmaxs[5] = float(max_z)

        out.contents = contents

        # Link firstmarksurface pointer offset into loadmodel.marksurfaces slice
        out.firstmarksurface_index = firstmarksurface
        out.nummarksurfaces = nummarksurfaces
        if loadmodel.marksurfaces:
            out.firstmarksurface = loadmodel.marksurfaces[firstmarksurface:]
        else:
            out.firstmarksurface = []

        # Resolve compressed PVS visdata pointer
        if visofs == -1:
            out.compressed_vis = None
        else:
            # Memory view/slice into loadmodel.visdata
            out.compressed_vis = (memoryview(loadmodel.visdata)[visofs:] if loadmodel.visdata else None)  # zero-copy view, like C's pointer

        # Entity fragments initialized to None
        out.efrags = None

        # Ambient sound levels (4 bytes)
        out.ambient_sound_level = [amb0, amb1, amb2, amb3]

        offset += DSLEAF_SIZE




def Mod_ProcessLeafs_L1(l: quakedef.lump_t) -> None:
    """Parses 32-bit BSP1/L1 leaf structures (dl1leaf_t) into quakedef.mleaf_t instances.

    C equivalent:
    static void Mod_ProcessLeafs_L1 (dl1leaf_t *in, int filelen) in gl_model.c
    """
    global loadmodel, mod_base

    # 1. Validate lump size alignment against sizeof(dl1leaf_t)
    if l.filelen % DL1LEAF_SIZE != 0:
        sys_sdl_unix.Sys_Error(
            f"Mod_ProcessLeafs: funny lump size in {loadmodel.name}"
        )

    count = l.filelen // DL1LEAF_SIZE

    # Allocate mleaf_t array under quakedef
    loadmodel.numleafs = count
    loadmodel.leafs = [quakedef.mleaf_t() for _ in range(count)]

    offset = l.fileofs

    for i in range(count):
        # Unpack dl1leaf_t struct layout (32 bytes):
        # contents: int32 (4)
        # visofs: int32 (4)
        # mins[3]: int16 x 3 (6)
        # maxs[3]: int16 x 3 (6)
        # firstmarksurface: int32 (4)
        # nummarksurfaces: int32 (4)
        # ambient_level[4]: uint8 x 4 (4)
        # Format string: "<ii6hii4B"
        (
            contents,
            visofs,
            min_x,
            min_y,
            min_z,
            max_x,
            max_y,
            max_z,
            firstmarksurface,
            nummarksurfaces,
            amb0,
            amb1,
            amb2,
            amb3,
        ) = struct.unpack("<ii6hii4B", mod_base[offset : offset + DL1LEAF_SIZE])

        out = loadmodel.leafs[i]

        # Populate minmaxs float array
        out.minmaxs[0] = float(min_x)
        out.minmaxs[1] = float(min_y)
        out.minmaxs[2] = float(min_z)
        out.minmaxs[3] = float(max_x)
        out.minmaxs[4] = float(max_y)
        out.minmaxs[5] = float(max_z)

        out.contents = contents

        # Link 32-bit firstmarksurface offset into loadmodel.marksurfaces slice
        out.firstmarksurface_index = firstmarksurface
        out.nummarksurfaces = nummarksurfaces
        if loadmodel.marksurfaces:
            out.firstmarksurface = loadmodel.marksurfaces[firstmarksurface:]
        else:
            out.firstmarksurface = []

        # Resolve compressed PVS visdata pointer
        if visofs == -1:
            out.compressed_vis = None
        else:
            out.compressed_vis = (memoryview(loadmodel.visdata)[visofs:] if loadmodel.visdata else None)  # zero-copy view, like C's pointer

        # Entity fragments initialized to None
        out.efrags = None

        # Ambient sound levels (4 bytes)
        out.ambient_sound_level = [amb0, amb1, amb2, amb3]

        offset += DL1LEAF_SIZE


def Mod_ProcessLeafs_L2(l: quakedef.lump_t) -> None:
    """Parses 32-bit floating-point BSP2/L2 leaf structures (dl2leaf_t) into quakedef.mleaf_t instances.

    C equivalent:
    static void Mod_ProcessLeafs_L2 (dl2leaf_t *in, int filelen) in gl_model.c
    """
    global loadmodel, mod_base

    # 1. Validate lump size alignment against sizeof(dl2leaf_t)
    if l.filelen % DL2LEAF_SIZE != 0:
        sys_sdl_unix.Sys_Error(
            f"Mod_ProcessLeafs: funny lump size in {loadmodel.name}"
        )

    count = l.filelen // DL2LEAF_SIZE

    # Allocate mleaf_t array under quakedef
    loadmodel.numleafs = count
    loadmodel.leafs = [quakedef.mleaf_t() for _ in range(count)]

    offset = l.fileofs

    for i in range(count):
        # Unpack dl2leaf_t struct layout (44 bytes):
        # contents: int32 (4)
        # visofs: int32 (4)
        # mins[3]: float32 x 3 (12)
        # maxs[3]: float32 x 3 (12)
        # firstmarksurface: int32 (4)
        # nummarksurfaces: int32 (4)
        # ambient_level[4]: uint8 x 4 (4)
        # Format string: "<ii6fii4B"
        (
            contents,
            visofs,
            min_x,
            min_y,
            min_z,
            max_x,
            max_y,
            max_z,
            firstmarksurface,
            nummarksurfaces,
            amb0,
            amb1,
            amb2,
            amb3,
        ) = struct.unpack("<ii6fii4B", mod_base[offset : offset + DL2LEAF_SIZE])

        out = loadmodel.leafs[i]

        # Populate minmaxs float array directly (no int-to-float cast required)
        out.minmaxs[0] = min_x
        out.minmaxs[1] = min_y
        out.minmaxs[2] = min_z
        out.minmaxs[3] = max_x
        out.minmaxs[4] = max_y
        out.minmaxs[5] = max_z

        out.contents = contents

        # Link 32-bit firstmarksurface offset into loadmodel.marksurfaces slice
        out.firstmarksurface_index = firstmarksurface
        out.nummarksurfaces = nummarksurfaces
        if loadmodel.marksurfaces:
            out.firstmarksurface = loadmodel.marksurfaces[firstmarksurface:]
        else:
            out.firstmarksurface = []

        # Resolve compressed PVS visdata pointer
        if visofs == -1:
            out.compressed_vis = None
        else:
            out.compressed_vis = (memoryview(loadmodel.visdata)[visofs:] if loadmodel.visdata else None)  # zero-copy view, like C's pointer

        # Entity fragments initialized to None
        out.efrags = None

        # Ambient sound levels (4 bytes)
        out.ambient_sound_level = [amb0, amb1, amb2, amb3]

        offset += DL2LEAF_SIZE


def Mod_LoadLeafs(l: quakedef.lump_t, bsp2: int) -> None:
    """Main lump dispatch routine."""
    if bsp2 == 2:
        Mod_ProcessLeafs_L2(l)
    elif bsp2:
        Mod_ProcessLeafs_L1(l)
    else:
        Mod_ProcessLeafs_S(l)



def Mod_LoadClipnodes(l: quakedef.lump_t, bsp2: bool) -> None:
    """Parses BSP collision clipnodes and initializes collision hulls 1 and 2.

    C equivalent:
    static void Mod_LoadClipnodes (lump_t *l, qboolean bsp2) in gl_model.c
    """
    global loadmodel, mod_base

    if bsp2:
        if l.filelen % DLCLIPNODE_SIZE != 0:
            sys_sdl_unix.Sys_Error(
                f"Mod_LoadClipnodes: funny lump size in {loadmodel.name}"
            )
        count = l.filelen // DLCLIPNODE_SIZE
    else:
        if l.filelen % DSCLIPNODE_SIZE != 0:
            sys_sdl_unix.Sys_Error(
                f"Mod_LoadClipnodes: funny lump size in {loadmodel.name}"
            )
        count = l.filelen // DSCLIPNODE_SIZE

    # Allocate mclipnode_t array
    out_nodes = [quakedef.mclipnode_t() for _ in range(count)]

    # johnfitz -- warn about exceeding old limits
    if count > 32767 and not bsp2:
        console.Con_DWarning(
            f"{count} clipnodes exceeds standard limit of 32767.\n"
        )

    loadmodel.clipnodes = out_nodes
    loadmodel.numclipnodes = count

    # Set up Hull 1 (Human size: 32x32x56 box)
    hull1 = loadmodel.hulls[1]
    hull1.clipnodes = out_nodes
    hull1.firstclipnode = 0
    hull1.lastclipnode = count - 1
    hull1.planes = loadmodel.planes
    hull1.clip_mins = [-16.0, -16.0, -24.0]
    hull1.clip_maxs = [16.0, 16.0, 32.0]

    # Set up Hull 2 (Large / Shambler / Player-in-vehicle size: 64x64x88 box)
    hull2 = loadmodel.hulls[2]
    hull2.clipnodes = out_nodes
    hull2.firstclipnode = 0
    hull2.lastclipnode = count - 1
    hull2.planes = loadmodel.planes
    hull2.clip_mins = [-32.0, -32.0, -24.0]
    hull2.clip_maxs = [32.0, 32.0, 64.0]

    offset = l.fileofs

    if bsp2:
        for i in range(count):
            # Format: planenum (int32), child0 (int32), child1 (int32)
            planenum, child0, child1 = struct.unpack(
                "<iii", mod_base[offset : offset + DLCLIPNODE_SIZE]
            )

            out = out_nodes[i]
            out.planenum = planenum

            # johnfitz -- bounds check
            if out.planenum < 0 or out.planenum >= loadmodel.numplanes:
                host.Host_Error("Mod_LoadClipnodes: planenum out of bounds")

            out.children[0] = child0
            out.children[1] = child1

            offset += DLCLIPNODE_SIZE
    else:
        for i in range(count):
            # Format: planenum (int32), child0 (uint16), child1 (uint16)
            planenum, child0, child1 = struct.unpack(
                "<iHH", mod_base[offset : offset + DSCLIPNODE_SIZE]
            )

            out = out_nodes[i]
            out.planenum = planenum

            # johnfitz -- bounds check
            if out.planenum < 0 or out.planenum >= loadmodel.numplanes:
                host.Host_Error("Mod_LoadClipnodes: planenum out of bounds")

            # johnfitz -- support clipnodes > 32k
            out.children[0] = child0
            out.children[1] = child1

            if out.children[0] >= count:
                out.children[0] -= 65536
            if out.children[1] >= count:
                out.children[1] -= 65536

            offset += DSCLIPNODE_SIZE

def Mod_MakeHull0() -> None:
    """Generates Hull 0 (point-trace collision hull) from the existing BSP render node tree.

    C equivalent:
    static void Mod_MakeHull0 (void) in gl_model.c
    """
    global loadmodel

    hull = loadmodel.hulls[0]
    count = loadmodel.numnodes

    # Allocate clipnode structures matching node count
    out_nodes = [quakedef.mclipnode_t() for _ in range(count)]

    hull.clipnodes = out_nodes
    hull.firstclipnode = 0
    hull.lastclipnode = count - 1
    hull.planes = loadmodel.planes

    # Create mapping dictionaries to emulate C pointer arithmetic:
    # (ptr - base_ptr) -> index
    plane_to_index = {
        id(plane): idx for idx, plane in enumerate(loadmodel.planes)
    }
    node_to_index = {id(node): idx for idx, node in enumerate(loadmodel.nodes)}

    for i in range(count):
        in_node = loadmodel.nodes[i]
        out_clip = out_nodes[i]

        # Calculate plane index: in->plane - loadmodel->planes
        out_clip.planenum = plane_to_index[id(in_node.plane)]

        # Traverse left/right children (j = 0, 1)
        for j in range(2):
            child = in_node.children[j]

            # If child is a leaf (contents < 0), store the negative CONTENTS_* flag directly
            if child.contents < 0:
                out_clip.children[j] = child.contents
            else:
                # Calculate node index: child - loadmodel->nodes
                out_clip.children[j] = node_to_index[id(child)]



def Mod_LoadMarksurfaces(l: quakedef.lump_t, bsp2: bool) -> None:
    """Loads BSP marksurfaces (leaf-to-surface reference array).

    C equivalent:
    static void Mod_LoadMarksurfaces (lump_t *l, int bsp2) in gl_model.c
    """
    global loadmodel, mod_base

    offset = l.fileofs

    if bsp2:
        entry_size = 4  # sizeof(unsigned int)
        if l.filelen % entry_size != 0:
            host.Host_Error(
                f"Mod_LoadMarksurfaces: funny lump size in {loadmodel.name}"
            )

        count = l.filelen // entry_size
        out_surfaces = [None] * count

        loadmodel.marksurfaces = out_surfaces
        loadmodel.nummarksurfaces = count

        for i in range(count):
            (j,) = struct.unpack(
                "<I", mod_base[offset : offset + entry_size]
            )

            if j >= loadmodel.numsurfaces:
                host.Host_Error("Mod_LoadMarksurfaces: bad surface number")

            # out[i] = loadmodel->surfaces + j
            out_surfaces[i] = loadmodel.surfaces[j]
            offset += entry_size

    else:
        entry_size = 2  # sizeof(short)
        if l.filelen % entry_size != 0:
            host.Host_Error(
                f"Mod_LoadMarksurfaces: funny lump size in {loadmodel.name}"
            )

        count = l.filelen // entry_size
        out_surfaces = [None] * count

        loadmodel.marksurfaces = out_surfaces
        loadmodel.nummarksurfaces = count

        # johnfitz -- warn mappers about exceeding old limits
        if count > 32767:
            console.Con_DWarning(
                f"{count} marksurfaces exceeds standard limit of 32767.\n"
            )

        for i in range(count):
            # johnfitz -- explicit cast as unsigned short ("<H")
            (j,) = struct.unpack(
                "<H", mod_base[offset : offset + entry_size]
            )

            if j >= loadmodel.numsurfaces:
                sys_sdl_unix.Sys_Error(
                    "Mod_LoadMarksurfaces: bad surface number"
                )

            # out[i] = loadmodel->surfaces + j
            out_surfaces[i] = loadmodel.surfaces[j]
            offset += entry_size


def Mod_LoadSurfedges(l: quakedef.lump_t) -> None:
    """Loads BSP surfedges (signed edge indices mapping face contours to global edges).

    C equivalent:
    static void Mod_LoadSurfedges (lump_t *l) in gl_model.c
    """
    global loadmodel, mod_base

    # 1. Validate lump size alignment against sizeof(int)
    if l.filelen % INT_SIZE != 0:
        sys_sdl_unix.Sys_Error(
            f"MOD_LoadBmodel: funny lump size in {loadmodel.name}"
        )

    count = l.filelen // INT_SIZE

    # Allocate integer array for surfedges
    out = [0] * count

    loadmodel.surfedges = out
    loadmodel.numsurfedges = count

    offset = l.fileofs

    # Read array of 32-bit signed integers (LittleLong handling via '<i')
    for i in range(count):
        (surfedge,) = struct.unpack("<i", mod_base[offset : offset + INT_SIZE])
        out[i] = surfedge
        offset += INT_SIZE


def Mod_LoadPlanes(l: quakedef.lump_t) -> None:
    """Loads world planes and calculates signbits for fast box-side evaluation.

    C equivalent:
    static void Mod_LoadPlanes (lump_t *l) in gl_model.c
    """
    global loadmodel, mod_base

    # Validate lump size alignment
    if l.filelen % DPLANE_SIZE != 0:
        sys_sdl_unix.Sys_Error(
            f"MOD_LoadBmodel: funny lump size in {loadmodel.name}"
        )

    count = l.filelen // DPLANE_SIZE

    # Allocate mplane_t array

    out_planes = [
        quakedef.mplane_t(
            normal=[0.0, 0.0, 0.0],
            dist=0.0,
            _type=0,
            signbits=0,
        )
        for _ in range(count)
    ]

    loadmodel.planes = out_planes
    loadmodel.numplanes = count

    offset = l.fileofs

    for i in range(count):
        # Format: normal[3] (3x float), dist (float), type (int32)
        nx, ny, nz, dist, plane_type = struct.unpack(
            "<ffffi", mod_base[offset : offset + DPLANE_SIZE]
        )

        out = out_planes[i]
        out.normal = [nx, ny, nz]
        out.dist = dist
        out.type = plane_type

        # Calculate signbits for axial optimization
        bits = 0
        for j in range(3):
            if out.normal[j] < 0:
                bits |= 1 << j

        out.signbits = bits

        offset += DPLANE_SIZE

def RadiusFromBounds(mins:list[float], maxs:list[float]) -> float:
    corner: list[float] = [0, 0, 0]
    for i in range(3):
        corner[i] = math.fabs(mins[i]) if math.fabs(mins[i]) > math.fabs(maxs[i]) else math.fabs(maxs[i])  # noqa: FURB136

    return mathlib.VectorLength(corner)



def Mod_LoadSubmodels(l: quakedef.lump_t) -> None:
    """Loads BSP submodels (inline models such as moving doors, lifts, and worldspawn).

    C equivalent:
    static void Mod_LoadSubmodels (lump_t *l) in gl_model.c
    """
    global loadmodel, mod_base

    # 1. Validate lump size alignment against sizeof(dmodel_t)
    if l.filelen % DMODEL_SIZE != 0:
        sys_sdl_unix.Sys_Error(
            f"MOD_LoadBmodel: funny lump size in {loadmodel.name}"
        )

    count = l.filelen // DMODEL_SIZE

    # Allocate array of dmodel_t structures under quakedef
    out_submodels = [quakedef.dmodel_t() for _ in range(count)]

    loadmodel.submodels = out_submodels
    loadmodel.numsubmodels = count

    offset = l.fileofs

    for i in range(count):
        # Unpack dmodel_t binary layout (64 bytes):
        # mins[3]: float32 x 3 (12)
        # maxs[3]: float32 x 3 (12)
        # origin[3]: float32 x 3 (12)
        # headnode[4]: int32 x 4 (16)
        # visleafs: int32 (4)
        # firstface: int32 (4)
        # numfaces: int32 (4)
        # Format string: "<9f7i"
        (
            min_x,
            min_y,
            min_z,
            max_x,
            max_y,
            max_z,
            org_x,
            org_y,
            org_z,
            h0,
            h1,
            h2,
            h3,
            visleafs,
            firstface,
            numfaces,
        ) = struct.unpack("<9f7i", mod_base[offset : offset + DMODEL_SIZE])

        out = out_submodels[i]

        # Spread mins and maxs by 1 unit
        out.mins = [min_x - 1.0, min_y - 1.0, min_z - 1.0]
        out.maxs = [max_x + 1.0, max_y + 1.0, max_z + 1.0]
        out.origin = [org_x, org_y, org_z]

        out.headnode = [h0, h1, h2, h3]
        out.visleafs = visleafs
        out.firstface = firstface
        out.numfaces = numfaces

        # Calculate bounding sphere radius
        out.radius = RadiusFromBounds(out.mins, out.maxs)

        offset += DMODEL_SIZE

    # johnfitz -- check world visleafs -- adapted from bjp
    world_model = loadmodel.submodels[0]
    if world_model.visleafs > 8192:
        console.Con_DWarning(
            f"{world_model.visleafs} visleafs exceeds standard limit of 8192.\n"
        )


def Mod_FindVisibilityExternal() -> typing.Optional[typing.BinaryIO]:
    """Searches for external visibility patch files (.vis) matching the current model.

    Returns an open file handle positioned right after the header if found, or None.

    C equivalent:
    static FILE *Mod_FindVisibilityExternal(void) in gl_model.c
    """
    global loadmodel, loadname, com_gamedir

    # 1. First attempt: maps/<loadname>.vis
    visfilename = f"maps/{loadname}.vis"
    ret, f, path_id = common.COM_FOpenFile(visfilename)

    if ret < 0:
        console.Con_DPrintf(f"{visfilename} not found, trying ")
        gamedir_short = common.COM_SkipPath(com_gamedir)
        visfilename = f"{gamedir_short}.vis"
        console.Con_DPrintf(f"{visfilename}\n")

        ret, f, path_id = common.COM_FOpenFile(visfilename)
        if ret < 0:
            console.Con_DPrintf("external vis not found\n")
            return None

    # Verify search path priority
    if path_id < loadmodel.path_id:
        f.close()
        console.Con_DPrintf(
            f"ignored {visfilename} from a gamedir with lower priority\n"
        )
        return None

    console.Con_DPrintf(f"Found external VIS {visfilename}\n")

    shortname = common.COM_SkipPath(loadmodel.name).lower()
    pos = 0

    while True:
        f.seek(pos, os.SEEK_SET)
        header_data = f.read(quakedef.VISPATCH_HEADER_LEN)

        if len(header_data) != quakedef.VISPATCH_HEADER_LEN:
            f.close()
            console.Con_DPrintf(f"{shortname} not found in {visfilename}\n")
            return None

        # Unpack header: mapname (32 bytes null-padded string), filelen (int32)
        mapname_raw, filelen = struct.unpack("<32si", header_data[:36])
        mapname = mapname_raw.decode("ascii", errors="ignore").rstrip("\x00")

        if filelen <= 0:  # Bad entry -- don't trust the rest
            f.close()
            return None

        if mapname.lower() == shortname:
            # File pointer is left positioned immediately after the header
            return f

        pos += filelen + quakedef.VISPATCH_HEADER_LEN


def Mod_LoadVisibilityExternal( f: io.BinaryIO,) -> bytearray | None:
    """Reads external visibility payload from an open file handle positioned at the entry length header.

    C equivalent:
    static byte *Mod_LoadVisibilityExternal (FILE *f) in gl_model.c
    """
    # 1. Read 4-byte integer length prefix
    header = f.read(4)
    if len(header) < 4:
        return None

    # Unpack Little-Endian 32-bit signed integer
    (filelen,) = struct.unpack("<i", header)

    if filelen <= 0:
        return None

    console.Con_DPrintf(f"...{filelen} bytes visibility data\n")

    # 2. Read full visibility byte payload
    visdata = bytearray(f.read(filelen))

    # Verify complete read matching expected filelen
    if len(visdata) < filelen:
        return None

    return visdata

def Mod_LoadLeafsExternal(f: typing.BinaryIO) -> None:
    """Reads external leaf data from a VIS patch file and processes it via Mod_ProcessLeafs_S.

    C equivalent:
    static void Mod_LoadLeafsExternal(FILE* f) in gl_model.c
    """
    # 1. Read 4-byte integer length header
    header = f.read(4)
    if len(header) < 4:
        return

    # Unpack Little-Endian 32-bit signed integer
    (filelen,) = struct.unpack("<i", header)

    if filelen <= 0:
        return

    console.Con_DPrintf(f"...{filelen} bytes leaf data\n")

    # 2. Read full leaf buffer payload
    raw_leafs = f.read(filelen)
    if len(raw_leafs) < filelen:
        return

    # Pass raw bytes buffer to leaf processing routine
    Mod_ProcessLeafs_S(raw_leafs, filelen)



# BSP Versions
BSPVERSION = 29
BSPVERSION_VALVE = 30
BSP2VERSION_2PSB = struct.unpack("<I", b"2PSB")[0]  # 0x42535032 ('2PSB')
BSP2VERSION_BSP2 = struct.unpack("<I", b"BSP2")[0]  # 0x32505342 ('BSP2')
BSPVERSION_QUAKE64 = 3

# Lump Indices
LUMP_ENTITIES = 0
LUMP_PLANES = 1
LUMP_TEXTURES = 2
LUMP_VERTEXES = 3
LUMP_VISIBILITY = 4
LUMP_NODES = 5
LUMP_TEXINFO = 6
LUMP_FACES = 7
LUMP_LIGHTING = 8
LUMP_CLIPNODES = 9
LUMP_LEAFS = 10
LUMP_MARKSURFACES = 11
LUMP_EDGES = 12
LUMP_SURFEDGES = 13
LUMP_MODELS = 14
HEADER_LUMPS = 15


def Mod_LoadBrushModel(mod: quakedef.model_t, buffer: bytes) -> None:
    """Loads a BSP brush model into the engine, unpacking lumps and instantiating submodels.

    C equivalent:
    static void Mod_LoadBrushModel (model_t *mod, void *buffer) in gl_model.c
    """
    global loadmodel, loadname, mod_base, sv, external_vis

    loadmodel = mod
    loadmodel.type = quakedef.modtype_t.mod_brush

    # Parse 4-byte little-endian header version
    (version,) = struct.unpack("<i", buffer[:4])
    mod.bspversion = version

    # Evaluate BSP variation format
    if mod.bspversion == BSPVERSION:
        bsp2 = 0
    elif mod.bspversion == BSPVERSION_VALVE:
        bsp2 = 0
    elif mod.bspversion == BSP2VERSION_2PSB:
        bsp2 = 1  # First iteration BSP2
    elif mod.bspversion == BSP2VERSION_BSP2:
        bsp2 = 2  # Sanitized revision BSP2
    elif mod.bspversion == BSPVERSION_QUAKE64:
        bsp2 = 0
    else:
        sys_sdl_unix.Sys_Error(
            f"Mod_LoadBrushModel: {mod.name} has unsupported version number ({mod.bspversion})"
        )

    mod_base = bytearray(buffer)

    # Convert the dheader_t array from little-endian integers (version + 15 lump pairs = 31 ints)
    header_ints = list(struct.unpack("<31i", mod_base[:124]))
    header = quakedef.dheader_t()
    header.version = header_ints[0]

    # Populate lump tables (offset, length)
    header.lumps = []
    for i in range(HEADER_LUMPS):
        lump = quakedef.lump_t( fileofs = header_ints[1 + i * 2], filelen = header_ints[2 + i * 2] )
        header.lumps.append(lump)

    # Load geometry, topology, material, and visibility lumps
    Mod_LoadVertexes(header.lumps[LUMP_VERTEXES])
    Mod_LoadEdges(header.lumps[LUMP_EDGES], bsp2)
    Mod_LoadSurfedges(header.lumps[LUMP_SURFEDGES])
    Mod_LoadEntities(header.lumps[LUMP_ENTITIES])
    Mod_LoadTextures(header.lumps[LUMP_TEXTURES])
    Mod_LoadLighting(header.lumps[LUMP_LIGHTING])
    Mod_LoadPlanes(header.lumps[LUMP_PLANES])
    Mod_LoadTexinfo(header.lumps[LUMP_TEXINFO])
    Mod_LoadFaces(header.lumps[LUMP_FACES], bsp2)
    Mod_LoadMarksurfaces(header.lumps[LUMP_MARKSURFACES], bsp2)

    # Attempt loading external VIS overrides if enabled
    vis_loaded = False
    if (
        mod.bspversion == BSPVERSION
        and cvar.Cvar_GetCvar('external_vis').value
        and sv_main.sv.modelname
        and loadname.lower() == sv_main.sv.name.lower() == 0
    ):

        console.Con_DPrintf("trying to open external vis file\n")
        fvis = Mod_FindVisibilityExternal()
        if fvis:
            loadmodel.leafs = None
            loadmodel.numleafs = 0
            console.Con_DPrintf("found valid external .vis file for map\n")
            loadmodel.visdata = Mod_LoadVisibilityExternal(fvis)

            if loadmodel.visdata:
                Mod_LoadLeafsExternal(fvis)

            fvis.close()

            if (
                loadmodel.visdata
                and loadmodel.leafs
                and loadmodel.numleafs > 0
            ):
                vis_loaded = True
            else:
                console.Con_DPrintf(
                    "External VIS data failed, using standard vis.\n"
                )

    if not vis_loaded:
        Mod_LoadVisibility(header.lumps[LUMP_VISIBILITY])
        Mod_LoadLeafs(header.lumps[LUMP_LEAFS], bsp2)

    # Load spatial tree structures and submodels
    Mod_LoadNodes(header.lumps[LUMP_NODES], bsp2)
    Mod_LoadClipnodes(header.lumps[LUMP_CLIPNODES], bsp2)
    Mod_LoadSubmodels(header.lumps[LUMP_MODELS])

    Mod_MakeHull0()

    mod.numframes = 2  # Regular and alternate animation frames

    # Set up submodels (*0 = world, *1..n = doors, lifts, platforms)
    for i in range(mod.numsubmodels):
        bm = mod.submodels[i]

        mod.hulls[0].firstclipnode = bm.headnode[0]
        for j in range(1, quakedef.MAX_MAP_HULLS):
            mod.hulls[j].firstclipnode = bm.headnode[j]
            mod.hulls[j].lastclipnode = mod.numclipnodes - 1

        mod.firstmodelsurface = bm.firstface
        mod.nummodelsurfaces = bm.numfaces

        mod.maxs = list(bm.maxs)
        mod.mins = list(bm.mins)

        # Calculate rotation and yaw bounding boxes
        radius = RadiusFromBounds(mod.mins, mod.maxs)
        mod.rmaxs = [radius, radius, radius]
        mod.ymaxs = [radius, radius, radius]
        mod.rmins = [-radius, -radius, -radius]
        mod.ymins = [-radius, -radius, -radius]

        # Correct physics culling boxes for non-world submodels
        if i > 0 or mod.name != sv_main.sv.modelname:
            mod.clipmaxs = list(mod.maxs)
            mod.clipmins = list(mod.mins)

        mod.numleafs = bm.visleafs

        # Instantiate inline submodel records (*1, *2, ...)
        if i < mod.numsubmodels - 1:
            sub_name = f"*{i + 1}"
            sub_model = Mod_FindName(sub_name)

            # C: *mod = *loadmodel  (struct copy). Copy every attribute, but give the
            # submodel its OWN hull_t objects: the clipnodes/planes they point at stay
            # shared, but firstclipnode/lastclipnode are rewritten per submodel on the
            # next loop iteration and must not leak back into the world model's hulls.
            import copy
            for k, v in vars(mod).items():
                if k not in ("name", "hulls"):
                    setattr(sub_model, k, v)
            sub_model.hulls = [copy.copy(h) for h in mod.hulls]
            sub_model.needload = False

            sub_model.name = sub_name
            mod = sub_model


# Global model loading declarations
pheader: quakedef.aliashdr_t | None = None


# Current pose counter: static int posenum
posenum: int = 0

# Binary record byte sizes
DALIASFRAME_SIZE = 24  # sizeof(daliasframe_t): 2x trivertx_t (8 bytes) + 16 bytes name
TRIVERTX_SIZE = 4      # sizeof(trivertx_t): 3 byte coords + 1 byte lightnormalindex


def Mod_LoadAliasFrame( pin_offset: int, frame: quakedef.maliasframedesc_t) -> int:
    """Loads a single Alias model frame from the binary buffer and assigns it

    to global poseverts[posenum].

    C equivalent:
    static void *Mod_LoadAliasFrame (void *pin, maliasframedesc_t *frame) in gl_model.c
    """
    global posenum, poseverts, pheader, mod_base

    if posenum >= quakedef.MAXALIASFRAMES:
        sys_sdl_unix.Sys_Error("posenum >= MAXALIASFRAMES")

    # Unpack daliasframe_t header (24 bytes)
    (
        min_x,
        min_y,
        min_z,
        min_norm,
        max_x,
        max_y,
        max_z,
        max_norm,
        raw_name,
    ) = struct.unpack("<8B16s", mod_base[pin_offset : pin_offset + DALIASFRAME_SIZE])

    name_str = raw_name.split(b"\x00", 1)[0].decode("ascii", errors="ignore")
    frame.name = name_str

    frame.firstpose = posenum
    frame.numposes = 1

    # Byte values (no endian conversion required)
    frame.bboxmin = [min_x, min_y, min_z]
    frame.bboxmax = [max_x, max_y, max_z]

    # Vertex payload offset immediately following daliasframe_t
    verts_offset = pin_offset + DALIASFRAME_SIZE

    # Store reference to raw trivertx_t buffer in global poseverts array
    verts_bytes_len = pheader.numverts * TRIVERTX_SIZE
    poseverts[posenum] = mod_base[verts_offset : verts_offset + verts_bytes_len]
    posenum += 1

    # Advance pointer past frame vertex array
    return verts_offset + verts_bytes_len

# Binary record sizes
DALIASGROUP_SIZE = 12     # sizeof(daliasgroup_t): int32 (4) + 2x trivertx_t (8) = 12 bytes
DALIASINTERVAL_SIZE = 4  # sizeof(daliasinterval_t): float (4 bytes)
DALIASFRAME_SIZE = 24     # sizeof(daliasframe_t): 2x trivertx_t (8) + 16-byte name = 24 bytes
TRIVERTX_SIZE = 4         # sizeof(trivertx_t): 3 byte coords + 1 byte lightnormalindex


def Mod_LoadAliasGroup( pin_offset: int, frame: quakedef.maliasframedesc_t) -> int:
    """Loads an animated Alias model group frame sequence from the binary buffer.

    Args:
        pin_offset: Current byte offset in mod_base buffer.
        frame: Runtime maliasframedesc_t object to populate.

    Returns:
        Updated byte offset in mod_base positioned after all poses in the group.

    C equivalent:
    static void *Mod_LoadAliasGroup (void *pin, maliasframedesc_t *frame) in gl_model.c
    """
    global posenum, poseverts, pheader, mod_base

    # Unpack daliasgroup_t header (12 bytes)
    numframes_raw, min_x, min_y, min_z, min_n, max_x, max_y, max_z, max_n = (
        struct.unpack("<i8B", mod_base[pin_offset : pin_offset + DALIASGROUP_SIZE])
    )

    numframes = numframes_raw

    frame.firstpose = posenum
    frame.numposes = numframes

    # Bounding box coordinates are single uint8 byte values
    frame.bboxmin = [min_x, min_y, min_z]
    frame.bboxmax = [max_x, max_y, max_z]

    # Advance to daliasinterval_t array following daliasgroup_t
    pin_intervals_offset = pin_offset + DALIASGROUP_SIZE

    # Read first interval value (LittleFloat)
    (interval_val,) = struct.unpack(
        "<f", mod_base[pin_intervals_offset : pin_intervals_offset + 4]
    )
    frame.interval = interval_val

    # Advance pointer past all daliasinterval_t elements (numframes * 4 bytes)
    ptemp_offset = pin_intervals_offset + (numframes * DALIASINTERVAL_SIZE)

    # Process each frame in the sequence
    for _ in range(numframes):
        if posenum >= quakedef.MAXALIASFRAMES:
            sys_sdl_unix.Sys_Error("posenum >= MAXALIASFRAMES")

        # Skip daliasframe_t header (24 bytes) to reach trivertx_t payload
        verts_offset = ptemp_offset + DALIASFRAME_SIZE

        # Register slice reference in global poseverts array
        verts_bytes_len = pheader.numverts * TRIVERTX_SIZE
        poseverts[posenum] = mod_base[verts_offset : verts_offset + verts_bytes_len]
        posenum += 1

        # Advance ptemp offset past daliasframe_t header + frame vertex payload
        ptemp_offset = verts_offset + verts_bytes_len

    return ptemp_offset

# Constants
FLOODFILL_FIFO_SIZE = 0x1000  # 4096 entries (must be power of 2)
FLOODFILL_FIFO_MASK = FLOODFILL_FIFO_SIZE - 1

class floodfill_t:
    """FIFO queue element for tracking 2D skin coordinates."""

    __slots__ = ("x", "y")

    def __init__(self, x: int = 0, y: int = 0) -> None:
        self.x = x
        self.y = y


def Mod_FloodFillSkin(skin: bytearray, skinwidth: int, skinheight: int) -> None:
    """Executes a BFS flood fill on an 8-bit indexed skin buffer starting from (0, 0).

    Args:
        skin: Mutable bytearray representing the 8-bit indexed skin texture.
        skinwidth: Width of the skin image in pixels.
        skinheight: Height of the skin image in pixels.

    C equivalent:
    static void Mod_FloodFillSkin (byte *skin, int skinwidth, int skinheight) in gl_model.c
    """
    if not skin:
        return

    fillcolor = skin[0]  # Assume pixel (0,0) defines the background color to replace

    # Search Quake 8-to-24 bit RGBA table for an opaque black entry
    filledcolor = 0
    for i in range(256):
        if gl_texmgr.d_8to24table[i] == (255 << 0):
            filledcolor = i
            break

    # Guard against filling to target color or sentinel marker (255)
    if fillcolor == filledcolor or fillcolor == 255:
        return

    # BFS over pixel offsets (x/y recovered with divmod); a plain growing list replaces
    # the C ring buffer, since every pixel is enqueued at most once
    w = skinwidth
    last_row = skinheight - 1
    queue = [0]
    qi = 0
    while qi < len(queue):
        pos = queue[qi]
        qi += 1
        y, x = divmod(pos, w)
        fdc = filledcolor

        if x > 0:
            p = pos - 1
            v = skin[p]
            if v == fillcolor:
                skin[p] = 255
                queue.append(p)
            elif v != 255:
                fdc = v
        if x < w - 1:
            p = pos + 1
            v = skin[p]
            if v == fillcolor:
                skin[p] = 255
                queue.append(p)
            elif v != 255:
                fdc = v
        if y > 0:
            p = pos - w
            v = skin[p]
            if v == fillcolor:
                skin[p] = 255
                queue.append(p)
            elif v != 255:
                fdc = v
        if y < last_row:
            p = pos + w
            v = skin[p]
            if v == fillcolor:
                skin[p] = 255
                queue.append(p)
            elif v != 255:
                fdc = v

        skin[pos] = fdc


# Constants
ALIAS_SKIN_SINGLE = 0
MAX_SKINS = 32
MF_HOLEY = quakedef.MF_HOLEY
# must match gl_texmgr (gl_texmgr imports this module, so the values are repeated here)
TEXPREF_MIPMAP     = 0x0001
TEXPREF_ALPHA      = 0x0008
TEXPREF_PAD        = 0x0010
TEXPREF_NOPICMIP   = 0x0080
TEXPREF_FULLBRIGHT = 0x0100
TEXPREF_NOBRIGHT   = 0x0200
TEXPREF_WARPIMAGE  = 0x0800


def Mod_LoadAllSkins(numskins: int, pin_offset: int) -> int:
    """Loads all single and grouped skin textures for an Alias model.

    Args:
        numskins: Total skin count specified in model header.
        pin_offset: Current byte offset in mod_base pointing to skin data.

    Returns:
        Updated byte offset in mod_base positioned after all skin structures.

    C equivalent:
    static void *Mod_LoadAllSkins (int numskins, daliasskintype_t *pskintype) in gl_model.c
    """
    global pheader, loadmodel, loadname, mod_base
    SRC_INDEXED = gl_texmgr.srcformat.SRC_INDEXED

    if numskins < 1 or numskins > MAX_SKINS:
        sys_sdl_unix.Sys_Error(f"Mod_LoadAliasModel: Invalid # of skins: {numskins}")

    size = pheader.skinwidth * pheader.skinheight
    texflags = TEXPREF_PAD

    if loadmodel.flags & MF_HOLEY:
        texflags |= TEXPREF_ALPHA

    curr_offset = pin_offset

    for i in range(numskins):
        # Read daliasskintype_t (int32)
        (skin_type,) = struct.unpack("<i", mod_base[curr_offset : curr_offset + 4])

        if skin_type == ALIAS_SKIN_SINGLE:
            # Skin pixel bytes follow daliasskintype_t
            skin_bytes_offset = curr_offset + 4

            # Mutable slice for flood filling in place
            skin_pixels = bytearray(
                mod_base[skin_bytes_offset : skin_bytes_offset + size]
            )
            Mod_FloodFillSkin(skin_pixels, pheader.skinwidth, pheader.skinheight)
            mod_base[skin_bytes_offset : skin_bytes_offset + size] = skin_pixels

            # Allocate texels buffer and bind offset relative to pheader
            texels = zone.Hunk_AllocName(size, loadname)
            pheader.texels[i] = (
                texels - pheader.offset if hasattr(pheader, "offset") else 0
            )

            texels[0:size] = mod_base[skin_bytes_offset : skin_bytes_offset + size]

            name = f"{loadmodel.name}:frame{i}"
            offset = skin_bytes_offset

            # Handle fullbright masks
            if Mod_CheckFullbrights(
                mod_base[skin_bytes_offset : skin_bytes_offset + size], size
            ):
                pheader.gltextures[i][0] = gl_texmgr.TexMgr_LoadImage(
                    loadmodel,
                    name,
                    pheader.skinwidth,
                    pheader.skinheight,
                    SRC_INDEXED,
                    mod_base[skin_bytes_offset : skin_bytes_offset + size],
                    loadmodel.name,
                    offset,
                    texflags | TEXPREF_NOBRIGHT,
                )
                fbr_mask_name = f"{loadmodel.name}:frame{i}_glow"
                pheader.fbtextures[i][0] = gl_texmgr.TexMgr_LoadImage(
                    loadmodel,
                    fbr_mask_name,
                    pheader.skinwidth,
                    pheader.skinheight,
                    SRC_INDEXED,
                    mod_base[skin_bytes_offset : skin_bytes_offset + size],
                    loadmodel.name,
                    offset,
                    texflags | TEXPREF_FULLBRIGHT,
                )
            else:
                pheader.gltextures[i][0] = gl_texmgr.TexMgr_LoadImage(
                    loadmodel,
                    name,
                    pheader.skinwidth,
                    pheader.skinheight,
                    SRC_INDEXED,
                    mod_base[skin_bytes_offset : skin_bytes_offset + size],
                    loadmodel.name,
                    offset,
                    texflags,
                )
                pheader.fbtextures[i][0] = None

            # Replicate texture pointers across 4 animation slots
            for slot in range(1, 4):
                pheader.gltextures[i][slot] = pheader.gltextures[i][0]
                pheader.fbtextures[i][slot] = pheader.fbtextures[i][0]

            curr_offset = skin_bytes_offset + size

        else:
            # Animated skin group
            curr_offset += 4  # Skip daliasskintype_t header

            # Read daliasskingroup_t (numskins: int32)
            (groupskins,) = struct.unpack(
                "<i", mod_base[curr_offset : curr_offset + 4]
            )
            curr_offset += 4

            # Skip daliasskininterval_t array (groupskins * float32)
            curr_offset += groupskins * 4

            for j in range(groupskins):
                skin_bytes_offset = curr_offset

                # Flood fill in place
                skin_pixels = bytearray(
                    mod_base[skin_bytes_offset : skin_bytes_offset + size]
                )
                Mod_FloodFillSkin(
                    skin_pixels, pheader.skinwidth, pheader.skinheight
                )
                mod_base[skin_bytes_offset : skin_bytes_offset + size] = skin_pixels

                if j == 0:
                    texels = zone.Hunk_AllocName(size, loadname)
                    pheader.texels[i] = (
                        texels - pheader.offset if hasattr(pheader, "offset") else 0
                    )
                    texels[:size] = mod_base[skin_bytes_offset : skin_bytes_offset + size]

                name = f"{loadmodel.name}:frame{i}_{j}"
                offset = skin_bytes_offset

                if Mod_CheckFullbrights(
                    mod_base[skin_bytes_offset : skin_bytes_offset + size], size
                ):
                    pheader.gltextures[i][j & 3] = gl_texmgr.TexMgr_LoadImage(
                        loadmodel,
                        name,
                        pheader.skinwidth,
                        pheader.skinheight,
                        SRC_INDEXED,
                        mod_base[skin_bytes_offset : skin_bytes_offset + size],
                        loadmodel.name,
                        offset,
                        texflags | TEXPREF_NOBRIGHT,
                    )
                    fbr_mask_name = f"{loadmodel.name}:frame{i}_{j}_glow"
                    pheader.fbtextures[i][j & 3] = gl_texmgr.TexMgr_LoadImage(
                        loadmodel,
                        fbr_mask_name,
                        pheader.skinwidth,
                        pheader.skinheight,
                        SRC_INDEXED,
                        mod_base[skin_bytes_offset : skin_bytes_offset + size],
                        loadmodel.name,
                        offset,
                        texflags | TEXPREF_FULLBRIGHT,
                    )
                else:
                    pheader.gltextures[i][j & 3] = gl_texmgr.TexMgr_LoadImage(
                        loadmodel,
                        name,
                        pheader.skinwidth,
                        pheader.skinheight,
                        SRC_INDEXED,
                        mod_base[skin_bytes_offset : skin_bytes_offset + size],
                        loadmodel.name,
                        offset,
                        texflags,
                    )
                    pheader.fbtextures[i][j & 3] = None

                curr_offset += size

            k = groupskins
            for j in range(k, 4):
                pheader.gltextures[i][j & 3] = pheader.gltextures[i][j - k]

    return curr_offset

FLT_MAX = sys.float_info.max


def Mod_CalcAliasBounds(a: quakedef.aliashdr_t) -> None:
    """Calculates model bounding boxes (AABB, yaw-rotated, fully-rotated) across all poses.

    Args:
        a: Alias header instance containing numposes and numverts count.

    C equivalent:
    static void Mod_CalcAliasBounds (aliashdr_t *a) in gl_model.c
    """
    global loadmodel, pheader, poseverts

    # Clear out bounding box arrays
    loadmodel.mins = [FLT_MAX, FLT_MAX, FLT_MAX]
    loadmodel.ymins = [FLT_MAX, FLT_MAX, FLT_MAX]
    loadmodel.rmins = [FLT_MAX, FLT_MAX, FLT_MAX]

    loadmodel.maxs = [-FLT_MAX, -FLT_MAX, -FLT_MAX]
    loadmodel.ymaxs = [-FLT_MAX, -FLT_MAX, -FLT_MAX]
    loadmodel.rmaxs = [-FLT_MAX, -FLT_MAX, -FLT_MAX]

    radius = 0.0
    yawradius = 0.0

    # Process all vertices across all poses
    for i in range(a.numposes):
        pose_bytes = poseverts[i]

        for j in range(a.numverts):
            # Unpack trivertx_t byte coordinates (x, y, z)
            vert_offset = j * 4
            v_x, v_y, v_z = struct.unpack("<3B", pose_bytes[vert_offset : vert_offset + 3])

            # Scale and offset quantized byte coordinates into world/model space
            vx = v_x * pheader.scale[0] + pheader.scale_origin[0]
            vy = v_y * pheader.scale[1] + pheader.scale_origin[1]
            vz = v_z * pheader.scale[2] + pheader.scale_origin[2]

            v = [vx, vy, vz]

            # Update Axis-Aligned Bounding Box (AABB)
            for k in range(3):
                loadmodel.mins[k] = min(loadmodel.mins[k], v[k])
                loadmodel.maxs[k] = max(loadmodel.maxs[k], v[k])

            # Track maximum squared 2D radius (XY plane)
            dist_2d = vx * vx + vy * vy
            if yawradius < dist_2d:  # noqa: PLR1730
                yawradius = dist_2d

            # Track maximum squared 3D radius (XYZ sphere)
            dist_3d = dist_2d + vz * vz
            if radius < dist_3d:  # noqa: PLR1730
                radius = dist_3d

    # Full 3D rotation bounding box (used when entity has non-zero pitch or roll)
    radius_val = math.sqrt(radius)
    loadmodel.rmins[0] = loadmodel.rmins[1] = loadmodel.rmins[2] = -radius_val
    loadmodel.rmaxs[0] = loadmodel.rmaxs[1] = loadmodel.rmaxs[2] = radius_val

    # Yaw rotation bounding box (used when entity has non-zero yaw)
    yawradius_val = math.sqrt(yawradius)
    loadmodel.ymins[0] = loadmodel.ymins[1] = -yawradius_val
    loadmodel.ymaxs[0] = loadmodel.ymaxs[1] = yawradius_val
    loadmodel.ymins[2] = loadmodel.mins[2]
    loadmodel.ymaxs[2] = loadmodel.maxs[2]


MAX_QPATH = 64

def nameInList(name_list: str, target_name: str) -> bool:
    """Checks whether target_name exists as an exact item in a comma-separated list string.

    Args:
        name_list: Comma-separated list string (e.g. "progs/player.mdl,progs/eyes.mdl").
        target_name: Target string to search for.

    Returns:
        True if target_name matches an entry in name_list, False otherwise.
    """
    if not name_list or not target_name:
        return False

    # Split on commas, strip whitespace/truncation up to MAX_QPATH - 1, and check membership
    return any(
        token[: MAX_QPATH - 1] == target_name
        for token in name_list.split(",")
        if token  # Filters out empty strings from consecutive commas
    )


def Mod_SetExtraFlags(mod: quakedef.qmodel_t):
    if not mod or mod.type != quakedef.modtype_t.mod_alias:
        return

    mod.flags &= ( 0xff | quakedef.MF_HOLEY )

    if nameInList(cvar.Cvar_GetCvar('r_nolerp_list').string, mod.name):
        mod.flags |= quakedef.MOD_NOLERP

    if nameInList(cvar.Cvar_GetCvar('r_noshadow_list').string, mod.name):
        mod.flags |= quakedef.MOD_NOSHADOW

    if mod.name in ['progs/flame2.mdl', 'progs/flame.mdl', 'progs/boss.mdl']:
        mod.flags |= quakedef.MOD_FBRIGHTHACK

# Binary Record Sizes (in bytes)
MDL_HEADER_SIZE = 84     # sizeof(mdl_t) header up to skins
STVERT_SIZE = 12         # sizeof(stvert_t): onseam (4), s (4), t (4)
DTRIANGLE_SIZE = 16      # sizeof(dtriangle_t): facesfront (4), vertindex[3] (12)
DALIASFRAMETYPE_SIZE = 4 # sizeof(daliasframetype_t): type (4)

# Constants
ALIAS_VERSION = 6
ALIAS_BASE_SIZE_RATIO = 1.0
MAX_LBM_HEIGHT = 480
MAXALIASVERTS = 2000
MAXALIASTRIS = 4000
ALIAS_SINGLE = 0


def Mod_LoadAliasModel(mod: quakedef.qmodel_t, buffer: bytes) -> None:
    """Parses a complete Quake .mdl binary buffer and populates model metadata.

    Args:
        mod: Target model instance to populate.
        buffer: Raw binary file bytes containing the .mdl data.

    C equivalent:
    static void Mod_LoadAliasModel (qmodel_t *mod, void *buffer) in gl_model.c
    """
    global pheader, mod_base, posenum, loadname, stverts, triangles

    start = zone.Hunk_LowMark()
    mod_base = buffer

    # Unpack mdl_t binary header (84 bytes)
    (
        ident,
        version,
        scale_x, scale_y, scale_z,
        orig_x, orig_y, orig_z,
        boundingradius,
        eye_x, eye_y, eye_z,
        numskins,
        skinwidth,
        skinheight,
        numverts,
        numtris,
        numframes,
        synctype,
        flags,
        size_val
    ) = struct.unpack("<2i10f8i1f", buffer[:MDL_HEADER_SIZE])

    if version != ALIAS_VERSION:
        sys_sdl_unix.Sys_Error(
            f"{mod.name} has wrong version number ({version} should be {ALIAS_VERSION})"
        )

    # Instantiate runtime alias header structure
    pheader = quakedef.aliashdr_t()
    mod.flags = flags

    pheader.boundingradius = boundingradius
    pheader.numskins = numskins
    pheader.skinwidth = skinwidth
    pheader.skinheight = skinheight

    if pheader.skinheight > MAX_LBM_HEIGHT:
        quakedef.Con_DWarning(
            f"model {mod.name} has a skin taller than {MAX_LBM_HEIGHT}"
        )

    pheader.numverts = numverts
    if pheader.numverts <= 0:
        sys_sdl_unix.Sys_Error(f"model {mod.name} has no vertices")
    if pheader.numverts > MAXALIASVERTS:
        sys_sdl_unix.Sys_Error(
            f"model {mod.name} has too many vertices ({pheader.numverts}; max = {MAXALIASVERTS})"
        )

    pheader.numtris = numtris
    if pheader.numtris <= 0:
        sys_sdl_unix.Sys_Error(f"model {mod.name} has no triangles")
    if pheader.numtris > MAXALIASTRIS:
        sys_sdl_unix.Sys_Error(
            f"model {mod.name} has too many triangles ({pheader.numtris}; max = {MAXALIASTRIS})"
        )

    pheader.numframes = numframes
    if pheader.numframes < 1:
        sys_sdl_unix.Sys_Error(
            f"Mod_LoadAliasModel: Invalid # of frames: {pheader.numframes}"
        )

    pheader.size = size_val * ALIAS_BASE_SIZE_RATIO
    mod.synctype = synctype
    mod.numframes = pheader.numframes

    pheader.scale = [scale_x, scale_y, scale_z]
    pheader.scale_origin = [orig_x, orig_y, orig_z]
    pheader.eyeposition = [eye_x, eye_y, eye_z]

    # Initialize frame array inside pheader
    pheader.frames = [quakedef.maliasframedesc_t() for _ in range(pheader.numframes)]

    # 1. Load Skins
    curr_offset = MDL_HEADER_SIZE
    curr_offset = Mod_LoadAllSkins(pheader.numskins, curr_offset)

    # 2. Load Base (S, T) Texture Coordinates
    for i in range(pheader.numverts):
        onseam, s, t = struct.unpack(
            "<3i", buffer[curr_offset : curr_offset + STVERT_SIZE]
        )
        stverts[i].onseam = onseam
        stverts[i].s = s
        stverts[i].t = t
        curr_offset += STVERT_SIZE

    # 3. Load Triangle Indices & Face Flags
    for i in range(pheader.numtris):
        facesfront, v0, v1, v2 = struct.unpack(
            "<4i", buffer[curr_offset : curr_offset + DTRIANGLE_SIZE]
        )
        triangles[i].facesfront = facesfront
        triangles[i].vertindex = [v0, v1, v2]
        curr_offset += DTRIANGLE_SIZE

    # 4. Load Pose Frames / Groups
    posenum = 0
    for i in range(pheader.numframes):
        (frame_type,) = struct.unpack(
            "<i", buffer[curr_offset : curr_offset + DALIASFRAMETYPE_SIZE]
        )
        curr_offset += DALIASFRAMETYPE_SIZE

        if frame_type == ALIAS_SINGLE:
            curr_offset = Mod_LoadAliasFrame(
                curr_offset, pheader.frames[i]
            )
        else:
            curr_offset = Mod_LoadAliasGroup(
                curr_offset, pheader.frames[i]
            )

    pheader.numposes = posenum
    mod.type = quakedef.modtype_t.mod_alias

    # Apply engine flags & bounds
    Mod_SetExtraFlags(mod)
    Mod_CalcAliasBounds(pheader)

    # Build GPU display lists
    gl_mesh.GL_MakeAliasModelDisplayLists(mod, pheader)

    # C copies the hunk (header + pose data) into the cache with memcpy.
    # Here the header is a Python object, so the cache just holds it directly
    # (same as the sprite loader does with psprite).
    mod.cache.data = pheader
    zone.Hunk_FreeToLowMark(start)


# Binary Structure Sizes (in bytes)
DSPRITEFRAME_SIZE = 16  # origin[2] (8), width (4), height (4)

# Texture Preference Flags
TEXPREF_PAD = 0x01
TEXPREF_ALPHA = 0x02
TEXPREF_NOPICMIP = 0x10
SRC_INDEXED = 0


def Mod_LoadSpriteFrame( pin_offset: int, frame_ref: list[quakedef.mspriteframe_t | None], framenum: int) -> int:
    """Parses a single sprite frame and registers its OpenGL texture.

    Args:
        pin_offset: Byte offset in mod_base pointing to the dspriteframe_t structure.
        frame_ref: Single-element list acting as a pointer reference (*ppframe) to store mspriteframe_t.
        framenum: Frame sequence index number.

    Returns:
        Updated byte offset in mod_base positioned after the frame data and pixel buffer.

    C equivalent:
    static void *Mod_LoadSpriteFrame (void *pin, mspriteframe_t **ppframe, int framenum) in gl_model.c
    """
    global loadmodel, loadname, mod_base

    # Unpack dspriteframe_t: origin[0] (i32), origin[1] (i32), width (i32), height (i32)
    orig_x, orig_y, width, height = struct.unpack(
        "<4i", mod_base[pin_offset : pin_offset + DSPRITEFRAME_SIZE]
    )
    size = width * height

    # Allocate runtime sprite frame structure
    pspriteframe = quakedef.mspriteframe_t()
    frame_ref[0] = pspriteframe

    pspriteframe.width = width
    pspriteframe.height = height

    # Calculate screen relative bounding extents
    pspriteframe.up = orig_y
    pspriteframe.down = orig_y - height
    pspriteframe.left = orig_x
    pspriteframe.right = width + orig_x

    # Calculate UV maximum limits accounting for texture padding
    pspriteframe.smax = float(width) / float(gl_texmgr.TexMgr_PadConditional(width))
    pspriteframe.tmax = float(height) / float(gl_texmgr.TexMgr_PadConditional(height))

    # Construct frame texture reference name
    name = f"{loadmodel.name}:frame{framenum}"

    # Pixel byte buffer offset immediately following the header
    pixel_offset = pin_offset + DSPRITEFRAME_SIZE
    offset = pixel_offset  # (src_offset_t)(pinframe + 1) - (src_offset_t)mod_base

    pixel_bytes = mod_base[pixel_offset : pixel_offset + size]

    # Load image texture into texture manager
    pspriteframe.gltexture = gl_texmgr.TexMgr_LoadImage(
        loadmodel,
        name,
        width,
        height,
        SRC_INDEXED,
        pixel_bytes,
        loadmodel.name,
        offset,
        TEXPREF_PAD | TEXPREF_ALPHA | TEXPREF_NOPICMIP,
    )

    # Return offset past header and raw image pixels
    return pixel_offset + size

# Binary Structure Sizes (in bytes)
DSPRITEGROUP_SIZE = 4     # numframes (i32)
DSPRITEINTERVAL_SIZE = 4  # interval (f32)

# Sprite Frame Types
SPR_SINGLE = 0
SPR_GROUP = 1
SPR_ANGLED = 2

def Mod_LoadSpriteGroup( pin_offset: int, frame_ref: typing.List[typing.Optional[quakedef.mspriteframe_t]], framenum: int, sprite_type: int,) -> int:
    """Parses a sprite frame group (animated sequence or 8-way directional view).

    Args:
        pin_offset: Byte offset in mod_base pointing to the dspritegroup_t structure.
        frame_ref: Single-element list acting as a reference (*ppframe) to store mspritegroup_t.
        framenum: Frame sequence index number.
        sprite_type: Type of sprite frame structure (SPR_SINGLE, SPR_GROUP, SPR_ANGLED).

    Returns:
        Updated byte offset in mod_base positioned after all group intervals and sub-frames.

    C equivalent:
    static void *Mod_LoadSpriteGroup (void *pin, mspriteframe_t **ppframe, int framenum, spriteframetype_t type) in gl_model.c
    """
    global loadname, mod_base

    # Unpack dspritegroup_t (numframes: i32)
    (numframes,) = struct.unpack(
        "<i", mod_base[pin_offset : pin_offset + DSPRITEGROUP_SIZE]
    )

    if sprite_type == SPR_ANGLED and numframes != 8:
        sys_sdl_unix.Sys_Error(f"Mod_LoadSpriteGroup: Bad # of frames: {numframes}")

    # Instantiate runtime sprite group structure
    pspritegroup = quakedef.mspritegroup_t()
    pspritegroup.numframes = numframes
    pspritegroup.frames = [None] * numframes
    pspritegroup.intervals = [0.0] * numframes

    # Assign group structure back to caller's output reference pointer
    frame_ref[0] = pspritegroup

    # Advance offset past dspritegroup_t header
    curr_offset = pin_offset + DSPRITEGROUP_SIZE

    # Parse dspriteinterval_t array
    for i in range(numframes):
        (interval,) = struct.unpack(
            "<f", mod_base[curr_offset : curr_offset + DSPRITEINTERVAL_SIZE]
        )
        if interval <= 0.0:
            sys_sdl_unix.Sys_Error("Mod_LoadSpriteGroup: interval<=0")

        pspritegroup.intervals[i] = interval
        curr_offset += DSPRITEINTERVAL_SIZE

    # Parse nested sprite frames
    for i in range(numframes):
        sub_frame_ref: typing.List[typing.Optional[quakedef.mspriteframe_t]] = [None]
        curr_offset = quakedef.Mod_LoadSpriteFrame(
            curr_offset, sub_frame_ref, framenum * 100 + i
        )
        pspritegroup.frames[i] = sub_frame_ref[0]

    return curr_offset

# Binary Record Sizes (in bytes)
DSPRITE_SIZE = 36          # sizeof(dsprite_t): ident (4), version (4), type (4), boundingradius (4), width (4), height (4), numframes (4), beamlength (4), synctype (4)
DSPRITEFRAMETYPE_SIZE = 4  # sizeof(dspriteframetype_t): type (4)

# Constants
SPRITE_VERSION = 1
mod_sprite = 2

# Frame Types
SPR_SINGLE = 0
SPR_GROUP = 1
SPR_ANGLED = 2


def Mod_LoadSpriteModel(mod: quakedef.qmodel_t, buffer: bytes) -> None:
    """Parses a complete Quake .spr binary buffer and populates model metadata.

    Args:
        mod: Target model instance to populate.
        buffer: Raw binary file bytes containing the .spr data.

    C equivalent:
    static void Mod_LoadSpriteModel (qmodel_t *mod, void *buffer) in gl_model.c
    """
    global mod_base, loadname

    mod_base = buffer

    # Unpack dsprite_t header (36 bytes)
    (
        ident,
        version,
        sprite_type,
        boundingradius,
        width,
        height,
        numframes,
        beamlength,
        synctype,
    ) = struct.unpack("<3iff2i1f1i", buffer[:DSPRITE_SIZE])

    if version != SPRITE_VERSION:
        sys_sdl_unix.Sys_Error(
            f"{mod.name} has wrong version number ({version} should be {SPRITE_VERSION})"
        )

    if numframes < 1:
        sys_sdl_unix.Sys_Error(
            f"Mod_LoadSpriteModel: Invalid # of frames: {numframes}"
        )

    # Instantiate runtime sprite header structure
    psprite = quakedef.msprite_t()
    mod.cache.data = psprite

    psprite.type = sprite_type
    psprite.maxwidth = width
    psprite.maxheight = height
    psprite.beamlength = beamlength
    mod.synctype = synctype
    psprite.numframes = numframes

    # Compute symmetric bounding box extents centered on origin
    half_width = width / 2.0
    half_height = height / 2.0

    mod.mins = [-half_width, -half_width, -half_height]
    mod.maxs = [half_width, half_width, half_height]

    mod.numframes = numframes
    psprite.frames = [quakedef.mspriteframedesc_t() for _ in range(numframes)]

    curr_offset = DSPRITE_SIZE

    # Parse individual frames and frame groups
    for i in range(numframes):
        (frametype,) = struct.unpack(
            "<i", buffer[curr_offset : curr_offset + DSPRITEFRAMETYPE_SIZE]
        )
        curr_offset += DSPRITEFRAMETYPE_SIZE

        psprite.frames[i].type = frametype
        frame_ref: typing.List[typing.Optional[quakedef.mspriteframe_t]] = [None]

        if frametype == SPR_SINGLE:
            curr_offset = Mod_LoadSpriteFrame(
                curr_offset, frame_ref, i
            )
        else:
            curr_offset = quakedef.Mod_LoadSpriteGroup(
                curr_offset, frame_ref, i, frametype
            )

        psprite.frames[i].frameptr = frame_ref[0]

    mod.type = mod_sprite


