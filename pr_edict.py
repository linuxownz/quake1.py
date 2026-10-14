# pr_edict.py

import io
import struct
import traceback
from enum import Enum

import _cmd
import common
import console
import crc
import cvar

# import gl_model
import host
import host_cmd
import mathlib
import pr_exec
import progdefs
import progs
import protocol
import quakedef
import server
import sv_main
import world


class etype_t(Enum):
    ev_bad = -1
    ev_void = 0
    ev_string = 1
    ev_float = 2
    ev_vector = 3
    ev_entity = 4
    ev_field = 5
    ev_function = 6
    ev_pointer = 7


OFS_NULL = 0
OFS_RETURN = 1
OFS_PARM0 = 4
OFS_PARM1 = 7
OFS_PARM2 = 10
OFS_PARM3 = 13
OFS_PARM4 = 16
OFS_PARM5 = 19
OFS_PARM6 = 22
OFS_PARM7 = 25
RESERVED_OFS = 28
OFS_SELF = 28
OFS_OTHER = 29
OFS_WORLD = 30
OFS_TIME = 31
OFS_FRAMETIME = 32

# Set True to get verbose entity-parse tracing
DEBUG_PARSE = False

OP_DONE = 0
OP_MUL_F = 1
OP_MUL_V = 2
OP_MUL_FV = 3
OP_MUL_VF = 4
OP_DIV_F = 5
OP_ADD_F = 6
OP_ADD_V = 7
OP_SUB_F = 8
OP_SUB_V = 9

OP_EQ_F = 10
OP_EQ_V = 11
OP_EQ_S = 12
OP_EQ_E = 13
OP_EQ_FNC = 14

OP_NE_F = 15
OP_NE_V = 16
OP_NE_S = 17
OP_NE_E = 18
OP_NE_FNC = 19

OP_LE = 20
OP_GE = 21
OP_LT = 22
OP_GT = 23

OP_LOAD_F = 24
OP_LOAD_V = 25
OP_LOAD_S = 26
OP_LOAD_ENT = 27
OP_LOAD_FLD = 28
OP_LOAD_FNC = 29

OP_ADDRESS = 30

OP_STORE_F = 31
OP_STORE_V = 32
OP_STORE_S = 33
OP_STORE_ENT = 34
OP_STORE_FLD = 35
OP_STORE_FNC = 36

OP_STOREP_F = 37
OP_STOREP_V = 38
OP_STOREP_S = 39
OP_STOREP_ENT = 40
OP_STOREP_FLD = 41
OP_STOREP_FNC = 42

OP_RETURN = 43
OP_NOT_F = 44
OP_NOT_V = 45
OP_NOT_S = 46
OP_NOT_ENT = 47
OP_NOT_FNC = 48
OP_IF = 49
OP_IFNOT = 50
OP_CALL0 = 51
OP_CALL1 = 52
OP_CALL2 = 53
OP_CALL3 = 54
OP_CALL4 = 55
OP_CALL5 = 56
OP_CALL6 = 57
OP_CALL7 = 58
OP_CALL8 = 59
OP_STATE = 60
OP_GOTO = 61
OP_AND = 62
OP_OR = 63

OP_BITAND = 64
OP_BITOR = 65

PR_STRING_ALLOCSLOTS = 256


class dstatement_t:
    def __init__(self):
        self.op = 0
        self.a = 0
        self.b = 0
        self.c = 0

    @classmethod
    def from_bytes(cls, data: bytes):
        inst = cls()
        inst.op, inst.a, inst.b, inst.c = struct.unpack('<HHHH', data[:8])
        return inst


class ddef_t:
    def __init__(self):
        self.type = 0
        self.ofs = 0
        self.s_name = 0

    @classmethod
    def from_bytes(cls, data: bytes):
        inst = cls()
        inst.type, inst.ofs, inst.s_name = struct.unpack('<HHI', data[:8])
        return inst


DEF_SAVEGLOBAL = 1 << 15

MAX_PARMS = 8


class dfunction_t:
    def __init__(self):
        self.first_statement = 0
        self.parm_start = 0
        self.locals = 0
        self.profile = 0
        self.s_name = 0
        self.s_file = 0
        self.numparms = 0
        self.parm_size = bytearray(MAX_PARMS)

    @classmethod
    def from_bytes(cls, data: bytes):
        inst = cls()
        (
            inst.first_statement,
            inst.parm_start,
            inst.locals,
            inst.profile,
            inst.s_name,
            inst.s_file,
            inst.numparms,
        ) = struct.unpack('<iiiiiii', data[:28])
        inst.parm_size = bytearray(data[28:36])
        return inst


PROG_VERSION = 6


class dprograms_t:
    def __init__(self):
        self.version = 0
        self.crc = 0
        self.ofs_statements = 0
        self.numstatements = 0
        self.ofs_globaldefs = 0
        self.numglobaldefs = 0
        self.ofs_fielddefs = 0
        self.numfielddefs = 0
        self.ofs_functions = 0
        self.numfunctions = 0
        self.ofs_strings = 0
        self.numstrings = 0
        self.ofs_globals = 0
        self.numglobals = 0
        self.entityfields = 0

    @classmethod
    def from_bytes(cls, data: bytes):
        inst = cls()
        (
            inst.version,
            inst.crc,
            inst.ofs_statements,
            inst.numstatements,
            inst.ofs_globaldefs,
            inst.numglobaldefs,
            inst.ofs_fielddefs,
            inst.numfielddefs,
            inst.ofs_functions,
            inst.numfunctions,
            inst.ofs_strings,
            inst.numstrings,
            inst.ofs_globals,
            inst.numglobals,
            inst.entityfields,
        ) = struct.unpack('<15i', data[:60])
        return inst


progz: dprograms_t = None
pr_functions: list[dfunction_t] = None

pr_strings = ''
pr_stringssize = 0
pr_knownstrings: list[str] = []
pr_maxknownstrings = 0
pr_numknownstrings = 0

pr_fielddefs: list[ddef_t] = []
pr_globaldefs: list[ddef_t] = []

pr_alpha_supported = False
pr_effects_mask = 0

pr_statements: list[dstatement_t] = []
pr_global_struct: progdefs.globalvars_t = None


