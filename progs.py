#progs.py

import protocol

MAX_ENT_LEAFS = 32

class eval_t():
    def __init__(self):
        self.string : int = 0
        self._float : float = 0.0
        self.vector : list[float] = [0., 0., 0.]
        self.function : int = 0
        self._int : int = 0
        self.edict : int = 0

class edict_t():
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
