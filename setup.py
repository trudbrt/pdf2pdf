#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
You feed it a pdf-file, it returns a pdf-file.
Meant to be used along with a Jupyter-Notebook.
"""

from setuptools import setup

setup(
        name='pdf2pdf',
        version='1.0.0',
        description='takes a pdf gives a pdf',
        licence=open('LICENSE').read(),
        author='Yours truly',
        author_email='thmartaf@protonmail.com',
        url='https://github.com/trudbrt/pdf2pdf',
        packages=['pdf2pdf'])
