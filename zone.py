# zone.py

DYNAMIC_SIZE = 4 * 1024 * 1024
ZONEID = 0x1D4A11
MINFRAGMENT = 64
PARANOID = 1
HUNK_SENTINEL = 0x1DF001ED
HUNKNAME_LEN = 24
CACHENAME_LEN = 32


class MemBlock:
    def __init__(self, size: int, tag: int, data_view: memoryview | None = None):
        self.size = size
        self.tag = tag  # 0 = free, >0 = used/tag id
        self.id = ZONEID
        self.data = data_view      # Full block view (len == block.size)
        self.payload = None        # Returned payload view
        self.offset = 0
        self.next: 'MemBlock' = self
        self.prev: 'MemBlock' = self

    @property
    def is_free(self) -> bool:
        return self.tag == 0


class cache_user_t:
    def __init__(self):
        self.data: memoryview | None = None
        self._cache_sys: 'cache_system_t | None' = None


class cache_system_t:
    """C equivalent (zone.c): struct cache_system_s"""

    def __init__(self, size: int = 0, name: str = ""):
        self.size: int = size
        self.name: str = name[:CACHENAME_LEN]
        self.user: cache_user_t | None = None
        self.prev: 'cache_system_t' = self
        self.next: 'cache_system_t' = self
        self.lru_prev: 'cache_system_t | None' = None
        self.lru_next: 'cache_system_t | None' = None
        self.data: memoryview | None = None
        self.offset: int = 0


class hunk_t:
    def __init__(self, sentinel: int, size: int, name: str):
        self.sentinel = sentinel
        self.size = size
        self.name = name[:HUNKNAME_LEN]
        self.is_high: bool = False
        self.offset: int = 0


class GlobalMemory:
    hunk_base: bytearray | memoryview | None = None
    hunk_size: int = 0
    hunk_low_used: int = 0
    hunk_high_used: int = 0
    hunk_tempactive: bool = False
    hunk_tempmark: int = 0
    cache_head: cache_system_t | None = None
    hunk_headers: list[hunk_t] = []


class ZoneManager:
    def __init__(self, buffer_slice: memoryview, size: int):
        self.buffer = buffer_slice
        self.total_size = size

        # 1. Create sentinel cap for blocklist
        self.blocklist = MemBlock(size=0, tag=1)
        self.blocklist.id = 0

        # 2. First large free block
        first_block = MemBlock(size=size, tag=0, data_view=memoryview(self.buffer))

        # 3. Circular double linking
        self.blocklist.next = first_block
        self.blocklist.prev = first_block
        first_block.next = self.blocklist
        first_block.prev = self.blocklist

        self.rover = first_block


mainzone_manager: ZoneManager | None = None


# ==============================================================================
# ZONE MEMORY ALLOCATION
# ==============================================================================

def Z_CheckHeap() -> None:
    """C equivalent: Z_CheckHeap"""
    import common

    if mainzone_manager is None:
        return

    block = mainzone_manager.blocklist.next
    while True:
        if block.next == mainzone_manager.blocklist:
            break

        if block.next.prev != block:
            common.Sys_Error("Z_CheckHeap: next block doesn't have proper back link")

        if block.is_free and block.next.is_free:
            common.Sys_Error("Z_CheckHeap: two consecutive free blocks")

        if block.data is not None and len(block.data) != block.size:
            common.Sys_Error("Z_CheckHeap: block size does not match data buffer length")

        block = block.next


