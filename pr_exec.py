#pr_exec.py 

import console
import sv_main


def PR_Profile_f():
    if not sv_main.sv.active:
        return

    pmax = 0
    num = 0
    best = None

    while True:
        for i in range(progs.numfunctions):
            f = pr_functions[i]
            if f.profile > pmax:
                pmax = f.profile
                best = f
        
        if best:
            if num < 10:
                console.Con_Printf(f'{best.profile} {PR_GetString(best.name)}\n')
            
            num += 1
            best.profile = 0

        if not best:
            break
