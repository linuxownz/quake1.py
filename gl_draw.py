#gl_draw.py

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import gl_texmgr
    import quakedef


import ctypes
import struct

import OpenGL.GL as gl

import cl_main
import common
import console
import gl_draw
import gl_screen
import gl_vidsdl
import gl_warp
import protocol

#import quakedef
import sbar
import sys_sdl_unix
import wad

# Evaluates to 8
size_in_bytes = ctypes.sizeof(ctypes.c_int) * 2

draw_disc     : wad.qpic_t = None
draw_backtile : wad.qpic_t = None

char_texture : gl_texmgr.gltexture_t = None

pic_ovr : wad.qpic_t = None
pic_ins : wad.qpic_t = None
pic_nul : wad.qpic_t = None
pic_crosshair : wad.qpic_t = None

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

class glpic_t:
    def __init__(self):
        self.gltexture : gl_texmgr.gltexture_t = None
        self.sl = 0.0
        self.tl = 0.0
        self.sh = 0.0
        self.th = 0.0


class cachepic_t:
    #unpack_string = f'<{MAX_QPATH}s{wad.qpic_t.unpack_string}32B'
    def __init__(self):
        self.name = ''
        self.pic : wad.qpic_t = None
        self.padding = [0 for i in range(32)]

MAX_CACHED_PICS = 128
menu_cachepics : list[cachepic_t] = [ cachepic_t() for i in range(MAX_CACHED_PICS)]
menu_numcachepics = 0

menuplyr_pixels = bytearray(4096)

MAX_SCRAPS   = 2
BLOCK_WIDTH  = 256
BLOCK_HEIGHT = 256
TEXEL_SIZE = BLOCK_WIDTH * BLOCK_HEIGHT

scrap_allocated = [[0 for i in range(BLOCK_WIDTH)] for _ in range(MAX_SCRAPS)]
scrap_texels    = [bytearray(TEXEL_SIZE) for _ in range(MAX_SCRAPS)]

scrap_dirty = False

def Draw_CachePic(path: str) -> wad.qpic_t:
    global menu_cachepics, menuplyr_pixels, menu_numcachepics

    # 1. Check existing cache
    for i in range(menu_numcachepics):
        if path == menu_cachepics[i].name:
            return menu_cachepics[i].pic

    # 2. Capacity guard
    if menu_numcachepics >= MAX_CACHED_PICS:
        sys_sdl_unix.Sys_Error('menu_numcachepics == MAX_CACHED_PICS')

    # 3. Reserve slot
    pic = menu_cachepics[menu_numcachepics]
    menu_numcachepics += 1
    pic.name = path

    # 4. Load lump file
    data = bytearray(common.COM_LoadTempFile(path, False))
    width, height = struct.unpack_from("<2i", data, 0)
    thedata = data[8 : 8 + (width * height)]

    if not thedata:
        sys_sdl_unix.Sys_Error(f'Draw_CachePic: failed to load {path}')

    dat: wad.qpic_t = wad.qpic_t(width, height, thedata)
    wad.SwapPic(dat)

    # 5. Handle player menu pixel buffer copy & calculate byte size
    size_in_bytes = dat.width * dat.height
    if path == 'gfx/menuplyr.lmp':
        menuplyr_pixels[:size_in_bytes] = dat.data[:size_in_bytes]

    pic.pic = dat
    pic.pic.width = dat.width
    pic.pic.height = dat.height

    # 6. Upload to texture manager
    glp: gl_draw.glpic_t = gl_texmgr.TexMgr_LoadImage(
        None, path, dat.width, dat.height,
        gl_texmgr.srcformat.SRC_INDEXED, dat.data, path, size_in_bytes,
        gl_texmgr.TEXPREF_ALPHA | gl_texmgr.TEXPREF_PAD | gl_texmgr.TEXPREF_NOPICMIP
    )

    # 7. Keep the qpic_t (Draw_Pic needs width/height/gl_texture/data UVs)
    dat.gl_texture = glp
    dat.data = [0.0,
                dat.width  / gl_texmgr.TexMgr_PadConditional(dat.width),
                0.0,
                dat.height / gl_texmgr.TexMgr_PadConditional(dat.height)]
    pic.pic = dat

    return pic.pic


