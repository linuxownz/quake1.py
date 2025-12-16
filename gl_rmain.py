#gl_rmain.py 

import gl_model
import render

modelorg    = [0, 0, 0]
r_entorigin = [0, 0, 0]

currententity : render.entity_t = None

r_visframecount = 0
r_framecount = 0

frustum : list[gl_model.mplane_t] = [ gl_model.mplane_t(0, 0, 0, 0) for i in range(4)]

rs_brushpolys       = 0
rs_aliaspolys       = 0
rs_skypolys         = 0
rs_dynamiclightmaps = 0
rs_brushpasses      = 0
rs_aliaspasses      = 0
rs_skypasses        = 0

vup       = [0, 0, 0]
vpn       = [0, 0, 0]
vright    = [0, 0, 0]
r_origin  = [0, 0, 0]

r_fovx = 0.0
r_fovy = 0.0

r_refdef : render.refdef_t = None

r_viewleaf    : gl_model.mleaf_t = None
r_oldviewleaf : gl_model.mleaf_t = None

d_lightstylevalue = [ 0 for i in range(256)]

map_wateralpha = 0
map_lavaalpha  = 0
map_telealpha  = 0
map_slimealpha = 0

r_drawflat_cheatsafe   = False
r_fullbright_cheatsafe = False
r_lightmap_cheatsafe   = False
r_drawworld_cheatsafe  = False

r_gamma_texture = 0
r_gamma_program = 0

r_gamma_texture_width = 0
r_gamma_texture_height = 0

gammaLoc = 0
contrastLoc = 0
textureLoc = 0


