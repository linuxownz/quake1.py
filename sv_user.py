#sv_user.py 

import cvar

sv_player : edict_t = None

sv_edgefriction = {'name': 'edgefriction', 'value': '2', 'flags': cvar.CVAR_NONE}

forward : vec3_t = [0., 0., 0.]
right   : vec3_t = [0., 0., 0.]
up      : vec3_t = [0., 0., 0.]

angles = 0.0
origin = 0.0
velocity = 0.0

onground = False

cmd : usercmd_t = None

sv_idealpitchscale = {'name': 'sv_idealpitchscale', 'value':'0.8', 'flags': cvar.CVAR_NONE}
sv_altnoclip       = {'name': 'sv_altnoclip', 'value':'1', 'flags': cvar.CVAR_ARCHIVE}

sv_maxspeed       = {'name': 'sv_maxspeed', 'value':'320', 'flags': cvar.CVAR_NOTIFY|cvar.CVAR_SERVERINFO}
sv_accelerate     = {'name': 'sv_accelerate', 'value':'10', 'flags': cvar.CVAR_NONE}


