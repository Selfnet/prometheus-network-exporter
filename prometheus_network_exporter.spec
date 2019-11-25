# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

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
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
          cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
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
