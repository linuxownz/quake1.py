#gl_rlight.py

import cl_main
import cvar
import gl_rmain
import quakedef

r_dlightframecount = 0

def R_AnimateLight():
    i = int(cl_main.cl.time*10)
    k = 0

    r_flatlightstyles = cvar.Cvar_GetCvar('r_flatlightstyles').value
    for j in range(quakedef.MAX_LIGHTSTYLES):
        if not cl_main.cl_lightstyle[j].length:
            gl_rmain.d_lightstylevalue[j] = 256
            continue
        if r_flatlightstyles == 2:
            k = cl_main.cl_lightstyle[j].peak - ord('a')
        elif r_flatlightstyles == 1:
            k = cl_main.cl_lightstyle[j].average - ord('a')
        else:
            k = i % cl_main.cl_lightstyle[j].length
            k = cl_main.cl_lightstyle[j].map[k] - ord('a')

        gl_rmain.d_lightstylevalue[j] = k * 22


def R_PushDlights():
    global r_dlightframecount

    if cvar.Cvar_GetCvar('gl_flashblend').value:
        return

    lights = cl_main.cl_dlights

    for i in range(quakedef.MAX_DLIGHTS):
        light = lights[i]
        if light.die < cl_main.cl.time or not light.radius:
            continue
        R_MarkLights(light, i, cl_main.cl.worldmodel.nodes)



