#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
================================================================================
Модуль main.py: Точка входа для запуска REST API сервера AI Contour
================================================================================
"""

import os
import sys
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Добавляем корень проекта в пути импорта
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Настройка логирования бэкенда
try:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
except Exception:
    pass

log_formatter = logging.Formatter('[%(asctime)s] %(levelname)s [%(name)s]: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%H:%M:%S'))
stream_handler.setLevel(logging.INFO)

try:
    file_handler = RotatingFileHandler(
        Path("logs/server_backend.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=2,
        encoding="utf-8"
    )
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.INFO)
except Exception:
    file_handler = None

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers = []
root_logger.addHandler(stream_handler)
if file_handler:
    root_logger.addHandler(file_handler)

import uvicorn
from server.server_api import app

if __name__ == "__main__":
    host = "0.0.0.0"
    port = 8000
    
    if os.name == 'nt':
        try:
            import subprocess
            netstat_out = subprocess.check_output("netstat -ano | findstr :8000", shell=True, text=True)
            pids_to_kill = set()
            current_pid = str(os.getpid())
            for line in netstat_out.strip().split("\n"):
                parts = [p.strip() for p in line.split(" ") if p.strip()]
                # netstat line format on Russian/English OS: Protocol Local-Address Foreign-Address State PID
                if len(parts) >= 5:
                    pid = parts[-1]
                    if pid.isdigit() and pid != current_pid:
                        pids_to_kill.add(pid)
            
            for pid in pids_to_kill:
                subprocess.run(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    print(f"Запуск веб-сервера AI Contour на http://{host}:{port}...")
    uvicorn.run(app, host=host, port=port, log_level="warning")
