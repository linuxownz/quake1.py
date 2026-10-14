#gl_texmgr.py

import array
import ctypes
import io
from enum import Enum

import numpy as np
import OpenGL
import OpenGL.GL

import _cmd
import common
import console
import crc
import cvar
import gl_model
import gl_rmain
import gl_texmgr
import gl_vidsdl
import gl_warp
import glquake
import host
import image
import quakedef
import r_brush
import render
import sbar
import sys_sdl_unix
import zone

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

class gltexture_t:
    def __init__(self):
        self.texnum = 0
        self.next  : gltexture_t       = None
        self.owner : gl_model.qmodel_t = None

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

gl_hardware_maxsize = 0;

MAX_GLTEXTURES = 4096
numgltextures = 0

active_gltextures : gltexture_t = None
free_gltextures   : gltexture_t = None

notexture   : gltexture_t = None
nulltexture : gltexture_t = None

in_reload_images = False

d_8to24table                = array.array('B', [0] * 1024)
d_8to24table_fbright        = array.array('B', [0] * 1024)
d_8to24table_fbright_fence  = array.array('B', [0] * 1024)
d_8to24table_nobright       = array.array('B', [0] * 1024)
d_8to24table_nobright_fence = array.array('B', [0] * 1024)
d_8to24table_conchars       = array.array('B', [0] * 1024)

class glmode_t:
    def __init__(self, magfilter, minfilter, name):
        self.magfilter = magfilter
        self.minfilter = minfilter
        self.name      = name

glmodes : list[glmode_t] = [
    glmode_t(OpenGL.GL.GL_NEAREST, OpenGL.GL.GL_NEAREST,                'GL_NEAREST'),
    glmode_t(OpenGL.GL.GL_NEAREST, OpenGL.GL.GL_NEAREST_MIPMAP_NEAREST, 'GL_NEAREST_MIPMAP_NEAREST'),
    glmode_t(OpenGL.GL.GL_NEAREST, OpenGL.GL.GL_NEAREST_MIPMAP_LINEAR,  'GL_NEAREST_MIPMAP_LINEAR'),
    glmode_t(OpenGL.GL.GL_LINEAR, OpenGL.GL.GL_LINEAR,                  'GL_LINEAR'),
    glmode_t(OpenGL.GL.GL_LINEAR, OpenGL.GL.GL_LINEAR_MIPMAP_NEAREST,   'GL_LINEAR_MIPMAP_NEAREST'),
    glmode_t(OpenGL.GL.GL_LINEAR, OpenGL.GL.GL_LINEAR_MIPMAP_LINEAR,    'GL_LINEAR_MIPMAP_LINEAR'),
]

NUM_GLMODES = len(glmodes)
glmode_idx  = NUM_GLMODES - 1

currenttexture:list[float] = []
currenttarget = OpenGL.GL.GL_TEXTURE0
mtexenabled = False

def TexMgr_LoadPalette():
    global d_8to24table, d_8to24table_conchars, d_8to24table_fbright
    global d_8to24table_fbright_fence, d_8to24table_nobright
    global d_8to24table_nobright_fence

    #handle, length, path_id, is_pak = common.COM_FOpenFile('gfx/palette.lmp')
    ffr = common.COM_FOpenFile('gfx/palette.lmp')

    handle = ffr.handle
    is_pak = ffr.is_pak

    mark = zone.Hunk_LowMark()
    pal = zone.Hunk_Alloc(768)

    assert(ffr.file)
    if ffr.file.readinto(pal) != 768:
        sys_sdl_unix.Sys_Error('failed to read palette')

    if not is_pak:
        ffr.file.close()

    assert(len(pal) == 768)

    # google says this is wrong
    # standard paletts, 255 is transparent

    for i in range(256):
        d_8to24table[i * 4 + 0] = pal[i * 3 + 0]
        d_8to24table[i * 4 + 1] = pal[i * 3 + 1]
        d_8to24table[i * 4 + 2] = pal[i * 3 + 2]
        d_8to24table[i * 4 + 3] = 255

    # d_8to24table[255 + 3] = 0 # ((byte *) &d_8to24table[255]) [3] = 0;

    # fullbright palette, 0-223 are black for additive blending
# fullbright palette: 0-223 are black, 224-255 are standard
    for i in range(224):
        d_8to24table_fbright[i * 4 + 0] = 0
        d_8to24table_fbright[i * 4 + 1] = 0
        d_8to24table_fbright[i * 4 + 2] = 0
        d_8to24table_fbright[i * 4 + 3] = 255

    for i in range(224, 256):
        d_8to24table_fbright[i * 4 + 0] = pal[i * 3 + 0]
        d_8to24table_fbright[i * 4 + 1] = pal[i * 3 + 1]
        d_8to24table_fbright[i * 4 + 2] = pal[i * 3 + 2]
        d_8to24table_fbright[i * 4 + 3] = 255

    # nobright palette: 0-223 are standard, 224-255 are black
    for i in range(224):
        d_8to24table_nobright[i * 4 + 0] = pal[i * 3 + 0]
        d_8to24table_nobright[i * 4 + 1] = pal[i * 3 + 1]
        d_8to24table_nobright[i * 4 + 2] = pal[i * 3 + 2]
        d_8to24table_nobright[i * 4 + 3] = 255

    for i in range(224, 256):
        d_8to24table_nobright[i * 4 + 0] = 0
        d_8to24table_nobright[i * 4 + 1] = 0
        d_8to24table_nobright[i * 4 + 2] = 0
        d_8to24table_nobright[i * 4 + 3] = 255


    # 1. Update the contents of the global arrays using slice assignment
    # This ensures other modules holding these references see the new data
    d_8to24table_fbright_fence[:]  = d_8to24table_fbright[:]
    d_8to24table_nobright_fence[:] = d_8to24table_nobright[:]
    d_8to24table_conchars[:]       = d_8to24table[:]

    # 2. Apply Alpha transparency overrides (0 = fully transparent)
    # Quake convention: index 255 is the transparent color key

    # Standard textures (e.g., status bar, crosshair)
    d_8to24table[255 * 4 + 3] = 0

    # Console characters (fonts)
    d_8to24table_conchars[0 * 4 + 3] = 0

    # Fence textures (textures that need to be transparent and fullbright/nobright)
    d_8to24table_fbright_fence[255 * 4 + 3] = 0
    d_8to24table_nobright_fence[255 * 4 + 3] = 0



def TexMgr_FindTexture(owner, name):
    glt : gltexture_t = None

    if name:
        glt = active_gltextures
        while glt:
            if glt.owner == owner and glt.name == name:
                return glt
            glt = glt.next

    return None

