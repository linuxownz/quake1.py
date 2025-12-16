#gl_texmgr.py 

import OpenGL
import OpenGL.GL
import array
import numpy as np
from typing import Union

import struct
import ctypes

from enum import Enum
from enum import Flag, auto

import _cmd
import cvar
import crc
import common
import console
import glquake
import gl_model
import gl_vidsdl
import gl_texmgr
import gl_rmain
import gl_warp
import r_brush
import sys_sdl_unix

from sys_sdl_unix import isDedicated

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

d_8to24table                = array.array('B', [0] * 256)
d_8to24table_fbright        = array.array('B', [0] * 256)
d_8to24table_fbright_fence  = array.array('B', [0] * 256)
d_8to24table_nobright       = array.array('B', [0] * 256)
d_8to24table_nobright_fence = array.array('B', [0] * 256)
d_8to24table_conchars       = array.array('B', [0] * 256)

class glmode_t():
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

currenttexture = [glquake.GL_UNUSED_TEXTURE, glquake.GL_UNUSED_TEXTURE, glquake.GL_UNUSED_TEXTURE]
currenttarget = OpenGL.GL.GL_TEXTURE0
mtexenabled = False

def TexMgr_LoadPalette():
    global d_8to24table, d_8to24table_conchars, d_8to24table_fbright
    global d_8to24table_fbright_fence, d_8to24table_nobright
    global d_8to24table_nobright_fence
 
    handle, length, path_id = common.COM_FOpenFile('gfx/palette.lmp')

    f = common.COM_FileIOFromHandle(handle)

    if f is None:
        sys_sdl_unix.Sys_Error('couldnt load gfx/palette.lmp')

    pal = f.read(768)
    f.close()

    assert(len(pal) == 768)

    # google says this is wrong
    # standard paletts, 255 is transparent

    for i in range(0, 256, 4):
        d_8to24table[i + 0] = pal[i + 0]
        d_8to24table[i + 1] = pal[i + 1]
        d_8to24table[i + 2] = pal[i + 2]
        d_8to24table[i + 3] = 255

    # d_8to24table[255 + 3] = 0 # ((byte *) &d_8to24table[255]) [3] = 0;

    # fullbright palette, 0-223 are black for additive blending

    for i in range(224, 256, 4):
        d_8to24table_fbright[i + 0] = pal[i + 0]
        d_8to24table_fbright[i + 1] = pal[i + 1]
        d_8to24table_fbright[i + 2] = pal[i + 2]
        d_8to24table_fbright[i + 3] = 255

    for i in range(224):
        d_8to24table_fbright[i + 0] = 0
        d_8to24table_fbright[i + 1] = 0
        d_8to24table_fbright[i + 2] = 0
        d_8to24table_fbright[i + 3] = 255

    # nobright palette, 224-255 are black 
    for i in range(0, 256, 4):
        d_8to24table_nobright[i + 0] = pal[i + 0]
        d_8to24table_nobright[i + 1] = pal[i + 1]
        d_8to24table_nobright[i + 2] = pal[i + 2]
        d_8to24table_nobright[i + 3] = 255
    
    for i in range(224, 256, 4):
        d_8to24table_nobright[i + 0] = 0
        d_8to24table_nobright[i + 1] = 0
        d_8to24table_nobright[i + 2] = 0
        d_8to24table_nobright[i + 3] = 255


    d_8to24table_fbright_fence  = d_8to24table_fbright[:]
    d_8to24table_nobright_fence = d_8to24table_nobright[:]
    d_8to24table_conchars       = d_8to24table[:]




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
        Sys_Error('numgltextures == MAX_GLTEXTURES')

    glt = free_gltextures
    free_gltextures = glt.next

    glt.next = active_gltextures
    active_gltextures = glt

    texnum = ctypes.c_int()
    OpenGL.GL.glGenTextures(1, texnum)
    glt.texnum = texnum.value

    return glt



def TexMgr_8to32(_in, pixels, usepal):
    out = bytearray(pixels * 4)

    for i in range(pixels):
        out[i] = usepal[_in[i]]
    
    return out

def TexMgr_Pad(s):
    i = i
    while i < s:
        i <<= 1
    return i

def TexMgr_PadConditional(s):
    if s < TexMgr_SafeTextureSize(s):
        return TexMgr_Pad(s)
    return s


