#mathlib.py

import math
import struct

import quakedef
import sys_sdl_unix

FLT_MAX = 3.402823466e+38

vec3_origin: list[float] = [0, 0, 0]

nanmask = ( 255 << 23 )

def ProjectPointOnPlane(dst: quakedef.vec3_t, p: quakedef.vec3_t, normal: quakedef.vec3_t):
    n: quakedef.vec3_t = [0., 0., 0.]

    inv_denom = 1.0 / DotProduct(normal, normal)
    d = DotProduct(normal, p) * inv_denom

    n[0] = normal[0] * inv_denom
    n[1] = normal[1] * inv_denom
    n[2] = normal[2] * inv_denom

    dst[0] = p[0] - d * n[0]
    dst[1] = p[1] - d * n[1]
    dst[2] = p[2] - d * n[2]

def PerpendicularVector(dst: quakedef.vec3_t, src: quakedef.vec3_t):
    tempvec: quakedef.vec3_t = [0., 0., 0.]
    minelem = 1.0

    pos = 0
    for i in range(3):
        if math.fabs(src[i]) < minelem:
            pos = i
            minelem = math.fabs(src[i])

    tempvec[pos] = 1.0

    ProjectPointOnPlane(dst, tempvec, src)
    VectorNormalize(dst)

def BoxOnPlaneSide(emins: quakedef.vec3_t, emaxs: quakedef.vec3_t, p: quakedef.mplane_t) -> int:
    xneg = p.signbits & 1
    yneg = (p.signbits >> 1) & 1
    zneg = (p.signbits >> 2) & 1

    dist1 = p.normal[0] * (emins if xneg else emaxs)[0] + p.normal[1] * (emins if yneg else emaxs)[1] + p.normal[2] * (emins if zneg else emaxs)[2];
    dist2 = p.normal[0] * (emaxs if xneg else emins)[0] + p.normal[1] * (emaxs if yneg else emins)[1] + p.normal[2] * (emaxs if zneg else emins)[2];

    if p.signbits & ~7:
        sys_sdl_unix.Sys_Error('BoxOnPlaneSide: Bad signbits')

    sides = 0
    if dist1 >= p.dist:
        sides = 1
    if dist2 < p.dist:
        sides |= 2

    if sides == 0:
        sys_sdl_unix.Sys_Error('BoxOnPlaneSide: sides == 0')

    return sides


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

def VectorCopy(a: list[float],b: list[float]):
    b[0]=a[0]
    b[1]=a[1]
    b[2]=a[2]

def DotProduct(x,y) -> float:
    return x[0]*y[0]+x[1]*y[1]+x[2]*y[2]

def DoublePrecisionDotProduct(x,y):
    return DotProduct(x, y)

def VectorSubtract(a:list[float], b:list[float], c:list[float]):
    """ c is calculated in place """
    c[0]=a[0]-b[0]
    c[1]=a[1]-b[1]
    c[2]=a[2]-b[2]

def VectorAdd(a:list[float], b:list[float], c:list[float]):
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


def VectorNormalize(v: list[float]) -> float:
    length = math.sqrt(DotProduct(v, v))

    if length:
        ilength = 1/length
        v[0] *= ilength
        v[1] *= ilength
        v[2] *= ilength

    return length

def VectorAngles(forward: list[float], angles: list[float]) -> None:
    """ angles is calculated in-place """

    temp:list[float] = [0, 0, 0]

    temp[0] = forward[0]
    temp[1] = forward[1]
    temp[2] = 0
    angles[quakedef.PITCH] = -math.atan2(forward[2], VectorLength(temp)) / math.pi / 180.0;
    angles[quakedef.YAW] = math.atan2(forward[1], forward[0]) / math.pi / 180;
    angles[quakedef.ROLL] = 0;

def AngleVectors( angles: list[float], forward: list[float], right: list[float], up: list[float]) -> None:
    """Converts angles [pitch, yaw, roll] to three vectors in-place."""
    angle_to_rad = math.pi / 180.0

    sy = math.sin(angles[quakedef.YAW] * angle_to_rad)
    cy = math.cos(angles[quakedef.YAW] * angle_to_rad)
    sp = math.sin(angles[quakedef.PITCH] * angle_to_rad)
    cp = math.cos(angles[quakedef.PITCH] * angle_to_rad)
    sr = math.sin(angles[quakedef.ROLL] * angle_to_rad)
    cr = math.cos(angles[quakedef.ROLL] * angle_to_rad)

    if forward:
        forward[0] = cp * cy
        forward[1] = cp * sy
        forward[2] = -sp

    if right:
        right[0] = (-1.0 * sr * sp * cy) + (-1.0 * cr * -sy)
        right[1] = (-1.0 * sr * sp * sy) + (-1.0 * cr * cy)
        right[2] = -1.0 * sr * cp

    if up:
        up[0] = (cr * sp * cy) + (-sr * -sy)
        up[1] = (cr * sp * sy) + (-sr * cy)
        up[2] = cr * cp


def anglemod(a:float) -> float:
    a = (360.0/65536) * ((int)(a*(65536/360.0)) & 65535)
    return a

def VectorCompare(v1: quakedef.vec3_t, v2: quakedef.vec3_t) -> int:
    for i in range(3):
        if v1[i] != v2[i]:
            return 0
    return 1

