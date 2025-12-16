#gl_draw.py 

import struct

import wad
import gl_texmgr
import screen
from quakedef import MAX_QPATH


draw_disc     : wad.qpic_t = None
draw_backtile : wad.qpic_t = None

char_texture : gl_texmgr.gltexture_t = None

pic_ovr : wad.qpic_t = None
pic_ins : wad.qpic_t = None
pic_nul : wad.qpic_t = None

pic_ovr_data = [
    255,255,255,255,255,255,255,255,
    255, 15, 15, 15, 15, 15, 15,255,
    255, 15, 15, 15, 15, 15, 15,  2,
    255, 15, 15, 15, 15, 15, 15,  2,
    255, 15, 15, 15, 15, 15, 15,  2,
    255, 15, 15, 15, 15, 15, 15,  2,
    255, 15, 15, 15, 15, 15, 15,  2,
    255,255,  2,  2,  2,  2,  2,  2,
]

pic_nul_data = [
    252,252,252,252,  0,  0,  0,  0,
    252,252,252,252,  0,  0,  0,  0,
    252,252,252,252,  0,  0,  0,  0,
    252,252,252,252,  0,  0,  0,  0,
      0,  0,  0,  0,252,252,252,252,
      0,  0,  0,  0,252,252,252,252,
      0,  0,  0,  0,252,252,252,252,
      0,  0,  0,  0,252,252,252,252,
]

pic_ins_data = [
     15, 15,255,255,255,255,255,255,
     15, 15,  2,255,255,255,255,255,
     15, 15,  2,255,255,255,255,255,
     15, 15,  2,255,255,255,255,255,
     15, 15,  2,255,255,255,255,255,
     15, 15,  2,255,255,255,255,255,
     15, 15,  2,255,255,255,255,255,
     15, 15,  2,255,255,255,255,255,
    255,  2,  2,255,255,255,255,255
]

pic_stipple_data = [
    255,  0,  0,  0,255,  0,  0,  0,
      0,  0,255,  0,  0,  0,255,  0,
    255,  0,  0,  0,255,  0,  0,  0,
      0,  0,255,  0,  0,  0,255,  0,
    255,  0,  0,  0,255,  0,  0,  0,
      0,  0,255,  0,  0,  0,255,  0,
    255,  0,  0,  0,255,  0,  0,  0,
      0,  0,255,  0,  0,  0,255,  0
]

pic_crosshair_data = [
    255,255,255,255,255,255,255,255,
    255,255,255,  8,  9,255,255,255,
    255,255,255,  6,  8,  2,255,255,
    255,  6,  8,  8,  6,  8,  8,255,
    255,255,  2,  8,  8,  2,  2,  2,
    255,255,255,  7,  8,  2,255,255,
    255,255,255,255,  2,  2,255,255,
    255,255,255,255,255,255,255,255
]

class glpic_t():
    def __init__(self):
        self.gltexture : gl_texmgr.gltexture_t = None
        self.sl = 0.0
        self.tl = 0.0
        self.sh = 0.0
        self.th = 0.0

currentcanvas : screen.canvastype = screen.canvastype.CANVAS_NONE 

class cachepic_t():
    unpack_string = f'<{MAX_QPATH}s{wad.qpic_t.unpack_string}32B'
    def __init__(self):
        self.name = ''
        self.pic : wad.qpic_t = None
        self.padding = [0 for i in range(32)]

MAX_CACHED_PIC = 128
menu_cachepics : list[cachepic_t] = [ cachepic_t() for i in range(MAX_CACHED_PIC)]
menu_numcachepics = 0

menuplyr_pixels = bytearray(4096)

MAX_SCRAPS   = 2
BLOCK_WIDTH  = 256
BLOCK_HEIGHT = 256
TEXEL_SIZE = BLOCK_WIDTH * BLOCK_HEIGHT