def Z_Free(ptr: memoryview | None) -> None:
    """C equivalent: Z_Free"""
    import common

    if ptr is None:
        common.Sys_Error("Z_Free: NULL pointer")

    zone = mainzone_manager
    if zone is None:
        return

    block = zone.blocklist.next
    found = False
    while block != zone.blocklist:
        if block.payload is ptr or block.data is ptr:
            found = True
            break
        block = block.next

    if not found or block.id != ZONEID:
        common.Sys_Error("Z_Free: freed a pointer without ZONEID")
    if block.is_free:
        common.Sys_Error("Z_Free: freed a freed pointer")

    block.tag = 0  # Mark as free
    block.payload = None

    # Merge with previous free block
    other = block.prev
    if other != zone.blocklist and other.is_free:
        other.size += block.size
        if other.data is not None and block.data is not None:
            full_buf = other.data.obj if hasattr(other.data, 'obj') else zone.buffer
            start_off = other.offset
            other.data = memoryview(full_buf)[start_off : start_off + other.size]
        other.next = block.next
        block.next.prev = other
        if zone.rover == block:
            zone.rover = other
        block = other

    # Merge with next free block
    other = block.next
    if other != zone.blocklist and other.is_free:
        block.size += other.size
        if block.data is not None and other.data is not None:
            full_buf = block.data.obj if hasattr(block.data, 'obj') else zone.buffer
            start_off = block.offset
            block.data = memoryview(full_buf)[start_off : start_off + block.size]
        block.next = other.next
        other.next.prev = block
        if zone.rover == other:
            zone.rover = block


def Z_TagMalloc(size: int, tag: int) -> memoryview | None:
    """C equivalent: Z_TagMalloc"""
    import common

    if not tag:
        common.Sys_Error("Z_TagMalloc: tried to use a 0 tag")

    zone = mainzone_manager
    if zone is None:
        return None

    HEADER_SIZE = 32
    alloc_size = (size + HEADER_SIZE + 7) & ~7

    base = rover = zone.rover
    start = base.prev

    while True:
        if rover == start:
            return None

        if not rover.is_free:
            rover = rover.next
            base = rover
        else:
            rover = rover.next

        if base.is_free and base.size >= alloc_size:
            break

    extra = base.size - alloc_size
    if extra > MINFRAGMENT:
        remaining_view = base.data[alloc_size:] if base.data is not None else None
        newblock = MemBlock(size=extra, tag=0, data_view=remaining_view)
        newblock.offset = base.offset + alloc_size
        newblock.prev = base
        newblock.next = base.next
        newblock.next.prev = newblock
        base.next = newblock

        base.size = alloc_size
        if base.data is not None:
            base.data = base.data[:alloc_size]

    base.tag = tag
    base.id = ZONEID
    zone.rover = base.next

    if base.data is not None:
        base.payload = base.data[HEADER_SIZE : HEADER_SIZE + size]
        return base.payload
    return None


def Z_Malloc(size: int) -> memoryview:
    """C equivalent: Z_Malloc"""
    import common

    Z_CheckHeap()
    buf = Z_TagMalloc(size, 1)
    if buf is None:
        common.Sys_Error(f"Z_Malloc: failed on allocation of {size} bytes")

    buf[:] = b"\x00" * len(buf)
    return buf


def Z_Realloc(ptr: memoryview | None, size: int) -> memoryview:
    """C equivalent: Z_Realloc"""
    import common

    if ptr is None:
        return Z_Malloc(size)

    zone = mainzone_manager
    if zone is None:
        common.Sys_Error("Z_Realloc: uninitialized mainzone")

    block = zone.blocklist.next
    found = False
    while block != zone.blocklist:
        if block.payload is ptr or block.data is ptr:
            found = True
            break
        block = block.next

    if not found or block.id != ZONEID:
        common.Sys_Error("Z_Realloc: realloced a pointer without ZONEID")
    if block.is_free:
        common.Sys_Error("Z_Realloc: realloced a freed pointer")

    HEADER_SIZE = 32
    old_payload_size = max(0, block.size - HEADER_SIZE)
    old_ptr = ptr

    Z_Free(ptr)
    new_ptr = Z_TagMalloc(size, 1)
    if new_ptr is None:
        common.Sys_Error(f"Z_Realloc: failed on allocation of {size} bytes")

    copy_bytes = min(old_payload_size, size)
    new_ptr[:copy_bytes] = old_ptr[:copy_bytes]

    if old_payload_size < size:
        new_ptr[old_payload_size:size] = b"\x00" * (size - old_payload_size)

    return new_ptr