class GlobalsTrapList(list):
    """Wrapper around pr_globals list to catch non-numeric/edict writes immediately."""

    def __setitem__(self, index, value):
        print('GlobalTrapList\n')
        if isinstance(index, slice):
            # Handle slice assignments: pr_globals[start:stop] = [val1, val2, ...]
            for idx, item in enumerate(value):
                if not isinstance(item, (int, float)):
                    print(
                        f'\n[TRAP TRIGGERED] Slice write at index {index.start + idx if index.start else idx} '
                        f"contains invalid type '{type(item).__name__}' ({item})!"
                    )
                    traceback.print_stack()
                    raise TypeError(
                        f"pr_globals slice write contained invalid type '{type(item).__name__}'"
                    )
        else:
            # Handle single item assignments: pr_globals[idx] = val
            if not isinstance(value, (int, float)):
                print(
                    f"\n[TRAP TRIGGERED] Storing invalid type '{type(value).__name__}' ({value}) "
                    f'into pr_globals[{index}]!'
                )
                traceback.print_stack()
                raise TypeError(
                    f"pr_globals[{index}] cannot be assigned type '{type(value).__name__}'"
                )

        super().__setitem__(index, value)


pr_globals: list[float] = []  # GlobalsTrapList([])

pr_edict_size = 0


pr_crc = 0

type_size = [1, 1, 1, 3, 1, 1, 1, 1]

MAX_FIELD_LEN = 64
GEFV_CACHESIZE = 2


class gefv_cache:
    def __init__(self):
        self.pcache: ddef_t = None
        self.field: str = ''


gefvCache: list[gefv_cache] = [gefv_cache() for _ in range(GEFV_CACHESIZE)]
rep_index = 0


def _edict_index(ent) -> int:
    """Index of ent in sv.edicts by *identity* (never ==), or -1 if not found."""
    edicts = sv_main.sv.edicts
    n = getattr(ent, 'num', None)
    if isinstance(n, int) and 0 <= n < len(edicts) and edicts[n] is ent:
        return n
    for i, e in enumerate(edicts):
        if e is ent:
            return i
    return -1


def PROG_TO_EDICT(offset) -> progs.edict_t:
    """Converts a VM entity reference (edict index) to an edict_t."""
    return sv_main.sv.edicts[int(offset) if offset else 0]


def EDICT_TO_PROG(ent: progs.edict_t) -> int:
    """Converts an edict_t to its VM entity reference (edict index)."""
    if ent is None:
        return 0
    i = _edict_index(ent)
    return i if i >= 0 else 0


# Map offset index (def.ofs) to entvars_t attribute names
# entvars_t fields in order of 32-bit slots (progdefs.h / pr_edict.c layout)
FIELD_OFFSET_MAP = {
    0: 'modelindex',
    1: 'absmin',  # float[3]
    4: 'absmax',  # float[3]
    7: 'ltime',
    8: 'movetype',
    9: 'solid',
    10: 'origin',  # float[3]
    13: 'oldorigin',  # float[3]
    16: 'velocity',  # float[3]
    19: 'angles',  # float[3]
    22: 'avelocity',  # float[3]
    25: 'punchangle',  # float[3]
    28: 'classname',  # string_t (int)
    29: 'model',  # string_t (int)
    30: 'frame',
    31: 'skin',
    32: 'effects',
    33: 'mins',  # float[3]
    36: 'maxs',  # float[3]
    39: 'size',  # float[3]
    42: 'touch',  # func_t (int)
    43: 'use',  # func_t (int)
    44: 'think',  # func_t (int)
    45: 'blocked',  # func_t (int)
    46: 'nextthink',
    47: 'groundentity',  # edict_t pointer (int)
    48: 'health',
    49: 'frags',
    50: 'weapon',
    51: 'weaponmodel',  # string_t (int)
    52: 'weaponframe',
    53: 'currentammo',
    54: 'ammo_shells',
    55: 'ammo_nails',
    56: 'ammo_rockets',
    57: 'ammo_cells',
    58: 'items',
    59: 'takedamage',
    60: 'chain',  # edict_t pointer (int)
    61: 'deadflag',
    62: 'view_ofs',  # float[3]
    65: 'button0',
    66: 'button1',
    67: 'button2',
    68: 'impulse',
    69: 'fixangle',
    70: 'v_angle',  # float[3]
    73: 'idealpitch',
    74: 'netname',  # string_t (int)
    75: 'enemy',  # edict_t pointer (int)
    76: 'flags',
    77: 'colormap',
    78: 'team',
    79: 'max_health',
    80: 'teleport_time',
    81: 'armortype',
    82: 'armorvalue',
    83: 'waterlevel',
    84: 'watertype',
    85: 'ideal_yaw',
    86: 'yaw_speed',
    87: 'aiment',  # edict_t pointer (int)
    88: 'goalentity',  # edict_t pointer (int)
    89: 'spawnflags',
    90: 'target',  # string_t (int)
    91: 'targetname',  # string_t (int)
    92: 'dmg_take',
    93: 'dmg_save',
    94: 'dmg_inflictor',  # edict_t pointer (int)
    95: 'owner',  # edict_t pointer (int)
    96: 'movedir',  # float[3]
    99: 'message',  # string_t (int)
    100: 'sounds',
    101: 'noise',  # string_t (int)
    102: 'noise1',  # string_t (int)
    103: 'noise2',  # string_t (int)
    104: 'noise3',  # string_t (int)
}


def get_edict_field_by_offset(ed, def_ofs: int):
    """C parity: (eval_t *)((char *)&ed->v + def->ofs * 4)

    Retrieves value dynamically by entvars offset index.
    """
    if ed is None or ed.v is None:
        return None

    # Check primary 32-bit slot map
    attr_name = FIELD_OFFSET_MAP.get(def_ofs)

    if attr_name and hasattr(ed.v, attr_name):
        return getattr(ed.v, attr_name)

    # Handle component vector offsets (e.g. def_ofs targeting origin[1] or origin[2])
    for base_ofs, vector_attr in FIELD_OFFSET_MAP.items():
        if base_ofs <= def_ofs < base_ofs + 3:
            val = getattr(ed.v, vector_attr, None)
            if isinstance(val, list) and len(val) == 3:
                return val

    return None


def is_field_zero(val, type_val: int) -> bool:
    """Replicates C zero-check for type_size slots (v[j])."""
    if val is None:
        return True

    # Vector types (3 floats)
    if type_val == etype_t.ev_vector:
        if isinstance(val, (list, tuple)) and len(val) >= 3:
            return val[0] == 0.0 and val[1] == 0.0 and val[2] == 0.0
        return True

    # Numeric/pointer/function/string types (1 slot)
    if isinstance(val, (int, float)):
        return val == 0 or val == 0.0
    if isinstance(val, str):
        return len(val) == 0

    return False


class _Link:
    """Fallback link_t (prev/next) used only if world.py defines no link_t."""

    def __init__(self):
        self.prev = None
        self.next = None


