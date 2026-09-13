#screen.py 

from enum import Enum


class canvastype(Enum):
    CANVAS_NONE         = 0       
    CANVAS_DEFAULT      = 1    
    CANVAS_CONSOLE      = 2    
    CANVAS_MENU         = 3       
    CANVAS_SBAR         = 4       
    CANVAS_WARPIMAGE    = 5  
    CANVAS_CROSSHAIR    = 6  
    CANVAS_BOTTOMLEFT   = 7 
    CANVAS_BOTTOMRIGHT  = 8
    CANVAS_TOPRIGHT     = 9   
    CANVAS_INVALID      = -1


