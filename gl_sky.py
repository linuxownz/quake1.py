#gl_sky.py 

import _cmd
import console
import gl_texmgr

MAX_CLIP_VERTS  = 64

skyflatcolor = [0, 0, 0]
skymins = [[0, 0, 0, 0, 0, 0],[0, 0, 0, 0, 0, 0]]
skymaxs = [[0, 0, 0, 0, 0, 0],[0, 0, 0, 0, 0, 0]]

skybox_name = ''

skybox_textures : list[gl_texmgr.gltexture_t] = []
solidskytexture : gl_texmgr.gltexture_t = None
alphaskytexture : gl_texmgr.gltexture_t = None

skytexorder = [0,2,1,3,4,5]

skyclip = [
    [ 1,  1, 0],
    [ 1, -1, 0],
    [ 0, -1, 1],
    [ 0,  1, 1],
    [ 1,  0, 1],
    [-1,  0, 1]
]

st_to_vec = [
    [ 3, -1, 2],                        
    [-3,  1, 2],
    [ 1,  3, 2],
    [-1, -3, 2],
    [-2, -1, 3],   #straight up
    [ 2, -1,-3]    # straight down
]

vec_to_st = [
    [-2, 3,  1],
    [ 2, 3, -1],
    [ 1, 3,  2],
    [-1, 3, -2],
    [-2,-1, 3 ],
    [-2, 1, -3],
]

skyfog = 0.0

def Sky_SkyCommand_f():
    match  _cmd.Cmd_Argc():
        case 1: 
            console.Con_Printf('sky is %s' % skybox_name)
        case 2:
            Sky_LoadSkyBox(_cmd.Cmd_Argv(1))
        case _:
            console.Con_Printf('usage: sky <skyname>')

def Sky_Init():
    import cvar

    r_fastsky     = {'name':"r_fastsky",    'value':  "0", 'flags': cvar.CVAR_NONE};           
    r_sky_quality = {'name':"r_sky_quality",'value': "12", 'flags': cvar.CVAR_NONE};
    r_skyalpha    = {'name':"r_skyalpha",   'value':  "1", 'flags': cvar.CVAR_NONE};
    r_skyfog      = {'name':"r_skyfog",     'value':"0.5", 'flags': cvar.CVAR_NONE};

    cvar.Cvar_RegisterVariable(r_fastsky)
    cvar.Cvar_RegisterVariable(r_sky_quality)
    cvar.Cvar_RegisterVariable(r_skyalpha)
    cvar.Cvar_RegisterVariable(r_skyfog)

    import _cmd
    _cmd.Cmd_AddCommand('sky', Sky_SkyCommand_f)

    for i in range(6):
        skybox_textures.append(None)



