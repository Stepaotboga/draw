def cnvrt(data, shift, speed=20):
    gcode = []
    data = list(map(lambda x: [round(x[0] + shift[0], 2), round(x[1] + shift[1], 2)] if x != 0 else 0, data))

    for n, i in enumerate(data):
        if n == 0:
            if i != 0:
                x, y = i
                gcode.extend(['U', 'H', f'M {x} {y} {speed}', 'D'])
            else:
                gcode.extend(['U', 'H', f'M 0 0 {speed}', 'D'])
        else:
            try:
                if i == 0:
                    gcode.append('U')
                elif data[n - 1] == 0:
                    x, y = i
                    gcode.extend([f'M {x} {y} {speed}', 'D'])
                else:
                    x, y = i
                    gcode.append(f'M {x} {y} {speed}')
            except Exception as exc:
                print(exc, n)

    gcode.extend(['U', 'H'])
    return gcode
