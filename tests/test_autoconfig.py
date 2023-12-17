from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import mock_open
from unittest.mock import patch

import pytest

from decouple import AutoConfig
from decouple import RepositoryEmpty
from decouple import UndefinedValueError
from decouple.decouple import DEFAULT_ENCODING

TEST_DIR = Path(__file__).parent


def test_autoconfig_env():
    config = AutoConfig()
    path = TEST_DIR / 'autoconfig' / 'env' / 'project'
    with patch.object(config, '_caller_path', return_value=path):
        assert 'ENV' == config('KEY')


def test_autoconfig_ini():
    config = AutoConfig()
    path = TEST_DIR / 'autoconfig' / 'ini' / 'project'
    with patch.object(config, '_caller_path', return_value=path):
        assert 'INI' == config('KEY')


def test_autoconfig_ini_in_subdir():
    """
    When `AutoConfig._find_file()` gets a relative path from
    `AutoConfig._caller_path()`, it will not properly search back to parent
    dirs.

    This is a regression test to make sure that when
    `AutoConfig._caller_path()` finds something like `./config.py` it will look
    for settings.ini in parent directories.
    """
    config = AutoConfig()
    subdir = TEST_DIR / 'autoconfig' / 'ini' / 'project' / 'subdir'
    os.chdir(subdir)
    path = subdir / 'empty.py'
    with patch.object(config, '_caller_path', return_value=path):
        assert 'INI' == config('KEY')


def test_autoconfig_none():
    os.environ['KeyFallback'] = 'On'
    config = AutoConfig()
    # path = os.path.join(os.path.dirname(__file__), 'autoconfig', 'none')
    with patch('decouple.decouple.Path.is_file', return_value=False):
        assert True is config('KeyFallback', cast=bool)
    del os.environ['KeyFallback']


def test_autoconfig_exception():
    os.environ['KeyFallback'] = 'On'
    config = AutoConfig()
    with patch(
        'decouple.decouple.Path.is_file', side_effect=Exception('PermissionDenied')
    ):
        assert True is config('KeyFallback', cast=bool)
    del os.environ['KeyFallback']


def test_autoconfig_is_not_a_file():
    os.environ['KeyFallback'] = 'On'
    config = AutoConfig()
    with patch('decouple.decouple.Path.is_file', return_value=False):
        assert True is config('KeyFallback', cast=bool)
    del os.environ['KeyFallback']


def test_autoconfig_search_path():
    path = TEST_DIR / 'autoconfig' / 'env' / 'custom-path'
    config = AutoConfig(path)
    assert 'CUSTOMPATH' == config('KEY')


def test_autoconfig_empty_repository():
    path = TEST_DIR / 'autoconfig' / 'env' / 'custom-path'
    config = AutoConfig(path)

    with pytest.raises(UndefinedValueError):
        config('KeyNotInEnvAndNotInRepository')

    assert isinstance(config.config.repository, RepositoryEmpty)


def test_autoconfig_ini_default_encoding():
    config = AutoConfig()
    path = TEST_DIR / 'autoconfig' / 'ini' / 'project'
    # filename = TEST_DIR / 'autoconfig' / 'ini' / 'project' / 'settings.ini'

    with patch.object(config, '_caller_path', return_value=path):
        with patch('decouple.decouple.Path.open', mock_open(read_data='')) as mopen:
            assert config.encoding == DEFAULT_ENCODING
            assert 'ENV' == config('KEY', default='ENV')
            mopen.assert_called_once_with(encoding=DEFAULT_ENCODING)


def test_autoconfig_env_default_encoding():
    config = AutoConfig()
    path = TEST_DIR / 'autoconfig' / 'env' / 'project'
    # filename = TEST_DIR / 'autoconfig' / 'env' / '.env'
    with patch.object(config, '_caller_path', return_value=path):
        with patch('decouple.decouple.Path.open', mock_open(read_data='')) as mopen:
            assert config.encoding == DEFAULT_ENCODING
            assert 'ENV' == config('KEY', default='ENV')
            mopen.assert_called_once_with(encoding=DEFAULT_ENCODING)


def test_autoconfig_no_repository():
    path = TEST_DIR / 'autoconfig' / 'ini' / 'no_repository'
    config = AutoConfig(path)

    with pytest.raises(UndefinedValueError):
        config('KeyNotInEnvAndNotInRepository')

    assert isinstance(config.config.repository, RepositoryEmpty)