def Z_Strdup(s: str) -> memoryview:
    """C equivalent: Z_Strdup"""
    s_bytes = s.encode("utf-8") + b"\x00"
    ptr = Z_Malloc(len(s_bytes))
    ptr[: len(s_bytes)] = s_bytes
    return ptr


def Z_Print(zone: ZoneManager | None = None) -> None:
    """C equivalent: Z_Print"""
    import common

    if zone is None:
        zone = mainzone_manager

    if zone is None:
        return

    common.Con_Printf(f"zone size: {zone.total_size}  location: 0x{id(zone):x}\n")

    block = zone.blocklist.next
    while True:
        common.Con_Printf(
            f"block:0x{id(block):x}    size:{block.size:7d}    tag:{block.tag:3d}\n"
        )
        if block.next == zone.blocklist:
            break
        if block.next.prev != block:
            common.Con_Printf("ERROR: next block doesn't have proper back link\n")
        if block.is_free and block.next.is_free:
            common.Con_Printf("ERROR: two consecutive free blocks\n")
        block = block.next


# ==============================================================================
# HUNK MEMORY ALLOCATION
# ==============================================================================

def Hunk_Check() -> None:
    """C equivalent: Hunk_Check"""
    import common

    if GlobalMemory.hunk_base is None:
        return

    for h in GlobalMemory.hunk_headers:
        if h.sentinel != HUNK_SENTINEL:
            common.Sys_Error("Hunk_Check: trashed sentinel")
        if h.size < 32 or h.size > GlobalMemory.hunk_size:
            common.Sys_Error("Hunk_Check: bad size")


def Hunk_Print(all_blocks: bool = False) -> None:
    """C equivalent: Hunk_Print"""
    import common

    count = 0
    sum_bytes = 0
    totalblocks = 0

    common.Con_Printf(f"          :{GlobalMemory.hunk_size:8d} total hunk size\n")
    common.Con_Printf("-------------------------\n")

    low_headers = [h for h in GlobalMemory.hunk_headers if not h.is_high]
    high_headers = [h for h in GlobalMemory.hunk_headers if h.is_high]

    for section_idx, block_list in enumerate([low_headers, high_headers]):
        if section_idx == 1:
            remaining = GlobalMemory.hunk_size - GlobalMemory.hunk_low_used - GlobalMemory.hunk_high_used
            common.Con_Printf("-------------------------\n")
            common.Con_Printf(f"          :{remaining:8d} REMAINING\n")
            common.Con_Printf("-------------------------\n")

        for i, h in enumerate(block_list):
            if h.sentinel != HUNK_SENTINEL:
                common.Sys_Error("Hunk_Check: trashed sentinel")
            if h.size < 32 or h.size > GlobalMemory.hunk_size:
                common.Sys_Error("Hunk_Check: bad size")

            next_h = block_list[i + 1] if (i + 1) < len(block_list) else None
            count += 1
            totalblocks += 1
            sum_bytes += h.size

            name = h.name[: HUNKNAME_LEN - 1] if h.name else "unknown"

            if all_blocks:
                common.Con_Printf(f"0x{id(h):08x} :{h.size:8d} {name:>8s}\n")

            if next_h is None or h.name != next_h.name:
                if not all_blocks:
                    common.Con_Printf(f"          :{sum_bytes:8d} {name:>8s} (TOTAL)\n")
                count = 0
                sum_bytes = 0

    common.Con_Printf("-------------------------\n")
    common.Con_Printf(f"{totalblocks:8d} total blocks\n")


def Hunk_Print_f() -> None:
    """C equivalent: Hunk_Print_f"""
    import _cmd

    all_blocks = False
    if _cmd.Cmd_Argc() > 1:
        arg = _cmd.Cmd_Argv(1).lower()
        if arg in ("all", "-all", "1"):
            all_blocks = True

    Hunk_Print(all_blocks)

