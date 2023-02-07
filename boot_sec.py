from helper import unpack


class BootSecor:
    BOOT_SECTOR_SIZE = 512

    def __init__(self, data):
        self.jump = unpack('=ccc', data, 0)
        self.oem_name = unpack('=8s', data, 3)
        self.bytes_per_sec = unpack('=H', data, 11)
        self.sec_per_cluster = unpack('=B', data, 13)
        self.reserved_sec_count = unpack('=H', data, 14)
        # Should always be 2
        self.num_of_FAT = unpack('=B', data, 16)
        # For FAT32 volumes, this field must always be 0.
        self.root_ent_count = unpack('=H', data, 17)
        # For FAT32 volumes, this field must always be 0.
        self.total_sec_16 = unpack('=H', data, 19)
        # This comes from the media determination of MS-DOS Ver.1 and not used for any purpose any longer.
        self.media = unpack('=B', data, 21)
        # On the FAT32 volumes, it must be an invalid value 0
        self.FAT_size_16 = unpack('=H', data, 22)
        # This field is relevant only for media that have geometry and used for only disk BIOS of IBM PC.
        self.sec_per_track = unpack('=H', data, 24)
        # This field is relevant only for media that have geometry and used for only disk BIOS of IBM PC.
        self.num_of_header = unpack('=H', data, 26)
        self.hidden_sec = unpack('=L', data, 28)
        self.total_sec_32 = unpack('=L', data, 32)
        # The fields in the first 36 bytes are common field for all FAT types
        # and the fields from byte offset 36 depends on whether the FAT type is FAT32 or FAT12/FAT16.
        self.FAT_size_32 = unpack('=L', data, 36)
        self.ext_flag = unpack('=H', data, 40)
        self.fs_version = unpack('=H', data, 42)
        self.root_cluster = unpack('=L', data, 44)
        self.fs_info = unpack('=H', data, 48)
        self.bk_boot_sec = unpack('=H', data, 50)
        # 12 bytes reserved
        self.drive_num = unpack('=B', data, 64)
        # 1 byte reseved
        self.boot_sig = unpack('=B', data, 66)
        self.vol_id = unpack('=L', data, 67)
        self.vol_lab = unpack('=11s', data, 71)
        self.fs_type = unpack('=8s', data, 82)
        # 420 bytes reserved
        self.bs_sig = unpack('=H', data, 510)  # 0x55aa

        # Calculated paramter
        self.FAT_start_sec = self.reserved_sec_count
        self.FAT_sec_count = self.FAT_size_32 * self.num_of_FAT

        self.root_dir_start_sec = self.FAT_start_sec + self.FAT_sec_count
        self.root_dir_sec_count = round(
            (32 * self.root_ent_count + self.bytes_per_sec - 1) / self.bytes_per_sec)

        self.data_start_sec = self.root_dir_start_sec + self.root_dir_sec_count
        self.data_sec_count = self.total_sec_32 - self.data_start_sec

    def dump(self):
        print('[Boot sector]')
        print(f'jump : {self.jump}')
        print(f'oem_name : {self.oem_name}')
        print(f'bytes_per_sec : {self.bytes_per_sec}')
        print(f'sec_per_cluster : {self.sec_per_cluster}')
        print(f'reserved_sec_count : {self.reserved_sec_count}')
        print(f'num_of_FAT : {self.num_of_FAT}')
        print(f'root_ent_count : {self.root_ent_count}')
        print(f'total_sec_16 : {self.total_sec_16}')
        print(f'media : {self.media}')
        print(f'FAT_size_16 : {self.FAT_size_16}')
        print(f'sec_per_track : {self.sec_per_track}')
        print(f'num_of_header : {self.num_of_header}')
        print(f'hidden_sec : {self.hidden_sec}')
        print(f'total_sec_32 : {self.total_sec_32}')
        print(f'FAT_size_32 : {self.FAT_size_32}')
        print(f'ext_flag : {self.ext_flag}')
        print(f'fs_version : {self.fs_version}')
        print(f'root_cluster : {self.root_cluster}')
        print(f'fs_info : {self.fs_info}')
        print(f'bk_boot_sec : {self.bk_boot_sec}')
        print(f'drive_num : {self.drive_num}')
        print(f'boot_sig : {self.boot_sig}')
        print(f'vol_id : {self.vol_id}')
        print(f'vol_lab : {self.vol_lab}')
        print(f'fs_type : {self.fs_type}')
        print(f'bs_sig : 0x{self.bs_sig:x}')

        # Calculated parameter
        print(f'FAT_start_sec : {self.FAT_start_sec}')
        print(f'FAT_sec_count : {self.FAT_sec_count}')
        print(f'root_dir_start_sec : {self.root_dir_start_sec}')
        print(f'root_dir_sec_count : {self.root_dir_sec_count}')
        print(f'data_start_sec : {self.data_start_sec}')
        print(f'data_sec_count : {self.data_sec_count}')
        print('')