def Scrap_Upload():
    global scrap_textures, scrap_dirty

    for i in range(MAX_SCRAPS):
        name = f'scrap{i}'

        scrap_textures[i] = \
            gl_texmgr.TexMgr_LoadImage(None, name, BLOCK_WIDTH, BLOCK_HEIGHT, \
            gl_texmgr.srcformat.SRC_INDEXED, scrap_texels[i], '', scrap_texels[i], \
            gl_texmgr.TEXPREF_ALPHA | gl_texmgr.TEXPREF_OVERWRITE | gl_texmgr.TEXPREF_NOPICMIP)

    scrap_dirty = False


def Scrap_AllocBlock(w, h) -> (int, int, int):
    x = y = 0

    for texnum in range(MAX_SCRAPS):
        best = BLOCK_HEIGHT

        for i in range(BLOCK_WIDTH - w):
            best2 = 0

            for j in range(w):
                if scrap_allocated[texnum][i + j] >= best:
                    break
                best2 = max(scrap_allocated[texnum][i + j], best2)
            else:
                # inner loop completed: all w columns fit below `best`
                x = i
                y = best = best2

        if best + h > BLOCK_HEIGHT:
            continue

        for i in range(w):
            scrap_allocated[texnum][x + i] = best + h

        return texnum, x, y

    sys_sdl_unix.Sys_Error('Scrap_AllocBlock: full')
    return 0, 0, 0

Scrap_AllocBlockFail = Scrap_AllocBlock


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
        gl.th = (y + p.height)/BLOCK_WIDTH
    else:
        texturename = wad.WADFILENAME + ':' + name

        # offset = wad.wad_base

        gl.gltexture = gl_texmgr.TexMgr_LoadImage(None, texturename, p.width, p.height, gl_texmgr.srcformat.SRC_INDEXED, data, wad.WADFILENAME, offset, \
        gl_texmgr.TEXPREF_ALPHA | gl_texmgr.TEXPREF_PAD | gl_texmgr.TEXPREF_NOPICMIP )

        gl.sl = 0
        gl.sh = p.width/gl_texmgr.TexMgr_PadConditional(p.width)
        gl.tl = 0
        gl.th = p.height/gl_texmgr.TexMgr_PadConditional(p.height)

    p.gl_texture = gl.gltexture
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
        sys_sdl_unix.Sys_Error('couldnt load conchars')

    #offset = data - wad.wad_base
    char_texture = gl_texmgr.TexMgr_LoadImage(None, wad.WADFILENAME + ':conchars', 128, 128, gl_texmgr.srcformat.SRC_INDEXED, data, wad.WADFILENAME, offset, \
        gl_texmgr.TEXPREF_ALPHA | gl_texmgr.TEXPREF_NEAREST | gl_texmgr.TEXPREF_NOPICMIP | gl_texmgr.TEXPREF_CONCHARS)

    draw_disc     = Draw_PicFromWad('disc')
    draw_backtile = Draw_PicFromWad('backtile')


def Draw_NewGame():
    global scrap_allocated, scrap_texels
    global menu_numcachepics, scrap_dirty

    scrap_allocated = [[0 for i in range(BLOCK_WIDTH)] for _ in range(MAX_SCRAPS)]
    scrap_texels    = [bytearray([255] * TEXEL_SIZE) for _ in range(MAX_SCRAPS)]
    scrap_dirty = True

    Scrap_Upload()
    wad.W_LoadWadFile('gfx.wad')
    Draw_LoadPics()

    gl_screen.SCR_LoadPics()
    sbar.Sbar_LoadPics()

    for i in range(menu_numcachepics):
        pic = menu_cachepics[i]
        pic.name = ''

    menu_numcachepics = 0

def Draw_Init():
    import quakedef
    global pic_ins, pic_ovr, pic_nul, pic_crosshair
    global scrap_textures
    global gl_texmgr, cvar
    global currentcanvas
    global scrap_textures

    import cvar
    import gl_texmgr
    import quakedef

    currentcanvas = quakedef.canvastype.CANVAS_NONE

    scrap_textures = [gl_texmgr.gltexture_t() for _ in range(MAX_SCRAPS)]

    scr_conalpha = {'name': "scr_conalpha", 'value': "0.5", 'flags': cvar.CVAR_ARCHIVE} #johnfitz
    cvar.Cvar_RegisterVariable(scr_conalpha)

    Scrap_Upload()

    pic_crosshair = Draw_MakePic('crosshair', 8, 8, pic_crosshair_data)

    pic_ins = Draw_MakePic('ins', 8, 9, pic_ins_data)
    pic_ovr = Draw_MakePic('ovr', 8, 8, pic_ovr_data)
    pic_nul = Draw_MakePic('nul', 8, 8, pic_nul_data)

    Draw_LoadPics()

