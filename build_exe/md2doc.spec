# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:\\project\\helper\\helper_md_doc\\build_exe\\entry_md2doc.py'],
    pathex=[],
    binaries=[('C:\\Users\\sw1\\anaconda3\\Scripts\\pandoc.EXE', '.')],
    datas=[('C:\\Users\\sw1\\AppData\\Local\\ms-playwright\\chromium-1208', 'playwright_browsers/chromium-1208'), ('D:\\project\\helper\\helper_md_doc\\src\\helper_md_doc\\katex', 'helper_md_doc/katex'), ('D:\\project\\helper\\helper_md_doc\\src\\helper_md_doc\\mermaid', 'helper_md_doc/mermaid'), ('D:\\project\\helper\\helper_md_doc\\src\\helper_md_doc\\D2Coding.ttc', 'helper_md_doc'), ('C:\\Users\\sw1\\anaconda3\\envs\\py311_helper\\Lib\\site-packages\\latex2mathml\\unimathsymbols.txt', 'latex2mathml'), ('D:\\project\\helper\\helper_md_doc\\src\\helper_md_doc\\reference.docx', 'helper_md_doc')],
    hiddenimports=['playwright.sync_api', 'playwright.async_api', 'playwright._impl._api_types', 'playwright._impl._connection', 'pypandoc', 'markdown', 'markdown.extensions.fenced_code', 'markdown.extensions.tables', 'latex2mathml', 'latex2mathml.converter', 'latex2mathml.symbols_parser', 'latex2mathml.tokenizer', 'latex2mathml.walker', 'latex2mathml.node', 'latex2mathml.exceptions', 'PIL', 'PIL.Image', 'PIL.ImageChops', 'helper_md_doc', 'helper_md_doc.requirements_rnac', 'helper_md_doc.helper_md_html', 'helper_md_doc.helper_html_doc', 'helper_md_doc.helper_md_doc', 'helper_md_doc.helper_md_text', 'helper_md_doc.helper_html_md', 'helper_md_doc.helper_doc_html', 'helper_md_doc.helper_md_pdf', 'helper_md_doc.helper_html_pdf'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'pandas'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='md2doc',
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
)
