#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
================================================================================
Модуль api_client.py: Фоновый асинхронный клиент для взаимодействия с сервером
================================================================================
"""

from PyQt6.QtCore import QThread, pyqtSignal
import requests

class NetworkStatusWorker(QThread):
    """Фоновый поток для неподвешивающего опроса состояния сервера автооконтурирования."""
    status_received = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, server_url: str, timeout: float = 2.0, client_id: str = "Неизвестный клиент"):
        super().__init__()
        self.server_url = server_url
        self.timeout = timeout
        self.client_id = client_id

    def run(self):
        try:
            # Выполняем сетевой запрос в фоновом потоке, не замораживая UI
            headers = {"X-Client-ID": self.client_id}
            response = requests.get(f"{self.server_url}/api/server/status", timeout=self.timeout, headers=headers)
            if response.status_code == 200:
                self.status_received.emit(response.json())
            else:
                self.error_occurred.emit(f"Server returned status {response.status_code}")
        except Exception as e:
            self.error_occurred.emit(str(e))