def Draw_CharacterQuad(x: int, y: int, num: int | str) -> None:
    # Handle both integer character codes (e.g. 65) and single-character strings (e.g. 'A')
    char_code: int = ord(num) if isinstance(num, str) else num

    row: int = char_code >> 4
    col: int = char_code & 15

    frow: float = row * 0.0625
    fcol: float = col * 0.0625
    size: float = 0.0625

    gl.glTexCoord2f(fcol, frow)
    gl.glVertex2f(x, y)

    gl.glTexCoord2f(fcol + size, frow)
    gl.glVertex2f(x + 8, y)

    gl.glTexCoord2f(fcol + size, frow + size)
    gl.glVertex2f(x + 8, y + 8)

    gl.glTexCoord2f(fcol, frow + size)
    gl.glVertex2f(x, y + 8)



def Draw_Pic(x, y, pic):
    if scrap_dirty:
        Scrap_Upload()

    if not pic or not hasattr(pic, 'gl_texture') or pic.gl_texture is None:
        return

    gl.glEnable(gl.GL_TEXTURE_2D)
    gl_texmgr.GL_Bind(pic.gl_texture)   # keep GL_Bind's current-texture cache in sync

    gl.glEnable(gl.GL_BLEND)
    gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

    sl, sh, tl, th = pic.data

    gl.glBegin(gl.GL_QUADS)
    gl.glTexCoord2f(sl, tl); gl.glVertex2f(x, y)
    gl.glTexCoord2f(sh, tl); gl.glVertex2f(x + pic.width, y)
    gl.glTexCoord2f(sh, th); gl.glVertex2f(x + pic.width, y + pic.height)
    gl.glTexCoord2f(sl, th); gl.glVertex2f(x, y + pic.height)
    gl.glEnd()

    gl.glDisable(gl.GL_BLEND)


oldtop: int    = -2
oldbottom: int = -2
def Draw_TransPicTranslate(x:int, y:int, pic: wad.qpic_t, top:int, bottom:int):
    global oldbottom, oldtop
    if top != oldtop or bottom != oldbottom:
        glt: gl_texmgr.gltexture_t = pic.gl_texture
        oldtop = top
        oldbottom = bottom
        gl_texmgr.TexMgr_ReloadImage(glt, top, bottom)

    Draw_Pic(x, y, pic)


def Draw_ConsoleBackground():
    import quakedef
    pic: wad.qpic_t = Draw_CachePic('gfx/conback.lmp')
    pic.width  = gl_vidsdl._vid.conwidth
    pic.height = gl_vidsdl._vid.conheight

    alpha: float = 1.0 if console.con_forcedup else cvar.Cvar_GetCvar('scr_conalpha').value

    GL_SetCanvas(quakedef.canvastype.CANVAS_CONSOLE)

    if alpha > 0.0:
        if alpha < 1.0:
            gl.glEnable(gl.GL_BLEND)
            gl.glColor4f(1, 1, 1, alpha)
            gl.glDisable(gl.GL_ALPHA_TEST)
            gl.glTexEnvf(gl.GL_TEXTURE_ENV, gl.GL_TEXTURE_ENV_MODE, gl.GL_MODULATE)

        Draw_Pic(0, 0, pic)

        if alpha < 1.0:
            gl.glTexEnvf(gl.GL_TEXTURE_ENV, gl.GL_TEXTURE_ENV_MODE, gl.GL_REPLACE)
            gl.glEnable(gl.GL_ALPHA_TEST)
            gl.glDisable(gl.GL_BLEND)
            gl.glColor4f(1, 1, 1, 1)

def Draw_TileClear(x:int, y:int, w:int, h:int):
    gl.glColor3f (1,1,1)
    gl.glEnable(gl.GL_TEXTURE_2D)
    gl_texmgr.GL_Bind (draw_backtile.gl_texture)
    gl.glBegin (gl.GL_QUADS);
    gl.glTexCoord2f (x/64.0, y/64.0);
    gl.glVertex2f (x, y);
    gl.glTexCoord2f ( (x+w)/64.0, y/64.0);
    gl.glVertex2f (x+w, y);
    gl.glTexCoord2f ( (x+w)/64.0, (y+h)/64.0);
    gl.glVertex2f (x+w, y+h);
    gl.glTexCoord2f ( x/64.0, (y+h)/64.0 );
    gl.glVertex2f (x, y+h);
    gl.glEnd ()


