from __future__ import annotations

import os
from pathlib import Path

import pytest

from decouple import Config
from decouple import RepositorySecret

TEST_DIR = Path(__file__).parent


def test_secrets():
    path = TEST_DIR / 'secrets'
    config = Config(RepositorySecret(path))

    assert 'hello' == config('db_user')
    assert 'world' == config('db_password')


def test_no_secret_but_present_in_os_environ():
    path = TEST_DIR / 'secrets'
    config = Config(RepositorySecret(path))

    os.environ['KeyOnlyEnviron'] = 'SOMETHING'
    assert 'SOMETHING' == config('KeyOnlyEnviron')
    del os.environ['KeyOnlyEnviron']


def test_secret_overriden_by_environ():
    path = TEST_DIR / 'secrets'
    config = Config(RepositorySecret(path))

    os.environ['db_user'] = 'hi'
    assert 'hi' == config('db_user')
    del os.environ['db_user']


def test_secret_repo_keyerror():
    path = TEST_DIR / 'secrets'
    repo = RepositorySecret(path)

    with pytest.raises(KeyError):
        repo['UndefinedKey']