def Hunk_AllocName(size: int, name: str) -> memoryview:
    """C equivalent: Hunk_AllocName"""
    import common

    if PARANOID:
        Hunk_Check()

    if size < 0:
        common.Sys_Error(f"Hunk_Alloc: bad size: {size}")

    HEADER_SIZE = 32
    # Aligned total memory consumption inside the hunk
    aligned_size = HEADER_SIZE + ((size + 15) & ~15)

    free_space = GlobalMemory.hunk_size - GlobalMemory.hunk_low_used - GlobalMemory.hunk_high_used
    if free_space < aligned_size:
        common.Sys_Error(f"Hunk_Alloc: failed on {aligned_size} bytes")

    start = GlobalMemory.hunk_low_used
    GlobalMemory.hunk_low_used += aligned_size

    Cache_FreeLow(GlobalMemory.hunk_low_used)

    if GlobalMemory.hunk_base is not None:
        GlobalMemory.hunk_base[start : start + aligned_size] = b"\x00" * aligned_size

    h = hunk_t(sentinel=HUNK_SENTINEL, size=aligned_size, name=name)
    h.is_high = False
    h.offset = start
    GlobalMemory.hunk_headers.append(h)

    # Slice payload EXACTLY to requested 'size', not padded 'aligned_size'
    payload_start = start + HEADER_SIZE
    payload_end = payload_start + size
    return memoryview(GlobalMemory.hunk_base)[payload_start:payload_end]


def Hunk_HighAllocName(size: int, name: str) -> memoryview | None:
    """C equivalent: Hunk_HighAllocName"""
    import common

    if size < 0:
        common.Sys_Error(f"Hunk_HighAllocName: bad size: {size}")

    if GlobalMemory.hunk_tempactive:
        Hunk_FreeToHighMark(GlobalMemory.hunk_tempmark)
        GlobalMemory.hunk_tempactive = False

    if PARANOID:
        Hunk_Check()

    HEADER_SIZE = 32
    aligned_size = HEADER_SIZE + ((size + 15) & ~15)

    free_space = GlobalMemory.hunk_size - GlobalMemory.hunk_low_used - GlobalMemory.hunk_high_used
    if free_space < aligned_size:
        common.Con_Printf(f"Hunk_HighAlloc: failed on {aligned_size} bytes\n")
        return None

    GlobalMemory.hunk_high_used += aligned_size
    Cache_FreeHigh(GlobalMemory.hunk_high_used)

    start_offset = GlobalMemory.hunk_size - GlobalMemory.hunk_high_used

    if GlobalMemory.hunk_base is not None:
        GlobalMemory.hunk_base[start_offset : start_offset + aligned_size] = b"\x00" * aligned_size

    h = hunk_t(sentinel=HUNK_SENTINEL, size=aligned_size, name=name)
    h.is_high = True
    h.offset = start_offset
    GlobalMemory.hunk_headers.append(h)

    # Slice payload EXACTLY to requested 'size', not padded 'aligned_size'
    payload_start = start_offset + HEADER_SIZE
    payload_end = payload_start + size
    return memoryview(GlobalMemory.hunk_base)[payload_start:payload_end]

def Hunk_Alloc(size: int) -> memoryview:
    """C equivalent: Hunk_Alloc"""
    return Hunk_AllocName(size, "unknown")


def Hunk_LowMark() -> int:
    """C equivalent: Hunk_LowMark"""
    return GlobalMemory.hunk_low_used


def Hunk_FreeToLowMark(mark: int) -> None:
    """C equivalent: Hunk_FreeToLowMark"""
    import common

    if mark < 0 or mark > GlobalMemory.hunk_low_used:
        common.Sys_Error(f"Hunk_FreeToLowMark: bad mark {mark}")

    clear_bytes = GlobalMemory.hunk_low_used - mark
    if GlobalMemory.hunk_base is not None and clear_bytes > 0:
        GlobalMemory.hunk_base[mark : GlobalMemory.hunk_low_used] = b"\x00" * clear_bytes

    GlobalMemory.hunk_low_used = mark


