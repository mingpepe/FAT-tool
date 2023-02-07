from helper import unpack


class Directory:
    ATTR_READ_ONLY = 0x01
    ATTR_HIDDEN = 0x02
    ATTR_SYSTEM = 0x04
    ATTR_VOLUME_ID = 0x08
    ATTR_DIRECTORY = 0x10
    ATTR_ARCHIVE = 0x20
    ATTR_LONG_FILE_NAME = 0x0f

    def __init__(self, data, sector_index, offset):
        self.sector_index = sector_index
        self.offset = offset
        self.name_bytes = unpack('=11s', data, 0)
        self.attr = unpack('=B', data, 11)
        self.is_read_only = self.attr & Directory.ATTR_READ_ONLY > 0
        self.is_hidden = self.attr & Directory.ATTR_HIDDEN > 0
        self.is_system = self.attr & Directory.ATTR_SYSTEM > 0
        self.is_vol_label = self.attr & Directory.ATTR_VOLUME_ID > 0
        self.is_dir = self.attr & Directory.ATTR_DIRECTORY > 0
        self.is_archive = self.attr & Directory.ATTR_ARCHIVE > 0
        self.is_long_filename = self.attr & Directory.ATTR_LONG_FILE_NAME > 0
        # Optional flags that indicates case information of the SFN.
        # 0x08: Every alphabet in the body is low-case.
        # 0x10: Every alphabet in the extensiton is low-case.
        self.nt_res = unpack('=B', data, 12)
        # Date bit fields
        # Bit 15-9: Count of years from 1980 in range of from 0 to 127 (1980-2107).
        # Bit 8-5: Month of year in range of from 1 to 12.
        # Bit 4-0: Day of month in range of from 1 to 31.

        # Time bit fields
        # Bit 15-11: Hours in range of from 0 to 23.
        # Bit 10-5: Minutes in range from 0 to 59.
        # Bit 4-0: 2 second count in range of form 0 to 29 (0-58 seconds).
        self.crt_time_tenth = unpack('=B', data, 13)
        self.crt_time = unpack('=H', data, 14)
        self.crt_date = unpack('=H', data, 16)
        self.last_access_date = unpack('=H', data, 18)
        self.fst_clus_hi = unpack('=H', data, 20)
        self.wrt_time = unpack('=H', data, 22)
        self.wrt_date = unpack('=H', data, 24)
        # Always zero if the file size is zero.
        self.fst_clus_lo = unpack('=H', data, 26)
        self.file_size = unpack('=L', data, 28)

        self.cluster = self.fst_clus_hi << 8 | self.fst_clus_lo
        self.not_used = self.name_bytes[0] == 0xe5 or self.name_bytes[0] == 0x00
        self.nothing_after = self.name_bytes[0] == 0x00

    def dump(self):
        if self.not_used:
            return

        print(
            f'[Directory] name : {self.name_bytes}, cluster = {self.cluster}, size = {self.file_size}, is archive = {self.is_archive}, is directory = {self.is_dir}')

    def get_name(self):
        if self.is_archive:
            name = self.name_bytes[0:8].decode('utf-8').strip().lower()
            ext = self.name_bytes[8:11].decode('utf-8').strip().lower()
            return name + '.' + ext
        else:
            return self.name_bytes.decode('utf-8').strip().lower()
