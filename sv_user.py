#sv_user.py

import progs
import quakedef

sv_player : progs.edict_t = None

forward : quakedef.vec3_t = [0., 0., 0.]
right   : quakedef.vec3_t = [0., 0., 0.]
up      : quakedef.vec3_t = [0., 0., 0.]

angles = 0.0
origin = 0.0
velocity = 0.0

onground = False

cmd : usercmd_t = None