def Hunk_HighMark() -> int:
    """C equivalent: Hunk_HighMark"""
    if GlobalMemory.hunk_tempactive:
        GlobalMemory.hunk_tempactive = False
        Hunk_FreeToHighMark(GlobalMemory.hunk_tempmark)

    return GlobalMemory.hunk_high_used


def Hunk_FreeToHighMark(mark: int) -> None:
    """C equivalent: Hunk_FreeToHighMark"""
    import common

    if GlobalMemory.hunk_tempactive:
        GlobalMemory.hunk_tempactive = False
        Hunk_FreeToHighMark(GlobalMemory.hunk_tempmark)

    if mark < 0 or mark > GlobalMemory.hunk_high_used:
        common.Sys_Error(f"Hunk_FreeToHighMark: bad mark {mark}")

    clear_bytes = GlobalMemory.hunk_high_used - mark
    if GlobalMemory.hunk_base is not None and clear_bytes > 0:
        start_offset = GlobalMemory.hunk_size - GlobalMemory.hunk_high_used
        end_offset = GlobalMemory.hunk_size - mark
        GlobalMemory.hunk_base[start_offset:end_offset] = b"\x00" * clear_bytes

    GlobalMemory.hunk_high_used = mark


def Hunk_AllocName(size: int, name: str) -> memoryview:
    """C equivalent: Hunk_AllocName"""
    import common

    if PARANOID:
        Hunk_Check()

    if size < 0:
        common.Sys_Error(f"Hunk_Alloc: bad size: {size}")

    HEADER_SIZE = 32
    # Aligned total memory consumption inside the hunk
    aligned_size = HEADER_SIZE + ((size + 15) & ~15)

    free_space = GlobalMemory.hunk_size - GlobalMemory.hunk_low_used - GlobalMemory.hunk_high_used
    if free_space < aligned_size:
        common.Sys_Error(f"Hunk_Alloc: failed on {aligned_size} bytes")

    start = GlobalMemory.hunk_low_used
    GlobalMemory.hunk_low_used += aligned_size

    Cache_FreeLow(GlobalMemory.hunk_low_used)

    if GlobalMemory.hunk_base is not None:
        GlobalMemory.hunk_base[start : start + aligned_size] = b"\x00" * aligned_size

    h = hunk_t(sentinel=HUNK_SENTINEL, size=aligned_size, name=name)
    h.is_high = False
    h.offset = start
    GlobalMemory.hunk_headers.append(h)

    # Slice payload EXACTLY to requested 'size', not padded 'aligned_size'
    payload_start = start + HEADER_SIZE
    payload_end = payload_start + size
    return memoryview(GlobalMemory.hunk_base)[payload_start:payload_end]


def Hunk_HighAllocName(size: int, name: str) -> memoryview | None:
    """C equivalent: Hunk_HighAllocName"""
    import common

    if size < 0:
        common.Sys_Error(f"Hunk_HighAllocName: bad size: {size}")

    if GlobalMemory.hunk_tempactive:
        Hunk_FreeToHighMark(GlobalMemory.hunk_tempmark)
        GlobalMemory.hunk_tempactive = False

    if PARANOID:
        Hunk_Check()

    HEADER_SIZE = 32
    aligned_size = HEADER_SIZE + ((size + 15) & ~15)

    free_space = GlobalMemory.hunk_size - GlobalMemory.hunk_low_used - GlobalMemory.hunk_high_used
    if free_space < aligned_size:
        common.Con_Printf(f"Hunk_HighAlloc: failed on {aligned_size} bytes\n")
        return None

    GlobalMemory.hunk_high_used += aligned_size
    Cache_FreeHigh(GlobalMemory.hunk_high_used)

    start_offset = GlobalMemory.hunk_size - GlobalMemory.hunk_high_used

    if GlobalMemory.hunk_base is not None:
        GlobalMemory.hunk_base[start_offset : start_offset + aligned_size] = b"\x00" * aligned_size

    h = hunk_t(sentinel=HUNK_SENTINEL, size=aligned_size, name=name)
    h.is_high = True
    h.offset = start_offset
    GlobalMemory.hunk_headers.append(h)

    # Slice payload EXACTLY to requested 'size', not padded 'aligned_size'
    payload_start = start_offset + HEADER_SIZE
    payload_end = payload_start + size
    return memoryview(GlobalMemory.hunk_base)[payload_start:payload_end]


