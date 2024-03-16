six_hr_format = [
    'LOCATION MB 6\n',
    'DT*DT*DT\n'
    'T 12 18*00 06 12 18*00 03 06\n',
    'S 12 18*00 06 12 18*00 03 06\n',
    'P 2 8*0 6 2 8*0 3 6\n',
    'S 2 8*0 6 2 8*0 3 6\n',
    'W 2 8*0 6 2 8*0 3 6\n',
    '% 2 8*0 6 2 8*0 3 6',
]

print(len(''.join(six_hr_format)))

print(''.join(six_hr_format))

three_hr_format = [
    'LOCATION MB 3\n',
    'DT12*DT\n'
    'T 12 15 18 21*00 03 06 09 12\n',
    'S 12 15 18 21*00 03 06 09 12\n',
    'P 2 5 8 1*0 3 6 9 2\n',
    'S 2 5 8 1*0 3 6 9 2\n',
    'W 2 5 8 1*0 3 6 9 2\n',
    '% 2 5 8 1*0 3 6 9 2',
]

print(len(''.join(three_hr_format)))

print(''.join(three_hr_format))

nine_day_format = [
    'LOCATION MB 24\n',
    'DT-DT\n'
    'T 01 02 03 04 05 06 07 08 09\n',
    'S 01 02 03 04 05 06 07 08 09\n',
    'P 1 2 3 4 5 6 7 8 9\n',
    'S 1 2 3 4 5 6 7 8 9\n',
    'W 1 2 3 4 5 6 7 8 9\n',
    '% 1 2 3 4 5 6 7 8 9',
]

print(len(''.join(nine_day_format)))

print(''.join(nine_day_format))