scrap_allocated = [[0 for i in range(BLOCK_WIDTH)] for _ in range(MAX_SCRAPS)]
scrap_texels    = [bytearray(TEXEL_SIZE) for _ in range(MAX_SCRAPS)]
scrap_textures : list[gl_texmgr.gltexture_t] = [gl_texmgr.gltexture_t() for _ in range(MAX_SCRAPS)]

scrap_dirty = False

def Draw_CachePic(path) -> wad.qpic_t:
  pass

def Scrap_Upload():
    for i in range(MAX_SCRAPS):
      name = f'scrap{i}' 

      scrap_textures[i] = \
        gl_texmgr.TexMgr_LoadImage(None, name, BLOCK_WIDTH, BLOCK_HEIGHT, \
          gl_texmgr.srcformat.SRC_INDEXED, scrap_texels[i], '', scrap_texels[i], \
            gl_texmgr.TEXPREF_ALPHA | gl_texmgr.TEXPREF_OVERWRITE | gl_texmgr.TEXPREF_NOPICMIP) 
      
      scrap_dirty = False
  

def Draw_MakePic(name, width, height, data):
    flags = gl_texmgr.TEXPREF_NEAREST | gl_texmgr.TEXPREF_ALPHA | gl_texmgr.TEXPREF_PERSIST | gl_texmgr.TEXPREF_NOPICMIP | gl_texmgr.TEXPREF_PAD

    pic = wad.qpic_t(width, height, None)

    gl = glpic_t()

    gl.gltexture = gl_texmgr.TexMgr_LoadImage(None, name, width, height, gl_texmgr.srcformat.SRC_INDEXED, \
        data, '', data, flags)
    gl.sl = 0
    gl.sh = float(width)/gl_texmgr.TexMgr_PadConditional(width)
    gl.tl = 0
    gl.th = float(height)/gl_texmgr.TexMgr_PadConditional(height)

    pic.data = struct.pack('<BBBB', gl.sl, int(gl.sh), gl.tl, int(gl.th))

    return pic


def Scrap_AllocBlock(w, h) -> (int, int, int):
    # Initialize best_x and best_y to track the best location found across all i
    best_x = -1
    best_y = BLOCK_HEIGHT # Initialize to max possible height

    for texnum in range(MAX_SCRAPS):
        # Reset best height tracker for this texture
        # NOTE: In the C code, 'best' is used for this, but it's confusingly named.
        min_required_height = BLOCK_HEIGHT 

        for i in range(BLOCK_WIDTH - w + 1): # +1 to include the last valid position
            best2 = 0 # Height of the tallest column in the current w-wide window

            for j in range(w):
                current_height = scrap_allocated[texnum][i + j]
                
                # C-break condition: if any column is too high, this position fails the overall test (Best-Fit logic is more complex)
                if current_height >= min_required_height:
                    break
                
                # Update best2: Find the tallest column in the current window
                if current_height > best2:
                    best2 = current_height

            # C condition: j == w means the inner loop completed successfully (all w columns checked)
            if j == w - 1: # Python's j loop ends at w-1, so checking j==w-1 means it completed
                
                # CRITICAL FIX: Track the *lowest* required shelf height (best2)
                if best2 < min_required_height:
                    min_required_height = best2
                    best_x = i
                    
        # After checking all 'i' positions, we have the best spot (best_x, min_required_height)

        # Check the final feasibility of the best spot found
        if min_required_height + h > BLOCK_HEIGHT:
            continue

        # Allocation: Use the stored best_x and min_required_height
        for i in range(w):
            scrap_allocated[texnum][best_x + i] = min_required_height + h
        
        return texnum, best_x, min_required_height

    # Sys_Error('Scrap_AllocBlock: full') # Replaced with standard Python exception
    raise Exception('Scrap_AllocBlock: full')