def TexMgr_MipMapW(data: bytes, width: int, height: int) -> np.ndarray:
    
    np_data = np.frombuffer(data, dtype=np.uint8)

    # --- Standard Validation and Calculation ---
    total_bytes = width * height * 4
    if np_data.size != total_bytes:
        raise Exception()
        # In a real application, you might raise an error here
        # or handle partial rows/images.
        pass

    num_input_bytes = (total_bytes // 8) * 8
    num_output_pixels = num_input_bytes // 8

    # 2. Reshape the relevant input data (Vectorized process begins)
    try:
        # Shape: (number of output pixels, 2 input pixels, 4 color components)
        in_view = np_data[:num_input_bytes].reshape(num_output_pixels, 2, 4)
    except ValueError as e:
        raise ValueError(f"Reshape failed: Check if W*H is an even number. Error: {e}")

    # 3. Perform the averaging
    summed_pixels = in_view.sum(axis=1, dtype=np.uint16)
    out_pixels = (summed_pixels // 2).astype(np.uint8)

    # 4. Overwrite the first half of the original array (in-place modification)
    # Since np_data is a view of the original bytes buffer (if possible), 
    # this modification happens in the memory buffer itself.
    np_data[:num_output_pixels * 4] = out_pixels.flatten()

    # 5. Return the modified NumPy array
    return np_data.tobytes()

def TexMgr_MipMapH(data, width, height):
    data = np.frombuffer(data, dtype=np.uint8)

    if data.dtype != np.uint8:
        data = data.astype(np.uint8)

    # 1. Reshape the 1D data into a 3D structure: [Rows, Pixels_Per_Row, Components]
    # We use -1 to let NumPy infer the number of rows. 
    # The image is treated as a stack of rows, where each row is W * 4 bytes.
    data_reshaped = data.reshape(height, width, 4)
    
    # Check if the height is even, as vertical averaging requires pairs of rows
    if height % 2 != 0:
        # For an odd height, the last row cannot be averaged. We proceed with 
        # the largest even number of rows that fits.
        print("Warning: Odd height, last row will be ignored for downsampling.")
    
    new_height = height // 2
    
    # 2. Reshape for vertical pairing
    # We create a view of the first (2 * new_height) rows and reshape them into pairs.
    # Shape: [new_height, 2, width, 4]
    # new_height = Number of output rows
    # 2 = The two rows being averaged (R_i and R_i+1)
    # width = Pixels per row
    # 4 = Components per pixel (RGBA)
    paired_rows = data_reshaped[:new_height * 2, ...].reshape(new_height, 2, width, 4)

    # 3. Perform the vectorized averaging
    
    # Sum the two rows (axis=1). Cast to uint16 to prevent overflow.
    summed_rows = paired_rows.sum(axis=1, dtype=np.uint16)
    
    # Integer division by 2 (equivalent to C's '>> 1') and cast back to uint8.
    averaged_rows = (summed_rows // 2).astype(np.uint8)
    
    # 4. Overwrite the first half of the original array (in-place modification)
    # The output size is new_height * width * 4 bytes
    
    # Calculate the total size of the output image in bytes
    output_size_bytes = new_height * width * 4
    
    # Overwrite the initial segment of the original 1D array
    data[:output_size_bytes] = averaged_rows.flatten()

    # Return the data (pointer equivalent)
    return data.tobytes()

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

    #print(data)
    gl_picmip = cvar.Cvar_GetCvar('gl_picmip')

    if not gl_vidsdl.gl_texture_NPOT:
        data = TexMgr_ResampleTexture(data, glt.width, glt.height, glt.flags & TEXPREF_ALPHA)
        glt.width = TexMgr_Pad(glt.width)
        glt.height = TexMgr_Pad(glt.height)

    picmip = 0 if glt.flags & TEXPREF_NOPICMIP else max(int(gl_picmip.value), 0)
    mipwidth  = TexMgr_SafeTextureSize(glt.width  >> picmip)
    mipheight = TexMgr_SafeTextureSize(glt.height >> picmip)

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

    OpenGL.GL.glTexImage2D(OpenGL.GL.GL_TEXTURE_2D, 0, internalformat, glt.width, glt.height, 0, \
        OpenGL.GL.GL_RGBA, OpenGL.GL.GL_UNSIGNED_BYTE, data)

    if glt.flags & TEXPREF_MIPMAP and not ( glt.flags & TEXPREF_WARPIMAGE):
        mipwidth = glt.width
        mipheight = glt.height

        miplevel = 1

        while mipwidth > 1 or mipheight > 1:
            if mipwidth > 1:
                TexMgr_MipMapW(data, mipwidth, mipheight)
                mipwidth >>= 1
            if mipheight > 1:
                TexMgr_MipMapH(data, mipwidth, mipheight)
                mipheight >>= 1
            
            OpenGL.GL.glTexImage2D(OpenGL.GL.GL_TEXTURE_2D, 0, internalformat, mipwidth, mipheight, 0, \
                OpenGL.GL.GL_RGBA, OpenGL.GL.GL_UNSIGNED_BYTE, data)


    TexMgr_SetFilterModes(glt)

            
def TexMgr_SafeTextureSize (s):
    gl_max_size = cvar.Cvar_GetCvar('gl_max_size')
    p = int(gl_max_size.value)

    if not gl_vidsdl.gl_texture_NPOT:
        s = TexMgr_Pad(s)

    if p > 0:
        p = TexMgr_Pad(p)
        if p < s:
            s = p
    
    if s > gl_hardware_maxsize:
        s = gl_hardware_maxsize

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
        if i == glt.width * glt.height:
            glt.flags -= TEXPREF_ALPHA

    if not usepal:
        if glt.flags & TEXPREF_FULLBRIGHT:
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
        pass


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
    gl_texture_anisotropy = {'name':"gl_texture_anisotropy", 'value':"1", 'flags':cvar.CVAR_ARCHIVE};
    anisotropy = cvar.Cvar_GetCvar('gl_texture_anisotropy').value
    if anisotropy < 1:
        cvar.Cvar_SetQuick(gl_texture_anisotropy, '1')
    elif anisotropy > gl_max_anisotropy:
        cvar.Cvar_SetValueQuick('gl_texture_anisotropy', gl_max_anisotropy)
    else:
        glt : gltexture_t = active_gltextures
        while glt:
            if glt.flags & TEXPREF_MIPMAP:
                OpenGL.GL.GL_Bind(glt)

def TexMgr_TextureMode_f(var):
    global glmode_idx

    glt : gltexture_t = None

    gl_texturemode = cvar.Cvar_GetCvar('gl_texturemode')

    for i in range(NUM_GLMODES):
        if glmodes[i].name == gl_texturemode.string:
            if glmode_idx != i:
                glmode_idx = i

                glt = active_gltextures

                while glt:
                    TexMgr_SetFilterModes(glt)
                    glt = glt.next
                Sbar_Changed()
                
            return
    for i in range(NUM_GLMODES):
        if glmodes[i].name.lower() == gl_texturemode.string.lower():
            cvar.Cvar_SetQuick(gl_texturemode, glmodes[i].name)
            return

    i = int(gl_texturemode.string)
    if i >= 1 and i <= NUM_GLMODES:
        cvar.Cvar_SetQuick(gl_texturemode, glmodes[i-1].name)
        return

    console.Con_Printf(f'{gl_texturemode.string} is not a valid texture mode\n')
    cvar.Cvar_SetQuick(gl_texturemode, glmodes[glmode_idx].name)


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
        OpenGL.GL.glTexParameterf(OpenGL.GL.GL_TEXTURE_2D, OpenGL.GL.GL_TEXTURE_MAG_FILTER, glmodes[glmode_idx].magfilter)
        OpenGL.GL.glTexParameterf(OpenGL.GL.GL_TEXTURE_2D, OpenGL.GL.GL_TEXTURE_MIN_FILTER, glmodes[glmode_idx].minfilter)
 
        




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

    notexture = TexMgr_LoadImage(None, 'notexture', 2, 2, srcformat.SRC_RGBA, notexture_data, '', notexture_data,\
        TEXPREF_NEAREST | TEXPREF_PERSIST | TEXPREF_NOPICMIP )
    nulltexture = TexMgr_LoadImage(None, 'nulltexture', 2, 2, srcformat.SRC_RGBA, nulltexture_data, '', nulltexture_data,\
        TEXPREF_NEAREST | TEXPREF_PERSIST | TEXPREF_NOPICMIP )

    gl_model.r_notexture_mip  = notexture
    gl_model.r_notexture_mip2 = notexture

    gl_warp.gl_warpimagesize = 0

    TexMgr_RecalcWarpImageSize()
   
    


 
        
