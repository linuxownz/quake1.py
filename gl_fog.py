#gl_fog.py

import OpenGL
import OpenGL.GL as gl

import _cmd
import console

DEFAULT_DENSITY = 0.0
DEFAULT_GRAY    = 0.3

fog_density = 0.0
fog_red     = 0.0
fog_green   = 0.0
fog_blue    = 0.0

old_density = 0.0
old_red     = 0.0
old_green   = 0.0
old_blue    = 0.0

fade_time   = 0.0 #duration of fade
fade_done   = 0.0 #time when fade will be done

def Fog_Update ( density, red, green, blue, time ):
    global old_density, old_red, old_green, old_blue
    global fog_density, fog_red, fog_green, fog_blue
    global fade_time, fade_done

    if time > 0:
        if fade_done > client.cl.time:
            f = (fade_done - client.cl.time) / fade_time;
            old_density = f * old_density + (1.0 - f) * fog_density
            old_red     = f * old_red     + (1.0 - f) * fog_red
            old_green   = f * old_green   + (1.0 - f) * fog_green
            old_blue    = f * old_blue    + (1.0 - f) * fog_blue
        else:
            old_density = fog_density;
            old_red = fog_red;
            old_green = fog_green;
            old_blue = fog_blue;

    fog_density = density
    fog_red = red
    fog_green = green
    fog_blue = blue
    fade_time = time
    fade_done = cl.time + time


def Fog_FogCommand_f():
    d = r = g = b = t = 0
    match _cmd.Cmd_Argc():
        case _, 1:
            console.Con_Printf("usage:\n")
            console.Con_Printf("   fog <density>\n")
            console.Con_Printf("   fog <red> <green> <blue>\n")
            console.Con_Printf("   fog <density> <red> <green> <blue>\n")
            console.Con_Printf("current values:\n")
            console.Con_Printf("   \"density\" is \"%f\"\n", fog_density)
            console.Con_Printf("   \"red\" is \"%f\"\n", fog_red)
            console.Con_Printf("   \"green\" is \"%f\"\n", fog_green)
            console.Con_Printf("   \"blue\" is \"%f\"\n", fog_blue)
            return
        case 2:
            d = float(_cmd.Cmd_Argv(1))
            t = 0.0
            r = fog_red
            g = fog_green
            b = fog_blue
        case 3:
            d = float(_cmd.Cmd_Argv(1))
            t = float(_cmd.Cmd_Argv(2))
            r = fog_red
            g = fog_green
            b = fog_blue
        case 4:
            d = fog_density
            t = 0.0
            r = float(_cmd.Cmd_Argv(1))
            g = float(_cmd.Cmd_Argv(2))
            b = float(_cmd.Cmd_Argv(3))
        case 5:
            d = float(_cmd.Cmd_Argv(1))
            r = float(_cmd.Cmd_Argv(2))
            g = float(_cmd.Cmd_Argv(3))
            b = float(_cmd.Cmd_Argv(4))
            t = 0.0
        case 6:
            d = float(_cmd.Cmd_Argv(1))
            r = float(_cmd.Cmd_Argv(1))
            g = float(_cmd.Cmd_Argv(1))
            b = float(_cmd.Cmd_Argv(1))
            t = float(_cmd.Cmd_Argv(1))

    d = max(d, 0.0)

    r = max(r, 0.0)
    r = min(r, 1.0)

    g = max(g, 0.0)
    g = min(g, 1.0)

    b = max(b, 0.0)
    b = min(b, 1.0)

    Fog_Update(d, r, g, b, t)

def Fog_SetupState():
    gl.glFogi(OpenGL.GL.GL_FOG_MODE, OpenGL.GL.GL_EXP2)

def Fog_Init():
    global fog_density, fog_red, fog_green, fog_blue

    _cmd.Cmd_AddCommand('fog', Fog_FogCommand_f)

    fog_density = DEFAULT_DENSITY
    fog_red     = DEFAULT_GRAY
    fog_green   = DEFAULT_GRAY
    fog_blue    = DEFAULT_GRAY

    Fog_SetupState()

def Fog_SetupFrame():
    gl.glFogfv(gl.GL_FOG_COLOR, Fog_GetColor())
    gl.glFogf(gl.GL_FOG_DENSITY, Fog_GetDensity())


