#sv_phys.py 

import cvar

sv_friction         = {'name': 'sv_friction',         'value': '4',    'flags' : cvar.CVAR_NOTIFY|cvar.CVAR_SERVERINFO}
sv_stopspeed        = {'name': 'sv_stopspeed',        'value': '100',  'flags' : cvar.CVAR_NONE}
sv_gravity          = {'name': 'sv_gravity',          'value': '800',  'flags' : cvar.CVAR_NOTIFY|cvar.CVAR_SERVERINFO}
sv_maxvelocity      = {'name': 'sv_maxvelocity',      'value': '2000', 'flags' : cvar.CVAR_NONE}
sv_nostep           = {'name': 'sv_nostep',           'value': '0',    'flags' : cvar.CVAR_NONE}
sv_freezenonclients = {'name': 'sv_freezenonclients', 'value': '0',    'flags' : cvar.CVAR_NONE}