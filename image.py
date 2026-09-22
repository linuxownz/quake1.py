#image.py

import io
import struct

from PIL import Image

import common
import sys_sdl_unix


class targaheader_t:
    def __init__(self):
        self.id_length = 0
        self.colormap_type = 0
        self.image_type = 0
        self.colormap_index = 0
        self.colormap_size = 0
        self.x_origin = 0
        self.y_origin = 0
        self.width = 0
        self.height = 0
        self.pixel_size = 0
        self.attributes = 0

TARGAHEADERSIZE = 18

class pcxheader_t:

    def __init__(self) -> None:
        self.signature: int = 0
        self.version: int = 0
        self.encoding: int = 0
        self.bits_per_pixel: int = 0
        self.xmin: int = 0
        self.ymin: int = 0
        self.xmax: int = 0
        self.ymax: int = 0
        self.hdpi: int = 0
        self.vdpi: int = 0
        self.colortable: bytes = b"\x00" * 48
        self.reserved: int = 0
        self.color_planes: int = 0
        self.bytes_per_line: int = 0
        self.palette_type: int = 0
        self.filler: bytes = b"\x00" * 58


loadfilename = ''


def fgetLittleShort(f: io.BufferedIOBase) -> int:
    """Reads a 2-byte signed little-endian short from a binary file stream.

    C equivalent (common.c):
    short fgetLittleShort (FILE *f)
    """
    data = f.read(2)
    if len(data) < 2:
        return 0  # EOF or truncated read parity

    # '<h' -> Little-endian ('<'), Signed 16-bit short ('h')
    return struct.unpack("<h", data)[0]

def fgetLittleLong(f: io.BufferedIOBase) -> int:
    """Reads a 4-byte signed little-endian integer from a binary file.

    C equivalent (common.c):
    int fgetLittleLong (FILE *f)
    """
    data = f.read(4)
    if len(data) < 4:
        return 0  # Truncated read / EOF parity

    # '<i' -> Little-endian ('<'), Signed 32-bit int ('i')
    return struct.unpack("<i", data)[0]

def Image_LoadImage(name: str, width: int, height: int) -> bytes:
    f: io.FileIO = common.COM_FOpenFile(f'{name}.tga')
    if f:
        return Image_LoadTGA(f, width, height)
    f = common.COM_FOpenFile(f'{name}.pcx')
    if f:
        return Image_LoadPCX(f, width, height)
    return None


def Image_WriteTGA(name:str, data: bytes, width: int, height: int, bpp: int, upsidedown:bool) -> bool:
    sys_sdl_unix.Sys_mkdir(common.com_gamedir)

    pathname = f'{common.com_gamedir}/{name}'

    handle = sys_sdl_unix.Sys_FileOpenWrite(pathname)

    if not handle:
        return False

    header: bytearray = bytearray(TARGAHEADERSIZE)
    header[2] = 2
    header[12] = width&255
    header[13] = width>>8
    header[14] = height&255
    header[15] = height>>8
    header[16] = bpp
    if upsidedown:
        header[17] = 0x20

    _bytes = bpp // 8
    size = width * height * _bytes

    data = bytearray(data[:size])
    for i in range(0, size, _bytes):
        data[i], data[i + 2] = data[i + 2], data[i]

    sys_sdl_unix.Sys_FileWrite(handle, header)
    sys_sdl_unix.Sys_FileWrite(handle, data)
    sys_sdl_unix.Sys_FileClose(handle)


