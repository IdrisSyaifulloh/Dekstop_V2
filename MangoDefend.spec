# -*- mode: utf-8 -*-
import os
import glob
import sys

import PySide6
import shiboken6

block_cipher = None

pyside6_dir = PySide6.__path__[0]
shiboken6_dir = shiboken6.__path__[0]
python_dir = os.path.dirname(sys.executable)

# Semua DLL PySide6 dan shiboken6 → langsung ke root _internal (bukan subfolder)
# agar Windows bisa resolve tanpa perlu PATH trick
pyside6_dlls = [(f, '.') for f in glob.glob(os.path.join(pyside6_dir, '*.dll'))]
shiboken6_dlls = [(f, '.') for f in glob.glob(os.path.join(shiboken6_dir, '*.dll'))]
python_dlls = [(f, '.') for f in glob.glob(os.path.join(python_dir, 'vcruntime*.dll'))]
ucrt_dll = [(r'C:\Windows\System32\ucrtbase.dll', '.')] if os.path.exists(r'C:\Windows\System32\ucrtbase.dll') else []

# opengl32sw wajib untuk VM tanpa GPU
opengl_dll = [(os.path.join(pyside6_dir, 'opengl32sw.dll'), '.')]

# Plugins PySide6 tetap di subfolder PySide6/plugins
pyside6_plugins = [(f, 'PySide6/plugins')
                   for f in glob.glob(os.path.join(pyside6_dir, 'plugins', '**', '*'), recursive=True)
                   if os.path.isfile(f)]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=pyside6_dlls + shiboken6_dlls + python_dlls + ucrt_dll + opengl_dll,
    datas=[
        ('assets',    'assets'),
        ('models',    'models'),
        ('config.ini','.'),
        (os.path.join(pyside6_dir, 'plugins'), 'PySide6/plugins'),
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtNetwork',
        'onnxruntime',
        'onnxruntime.capi',
        'onnxruntime.capi.onnxruntime_pybind11_state',
        'watchdog',
        'watchdog.observers',
        'watchdog.observers.winapi',
        'watchdog.events',
        'psutil',
        'PIL',
        'PIL.Image',
        'numpy',
        'requests',
        'urllib3',
        'zipfile',
        'rarfile',
        'py7zr',
        'winreg',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets',
        'torch', 'torchvision', 'matplotlib', 'tkinter',
        'unittest', 'xmlrpc', 'pydoc',
    ],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MangoDefend',
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon='assets/icon.ico',
    uac_admin=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='MangoDefend',
)
