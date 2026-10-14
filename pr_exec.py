# pr_exec.py

import struct

import console
import host
import pr_cmds
import pr_edict
import progs
import sv_main
import sys_sdl_unix


class prstack_t:
    def __init__(self):
        self.s = 0
        self.f: pr_edict.dfunction_t = None

MAX_STACK_DEPTH = 64
pr_stack: list[prstack_t] = [prstack_t() for _ in range(MAX_STACK_DEPTH)]
pr_depth = 0

LOCALSTACK_SIZE = 2048
localstack: list[int | float] = [0 for _ in range(LOCALSTACK_SIZE)]
localstack_used = 0

pr_trace = False
pr_xfunction: pr_edict.dfunction_t = None
pr_xstatement = 0
pr_argc = 0

pr_opnames: list[str] = [
    "DONE", "MUL_F", "MUL_V", "MUL_FV", "MUL_VF", "DIV", "ADD_F", "ADD_V",
    "SUB_F", "SUB_V", "EQ_F", "EQ_V", "EQ_S", "EQ_E", "EQ_FNC", "NE_F",
    "NE_V", "NE_S", "NE_E", "NE_FNC", "LE", "GE", "LT", "GT", "INDIRECT",
    "INDIRECT", "INDIRECT", "INDIRECT", "INDIRECT", "INDIRECT", "ADDRESS",
    "STORE_F", "STORE_V", "STORE_S", "STORE_ENT", "STORE_FLD", "STORE_FNC",
    "STOREP_F", "STOREP_V", "STOREP_S", "STOREP_ENT", "STOREP_FLD", "STOREP_FNC",
    "RETURN", "NOT_F", "NOT_V", "NOT_S", "NOT_ENT", "NOT_FNC", "IF", "IFNOT",
    "CALL0", "CALL1", "CALL2", "CALL3", "CALL4", "CALL5", "CALL6", "CALL7", "CALL8",
    "STATE", "GOTO", "AND", "OR", "BITAND", "BITOR"
]

ENTVARS_OFFSET_TABLE: dict[int, tuple[str, int]] = {
    0: ("modelindex", -1),
    1: ("absmin", 0), 2: ("absmin", 1), 3: ("absmin", 2),
    4: ("absmax", 0), 5: ("absmax", 1), 6: ("absmax", 2),
    7: ("ltime", -1),
    8: ("movetype", -1),
    9: ("solid", -1),
    10: ("origin", 0), 11: ("origin", 1), 12: ("origin", 2),
    13: ("oldorigin", 0), 14: ("oldorigin", 1), 15: ("oldorigin", 2),
    16: ("velocity", 0), 17: ("velocity", 1), 18: ("velocity", 2),
    19: ("angles", 0), 20: ("angles", 1), 21: ("angles", 2),
    22: ("avelocity", 0), 23: ("avelocity", 1), 24: ("avelocity", 2),
    25: ("punchangle", 0), 26: ("punchangle", 1), 27: ("punchangle", 2),
    28: ("classname", -1),
    29: ("model", -1),
    30: ("frame", -1),
    31: ("skin", -1),
    32: ("effects", -1),
    33: ("mins", 0), 34: ("mins", 1), 35: ("mins", 2),
    36: ("maxs", 0), 37: ("maxs", 1), 38: ("maxs", 2),
    39: ("size", 0), 40: ("size", 1), 41: ("size", 2),
    42: ("touch", -1),
    43: ("use", -1),
    44: ("think", -1),
    45: ("blocked", -1),
    46: ("nextthink", -1),
    47: ("groundentity", -1),
    48: ("health", -1),
    49: ("frags", -1),
    50: ("weapon", -1),
    51: ("weaponmodel", -1),
    52: ("weaponframe", -1),
    53: ("currentammo", -1),
    54: ("ammo_shells", -1),
    55: ("ammo_nails", -1),
    56: ("ammo_rockets", -1),
    57: ("ammo_cells", -1),
    58: ("items", -1),
    59: ("takedamage", -1),
    60: ("chain", -1),
    61: ("deadflag", -1),
    62: ("view_ofs", 0), 63: ("view_ofs", 1), 64: ("view_ofs", 2),
    65: ("button0", -1),
    66: ("button1", -1),
    67: ("button2", -1),
    68: ("impulse", -1),
    69: ("fixangle", -1),
    70: ("v_angle", 0), 71: ("v_angle", 1), 72: ("v_angle", 2),
    73: ("idealpitch", -1),
    74: ("netname", -1),
    75: ("enemy", -1),
    76: ("flags", -1),
    77: ("colormap", -1),
    78: ("team", -1),
    79: ("max_health", -1),
    80: ("teleport_time", -1),
    81: ("armortype", -1),
    82: ("armorvalue", -1),
    83: ("waterlevel", -1),
    84: ("watertype", -1),
    85: ("ideal_yaw", -1),
    86: ("yaw_speed", -1),
    87: ("aiment", -1),
    88: ("goalentity", -1),
    89: ("spawnflags", -1),
    90: ("target", -1),
    91: ("targetname", -1),
    92: ("dmg_take", -1),
    93: ("dmg_save", -1),
    94: ("dmg_inflictor", -1),
    95: ("owner", -1),
    96: ("movedir", 0), 97: ("movedir", 1), 98: ("movedir", 2),
    99: ("message", -1),
    100: ("sounds", -1),
    101: ("noise", -1),
    102: ("noise1", -1),
    103: ("noise2", -1),
    104: ("noise3", -1),
}