def Image_LoadTGA(fin: io.BufferedIOBase, width: int, height: int) -> bytes:
    """Reads an uncompressed TGA image from a binary stream for known dimensions.

    C equivalent (gl_draw.c / image.c):
    byte *LoadTGA (FILE *fin, int width, int height)
    """
    header_data = fin.read(TARGAHEADERSIZE)
    if len(header_data) < TARGAHEADERSIZE:
        return b""

    # Unpack 18-byte TGA Header (Little-Endian)
    unpacked = struct.unpack("<BBBHHBHHBB", header_data)

    id_length = unpacked[0]
    colormap_type = unpacked[1]
    image_type = unpacked[2]
    colormap_length = unpacked[4]
    colormap_size = unpacked[5]
    tga_width = unpacked[8]
    tga_height = unpacked[9]
    pixel_size = unpacked[10]
    attributes = unpacked[11]

    # Validate image type: 2 = uncompressed true-color, 3 = uncompressed grayscale
    if image_type not in (2, 3):
        return b""

    # Skip image ID field if present
    if id_length > 0:
        fin.read(id_length)

    # Skip color map if present
    if colormap_type != 0:
        colormap_bytes = (colormap_length * colormap_size) // 8
        fin.read(colormap_bytes)

    bpp = pixel_size
    if bpp not in (8, 24, 32):
        return b""

    bytes_per_pixel = bpp // 8
    image_size = width * height * bytes_per_pixel

    raw_pixels = fin.read(image_size)
    if len(raw_pixels) < image_size:
        return b""

    pixels = bytearray(raw_pixels)

    # Convert BGR(A) -> RGB(A) by swapping Red and Blue channels for 24-bit and 32-bit images
    if bytes_per_pixel >= 3:
        for i in range(0, image_size, bytes_per_pixel):
            pixels[i], pixels[i + 2] = pixels[i + 2], pixels[i]

    # Handle vertical flip if bit 5 (0x20) is NOT set (bottom-up image origin)
    top_to_bottom = bool(attributes & 0x20)
    if not top_to_bottom:
        row_size = width * bytes_per_pixel
        flipped = bytearray(image_size)
        for y in range(height):
            src_offset = y * row_size
            dst_offset = (height - 1 - y) * row_size
            flipped[dst_offset : dst_offset + row_size] = pixels[
                src_offset : src_offset + row_size
            ]
        pixels = flipped

    return bytes(pixels)

PCX_HEADER_SIZE: int = 128

def Image_LoadPCX(
    f: io.BufferedIOBase,
    loadfilename: str,
    width: int = 0,
    height: int = 0,
) -> tuple[bytearray, int, int]:
    # 1. Save start position BEFORE reading header
    start = f.tell()

    header_data = f.read(PCX_HEADER_SIZE)
    if len(header_data) < PCX_HEADER_SIZE:
        sys_sdl_unix.Sys_Error(f"Failed to read header from {loadfilename}")

    # 2. Unpack header fields
    pcx = pcxheader_t()
    pcx.signature = header_data[0]
    pcx.version = header_data[1]
    pcx.encoding = header_data[2]
    pcx.bits_per_pixel = header_data[3]
    pcx.xmin = header_data[4] | (header_data[5] << 8)
    pcx.ymin = header_data[6] | (header_data[7] << 8)
    pcx.xmax = header_data[8] | (header_data[9] << 8)
    pcx.ymax = header_data[10] | (header_data[11] << 8)
    pcx.hdpi = header_data[12] | (header_data[13] << 8)
    pcx.vdpi = header_data[14] | (header_data[15] << 8)
    pcx.colortable = header_data[16:64]
    pcx.reserved = header_data[64]
    pcx.color_planes = header_data[65]
    pcx.bytes_per_line = header_data[66] | (header_data[67] << 8)
    pcx.palette_type = header_data[68] | (header_data[69] << 8)
    pcx.filler = header_data[70:128]

    # 3. Validate header attributes
    if pcx.signature != 0x0A:
        sys_sdl_unix.Sys_Error(f"'{loadfilename}' is not a valid PCX file")

    if pcx.version != 5:
        sys_sdl_unix.Sys_Error(
            f"'{loadfilename}' is version {pcx.version}, should be 5"
        )

    if (
        pcx.encoding != 1
        or pcx.bits_per_pixel != 8
        or pcx.color_planes != 1
    ):
        sys_sdl_unix.Sys_Error(
            f"'{loadfilename}' has wrong encoding or bit depth"
        )

    w = pcx.xmax - pcx.xmin + 1
    h = pcx.ymax - pcx.ymin + 1

    # 4. Pre-allocate output RGBA pixel buffer
    data = bytearray((w * h + 1) * 4)

    # 5. Load 768-byte palette from end of file
    f.seek(start + common.com_filesize - 768, io.SEEK_SET)
    palette = f.read(768)
    if len(palette) < 768:
        sys_sdl_unix.Sys_Error(f"Failed reading palette from '{loadfilename}'")

    # 6. Seek to start of RLE compressed image scanlines (after 128-byte header)
    f.seek(start + PCX_HEADER_SIZE, io.SEEK_SET)

    # 7. Decode PCX RLE scanlines into RGBA data
    for y in range(h):
        p = y * w * 4  # Integer index offset into RGBA buffer
        x = 0

        while x < pcx.bytes_per_line:
            b = f.read(1)
            if not b:
                break
            readbyte = b[0]

            if readbyte >= 0xC0:
                runlength = readbyte & 0x3F
                b2 = f.read(1)
                readbyte = b2[0] if b2 else 0
            else:
                runlength = 1

            while runlength > 0:
                if x < w:
                    pal_idx = readbyte * 3
                    data[p] = palette[pal_idx]  # R
                    data[p + 1] = palette[pal_idx + 1]  # G
                    data[p + 2] = palette[pal_idx + 2]  # B
                    data[p + 3] = 255  # A
                    p += 4
                x += 1
                runlength -= 1

    return data, w, h


