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
        self.data = [0]

class dma_t:
    def __init__(self):
        self.channels = 0
        self.samples = 0
        self.submission_chunk = 0
        self.samplepos = 0
        self.samplebits = 0
        self.signed8 = 0
        self.speed = 0
        self.buffer = None

class channel_t:
    def __init__(self):
        self.sfx : sfx_t = None
        self.leftvol = 0
        self.rightvol = 0
        self.end = 0
        self.pos = 0
        self.looping = 0
        self.entnum = 0
        self.entchannel = 0
        self.origin = [0, 0, 0]
        self.dist_mult = [0, 0, 0]
        self.master_vol = 0

class wavinfo_t:
    def __init__(self):
        self.rate = 0
        self.width = 0
        self.channels = 0
        self.loopstart = 0
        self.samples = 0
        self.dataofs = 0