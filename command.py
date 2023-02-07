import os

from boot_sec import BootSecor
from fs_info import FSInfo
from fat import FAT
from dir import Directory
from helper import read_sector, read_sectors
from helper import write_sector, write_sectors
from helper import SECTOR_SIZE

DIR_SIZE = 32


class CommandController:
    CMD_INDEX = 0
    DESC_INDEX = 1

    def __init__(self, path):
        self.path = path
        self.curr_cluster_index = 2  # Root cluster
        self.cluster_index_stack = []
        self.pwd = path
        self.pwd_stack = []
        self.table = {
            'cd': (self._cd_cmd, 'cd'),
            'dir': (self._dir_cmd, 'dir'),
            'del': (self._del_cmd, 'del'),
            'mkdir': (self._mkdir_cmd, 'mkdir'),
            'rmdir': (self._rmdir_cmd, 'rmdir'),
            'dump': (self._dump_cmd, 'dump'),
            'pwd': (self._pwd_cmd, 'pwd'),
            'download': (self._download_cmd, 'download'),
            'load': (self._load_FAT_cmd, 'load FAT'),
            'help': (self._help_cmd, ''),
        }
        self.bs = None
        self.fs_info = None
        self.fat = None

    def run(self):
        print('Load boot secotr...', end='')
        data = read_sector(self.path, 0)
        self.bs = BootSecor(data)
        print('Done')

        print('Load FS info sector...', end='')
        data = read_sector(self.path, self.bs.fs_info)
        self.fs_info = FSInfo(data)
        print('Done')

        print('Load FAT...', end='')
        self._load_FAT_cmd(None)
        print('Done')

        self.main_loop()

    def main_loop(self):
        while True:
            print('>> ', end='')
            cmd = input()
            cmd = cmd.strip().lower()
            split = cmd.split(' ')
            cmd = split[0]
            if len(split) == 1:
                cmd = split[0]
                arg = None
            elif len(split) == 2:
                cmd = split[0]
                arg = split[1]
            else:
                print('Invalid command format')
                continue

            if cmd == 'q':
                break
            elif cmd in self.table:
                self.table[cmd][CommandController.CMD_INDEX](arg)
            else:
                print(f'Unknown cmd : {cmd}')

    def _to_sector_index(self, cluster_index):
        sec_per_cluster = self.bs.sec_per_cluster
        root_dir_start_sec = self.bs.root_dir_start_sec
        return root_dir_start_sec + (cluster_index - 2) * sec_per_cluster

    def _read_cluster(self, index):
        sec_per_cluster = self.bs.sec_per_cluster
        sector_index = self._to_sector_index(index)
        return read_sectors(self.path, sector_index, sec_per_cluster)

    def _write_cluster(self, index, data):
        sec_per_cluster = self.bs.sec_per_cluster
        sector_index = self._to_sector_index(index)
        return write_sectors(self.path, sector_index, data, sec_per_cluster)

    def _cd_cmd(self, target):
        if target == '.':
            return
        if target == '..':
            if len(self.cluster_index_stack) != 0:
                self.curr_cluster_index = self.cluster_index_stack.pop()
                self.pwd = self.pwd_stack.pop()
            return

        target_cluster_index = None
        for directory in self._get_dir_entity(self.curr_cluster_index):
            if directory.is_archive:
                continue
            name = directory.get_name()
            if name.startswith(target):
                target_cluster_index = directory.cluster
                break
        if target_cluster_index is None:
            print(f'Can not find path {target}')
        else:
            self.cluster_index_stack.append(self.curr_cluster_index)
            self.curr_cluster_index = target_cluster_index
            self.pwd_stack.append(self.pwd)
            self.pwd += f'\\{name}'

    def _dir_cmd(self, _):
        print('dir')
        for directory in self._get_dir_entity(self.curr_cluster_index, False):
            directory.dump()

    def _get_file(self, name):
        for directory in self._get_dir_entity(self.curr_cluster_index):
            if directory.is_dir:
                continue

            if directory.get_name() == name:
                return directory
        return None

    def _get_directory(self, name):
        for directory in self._get_dir_entity(self.curr_cluster_index):
            if directory.is_archive:
                continue

            if directory.get_name() == name:
                return directory
        return None

    def _get_dir_entity(self, cluster_index, bypass_sys=True):
        ret = []
        sector_index = self._to_sector_index(cluster_index)
        while True:
            ptr = 0
            data = self._read_cluster(cluster_index)
            for _ in range(self.bs.sec_per_cluster):
                offset = 0
                for _ in range(int(SECTOR_SIZE / DIR_SIZE)):
                    directory = Directory(
                        data[ptr: ptr + DIR_SIZE], sector_index, offset)
                    ptr += DIR_SIZE
                    offset += DIR_SIZE

                    if directory.not_used:
                        continue
                    if directory.is_hidden:
                        continue

                    if bypass_sys:
                        name = directory.get_name()
                        if name == '.' or name == '..':
                            continue
                    ret.append(directory)

                sector_index += 1
            if self.fat.state[cluster_index] == FAT.IN_USE:
                cluster_index = self.fat.data[cluster_index]
            else:
                break
        return ret

    def _get_ununsed_dir_entity(self):
        cluster_index = self.curr_cluster_index
        sector_index = self._to_sector_index(cluster_index)
        while True:
            ptr = 0
            data = self._read_cluster(cluster_index)
            for _ in range(self.bs.sec_per_cluster):
                offset = 0
                for _ in range(int(SECTOR_SIZE / DIR_SIZE)):
                    directory = Directory(
                        data[ptr: ptr + DIR_SIZE], sector_index, offset)
                    ptr += DIR_SIZE
                    offset += DIR_SIZE

                    if directory.is_hidden:
                        continue
                    if directory.not_used:
                        return directory
                sector_index += 1
            if self.fat.state[cluster_index] == FAT.IN_USE:
                cluster_index = self.fat.data[cluster_index]
            else:
                return None

    def _del_cmd(self, filename):
        directory = self._get_file(filename)
        if directory is None:
            print(f'Can not find {filename}')
        else:
            self._del_dir(directory)

    def _mkdir_cmd(self, dir_name):
        directory = self._get_ununsed_dir_entity()
        if directory is None:
            print('Fail to make new directory')
            return
        offset = directory.offset
        data = read_sector(self.path, directory.sector_index)
        data = bytearray(data)
        dir_name_bytes = str.encode(dir_name, encoding='utf-8')
        # Set directory name
        for i in range(min(11, len(dir_name_bytes))):
            data[offset + i] = dir_name_bytes[i]
        
        data[offset + 11] = Directory.ATTR_DIRECTORY
        # Set file size = 0
        for i in range(4):
            data[offset + 28 + i] = 0
        write_sector(self.path, directory.sector_index, data)

    def _rmdir_cmd(self, dir_name):
        directory = self._get_directory(dir_name)
        if directory is None:
            print(f'Can not find {dir_name}')
            return
        else:
            for _dir in self._get_dir_entity(directory.cluster):
                name = _dir.get_name()
                self._cd_cmd(dir_name)
                if _dir.is_archive:
                    self._del_cmd(name)
                else:
                    self._rmdir_cmd(name)
                self._cd_cmd('..')
        self._del_dir(directory)

    def _del_dir(self, directory):
        data = read_sector(self.path, directory.sector_index)
        data = bytearray(data)
        data[directory.offset] = 0xe5
        write_sector(self.path, directory.sector_index, data)

        # Clear FAT table
        cluster_index = directory.cluster
        while True:
            if self.fat.state[cluster_index] == FAT.IN_USE:
                self.fat.state[cluster_index] = FAT.FREE
                cluster_index = self.fat.data[cluster_index]
                byte_offset = cluster_index % (SECTOR_SIZE // DIR_SIZE)
                data = read_sector(
                    self.path, self.bs.FAT_start_sec + byte_offset)
                data = bytearray(data)
                data[byte_offset * 4 + 0] = 0xff
                data[byte_offset * 4 + 1] = 0xff
                data[byte_offset * 4 + 2] = 0xff
                data[byte_offset * 4 + 3] = 0xff
                write_sector(self.path, self.bs.FAT_start_sec +
                             byte_offset, data)
            else:
                break

    def _dump_cmd(self, param):
        if param == 'bs':
            self.bs.dump()
        elif param == 'fsinfo':
            self.fs_info.dump()
        elif param == 'fat':
            self.fat.dump()
        else:
            print(f'Unknown param for dump command : {param}')
            print('bs : boot sector')
            print('fsindo : FS info')
            print('fat : FAT')

    def _pwd_cmd(self, _):
        print(self.pwd)

    def _download_cmd(self, param):
        for directory in self._get_dir_entity(self.curr_cluster_index):
            name = directory.get_name()
            if param == name:
                if directory.is_archive:
                    self._download_file(directory)
                else:
                    self._download_directory(directory)
                return

        print(f'Can not find {param}')

    def _download_directory(self, directory):
        name = directory.get_name()
        if not os.path.isdir(name):
            os.mkdir(name)
        os.chdir(name)

        for _dir in self._get_dir_entity(directory.cluster):
            if _dir.is_archive:
                self._download_file(_dir)
            else:
                self._download_directory(_dir)
        os.chdir('..')

    def _download_file(self, directory):
        remain = directory.file_size
        buffer = bytearray(remain)
        ptr = 0
        while remain > 0:
            data = self._read_cluster(directory.cluster)
            size = min(len(data), remain)
            for i in range(size):
                buffer[ptr] = data[i]
                ptr += 1
            remain -= size
        name = directory.get_name()
        with open(name, 'wb+') as f:
            f.write(buffer)

    def _load_FAT_cmd(self, _):
        data = read_sectors(self.path, self.bs.FAT_start_sec,
                            self.bs.FAT_sec_count)
        self.fat = FAT(data, self.bs.FAT_sec_count * SECTOR_SIZE)

    def _help_cmd(self, _):
        for key, val in self.table.items():
            desc = val[CommandController.DESC_INDEX]
            if len(desc) == 0:
                continue
            print(f'{key} : {desc}')