def Image_WriteJPG( name: str, data: bytes, width: int, height: int, bpp: int, quality: int, upsidedown: bool) -> bool:
    """Writes a raw RGB/RGBA byte buffer to a JPEG file.
    C equivalent (image.c / gl_draw.c):
    qboolean Image_WriteJPG (const char *name, byte *data, int width, int height, int bpp, int quality, qboolean upsidedown)
    """
    sys_sdl_unix.Sys_mkdir(common.com_gamedir)

    pathname = f"{common.com_gamedir}/{name}"
    handle = sys_sdl_unix.Sys_FileOpenWrite(pathname)

    if not handle:
        return False

    bytes_per_pixel = bpp // 8
    image_size = width * height * bytes_per_pixel

    buffer = bytearray(data[:image_size])

    # 1. Image Mode & Color Swapping (Convert BGR(A) to RGB(A) if necessary)
    mode = "RGBA" if bytes_per_pixel == 4 else "RGB"
    if bytes_per_pixel >= 3:
        for i in range(0, image_size, bytes_per_pixel):
            buffer[i], buffer[i + 2] = buffer[i + 2], buffer[i]

    # 2. Construct PIL Image from raw byte stream
    img = Image.frombytes(mode, (width, height), bytes(buffer))

    # JPEG does not support an alpha channel; flatten to RGB
    if mode == "RGBA":
        img = img.convert("RGB")

    # 3. Handle Vertical Flip
    # Quake framebuffers are stored bottom-to-top; if upsidedown is True, flip vertically
    if upsidedown:
        img = img.transpose(Image.FLIP_TOP_BOTTOM)

    # 4. Save JPEG directly into the engine's file handle
    try:
        img.save(handle, format="JPEG", quality=quality)
        sys_sdl_unix.Sys_FileClose(handle)
        return True
    except Exception:
        sys_sdl_unix.Sys_FileClose(handle)
        return False




def Image_LoadJPG(f: io.BufferedIOBase) -> tuple[bytearray, int, int]:
    """Decodes a JPG stream into a raw 32-bit RGBA bytearray to match Quake's Image_Load* interface."""
    try:
        # Open stream with PIL without loading full image into memory yet
        with Image.open(f) as img:
            img = img.convert("RGBA")
            width, height = img.size

            # Extract raw RGBA bytes into a mutable bytearray
            raw_data = bytearray(img.tobytes())

            return raw_data, width, height
    except Exception:
        return bytearray(), 0, 0