#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Добавляем корень проекта в пути импорта
sys.path.append(str(Path(__file__).resolve().parent))

# Инициализируем QApplication для корректной работы Qt Сигналов в тестах
from PyQt6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

from src.network.api_client import NetworkStatusWorker

class TestNetworkStatusWorker(unittest.TestCase):
    @patch("requests.get")
    def test_worker_success_emits_status_received(self, mock_get):
        # 1. Настраиваем успешный ответ сервера
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "is_paused": False,
            "jobs": [{"job_id": "1", "status": "PENDING"}]
        }
        mock_get.return_value = mock_response

        # 2. Создаем воркера
        worker = NetworkStatusWorker("http://fake-server-url", timeout=1.0)
        
        # Шпион для сбора сигналов
        received_data = []
        def on_received(data):
            received_data.append(data)
            
        worker.status_received.connect(on_received)

        # 3. Запускаем поток и ждем его завершения
        worker.start()
        worker.wait(2000)
        app.processEvents()  # Ждем до 2 сек завершения потока

        # 4. Проверяем корректность вызовов
        mock_get.assert_called_once_with("http://fake-server-url/api/server/status", timeout=1.0, headers={"X-Client-ID": "Неизвестный клиент"})
        self.assertEqual(len(received_data), 1)
        self.assertEqual(received_data[0]["is_paused"], False)
        self.assertEqual(len(received_data[0]["jobs"]), 1)

    @patch("requests.get")
    def test_worker_failure_emits_error_occurred(self, mock_get):
        # 1. Настраиваем ошибочный ответ сервера
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        worker = NetworkStatusWorker("http://fake-server-url", timeout=1.0)
        
        errors = []
        def on_error(err):
            errors.append(err)
            
        worker.error_occurred.connect(on_error)

        # 2. Запускаем поток
        worker.start()
        worker.wait(2000)
        app.processEvents()

        # 3. Проверяем сигналы
        self.assertEqual(len(errors), 1)
        self.assertIn("Server returned status 500", errors[0])

    @patch("requests.get")
    def test_worker_exception_emits_error_occurred(self, mock_get):
        # 1. Мокаем сетевой сбой (таймаут)
        mock_get.side_effect = Exception("Connection Timeout")

        worker = NetworkStatusWorker("http://fake-server-url", timeout=1.0)
        
        errors = []
        def on_error(err):
            errors.append(err)
            
        worker.error_occurred.connect(on_error)

        # 2. Запускаем поток
        worker.start()
        worker.wait(2000)
        app.processEvents()

        # 3. Проверяем сигналы
        self.assertEqual(len(errors), 1)
        self.assertIn("Connection Timeout", errors[0])

if __name__ == "__main__":
    unittest.main()