def Hunk_TempAlloc(size: int) -> memoryview | None:
    """C equivalent: Hunk_TempAlloc"""
    # size = (size + 15) & ~15

    if GlobalMemory.hunk_tempactive:
        Hunk_FreeToHighMark(GlobalMemory.hunk_tempmark)
        GlobalMemory.hunk_tempactive = False

    GlobalMemory.hunk_tempmark = Hunk_HighMark()
    buf = Hunk_HighAllocName(size, "temp")
    GlobalMemory.hunk_tempactive = True
    return buf


def Hunk_Strdup(s: str, name: str) -> memoryview:
    """C equivalent: Hunk_Strdup"""
    s_bytes = s.encode("utf-8") + b"\x00"
    ptr = Hunk_AllocName(len(s_bytes), name)
    ptr[: len(s_bytes)] = s_bytes
    return ptr


# ==============================================================================
# CACHE MEMORY ALLOCATION
# ==============================================================================

def Cache_UnlinkLRU(cs: cache_system_t) -> None:
    """C equivalent: Cache_UnlinkLRU"""
    import common

    if cs.lru_next is None or cs.lru_prev is None:
        common.Sys_Error("Cache_UnlinkLRU: NULL link")

    cs.lru_next.lru_prev = cs.lru_prev
    cs.lru_prev.lru_next = cs.lru_next
    cs.lru_prev = None
    cs.lru_next = None


def Cache_MakeLRU(cs: cache_system_t) -> None:
    """C equivalent: Cache_MakeLRU"""
    import common

    if cs.lru_next is not None or cs.lru_prev is not None:
        common.Sys_Error("Cache_MakeLRU: active link")

    cache_head = GlobalMemory.cache_head
    if cache_head is None:
        return

    cache_head.lru_next.lru_prev = cs
    cs.lru_next = cache_head.lru_next
    cs.lru_prev = cache_head
    cache_head.lru_next = cs


