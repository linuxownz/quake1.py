#chase.py
import world  # noqa: I001
import cl_main
import mathlib
import gl_rmain
import quakedef


def Chase_Init():
    global cvar
    import cvar

    chase_back   = {'name':"chase_back",  'value':"100", 'flags':cvar.CVAR_NONE};
    chase_up     = {'name':"chase_up",    'value': "16", 'flags':cvar.CVAR_NONE};
    chase_right  = {'name':"chase_right", 'value': "0",  'flags':cvar.CVAR_NONE};
    chase_active = {'name':"chase_active",'value': "0",  'flags':cvar.CVAR_NONE};

    cvar.Cvar_RegisterVariable(chase_back)
    cvar.Cvar_RegisterVariable(chase_up)
    cvar.Cvar_RegisterVariable(chase_right)
    cvar.Cvar_RegisterVariable(chase_active)

def TraceLine(start: list[float], end: list[float], impact: list[float]) -> list[float]:
    trace: world_trace_t = world.SV_RecursiveHullCHeck(cl_main.cl.worldmodel.hulls, 0, 0, 1, start, end)
    mathlib.VectorCopy(trace.endpoint, impact)
    return trace.endpos

def Chase_UpdateForDrawing():
    ideal: list[float] = 0.0
    crosshair: list[float] = 0.0
    temp: list[float] = 0.0

    forward, right, up = mathlib.AngleVectors(cl_main.cl.viewangles)

    chase_back  = cvar.Cvar_GetCvar('chase_back').value
    chase_right = cvar.Cvar_GetCvar('chase_right').value
    chase_up    = cvar.Cvar_GetCvar('chase_up').value

    for i in range(3):
        ideal[i] = cl_main.cl.viewent.origin[i] - \
            forward[i] * chase_back+ \
            right[i] * chase_right

    ideal[2] = cl_main.cl.viewent.origin[2] + chase_up

    temp = TraceLine( gl_rmain.r_refdef.vieworg, ideal)

    if mathlib.VectorLength(temp) != 0:
        mathlib.VectorCopy(temp, ideal)

    mathlib.VectorCopy(ideal, gl_rmain.r_refdef.vieworg)

    mathlib.VectorMA(cl_main.cl.viewent.origin, 1 << 20, forward, temp)
    crosshair = TraceLine(cl_main.cl.viewent.origin, temp)

    temp = mathlib.VectorSubtract(crosshair, gl_rmain.r_refdef.vieworg)
    mathlib.VectorAngles(temp, gl_rmain.r_refdef.viewangles)

    if gl_rmain.r_refdef.viewangles[quakedef.PITCH] == 90 or gl_rmain.r_refdef.viewangles[quakedef.PITCH] == -90:
        gl_rmain.r_refdef.viewangles[quakedef.YAW] = cl_main.cl.viewangles[quakedef.YAW]