def ED_ClearEdict(e: progs.edict_t) -> None:
    """C equivalent: ED_ClearEdict / memset(e, 0, pr_edict_size)"""
    # 1. Reset edict_t header fields (engine entity metadata)
    e.free = False
    e.freetime = 0.0
    e.entnum = getattr(e, 'entnum', 0)  # Preserve identity index
    # In C, area is a link_t embedded in the edict: it always exists and a
    # cleared edict just has prev = next = NULL. SV_LinkEdict tests
    # ent.area.prev, so area itself must never be None.
    area = getattr(e, 'area', None)
    if area is None:
        link_cls = getattr(quakedef, 'link_t', None) or _Link
        area = link_cls()
        e.area = area
    area.prev = None
    area.next = None
    e.num_leafs = 0
    # always (re)create it: a missing or short list breaks SV_FindTouchedLeafs
    e.leafnums = [0] * getattr(progs, 'MAX_ENT_LEAFS', 16)

    # 2. Reset QuakeC entvars_t fields (memset &e->v)
    if e.v is not None:
        e.v.reset_fields()
    else:
        e.v = progdefs.entvars_t()
    pr_exec.ClearExtraFields(e.v)


def ED_Alloc() -> progs.edict_t:
    """Allocates a free edict slot or expands sv.num_edicts."""
    sv = sv_main.sv
    svs = sv_main.svs

    start_idx = svs.maxclients + 1

    # 1. Search for a reusable free edict
    for i in range(start_idx, sv.num_edicts):
        e = EDICT_NUM(i)

        # Hysteresis check: relaxed allocation within first 2 seconds of server time
        if e.free and (e.freetime < 2.0 or (sv.time - e.freetime) > 0.5):
            ED_ClearEdict(e)
            return e

    # 2. Check maximum edict capacity
    if sv.num_edicts >= sv.max_edicts:
        host.Host_Error(
            f'ED_Alloc: no free edicts (max_edicts is {sv.max_edicts})'
        )

    # 3. Expand edict pool
    i = sv.num_edicts
    sv.num_edicts += 1

    e = EDICT_NUM(i)
    ED_ClearEdict(e)

    if hasattr(e, 'baseline') and e.baseline is not None:
        e.baseline.scale = protocol.ENTALPHA_DEFAULT

    return e


def ED_Free(ed: progs.edict_t):
    world.SV_UnlinkEdict(ed)

    ed.free = True
    ed.v.model = 0
    ed.v.takedamage = 0
    ed.v.modelindex = 0
    ed.v.colormap = 0
    ed.v.skin = 0
    ed.v.frame = 0
    mathlib.VectorCopy(mathlib.vec3_origin, ed.v.origin)
    mathlib.VectorCopy(mathlib.vec3_origin, ed.v.angles)
    ed.v.nextthink = -1
    ed.v.solid = 0
    ed.alpha = protocol.ENTALPHA_DEFAULT
    ed.scale = protocol.ENTALPHA_DEFAULT

    ed.freetime = sv_main.sv.time


def ED_GlobalAtOfs(ofs: int) -> ddef_t:
    if progz is None:
        return None
    for i in range(progz.numglobaldefs):
        _def = pr_globaldefs[i]
        if _def.ofs == ofs:
            return _def
    return None


def ED_FieldAtOfs(ofs: int) -> ddef_t:
    if progz is None:
        return None
    for i in range(progz.numfielddefs):
        _def = pr_fielddefs[i]
        if _def.ofs == ofs:
            return _def
    return None


def ED_FindField(name: str) -> ddef_t:
    if progz is None:
        return None
    for i in range(progz.numfielddefs):
        _def = pr_fielddefs[i]
        if PR_GetString(_def.s_name) == name:
            return _def
    return None


class GlobalVars:
    """Live name -> pr_globals view (replaces progdefs.globalvars_t(pr_globals),
    which copied values instead of reading/writing the flat globals list)."""
    __slots__ = ('_ofs', '_typ')

    def __init__(self):
        object.__setattr__(self, '_ofs', {})
        object.__setattr__(self, '_typ', {})
        for gd in pr_globaldefs:
            name = PR_GetString(gd.s_name)
            if name and name not in self._ofs:
                self._ofs[name] = gd.ofs
                self._typ[name] = gd.type & ~DEF_SAVEGLOBAL

    def __getattr__(self, name):
        try:
            ofs = self._ofs[name]
        except KeyError:
            raise AttributeError(f'progs.dat has no global {name!r}')
        t = self._typ[name]
        if t == etype_t.ev_vector.value:
            return list(pr_globals[ofs:ofs + 3])
        v = pr_globals[ofs]
        if t == etype_t.ev_float.value:
            return float(v)
        return int(v)

    def __setattr__(self, name, value):
        try:
            ofs = self._ofs[name]
        except KeyError:
            raise AttributeError(f'progs.dat has no global {name!r}')
        t = self._typ[name]
        if t == etype_t.ev_vector.value:
            for i in range(3):
                pr_globals[ofs + i] = float(value[i])
        elif t == etype_t.ev_float.value:
            pr_globals[ofs] = float(value)
        elif t == etype_t.ev_entity.value and not isinstance(value, (int, float)):
            pr_globals[ofs] = EDICT_TO_PROG(value)
        else:
            pr_globals[ofs] = int(value)


def ED_FindGlobal(name: str) -> ddef_t:
    if progz is None:
        return None
    for i in range(progz.numglobaldefs):
        _def = pr_globaldefs[i]
        if PR_GetString(_def.s_name) == name:
            return _def
    return None


def ED_FindFunction(name: str) -> dfunction_t:
    if progz is None or not name:
        return None

    clean_name = name.rstrip('\x00').strip() if isinstance(name, str) else name
    if not clean_name:
        return None

    # Skip index 0 (reserved NULL function pointer)
    for i in range(1, progz.numfunctions):
        func = pr_functions[i]
        func_name = PR_GetString(func.s_name).rstrip('\x00')
        if func_name == clean_name:
            return func

    return None


def GetEdictFieldValue(ed, field: str):
    """Python parity for GetEdictFieldValue."""
    global rep_index

    def_ptr = None

    # 1. Search cache
    for entry in gefvCache:
        if entry.field and entry.field == field:
            def_ptr = entry.pcache
            break

    # 2. Cache miss -> perform lookup
    if def_ptr is None:
        def_ptr = ED_FindField(field)

        if def_ptr is not None and len(field) < MAX_FIELD_LEN:
            gefvCache[rep_index].pcache = def_ptr
            gefvCache[rep_index].field = field
            rep_index ^= 1

    if def_ptr is None:
        return None

    # 3. Retrieve value from entvars_t
    if hasattr(ed.v, field):
        return getattr(ed.v, field)

    return get_edict_field_by_offset(ed, def_ptr.ofs)


