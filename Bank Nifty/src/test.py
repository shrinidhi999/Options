file = open("Bank Nifty\src\credentials.txt", "r").read().split('\n')
print(file[0].split(' = ')[1])
print(file[1].split(' = ')[1])
print(file[2].split(' = ')[1])
