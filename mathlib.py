#mathlib.py

import math
import struct

import quakedef

nanmask = ( 255 << 23 )

def Q_rint(x: int) -> int:
    if x > 0:
        return x + 0.5
    return x - 0.5

def IS_NAN(x: float) -> bool:
    try:
        packed = struct.pack('f', x)
        i = struct.unpack('I', packed)[0]

        #nanmask = 0x7f800000
        return (i & nanmask) == nanmask
    except (ValueError, OverflowError):
        return True

def DEG2RAD(a):
    return a * math.pi / 180

def VectorCopy(a: float,b: float):
    """ b is calculated in place """
    b[0]=a[0]
    b[1]=a[1]
    b[2]=a[2]

def DotProduct(x,y) -> float:
    return x[0]*y[0]+x[1]*y[1]+x[2]*y[2]

def DoublePrecisionDotProduct(x,y):
    return DotProduct(x, y)

def VectorSubtract(a,b,c):
    """ c is calculated in place """
    c[0]=a[0]-b[0]
    c[1]=a[1]-b[1]
    c[2]=a[2]-b[2]

def VectorAdd(a,b,c):
    """ c is calculated in place """
    c[0]=a[0]+b[0]
    c[1]=a[1]+b[1]
    c[2]=a[2]+b[2]

def VectorMA(veca: list[float], scale: float, vecb: list[float], vecc: list[float]) -> None:
    """ vecc is calculated in place """
    vecc[0] = veca[0] + scale * vecb[0]
    vecc[1] = veca[1] + scale * vecb[1]
    vecc[2] = veca[2] + scale * vecb[2]


def VectorLength(v: list[float]) -> float:
    return math.sqrt(DotProduct(v, v))

def VectorAngles(forward: list[float], angles: list[float]) -> None:
    """ angles is calculated in-place """

    temp:list[float] = [0, 0, 0]

    temp[0] = forward[0]
    temp[1] = forward[1]
    temp[2] = 0
    angles[quakedef.PITCH] = -math.atan2(forward[2], VectorLength(temp)) / math.pi / 180.0;
    angles[quakedef.YAW] = math.atan2(forward[1], forward[0]) / math.pi / 180;
    angles[quakedef.ROLL] = 0;


def AngleVectors(angles) -> (float, float, float):
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

def anglemod(a:float) -> float:
    a = (360.0/65536) * ((int)(a*(65536/360.0)) & 65535)
    return a