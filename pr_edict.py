#pr_edict.py

import _cmd
import console
import cvar
import host
import pr_exec
import sv_main

progs : dprograms_t = None
pr_functions : dfunction_t = None

pr_strings = ''
pr_stringssize = 0
pr_knownstrings = ''
pr_maxknownstrings = 0
pr_numknownstrings = 0
pr_fielddefs : ddef_t = None
pr_globaldefs : ddef_t = None

pr_alpha_supported = False
pr_effects_mask = 0

pr_statements : dstatement_t = None
pr_global_struct : globalvars_t = None

pr_globals = 0.0
pr_edict_size = 0

pr_crc = 0

type_size = [ 1, 1, 1, 3, 1, 1, 1, 1 ]

MAX_FIELD_LEN = 64
GEFV_CACHESIZE = 2


def ED_PrintNum(ent):
    ED_Print(EDICT_NUM(ent))

def ED_PrintEdict_f():
    if not sv_main.sv.active:
        return

    i = int(_cmd.Cmd_Argv(1))

    if i < 0 or i >= sv_main.sv.num_edicts:
        console.Con_Printf('bad edict number')
        return
    ED_PrintNum(i)

def ED_PrintEdicts_f():
    if not sv_main.sv.active:
        return

    console.Con_Printf(f'{sv_main.sv.num_edicts} entities')

    for i in range(sv_main.sv.num_edicts):
        ED_PrintNum(i)

def ED_Count():
    active = 0; models = 0; solid = 0; step = 0

    if not sv_main.sv.active:
        return

    for i in range(sv_main.sv.num_edicts):
        ent = EDICT_NUM(i)

        if ent.free:
            continue

        active += 1
        if ent.v.solid:
            solid += 1
        if ent.v.model:
            models += 1
        if ent.v.movetype == server.MOVETYPE_STEP:
            step += 1

    console.Con_Printf(f'num_edicts: {sv_main.sv.num_edicts}')
    console.Con_Printf(f'active    : {active}')
    console.Con_Printf(f'view      : {models}')
    console.Con_Printf(f'touch     : {solid}')
    console.Con_Printf(f'step      : {step}')

def ED_Nomonsters_f(cvar):
    if cvar.value:
        console.Con_Warning(f'{cvar.name} can break gameplay')

def PR_Init():
    _cmd.Cmd_AddCommand('edict', ED_PrintEdict_f)
    _cmd.Cmd_AddCommand('edicts', ED_PrintEdicts_f)
    _cmd.Cmd_AddCommand('edictcount', ED_Count)
    _cmd.Cmd_AddCommand('profile', pr_exec.PR_Profile_f)

    nomonsters   = {'name': 'nomonsters',   'value': '0', 'flags': cvar.CVAR_NONE}
    gamecfg      = {'name': 'gamecfg',      'value': '0', 'flags': cvar.CVAR_NONE}
    scratch1     = {'name': 'scratch1',     'value': '0', 'flags': cvar.CVAR_NONE}
    scratch2     = {'name': 'scratch2',     'value': '0', 'flags': cvar.CVAR_NONE}
    scratch3     = {'name': 'scratch3',     'value': '0', 'flags': cvar.CVAR_NONE}
    scratch4     = {'name': 'scratch4',     'value': '0', 'flags': cvar.CVAR_NONE}
    savedgamecfg = {'name': 'savedgamecfg', 'value': '0', 'flags': cvar.CVAR_NONE}
    saved1       = {'name': 'saved1',       'value': '0', 'flags': cvar.CVAR_NONE}
    saved2       = {'name': 'saved2',       'value': '0', 'flags': cvar.CVAR_NONE}
    saved3       = {'name': 'saved3',       'value': '0', 'flags': cvar.CVAR_NONE}
    saved4       = {'name': 'saved4',       'value': '0', 'flags': cvar.CVAR_NONE}

    cvar.Cvar_RegisterVariable(nomonsters)
    cvar.Cvar_SetCallback(nomonsters, ED_Nomonsters_f)

    cvar.Cvar_RegisterVariable(gamecfg)
    cvar.Cvar_RegisterVariable(scratch1)
    cvar.Cvar_RegisterVariable(scratch2)
    cvar.Cvar_RegisterVariable(scratch3)
    cvar.Cvar_RegisterVariable(scratch4)
    cvar.Cvar_RegisterVariable(savedgamecfg)
    cvar.Cvar_RegisterVariable(saved1)
    cvar.Cvar_RegisterVariable(saved2)
    cvar.Cvar_RegisterVariable(saved3)
    cvar.Cvar_RegisterVariable(saved4)

def EDICT_NUM(n):
    """
    Returns the edict (entity) at the specified index.
    Ported from the QuakeSpasm C source.
    """
    # 1. Bounds checking against the server's current max_edicts cvar
    if n < 0 or n >= sv_main.sv.max_edicts:
        host.Host_Error(f"EDICT_NUM: bad number {n}")

    # 2. Return the object from your edict list/array
    # In C, this is pointer arithmetic: (byte *)sv.edicts + (n * pr_edict_size)
    # In Python, this is a simple list access.
    return sv_main.sv.edicts[n]

def NUM_FOR_EDICT(e):
    """
    Returns the index (number) for a given edict object.
    Ported from host.c.
    """
    try:
        # 1. Find the index of the edict object in the server's edict list
        # This replaces the C pointer subtraction: (byte *)e - (byte *)sv.edicts
        b = sv_main.sv.edicts.index(e)
    except ValueError:
        # If the object is not in the list at all, it's a "bad pointer"
        host.Host_Error("NUM_FOR_EDICT: bad pointer")

    # 2. Bounds checking against active edicts
    if b < 0 or b >= sv_main.sv.num_edicts:
        host.Host_Error("NUM_FOR_EDICT: bad pointer")

    return b
