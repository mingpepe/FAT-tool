from helper import unpack

class FSInfo:
    def __init__(self, data):
        self.lead_sig = unpack('L', data, 0)
        # 480 bytes reserved
        self.struc_sig = unpack('L', data, 484)
        self.free_count = unpack('L', data, 488)
        self.next_free = unpack('L', data, 492)
        # 12 bytes reserved
        self.tail_sig = unpack('L', data, 508)
    
    def dump(self):
        print('[FS info sector]')
        print(f'lead_sig : 0x{self.lead_sig:x}')
        print(f'struc_sig : 0x{self.struc_sig:x}')
        print(f'free_count : {self.free_count}')
        print(f'next_free : {self.next_free}')
        print(f'tail_sig : 0x{self.tail_sig:x}')
        print('')