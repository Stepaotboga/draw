import sys
import os
import traceback
import serial
import time
import serial.tools.list_ports
from random import *
import json
from PIL import Image, ImageDraw

import splitter
import convert
import printer

from PyQt5 import uic
from PyQt5.QtCore import QRect
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow
from PyQt5.QtWidgets import QLabel, QPushButton, QLineEdit, QFileDialog


class Drawer(QMainWindow):
    def __init__(self):
        super().__init__()

        self.font_path = 'C:/draw/fonts/font_russia_1.json'
        self.mode_path = 'C:/draw/mods/mod_1.json'
        self.image_path = ''
        self.comport = ''

        self.data = []
        self.y_err = []
        self.x_poss = []
        self.shift = [5, 4] #145
        self.shifts = [[0, 0]]
        self.text = ''
        self.y_poss = []
        self.replace_letter = ' '
        self.special_letter = ' \n\t'

        self.scale_k = 4    # px per mm
        self.scale = 4      # mm per imagine_num

        self.x_scale = 160
        self.y_scale = 205

        self.min_x = 23
        self.max_x = 150

        #self.line_yshift = 10
        #self.line_lenght = 173.5
        #self.line_n = 23
        self.line_yshift = 5.5
        self.line_lenght = 188
        self.line_n = 20

        self.red_line_pos = 22
        self.speed = 20

        self.letters_dist = 1
        self.gap_dist = 2
        self.x_comp = 1
        self.y_comp = 1

        self.flag = False
        self.do_paint = True
        self.moving_flag = False
        self.is_draw_point = False
        self.use_mod = False

        self.imagine_line = ()
        self.resolution = 0.01
        self.imagine_line_max_len = 0.1
        self.point_pos = [0, 0]
        self.end_letter_pos = None

        self.prev_data = []
        self.next_data = []

        self.traccer_y_lines()
        uic.loadUi('C:/draw/design_ui/new.ui', self)
        self.initUI()

        self.image = None
        self.show_text()

    def initUI(self):
        self.setWindowTitle('ПО для ЧПУ')
        self.setMouseTracking(True)
        self.mode_rbtn.setChecked(False)
        self.mode_btn.hide()
        self.mode_label.hide()

        self.shift_edit.setText(str(' '.join(list(map(str, self.shift)))))
        self.spd_edit.setText(str(self.speed))
        #self.image_label.setStyleSheet("background-color : white")

        self.mode_rbtn.clicked.connect(self.set_chose_mod)
        self.mode_btn.clicked.connect(self.chose_mod)
        self.port_box.activated.connect(self.handleActivated)

        self.path_btn.clicked.connect(self.chose_font)
        self.show_btn.clicked.connect(self.show_text)
        self.update_btn.clicked.connect(self.update_comports)
        self.print_btn.clicked.connect(self.export_data)
        self.calibrate_btn.clicked.connect(self.calibrate)

    def paintEvent(self, event):
        try:
            if self.do_paint and self.image_path:
                pixmap = QPixmap(self.image_path)
                self.image_label.setPixmap(pixmap)
        except:
            print(traceback.format_exc())

    def draw_lines(self, draw):
        wdth = 1

        for i in self.y_poss:
            draw.line((0, round(i * self.scale_k), round(self.x_scale * self.scale_k), round(i * self.scale_k)), fill=(0, 0, 255, 50), width=wdth)

        draw.line((round(self.red_line_pos * self.scale_k), 0, round(self.red_line_pos * self.scale_k), round(self.y_scale * self.scale_k)), fill='red', width=2)

    def draw_dots(self, draw):
        for i in self.data:
            if i != 0:
                x = round(i[0] * self.scale_k)
                y = round(i[1] * self.scale_k)

                #draw.rounded_rectangle(((x-1, y-1), (x+1, y+1)), radius=2, fill=(0, 0, 100))
                #draw.point((x, y), fill=(0, 0, 100))
                draw.ellipse((x, y, x + 2, y + 2), fill=(0, 0, 100))

    def draw_data(self, draw):
        for i in range(len(self.data) - 1):
            if self.data[i] != 0 and self.data[i + 1] != 0:
                x1 = round(self.data[i][0] * self.scale_k)
                y1 = round(self.data[i][1] * self.scale_k)

                x2 = round(self.data[i + 1][0] * self.scale_k)
                y2 = round(self.data[i + 1][1] * self.scale_k)

                draw.line((x1, y1, x2, y2), fill=(0, 0, 100), width=2)

    def set_chose_mod(self, event):
        if self.mode_rbtn.isChecked():
            self.mode_btn.show()
            self.mode_label.show()
            self.use_mod = True
        else:
            self.mode_btn.hide()
            self.mode_label.hide()
            self.use_mod = False
        self.show_text()

    def chose_font(self):
        try:
            path = QFileDialog.getOpenFileName(self, 'Выбрать шрифт', 'C:/draw/fonts')[0]
            if path and path[-5:] == '.json':
                with open(path, 'r', encoding='utf-8') as json_file:
                    data = json.load(json_file)
                    name = data['name']
                    if data['type'] != 'font':
                        raise Exception('youre choosing not font')
                self.font_path = path
                self.font_label.setText(name)
                self.show_text()
        except Exception as exc:
            print(exc)

    def chose_mod(self):
        try:
            path = QFileDialog.getOpenFileName(self, 'Выбрать модификацию', 'C:/draw/mods')[0]
            if path and path[-5:] == '.json':
                with open(path, 'r', encoding='utf-8') as json_file:
                    data = json.load(json_file)
                    name = data['name']
                    if data['type'] != 'mod':
                        self.statusbar.showMessage('youre choosing not font')
                        raise Exception('youre choosing not font')
                    self.shifts = [[0, 0]]
                    power = 20
                    for i in range(power):
                        length = randrange(*data['mode']['random_x_shift_len'])
                        x_shift = round(randrange(*list(map(lambda x: round(x * 100), data['mode']['random_x_shift_amplitude']))) / 100, 2)
                        y_shift = 0 # round(randrange(*list(map(lambda x: round(x * 100), data['mode']['random_y_shift_amplitude']))) / 100, 2)
                        x_prev = self.shifts[-1][0]
                        y_prev = 0 # self.shifts[-1][1]
                        for i in range(length):
                            self.shifts.append([round((x_shift - x_prev) * ((i + 1) / length) + x_prev, 2),
                                                round((y_shift - y_prev) * ((i + 1) / length) + y_prev, 2)])
                        if i == power - 1:
                            x_prev = self.shifts[-1][0]
                            y_prev = 0 # self.shifts[-1][1]
                            for i in range(length):
                                self.shifts.append([round((0 - x_prev) * ((i + 1) / length) + x_prev, 2),
                                                    round((0 - y_prev) * ((i + 1) / length) + y_prev, 2)])
                    #print(self.shifts)

                self.mode_path = path
                self.mode_label.setText(name)
                self.show_text()
        except Exception as exc:
            print(exc)

    def handleActivated(self, index):
        try:
            self.comport = self.port_box.itemText(index).split(' ')[0]
        except Exception:
            print(traceback.format_exc())

    def show_text(self):
        try:
            with open(self.font_path, 'r', encoding='utf-8') as json_file:
                main_dict = json.load(json_file)

            text_inp = self.text_input.toPlainText().replace('"', "''").replace('—', '-').replace('«', "''").replace('»', "''")
            text = ''
            for i in text_inp:
                if i in main_dict['font']['letters'].keys() or i in self.special_letter:
                    text += i
                else:
                    text += self.replace_letter
                    print('dont excist', i)


            self.data = []
            words = []
            for i in text:
                if words and i in splitter.letters and words[-1][0] in splitter.letters:
                    words[-1] += i
                else:
                    words.append(i)
            syllables = []
            for i in words:
                if len(i) != 0 and i[0] in splitter.letters:
                    syllables.extend(splitter.split_word(i))
                else:
                    syllables.extend(i)
            #print(syllables)
            self.traccer_y_lines()

            self.x_comp = float(self.x_comp_edit.text())
            self.y_comp = float(self.y_comp_edit.text())
            self.scale_k = float(self.scale_edit.text())

            current_line = 1
            current_x_pos = self.min_x
            for n_syl, syllable in enumerate(syllables):
                # проход по слогам / n_sul - номер текущ. слога / syllable - слог
                if syllable == ' ':
                    current_x_pos = round(self.gap_dist + current_x_pos, 2)
                    if syllable != syllables[-1] and not syllables[n_syl + 1] in self.special_letter:
                        length = 0
                        for lns_pos, letter_ns in enumerate(syllables[n_syl + 1]):
                            max_x_pos_ns = main_dict['font']['letters'][letter_ns]['max_x_pos']
                            end_x_pos_ns = main_dict['font']['letters'][letter_ns]['end_x_pos']
                            min_x_pos_ns = main_dict['font']['letters'][letter_ns]['min_x_pos']

                            length = round(length - min_x_pos_ns * self.scale * self.x_comp, 2)

                            if letter_ns != syllables[n_syl + 1][-1]:
                                conn_key_ns = ''
                                if letter_ns in main_dict['font']['connections'].keys():
                                    for key in main_dict['font']['connections'][letter_ns].keys():
                                        if syllables[n_syl + 1][0] in key:
                                            conn_key_ns = key
                                            break
                                    if conn_key_ns:
                                        length = round(length + end_x_pos_ns * self.scale * self.x_comp, 2)
                                        len_min_max = main_dict['font']['connections'][letter_ns][conn_key_ns]['len_min_max']
                                        min_x_pos_next = main_dict['font']['letters'][syllables[n_syl + 1][lns_pos + 1]]['min_x_pos']

                                        length = round(length + len_min_max * self.scale * self.x_comp + min_x_pos_next * self.scale * self.x_comp, 2)
                                if not conn_key_ns:
                                    length = round(length + max_x_pos_ns * self.scale * self.x_comp + self.letters_dist, 2)
                            else:
                                round(length + max_x_pos_ns * self.scale * self.x_comp, 2)
                        # checking length --------------------------------------------------------------------------------------------------------------------------------------------
                        if current_x_pos + length > self.max_x:
                            self.data.append(0)
                            self.y_err.append(0)

                            current_line += 1

                            if syllables[n_syl + 1] == ' ':
                                current_x_pos = round(self.min_x - self.gap_dist, 2)
                            else:
                                current_x_pos = self.min_x

                elif syllable == '\t':
                    current_x_pos = round(self.gap_dist * 5 + current_x_pos, 2)
                elif syllable == '\n':
                    current_x_pos = self.min_x
                    current_line += 1
                else:
                    for n_letter, letter in enumerate(syllable):
                        # проход по буквам в слоге / n_letter - номер буквы / letter - буква
                        data = self.mode_data(main_dict['font']['letters'][letter]['data'])
                        max_x_pos = main_dict['font']['letters'][letter]['max_x_pos']
                        end_x_pos = main_dict['font']['letters'][letter]['end_x_pos']
                        min_x_pos = main_dict['font']['letters'][letter]['min_x_pos']
                        # загрузка траектории и мин. / мас. позиции буквы

                        while data[-1] == 0:
                            del data[-1]
                        # удаление разделителей в конце траектории

                        current_x_pos = round(current_x_pos - min_x_pos * self.scale * self.x_comp, 2)
                        # текущ. позиция

                        if current_line > len(self.y_poss) - 1:
                            print('END LEAF!!!!!')
                            continue

                        data_y_pos = list(map(lambda x: round(x[1], 2) if x != 0 else 0, data))
                        data = list(map(lambda x: [round(current_x_pos + x[0], 2), round(self.y_poss[current_line] - x[1], 2)] if x != 0 else 0, data))

                        if self.data and self.data[-1] != 0:
                            x1 = self.data[-1][0]
                            y1 = self.data[-1][1]
                            x2 = data[0][0]
                            y2 = data[0][1]
                            distance = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
                            if distance > 0.5:
                                self.data.append(0)
                                self.y_err.append(0)

                        self.data.extend(data)
                        self.y_err.extend(data_y_pos)

                        if letter == syllable[-1] and syllable != syllables[-1]:
                            # проверка на последнюю букву в слоге. если последняя то расчет длины след. слога и перенос если выход за границу
                            length = 0

                            if syllables[n_syl + 1] == ' ':
                                current_x_pos = round(current_x_pos + max_x_pos * self.scale * self.x_comp, 2)
                                length = self.gap_dist
                                if current_x_pos + length > self.max_x:
                                    self.data.append(0)
                                    self.y_err.append(0)
                                    current_line += 1
                                    current_x_pos = round(self.min_x - self.gap_dist, 2)
                            elif syllables[n_syl + 1] == '\n':
                                current_x_pos = self.min_x
                            else:
                                conn_key = ''
                                if letter in main_dict['font']['connections'].keys():
                                    for key in main_dict['font']['connections'][letter].keys():
                                        if syllables[n_syl + 1][0] in key:
                                            conn_key = key
                                            break
                                    if conn_key:
                                        length = round(length + end_x_pos * self.scale * self.x_comp, 2)
                                        len_min_max = main_dict['font']['connections'][letter][conn_key]['len_min_max']
                                        min_x_pos_next = main_dict['font']['letters'][syllables[n_syl + 1][0]]['min_x_pos']

                                        length = round(length + len_min_max * self.scale * self.x_comp + min_x_pos_next * self.scale * self.x_comp, 2)
                                if not conn_key:
                                    length = round(length + max_x_pos * self.scale * self.x_comp + self.letters_dist, 2)

                                for lns_pos, letter_ns in enumerate(syllables[n_syl + 1]):
                                    max_x_pos_ns = main_dict['font']['letters'][letter_ns]['max_x_pos']
                                    end_x_pos_ns = main_dict['font']['letters'][letter_ns]['end_x_pos']
                                    min_x_pos_ns = main_dict['font']['letters'][letter_ns]['min_x_pos']

                                    length = round(length - min_x_pos_ns * self.scale * self.x_comp, 2)

                                    if letter_ns != syllables[n_syl + 1][-1]:
                                        conn_key_ns = ''
                                        if letter_ns in main_dict['font']['connections'].keys():
                                            for key in main_dict['font']['connections'][letter_ns].keys():
                                                if syllables[n_syl + 1][0] in key:
                                                    conn_key_ns = key
                                                    break
                                            if conn_key_ns:
                                                length = round(length + end_x_pos_ns * self.scale * self.x_comp, 2)
                                                len_min_max = main_dict['font']['connections'][letter_ns][conn_key_ns]['len_min_max']
                                                min_x_pos_next = main_dict['font']['letters'][syllables[n_syl + 1][lns_pos + 1]]['min_x_pos']

                                                length = round(length + len_min_max * self.scale * self.x_comp + min_x_pos_next * self.scale * self.x_comp, 2)
                                        if not conn_key_ns:
                                            length = round(length + max_x_pos_ns * self.scale * self.x_comp + self.letters_dist, 2)
                                    else:
                                        round(length + max_x_pos_ns * self.scale * self.x_comp, 2)

                                # main -----------------------------------------------------------------------------------------------------------------------------------

                                if current_x_pos + length > self.max_x:
                                    if letter in splitter.letters and syllables[n_syl + 1][0] in splitter.letters:
                                        data = self.mode_data(main_dict['font']['letters']['-']['data'])

                                        while data[-1] == 0:
                                            del data[-1]

                                        current_x_pos = round(current_x_pos + max_x_pos * self.scale * self.x_comp + self.letters_dist, 2)

                                        data_y_pos = list(map(lambda x: round(x[1], 2) if x != 0 else 0, data))
                                        data = list(map(lambda x: [round(current_x_pos + x[0], 2), round(self.y_poss[current_line] - x[1], 2)] if x != 0 else 0, data))

                                        self.data.append(0)
                                        self.y_err.append(0)

                                        self.data.extend(data)
                                        self.y_err.extend(data_y_pos)

                                        self.data.append(0)
                                        self.y_err.append(0)

                                        current_line += 1

                                        if syllables[n_syl + 1] == ' ':
                                            current_x_pos = round(self.min_x - self.gap_dist, 2)
                                        else:
                                            current_x_pos = self.min_x
                                    else:
                                        self.data.append(0)
                                        self.y_err.append(0)

                                        current_line += 1

                                        if syllables[n_syl + 1] == ' ':
                                            current_x_pos = round(self.min_x - self.gap_dist, 2)
                                        else:
                                            current_x_pos = self.min_x

                                else:
                                    conn_key = ''
                                    if letter in main_dict['font']['connections'].keys():
                                        for key in main_dict['font']['connections'][letter].keys():
                                            if syllables[n_syl + 1][0] in key:
                                                conn_key = key
                                                break
                                        if conn_key:
                                            data = self.mode_data(main_dict['font']['connections'][letter][conn_key]['data'])
                                            len_min_max = main_dict['font']['connections'][letter][conn_key]['len_min_max']
                                            min_x_pos_next = main_dict['font']['letters'][syllables[n_syl + 1][0]]['min_x_pos']

                                            while data[-1] == 0:
                                                del data[-1]

                                            current_x_pos = round(current_x_pos + end_x_pos * self.scale * self.x_comp, 2)

                                            data_y_pos = list(map(lambda x: round(x[1], 2) if x != 0 else 0, data))
                                            data = list(map(lambda x: [round(current_x_pos + x[0], 2), round(self.y_poss[current_line] - x[1], 2)] if x != 0 else 0, data))

                                            if self.data and self.data[-1] != 0:
                                                x1 = self.data[-1][0]
                                                y1 = self.data[-1][1]
                                                x2 = data[0][0]
                                                y2 = data[0][1]
                                                distance = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
                                                if distance > 0.5:
                                                    self.data.append(0)
                                                    self.y_err.append(0)

                                            self.data.extend(data)
                                            self.y_err.extend(data_y_pos)

                                            current_x_pos = round(current_x_pos + len_min_max * self.scale * self.x_comp + min_x_pos_next * self.scale * self.x_comp, 2)
                                    if not conn_key:
                                        current_x_pos = round(current_x_pos + max_x_pos * self.scale * self.x_comp + self.letters_dist, 2)


                        else:
                            conn_key = ''
                            if letter in main_dict['font']['connections'].keys():
                                for key in main_dict['font']['connections'][letter].keys():
                                    if not letter == syllable[-1] and syllable[n_letter + 1] in key:
                                        conn_key = key
                                        break
                                if conn_key:
                                    data = self.mode_data(main_dict['font']['connections'][letter][conn_key]['data'])
                                    len_min_max = main_dict['font']['connections'][letter][conn_key]['len_min_max']
                                    min_x_pos_next = main_dict['font']['letters'][syllable[n_letter + 1]]['min_x_pos']

                                    while data[-1] == 0:
                                        del data[-1]


                                    current_x_pos = round(current_x_pos + end_x_pos * self.scale * self.x_comp, 2)

                                    data_y_pos = list(map(lambda x: round(x[1], 2) if x != 0 else 0, data))
                                    data = list(map(lambda x: [round(current_x_pos + x[0], 2), round(self.y_poss[current_line] - x[1], 2)] if x != 0 else 0, data))

                                    if self.data and self.data[-1] != 0:
                                        x1 = self.data[-1][0]
                                        y1 = self.data[-1][1]
                                        x2 = data[0][0]
                                        y2 = data[0][1]
                                        distance = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
                                        if distance > 0.5:
                                            self.data.append(0)
                                            self.y_err.append(0)

                                    self.data.extend(data)
                                    self.y_err.extend(data_y_pos)
                                    current_x_pos = round(current_x_pos + len_min_max * self.scale * self.x_comp + min_x_pos_next * self.scale * self.x_comp, 2)

                            if not conn_key:
                                current_x_pos = round(current_x_pos + max_x_pos * self.scale * self.x_comp + self.letters_dist, 2)
            if self.use_mod:
                n_data = []
                for i in range(len(self.data)):
                    if self.data[i] != 0:
                        x = self.data[i][0]
                        y = self.data[i][1]
                        n_data.append([round(x + self.shifts[i % len(self.shifts)][0] * self.y_err[i], 2),
                                       round(y + self.shifts[i % len(self.shifts)][1], 2)])
                    else:
                        n_data.append(0)
                self.data = n_data

            self.image_label.resize(round(self.x_scale * self.scale_k), round(self.y_scale * self.scale_k))

            image = Image.new("RGBA", (round(self.x_scale * self.scale_k), round(self.y_scale * self.scale_k)), (255, 255, 255))
            draw = ImageDraw.Draw(image)

            self.draw_lines(draw)
            if self.data:
                self.draw_dots(draw)
                self.draw_data(draw)

            image = image.resize((int(image.width / 3), int(image.height / 3)))

            image.save('C:/draw/leaf.png')
            self.image_path = 'C:/draw/leaf.png'

            self.update()
            self.do_paint = True

        except Exception:
            print(traceback.format_exc())


    def traccer_y_lines(self):
        self.y_poss = [0]
        for i in range(1, self.line_n):
            self.y_poss.append(round((self.line_lenght - self.y_poss[-1]) / (self.line_n - i) + self.y_poss[-1], 2))
        self.y_poss = list(map(lambda x: round(x + self.line_yshift, 2), self.y_poss))

    def mode_data(self, data):
        data = list(map(lambda x: [round(x[0] * self.x_comp * self.scale, 2), round(x[1] * self.y_comp * self.scale, 2)] if x != 0 else 0, data))
        return data

    def update_comports(self):
        try:
            ports = serial.tools.list_ports.comports()
            self.port_box.clear()
            if ports:
                self.port_box.addItems([str(ports[0])])
                self.comport = self.port_box.itemText(0).split(' ')[0]
        except Exception:
            print(traceback.format_exc())

    def calibrate(self):
        try:
            port = self.comport
            if port:
                self.statusbar.setStyleSheet('background-color : lightgray')
                self.statusbar.showMessage('ok')

                x = self.red_line_pos
                y = self.y_poss[0]
                data = [[round(x - 3), round(y)], [round(x), round(y)], [round(x), round(y + 3)]]
                self.shift = list(map(float, self.shift_edit.text().split(' ')))
                gcode = convert.cnvrt(data, self.shift, speed=10)
                printer.draw(gcode, port)
            else:
                self.statusbar.setStyleSheet('background-color : pink')
                self.statusbar.showMessage('dont choosen comport')
        except Exception:
            print(traceback.format_exc())

    def export_data(self):
        try:
            port = self.comport
            if port:
                self.statusbar.setStyleSheet('background-color : lightgray')
                self.statusbar.showMessage('ok')

                self.shift = list(map(float, self.shift_edit.text().split(' ')))
                self.speed = int(self.spd_edit.text())
                gcode = convert.cnvrt(self.data, self.shift, speed=self.speed)
                print(gcode)
                printer.draw(gcode, port, obj=self.statusbar)
            else:
                self.statusbar.setStyleSheet('background-color : pink')
                self.statusbar.showMessage('dont choosen comport')

        except Exception as exc:
            print(exc)



if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Drawer()
    ex.show()
    sys.exit(app.exec())