def TexMgr_NewTexture():
    global free_gltextures, active_gltextures

    if numgltextures == MAX_GLTEXTURES:
        sys_sdl_unix.Sys_Error('numgltextures == MAX_GLTEXTURES')

    glt = free_gltextures
    free_gltextures = glt.next

    glt.next = active_gltextures
    active_gltextures = glt

    texnum = ctypes.c_int()
    OpenGL.GL.glGenTextures(1, texnum)
    glt.texnum = texnum.value

    return glt


def TexMgr_FreeTexture(kill: gltexture_t):
    global active_gltextures, free_gltextures, numgltextures

    if in_reload_images:
        return

    if kill is None:
        console.Con_Printf('TexMgr_FreeTexture: Null texture')
        return

    if active_gltextures == kill:
        active_gltextures = kill.next
        kill.next = free_gltextures
        free_gltextures = kill

        GL_DeleteTexture(kill)
        numgltextures -= 1
        return

    glt: gltexture_t = active_gltextures

    while glt:
        if glt.next == kill:
            glt.next = kill.next
            kill.next = free_gltextures
            free_gltextures = kill

            GL_DeleteTexture(kill)
            numgltextures -= 1
            return
        glt = glt.next

    console.Con_Printf('TexMgr_FreeTexture: not found')



def TexMgr_FreeTextures(flags: int, mask: int):
    glt: gltexture_t = active_gltextures

    while glt:
        next_glt: gltexture_t = glt.next
        if ( glt.flags & mask ) == ( flags & mask ):
            TexMgr_FreeTexture(glt)
        glt = next_glt


def TexMgr_FreeTexturesForOwner(owner: quakedef.qmodel_t):
    glt: gltexture_t = active_gltextures

    while glt:
        next_glt: gltexture_t = glt.next
        if glt and glt.owner == owner:
            TexMgr_FreeTexture(glt)
        glt = next_glt

def TexMgr_DeleteTextureObjects():
    glt: gltexture_t = active_gltextures

    while glt:
        GL_DeleteTexture(glt)
        glt = glt.next





def TexMgr_8to32(_in, pixels, usepal):
    # _in: raw 8-bit bytes from the WAD
    # usepal: the array of 1024 bytes (256 colors * 4 components)
    out = bytearray(pixels * 4)

    for i in range(pixels):
        pal_index = _in[i] * 4
        out[i * 4 + 0] = usepal[pal_index + 0] # R
        out[i * 4 + 1] = usepal[pal_index + 1] # G
        out[i * 4 + 2] = usepal[pal_index + 2] # B
        out[i * 4 + 3] = usepal[pal_index + 3] # A

    return out

def TexMgr_Pad(s):
    i = 1
    while i < s:
        i <<= 1
    return i

def TexMgr_PadConditional(s):
    if s < TexMgr_SafeTextureSize(s):
        return TexMgr_Pad(s)
    return s