_extra_fallback: dict[int, dict[int, float | int]] = {}


def _extra(ent_v, create: bool = False):
    """Storage for field offsets outside ENTVARS_OFFSET_TABLE (QC-defined fields)."""
    ex = getattr(ent_v, '_extra', None)
    if ex is None:
        ex = _extra_fallback.get(id(ent_v))
        if ex is None and create:
            ex = {}
            try:
                ent_v._extra = ex
            except AttributeError:  # e.g. __slots__ class
                _extra_fallback[id(ent_v)] = ex
    return ex


def ClearExtraFields(ent_v) -> None:
    ex = _extra(ent_v)
    if ex:
        ex.clear()


def GetEdictFieldValue(ent_v, f_offset: int):
    """Reads one 32-bit field word by offset. Ints stay ints, floats stay floats."""
    mapping = ENTVARS_OFFSET_TABLE.get(f_offset)
    if not mapping:
        ex = _extra(ent_v)
        return ex.get(f_offset, 0) if ex else 0

    field_name, idx = mapping
    val = getattr(ent_v, field_name)

    if idx >= 0:
        return float(val[idx])
    return val


def SetEdictFieldValue(ent_v, f_offset: int, value) -> None:
    """Writes one 32-bit field word by offset, without coercing int<->float."""
    mapping = ENTVARS_OFFSET_TABLE.get(f_offset)
    if not mapping:
        _extra(ent_v, create=True)[f_offset] = value
        return

    field_name, idx = mapping
    if idx >= 0:
        getattr(ent_v, field_name)[idx] = float(value)
    else:
        current_val = getattr(ent_v, field_name)
        if (
            isinstance(current_val, int)
            and isinstance(value, float)
            and value.is_integer()
        ):
            value = int(value)
        setattr(ent_v, field_name, value)


def _s16(v: int) -> int:
    """Statement operands are stored unsigned; jump offsets are signed."""
    return v - 65536 if v & 0x8000 else v


def PR_PrintStatement(s: pr_edict.dstatement_t):
    if int(s.op) < len(pr_opnames):
        name = pr_opnames[s.op]
        console.Con_Printf(f'{name:10s}')

    if s.op in (pr_edict.OP_IF, pr_edict.OP_IFNOT):
        console.Con_Printf(f'{pr_edict.PR_GlobalString(s.a)}branch {s.b}')
    elif s.op == pr_edict.OP_GOTO:
        console.Con_Printf(f'branch {s.a}')
    elif int(s.op - pr_edict.OP_STORE_F) < 6:
        console.Con_Printf(pr_edict.PR_GlobalString(s.a))
        console.Con_Printf(pr_edict.PR_GlobalStringNoContents(s.b))
    else:
        if s.a:
            console.Con_Printf(pr_edict.PR_GlobalString(s.a))
        if s.b:
            console.Con_Printf(pr_edict.PR_GlobalString(s.b))
        if s.c:
            console.Con_Printf(pr_edict.PR_GlobalString(s.c))
    console.Con_Printf('\n')