def PR_ValueString(_type: int, val) -> str:
    """Safely formats a global or edict variable value into a readable debug string."""
    _type &= ~DEF_SAVEGLOBAL

    match _type:
        case etype_t.ev_string.value:
            s_idx = (
                int(val)
                if isinstance(val, (int, float))
                else getattr(val, 'string', 0)
            )
            line = PR_GetString(s_idx)
        case etype_t.ev_entity.value:
            ent_idx = (
                int(val)
                if isinstance(val, (int, float))
                else getattr(val, 'edict', 0)
            )
            line = f'entity {NUM_FOR_EDICT(PROG_TO_EDICT(ent_idx))}'
        case etype_t.ev_function.value:
            func_idx = (
                int(val)
                if isinstance(val, (int, float))
                else getattr(val, 'function', 0)
            )
            if (
                pr_functions is None
                or func_idx <= 0
                or func_idx >= len(pr_functions)
            ):
                line = 'NULL'
            else:
                f = pr_functions[func_idx]
                func_name = PR_GetString(f.s_name)
                line = f'{func_name}()'
        case etype_t.ev_field.value:
            field_ofs = (
                int(val)
                if isinstance(val, (int, float))
                else getattr(val, '_int', 0)
            )
            _def = ED_FieldAtOfs(field_ofs)
            line = f'.{PR_GetString(_def.s_name)}' if _def else f'.{field_ofs}'
        case etype_t.ev_void.value:
            line = 'void'
        case etype_t.ev_float.value:
            fval = (
                float(val)
                if isinstance(val, (int, float))
                else getattr(val, '_float', 0.0)
            )
            line = f'{fval:5.1f}'
        case etype_t.ev_vector.value:
            if isinstance(val, (list, tuple)) and len(val) >= 3:
                line = f"'{val[0]:5.1f} {val[1]:5.1f} {val[2]:5.1f}'"
            elif hasattr(val, 'vector'):
                line = f"'{val.vector[0]:5.1f} {val.vector[1]:5.1f} {val.vector[2]:5.1f}'"
            elif isinstance(val, (int, float)):
                line = f"'{float(val):5.1f} 0.0 0.0'"
            else:
                line = "'0.0 0.0 0.0'"
        case etype_t.ev_pointer.value:
            line = 'pointer'
        case _:
            line = f'bad type {_type}'

    return line


def PR_UglyValueString(_type: int, val) -> str:
    """Formats values for saving to file streams without decorative padding."""
    _type &= ~DEF_SAVEGLOBAL

    match _type:
        case etype_t.ev_string.value | etype_t.ev_string:
            s_idx = (
                int(val)
                if isinstance(val, (int, float))
                else getattr(val, 'string', 0)
            )
            line = PR_GetString(s_idx)
        case etype_t.ev_entity.value | etype_t.ev_entity:
            ent_idx = (
                int(val)
                if isinstance(val, (int, float))
                else getattr(val, 'edict', 0)
            )
            line = f'{NUM_FOR_EDICT(PROG_TO_EDICT(ent_idx))}'
        case etype_t.ev_function.value | etype_t.ev_function:
            func_idx = (
                int(val)
                if isinstance(val, (int, float))
                else getattr(val, 'function', 0)
            )
            if (
                pr_functions is None
                or func_idx <= 0
                or func_idx >= len(pr_functions)
            ):
                line = 'NULL'
            else:
                f = pr_functions[func_idx]
                line = f'{PR_GetString(f.s_name)}'
        case etype_t.ev_field.value | etype_t.ev_field:
            field_ofs = (
                int(val)
                if isinstance(val, (int, float))
                else getattr(val, '_int', 0)
            )
            _def = ED_FieldAtOfs(field_ofs)
            line = f'{PR_GetString(_def.s_name)}' if _def else f'{field_ofs}'
        case etype_t.ev_void.value | etype_t.ev_void:
            line = 'void'
        case etype_t.ev_float.value | etype_t.ev_float:
            fval = (
                float(val)
                if isinstance(val, (int, float))
                else getattr(val, '_float', 0.0)
            )
            line = f'{fval:f}'
        case etype_t.ev_vector.value | etype_t.ev_vector:
            if isinstance(val, (list, tuple)) and len(val) >= 3:
                line = f'{val[0]:f} {val[1]:f} {val[2]:f}'
            elif hasattr(val, 'vector'):
                line = (
                    f'{val.vector[0]:f} {val.vector[1]:f} {val.vector[2]:f}'
                )
            elif isinstance(val, (int, float)):
                line = f'{float(val):f} 0.0 0.0'
            else:
                line = '0.0 0.0 0.0'
        case _:
            line = f'bad type {_type}'

    return line


def PR_GlobalString(ofs: int) -> str:
    """Formats a global variable at a given memory offset into a debug string."""
    def_ptr = ED_GlobalAtOfs(ofs)

    if def_ptr is None:
        line = f'{ofs}(?)'
    else:
        val = pr_globals[ofs] if 0 <= ofs < len(pr_globals) else 0

        val_str = PR_ValueString(def_ptr.type, val)
        var_name = PR_GetString(def_ptr.s_name)

        line = f'{ofs}({var_name}){val_str}'

    if len(line) < 20:
        line = line.ljust(20) + ' '
    else:
        line = line + ' '

    return line


def PR_GlobalStringNoContents(ofs: int) -> str:
    """Formats a global variable header at an offset without evaluating its content."""
    def_ptr = ED_GlobalAtOfs(ofs)

    if def_ptr is None:
        line = f'{ofs}(?)'
    else:
        var_name = PR_GetString(def_ptr.s_name)
        line = f'{ofs}({var_name})'

    if len(line) < 20:
        line = line.ljust(20) + ' '
    else:
        line = line + ' '

    return line


def ED_Print(ed: progs.edict_t):
    if ed.free:
        console.Con_Printf('FREE\n')
        return

    console.Con_Printf(f'\nEDICT {_edict_index(ed)}:\n')

    for i in range(progz.numfielddefs):
        d = pr_fielddefs[i]
        name = PR_GetString(d.s_name).rstrip('\x00')

        if not name or name.startswith('PR_'):
            continue

        # Strip high save flags (0x8000) from type definition
        type_mask = d.type & 0x7FFF

        # Retrieve value from entity field offset
        v = (
            ed.v[d.ofs]
            if hasattr(ed.v, '__getitem__')
            else getattr(ed.v, name, 0)
        )

        if type_mask == progs.ev_string:
            s = PR_GetString(v).rstrip('\x00')
            if s:
                console.Con_Printf(f'{name:<15} {s}\n')
        elif type_mask == progs.ev_float:
            if v != 0:
                console.Con_Printf(f'{name:<15} {v:g}\n')
        elif type_mask == progs.ev_vector:
            v0 = ed.v[d.ofs]
            v1 = ed.v[d.ofs + 1]
            v2 = ed.v[d.ofs + 2]
            if v0 or v1 or v2:
                console.Con_Printf(f"{name:<15} '{v0:g} {v1:g} {v2:g}'\n")
        elif type_mask == progs.ev_entity:
            if v:
                console.Con_Printf(f'{name:<15} {int(v)}\n')
        elif type_mask == progs.ev_function:
            if v:
                func_name = (
                    PR_GetString(pr_functions[int(v)].s_name)
                    if int(v) < len(pr_functions)
                    else f'{v}'
                )
                console.Con_Printf(f'{name:<15} {func_name}\n')
        elif type_mask == progs.ev_pointer:
            if v:
                console.Con_Printf(f'{name:<15} {v}\n')


