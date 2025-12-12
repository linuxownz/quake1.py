#!/usr/bin/python 
# main_sdl.py for main_sdl.c

import sys
import ctypes
import atexit
from sdl2 import *
#from common import COM_InitArgv
import sys_sdl_unix as unix
import host
import console
import sys_sdl_unix
import gl_vidsdl
import common

class quakeparms_t:
    def __init__(self):
        self.basedir = '.'
        self.userdir = '.'
        self.argc = 0
        self.argv = []

def Sys_AtExit():
    SDL_Quit()
    console.LOG_Close()

def Sys_InitSDL():
    version = SDL_version()
    SDL_GetVersion(version)

    print(f"SDL Version: {version.major}.{version.minor}.{version.patch}")

    if SDL_Init(0) < 0:
        #Sys_Error("Couldn't init SDL: %s" % SDL_GetError());
        print("Couldn't init SDL: %s" % SDL_GetError());
        exit(1)

    atexit.register( Sys_AtExit )

parms : quakeparms_t = quakeparms_t()
parms.basedir = '.'
parms.userdir = '.'
parms.argc = len(sys.argv)
parms.argv = sys.argv


def main():
    global parms

    # parms = quakeparms_t()
    # parms.basedir = '.'
    # parms.userdir = '.'
    # parms.argc = len(sys.argv)
    # parms.argv = sys.argv

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
                SDL_Delay(1)
                newtime = sys_sdl_unix.Sys_DoubleTime()
                time = newtime - oldtime

            host.Host_Frame(time)
            oldtime = newtime

    else:
        while True:
            if not gl_vidsdl.VID_HasMouseOrInputFocus() or cl.paused:
                SDL_Delay(16)

            if gl_vidsdl.VID_IsMinimized():
                scr_skipupdate = True
                SDL_Delay(32)
            else:
                scr_skipupdate = False

            newtime = sys_sdl_unix.Sys_DoubleTime()
            time = newtime = oldtime

            host.Host_Frame(time)

            if time < sys_throttle.value and not cls.timedemo:
                SDL_Delay(1)

            oldtime = newtime

    return 0

            

if __name__ == '__main__':
    main()