def PR_StackTrace():
    if pr_depth == 0:
        console.Con_Printf('<NO STACK>\n')
        return

    pr_stack[pr_depth].f = pr_xfunction
    for i in range(pr_depth, -1, -1):
        f = pr_stack[i].f
        if not f:
            console.Con_Printf('<NO FUNCTION>\n')
        else:
            console.Con_Printf(f'{pr_edict.PR_GetString(f.s_file):12s} : {pr_edict.PR_GetString(f.s_name)}\n')


def PR_RunError(error):
    global pr_depth
    PR_PrintStatement(pr_edict.pr_statements[pr_xstatement])
    PR_StackTrace()
    console.Con_Printf(f'{error}\n')
    pr_depth = 0
    host.Host_Error('Program error')


def PR_EnterFunction(f: pr_edict.dfunction_t) -> int:
    global pr_depth, localstack_used, pr_xfunction

    pr_stack[pr_depth].s = pr_xstatement
    pr_stack[pr_depth].f = pr_xfunction

    pr_depth += 1
    if pr_depth >= MAX_STACK_DEPTH:
        PR_RunError('stack overflow')

    c = f.locals
    if localstack_used + c > LOCALSTACK_SIZE:
        PR_RunError('PR_ExecuteProgram: locals stack overflow')

    # Save caller locals onto localstack
    for i in range(c):
        localstack[localstack_used + i] = pr_edict.pr_globals[f.parm_start + i]
    localstack_used += c

    # Map passed parameters into target function locals
    o = f.parm_start
    for i in range(f.numparms):
        for j in range(f.parm_size[i]):
            pr_edict.pr_globals[o] = pr_edict.pr_globals[pr_edict.OFS_PARM0 + i * 3 + j]
            o += 1

    pr_xfunction = f
    return f.first_statement - 1


def PR_LeaveFunction() -> int:
    global localstack_used, pr_depth, pr_xfunction

    if pr_depth <= 0:
        host.Host_Error('prog stack underflow')

    c = pr_xfunction.locals
    localstack_used -= c
    if localstack_used < 0:
        PR_RunError('PR_ExecuteProgram: locals stack underflow')

    # Restore saved caller locals
    for i in range(c):
        pr_edict.pr_globals[pr_xfunction.parm_start + i] = localstack[localstack_used + i]

    pr_depth -= 1
    pr_xfunction = pr_stack[pr_depth].f
    return pr_stack[pr_depth].s


def G_STR(idx):
    offset = int(pr_edict.pr_globals[idx])
    return pr_edict.PR_GetString(offset) if offset else ""