def ED_Write(f, ed: progs.edict_t) -> None:
    """Writes an edict's non-zero key-value pairs to a savegame/map file buffer."""
    f.write('{\n')

    if ed.free:
        f.write('}\n')
        return

    if progz is None:
        f.write('}\n')
        return

    for i in range(1, progz.numfielddefs):
        d = pr_fielddefs[i]
        name = PR_GetString(d.s_name)
        j = len(name)

        if j > 1 and name[j - 2] == '_':
            continue

        type_val = d.type & ~DEF_SAVEGLOBAL

        if type_val >= len(type_size):
            continue

        val = GetEdictFieldValue(ed, name)

        if is_field_zero(val, type_val):
            continue

        ugly_str = PR_UglyValueString(d.type, val)
        f.write(f'"{name}" "{ugly_str}"\n')

    if not pr_alpha_supported and ed.alpha != protocol.ENTALPHA_DEFAULT:
        alpha_val = protocol.ENTALPHA_TOSAVE(ed.alpha)
        f.write(f'"alpha" "{alpha_val:f}"\n')

    f.write('}\n')


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
    active = 0
    models = 0
    solid = 0
    step = 0

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


def ED_WriteGlobals(f: io.FileIO):
    f.write('{\n')

    for i in range(progz.numglobaldefs):
        _def = pr_globaldefs[i]
        if not (_def.type & DEF_SAVEGLOBAL):
            continue

        _type = _def.type & ~DEF_SAVEGLOBAL
        if _type not in (
            etype_t.ev_string,
            etype_t.ev_float,
            etype_t.ev_entity,
        ):
            continue

        name = PR_GetString(_def.s_name)
        val = pr_globals[_def.ofs]

        eval_val = progs.eval_t()
        if _type == etype_t.ev_string:
            eval_val.string = int(val)
        elif _type == etype_t.ev_entity:
            eval_val.edict = int(val)
        else:
            eval_val._float = float(val)

        ugly_str = PR_UglyValueString(_def.type, eval_val)
        f.write(f'"{name}" "{ugly_str}"\n')

    f.write('}\n')


def ED_ParseGlobals(data: str) -> str:
    while True:
        data = common.COM_Parse(data)
        if common.com_token[0] == '}':
            break
        if not data:
            host.Host_Error('ED_ParseEntity: EOF without closing brace')

        keyname = common.com_token[:]

        data = common.COM_Parse(data)

        if not data:
            host.Host_Error('ED_ParseEntity: EOF without closing brace')

        if common.com_token[0] == '}':
            host.Host_Error('ED_ParseEntity: closing brace without data')

        key = ED_FindGlobal(keyname)
        if not key:
            console.Con_Printf(f'{keyname} is not a global\n')
            continue

        if not ED_ParseEpair(pr_globals, key, common.com_token):
            host.Host_Error('ED_ParseGlobals: parse error')

    return data


def ED_NewString(string: str) -> int:
    """Allocates and processes escape characters for a new string, returning its string offset."""
    if not string:
        return 0

    chars: list[str] = []
    i = 0
    l = len(string)

    while i < l:
        if string[i] == '\\' and i < l - 1:
            i += 1
            if string[i] == 'n':
                chars.append('\n')
            else:
                chars.append('\\')
        else:
            chars.append(string[i])
        i += 1

    processed_str = ''.join(chars)

    return PR_SetEngineString(processed_str)


def ED_ParseEpair(base: object, key: ddef_t, s: str) -> bool:
    """Parses an entity key-value string pair into the base object's field memory offset."""
    field_type = int(key.type & ~DEF_SAVEGLOBAL)

    ev_string_val = int(etype_t.ev_string.value)
    ev_float_val = int(etype_t.ev_float.value)
    ev_vector_val = int(etype_t.ev_vector.value)
    ev_entity_val = int(etype_t.ev_entity.value)
    ev_field_val = int(etype_t.ev_field.value)
    ev_func_val = int(etype_t.ev_function.value)

    if base == pr_globals or isinstance(base, (list, dict)):
        if field_type == ev_string_val:
            pr_globals[key.ofs] = ED_NewString(s)
        elif field_type == ev_float_val:
            try:
                pr_globals[key.ofs] = float(s)
            except ValueError:
                pr_globals[key.ofs] = 0.0
        elif field_type == ev_vector_val:
            parts = s.split()
            for i in range(min(len(parts), 3)):
                try:
                    pr_globals[key.ofs + i] = float(parts[i])
                except ValueError:
                    pr_globals[key.ofs + i] = 0.0
        return True

    if field_type == ev_string_val:
        val = ED_NewString(s)
        if DEBUG_PARSE:
            print(f"[DEBUG PARSE] Key: {PR_GetString(key.s_name)!r} | Raw String: {s!r} | Allocated Offset: {val}")
        SetEdictFieldValueByOfs(base, key.ofs, val)

    elif field_type == ev_float_val:
        try:
            val = float(s)
        except ValueError:
            val = 0.0
        SetEdictFieldValueByOfs(base, key.ofs, val)

    elif field_type == ev_vector_val:
        parts = s.split()
        vec = [0.0, 0.0, 0.0]

        count = min(len(parts), 3)
        for i in range(count):
            try:
                vec[i] = float(parts[i])
            except ValueError:
                vec[i] = 0.0

        if count < 3:
            key_name = PR_GetString(key.s_name)
            console.Con_DWarning(
                f'Avoided reading garbage for "{key_name}" "{s}"\n'
            )

        SetEdictFieldValueByOfs(base, key.ofs, vec)

    elif field_type == ev_entity_val:
        try:
            ent_num = int(s)
        except ValueError:
            ent_num = 0
        val = EDICT_TO_PROG(EDICT_NUM(ent_num))
        SetEdictFieldValueByOfs(base, key.ofs, val)

    elif field_type == ev_field_val:
        def_ptr = ED_FindField(s)
        if def_ptr is None:
            if not s.startswith('sky') and s != 'fog':
                console.Con_DPrintf(f"Can't find field {s}\n")
            return False

        SetEdictFieldValueByOfs(base, key.ofs, progs.G_INT(def_ptr.ofs))

    elif field_type == ev_func_val:
        func = ED_FindFunction(s)
        if func is None:
            console.Con_Printf(f"Can't find function {s}\n")
            return False

        func_index = pr_functions.index(func) if pr_functions else 0
        SetEdictFieldValueByOfs(base, key.ofs, func_index)

    else:
        console.Con_DPrintf(f'ED_ParseEpair: unknown field_type {field_type}\n')

    return True


