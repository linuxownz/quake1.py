#q_sound.py

import zone

MAX_CHANNELS          = 1024
MAX_DYNAMIC_CHANNELS  = 128
MAX_RAW_SAMPLES       = 8192

WAV_FORMAT_PCM        = 1

class portable_samplepair_t:
    def __init__(self):
        self.left  = 0
        self.right = 0

class sfx_t:
    def __init__(self):
        self.name = ''
        self.cache : zone.cache_user_t = None #  is just void *data

class sfxcache_t:
    def __init__(self):
        self.length = 0
        self.loopstart = 0
        self.speed = 0
        self.width = 0
        self.stereo = 0
        self.data = [0] # variable sized, should be bytearray?

class dma_t:
    def __init__(self):
        self.channels = 0
        self.samples = 0
        self.submission_chunk = 0
        self.samplepos = 0
        self.samplebits = 0
        self.signed8 = 0
        self.speed = 0
        self.buffer:bytearray = bytearray()

class channel_t:
    def __init__(self) -> None:
        self.clear()
    def clear(self) -> None:
        self.sfx: sfx_t | None = None  # C: sfx_t *sfx = NULL
        self.leftvol: int = 0  # C: int leftvol
        self.rightvol: int = 0  # C: int rightvol
        self.end: int = 0  # C: int end
        self.pos: int = 0  # C: int pos
        self.looping: int = 0  # C: qboolean looping
        self.entnum: int = 0  # C: int entnum
        self.entchannel: int = 0  # C: int entchannel
        self.origin: list[float] = [0.0, 0.0, 0.0]  # C: vec3_t origin
        self.dist_mult: float = 0.0  # C: float dist_mult
        self.master_vol: int = 0  # C: int master_vol

class wavinfo_t:
    def __init__(self):
        self.rate = 0
        self.width = 0
        self.channels = 0
        self.loopstart = 0
        self.samples = 0
        self.dataofs = 0