def PR_ExecuteProgram(fnum: int) -> None:
    """Executes a QuakeC program entry point or function."""
    global pr_depth, pr_xstatement, pr_xfunction, pr_trace, pr_argc

    if not fnum or fnum < 0 or fnum >= len(pr_edict.pr_functions):
        # parm0 is not a string, so the old message printed garbage ("bjerror").
        # Print who asked for function 0 instead. Still non-fatal, like before.
        import traceback

        self_n = int(pr_edict.pr_globals[pr_edict.OFS_SELF])
        print(f"PR_ExecuteProgram: NULL function (fnum={fnum!r}, self={self_n}); requested by:")
        traceback.print_stack(limit=5)
        return

    f = pr_edict.pr_functions[fnum]

    # Enter root function
    exit_depth = pr_depth
    s = PR_EnterFunction(f)

    while True:
        s += 1
        st = pr_edict.pr_statements[s]
        pr_xstatement = s

        if pr_trace:
            PR_PrintStatement(st)

        op = st.op
        a, b, c = st.a & 0xFFFF, st.b & 0xFFFF, st.c & 0xFFFF

        if op == pr_edict.OP_DONE or op == pr_edict.OP_RETURN:
            pr_edict.pr_globals[pr_edict.OFS_RETURN] = pr_edict.pr_globals[a]
            pr_edict.pr_globals[pr_edict.OFS_RETURN + 1] = pr_edict.pr_globals[a + 1]
            pr_edict.pr_globals[pr_edict.OFS_RETURN + 2] = pr_edict.pr_globals[a + 2]

            s = PR_LeaveFunction()
            if pr_depth == exit_depth:
                return

        elif op == pr_edict.OP_MUL_F:
            pr_edict.pr_globals[c] = pr_edict.pr_globals[a] * pr_edict.pr_globals[b]

        elif op == pr_edict.OP_MUL_V:
            # vector * vector = dot product (float result)
            pr_edict.pr_globals[c] = (
                pr_edict.pr_globals[a] * pr_edict.pr_globals[b]
                + pr_edict.pr_globals[a + 1] * pr_edict.pr_globals[b + 1]
                + pr_edict.pr_globals[a + 2] * pr_edict.pr_globals[b + 2]
            )

        elif op == pr_edict.OP_MUL_FV:
            pr_edict.pr_globals[c] = pr_edict.pr_globals[a] * pr_edict.pr_globals[b]
            pr_edict.pr_globals[c + 1] = pr_edict.pr_globals[a] * pr_edict.pr_globals[b + 1]
            pr_edict.pr_globals[c + 2] = pr_edict.pr_globals[a] * pr_edict.pr_globals[b + 2]

        elif op == pr_edict.OP_MUL_VF:
            pr_edict.pr_globals[c] = pr_edict.pr_globals[a] * pr_edict.pr_globals[b]
            pr_edict.pr_globals[c + 1] = pr_edict.pr_globals[a + 1] * pr_edict.pr_globals[b]
            pr_edict.pr_globals[c + 2] = pr_edict.pr_globals[a + 2] * pr_edict.pr_globals[b]

        elif op == pr_edict.OP_DIV_F:
            _num, _den = pr_edict.pr_globals[a], pr_edict.pr_globals[b]
            if _den:
                pr_edict.pr_globals[c] = _num / _den
            elif _num:
                pr_edict.pr_globals[c] = float('inf') if _num > 0 else float('-inf')
            else:
                pr_edict.pr_globals[c] = float('nan')

        elif op == pr_edict.OP_ADD_F:
            pr_edict.pr_globals[c] = pr_edict.pr_globals[a] + pr_edict.pr_globals[b]

        elif op == pr_edict.OP_ADD_V:
            pr_edict.pr_globals[c] = pr_edict.pr_globals[a] + pr_edict.pr_globals[b]
            pr_edict.pr_globals[c + 1] = pr_edict.pr_globals[a + 1] + pr_edict.pr_globals[b + 1]
            pr_edict.pr_globals[c + 2] = pr_edict.pr_globals[a + 2] + pr_edict.pr_globals[b + 2]

        elif op == pr_edict.OP_SUB_F:
            pr_edict.pr_globals[c] = pr_edict.pr_globals[a] - pr_edict.pr_globals[b]

        elif op == pr_edict.OP_SUB_V:
            pr_edict.pr_globals[c] = pr_edict.pr_globals[a] - pr_edict.pr_globals[b]
            pr_edict.pr_globals[c + 1] = pr_edict.pr_globals[a + 1] - pr_edict.pr_globals[b + 1]
            pr_edict.pr_globals[c + 2] = pr_edict.pr_globals[a + 2] - pr_edict.pr_globals[b + 2]

        elif op == pr_edict.OP_EQ_F:
            pr_edict.pr_globals[c] = float(pr_edict.pr_globals[a] == pr_edict.pr_globals[b])

        elif op == pr_edict.OP_EQ_V:
            pr_edict.pr_globals[c] = float(
                pr_edict.pr_globals[a] == pr_edict.pr_globals[b] and
                pr_edict.pr_globals[a + 1] == pr_edict.pr_globals[b + 1] and
                pr_edict.pr_globals[a + 2] == pr_edict.pr_globals[b + 2]
            )

        elif op == pr_edict.OP_EQ_S:
            pr_edict.pr_globals[c] = float(G_STR(a) == G_STR(b))

        elif op == pr_edict.OP_EQ_E or op == pr_edict.OP_EQ_FNC:
            pr_edict.pr_globals[c] = float(int(pr_edict.pr_globals[a]) == int(pr_edict.pr_globals[b]))

        elif op == pr_edict.OP_NE_F:
            pr_edict.pr_globals[c] = float(pr_edict.pr_globals[a] != pr_edict.pr_globals[b])

        elif op == pr_edict.OP_NE_V:
            pr_edict.pr_globals[c] = float(
                pr_edict.pr_globals[a] != pr_edict.pr_globals[b] or
                pr_edict.pr_globals[a + 1] != pr_edict.pr_globals[b + 1] or
                pr_edict.pr_globals[a + 2] != pr_edict.pr_globals[b + 2]
            )

        elif op == pr_edict.OP_NE_S:
            pr_edict.pr_globals[c] = float(G_STR(a) != G_STR(b))

        elif op == pr_edict.OP_NE_E or op == pr_edict.OP_NE_FNC:
            pr_edict.pr_globals[c] = float(int(pr_edict.pr_globals[a]) != int(pr_edict.pr_globals[b]))

        elif op == pr_edict.OP_LE:
            pr_edict.pr_globals[c] = float(pr_edict.pr_globals[a] <= pr_edict.pr_globals[b])

        elif op == pr_edict.OP_GE:
            pr_edict.pr_globals[c] = float(pr_edict.pr_globals[a] >= pr_edict.pr_globals[b])

        elif op == pr_edict.OP_LT:
            pr_edict.pr_globals[c] = float(pr_edict.pr_globals[a] < pr_edict.pr_globals[b])

        elif op == pr_edict.OP_GT:
            pr_edict.pr_globals[c] = float(pr_edict.pr_globals[a] > pr_edict.pr_globals[b])

        elif op in (
            pr_edict.OP_LOAD_F,
            pr_edict.OP_LOAD_S,
            pr_edict.OP_LOAD_ENT,
            pr_edict.OP_LOAD_FLD,
            pr_edict.OP_LOAD_FNC,
        ):
            ent = sv_main.sv.edicts[int(pr_edict.pr_globals[a])]
            f_offset = int(pr_edict.pr_globals[b])  # value of global B is the field offset
            pr_edict.pr_globals[c] = GetEdictFieldValue(ent.v, f_offset)

        elif op == pr_edict.OP_LOAD_V:
            ent_num = int(pr_edict.pr_globals[a])
            ent = sv_main.sv.edicts[ent_num]
            f_offset = int(pr_edict.pr_globals[b])
            pr_edict.pr_globals[c] = GetEdictFieldValue(ent.v, f_offset)
            pr_edict.pr_globals[c + 1] = GetEdictFieldValue(ent.v, f_offset + 1)
            pr_edict.pr_globals[c + 2] = GetEdictFieldValue(ent.v, f_offset + 2)

        elif op == pr_edict.OP_ADDRESS:
            ent_num = int(pr_edict.pr_globals[a])
            f_offset = int(pr_edict.pr_globals[b])
            # Quake VM address calculation: (edict_num * entityfields) + field_offset
            pr_edict.pr_globals[c] = (ent_num * pr_edict.progz.entityfields) + f_offset

        elif op in (
            pr_edict.OP_STORE_F,
            pr_edict.OP_STORE_S,
            pr_edict.OP_STORE_ENT,
            pr_edict.OP_STORE_FLD,
            pr_edict.OP_STORE_FNC,
        ):
            pr_edict.pr_globals[b] = pr_edict.pr_globals[a]

        elif op == pr_edict.OP_STORE_V:
            pr_edict.pr_globals[b] = pr_edict.pr_globals[a]
            pr_edict.pr_globals[b + 1] = pr_edict.pr_globals[a + 1]
            pr_edict.pr_globals[b + 2] = pr_edict.pr_globals[a + 2]

        elif op in (
            pr_edict.OP_STOREP_F,
            pr_edict.OP_STOREP_S,
            pr_edict.OP_STOREP_ENT,
            pr_edict.OP_STOREP_FLD,
            pr_edict.OP_STOREP_FNC,
        ):
            ptr = int(pr_edict.pr_globals[b])
            ent_num = ptr // pr_edict.progz.entityfields
            f_offset = ptr % pr_edict.progz.entityfields
            ent = sv_main.sv.edicts[ent_num]
            SetEdictFieldValue(ent.v, f_offset, pr_edict.pr_globals[a])

        elif op == pr_edict.OP_STOREP_V:
            ptr = int(pr_edict.pr_globals[b])
            ent_num = ptr // pr_edict.progz.entityfields
            f_offset = ptr % pr_edict.progz.entityfields
            ent = sv_main.sv.edicts[ent_num]
            SetEdictFieldValue(ent.v, f_offset, pr_edict.pr_globals[a])
            SetEdictFieldValue(ent.v, f_offset + 1, pr_edict.pr_globals[a + 1])
            SetEdictFieldValue(ent.v, f_offset + 2, pr_edict.pr_globals[a + 2])

        elif op == pr_edict.OP_NOT_F:
            pr_edict.pr_globals[c] = float(not pr_edict.pr_globals[a])

        elif op == pr_edict.OP_NOT_V:
            pr_edict.pr_globals[c] = float(
                not pr_edict.pr_globals[a] and
                not pr_edict.pr_globals[a + 1] and
                not pr_edict.pr_globals[a + 2]
            )

        elif op == pr_edict.OP_NOT_S:
            pr_edict.pr_globals[c] = float(not G_STR(a))

        elif op == pr_edict.OP_NOT_ENT or op == pr_edict.OP_NOT_FNC:
            pr_edict.pr_globals[c] = float(not int(pr_edict.pr_globals[a]))

        elif op in (
            pr_edict.OP_CALL0,
            pr_edict.OP_CALL1,
            pr_edict.OP_CALL2,
            pr_edict.OP_CALL3,
            pr_edict.OP_CALL4,
            pr_edict.OP_CALL5,
            pr_edict.OP_CALL6,
            pr_edict.OP_CALL7,
            pr_edict.OP_CALL8,
        ):
            pr_argc = op - pr_edict.OP_CALL0
            raw_val = pr_edict.pr_globals[a]

            # Resolve function index from int, float, or IEEE float bits
            if isinstance(raw_val, int):
                newf = raw_val
            elif isinstance(raw_val, float):
                if raw_val.is_integer() and 0 <= raw_val < len(pr_edict.pr_functions):
                    newf = int(raw_val)
                else:
                    # Unpack raw IEEE 754 bit pattern if it was bit-cast into a float
                    newf = struct.unpack('<i', struct.pack('<f', raw_val))[0]
            else:
                newf = 0

            if not newf or newf >= len(pr_edict.pr_functions):
                caller_name = pr_edict.PR_GetString(pr_xfunction.s_name) if pr_xfunction else 'unknown'
                sys_sdl_unix.Sys_Error(f"PR_ExecuteProgram: NULL function call from {caller_name}")

            target_func = pr_edict.pr_functions[newf]

            if target_func.first_statement < 0:
                built_in = -target_func.first_statement
                pr_cmds.pr_builtin[built_in]()
            else:
                s = PR_EnterFunction(target_func)

        elif op == pr_edict.OP_STATE:
            ent = sv_main.sv.edicts[int(pr_edict.pr_globals[pr_edict.OFS_SELF])]
            ent.v.nextthink = pr_edict.pr_globals[pr_edict.OFS_TIME] + 0.1
            ent.v.frame = pr_edict.pr_globals[a]
            ent.v.think = int(pr_edict.pr_globals[b])

        elif op == pr_edict.OP_GOTO:
            s += _s16(st.a) - 1  # loop increments s first, so back off by one

        elif op == pr_edict.OP_IF:
            if pr_edict.pr_globals[a]:
                s += _s16(st.b) - 1

        elif op == pr_edict.OP_IFNOT:
            if not pr_edict.pr_globals[a]:
                s += _s16(st.b) - 1

        elif op == pr_edict.OP_AND:
            pr_edict.pr_globals[c] = float(bool(pr_edict.pr_globals[a]) and bool(pr_edict.pr_globals[b]))

        elif op == pr_edict.OP_OR:
            pr_edict.pr_globals[c] = float(bool(pr_edict.pr_globals[a]) or bool(pr_edict.pr_globals[b]))

        elif op == pr_edict.OP_BITAND:
            pr_edict.pr_globals[c] = float(int(pr_edict.pr_globals[a]) & int(pr_edict.pr_globals[b]))

        elif op == pr_edict.OP_BITOR:
            pr_edict.pr_globals[c] = float(int(pr_edict.pr_globals[a]) | int(pr_edict.pr_globals[b]))

        else:
            fname = pr_edict.PR_GetString(pr_xfunction.s_name) if pr_xfunction else 'unknown'
            sys_sdl_unix.Sys_Error(f"Bad opcode {op} in {fname}")


def PR_Profile_f():
    """Prints profiling information for top QuakeC functions."""
    if not sv_main.sv.active:
        return

    pmax = 0
    num = 0
    best = None

    while True:
        pmax = 0
        best = None
        for i in range(pr_edict.progz.numfunctions):
            f = pr_edict.pr_functions[i]
            if f.profile > pmax:
                pmax = f.profile
                best = f

        if best:
            if num < 10:
                console.Con_Printf(f'{best.profile:7d} {pr_edict.PR_GetString(best.s_name)}\n')
            num += 1
            best.profile = 0

        if not best:
            break