def Scrap_AllocBlockFail(w, h) -> (int, int, int):
    x = y = 0

    for texnum in range(MAX_SCRAPS):
        best = BLOCK_HEIGHT

        for i in range(BLOCK_WIDTH - w):
            best2 = 0

            for j in range(w):
                if scrap_allocated[texnum][i + j] >= best:
                    break
                if scrap_allocated[texnum][i + j] >= best2:
                    best2 = scrap_allocated[texnum][i + j]

            if j == w:
                x = i
                y = best = best2
        if best + h > BLOCK_HEIGHT:
            continue

        for i in range(w):
            scrap_allocated[texnum][x + i] = best + h
        
        return texnum, x, y

    Sys_Error('Scrap_AllocBlock: full')
    return 0

def Draw_PicFromWad(name):
    global scrap_dirty

    gl : glpic_t = glpic_t()

    data, offset = wad.W_GetLumpName(name)
    if data is None:
        return pic_nul

    p : wad.qpic_t = wad.qpic_t(struct.unpack('<I', data[0:4])[0], struct.unpack('<I', data[4:8])[0], data[8:])

    if p.width < 64 and p.height < 64:
        texnum, x, y = Scrap_AllocBlock(p.width, p.height)
        scrap_dirty = True

        k = 0
        for i in range(p.height):
            for j in range(p.width):
                scrap_texels[texnum][(y+i)*BLOCK_WIDTH + x + j] = p.data[k]
                k += 1

        gl.gltexture = scrap_textures[texnum]
        gl.sl = x/BLOCK_WIDTH
        gl.sh = (x + p.width)/BLOCK_WIDTH
        gl.tl = y/BLOCK_WIDTH
        gl.sh = (y + p.height)/BLOCK_WIDTH
    else:
        texturename = wad.WADFILENAME + ':' + name 

        # offset = wad.wad_base

        gl.gltexture = gl_texmgr.TexMgr_LoadImage(None, texturename, p.width, p.height, gl_texmgr.srcformat.SRC_INDEXED, data, wad.WADFILENAME, offset, \
        gl_texmgr.TEXPREF_ALPHA | gl_texmgr.TEXPREF_PAD | gl_texmgr.TEXPREF_NOPICMIP )

        gl.sl = 0
        gl.sh = p.width/gl_texmgr.TexMgr_PadConditional(p.width)
        gl.tl = 0
        gl.th = p.height/gl_texmgr.TexMgr_PadConditional(p.height)

    p.data = [0, 0, 0, 0]
    p.data[0] = gl.sl
    p.data[1] = gl.sh
    p.data[2] = gl.tl
    p.data[3] = gl.th

    return p


def Draw_LoadPics():
    global char_texture
    global draw_disc
    global draw_backtile

    data, offset = wad.W_GetLumpName('conchars')

    if data is None:
        Sys_Error('couldnt load conchars')

    #offset = data - wad.wad_base
    char_texture = gl_texmgr.TexMgr_LoadImage(None, wad.WADFILENAME + ':conchars', 128, 128, gl_texmgr.srcformat.SRC_INDEXED, data, wad.WADFILENAME, offset, \
        gl_texmgr.TEXPREF_ALPHA | gl_texmgr.TEXPREF_NEAREST | gl_texmgr.TEXPREF_NOPICMIP | gl_texmgr.TEXPREF_CONCHARS)

    draw_disc     = Draw_PicFromWad('disc')
    draw_backtile = Draw_PicFromWad('backtile')

def Draw_Init():
    global pic_ins, pic_ovr, pic_nul
    import cvar

    scr_conalpha = {'name': "scr_conalpha", 'value': "0.5", 'flags': cvar.CVAR_ARCHIVE} #johnfitz
    cvar.Cvar_RegisterVariable(scr_conalpha)

    Scrap_Upload()

    pic_ins = Draw_MakePic('ins', 8, 9, pic_ins_data)
    pic_ovr = Draw_MakePic('ovr', 8, 8, pic_ovr_data)
    pic_ins = Draw_MakePic('ins', 8, 8, pic_nul_data)

    Draw_LoadPics()

    