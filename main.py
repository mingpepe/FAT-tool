import sys

from command import CommandController


def main():
    if len(sys.argv) == 2:
        path = sys.argv[1]
        controller = CommandController(path)
        controller.run()
    else:
        print('Usage : main.py FAT32_DIR_PATH')
        print('E.g. main.py \\\\.\\C:')
        print('E.g. main.py file_system/c.img')


if __name__ == '__main__':
    main()
