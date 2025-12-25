#cfgfile.py

from __future__ import annotations

import common
import cvar

cfg_file : common._fshandle_t = None

def CFG_CloseConfig():
    global cfg_file
    if cfg_file:
        common.FS_fclose(cfg_file)
        cfg_file = None

def CFG_OpenConfig(cfg_name) -> bool:
    global cfg_file

    CFG_CloseConfig()

    (handle, length, path_id, is_pak ) = common.COM_FOpenFile(cfg_name)

    f = common.COM_FileIOFromHandle(handle)

    if length == -1:
        return -1

    cfg_file = common._fshandle_t(f, is_pak, f.tell(), length, 0)

    return 0

def CFG_ReadCvars(vars):
    global cfg_file

    num_vars = len(vars)

    if cfg_file is None or num_vars == 0:
        return

    j = 0

    while True:

        buff = common.FS_fgetl(cfg_file)

        if buff is None:
            break

        buff = str(buff, encoding='ascii')
        buff = buff.strip()
        buff = ' '.join(buff.split())

        if buff == '':
            continue

        if buff[-1] != '"':
            continue

        for var in vars:
            if var in buff:
                arg = buff.split()[1]
                arg = arg.replace('"', '')
                cvar.Cvar_Set(var, arg)
                j += 1
                break

        if j == num_vars:
            break

    assert ( j == num_vars )

    common.FS_rewind(cfg_file)

def CFG_ReadCvarOverrides(vars):
    num_vars = len(vars)

    if num_vars < 1:
        return

    for var in vars:
        buff = '+' + var

        j = common.COM_CheckParm(buff)

        if j != 0 and j < com_argc - 1:
            if not com_argv[j + 1].startswith('-') and not com_argv[j + 1].startswith('+'):
                Cvar_Set(vars[i], com_argv[j+1])


