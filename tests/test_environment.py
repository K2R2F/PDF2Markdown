import importlib.metadata
from io import BytesIO
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from environment import detection, downloads, installer, jobs


class EnvironmentTests(unittest.TestCase):
    def test_missing_onnx_is_not_ready(self):
        def version(name):
            if name == 'onnxruntime':
                raise importlib.metadata.PackageNotFoundError(name)
            return '1.0'
        with patch.object(detection.importlib.metadata, 'version', side_effect=version), patch.object(detection, 'tesseract_path', return_value=None):
            report = detection.inspect_environment()
        self.assertFalse(report['rapidocr']['ready'])
        self.assertEqual(report['rapidocr']['missing'], ['onnxruntime'])
        self.assertFalse(report['tesseract']['ready'])

    def test_tesseract_missing_japanese_data(self):
        outputs = [subprocess.CompletedProcess([], 0, 'tesseract 5.4\n', ''),
                   subprocess.CompletedProcess([], 0, 'List of languages:\neng\nosd\n', '')]
        with patch.object(detection, 'tesseract_path', return_value=Path('tesseract.exe')), patch.object(detection, 'run', side_effect=outputs):
            report = detection.inspect_environment()['tesseract']
        self.assertFalse(report['ready'])
        self.assertIn('jpn', report['missing'])

    def test_checksum_mismatch_prevents_installer_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'installer.exe'
            with patch.object(downloads.urllib.request, 'urlopen', return_value=BytesIO(b'not the installer')):
                with self.assertRaises(ValueError):
                    downloads.download('https://example.org/installer', path, '0' * 64)
            self.assertFalse(path.exists())
            self.assertFalse(path.with_suffix('.exe.part').exists())

    def test_pip_failure_propagates_and_uses_current_python(self):
        with patch.object(installer, 'inspect_environment', return_value={'rapidocr': {'ready': False}}), \
             patch.object(installer, 'run', side_effect=subprocess.CalledProcessError(1, ['pip'])) as command:
            with self.assertRaises(subprocess.CalledProcessError):
                installer.install_component('rapidocr')
        args = command.call_args.args[0]
        self.assertEqual(args[:4], [installer.sys.executable, '-m', 'pip', 'install'])
        self.assertIn('onnxruntime==1.30.0', args)

    def test_existing_package_is_verified_without_reinstall(self):
        with patch.object(installer, 'inspect_environment', return_value={'easyocr': {'ready': True}}), patch.object(installer, 'run') as command:
            installer.install_component('easyocr')
        self.assertEqual(command.call_count, 1)
        self.assertEqual(command.call_args.args[0][1], '-c')

    def test_new_tesseract_configuration_is_picked_up(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for lang in detection.LANGUAGES:
                (root / f'{lang}.traineddata').write_bytes(b'model')
            with patch.object(detection, 'TESSDATA', root), patch.object(detection, 'tesseract_path', return_value=root / 'tesseract.exe'):
                config = detection.tesseract_configuration()
            self.assertEqual(config['path'], str(root))
            self.assertEqual(config['tesseract_cmd'], str(root / 'tesseract.exe'))

    @unittest.skipUnless(installer.os.name == 'nt', 'Windows installer flow')
    def test_tesseract_install_downloads_verified_installer_then_languages(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = root / 'tesseract' / 'tesseract.exe'
            with patch.object(installer, 'RUNTIME', root), patch.object(installer, 'TESSDATA', root / 'tessdata'), \
                 patch.object(installer, 'TESS_EXE', executable), \
                 patch.object(installer, 'tesseract_path', side_effect=[None, executable]), \
                 patch.object(installer.platform, 'machine', return_value='AMD64'), \
                 patch.object(installer, 'download') as download, patch.object(installer, 'run') as run, \
                 patch.object(installer, 'inspect_environment', return_value={'tesseract': {'ready': True}}):
                installer.install_component('tesseract')
            self.assertEqual(download.call_args_list[0].args[2], installer.INSTALLER_SHA256)
            self.assertEqual(download.call_count, 5)
            self.assertIn(str(installer.ROOT / 'install_tesseract.ps1'), run.call_args.args[0])
            self.assertIn(str(executable.parent), run.call_args.args[0])

    def test_only_fixed_components_and_single_operation(self):
        with self.assertRaises(ValueError):
            jobs.start_setup('something; whoami')
        with jobs.OPERATION_LOCK:
            with self.assertRaises(RuntimeError):
                jobs.start_setup('easyocr')

    def test_setup_worker_entry_and_completion_release_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(jobs, 'RUNTIME', Path(directory)), \
                 patch.object(jobs.subprocess, 'Popen') as spawn, \
                 patch.object(jobs.threading, 'Thread') as thread:
                spawn.return_value.wait.return_value = 0
                try:
                    jobs.start_setup('rapidocr')
                    command = spawn.call_args.args[0]
                    self.assertEqual(command, [jobs.sys.executable, '-u',
                        str(jobs.ROOT / 'environment_support.py'), 'rapidocr'])
                    self.assertTrue(Path(command[2]).is_file())
                    self.assertEqual(jobs.job_snapshot()['state'], 'running')
                    self.assertTrue(jobs.OPERATION_LOCK.locked())
                    thread.call_args.kwargs['target']()
                    self.assertEqual(jobs.job_snapshot()['state'], 'success')
                    self.assertFalse(jobs.OPERATION_LOCK.locked())
                finally:
                    jobs.JOB.clear()
                    if jobs.OPERATION_LOCK.locked():
                        jobs.OPERATION_LOCK.release()
