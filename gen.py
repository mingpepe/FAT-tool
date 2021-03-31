for i in range(2191, 2500):
    try:
        with open('\\\\.\\E:', 'r+b') as f:
            N = i
            f.seek(N * 512)
            data = f.read(512)
            f.seek(N * 512)
            f.write(data)
    except Exception as e:
        print(f'Error : {e} {i}')
        break

print('ENd')
input()