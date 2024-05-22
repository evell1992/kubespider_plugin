#! /bin/sh
cd nexus
pyinstaller -F provider.py --distpath=bin --collect-all=kubespider_plugin --clean
rm -rf build
rm -rf rm provider.spec