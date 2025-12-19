#!/usr/bin/python 
# main_sdl.py for main_sdl.c

import sys
import os
import atexit
import sdl2
import sdl2.ext
import ctypes

#from common import COM_InitArgv
import common
import console
import client
import gl_vidsdl
import host
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
        #Sys_Error("Couldn't init SDL: %s" % SDL_GetError());
        print("Couldn't init SDL: %s" % sdl2.SDL_GetError());
        exit(1)

    atexit.register( Sys_AtExit )

def main():
    host.membase = bytearray(host.memsize)

    if host.membase is None:
        Sys_Error("failed to alloc %d bytes of memory" % host.memsize)

    common.COM_InitArgv()
    Sys_InitSDL()
    unix.Sys_Init()

    print("Initializing QuakeSpasm.py v1.0")

    sys_sdl_unix.Sys_Printf('host init')
    host.Host_Init()

    oldtime = sys_sdl_unix.Sys_DoubleTime()
    if sys_sdl_unix.Sys_IsDedicated():
        while True:
            newtime = sys_sdl_unix.Sys_DoubleTime()
            time = newtime - oldtime

            while time < sys_ticrate.value:
                sdl2.SDL_Delay(1)
                newtime = sys_sdl_unix.Sys_DoubleTime()
                time = newtime - oldtime

            host.Host_Frame(time)
            oldtime = newtime

    else:
        while True:
            if not gl_vidsdl.VID_HasMouseOrInputFocus() or cl.paused:
                sdl2.SDL_Delay(16)

            if gl_vidsdl.VID_IsMinimized():
                scr_skipupdate = True
                sdl2.SDL_Delay(32)
            else:
                scr_skipupdate = False

            newtime = sys_sdl_unix.Sys_DoubleTime()
            time = newtime = oldtime

            host.Host_Frame(time)

            if time < sys_throttle.value and not client.cls.timedemo:
                sdl2.SDL_Delay(1)

            oldtime = newtime

    return 0

if __name__ == '__main__':
    main()
