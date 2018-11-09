from __future__ import absolute_import
import re
import ast
import io
from setuptools import setup

_version_re = re.compile(r'__version__\s+=\s+(.*)')

with io.open('parasite/pa/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))

setup(
    name='pa',
    description='Parasite',
    version=version,
    install_requires=[
        'requests',
        'termcolor',
        'click'
    ],
    packages=[
        'pa',
        'pa.bin'
    ],
    package_dir={
        "pa": "parasite/pa",
        "pa.bin": "bin"
    },
    eager_resources=['sample/__manifest__.py'],
    package_data={
        '': ['sample/__manifest__.py']
    },
    include_package_data=True,
    entry_points={"console_scripts": ["pa=pa.bin:main"]},
    tests_require=['pytest'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],
)
