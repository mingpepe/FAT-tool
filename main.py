import sys

from cmd import CommandController

def main():
    if len(sys.argv) == 2:
        path = sys.argv[1]
        controller = CommandController(path)
        controller.run()
    else:
        print('Usage : main.py FAT32_DIR_PATH')
    
if __name__ == '__main__':
    main()