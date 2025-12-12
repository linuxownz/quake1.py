#chase.py 

import cvar

chase_back   = {'name':"chase_back",  'value':"100", 'flags':cvar.CVAR_NONE};
chase_up     = {'name':"chase_up",    'value': "16", 'flags':cvar.CVAR_NONE};
chase_right  = {'name':"chase_right", 'value': "0",  'flags':cvar.CVAR_NONE};
chase_active = {'name':"chase_active",'value': "0",  'flags':cvar.CVAR_NONE};

def Chase_Init():
    global chase_back
    global chase_up
    global chase_right
    global chase_active

    cvar.Cvar_RegisterVariable(chase_back)
    cvar.Cvar_RegisterVariable(chase_up)
    cvar.Cvar_RegisterVariable(chase_right)
    cvar.Cvar_RegisterVariable(chase_active)