def SetEdictFieldValueByOfs(
    base: object, ofs: int, val: float | int | str | list[float]
) -> None:
    """Sets a field value on an edict (or entvars_t base) given a 32-bit offset index."""
    entvars = getattr(base, 'v', base)
    if entvars is None:
        return

    # 1. Exact field match (scalar or full 3D vector)
    if ofs in FIELD_OFFSET_MAP:
        attr_name = FIELD_OFFSET_MAP[ofs]
        if hasattr(entvars, attr_name):
            if isinstance(val, (list, tuple)) and len(val) == 3:
                setattr(entvars, attr_name, [float(x) for x in val])
            else:
                setattr(entvars, attr_name, val)
            return

    # 2. Vector component fallback (e.g. OP_STORE_F writing to origin_y at offset base + 1)
    for base_ofs, attr_name in FIELD_OFFSET_MAP.items():
        if base_ofs <= ofs < base_ofs + 3:
            vec = getattr(entvars, attr_name, None)
            if isinstance(vec, list):
                component = ofs - base_ofs
                if isinstance(val, (int, float)):
                    vec[component] = float(val)
                elif isinstance(val, (list, tuple)) and val:
                    vec[component] = float(val[0])
                return

    # 3. Offsets outside the entvars_t table (QC-defined fields, e.g. light_lev)
    if isinstance(val, (list, tuple)):
        for i, x in enumerate(val):
            pr_exec.SetEdictFieldValue(entvars, ofs + i, float(x))
    else:
        pr_exec.SetEdictFieldValue(entvars, ofs, val)


def ED_ParseEdict(data: str, ent: progs.edict_t) -> str | None:
    """Parses key-value dictionary pairs from a map or savegame data stream into an edict."""
    init = False

    while True:
        data = common.COM_Parse(data)
        if not common.com_token:
            break

        if common.com_token[0] == '}':
            break

        if data is None:
            host.Host_Error('ED_ParseEntity: EOF without closing brace')

        if common.com_token == 'angle':
            common.com_token = 'angles'
            anglehack = True
        else:
            anglehack = False

        if common.com_token == 'light':
            common.com_token = 'light_lev'

        keyname = common.com_token.rstrip(' ')

        cpe_flag = (
            common.cpe_mode.CPE_ALLOWTRUNC
            if keyname == 'wad'
            else common.cpe_mode.CPE_NOTRUNC
        )
        data = common.COM_ParseEx(data, cpe_flag)

        if data is None:
            host.Host_Error('ED_ParseEntity: EOF without closing brace')

        if common.com_token and common.com_token[0] == '}':
            host.Host_Error('ED_ParseEntity: closing brace without data')

        init = True

        if keyname.startswith('_'):
            continue

        if keyname == 'alpha':
            try:
                alpha_float = float(common.com_token)
            except ValueError:
                alpha_float = 1.0
            ent.alpha = protocol.ENTALPHA_ENCODE(alpha_float)

        key = ED_FindField(keyname)
        if key is None:
            if (
                not keyname.startswith('sky')
                and keyname != 'fog'
                and keyname != 'alpha'
            ):
                console.Con_DPrintf(f'"{keyname}" is not a field\n')
            continue

        if anglehack:
            common.com_token = f'0 {common.com_token} 0'

        if not ED_ParseEpair(ent.v, key, common.com_token):
            host.Host_Error('ED_ParseEdict: parse error')

    if not init:
        ent.free = True

    return data


def ED_LoadFromFile(data):
    # Decode raw bytes to string if needed
    if isinstance(data, (bytes, bytearray)):
        data = data.decode('latin-1')

    try:
        pr_global_struct.time = sv_main.sv.time
    except Exception:
        pass
    pr_globals[OFS_TIME] = sv_main.sv.time

    ent: progs.edict_t = None
    inhibit = 0

    while True:
        data = common.COM_Parse(data)

        if not data:
            break

        # Safely convert com_token to string
        token = (
            common.com_token.decode('latin-1')
            if isinstance(common.com_token, (bytes, bytearray))
            else common.com_token
        )

        if not token or token[0] != '{':
            host.Host_Error(f'ED_LoadFromFile: found {token} when expecting {{')

        # Guarantee edict 0 is reserved strictly for worldspawn
        if ent is None:
            ent = EDICT_NUM(0)
        else:
            ent = ED_Alloc()

        # Parse key/value block for current entity
        data = ED_ParseEdict(data, ent)

        # Retrieve and clean classname string from string table offset
        classname: str = PR_GetString(ent.v.classname).rstrip('\x00').strip()

        if not classname:
            console.Con_Printf('No classname for edict:\n')
            ED_Print(ent)
            ED_Free(ent)
            continue

        # Filter entities based on deathmatch / skill spawnflags
        spawnflags = (
            int(ent.v.spawnflags) if hasattr(ent.v, 'spawnflags') else 0
        )

        if cvar.Cvar_GetCvar('deathmatch').value:
            if spawnflags & server.SPAWNFLAG_NOT_DEATHMATCH:
                ED_Free(ent)
                inhibit += 1
                continue
        elif (
            (host_cmd.current_skill == 0 and (spawnflags & server.SPAWNFLAG_NOT_EASY))
            or (host_cmd.current_skill == 1 and (spawnflags & server.SPAWNFLAG_NOT_MEDIUM))
            or (host_cmd.current_skill >= 2 and (spawnflags & server.SPAWNFLAG_NOT_HARD))
        ):
            ED_Free(ent)
            inhibit += 1
            continue

        if sv_main.sv.nomonsters and classname.startswith('monster_'):
            ED_Free(ent)
            inhibit += 1
            continue

        # Look up spawn function
        func = ED_FindFunction(classname)
        if not func:
            console.Con_Printf(f'no spawn function for: {classname}\n')
            ED_Print(ent)
            ED_Free(ent)
            continue

        sv_main.SV_ReserveSignonSpace(512)

        # Assign global 'self' entity reference before invoking spawn program
        # (struct write first, then the raw slot, so the slot always ends up an int)
        ent_ref = EDICT_TO_PROG(ent)
        try:
            pr_global_struct.self = ent_ref
        except Exception:
            pass
        pr_globals[OFS_SELF] = ent_ref

        # Locate function index using object identity ('is') to avoid index 0 equality traps
        func_index = 0
        if pr_functions:
            for i, f in enumerate(pr_functions):
                if f is func:
                    func_index = i
                    break

        if func_index > 0:
            if DEBUG_PARSE:
                print(f"[spawn] {classname} ent={ent_ref} self={pr_globals[OFS_SELF]!r}")
            pr_exec.PR_ExecuteProgram(func_index)

    console.Con_DPrintf(f'{inhibit} entities inhibited\n')


