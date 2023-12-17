from __future__ import annotations

import re
from pathlib import Path

from setuptools import find_packages
from setuptools import setup

BASE_DIR = Path(__file__).resolve().parent


def load_version() -> str:
    file_path = BASE_DIR / 'decouple' / 'version.py'
    file_contents = file_path.read_text()
    version_regex = r"^__version__ = ['\"]([^'\"]*)['\"]"
    match = re.search(version_regex, file_contents, re.M)
    if match:
        return match.group(1)
    else:
        raise RuntimeError('Unable to find version string')


NAME = 'python-decouple-typed'
DESCRIPTION = 'Strict separation of settings from code.'
URL = 'https://github.com/kaas-mulvad/python-decouple-typed'
EMAIL = 'shmulvad@gmail.com'
AUTHOR = 'Søren Mulvad'
REQUIRES_PYTHON = '>=3.8.0'
REQUIRED: list[str] = []
VERSION = load_version()

README = BASE_DIR / 'README.rst'

setup(
    name='python-decouple-typed',
    version=VERSION,
    description='Typed strict separation of settings from code.',
    long_description=README.read_text(),
    long_description_content_type='text/x-rst',
    author=AUTHOR,
    author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,
    license='MIT',
    py_modules=['decouple'],
    zip_safe=False,
    platforms='any',
    install_requires=REQUIRED,
    package_data={'decouple': ['py.typed']},
    packages=find_packages(exclude=['tests', '*.tests', '*.tests.*', 'tests.*']),
    include_package_data=True,
    url=URL,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Framework :: Django',
        'Framework :: Flask',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries',
    ],
)