def Cache_TryAlloc(size: int, nobottom: bool) -> cache_system_t | None:
    """C equivalent: Cache_TryAlloc"""
    import common

    cache_head = GlobalMemory.cache_head
    if cache_head is None:
        return None

    HEADER_SIZE = 32

    # 1. Empty cache pool
    if not nobottom and cache_head.prev == cache_head:
        free_space = GlobalMemory.hunk_size - GlobalMemory.hunk_high_used - GlobalMemory.hunk_low_used
        if free_space < size:
            common.Sys_Error(f"Cache_TryAlloc: {size} is greater then free hunk")

        new_cs = cache_system_t(size=size)
        new_cs.offset = GlobalMemory.hunk_low_used

        if GlobalMemory.hunk_base is not None:
            start = GlobalMemory.hunk_low_used
            GlobalMemory.hunk_base[start : start + size] = b"\x00" * size
            new_cs.data = memoryview(GlobalMemory.hunk_base)[start + HEADER_SIZE : start + size]

        cache_head.prev = new_cs
        cache_head.next = new_cs
        new_cs.prev = cache_head
        new_cs.next = cache_head

        Cache_MakeLRU(new_cs)
        return new_cs

    # 2. Search bottom-up gap
    new_offset = GlobalMemory.hunk_low_used
    cs = cache_head.next

    while True:
        if not nobottom or cs != cache_head.next:
            if (cs.offset - new_offset) >= size:
                new_cs = cache_system_t(size=size)
                new_cs.offset = new_offset

                if GlobalMemory.hunk_base is not None:
                    GlobalMemory.hunk_base[new_offset : new_offset + size] = b"\x00" * size
                    new_cs.data = memoryview(GlobalMemory.hunk_base)[new_offset + HEADER_SIZE : new_offset + size]

                new_cs.next = cs
                new_cs.prev = cs.prev
                cs.prev.next = new_cs
                cs.prev = new_cs

                Cache_MakeLRU(new_cs)
                return new_cs

        new_offset = cs.offset + cs.size
        cs = cs.next
        if cs == cache_head:
            break

    # 3. Allocation at the end
    high_hunk_start = GlobalMemory.hunk_size - GlobalMemory.hunk_high_used
    if (high_hunk_start - new_offset) >= size:
        new_cs = cache_system_t(size=size)
        new_cs.offset = new_offset

        if GlobalMemory.hunk_base is not None:
            GlobalMemory.hunk_base[new_offset : new_offset + size] = b"\x00" * size
            new_cs.data = memoryview(GlobalMemory.hunk_base)[new_offset + HEADER_SIZE : new_offset + size]

        new_cs.next = cache_head
        new_cs.prev = cache_head.prev
        cache_head.prev.next = new_cs
        cache_head.prev = new_cs

        Cache_MakeLRU(new_cs)
        return new_cs

    return None


def Cache_Free(c: cache_user_t, freetextures: bool = True) -> None:
    """C equivalent: Cache_Free"""
    import common

    if c is None or c.data is None:
        common.Sys_Error("Cache_Free: not allocated")

    cs = c._cache_sys
    if cs is None:
        cache_head = GlobalMemory.cache_head
        if cache_head is not None:
            curr = cache_head.next
            while curr != cache_head:
                if curr.user == c:
                    cs = curr
                    break
                curr = curr.next

    if cs is None:
        common.Sys_Error("Cache_Free: invalid cache user handle")

    cs.prev.next = cs.next
    cs.next.prev = cs.prev
    cs.next = cs.prev = None
    c.data = None
    c._cache_sys = None

    Cache_UnlinkLRU(cs)

    if freetextures and "TexMgr_FreeTexturesForOwner" in globals():
        globals()["TexMgr_FreeTexturesForOwner"](c)


def Cache_Check(c: cache_user_t) -> memoryview | None:
    """C equivalent: Cache_Check"""
    if c.data is None:
        return None

    cs = c._cache_sys
    if cs is not None:
        Cache_UnlinkLRU(cs)
        Cache_MakeLRU(cs)

    return c.data


def Cache_Alloc(c: cache_user_t, size: int, name: str) -> memoryview | None:
    """C equivalent: Cache_Alloc"""
    import common

    if c.data is not None:
        common.Sys_Error("Cache_Alloc: already allocated")

    if size <= 0:
        common.Sys_Error(f"Cache_Alloc: size {size}")

    HEADER_SIZE = 32
    aligned_size = (size + HEADER_SIZE + 15) & ~15

    cache_head = GlobalMemory.cache_head

    while True:
        cs = Cache_TryAlloc(aligned_size, False)
        if cs is not None:
            cs.name = name[:CACHENAME_LEN]
            c.data = cs.data
            cs.user = c
            c._cache_sys = cs
            break

        if cache_head is None or cache_head.lru_prev == cache_head or cache_head.lru_prev is None:
            common.Sys_Error("Cache_Alloc: out of memory")

        Cache_Free(cache_head.lru_prev.user, True)

    return Cache_Check(c)