def Draw_MakePic(name, width, height, data):
    flags = gl_texmgr.TEXPREF_NEAREST | gl_texmgr.TEXPREF_ALPHA | gl_texmgr.TEXPREF_PERSIST | gl_texmgr.TEXPREF_NOPICMIP | gl_texmgr.TEXPREF_PAD

    pic = wad.qpic_t(width, height, None)

    # Load the texture
    tex = gl_texmgr.TexMgr_LoadImage(None, name, width, height, gl_texmgr.srcformat.SRC_INDEXED,
                                     data, '', data, flags)

    # Store the texture object inside the pic so we can Bind it later
    pic.gl_texture = tex

    # Calculate UV coordinates
    sl = 0.0
    sh = float(width) / gl_texmgr.TexMgr_PadConditional(width)
    tl = 0.0
    th = float(height) / gl_texmgr.TexMgr_PadConditional(height)

    # Store UVs in the data field as a list for easy access
    pic.data = [sl, sh, tl, th]

    return pic

def Draw_Character(x, y, num):
    if y <= -8:
        return

    if isinstance(num, str):
        num = ord(num)
    num &= 255
    if num == 32:
        return

    gl.glEnable(gl.GL_TEXTURE_2D)
    gl_texmgr.GL_Bind(char_texture)
    gl.glBegin(gl.GL_QUADS)

    Draw_CharacterQuad(x, y, num)

    gl.glEnd()


def Draw_String(x, y, text):
    for i, char in enumerate(text):
        Draw_Character(x + (i * 8), y, ord(char))


def Draw_Fill(x, y, w, h, color_index):
    gl.glDisable(gl.GL_TEXTURE_2D)
    gl.glEnable(gl.GL_BLEND)

    # Check if this is the console background (usually index 200-ish)
    if color_index >= 200:
        # Dark grey with 60% opacity (0.6)
        gl.glColor4f(0.15, 0.15, 0.15, 0.6)
    else:
        # Fallback for other UI elements
        gl.glColor4f(0.5, 0.5, 0.5, 1.0)

    gl.glBegin(gl.GL_QUADS)
    gl.glVertex2f(x, y)
    gl.glVertex2f(x + w, y)
    gl.glVertex2f(x + w, y + h)
    gl.glVertex2f(x, y + h)
    gl.glEnd()

    gl.glEnable(gl.GL_TEXTURE_2D)
    gl.glColor4f(1.0, 1.0, 1.0, 1.0) # Reset to white for next draw


def Draw_FadeScreen():
    import quakedef
    GL_SetCanvas(quakedef.canvastype.CANVAS_DEFAULT)

    gl.glEnable (gl.GL_BLEND);
    gl.glDisable (gl.GL_ALPHA_TEST);
    gl.glDisable (gl.GL_TEXTURE_2D);
    gl.glColor4f (0, 0, 0, 0.5);
    gl.glBegin (gl.GL_QUADS);

    gl.glVertex2f (0,0);
    gl.glVertex2f (gl_screen.glwidth, 0);
    gl.glVertex2f (gl_screen.glwidth, gl_screen.glheight);
    gl.glVertex2f (0, gl_screen.glheight);

    gl.glEnd ();
    gl.glColor4f (1,1,1,1);
    gl.glEnable (gl.GL_TEXTURE_2D);
    gl.glEnable (gl.GL_ALPHA_TEST);
    gl.glDisable (gl.GL_BLEND);

    sbar.Sbar_Changed();

