#zone_tester.py 

import zone

if __name__ == "__main__":
    # 1. Setup a dummy 8MB buffer
    raw_mem = bytearray(8 * 1024 * 1024)
    zone.Memory_Init(raw_mem, len(raw_mem))
    
    # 2. Allocate two blocks
    p1 = zone.Z_Malloc(1024)
    p2 = zone.Z_Malloc(1024)
    print(f"Allocated two 1KB blocks. Rover moved.")

    # 3. Free them
    zone.Z_Free(p1)
    zone.Z_Free(p2)
    print(f"Freed blocks. If coalesce worked, we should have one large free block again.")
    
    # Check the first block's size (should be roughly 4MB minus whatever Hunk used)
    first_b = zone.mainzone_manager.blocklist.next
    print(f"Main free block size: {first_b.size} bytes")