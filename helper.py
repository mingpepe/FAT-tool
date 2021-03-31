import os
import time
import struct

SECTOR_SIZE = 512

def unpack(format, data, offset):
    return struct.unpack_from(format, data, offset)[0]

def read_sector(path, index):
    return read_sectors(path, index, 1)

def read_sectors(path, index, count):
    with open(path, 'rb') as f:
        f.seek(index * SECTOR_SIZE)
        return f.read(count * SECTOR_SIZE)

def write_sector(path, index, data):
    write_sectors(path, index, data, 1)

def write_sectors(path, index, data, count):
    if len(data) != count * SECTOR_SIZE:
        raise BufferError()

    # We can not write sectors for FAT and data regions
    # The workaround is to clear boot sector and write 
    # it back after write the target sections
    with open(path, 'rb+') as f:
        bs = f.read(SECTOR_SIZE)
        zeros = bytearray(SECTOR_SIZE)
        f.seek(0)
        f.write(zeros)

    with open(path, 'rb+') as f:
        f.seek(index * SECTOR_SIZE)
        f.write(data)

    with open(path, 'rb+') as f:
        f.write(bs)