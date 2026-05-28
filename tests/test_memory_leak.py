#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import unittest
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import numpy as np
import nibabel as nib
import psutil
import gc


# Добавляем корень проекта в пути импорта
sys.path.append(str(Path(__file__).resolve().parent.parent))

from contour_engine import ContourEngine

class TestContourEngineMemoryLeak(unittest.TestCase):
    def setUp(self):
        self.dicom_dir = Path("test_memory_dicom")
        self.output_dir = Path("test_memory_output")
        self.dicom_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        
        # Создаем один минимальный фейковый DICOM файл, чтобы пройти валидацию структуры
        import pydicom
        from pydicom.dataset import FileDataset, FileMetaDataset
        
        filename = self.dicom_dir / "slice_0.dcm"
        file_meta = FileMetaDataset()
        file_meta.TransferSyntaxUID = pydicom.uid.ImplicitVRLittleEndian
        
        ds = FileDataset(str(filename), {}, file_meta=file_meta, preamble=b"\0" * 128)
        ds.PatientID = "TestPatient123"
        ds.PatientName = "Memory^Leak^Test"
        ds.StudyDate = "20260528"
        ds.SeriesInstanceUID = "1.2.3.4.5.6"
        ds.SOPInstanceUID = "1.2.3.4.5.6.1"
        ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.2"  # CT Image Storage
        ds.is_little_endian = True
        ds.is_implicit_VR = True
        ds.save_as(str(filename))

        self.engine = ContourEngine()

    def tearDown(self):
        # Удаляем временные файлы
        shutil.rmtree(self.dicom_dir, ignore_errors=True)
        shutil.rmtree(self.output_dir, ignore_errors=True)

    @patch("dicom2nifti.dicom_series_to_nifti")
    @patch("subprocess.Popen")
    @patch("rt_utils.RTStructBuilder.create_new")
    def test_run_pipeline_memory_stability(self, mock_create_new, mock_popen, mock_d2n):
        # 1. Настройка моков для обхода тяжелых вычислений
        # Имитируем успешный запуск dicom2nifti (создает пустой nifti-файл на диске)
        def fake_d2n(d_dir, out_path, reorient_nifti=False):
            # Создаем фейковый NIfTI файл
            data = np.zeros((30, 30, 30), dtype=np.int16)
            img = nib.Nifti1Image(data, np.eye(4))
            nib.save(img, out_path)
            
        mock_d2n.side_effect = fake_d2n
        
        # Имитируем запуск TotalSegmentator
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 0
        mock_proc.wait.return_value = 0
        mock_proc.stdout.readline.side_effect = ["", ""]
        mock_popen.return_value = mock_proc
        
        # Мокаем RTStructBuilder
        mock_rt = MagicMock()
        mock_rt.get_roi_names.return_value = ["UrinaryBladder"]
        mock_create_new.return_value = mock_rt
        
        # Патчим сохранение масок TotalSegmentator, имитируя создание файлов ИИ-масок
        def fake_totalseg(*args, **kwargs):
            # Создаем фейковую маску во временной папке сегментации
            temp_seg_dir = self.output_dir / "temp_autocontour_workspace" / "temp_masks"
            temp_seg_dir.mkdir(parents=True, exist_ok=True)
            
            mask_data = np.zeros((30, 30, 30), dtype=np.uint8)
            mask_data[10:20, 10:20, 10:20] = 1 # непустой ROI
            img = nib.Nifti1Image(mask_data, np.eye(4))
            nib.save(img, str(temp_seg_dir / "urinary_bladder.nii.gz"))
            return mock_proc
            
        mock_popen.side_effect = fake_totalseg

        # 2. Измеряем начальный объем RAM процесса
        process = psutil.Process(os.getpid())
        gc.collect()
        initial_memory = process.memory_info().rss
        
        # 3. Выполняем пайплайн в цикле несколько раз для выявления прогрессирующих утечек
        iterations = 4
        memories = []
        
        for idx in range(iterations):
            # Запуск пайплайна
            self.engine.run_pipeline(
                dicom_dir_path=str(self.dicom_dir),
                output_dir_path=str(self.output_dir),
                preset_name="Малый таз (Pelvis)",
                precision_mode="normal",
                use_gpu=False
            )
            
            # Чистим временные файлы вывода, чтобы не накапливать дисковый кэш в памяти OS
            shutil.rmtree(self.output_dir, ignore_errors=True)
            self.output_dir.mkdir(exist_ok=True)
            
            gc.collect()
            current_mem = process.memory_info().rss
            memories.append(current_mem)
            print(f"Итерация {idx + 1}: RAM = {current_mem / (1024*1024):.2f} MB")

        # 4. Проверяем стабильность потребления памяти
        # Память не должна бесконечно расти. Разница между последней и второй итерацией
        # должна стремиться к нулю (с учетом погрешности аллокатора кучи Python допуск 5 МБ)
        mem_diff = memories[-1] - memories[1]
        mem_diff_mb = mem_diff / (1024 * 1024)
        
        print(f"Разница в памяти между 4-й и 2-й итерациями: {mem_diff_mb:.2f} MB")
        self.assertTrue(
            mem_diff_mb < 5.0,
            f"Обнаружена утечка памяти! Потребление выросло на {mem_diff_mb:.2f} MB"
        )

if __name__ == "__main__":
    unittest.main()