def TexMgr_MipMapW(data: bytes, width: int, height: int) -> np.ndarray:
    np_data = np.frombuffer(data, dtype=np.uint8)

    # If width is 1, we can't downsample further horizontally
    if width < 2:
        return data

    total_bytes = width * height * 4

    # Ensure we don't try to process more data than we have
    if np_data.size < total_bytes:
        return data

    num_input_bytes = (total_bytes // 8) * 8
    num_output_pixels = num_input_bytes // 8

    try:
        in_view = np_data[:num_input_bytes].reshape(num_output_pixels, 2, 4)
        summed_pixels = in_view.sum(axis=1, dtype=np.uint16)
        out_pixels = (summed_pixels // 2).astype(np.uint8)

        # We need a writable copy if the buffer is read-only
        res = bytearray(data)
        res[:num_output_pixels * 4] = out_pixels.flatten().tobytes()
        return bytes(res)
    except Exception:
        return data

def TexMgr_MipMapH(data, width, height):
    # If height is 1, we can't downsample further vertically
    if height < 2:
        return data

    data_np = np.frombuffer(data, dtype=np.uint8)
    expected_size = width * height * 4

    if len(data_np) < expected_size:
        return data

    data_reshaped = data_np[:expected_size].reshape(height, width, 4)
    new_height = height // 2

    paired_rows = data_reshaped[:new_height * 2, ...].reshape(new_height, 2, width, 4)
    summed_rows = paired_rows.sum(axis=1, dtype=np.uint16)
    averaged_rows = (summed_rows // 2).astype(np.uint8)

    res = bytearray(data)
    output_size_bytes = new_height * width * 4
    res[:output_size_bytes] = averaged_rows.flatten().tobytes()

    return bytes(res)

def TexMgr_AlphaEdgeFix(data: bytes, width: int, height: int) -> bytes:

    data = np.frombuffer(data, dtype=np.uint8)

    if data.dtype != np.uint8:
        data = data.astype(np.uint8)

    # 1. Reshape the 1D data into an image structure: [Height, Width, 4 (RGBA)]
    try:
        image = data.reshape(height, width, 4)
    except ValueError:
        raise ValueError("Data size does not match width * height * 4.")

    # 2. Identify Target Pixels (where Alpha is 0)
    # The 'dest[3]' check in C corresponds to pixels where image[..., 3] == 0.
    # Note: The C code uses 'if (dest[3]) continue;' meaning it only processes
    # pixels where dest[3] is FALSE (0), or where the condition is false.
    # We are looking for the pixels where the Alpha channel is 0 (fully transparent).
    is_transparent = (image[..., 3] == 0)

    # Get the (row, col) indices of all transparent pixels to be processed
    r_indices, c_indices = np.where(is_transparent)

    # Create an array of the 3D indices [row, col, :] for all transparent pixels
    target_coords = np.stack([r_indices, c_indices], axis=1)

    # 3. Iterate over the identified transparent pixels (r_i, c_i)
    # We must use a loop here because the C logic relies on neighbor-by-neighbor
    # averaging which is highly conditional and difficult to vectorize globally.
    for r_i, c_i in target_coords:

        # Determine the neighbors' coordinates with wrapping (toroidal addressing)
        # lastrow, thisrow, nextrow, etc. in C are handled by modular arithmetic.

        # Calculate indices for the 3x3 neighborhood
        r_prev = (r_i - 1) % height
        r_next = (r_i + 1) % height
        c_prev = (c_i - 1) % width
        c_next = (c_i + 1) % width

        # List of coordinates for the 8 neighbors (excluding the center target pixel)
        # This corresponds to the 8 'b = ...' lines in the C code.
        neighbor_coords = [
            (r_prev, c_prev), (r_i, c_prev), (r_next, c_prev), # Left column
            (r_prev, c_i),                  (r_next, c_i),     # Middle column (excluding center)
            (r_prev, c_next), (r_i, c_next), (r_next, c_next)  # Right column
        ]

        # Use a temporary array to gather the non-transparent neighbor colors
        temp_sum = np.zeros(3, dtype=np.uint32)
        n = 0 # Counter for non-transparent neighbors

        for r_n, c_n in neighbor_coords:
            neighbor = image[r_n, c_n]

            # Check if neighbor is non-transparent (if (data[b+3]) in C)
            if neighbor[3] > 0:
                # Accumulate RGB values (c[0], c[1], c[2] in C)
                # Use uint32 for accumulation to safely prevent overflow
                temp_sum += neighbor[:3].astype(np.uint32)
                n += 1

        # 4. Final Averaging and Assignment
        if n > 0:
            # dest[0] = (byte)(c[0]/n) in C
            avg_color = (temp_sum // n).astype(np.uint8)

            # Overwrite the RGB channels of the transparent pixel
            image[r_i, c_i, :3] = avg_color

    # The 'data' array is modified because 'image' is a view of it.
    return data.tobytes()

def TexMgr_LoadImage32(glt: gltexture_t, data):
    gl_picmip = cvar.Cvar_GetCvar('gl_picmip')

    if not gl_vidsdl.gl_texture_NPOT:
        data = TexMgr_ResampleTexture(data, glt.width, glt.height, glt.flags & TEXPREF_ALPHA)
        glt.width = TexMgr_Pad(glt.width)
        glt.height = TexMgr_Pad(glt.height)

    picmip = 0 if glt.flags & TEXPREF_NOPICMIP else max(int(gl_picmip.value), 0)
    mipwidth  = TexMgr_SafeTextureSize(glt.width  >> picmip)
    mipheight = TexMgr_SafeTextureSize(glt.height >> picmip)

    # Initial picmip reduction
    while glt.width > mipwidth:
        data = TexMgr_MipMapW(data, glt.width, glt.height)
        glt.width >>= 1
        if glt.flags & TEXPREF_ALPHA:
            TexMgr_AlphaEdgeFix(data, glt.width, glt.height)

    while glt.height > mipheight:
        data = TexMgr_MipMapH(data, glt.width, glt.height)
        glt.height >>= 1
        if glt.flags & TEXPREF_ALPHA:
            TexMgr_AlphaEdgeFix(data, glt.width, glt.height)

    GL_Bind(glt)
    internalformat = gl_alpha_format if glt.flags & TEXPREF_ALPHA else gl_solid_format

    # Upload Level 0
    OpenGL.GL.glTexImage2D(OpenGL.GL.GL_TEXTURE_2D, 0, internalformat, glt.width, glt.height, 0,
        OpenGL.GL.GL_RGBA, OpenGL.GL.GL_UNSIGNED_BYTE, data)

    # Generate Mipmap Chain
    if glt.flags & TEXPREF_MIPMAP and not (glt.flags & TEXPREF_WARPIMAGE):
        m_width = glt.width
        m_height = glt.height
        miplevel = 1

        while m_width > 1 or m_height > 1:
            if m_width > 1:
                data = TexMgr_MipMapW(data, m_width, m_height)
                m_width >>= 1
            if m_height > 1:
                data = TexMgr_MipMapH(data, m_width, m_height)
                m_height >>= 1

            # UPLOAD TO miplevel, NOT 0
            OpenGL.GL.glTexImage2D(OpenGL.GL.GL_TEXTURE_2D, miplevel, internalformat, m_width, m_height, 0,
                OpenGL.GL.GL_RGBA, OpenGL.GL.GL_UNSIGNED_BYTE, data)
            miplevel += 1

    TexMgr_SetFilterModes(glt)


def TexMgr_SafeTextureSize (s):
    gl_max_size = cvar.Cvar_GetCvar('gl_max_size')
    p = int(gl_max_size.value)

    if not gl_vidsdl.gl_texture_NPOT:
        s = TexMgr_Pad(s)

    if p > 0:
        p = TexMgr_Pad(p)
        s = min(s, p)

    s = min(s, gl_hardware_maxsize)

    return s



def TexMgr_LoadImage8(glt: gltexture_t, data: bytearray, usepal):
    padw = False
    padh = False

    padbyte = 0

    gl_fullbrights = cvar.Cvar_GetCvar('gl_fullbrights')

    if glt.flags & TEXPREF_ALPHA and not(glt.flags & TEXPREF_CONCHARS):
        for i in range(glt.width * glt.height):
            if data[i] == 255:
                break
        else:
            glt.flags &= ~TEXPREF_ALPHA

    if not usepal:
        # NEW: Check specifically for the console font flag
        if glt.flags & TEXPREF_CONCHARS:
            usepal = d_8to24table_conchars
        elif glt.flags & TEXPREF_FULLBRIGHT:
            if glt.flags & TEXPREF_ALPHA:
                usepal = d_8to24table_fbright_fence
            else:
                usepal = d_8to24table_fbright
            padbyte = 0
        elif glt.flags & TEXPREF_NOBRIGHT and gl_fullbrights.value:
            if glt.flags & TEXPREF_ALPHA:
                usepal = d_8to24table_nobright_fence
            else:
                usepal = d_8to24table_nobright
            padbyte = 0
        else:
            usepal = d_8to24table
            padbyte = 255

    if glt.flags & TEXPREF_PAD:
        if glt.width < TexMgr_SafeTextureSize(glt.width):
            data = TexMgr_PadImageW ( data, glt.width, glt.height, padbyte)
            glt.width = TexMgr_Pad(glt.width)
            padw = True

        if glt.height < TexMgr_SafeTextureSize(glt.height):
            data = TexMgr_PadImageH ( data, glt.width, glt.height, padbyte)
            glt.height = TexMgr_Pad(glt.height)
            padh = True

    data = TexMgr_8to32(data, glt.width * glt.height, usepal)

    if glt.flags & TEXPREF_ALPHA:
        pass
        #TexMgr_AlphaEdgeFix(data, glt.width, glt.height)
    else:
        if padw:
            TexMgr_PadEdgeFixW( data, glt.source_width, glt.source_height)
        if padh:
            TexMgr_PadEdgeFixH( data, glt.source_width, glt.source_height)

    TexMgr_LoadImage32(glt, data)


def TexMgr_LoadImage(owner:gl_model.qmodel_t, name, width, height, format : gl_texmgr.srcformat, data : bytes, source_file, source_offset : int, flags):

    from sys_sdl_unix import isDedicated
    if isDedicated:
        return None

    glt : gltexture_t = None

    if name == 'scrap0':
        #breakpoint()
        pass

    match format:
        case gl_texmgr.srcformat.SRC_INDEXED | gl_texmgr.srcformat.SRC_INDEXED_PALETTE:
            _crc = crc.CRC_Block(data, width * height)
        case gl_texmgr.srcformat.SRC_LIGHTMAP:
            _crc = crc.CRC_Block(data, width * height * r_brush.lightmap_bytes)
        case gl_texmgr.srcformat.SRC_RGBA:
            _crc = crc.CRC_Block(data, width * height * 4)
        case _:
            _crc = 0

    if flags & TEXPREF_OVERWRITE:
        glt = TexMgr_FindTexture(owner, name)
        if glt is not None:
            if glt.source_crc == _crc:
                return glt
        else:
            glt = TexMgr_NewTexture()
    else:
        glt = TexMgr_NewTexture()


    if glt is None:
        breakpoint()


    glt.owner = owner
    glt.name = name
    glt.width = width
    glt.height = height
    glt.flags = flags
    glt.shirt = -1
    glt.pants = -1
    glt.source_file = source_file
    glt.source_offset = source_offset
    glt.source_format = format
    glt.source_width = width
    glt.source_height = height
    glt.source_crc = _crc

    match glt.source_format:
        case gl_texmgr.srcformat.SRC_INDEXED:
            TexMgr_LoadImage8(glt, data, None)
        case gl_texmgr.srcformat.SRC_LIGHTMAP:
            TexMgr_LoadLightmap(glt, data)
        case gl_texmgr.srcformat.SRC_RGBA:
            TexMgr_LoadImage32(glt, data)
        case gl_texmgr.srcformat.SRC_INDEXED_PALETTE:
            TexMgr_LoadImage8Valve(glt, data)


    return glt

def GL_Bind(texture: gltexture_t):
    if texture is None:
        texture = nulltexture

    if texture.texnum != currenttexture[currenttarget - OpenGL.GL.GL_TEXTURE0]:
        currenttexture[currenttarget - OpenGL.GL.GL_TEXTURE0] = texture.texnum
        OpenGL.GL.glBindTexture(OpenGL.GL.GL_TEXTURE_2D, texture.texnum)
        texture.visframe = gl_rmain.r_framecount


def TexMgr_Anisotropy_f(var):
    # gl_texture_anisotropy = {'name':"gl_texture_anisotropy", 'value':"1", 'flags':cvar.CVAR_ARCHIVE};

    anisotropy = cvar.Cvar_GetCvar('gl_texture_anisotropy')
    if anisotropy.value < 1:
        cvar.Cvar_SetQuick(anisotropy, '1')
    elif anisotropy.value > gl_vidsdl.gl_max_anisotropy:
        cvar.Cvar_SetValueQuick('gl_texture_anisotropy', gl_vidsdl.gl_max_anisotropy)
    else:
        glt : gltexture_t = active_gltextures
        while glt:
            if glt.flags & TEXPREF_MIPMAP:
                OpenGL.GL.GL_Bind(glt)
            glt = glt.next

def TexMgr_TextureMode_f(var):
    global glmode_idx

    # 1. Get the current string from the cvar
    # 'var' is passed in via the callback, so we can use it directly
    mode_str = var.string.strip().strip('"').upper()

    # 2. Exact Match Check
    # Check if the string matches one of our known modes (GL_LINEAR, etc.)
    for i in range(NUM_GLMODES):
        if glmodes[i].name == mode_str:
            # If the index is already correct, do nothing (breaks recursion)
            if glmode_idx == i:
                return

            # Apply the change
            glmode_idx = i

            # Update all existing textures with the new filter modes
            glt = active_gltextures
            while glt:
                TexMgr_SetFilterModes(glt)
                glt = glt.next

            # Notify the UI (StatusBar) that graphics have changed
            sbar.Sbar_Changed()
            return

    # 3. Numeric Check (Handling "gl_texturemode 1")
    try:
        idx = int(mode_str)
        if 1 <= idx <= NUM_GLMODES:
            # Correct the cvar to the actual string name
            # This will re-trigger this function once more, hitting Step 2
            cvar.Cvar_SetQuick(var, glmodes[idx-1].name)
            return
    except ValueError:
        pass

    # 4. Fuzzy Match / Lowercase Check
    for i in range(NUM_GLMODES):
        if glmodes[i].name.lower() == mode_str.lower():
            cvar.Cvar_SetQuick(var, glmodes[i].name)
            return

    # 5. Failure Case
    console.Con_Printf(f'"{mode_str}" is not a valid texture mode\n')
    # Revert to the last known good mode
    cvar.Cvar_SetQuick(var, glmodes[glmode_idx].name)


def TexMgr_DescribeTextureModes_f():
    for i in range(NUM_GLMODES):
        console.Con_Printf(f'    {i + 1}: {glmodes[i].name}\n')
    console.Con_Printf(f'{i} modes\n')

def TexMgr_SetFilterModes(glt: gltexture_t):
    GL_Bind(glt)

    gl_texture_anisotropy = int(cvar.Cvar_GetCvar('gl_texture_anisotropy').value)

    if glt.flags & TEXPREF_NEAREST:
        OpenGL.GL.glTexParameterf(OpenGL.GL.GL_TEXTURE_2D, OpenGL.GL.GL_TEXTURE_MAG_FILTER, OpenGL.GL.GL_NEAREST)
        OpenGL.GL.glTexParameterf(OpenGL.GL.GL_TEXTURE_2D, OpenGL.GL.GL_TEXTURE_MIN_FILTER, OpenGL.GL.GL_NEAREST)
    elif glt.flags & TEXPREF_LINEAR:
        OpenGL.GL.glTexParameterf(OpenGL.GL.GL_TEXTURE_2D, OpenGL.GL.GL_TEXTURE_MAG_FILTER, OpenGL.GL.GL_LINEAR)
        OpenGL.GL.glTexParameterf(OpenGL.GL.GL_TEXTURE_2D, OpenGL.GL.GL_TEXTURE_MIN_FILTER, OpenGL.GL.GL_LINEAR)
    elif glt.flags & TEXPREF_MIPMAP:
        OpenGL.GL.glTexParameterf(OpenGL.GL.GL_TEXTURE_2D, OpenGL.GL.GL_TEXTURE_MAG_FILTER, glmodes[glmode_idx].magfilter)
        OpenGL.GL.glTexParameterf(OpenGL.GL.GL_TEXTURE_2D, OpenGL.GL.GL_TEXTURE_MIN_FILTER, glmodes[glmode_idx].minfilter)
        OpenGL.GL.glTexParameterf(OpenGL.GL.GL_TEXTURE_2D, OpenGL.GL.GL_TEXTURE_MAX_ANISOTROPY, gl_texture_anisotropy)
    else:
        # no mipmaps uploaded for this texture: a mipmap min filter would make it
        # incomplete (samples as white / disabled), so use the mag filter for both (as C does)
        OpenGL.GL.glTexParameterf(OpenGL.GL.GL_TEXTURE_2D, OpenGL.GL.GL_TEXTURE_MAG_FILTER, glmodes[glmode_idx].magfilter)
        OpenGL.GL.glTexParameterf(OpenGL.GL.GL_TEXTURE_2D, OpenGL.GL.GL_TEXTURE_MIN_FILTER, glmodes[glmode_idx].magfilter)




def TexMgr_ReloadNobrightsImages():
    glt : gltexture_t = active_gltextures

    while glt:
        if glt.flags & TEXPREF_NOBRIGHT:
            TexMgr_ReloadImage(glt, -1, -1)
        glt = glt.next


def TexMgr_Imagelist_f():
    vid_bpp = int(cvar.Cvar_GetCvar('vid_bpp').value)
    texels = 0
    glt : gltexture_t = active_gltextures

    while glt:
        console.Con_Printf(f'    {glt.width}x{glt.height} {glt.name}\n')
        if glt.flags & gl_texmgr.TEXPREF_MIPMAP:
            texels += glt.width * glt.height * 4/3
        else:
            texels += glt.width * glt.height

    mb = texels * vid_bpp / 8 / 0x100000
    console.Con_Printf(f'{numgltextures} textures {texels} {mb} megabytes\n')

def TexMgr_Imagedump_f():
    raise NotImplementedError

def TexMgr_FrameUsage() -> float:
    glt: gltexture_t = active_gltextures
    texels = 0.0

    while glt:
        if glt.visframe == gl_rmain.r_framecount:
            if glt.flags & TEXPREF_MIPMAP:
                texels += glt.width * glt.height * 4.0/3.0
            else:
                texels += glt.width * glt.height
        glt = glt.next

    mb = texels * cvar.Cvar_VariableValue('vid_bpp') / 8.0 / 0x100000
    return mb

def TexMgr_RecalcWarpImageSize():
    gl_warp.gl_warpimagesize = TexMgr_SafeTextureSize(512)

    while gl_warp.gl_warpimagesize > gl_vidsdl._vid.width:
        gl_warp.gl_warpimagesize >>= 1
    while gl_warp.gl_warpimagesize > gl_vidsdl._vid.height:
        gl_warp.gl_warpimagesize >>= 1

    dummy = bytearray(gl_warp.gl_warpimagesize * gl_warp.gl_warpimagesize * 4)

    glt : gltexture_t = active_gltextures
    while glt:
        if glt.flags & TEXPREF_WARPIMAGE:
            GL_Bind(glt)
            OpenGL.GL.glTexImage2D(OpenGL.GL.GL_TEXTURE_2D, 0, gl_solid_format, gl_warp.gl_warpimagesize, gl_warp.gl_warpimagesize, 0, OpenGL.GL.GL_RGBA, OpenGL.GL.GL_UNSIGNED_BYTE, dummy)
            glt.width = glt.height = gl_warp.gl_warpimagesize
        glt = glt.next


def TexMgr_Init():
    global free_gltextures
    global active_gltextures
    global numgltextures
    global gl_hardware_maxsize
    global currenttexture
    import glquake
    currenttexture = [glquake.GL_UNUSED_TEXTURE] * 3

    notexture_data   = bytes([159,91,83,255,0,0,0,255,0,0,0,255,159,91,83,255])
    nulltexture_data = bytes([127,191,255,255,0,0,0,255,0,0,0,255,127,191,255,255])

    active_gltextures = None
    texture_list = [ gltexture_t() for i in range (MAX_GLTEXTURES)]
    free_gltextures = texture_list[0]
    for i in range(MAX_GLTEXTURES - 1):
        if i == 0:
            free_gltextures.next = texture_list[1]
        texture_list[i].next = texture_list[i+1]

    numgltextures = 0

    TexMgr_LoadPalette()

    gl_texturemode        = {'name':"gl_texturemode",        'value':"",  'flags':cvar.CVAR_ARCHIVE};
    gl_texture_anisotropy = {'name':"gl_texture_anisotropy", 'value':"1", 'flags':cvar.CVAR_ARCHIVE};
    gl_max_size           = {'name':"gl_max_size",           'value':"0", 'flags':cvar.CVAR_NONE};
    gl_picmip             = {'name':"gl_picmip",             'value':"0", 'flags':cvar.CVAR_NONE};

    cvar.Cvar_RegisterVariable(gl_max_size)
    cvar.Cvar_RegisterVariable(gl_picmip)
    cvar.Cvar_RegisterVariable(gl_texture_anisotropy)
    cvar.Cvar_SetCallback(gl_texture_anisotropy, TexMgr_Anisotropy_f)
    cvar.Cvar_RegisterVariable(gl_texturemode)
    cvar.Cvar_GetCvar('gl_texturemode').string = glmodes[glmode_idx].name
    cvar.Cvar_SetCallback(gl_texturemode, TexMgr_TextureMode_f)

    _cmd.Cmd_AddCommand('gl_describetexturemodes', TexMgr_DescribeTextureModes_f)
    _cmd.Cmd_AddCommand('imagelist', TexMgr_Imagelist_f)
    _cmd.Cmd_AddCommand('imagedump', TexMgr_Imagedump_f)

    val = OpenGL.GL.glGetIntegerv(OpenGL.GL.GL_MAX_TEXTURE_SIZE)
    gl_hardware_maxsize = int(val)

    global nulltexture, notexture
    notexture = TexMgr_LoadImage(None, 'notexture', 2, 2, srcformat.SRC_RGBA, notexture_data, '', notexture_data,\
        TEXPREF_NEAREST | TEXPREF_PERSIST | TEXPREF_NOPICMIP )
    nulltexture = TexMgr_LoadImage(None, 'nulltexture', 2, 2, srcformat.SRC_RGBA, nulltexture_data, '', nulltexture_data,\
        TEXPREF_NEAREST | TEXPREF_PERSIST | TEXPREF_NOPICMIP )

    gl_model.r_notexture_mip  = notexture
    gl_model.r_notexture_mip2 = notexture

    gl_warp.gl_warpimagesize = 0

    TexMgr_RecalcWarpImageSize()




def TexMgr_NewGame():
    TexMgr_FreeTextures(0, TEXPREF_PERSIST)
    TexMgr_LoadPalette()



def TexMgr_ResampleTexture(
    in_buf: bytes | bytearray, inwidth: int, inheight: int, alpha: bool
) -> bytes:
    """Resamples a 32-bit RGBA texture buffer to power-of-two dimensions using 16.16

    fixed-point bilinear interpolation.

    C equivalent:
    TexMgr_ResampleTexture in gl_texmgr.c
    """
    if inwidth == gl_texmgr.TexMgr_Pad(inwidth) and inheight == gl_texmgr.TexMgr_Pad( inheight):
        return bytes(in_buf)

    outwidth = gl_texmgr.TexMgr_Pad(inwidth)
    outheight = gl_texmgr.TexMgr_Pad(inheight)

    # C equivalent: out = (unsigned *) Hunk_Alloc(outwidth*outheight*4);
    # Note: FitzQuake allocates byte-size outwidth*outheight*4 (or outwidth*outheight 32-bit pixels)
    out = bytearray(outwidth * outheight * 4)

    # 16.16 fixed-point step increments (using integer division //)
    xfrac = (
        ((inwidth - 1) << 16) // (outwidth - 1) if outwidth > 1 else 0
    ) & 0xFFFFFFFF
    yfrac = (
        ((inheight - 1) << 16) // (outheight - 1) if outheight > 1 else 0
    ) & 0xFFFFFFFF

    outjump = 0
    y = 0

    for i in range(outheight):
        mody = (y >> 8) & 0xFF
        imody = (256 - mody) & 0xFFFFFFFF
        injump = ((y >> 16) * inwidth) & 0xFFFFFFFF
        x = 0

        for j in range(outwidth):
            modx = (x >> 8) & 0xFF
            imodx = (256 - modx) & 0xFFFFFFFF

            # Pixel offset in the source buffer: (x>>16) + injump
            # Converted to byte offset by multiplying by 4 (since each pixel is 4 bytes)
            nwpx_idx = ((x >> 16) + injump) * 4

            # Pointer offsets matching C: nepx = nwpx + 4, swpx = nwpx + inwidth*4, sepx = swpx + 4
            nepx_idx = nwpx_idx + 4
            swpx_idx = nwpx_idx + (inwidth * 4)
            sepx_idx = swpx_idx + 4

            # Destination byte offset: (outjump + j) * 4
            dest_idx = (outjump + j) * 4

            # Channel 0 (Red)
            out[dest_idx] = (
                in_buf[nwpx_idx] * imodx * imody
                + in_buf[nepx_idx] * modx * imody
                + in_buf[swpx_idx] * imodx * mody
                + in_buf[sepx_idx] * modx * mody
            ) >> 16

            # Channel 1 (Green)
            out[dest_idx + 1] = (
                in_buf[nwpx_idx + 1] * imodx * imody
                + in_buf[nepx_idx + 1] * modx * imody
                + in_buf[swpx_idx + 1] * imodx * mody
                + in_buf[sepx_idx + 1] * modx * mody
            ) >> 16

            # Channel 2 (Blue)
            out[dest_idx + 2] = (
                in_buf[nwpx_idx + 2] * imodx * imody
                + in_buf[nepx_idx + 2] * modx * imody
                + in_buf[swpx_idx + 2] * imodx * mody
                + in_buf[sepx_idx + 2] * modx * mody
            ) >> 16

            # Channel 3 (Alpha)
            if alpha:
                out[dest_idx + 3] = (
                    in_buf[nwpx_idx + 3] * imodx * imody
                    + in_buf[nepx_idx + 3] * modx * imody
                    + in_buf[swpx_idx + 3] * imodx * mody
                    + in_buf[sepx_idx + 3] * modx * mody
                ) >> 16
            else:
                out[dest_idx + 3] = 255

            x = (x + xfrac) & 0xFFFFFFFF

        outjump = (outjump + outwidth) & 0xFFFFFFFF
        y = (y + yfrac) & 0xFFFFFFFF

    return bytes(out)


def TexMgr_PadEdgeFixW(data: bytearray, width: int, height: int) -> None:
    """Clones horizontal edge texels across padded texture boundaries to fix seamless texture

    wrapping, leaving the alpha channel untouched (0x00). Modifies bytearray in place.

    C equivalent:
    static void TexMgr_PadEdgeFixW (byte *data, int width, int height) in gl_texmgr.c
    """
    padw = gl_texmgr.TexMgr_PadConditional(width)
    padh = gl_texmgr.TexMgr_PadConditional(height)

    # Copy last full column to first empty column, leaving alpha byte at zero
    src_idx = (width - 1) * 4
    for _ in range(padh):
        data[src_idx + 4] = data[src_idx]      # Red
        data[src_idx + 5] = data[src_idx + 1]  # Green
        data[src_idx + 6] = data[src_idx + 2]  # Blue
        # src_idx + 7 (Alpha) remains untouched
        src_idx += padw * 4

    # Copy first full column to last empty column, leaving alpha byte at zero
    src_idx = 0
    dst_idx = (padw - 1) * 4
    for _ in range(padh):
        data[dst_idx]     = data[src_idx]      # Red
        data[dst_idx + 1] = data[src_idx + 1]  # Green
        data[dst_idx + 2] = data[src_idx + 2]  # Blue
        # dst_idx + 3 (Alpha) remains untouched
        src_idx += padw * 4
        dst_idx += padw * 4

def TexMgr_PadEdgeFixH(data: bytearray, width: int, height: int) -> None:
    """Clones vertical edge texels across padded texture boundaries to fix seamless texture

    wrapping, leaving the alpha channel untouched (0x00). Modifies bytearray in place.

    C equivalent:
    static void TexMgr_PadEdgeFixH (byte *data, int width, int height) in gl_texmgr.c
    """
    padw = gl_texmgr.TexMgr_PadConditional(width)
    padh = gl_texmgr.TexMgr_PadConditional(height)

    # Copy last full row to first empty row, leaving alpha byte at zero
    dst_idx = height * padw * 4
    src_idx = dst_idx - (padw * 4)
    for _ in range(padw):
        data[dst_idx]     = data[src_idx]      # Red
        data[dst_idx + 1] = data[src_idx + 1]  # Green
        data[dst_idx + 2] = data[src_idx + 2]  # Blue
        # dst_idx + 3 (Alpha) remains untouched
        src_idx += 4
        dst_idx += 4

    # Copy first full row to last empty row, leaving alpha byte at zero
    dst_idx = (padh - 1) * padw * 4
    src_idx = 0
    for _ in range(padw):
        data[dst_idx]     = data[src_idx]      # Red
        data[dst_idx + 1] = data[src_idx + 1]  # Green
        data[dst_idx + 2] = data[src_idx + 2]  # Blue
        # dst_idx + 3 (Alpha) remains untouched
        src_idx += 4
        dst_idx += 4



def TexMgr_PadImageW(
    in_buf: bytes | bytearray, width: int, height: int, padbyte: int
) -> bytes:
    """Pads an 8-bit indexed image buffer horizontally to power-of-two width using a fill byte.

    C equivalent:
    static byte *TexMgr_PadImageW (byte *in, int width, int height, byte padbyte) in gl_texmgr.c
    """
    outwidth = gl_texmgr.TexMgr_Pad(width)

    if width == outwidth:
        return bytes(in_buf)

    # C equivalent: out = data = (byte *) Hunk_Alloc(outwidth*height);
    out = bytearray(outwidth * height)

    in_idx = 0
    out_idx = 0

    for i in range(height):
        # Copy original row bytes (*out++ = *in++)
        for j in range(width):
            out[out_idx] = in_buf[in_idx]
            out_idx += 1
            in_idx += 1

        # Pad remaining row pixels (*out++ = padbyte)
        for j in range(width, outwidth):
            out[out_idx] = padbyte
            out_idx += 1

    return bytes(out)

def TexMgr_PadImageH(
    in_buf: bytes | bytearray, width: int, height: int, padbyte: int
) -> bytes:
    """Pads an 8-bit indexed image buffer vertically to power-of-two height using a fill byte.

    C equivalent:
    static byte *TexMgr_PadImageH (byte *in, int width, int height, byte padbyte) in gl_texmgr.c
    """
    outheight = gl_texmgr.TexMgr_Pad(height)

    if height == outheight:
        return bytes(in_buf)

    srcpix = width * height
    dstpix = width * outheight

    # C equivalent: out = data = (byte *) Hunk_Alloc(dstpix);
    out = bytearray(dstpix)

    # Copy original image texels (*out++ = *in++)
    out[:srcpix] = in_buf[:srcpix]

    # Pad remaining vertical rows (*out++ = padbyte)
    out[srcpix:dstpix] = bytes([padbyte]) * (dstpix - srcpix)

    return bytes(out)


def TexMgr_LoadImage8(
    glt: gl_texmgr.gltexture_t,
    data: bytes | bytearray,
    usepal: list[int] | None = None,
) -> None:
    """Processes, pads, palette-translates (8-to-32-bit), edge-fixes, and uploads an

    8-bit palettized texture to OpenGL.

    C equivalent:
    static void TexMgr_LoadImage8 (gltexture_t *glt, byte *data, unsigned int *usepal) in gl_texmgr.c
    """
    padw: bool = False
    padh: bool = False
    padbyte: int = 0

    # Ensure data is mutable in case of local byte modifications or hacks
    data_buf = bytearray(data)

    # HACK HACK HACK -- taken from tomazquake
    # b_shell1.bsp "shot1sid" texture corruption fix
    if (
        "shot1sid" in glt.name
        and glt.width == 32
        and glt.height == 32
        and crc.CRC_Block(data_buf, 1024) == 65393
    ):
        # Copy 32 pixels (32 bytes) from bottom row (row 31) to top row
        data_buf[:32] = data_buf[32 * 31 : 32 * 31 + 32]

    # Detect false alpha cases (strip TEXPREF_ALPHA flag if index 255 is never present)
    if (glt.flags & gl_texmgr.TEXPREF_ALPHA) and not (
        glt.flags & gl_texmgr.TEXPREF_CONCHARS
    ):
        total_pixels = glt.width * glt.height
        has_alpha_index = False
        for i in range(total_pixels):
            if data_buf[i] == 255:  # Transparent palette index
                has_alpha_index = True
                break
        if not has_alpha_index:
            glt.flags &= ~gl_texmgr.TEXPREF_ALPHA

    # Choose palette and padbyte if not explicitly provided
    if usepal is None:
        if glt.flags & gl_texmgr.TEXPREF_FULLBRIGHT:
            if glt.flags & gl_texmgr.TEXPREF_ALPHA:
                usepal = gl_texmgr.d_8to24table_fbright_fence
            else:
                usepal = gl_texmgr.d_8to24table_fbright
            padbyte = 0
        elif (
            glt.flags & gl_texmgr.TEXPREF_NOBRIGHT
        ) and cvar.Cvar_GetCvar("gl_fullbrights").value:
            if glt.flags & gl_texmgr.TEXPREF_ALPHA:
                usepal = gl_texmgr.d_8to24table_nobright_fence
            else:
                usepal = gl_texmgr.d_8to24table_nobright
            padbyte = 0
        elif glt.flags & gl_texmgr.TEXPREF_CONCHARS:
            usepal = gl_texmgr.d_8to24table_conchars
            padbyte = 0
        else:
            usepal = gl_texmgr.d_8to24table
            padbyte = 255

    # Pad each dimension, but only if it's not going to be downsampled later
    if glt.flags & gl_texmgr.TEXPREF_PAD:
        if glt.width < gl_texmgr.TexMgr_SafeTextureSize(glt.width):
            data_buf = bytearray(
                gl_texmgr.TexMgr_PadImageW(
                    data_buf, glt.width, glt.height, padbyte
                )
            )
            glt.width = gl_texmgr.TexMgr_Pad(glt.width)
            padw = True

        if glt.height < gl_texmgr.TexMgr_SafeTextureSize(glt.height):
            data_buf = bytearray(
                gl_texmgr.TexMgr_PadImageH(
                    data_buf, glt.width, glt.height, padbyte
                )
            )
            glt.height = gl_texmgr.TexMgr_Pad(glt.height)
            padh = True

    # Convert 8-bit indexed palette buffer to 32-bit RGBA buffer
    data_32 = gl_texmgr.TexMgr_8to32(
        data_buf, glt.width * glt.height, usepal
    )

    # Fix edge artifacts for transparent or padded textures
    if glt.flags & gl_texmgr.TEXPREF_ALPHA:
        gl_texmgr.TexMgr_AlphaEdgeFix(data_32, glt.width, glt.height)
    else:
        if padw:
            gl_texmgr.TexMgr_PadEdgeFixW(
                data_32, glt.source_width, glt.source_height
            )
        if padh:
            gl_texmgr.TexMgr_PadEdgeFixH(
                data_32, glt.source_width, glt.source_height
            )

    # Upload converted 32-bit RGBA image
    gl_texmgr.TexMgr_LoadImage32(glt, data_32)




def TexMgr_LoadLightmap(glt: gltexture_t, data: bytes):
    wide10bits: bool = bool(cvar.Cvar_GetCvar('r_lightmapwide').value)
    _type = OpenGL.GL.GL_UNSIGNED_INT_10_10_10_2 if wide10bits else OpenGL.GL.GL_UNSIGNED_BYTE
    internalfmt = OpenGL.GL.GL_RGB10_A2 if wide10bits else r_brush.lightmap_bytes

    GL_Bind(glt)
    OpenGL.GL.glTexImage2D(OpenGL.GL.GL_TEXTURE_2D, 0, internalfmt, glt.width, glt.height, 0, r_brush.gl_lightmap_format, _type, data)

    TexMgr_SetFilterModes(glt)



def TexMgr_ReloadImage(
    glt: gl_texmgr.gltexture_t, shirt: int = -1, pants: int = -1
) -> None:
    """Reloads texture data from disk or memory sources and updates OpenGL texture state.

    Supports player skin colormapping (shirt/pants translation) for indexed textures.

    C equivalent:
    void TexMgr_ReloadImage (gltexture_t *glt, int shirt, int pants) in gl_texmgr.c
    """
    data: bytearray | bytes | None = None

    # Load texture source buffer
    if glt.source_file and glt.source_offset:
        f: io.FileIO | None = None
        f, _, _, _ = common.COM_FOpenFile(glt.source_file)

        if f:
            f.seek(glt.source_offset, 1)  # SEEK_CUR
            size = glt.source_width * glt.source_height

            if glt.source_format == gl_texmgr.srcformat.SRC_RGBA:
                size *= 4
            elif glt.source_format == gl_texmgr.srcformat.SRC_LIGHTMAP:
                size *= r_brush.lightmap_bytes

            data = bytearray(f.read(size))
            f.close()

            if len(data) != size:
                host.Host_Error(f"read error for {glt.name}")

    elif glt.source_file and not glt.source_offset:
        (
            data,
            glt.source_width,
            glt.source_height,
        ) = image.Image_LoadImage(glt.source_file)

    elif not glt.source_file and glt.source_offset:
        # Source offset pointing directly to raw memory address
        data = glt.source_offset

    if not data:
        console.Con_Printf(
            f"TexMgr_ReloadImage: invalid source for {glt.name}\n"
        )
        return

    # Reset operating dimensions back to initial unpadded source dimensions
    glt.width = glt.source_width
    glt.height = glt.source_height

    # Validate colormap requests
    if shirt > -1 and pants > -1:
        if glt.source_format == gl_texmgr.srcformat.SRC_INDEXED:
            glt.shirt = shirt
            glt.pants = pants
        else:
            console.Con_Printf(
                f"TexMgr_ReloadImage: cant colormap a non SRC_INDEXED texture {glt.name}\n"
            )

    # Process shirt and pants player skin color translation table
    if glt.shirt > -1 and glt.pants > -1:
        translation = list(range(256))

        # Top range (shirt) translation
        shirt_val = glt.shirt * 16
        if shirt_val < 128:
            for i in range(16):
                translation[render.TOP_RANGE + i] = shirt_val + i
        else:
            for i in range(16):
                translation[render.TOP_RANGE + i] = shirt_val + 15 - i

        # Bottom range (pants) translation
        pants_val = glt.pants * 16
        if pants_val < 128:
            for i in range(16):
                translation[render.BOTTOM_RANGE + i] = pants_val + i
        else:
            for i in range(16):
                translation[render.BOTTOM_RANGE + i] = pants_val + 15 - i

        # Translate original indexed buffer into new colormapped destination buffer
        size = glt.width * glt.height
        dst = bytearray(size)
        for i in range(size):
            dst[i] = translation[data[i]]

        # Rebind translated buffer to data for uploading
        data = dst

    # Forward to target format upload loader
    match glt.source_format:
        case gl_texmgr.srcformat.SRC_INDEXED:
            gl_texmgr.TexMgr_LoadImage8(glt, data, None)
        case gl_texmgr.srcformat.SRC_LIGHTMAP:
            gl_texmgr.TexMgr_LoadLightmap(glt, data)
        case gl_texmgr.srcformat.SRC_RGBA:
            gl_texmgr.TexMgr_LoadImage32(glt, data)
        case gl_texmgr.srcformat.SRC_INDEXED_PALETTE:
            raise NotImplementedError("SRC_INDEXED_PALETTE reloading is not implemented.")



def TexMgr_ReloadImages() -> None:
    global in_reload_images
    in_reload_images = True

    glt: gl_texmgr.gltexture_t | None = gl_texmgr.active_gltextures
    while glt is not None:
        # Explicit 2-argument form passing output buffer
        tex_id = (OpenGL.GL.GLuint * 1)()
        OpenGL.GL.glGenTextures(1, tex_id)
        glt.texnum = tex_id[0]

        gl_texmgr.TexMgr_ReloadImage(glt, -1, -1)

        glt = glt.next

    in_reload_images = False


def GL_SelectTexture(target):
    global currenttarget
    if target == currenttarget:
        return

    OpenGL.GL.glActiveTexture(target)
    currenttarget = target

def GL_DisableMultitexture():
    global mtexenabled
    if mtexenabled:
        OpenGL.GL.glDisable(OpenGL.GL.GL_TEXTURE_2D)
        GL_SelectTexture(OpenGL.GL.GL_TEXTURE0)
        mtexenabled = False

def GL_EnableMultitexture():
    global mtexenabled
    if gl_vidsdl.gl_mtexable:
        GL_SelectTexture(OpenGL.GL.GL_TEXTURE1)
        OpenGL.GL.glEnable(OpenGL.GL.GL_TEXTURE_2D)
        mtexenabled = True

def GL_DeleteTexture(texture: gltexture_t):
    if not texture or not texture.texnum:
        return

    # Delete hardware OpenGL texture handle passing count and sequence/pointer
    OpenGL.GL.glDeleteTextures(1, [texture.texnum])

    # Invalidate bound texture cache state across active texture units
    if texture.texnum == currenttexture[0]:
        currenttexture[0] = glquake.GL_UNUSED_TEXTURE

    if texture.texnum == currenttexture[1]:
        currenttexture[1] = glquake.GL_UNUSED_TEXTURE

    if texture.texnum == currenttexture[2]:
        currenttexture[2] = glquake.GL_UNUSED_TEXTURE

    # Reset texture handle on the engine texture object
    texture.texnum = 0


def GL_ClearBindings():
    for i in range(3):
        currenttexture[i] = glquake.GL_UNUSED_TEXTURE