def Cache_Move(c: cache_system_t) -> None:
    """C equivalent: Cache_Move"""
    new_cs = Cache_TryAlloc(c.size, True)

    if new_cs is not None:
        if c.data is not None and new_cs.data is not None:
            payload_size = min(len(c.data), len(new_cs.data))
            new_cs.data[:payload_size] = c.data[:payload_size]

        new_cs.user = c.user
        new_cs.name = c.name

        Cache_Free(c.user, False)

        if new_cs.user is not None:
            new_cs.user.data = new_cs.data
            new_cs.user._cache_sys = new_cs
    else:
        Cache_Free(c.user, True)


def Cache_FreeLow(new_low_hunk: int) -> None:
    """C equivalent: Cache_FreeLow"""
    cache_head = GlobalMemory.cache_head
    if cache_head is None:
        return

    while True:
        c = cache_head.next
        if c == cache_head:
            return

        if c.offset >= new_low_hunk:
            return

        Cache_Move(c)


def Cache_FreeHigh(new_high_hunk: int) -> None:
    """C equivalent: Cache_FreeHigh"""
    cache_head = GlobalMemory.cache_head
    if cache_head is None:
        return

    prev = None
    while True:
        c = cache_head.prev
        if c == cache_head:
            return

        if (c.offset + c.size) <= (GlobalMemory.hunk_size - new_high_hunk):
            return

        if c == prev:
            Cache_Free(c.user, True)
        else:
            Cache_Move(c)
            prev = c


def Cache_Flush() -> None:
    """C equivalent: Cache_Flush"""
    cache_head = GlobalMemory.cache_head
    if cache_head is None:
        return

    while cache_head.next != cache_head:
        Cache_Free(cache_head.next.user, True)


def Cache_Print() -> None:
    """C equivalent: Cache_Print"""
    import common

    cache_head = GlobalMemory.cache_head
    if cache_head is None:
        return

    cd = cache_head.next
    while cd != cache_head:
        common.Con_Printf(f"{cd.size:8d} : {cd.name}\n")
        cd = cd.next


def Cache_Report() -> None:
    """C equivalent: Cache_Report"""
    import common

    free_bytes = GlobalMemory.hunk_size - GlobalMemory.hunk_high_used - GlobalMemory.hunk_low_used
    megabytes = free_bytes / (1024.0 * 1024.0)
    common.Con_DPrintf(f"{megabytes:4.1f} megabyte data cache\n")


def Cache_Init() -> None:
    """C equivalent: Cache_Init"""
    import _cmd

    cache_head = cache_system_t(size=0, name="head")
    cache_head.next = cache_head
    cache_head.prev = cache_head
    cache_head.lru_next = cache_head
    cache_head.lru_prev = cache_head

    GlobalMemory.cache_head = cache_head
    _cmd.Cmd_AddCommand("flush", Cache_Flush)


def Memory_InitZone(zone_slice: memoryview, size: int) -> None:
    """C equivalent: Memory_InitZone"""
    global mainzone_manager
    mainzone_manager = ZoneManager(zone_slice, size)


def Memory_Init(buf: bytearray | memoryview, total_size: int) -> None:
    """C equivalent: Memory_Init"""
    import _cmd
    import common

    GlobalMemory.hunk_base = memoryview(buf) if not isinstance(buf, memoryview) else buf
    GlobalMemory.hunk_size = total_size
    GlobalMemory.hunk_low_used = 0
    GlobalMemory.hunk_high_used = 0
    GlobalMemory.hunk_headers = []

    Cache_Init()

    zonesize = DYNAMIC_SIZE
    p = common.COM_CheckParm("-zone")
    if p:
        if p < common.com_argc - 1:
            try:
                zonesize = int(common.com_argv[p + 1]) * 1024
            except ValueError:
                common.Sys_Error("Memory_Init: invalid -zone value")
        else:
            common.Sys_Error("Memory_Init: you must specify a size in KB after -zone")

    zone_buf = Hunk_AllocName(zonesize, "zone")
    Memory_InitZone(zone_buf, zonesize)

    _cmd.Cmd_AddCommand("hunk_print", Hunk_Print_f)













