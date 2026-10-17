import serial
import time


def draw(gcode, port, obj=None):
    arduino = serial.Serial(port, 57600, timeout=None)
    time.sleep(2)

    lenn = len(gcode)
    counter = 0

    for n, i in enumerate(gcode):
        arduino.write(str(i + '\n').encode())
        if counter > 10:
            if obj:
                obj.showMessage(f'in process {round(n / lenn * 100, 1)}%')
            else:
                print(n / lenn * 100, '%\n')
            counter = 0
        counter += 1
        while True:
            data = arduino.readline().decode('utf-8').strip()
            # print('output:', data)
            if data == "done":
                break
    if obj:
        obj.showMessage('done!')


if __name__ == '__main__':
    gcode = ['U', 'H', 'M 77.24 21.88 20', 'D', 'M 77.24 21.56 20', 'M 77.12 21.36 20', 'M 76.88 21.16 20', 'M 76.64 21.12 20', 'M 76.36 21.2 20', 'M 76.04 21.36 20', 'M 75.8 21.56 20', 'M 75.56 21.84 20', 'M 75.36 22.16 20', 'M 75.2 22.48 20', 'M 75.08 22.84 20', 'M 75.0 23.2 20', 'M 75.0 23.52 20', 'M 75.12 23.8 20', 'M 75.32 23.96 20', 'M 75.6 24.0 20', 'M 75.92 23.92 20', 'M 76.2 23.76 20', 'M 76.48 23.52 20', 'M 76.68 23.24 20', 'M 76.88 22.92 20', 'M 77.04 22.6 20', 'M 77.16 22.24 20', 'M 77.32 21.88 20', 'M 77.48 21.52 20', 'M 77.64 21.16 20', 'M 77.48 21.52 20', 'M 77.32 21.88 20', 'M 77.2 22.24 20', 'M 77.08 22.6 20', 'M 76.96 22.96 20', 'M 76.88 23.32 20', 'M 76.84 23.68 20', 'M 76.96 23.92 20', 'M 77.16 24.0 20', 'M 77.4 23.92 20', 'M 77.68 23.72 20', 'M 77.92 23.48 20', 'U', 'H']
    port = 'COM5'
    draw(gcode, port)