def PR_HasGlobal(name, value) -> bool:
    g = ED_FindGlobal(name)
    return (
        g
        and (g.type & ~DEF_SAVEGLOBAL) == etype_t.ev_float
        and progs.G_FLOAT(g.ofs) == value
    )


def PR_FindSupportedEffects():
    isqex = PR_HasGlobal(
        'EF_QUADLIGHT', quakedef.EF_QEX_QUADLIGHT
    ) and (
        PR_HasGlobal('EF_PENTLIGHT', quakedef.EF_QEX_PENTALIGHT)
        or PR_HasGlobal('EF_PENTALIGHT', quakedef.EF_QEX_PENTALIGHT)
    )

    return (
        -1
        if isqex
        else -1
        & ~(
            quakedef.EF_QEX_QUADLIGHT
            | quakedef.EF_QEX_PENTALIGHT
            | quakedef.EF_QEX_CANDLELIGHT
        )
    )


# Extended builtins array for Quake 2021 Re-release (KEX Engine) patching
exbuiltins: list[progs.exbuiltin_t] = [
    progs.exbuiltin_t('centerprint', -90, -73),
    progs.exbuiltin_t('bprint', -91, -23),
    progs.exbuiltin_t('sprint', -92, -24),
    progs.exbuiltin_t('ex_centerprint', 0, -73),
    progs.exbuiltin_t('ex_bprint', 0, -23),
    progs.exbuiltin_t('ex_sprint', 0, -24),
    progs.exbuiltin_t('ex_finaleFinished', 0, -79),
    progs.exbuiltin_t('ex_localsound', 0, -80),
    progs.exbuiltin_t('ex_draw_point', 0, -81),
    progs.exbuiltin_t('ex_draw_line', 0, -82),
    progs.exbuiltin_t('ex_draw_arrow', 0, -83),
    progs.exbuiltin_t('ex_draw_ray', 0, -84),
    progs.exbuiltin_t('ex_draw_circle', 0, -85),
    progs.exbuiltin_t('ex_draw_bounds', 0, -86),
    progs.exbuiltin_t('ex_draw_worldtext', 0, -87),
    progs.exbuiltin_t('ex_draw_sphere', 0, -88),
    progs.exbuiltin_t('ex_draw_cylinder', 0, -89),
    progs.exbuiltin_t('ex_CheckPlayerEXFlags', 0, -90),
    progs.exbuiltin_t('ex_walkpathtogoal', 0, -91),
    progs.exbuiltin_t('ex_bot_movetopoint', 0, -92),
    progs.exbuiltin_t('ex_bot_followentity', 0, -92),
]


def PR_PatchRereleaseBuiltins(func: dfunction_t) -> None:
    """Patches functions loading Nightdive / KEX re-release builtins to match engine builtin indices."""
    func_name = PR_GetString(func.s_name)

    for entry in exbuiltins:
        if getattr(entry, 'name', None) is None:
            break

        first_stmt = getattr(
            entry, 'first_statement', getattr(entry, 'old_id', 0)
        )
        patch_stmt = getattr(
            entry, 'patch_statement', getattr(entry, 'new_id', 0)
        )

        if first_stmt != 0 and func.first_statement == first_stmt:
            func.first_statement = patch_stmt
            return

        if first_stmt == 0 and func_name == entry.name:
            func.first_statement = patch_stmt
            return


def PR_LoadProgs() -> None:
    """Loads and initializes progs.dat into VM state tables and structs."""
    global progz, pr_functions, pr_strings, pr_globaldefs, pr_fielddefs
    global pr_statements, pr_global_struct, pr_crc
    global pr_numknownstrings, pr_maxknownstrings, pr_stringssize, pr_knownstrings
    global pr_alpha_supported, pr_edict_size, pr_effects_mask, gefvCache

    for i in range(GEFV_CACHESIZE):
        gefvCache[i].field = ''

    raw_data = common.COM_LoadHunkFile('progs.dat', False)
    if not raw_data:
        ffr = common.COM_OpenFile('progs.dat')
        print('DBG handle=', ffr.handle, 'size=', ffr.filesize, 'pak=', ffr.is_pak)
        import sys_sdl_unix
        print('DBG sys_handles=', getattr(sys_sdl_unix, 'sys_handles', None))
        host.Host_Error("PR_LoadProgs: couldn't load progs.dat")

    console.Con_Printf(f'Programs occupy {len(raw_data) // 1024}K.\n')

    pr_crc = crc.CRC_Init()
    for byte_val in raw_data:
        b = ord(byte_val) if isinstance(byte_val, str) else byte_val
        pr_crc = crc.CRC_ProcessByte(pr_crc, b)

    progz = dprograms_t.from_bytes(raw_data[:60])

    if progz.version != PROG_VERSION:
        host.Host_Error(
            f'progs.dat has wrong version number ({progz.version} should be {PROG_VERSION})'
        )
    if progz.crc != progdefs.PROGHEADER_CRC:
        host.Host_Error(
            'progs.dat system vars have been modified, progdefs.h is out of date'
        )

    if progz.ofs_strings + progz.numstrings > len(raw_data):
        host.Host_Error('progs.dat strings go past end of file\n')

    pr_strings = raw_data[
        progz.ofs_strings : progz.ofs_strings + progz.numstrings
    ].decode('latin-1')

    pr_numknownstrings = 0
    pr_maxknownstrings = 0
    pr_stringssize = progz.numstrings
    pr_knownstrings = []
    PR_SetEngineString('')

    pr_statements = []
    stmt_ofs = progz.ofs_statements
    for _ in range(progz.numstatements):
        stmt = dstatement_t.from_bytes(raw_data[stmt_ofs : stmt_ofs + 8])
        pr_statements.append(stmt)
        stmt_ofs += 8

    pr_functions = []
    func_ofs = progz.ofs_functions
    for _ in range(progz.numfunctions):
        func = dfunction_t.from_bytes(raw_data[func_ofs : func_ofs + 36])
        pr_functions.append(func)
        func_ofs += 36

    pr_globaldefs = []
    gdef_ofs = progz.ofs_globaldefs
    for _ in range(progz.numglobaldefs):
        gdef = ddef_t.from_bytes(raw_data[gdef_ofs : gdef_ofs + 8])
        pr_globaldefs.append(gdef)
        gdef_ofs += 8

    pr_alpha_supported = False
    pr_fielddefs = []
    fdef_ofs = progz.ofs_fielddefs

    for _ in range(progz.numfielddefs):
        fdef = ddef_t.from_bytes(raw_data[fdef_ofs : fdef_ofs + 8])

        if fdef.type & DEF_SAVEGLOBAL:
            host.Host_Error(
                'PR_LoadProgs: pr_fielddefs[i].type & DEF_SAVEGLOBAL'
            )

        pr_fielddefs.append(fdef)
        fdef_ofs += 8

        f_name = PR_GetString(fdef.s_name)
        if f_name == 'alpha':
            pr_alpha_supported = True

    # Globals are raw 32-bit words. Slots typed string/entity/field/function/
    # pointer hold ints; everything else holds floats. Reading an int word as
    # float32 turns it into a ~1e-42 denormal that int() truncates to 0.
    n = progz.numglobals
    as_floats = struct.unpack_from(f'<{n}f', raw_data, progz.ofs_globals)
    as_words = struct.unpack_from(f'<{n}i', raw_data, progz.ofs_globals)
    pr_globals.clear()  # in place: globalvars_t keeps a reference to this list
    pr_globals.extend(as_floats)
    int_types = (
        etype_t.ev_string.value,
        etype_t.ev_entity.value,
        etype_t.ev_field.value,
        etype_t.ev_function.value,
        etype_t.ev_pointer.value,
    )
    for gd in pr_globaldefs:
        if (gd.type & ~DEF_SAVEGLOBAL) in int_types and gd.ofs < n:
            pr_globals[gd.ofs] = as_words[gd.ofs]

    pr_global_struct = GlobalVars()

    pr_edict_size = progz.entityfields * 4

    for func in pr_functions:
        PR_PatchRereleaseBuiltins(func)

    pr_effects_mask = PR_FindSupportedEffects()


