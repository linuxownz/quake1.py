#cfgfile.py  

from __future__ import annotations

import common
import cvar

cfg_file : common._fshandle_t = None

def CFG_CloseConfig(file):
    if cfg_file:
        FS_fclose(cfg_file)
        cfg_file = None

def CFG_OpenConfig(cfg_name) -> bool:
    CFG_CloseConfig()

    f, length = common.COM_FOpenFile(cfg_name, common.findfilewant.WantHandle)

    if length == -1:
        return -1

    cfg_file = common._fshandle_t(f, common.file_from_pak, f.tell(), length, 0)

    return 0

def CFG_ReadCvars(vars):
    global cfg_file

    num_vars = len(vars)

    if cfg_file is None or num_vars == 0:
        return

    j = 0

    while True:

        buff = common.FS_fgetl(cfg_file)

        if buff == '':
            break

        buff = buff.strip()
        buff = ' '.join(buff.split())

        assert(buff[-1] == '"') # must end with a "
        
        for var in vars:
            if var in buff:
                arg = buff.split()[1]
                arg.replace('"', '')
                cvar.Cvar_Set(var, arg)
            
            j += 1
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
            

