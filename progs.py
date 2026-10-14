#progs.py
import struct
from typing import Any
#from watchpoints import watch

import common
import pr_edict
import progdefs
import protocol
import quakedef
import sv_main

MAX_ENT_LEAFS = 32

# Memory backing allocations in engine state:
# pr_globals: list[float] or ctypes array of floats
#pr_globals: list[float] = [0.0] * 2048 # this is a duplicate. original is in pr_edict.p
#watch(pr_globals)

class eval_t:
    def __init__(self):
        self.string : int = 0
        self._float : float = 0.0
        self.vector : list[float] = [0., 0., 0.]
        self.function : int = 0
        self._int : int = 0
        self.edict : int = 0

class edict_t:
    def __init__(self):
        self.free : bool = False
        self.area : quakedef.link_t = quakedef.link_t()
        self.num_leafs: int = 0
        self.leafnums : list[int] = [0 for i in range(MAX_ENT_LEAFS)]

        self.baseline : protocol.entity_state_t =protocol.entity_state_t()
        self.alpha : int = 0
        self.scale : int = 0
        self.sendinterval : bool = False
        self.oldframe : float = 0.0
        self.oldthinktime : float = 0.0
        self.freetime : float = 0.0
        self.v: progdefs.entvars_t = progdefs.entvars_t()

class exbuiltin_t:
    def __init__(self, name, first, patch):
        self.name = name
        self.first_statement = first
        self.patch_statement = patch

def EDICT_TO_PROG(e):
    """
    Converts an edict object to its integer index in the global array.
    Matches: (int)((byte *)e - (byte *)sv.edicts)
    """
    if e is None:
        return 0
    try:
        # sv_main.sv.edicts is the list of edict objects
        return sv_main.sv.edicts.index(e)
    except ValueError:
        return 0

def PROG_TO_EDICT(i):
    """
    Converts an integer index back to the corresponding edict object.
    Matches: ((edict_t *)((byte *)sv.edicts + e))
    """
    if i < 0 or i >= len(sv_main.sv.edicts):
        return None # Or return the world entity (edicts[0]) depending on context
    return sv_main.sv.edicts[i]

def NEXT_EDICT(e):
    """
    Returns the next edict in the global edict list.
    Matches: ((edict_t *)( (byte *)e + pr_edict_size))
    """
    if e is None:
        return None

    try:
        # 1. Find the current index of the entity
        idx = sv_main.sv.edicts.index(e)

        # 2. Return the next one if it exists within bounds
        if idx + 1 < len(sv_main.sv.edicts):
            return sv_main.sv.edicts[idx + 1]
    except ValueError:
        # Entity not found in the list
        pass

    return None


# Helper for C int-to-float pointer typecasting (*(int *)&pr_globals[o])
def _float_to_int(val: float) -> int:
    v = struct.unpack("i", struct.pack("f", val))[0]
    return v


def _int_to_float(val: int) -> float:
    return struct.unpack("f", struct.pack("i", val))[0]


# --- Global Memory Accessors (G_*) ---


def G_INT(o: int) -> int:
    """Retrieves an integer/string/edict index from pr_globals[o]."""
    val = pr_edict.pr_globals[o]

    if isinstance(val, int):
        return val

    if isinstance(val, float):
        # If it's a whole number in standard range (like 63.0), cast directly
        if val.is_integer() and -2147483648 <= val <= 2147483647:
            return int(val)
        # If it's a bit-pattern float (e.g. subnormal/IEEE float representation)
        return struct.unpack('<i', struct.pack('<f', val))[0]

    return 0

def G_FLOAT(o: int) -> float:
    """Reinterprets the bit pattern of pr_globals[o] as a 32-bit float."""
    val = pr_edict.pr_globals[o]
    if isinstance(val, float):
        return val
    # Bit-cast int32 bits to float32
    return struct.unpack("<f", struct.pack("<i", val))[0]


def G_EDICT(o: int) -> Any:
    """#define G_EDICT(o) EDICT_NUM(G_INT(o))"""
    e_num = G_INT(o)

    # In Quake C, if e_num is a raw byte offset rather than a direct edict index,
    # convert byte offset to entity index using entityfields
    if e_num >= 1024:
        byte_size = pr_edict.progz.entityfields * 4
        if byte_size > 0:
            e_num = e_num // byte_size

    return pr_edict.EDICT_NUM(e_num)


def G_EDICTNUM(o: int) -> int:
    """#define G_EDICTNUM(o) NUM_FOR_EDICT(G_EDICT(o))"""
    return sv.NUM_FOR_EDICT(G_EDICT(o))


def G_VECTOR(o: int) -> list[float]:
    """#define G_VECTOR(o) (&pr_globals[o])

    Returns 3-element slice matching continuous vec3_t globals layout [x, y, z].
    """
    return [pr_edict.pr_globals[o], pr_edict.pr_globals[o + 1], pr_edict.pr_globals[o + 2]]


def G_STRING(o: int) -> str:
    """#define G_STRING(o) (PR_GetString(*(string_t *)&pr_globals[o]))"""
    str_offset = G_INT(o)
    return pr_edict.PR_GetString(str_offset)


def G_FUNCTION(o: int) -> int:
    """#define G_FUNCTION(o) (*(func_t *)&pr_globals[o])"""
    return G_INT(o)


# --- Edict Entity Variable Accessors (E_*) ---


def E_FLOAT(e: Any, o: int) -> float:
    """#define E_FLOAT(e,o) (((float*)&e->v)[o])"""
    return e.v[o]


def E_INT(e: Any, o: int) -> int:
    """#define E_INT(e,o) (*(int *)&((float*)&e->v)[o])"""
    return _float_to_int(e.v[o])


def E_VECTOR(e: Any, o: int) -> list[float]:
    """#define E_VECTOR(e,o) (&((float*)&e->v)[o])"""
    return [e.v[o], e.v[o + 1], e.v[o + 2]]


def E_STRING(e: Any, o: int) -> str:
    """#define E_STRING(e,o) (PR_GetString(*(string_t *)&((float*)&e->v)[o]))"""
    str_offset = E_INT(e, o)
    return progs.PR_GetString(str_offset)