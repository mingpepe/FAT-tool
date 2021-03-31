from helper import unpack

class FAT:
    FREE = 0
    RESERVED = 1
    IN_USE = 2
    BAD_CLUSTER = 3
    END_OF_CHAIN = 4
    def __init__(self, raw, length):
        self.count = int(length / 4)
        self.data = self.count * [None]
        self.state = self.count * [None]
        for i in range(self.count):
            self.data[i] = unpack('L', raw, i * 4)
            if self.data[i] == 0:
                self.state[i] = FAT.FREE
            elif self.data[i] == 1:
                self.state[i] = FAT.RESERVED
            elif self.data[i] == 0xffffff7:
                self.state[i] = FAT.BAD_CLUSTER
            elif 0xffffff8 <= self.data[i] and self.data[i] <= 0xffffffff:
                self.state[i] = FAT.END_OF_CHAIN
            else:
                self.state[i] = FAT.IN_USE

    def dump(self):
        for i in range(self.count):
            if self.state[i] != FAT.IN_USE: continue
            buffer = ''
            buffer += str(i) + ' -> '
            next = self.data[i]
            while True:
                buffer += str(next) + ' -> '
                if self.state[next] == FAT.IN_USE:
                    next = self.data[next]
                else:
                    print(buffer)
                    break