def GL_SetCanvas(newcanvas: quakedef.canvastype):
    import quakedef
    global currentcanvas

    if newcanvas == currentcanvas:
        return

    currentcanvas = newcanvas

    gl.glMatrixMode(gl.GL_PROJECTION)
    gl.glLoadIdentity()

    match newcanvas:
        case quakedef.canvastype.CANVAS_DEFAULT:
            gl.glOrtho(0, gl_screen.glwidth, gl_screen.glheight, 0, -99999, 99999)
            gl.glViewport(gl_screen.glx, gl_screen.gly, gl_screen.glwidth, gl_screen.glheight)
        case quakedef.canvastype.CANVAS_CONSOLE:
            lines = gl_vidsdl._vid.conheight - ( gl_screen.scr_con_current * gl_vidsdl._vid.conheight / gl_screen.glheight)
            gl.glOrtho(0, gl_vidsdl._vid.conwidth, gl_vidsdl._vid.conheight + lines, lines, -99999, 99999)
            gl.glViewport(gl_screen.glx, gl_screen.gly, gl_screen.glwidth, gl_screen.glheight)
        case quakedef.canvastype.CANVAS_MENU:
            s = min(gl_screen.glwidth/320, gl_screen.glheight/200)
            s = common.CLAMP(1.0, cvar.Cvar_GetCvar('scr_menuscale').value, s)
            gl.glOrtho(0, 640, 200, 0, -99999, 99999)
            gl.glViewport(int(gl_screen.glx + ( gl_screen.glwidth - 320 * s) / 2), int(gl_screen.gly + (gl_screen.glheight - 200 * s)/2), int(640 * s), int(200 * s))
        case quakedef.canvastype.CANVAS_SBAR:
            s = int(common.CLAMP(1.0, cvar.Cvar_GetCvar('scr_sbarscale').value, float(gl_screen.glwidth)/320))
            if cl_main.cl.gametype == protocol.GAME_DEATHMATCH:
                gl.glOrtho(0, gl_screen.glwidth / s, 48, 0, -99999, 99999)
                gl.glViewport(gl_screen.glx, gl_screen.gly, gl_screen.glwidth, 48 * s)
            else:
                gl.glOrtho(0, 320, 48, 0, -99999, 99999)
                gl.glViewport (gl_screen.glx + (gl_screen.glwidth - 320*s) // 2, gl_screen.gly, 320*s, 48*s)
        case quakedef.canvastype.CANVAS_WARPIMAGE:
            gl.glOrtho(0, 128, 0, 128, -99999, 99999)
            gl.glViewport(gl_screen.glx, gl_screen.gly+gl_screen.glheight-gl_warp.gl_warpimagesize, gl_warp.gl_warpimagesize, gl_warp.gl_warpimagesize)
        case quakedef.canvastype.CANVAS_CROSSHAIR:
            s = common.CLAMP(1.0, cvar.Cvar_GetCvar('scr_crosshairscale').value, 10.0)
            gl.glOrtho(gl_screen.scr_vrect.width/-2/s, gl_screen.scr_vrect.width/2/s, gl_screen.scr_vrect.height/2/s, gl_screen.scr_vrect.height/-2/s, -99999, 99999)
            gl.glViewport(gl_screen.scr_vrect.x, gl_screen.glheight - gl_screen.scr_vrect.y - gl_screen.scr_vrect.height, gl_screen.scr_vrect.width & ~1, gl_screen.scr_vrect.height & ~1)
        case quakedef.canvastype.CANVAS_BOTTOMLEFT:
            s = gl_screen.glwidth / gl_vidsdl._vid.conwidth
            gl.glOrtho(0, 320, 200, 0, -99999, 99999)
            gl.glViewport(gl_screen.glx, gl_screen.gly, int(320 * s), int(200 * s))
        case quakedef.canvastype.CANVAS_BOTTOMRIGHT:
            s = gl_screen.glwidth/gl_vidsdl._vid.conwidth
            gl.glOrtho (0, 320, 200, 0, -99999, 99999);
            gl.glViewport (gl_screen.glx+gl_screen.glwidth-int(320*s), gl_screen.gly, int(320*s), int(200*s));

        case quakedef.canvastype.CANVAS_TOPRIGHT:
            s = 1
            gl.glOrtho(0, 320, 200, 0, -99999, 99999)
            gl.glViewport(gl_screen.glx+gl_screen.glwidth-320*s, gl_screen.gly+gl_screen.glheight-200*s, 320*s, 200*s)

        case _:
            sys_sdl_unix.Sys_Error('GL_SetCanvas: bad canvas type')

    gl.glMatrixMode(gl.GL_MODELVIEW)
    gl.glLoadIdentity()

def GL_Set2D():
    import quakedef
    global currentcanvas
    currentcanvas = quakedef.canvastype.CANVAS_INVALID
    GL_SetCanvas(quakedef.canvastype.CANVAS_DEFAULT)

    gl.glDisable (gl.GL_DEPTH_TEST)
    gl.glDisable (gl.GL_CULL_FACE)
    gl.glDisable (gl.GL_BLEND)
    gl.glEnable (gl.GL_ALPHA_TEST)
    gl.glColor4f (1,1,1,1)

