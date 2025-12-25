# sys_sdl_unix.py

import os, sys, io
import sdl2

import in_sdl
import common
import cvar
import host
import main_sdl

isDedicated = False
stdinIsATTY = False

MAX_HANDLES = 32
sys_handles : list[io.FileIO] = [None] # could be io.BufferedStream, etc TODO


__cwd = '.'
__userdir = ''

def Sys_Printf(msg):
    print(msg)

def Sys_GetBasedir():
    global __cwd

    script_path = os.path.abspath(__file__)
    __cwd = os.path.dirname(script_path)
    print(f"cwd {__cwd}")

    host.parms.basedir = __cwd

def Sys_GetUserDir():
    global __userdir
    __userdir = os.getenv("HOME")
    print(f"users' userdir is {__userdir}")
    host.parms.basedir = __userdir

def Sys_mkdir():
    print("Sys_mkdir pass")
    pass

def Sys_Init():
    global stdinIsATTY
    global isDedicated

    isDedicated = False
    if '-dedicated' in sys.argv:
        isDedicated = True
    print(f"isDedicated:{isDedicated}")

    term = os.getenv('TERM')
    
    stdinIsATTY = sys.stdin.isatty() and ( term != 'raw' or term != 'dumb' )

    if not stdinIsATTY:
        print("stdin is NOT a tty")
    else:
        print("stdin IS a tty")

    Sys_GetBasedir()
    Sys_GetUserDir()
    Sys_mkdir()

def Sys_IsDedicated():
    global isDedicated
    return isDedicated    

def Sys_DoubleTime():
    return sdl2.SDL_GetTicks() / 1000.0

def Sys_Error(msg):
    print(msg)
    host.Host_Shutdown()

    sys.exit(1)

def Sys_filelength(file: io.FileIO) -> int:
    pos = file.tell()
    file.seek(0, os.SEEK_END)
    end = file.tell()
    file.seek(pos, os.SEEK_SET)
    return end

def findhandle():
    for i in range(1, MAX_HANDLES):
        try:
            dummy = sys_handles[i]
        except IndexError:
            return i

    Sys_Error("out of handles")
    return -1

def Sys_FileOpenRead(path) -> (int, int): # return handle, file length
    i = findhandle()

    try:
        file = open(path, 'rb', buffering = 0)
    except FileNotFoundError:
        return (-1, -1)

    sys_handles.insert(i, file)

    return (i, Sys_filelength(file))

def Sys_FileOpenWrite(path) -> int: # return file handle index into sys_handles
    i = findhandle()
    try:
        file = open ( path, 'wb', buffering = False)
    except:
        Sys_Error(f"error opening file{path} for writing")

    sys_handles.insert(i, file)
    return i

def Sys_FileClose(handle) -> None:
    sys_handles[handle].close()
    sys_handles[handle] = None

def Sys_FileSeek(handle, position) -> None:
    file: io.FileIO = sys_handles[handle]
    file.seek(position, io.SEEK_SET)

def Sys_FileRead(handle, count) -> bytes:
    file: io.FileIO = sys_handles[handle]
    return file.read(count)

def Sys_FileWrite(handle, data: bytes) -> int:
    file: io.FileIO = sys_handles[handle]
    return file.write(data)

def Sys_FileType(path):
    if os.path.isdir(path):
        return common.FS_ENT_DIRECTORY
    elif os.path.isfile(path):
        return common.FS_ENT_FILE
    return common.FS_ENT_NONE

def Sys_NumCPUS() -> int:
    return 1

def Sys_SendKeyEvents():
    #in_sdl.IN_Commands()
    in_sdl.IN_SendKeyEvents()


def Sys_Quit():
    host.Host_Shutdown()
    sys.exit(0)