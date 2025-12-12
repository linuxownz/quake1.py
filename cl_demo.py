#cl_demo.py 

import cl_main
import _cmd
import net_main


def CL_StopPlayback():
    if not cl_main.cls.demoplayback:
        return

    cl_main.cls.demoplayback.close()
    cl_main.cls.demoplayback = False
    cl_main.cls.demopaused = False
    cl_main.cls.demofile = None
    cl_main.cls.state = cactive_t.ca_disconnected

    if cl_main.cls.timedemo:
        CL_FinishTimeDemo()

def CL_Stop_f():
    if cmd.cmd_source != cmd.cmd_source_t.src_command:
        return
    
    if not cl_main.cls.demorecording:
        Con_Printf('not recording a demo')
        return

    SZ_Clear(net_main.net_message)
    MSG_WriteByte( net_main.net_message, svc_disconnect)
    CL_WriteDemoMessage()

    cl_main.cls.demofile.close()
    cl_main.cls.demofile = None
    cl_main.cls.demorecording = False
    Con_Printf('Completed demo\n')

    DemoList_Rebuild()

    
    


