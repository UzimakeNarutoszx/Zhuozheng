import PyInstaller.__main__
from pathlib import Path

#desktop = str(Path.home()) + '/Desktop' # 取得桌面路径
'''
打包前再将要打包的作品前添加：
import os
import sys

# resource
base_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
os.chdir(base_dir)
'''

PyInstaller.__main__.run([
    #'--distpath=' + str(desktop) + '/codemao/dist',  # 指定应用程序输出目录为桌面-codemao-dist
    #'--workpath=' + str(desktop) + '/codemao/build',  # 指定过程生成文件位于桌面-codemao-build
    'main.py',  # 需要打包的Python程序
    '--add-data=images;images',  # 资源文件
    '--add-data=临时文件;临时文件',
    '--add-data=files;files',
    '--add-data=范例图片;范例图片',
    '-n=拙政园中的造景手法',  # 设置app或者exe名称
    '-w',  # Mac打包为app；Windows打包为文件夹
    '-i=images/图标.ico',  # 设置app或者exe图标
    '-y',  # 替换输出目录
])