def gl_rmain_Init():
    import cvar

    r_norefresh           = {'name': "r_norefresh",       'value':"0",        'flags': cvar.CVAR_NONE};                                
    r_drawentities        = {'name': "r_drawentities",    'value':"1",        'flags': cvar.CVAR_NONE};
    r_drawviewmodel       = {'name': "r_drawviewmodel",   'value':"1",        'flags': cvar.CVAR_NONE};
    r_speeds              = {'name': "r_speeds",          'value':"0",        'flags': cvar.CVAR_NONE};
    r_pos                 = {'name': "r_pos",             'value':"0",        'flags': cvar.CVAR_NONE};
    r_fullbright          = {'name': "r_fullbright",      'value':"0",        'flags': cvar.CVAR_NONE};
    r_lightmap            = {'name': "r_lightmap",        'value':"0",        'flags': cvar.CVAR_NONE};
    r_shadows             = {'name': "r_shadows",         'value':"0",        'flags': cvar.CVAR_ARCHIVE};
    r_wateralpha          = {'name': "r_wateralpha",      'value':"1",        'flags': cvar.CVAR_ARCHIVE};
    r_litwater            = {'name': "r_litwater",        'value':"1",        'flags': cvar.CVAR_NONE};
    r_dynamic             = {'name': "r_dynamic",         'value':"1",        'flags': cvar.CVAR_ARCHIVE};
    r_novis               = {'name': "r_novis",           'value':"0",        'flags': cvar.CVAR_ARCHIVE};
    
    gl_finish             = {'name': "gl_finish",         'value':"0",        'flags': cvar.CVAR_NONE};
    gl_clear              = {'name': "gl_clear",          'value':"1",        'flags': cvar.CVAR_NONE};
    gl_cull               = {'name': "gl_cull",           'value':"1",        'flags': cvar.CVAR_NONE};
    gl_smoothmodels       = {'name': "gl_smoothmodels",   'value':"1",        'flags': cvar.CVAR_NONE};
    gl_affinemodels       = {'name': "gl_affinemodels",   'value':"0",        'flags': cvar.CVAR_NONE};
    gl_polyblend          = {'name': "gl_polyblend",      'value':"1",        'flags': cvar.CVAR_NONE};
    gl_flashblend         = {'name': "gl_flashblend",     'value':"0",        'flags': cvar.CVAR_ARCHIVE};
    gl_playermip          = {'name': "gl_playermip",      'value':"0",        'flags': cvar.CVAR_NONE};
    gl_nocolors           = {'name': "gl_nocolors",       'value':"0",        'flags': cvar.CVAR_NONE};
    
    r_stereo              = {'name': "r_stereo",          'value':"0",        'flags': cvar.CVAR_NONE};
    r_stereodepth         = {'name': "r_stereodepth",     'value':"128",      'flags': cvar.CVAR_NONE};
    r_clearcolor          = {'name': "r_clearcolor",      'value':"2",        'flags': cvar.CVAR_ARCHIVE};
    r_drawflat            = {'name': "r_drawflat",        'value':"0",        'flags': cvar.CVAR_NONE};
    r_flatlightstyles     = {'name': "r_flatlightstyles", 'value': "0",       'flags': cvar.CVAR_NONE};
    gl_fullbrights        = {'name': "gl_fullbrights",    'value': "1",       'flags': cvar.CVAR_ARCHIVE};
    gl_farclip            = {'name': "gl_farclip",        'value': "65536",   'flags': cvar.CVAR_ARCHIVE};
    gl_overbright         = {'name': "gl_overbright",     'value': "1",       'flags': cvar.CVAR_ARCHIVE};
    gl_overbright_models  = {'name': "gl_overbright_models", 'value': "1",    'flags': cvar.CVAR_ARCHIVE};
    r_oldskyleaf          = {'name': "r_oldskyleaf",       'value': "0",      'flags': cvar.CVAR_NONE};
    r_drawworld           = {'name': "r_drawworld",        'value': "1",      'flags': cvar.CVAR_NONE};
    r_showtris            = {'name': "r_showtris",         'value': "0",      'flags': cvar.CVAR_NONE};
    r_showbboxes          = {'name': "r_showbboxes",       'value': "0",      'flags': cvar.CVAR_NONE};
    r_lerpmodels          = {'name': "r_lerpmodels",       'value': "1",      'flags': cvar.CVAR_NONE};
    r_lerpmove            = {'name': "r_lerpmove",         'value': "1",      'flags': cvar.CVAR_NONE};
    r_nolerp_list         = {'name': "r_nolerp_list",      'value': "progs/flame.mdl,progs/flame2.mdl,progs/braztall.mdl,progs/brazshrt.mdl,progs/longtrch.mdl,progs/flame_pyre.mdl,progs/v_saw.mdl,progs/v_xfist.mdl,progs/h2stuff/newfire.mdl", 'flags' : cvar.CVAR_NONE} 
    
    r_noshadow_list       = {'name': "r_noshadow_list",    'value': "progs/flame2.mdl,progs/flame.mdl,progs/bolt1.mdl,progs/bolt2.mdl,progs/bolt3.mdl,progs/laser.mdl", 'flags':cvar.CVAR_NONE};
    
    r_lavaalpha           = {'name': "r_lavaalpha",        'value':"0",        'flags': cvar.CVAR_NONE};
    r_telealpha           = {'name': "r_telealpha",        'value':"0",        'flags': cvar.CVAR_NONE};
    r_slimealpha          = {'name': "r_slimealpha",       'value':"0",        'flags': cvar.CVAR_NONE};
    r_scale               = {'name': "r_scale",            'value': "1",       'flags': cvar.CVAR_ARCHIVE};

    import gl_rmisc
    import gl_vidsdl

    cvar.Cvar_RegisterVariable(r_norefresh)
    cvar.Cvar_RegisterVariable(r_drawentities)
    cvar.Cvar_RegisterVariable(r_drawviewmodel)
    cvar.Cvar_RegisterVariable(r_speeds)
    cvar.Cvar_RegisterVariable(r_pos)
    cvar.Cvar_RegisterVariable(r_fullbright)
    cvar.Cvar_RegisterVariable(r_lightmap)
    cvar.Cvar_RegisterVariable(r_shadows)
    cvar.Cvar_RegisterVariable(r_wateralpha)
    cvar.Cvar_SetCallback (r_wateralpha, gl_rmisc.R_SetWateralpha_f)
    cvar.Cvar_RegisterVariable(r_litwater)
    cvar.Cvar_RegisterVariable(r_dynamic)
    cvar.Cvar_RegisterVariable(r_novis)

    cvar.Cvar_RegisterVariable(gl_finish)
    cvar.Cvar_RegisterVariable(gl_clear)
    cvar.Cvar_RegisterVariable(gl_cull)
    cvar.Cvar_RegisterVariable(gl_smoothmodels)
    cvar.Cvar_RegisterVariable(gl_affinemodels)
    cvar.Cvar_RegisterVariable(gl_polyblend)
    cvar.Cvar_RegisterVariable(gl_flashblend)
    cvar.Cvar_RegisterVariable(gl_playermip)
    cvar.Cvar_RegisterVariable(gl_nocolors)

    cvar.Cvar_RegisterVariable(r_stereo)
    cvar.Cvar_RegisterVariable(r_stereodepth)
    cvar.Cvar_RegisterVariable(r_clearcolor)
    cvar.Cvar_SetCallback (r_clearcolor, gl_rmisc.R_SetClearColor_f)
    cvar.Cvar_RegisterVariable(r_drawflat)
    cvar.Cvar_RegisterVariable(r_flatlightstyles)
    cvar.Cvar_RegisterVariable(gl_fullbrights)
    cvar.Cvar_RegisterVariable(gl_farclip)
    cvar.Cvar_RegisterVariable(gl_overbright)
    cvar.Cvar_RegisterVariable(gl_overbright_models)
    cvar.Cvar_RegisterVariable(r_oldskyleaf)
    cvar.Cvar_RegisterVariable(r_drawworld)
    cvar.Cvar_RegisterVariable(r_showtris)
    cvar.Cvar_RegisterVariable(r_showbboxes)
    cvar.Cvar_RegisterVariable(r_lerpmodels)
    cvar.Cvar_RegisterVariable(r_lerpmove)
    cvar.Cvar_RegisterVariable(r_nolerp_list)

    cvar.Cvar_RegisterVariable(r_noshadow_list)

    cvar.Cvar_RegisterVariable(r_lavaalpha)
    cvar.Cvar_RegisterVariable(r_telealpha)
    cvar.Cvar_RegisterVariable(r_slimealpha)
    cvar.Cvar_RegisterVariable(r_scale)

    cvar.Cvar_SetCallback (gl_fullbrights, gl_rmisc.GL_Fullbrights_f)            
    cvar.Cvar_SetCallback (gl_overbright,  gl_rmisc.GL_Overbright_f) 

    cvar.Cvar_SetCallback (r_nolerp_list,   gl_rmisc.R_Model_ExtraFlags_List_f)
    cvar.Cvar_SetCallback (r_noshadow_list, gl_rmisc.R_Model_ExtraFlags_List_f)

    cvar.Cvar_SetROM ("r_lightmapwide", "1" if gl_vidsdl.gl_packed_pixels else "0")

    cvar.Cvar_SetCallback (r_lavaalpha,  gl_rmisc.R_SetLavaalpha_f)
    cvar.Cvar_SetCallback (r_telealpha,  gl_rmisc.R_SetTelealpha_f)
    cvar.Cvar_SetCallback (r_slimealpha, gl_rmisc.R_SetSlimealpha_f)


