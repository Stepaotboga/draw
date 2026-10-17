def split_word(word):
    vowels_set = set('аеёиоуыэюяАЕЁИОУЫЭЮЯ' + 'AaEeIiOoUuYy')
    specials_set = set('йьъЙЬЪ')

    prev_vowel = len(word)
    for i in range(len(word)):
        if word[i] in vowels_set:
            prev_vowel = i
            break

    pos = 0
    data = []
    for i in range(prev_vowel + 1, len(word)):
        if word[i] in vowels_set:
            a, b = prev_vowel, i
            if b - a == 1:
                data.append(word[pos:b])
                pos = b
            else:
                for j in reversed(range(a + 1, b)):
                    if word[j] in specials_set:
                        data.append(word[pos:j + 1])
                        pos = j + 1
                        break
                else:
                    if b - a == 2:
                        data.append(word[pos:b - 1])
                        pos = b - 1
                    else:
                        data.append(word[pos:a + 2])
                        pos = a + 2
            prev_vowel = i
    data.append(word[pos:])

    if len(data) > 1:
        if len(data[0]) == 1:
            data[1] = data[0] + data[1]
            del data[0]
        if len(data[-1]) == 1:
            data[-2] += data[-1]
            del data[-1]

    data = list(filter(lambda x: len(x) < 15, data)) # очистка от оочень длинных слогов

    return data

letters = 'ёйцукенгшщзхъфывапролджэячсмитьбюЁЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮQWERTYUIOPASDFGHJKLZXCVBNMqwertyuiopasdfghjklzxcvbnm'




if __name__ == '__main__':
    word = input()
    print(split_word(word))