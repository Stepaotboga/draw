#include <iostream>
#include <fstream>
#include <string>
#include <windows.h>
#include <nlohmann/json.hpp>

// Функция для чтения COM-порта из JSON файла
std::string readPortFromJson(const std::string& filename) {
    std::ifstream file(filename);
    if (!file.is_open()) {
        throw std::runtime_error("Не удалось открыть файл: " + filename);
    }

    nlohmann::json jsonData;
    file >> jsonData;
    return jsonData["port"];
}

// Функция для открытия COM-порта
HANDLE openSerialPort(const std::string& portName) {
    HANDLE hSerial = CreateFile(portName.c_str(),
                                 GENERIC_READ | GENERIC_WRITE,
                                 0,
                                 NULL,
                                 OPEN_EXISTING,
                                 0,
                                 NULL);

    if (hSerial == INVALID_HANDLE_VALUE) {
        throw std::runtime_error("Не удалось открыть COM порт: " + portName);
    }

    DCB dcbSerialParams = {0};
    dcbSerialParams.DCBlength = sizeof(dcbSerialParams);
    if (!GetCommState(hSerial, &dcbSerialParams)) {
        throw std::runtime_error("Ошибка при получении состояния порта");
    }

    dcbSerialParams.BaudRate = CBR_9600;
    dcbSerialParams.ByteSize = 8;
    dcbSerialParams.StopBits = ONESTOPBIT;
    dcbSerialParams.Parity = NOPARITY;

    if (!SetCommState(hSerial, &dcbSerialParams)) {
        throw std::runtime_error("Ошибка при установке параметров порта");
    }

    return hSerial;
}

// Функция отправки команды на COM-порт
void sendCommand(HANDLE hSerial, const std::string& command) {
    DWORD bytesWritten;
    WriteFile(hSerial, command.c_str(), command.size(), &bytesWritten, NULL);
}

// Функция чтения ответа с COM-порта
std::string readResponse(HANDLE hSerial) {
    char buffer[128];
    DWORD bytesRead;
    ReadFile(hSerial, buffer, sizeof(buffer) - 1, &bytesRead, NULL);
    buffer[bytesRead] = '\0';  // Null-terminate the string
    return std::string(buffer);
}

int main() {
    try {
        std::string portName = readPortFromJson("parameters.json");
        
        HANDLE hSerial = openSerialPort(portName);

        std::ifstream commandFile("data.txt");
        if (!commandFile.is_open()) {
            throw std::runtime_error("Не удалось открыть файл с командами: data.txt");
        }

        std::string command;
        while (std::getline(commandFile, command)) {
            sendCommand(hSerial, command + "\n");

            std::string response = readResponse(hSerial);
            if (response == "done\n") {
                std::cout << "Команда выполнена: " << command << std::endl;
            } else {
                std::cerr << "Ошибка выполнения команды: " << command << ", ответ: " << response << std::endl;
            }
        }

        CloseHandle(hSerial);
    } 
    catch (const std::exception& ex) {
        std::cerr << "Ошибка: " << ex.what() << std::endl;
    }

    return 0;
}