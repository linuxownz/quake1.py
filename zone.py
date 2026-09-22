# zone.py

DYNAMIC_SIZE = (4 * 1024 * 1024)
ZONEID = 0x1d4a11
MINFRAGMENT = 64
PARANOID = 1
HUNK_SENTINEL = 0x1df001ed
HUNKNAME_LEN  = 24
CACHENAME_LEN = 32

class MemBlock:
    def __init__(self, size, tag, data_view=None):
        self.size = size
        self.tag = tag      # 0 = free, 1 = used, 2 = fixed
        self.data = data_view

        # Pointers (References)
        self.next = None
        self.prev = None

    @property
    def is_free(self):
        return self.tag == 0

class cache_user_t:
    def __init__(self):
        self.data = None

class hunk_t:
    def __init__(self, sentinel, size, name):
        self.sentinel = 0
        self.size = 0
        self.name = ''

class GlobalMemory:
    hunk_base = None
    hunk_size = 0
    hunk_low_used = 0
    hunk_high_used = 0
    hunk_tempactive = False
    hunk_tempmark = 0
    mainzone = None

class CacheManager:
    def __init__(self):
        # A list of headers that we can search through
        self.headers = []
        # Points to the oldest item (to be kicked out first)
        self.lru_head = None
        self.lru_tail = None

class ZoneManager:
    def __init__(self, buffer_slice, size):
        # zone_buf from Hunk_AllocName is already a slice of main_buffer
        self.buffer = buffer_slice
        self.total_size = size

        # 1. Create the Sentinel (C: zone->blocklist)
        # It has 0 size and is always 'In Use' (tag=1)
        self.blocklist = MemBlock(size=0, tag=1)

        # 2. Create the first big free block (C: zone->rover)
        # This view covers the entire buffer_slice
        full_view = memoryview(self.buffer)
        first_block = MemBlock(size=size, tag=0, data_view=full_view)

        # 3. Link them together (The circular doubly linked list)
        self.blocklist.next = first_block
        self.blocklist.prev = first_block

        first_block.next = self.blocklist
        first_block.prev = self.blocklist

        # 4. Set the rover to the first available block
        self.rover = first_block


#--------------------------------------------------------------

def Cache_Flush():
    raise NotImplementedError

def Cache_Init():
    global cache_system
    cache_system = CacheManager()

    import _cmd
    _cmd.Cmd_AddCommand('flush', Cache_Flush)

def Hunk_Check():
    print('Hunk_Check not implemented yet')

def Cache_FreeLow(used):
    pass

def Z_Malloc(size):
    """
    Direct conversion of Z_Malloc.
    Finds a block in the mainzone_manager and returns its data view.
    """
    zone = mainzone_manager
    # 1. Account for the header/alignment logic
    # (Simplified for Pythonic logic)

    # Start searching at the rover
    start = zone.rover
    current = start

    while True:
        # Check if the current block is free and large enough
        if current.is_free and current.size >= size:
            break

        current = current.next

        # If we looped all the way back to the start, the zone is full
        if current == start:
            raise MemoryError(f"Z_Malloc: failed on allocation of {size} bytes")

    # 2. Split the block if it's significantly larger than requested
    # We use MINFRAGMENT (64) to prevent tiny "useless" blocks
    if current.size - size >= MINFRAGMENT:
        # Create a view for the 'extra' memory that will remain free
        remaining_view = current.data[size:]
        remaining_size = current.size - size

        # Create the new free block
        new_block = MemBlock(size=remaining_size, tag=0, data_view=remaining_view)

        # Link the new block into the list
        new_block.next = current.next
        new_block.prev = current
        current.next.prev = new_block
        current.next = new_block

        # Shrink the current block to the requested size
        current.data = current.data[:size]
        current.size = size

    # 3. Mark current block as used (tag 1)
    current.tag = 1

    # 4. Move the rover to the next block to distribute future allocations
    zone.rover = current.next
    if zone.rover == zone.blocklist:
        zone.rover = zone.blocklist.next

    return current.data

def Hunk_AllocName(size, name) -> bytes:
    # Calculate where the new memory starts
    start = GlobalMemory.hunk_low_used

    # Check for overflow
    if start + size > GlobalMemory.hunk_size:
        raise Exception(f"Hunk_Alloc: overflow on {name}")

    # Update the "pointer" (the index)
    GlobalMemory.hunk_low_used += size

    # Return a "pointer" (a slice of the buffer)
    return GlobalMemory.hunk_base[start : start + size]


def Memory_InitZone(zone, size):
    """
    Direct conversion of Memory_InitZone.
    zone_buf: the memoryview/slice returned by Hunk_AllocName
    size: the total size of that slice
    """
    # In Python, we initialize our Manager object with the slice.
    # This replaces the C logic of setting zone->blocklist.next, etc.

    global mainzone_manager
    mainzone_manager = ZoneManager(zone, size)

    # The original C code also set the ID and size here.
    # Our ZoneManager constructor handles this internally by
    # creating the first MemBlock.


def Hunk_Print_f():
    pass

def Z_Free(ptr):
    """
    Direct conversion of Z_Free.
    In Python, 'ptr' is the data_view (memoryview) of the block.
    """
    # 1. Find the block header that owns this data
    # We navigate via the global mainzone_manager
    zone = mainzone_manager

    # Start searching from the blocklist
    block = zone.blocklist.next
    found = False

    while block != zone.blocklist:
        if block.data is ptr:
            found = True
            break
        block = block.next

    if not found:
        print("Error: Z_Free: freed a pointer without a block")
        return

    # 2. Mark as free
    block.tag = 0

    # 3. Coalesce with neighbor to the RIGHT
    other = block.next
    if other != zone.blocklist and other.is_free:
        # Update the memoryview to cover both blocks
        # We slice from the start of current block to the end of the next block
        new_total_size = block.size + other.size
        # This assumes the memory is contiguous (which it is in our Hunk)
        # Note: This is more for completeness than functionality
        block.size = new_total_size

        block.next = other.next
        other.next.prev = block

    # 4. Coalesce with neighbor to the LEFT
    other = block.prev
    if other != zone.blocklist and other.is_free:
        other.size += block.size
        other.next = block.next
        block.next.prev = other
        if zone.rover == block:
            zone.rover = other


def Memory_Init(buf, total_size):
    # 1. Setup Hunk limits using the TOTAL buffer size
    GlobalMemory.hunk_base = memoryview(buf)
    GlobalMemory.hunk_size = total_size
    GlobalMemory.hunk_low_used = 0
    GlobalMemory.hunk_high_used = 0

    Cache_Init()

    # 2. Set the default size for the dynamic zone (heap)
    # We use our constant, but allow the command line to override it
    zonesize = DYNAMIC_SIZE

    import common
    p = common.COM_CheckParm('-zone')
    if p:
        if p < common.com_argc - 1:
            try:
                # Convert KB to Bytes
                zonesize = int(common.com_argv[p+1]) * 1024
            except ValueError:
                print("Warning: Invalid -zone value, using default.")
        else:
            print('Memory_Init: must specify size in KB after -zone')

    # 3. Carve the zone out of the hunk base
    # This moves hunk_low_used forward by 'zonesize'
    zone_buf = Hunk_AllocName(zonesize, 'zone')

    # 4. Initialize the ZoneManager logic within that slice
    Memory_InitZone(zone_buf, zonesize)

    import _cmd
    _cmd.Cmd_AddCommand('hunk_print', Hunk_Print_f)

