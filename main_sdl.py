#!/usr/bin/python
# main_sdl.py for main_sdl.c

import atexit
import sys

import sdl2
import sdl2.ext

import cl_main
import common
import console
import gl_vidsdl
import host
import sv_main
import sys_sdl_unix
import sys_sdl_unix as unix


def Sys_AtExit():
    sdl2.SDL_Quit()
    console.LOG_Close()

def Sys_InitSDL():
    version = sdl2.SDL_version()
    sdl2.SDL_GetVersion(version)

    print(f"SDL Version: {version.major}.{version.minor}.{version.patch}")

    if sdl2.SDL_Init(0) < 0:
        print(f"Couldn't init SDL: {sdl2.SDL_GetError()}");
        sys.exit(1)

    atexit.register( Sys_AtExit )

def main():
    global cvar
    import cvar
    host.membase = bytearray(host.memsize)

    if host.membase is None:
        unix.Sys_Error(f"failed to alloc {host.memsize} bytes of memory")

    common.COM_InitArgv()
    Sys_InitSDL()
    unix.Sys_Init()

    print("Initializing QuakeSpasm.py v1.0")

    sys_sdl_unix.Sys_Printf('host init')
    host.Host_Init()

    oldtime = sys_sdl_unix.Sys_DoubleTime()
    if sys_sdl_unix.Sys_IsDedicated():
        while True:
            sys_ticrate = int(cvar.Cvar_GetCvar('sys_ticrate').value)
            newtime = sys_sdl_unix.Sys_DoubleTime()
            time = newtime - oldtime

            while time < sys_ticrate:
                sdl2.SDL_Delay(1)
                newtime = sys_sdl_unix.Sys_DoubleTime()
                time = newtime - oldtime

            host.Host_Frame(time)
            oldtime = newtime

    else:
        sys_throttle = float(cvar.Cvar_GetCvar('sys_throttle').value)
        while True:

            #print(f"cls.state: {cl_main.cls.state} | host_frametime: {host.host_frametime} | sv.time: {sv_main.sv.time}")


            if not gl_vidsdl.VID_HasMouseOrInputFocus() or cl_main.cl.paused:
                sdl2.SDL_Delay(16)

            if gl_vidsdl.VID_IsMinimized():
                gl_vidsdl.scr_skipupdate = True
                sdl2.SDL_Delay(32)
            else:
                gl_vidsdl.scr_skipupdate = False

            newtime = sys_sdl_unix.Sys_DoubleTime()
            time = newtime - oldtime

            host.Host_Frame(time)

            sdl2.SDL_GL_SwapWindow(gl_vidsdl.draw_context)

            if time < sys_throttle and not cl_main.cls.timedemo:
                sdl2.SDL_Delay(1)

            oldtime = newtime

    return 0

if __name__ == '__main__':
    main()
