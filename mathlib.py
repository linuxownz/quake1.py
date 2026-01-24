#mathlib.py

import math

import quakedef

def DEG2RAD(a):
    return a * math.pi / 180

def VectorCopy(a,b):
    b[0]=a[0]
    b[1]=a[1]
    b[2]=a[2]

def DotProduct(x,y):
    return x[0]*y[0]+x[1]*y[1]+x[2]*y[2]

def DoublePrecisionDotProduct(x,y):
    return DotProduct(x, y)

def VectorSubtract(a,b,c):
    c[0]=a[0]-b[0]
    c[1]=a[1]-b[1]
    c[2]=a[2]-b[2]

def VectorAdd(a,b,c):
    c[0]=a[0]+b[0]
    c[1]=a[1]+b[1]
    c[2]=a[2]+b[2]

def AngleVectors(angles):
    """ Converts angles [pitch, yaw, roll] to three vectors.  """
    angle_to_rad = math.pi / 180.0

    sy = math.sin(angles[quakedef.YAW] * angle_to_rad)
    cy = math.cos(angles[quakedef.YAW] * angle_to_rad)
    sp = math.sin(angles[quakedef.PITCH] * angle_to_rad)
    cp = math.cos(angles[quakedef.PITCH] * angle_to_rad)
    sr = math.sin(angles[quakedef.ROLL] * angle_to_rad)
    cr = math.cos(angles[quakedef.ROLL] * angle_to_rad)

    forward = [
        cp * cy,
        cp * sy,
        -sp
    ]

    right = [
        (-1*sr*sp*cy + -1*cr*-sy),
        (-1*sr*sp*sy + -1*cr*cy),
        -1*sr*cp
    ]

    up = [
        (cr*sp*cy + -sr*-sy),
        (cr*sp*sy + -sr*cy),
        cr*cp
    ]

    return forward, right, up