def CrossProduct(v1: quakedef.vec3_t, v2: quakedef.vec3_t, cross: quakedef.vec3_t):
    cross[0] = v1[1]*v2[2] - v1[2]*v2[1]
    cross[1] = v1[2]*v2[0] - v1[0]*v2[2]
    cross[2] = v1[0]*v2[1] - v1[1]*v2[0]

def VectorInverse(v: quakedef.vec3_t):
    v[0] = -v[0]
    v[1] = -v[1]
    v[2] = -v[2]

def VectorScale(_in: quakedef.vec3_t, scale: quakedef.vec3_t, out: quakedef.vec3_t):
    out[0] = _in[0]*scale
    out[1] = _in[1]*scale
    out[2] = _in[2]*scale

def Q_log2(val: int):
    return math.log2(val)

def R_ConcatRotations(in1: list[float], in2: list[float], out: list[float]):
    out[0][0] = in1[0][0] * in2[0][0] + in1[0][1] * in2[1][0] + in1[0][2] * in2[2][0]
    out[0][1] = in1[0][0] * in2[0][1] + in1[0][1] * in2[1][1] + in1[0][2] * in2[2][1]
    out[0][2] = in1[0][0] * in2[0][2] + in1[0][1] * in2[1][2] + in1[0][2] * in2[2][2]
    out[1][0] = in1[1][0] * in2[0][0] + in1[1][1] * in2[1][0] + in1[1][2] * in2[2][0]
    out[1][1] = in1[1][0] * in2[0][1] + in1[1][1] * in2[1][1] + in1[1][2] * in2[2][1]
    out[1][2] = in1[1][0] * in2[0][2] + in1[1][1] * in2[1][2] + in1[1][2] * in2[2][2]
    out[2][0] = in1[2][0] * in2[0][0] + in1[2][1] * in2[1][0] + in1[2][2] * in2[2][0]
    out[2][1] = in1[2][0] * in2[0][1] + in1[2][1] * in2[1][1] + in1[2][2] * in2[2][1]
    out[2][2] = in1[2][0] * in2[0][2] + in1[2][1] * in2[1][2] + in1[2][2] * in2[2][2]


def R_ConcatTransforms(in1: list[float], in2:list[float], out:list[float]):
    out[0][0] = in1[0][0] * in2[0][0] + in1[0][1] * in2[1][0] + in1[0][2] * in2[2][0]
    out[0][1] = in1[0][0] * in2[0][1] + in1[0][1] * in2[1][1] + in1[0][2] * in2[2][1]
    out[0][2] = in1[0][0] * in2[0][2] + in1[0][1] * in2[1][2] + in1[0][2] * in2[2][2]
    out[0][3] = in1[0][0] * in2[0][3] + in1[0][1] * in2[1][3] + in1[0][2] * in2[2][3] + in1[0][3]
    out[1][0] = in1[1][0] * in2[0][0] + in1[1][1] * in2[1][0] + in1[1][2] * in2[2][0]
    out[1][1] = in1[1][0] * in2[0][1] + in1[1][1] * in2[1][1] + in1[1][2] * in2[2][1]
    out[1][2] = in1[1][0] * in2[0][2] + in1[1][1] * in2[1][2] + in1[1][2] * in2[2][2]
    out[1][3] = in1[1][0] * in2[0][3] + in1[1][1] * in2[1][3] + in1[1][2] * in2[2][3] + in1[1][3]
    out[2][0] = in1[2][0] * in2[0][0] + in1[2][1] * in2[1][0] + in1[2][2] * in2[2][0]
    out[2][1] = in1[2][0] * in2[0][1] + in1[2][1] * in2[1][1] + in1[2][2] * in2[2][1]
    out[2][2] = in1[2][0] * in2[0][2] + in1[2][1] * in2[1][2] + in1[2][2] * in2[2][2]
    out[2][3] = in1[2][0] * in2[0][3] + in1[2][1] * in2[1][3] + in1[2][2] * in2[2][3] + in1[2][3]

def FloorDivMod(numer: float, denom: float, quotient: int, rem: int) -> tuple[int, int]:
    if denom <= 0.0:
        sys_sdl_unix.Sys_Error(f'FloorDivMod: bad denominator {denom}')

    if numer >= 0.0:
        x = math.floor(numer/denom)
        q = int(x)
        r = math.floor(numer - ( x * denom))
    else:
        x = math.floor(-numer / denom)
        q = -int(x)
        r = math.floor(-numer - ( x * denom))

        if r != 0:
            q -= 1
            r = int(denom) - r

    quotient = q
    rem = r

    return quotient, rem


def GreatestCommonDivisor(i1: int, i2: int) -> int:
    if i1 > i2:
        if i2 == 0:
            return i1
        return GreatestCommonDivisor(i2, i1 % i2)
    else:
        if i1 == 0:
            return i2
        return GreatestCommonDivisor(i1, i2 % i1)

def Invert24To16(val: int) -> int:
    """Calculates reciprocal value in 16.16 fixed-point format for 24-bit depth values.

    C equivalent (d_edge.c):
    fixed16_t Invert24To16(fixed16_t val)
    """
    # Force 32-bit unsigned interpretation for the comparison check
    val_u = val & 0xFFFFFFFF

    if val_u < 256:
        # Returns -1 (0xFFFFFFFF in 32-bit signed two's complement)
        return -1

    # Floating-point division and +0.5 rounding matching C double cast
    result = int(((65536.0 * 16777216.0) / float(val_u)) + 0.5)

    # Convert unsigned uint32 result back to 32-bit signed integer
    result &= 0xFFFFFFFF
    return result if result < 0x80000000 else result - 0x100000000
