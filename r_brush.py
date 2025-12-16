#r_brush.py 

import glquake

gl_lightmap_format = 0
lightmap_bytes = 0

MAX_SANITY_LIGHTMAPS = ( 1 << 20 )
lightmaps : glquake.lightmap_s = None
lightmap_count = 0

allocated = [0 for i in range(glquake.LMBLOCK_WIDTH)]
last_lightmap_allocated = 0

blocklights = [ 0 for _ in range(glquake.LMBLOCK_WIDTH*glquake.LMBLOCK_HEIGHT*3)]

