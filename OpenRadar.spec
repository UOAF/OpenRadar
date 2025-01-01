# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

from glfw import __file__ as glfw_path
from OpenGL import __file__ as opengl_path
import os


def get_glfw_dll():
    return os.path.join(os.path.dirname(glfw_path), 'glfw3.dll')


def get_opengl_dlls():
    return os.path.join(os.path.dirname(opengl_path), 'DLLS', '*.dll')


a = Analysis(
    ['src\\OpenRadar.py'],
    pathex=[],
    binaries=[(get_glfw_dll(), '.'), (get_opengl_dlls(), '.')],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

a.datas += Tree('resources', prefix='resources')

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.datas, [],
          name='OpenRadar',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True,
          disable_windowed_traceback=False,
          argv_emulation=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None,
          icon='resources\\icons\\OpenRadar_icon.ico')
