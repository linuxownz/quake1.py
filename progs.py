#progs.py

import protocol
import sv_main

MAX_ENT_LEAFS = 32

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
        self.area : int  = 0
        self.num_leafs: int = 0
        self.leafnums : list[int] = [0 for i in range(MAX_ENT_LEAFS)]

        self.baseline : protocol.entity_state_t = None
        self.alpha : int = 0
        self.scale : int = 0
        self.sendinterval : bool = False
        self.oldframe : float = 0.0
        self.oldthinktime : float = 0.0
        self.freetime : float = 0.0

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