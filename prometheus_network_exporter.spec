# -*- mode: python ; coding: utf-8 -*-

added_files = [
    ('prometheus_network_exporter/collectors/junos/*.yaml', 'prometheus_network_exporter/collectors/junos'),
    ('prometheus_network_exporter/views/junos/*.yml', 'prometheus_network_exporter/views/junos')
]
a = Analysis(['prometheus_network_exporter/app.py'],
             pathex=['prometheus_junos_exporter'],
             binaries=[],
             datas=added_files,
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.datas,
          [],
          name='prometheus_network_exporter',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True)
