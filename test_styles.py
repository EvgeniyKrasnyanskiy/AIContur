#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import unittest
from pathlib import Path

# Добавляем корень проекта в пути импорта
sys.path.append(str(Path(__file__).resolve().parent))

from src.ui.styles import StyleManager

class TestStyleManager(unittest.TestCase):
    def test_get_dark_theme_not_empty(self):
        theme = StyleManager.get_dark_theme()
        self.assertIsNotNone(theme)
        self.assertTrue(len(theme.strip()) > 0, "Тема оформления пуста!")

    def test_get_dark_theme_contains_qss_syntax(self):
        theme = StyleManager.get_dark_theme()
        # Проверяем наличие ключевых селекторов и свойств QSS
        self.assertIn("QWidget", theme)
        self.assertIn("background-color:", theme)
        self.assertIn("color:", theme)
        self.assertIn("QPushButton", theme)
        self.assertIn("QTabWidget::pane", theme)

if __name__ == "__main__":
    unittest.main()
