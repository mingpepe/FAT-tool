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
        self.curr_cluster_index = 2 # Root cluster
        self.cluster_index_stack = []
        self.pwd = path
        self.pwd_stack = []

    def run(self):
        self.table = {
            'cd' : (self._cd_cmd, 'cd'),
            'dir' : (self._dir_cmd, 'dir'),
            'del' : (self._del_cmd, 'del'),
            'mkdir' : (self._mkdir_cmd, 'mkdir'),
            'rmdir' : (self._rmdir_cmd, 'rmdir'),
            'dump': (self._dump_cmd, 'dump'),
            'pwd': (self._pwd_cmd, 'pwd'),
            'download': (self._download_cmd, 'download'),
            'load': (self._load_FAT_cmd, 'load FAT'),
            'help': (self._help_cmd, ''),
        }
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
        if target == '.': return
        if target == '..':
            self.curr_cluster_index = self.cluster_index_stack.pop()
            self.pwd = self.pwd_stack.pop()
            return

        target_cluster_index = None
        for dir in self._get_dir_entity(self.curr_cluster_index):
            if dir.is_archive: continue
            name = dir.get_name()
            if name.startswith(target):
                target_cluster_index = dir.cluster
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
        for dir in self._get_dir_entity(self.curr_cluster_index, False):
            dir.dump()        
    
    def _get_file(self, name):
        for dir in self._get_dir_entity(self.curr_cluster_index):
            if dir.is_dir: continue

            if dir.get_name() == name:
                return dir
        return None

    def _get_directory(self, name):
        for dir in self._get_dir_entity(self.curr_cluster_index):
            if dir.is_archive: continue

            if dir.get_name() == name:
                return dir
        return None

    def _get_dir_entity(self, cluster_index, bypass_sys = True):
        ret = []
        sector_index = self._to_sector_index(cluster_index)
        while True:
            ptr = 0
            data = self._read_cluster(cluster_index)
            for i in range(self.bs.sec_per_cluster):
                offset = 0
                for j in range(int(SECTOR_SIZE / DIR_SIZE)):
                    dir = Directory(data[ptr : ptr + DIR_SIZE], sector_index, offset)
                    ptr += DIR_SIZE
                    offset += DIR_SIZE

                    if dir.not_used:continue
                    if dir.is_hidden: continue

                    if bypass_sys:
                        name = dir.get_name()
                        if name == '.' or name == '..': continue
                    ret.append(dir)

                sector_index += 1
            if self.fat.state[cluster_index] == FAT.IN_USE:
                cluster_index = self.fat.data[cluster_index]
            else:
                break
        return ret

    def _del_cmd(self, filename):
        dir = self._get_file(filename)
        if dir is None:
            print(f'Can not find {filename}')
        else:
            self._del_dir(dir)

    def _mkdir_cmd(self, dir_name):
        print('Not implement yet')

    def _rmdir_cmd(self, dir_name):
        dir = self._get_directory(dir_name)
        if dir is None:
            print(f'Can not find {dir_name}')
            return
        else:
            for _dir in self._get_dir_entity(dir.cluster):
                name = _dir.get_name()
                self._cd_cmd(dir_name)
                if _dir.is_archive:
                    self._del_cmd(name)
                else:
                    self._rmdir_cmd(name)
                self._cd_cmd('..')
        self._del_dir(dir)
    
    def _del_dir(self, dir):
        data = read_sector(self.path, dir.sector_index)
        data = bytearray(data)
        data[dir.offset] = 0xe5
        write_sector(self.path, dir.sector_index, data)

        # Clear FAT table
        cluster_index = dir.cluster
        while True:
            if self.fat.state[cluster_index] == FAT.IN_USE:
                self.fat.state[cluster_index] = FAT.FREE
                cluster_index = self.fat.data[cluster_index]
                sector_offset = cluster_index // (SECTOR_SIZE // DIR_SIZE)
                byte_offset = cluster_index % (SECTOR_SIZE // DIR_SIZE)
                data = read_sector(self.path, self.bs.FAT_start_sec + byte_offset)
                data = bytearray(data)
                data[byte_offset * 4 + 0] = 0xff
                data[byte_offset * 4 + 1] = 0xff
                data[byte_offset * 4 + 2] = 0xff
                data[byte_offset * 4 + 3] = 0xff
                write_sector(self.path, self.bs.FAT_start_sec + byte_offset, data)
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
        for dir in self._get_dir_entity(self.curr_cluster_index):
            name = dir.get_name()
            if param == name:
                if dir.is_archive:
                    self._download_file(dir)
                else:
                    self._download_directory(dir)
                return

        print(f'Can not find {param}')

    def _download_directory(self, dir):
        name = dir.get_name()
        if not os.path.isdir(name):
            os.mkdir(name)
        os.chdir(name)

        for dir in self._get_dir_entity(dir.cluster):
            if dir.is_archive:
                self._download_file(dir)
            else:
                self._download_directory(dir)
        os.chdir('..')

    def _download_file(self, dir):
        remain = dir.file_size
        buffer = bytearray(remain)
        ptr = 0
        while remain > 0:
            data = self._read_cluster(dir.cluster)
            size = min(len(data), remain)
            for i in range(size):
                buffer[ptr] = data[i]
                ptr += 1
            remain -= size
        name = dir.get_name()
        with open(name, 'wb+') as f:
            f.write(buffer)

    def _load_FAT_cmd(self, _):
        data = read_sectors(self.path, self.bs.FAT_start_sec, self.bs.FAT_sec_count)
        self.fat = FAT(data, self.bs.FAT_sec_count * SECTOR_SIZE)

    def _help_cmd(self, _):
        for cmd in self.table:
            desc = self.table[cmd][CommandController.DESC_INDEX]
            if len(desc) == 0:
                continue
            print(f'{cmd} : {desc}')