def ED_Nomonsters_f(cvar):
    if cvar.value:
        console.Con_Warning(f'{cvar.name} can break gameplay')


def PR_Init():
    _cmd.Cmd_AddCommand('edict', ED_PrintEdict_f)
    _cmd.Cmd_AddCommand('edicts', ED_PrintEdicts_f)
    _cmd.Cmd_AddCommand('edictcount', ED_Count)
    _cmd.Cmd_AddCommand('profile', pr_exec.PR_Profile_f)

    nomonsters = {
        'name': 'nomonsters',
        'value': '0',
        'flags': cvar.CVAR_NONE,
    }
    gamecfg = {'name': 'gamecfg', 'value': '0', 'flags': cvar.CVAR_NONE}
    scratch1 = {'name': 'scratch1', 'value': '0', 'flags': cvar.CVAR_NONE}
    scratch2 = {'name': 'scratch2', 'value': '0', 'flags': cvar.CVAR_NONE}
    scratch3 = {'name': 'scratch3', 'value': '0', 'flags': cvar.CVAR_NONE}
    scratch4 = {'name': 'scratch4', 'value': '0', 'flags': cvar.CVAR_NONE}
    savedgamecfg = {
        'name': 'savedgamecfg',
        'value': '0',
        'flags': cvar.CVAR_NONE,
    }
    saved1 = {'name': 'saved1', 'value': '0', 'flags': cvar.CVAR_NONE}
    saved2 = {'name': 'saved2', 'value': '0', 'flags': cvar.CVAR_NONE}
    saved3 = {'name': 'saved3', 'value': '0', 'flags': cvar.CVAR_NONE}
    saved4 = {'name': 'saved4', 'value': '0', 'flags': cvar.CVAR_NONE}

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
    if n < 0 or n >= sv_main.sv.max_edicts:
        host.Host_Error(f'EDICT_NUM: bad number {n}')

    return sv_main.sv.edicts[n]


def NUM_FOR_EDICT(e):
    b = _edict_index(e)

    if b < 0 or b >= sv_main.sv.num_edicts:
        host.Host_Error('NUM_FOR_EDICT: bad pointer')

    return b


def PR_AllocString(size: int) -> tuple[int, str]:
    global pr_numknownstrings

    if not size:
        return 0, ''

    i = 0
    for i in range(pr_numknownstrings):
        if pr_knownstrings[i] is None:
            break
    else:
        i = pr_numknownstrings

    if i >= pr_maxknownstrings:
        PR_AllocStringSlots()

    pr_numknownstrings += 1

    allocated_str = '\x00' * size

    if i < len(pr_knownstrings):
        pr_knownstrings[i] = allocated_str
    else:
        pr_knownstrings.append(allocated_str)

    return -1 - i, pr_knownstrings[i]


def PR_AllocStringSlots() -> None:
    global pr_maxknownstrings, pr_knownstrings

    pr_maxknownstrings += PR_STRING_ALLOCSLOTS
    console.Con_DPrintf(
        f"PR_AllocStringSlots: realloc'ing for {pr_maxknownstrings} slots\n"
    )

    if pr_knownstrings is None:
        pr_knownstrings = []

    current_len = len(pr_knownstrings)
    if current_len < pr_maxknownstrings:
        pr_knownstrings.extend([None] * (pr_maxknownstrings - current_len))


def PR_GetString(num) -> str:
    if num is None:
        return ''

    # Cast VM float offset (or eval_t) to integer byte offset
    if isinstance(num, float):
        num = int(num)

    # Negative index maps to pr_knownstrings (-1 -> slot 0, -2 -> slot 1)
    if num < 0:
        idx = -1 - num
        if idx < len(pr_knownstrings) and pr_knownstrings[idx] is not None:
            return pr_knownstrings[idx]
        return ''

    # Ensure pr_strings is treated as bytes
    if isinstance(pr_strings, str):
        # Fallback if pr_strings was stored as str
        raw_bytes = pr_strings.encode('latin-1')
    else:
        raw_bytes = pr_strings

    if num >= len(raw_bytes):
        return ''

    # Find trailing null byte in raw memory
    null_ofs = raw_bytes.find(b'\x00', num)
    if null_ofs == -1:
        extracted = raw_bytes[num:]
    else:
        extracted = raw_bytes[num:null_ofs]

    # Decode safely into a standard Python string
    return extracted.decode('latin-1', errors='ignore')


def PR_SetEngineString(s: str | None) -> int:
    global pr_numknownstrings, pr_knownstrings

    if not s:
        return 0

    # Match exact null-terminated strings in static pr_strings
    if pr_strings:
        target = s + '\x00'
        ofs = pr_strings.find(target)
        if ofs != -1:
            return ofs

    # Match in dynamic pr_knownstrings
    if pr_knownstrings:
        for i in range(pr_numknownstrings):
            if pr_knownstrings[i] == s:
                return -1 - i

    i = 0
    for i in range(pr_numknownstrings):
        if pr_knownstrings[i] is None:
            break
    else:
        i = pr_numknownstrings

    if i >= pr_maxknownstrings:
        PR_AllocStringSlots()

    pr_numknownstrings += 1

    if i < len(pr_knownstrings):
        pr_knownstrings[i] = s
    else:
        pr_knownstrings.append(s)

    return -1 - i