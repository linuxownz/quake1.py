#sv_user.py 


sv_player : edict_t = None

forward : vec3_t = [0., 0., 0.]
right   : vec3_t = [0., 0., 0.]
up      : vec3_t = [0., 0., 0.]

angles = 0.0
origin = 0.0
velocity = 0.0

onground = False

cmd : usercmd_t = None


