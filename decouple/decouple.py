from __future__ import annotations

import os
import string
import sys
from collections import OrderedDict
from configparser import ConfigParser
from configparser import NoOptionError
from pathlib import Path
from shlex import shlex
from typing import Any
from typing import Callable
from typing import Generic
from typing import TypeVar
from typing import overload

T = TypeVar('T')

DEFAULT_ENCODING = 'UTF-8'

TRUE_VALUES = {'y', 'yes', 't', 'true', 'on', '1'}
FALSE_VALUES = {'n', 'no', 'f', 'false', 'off', '0'}


def strtobool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value

    value = value.lower()
    if value in TRUE_VALUES:
        return True
    elif value in FALSE_VALUES:
        return False

    raise ValueError(f'Invalid truth value: {value!r}')


class UndefinedValueError(Exception):
    pass


class Undefined:
    """
    Class to represent undefined type.
    """


# Reference instance to represent undefined values
undefined = Undefined()


class RepositoryEmpty:
    def __init__(
        self,
        source: str | Path = '',
        encoding: str = DEFAULT_ENCODING,
    ) -> None:
        pass

    def __contains__(self, key: str) -> bool:
        return False

    def __getitem__(self, key: str) -> str:
        raise NotImplementedError


def _cast_boolean(value: Any) -> bool:
    """
    Helper to convert config values to boolean as ConfigParser do.
    """
    value = str(value)
    return bool(value) if value == '' else strtobool(value)


class Config:
    """
    Handle .env file format used by Foreman.
    """

    def __init__(self, repository: RepositoryEmpty) -> None:
        self.repository: RepositoryEmpty = repository

    @staticmethod
    def _cast_do_nothing(value: T) -> T:
        return value

    @overload
    def get(  # type: ignore
        self,
        option: str,
        default: Undefined = ...,
        cast: Undefined = ...,
    ) -> str: ...

    @overload
    def get(self, option: str, default: T, cast: Undefined = ...) -> T: ...

    @overload
    def get(
        self,
        option: str,
        default: Undefined = ...,
        cast: Callable[[str], T] = ...,  # type: ignore
    ) -> T: ...

    @overload
    def get(self, option: str, default: T, cast: Callable[[str], T]) -> T: ...

    def get(
        self,
        option: str,
        default: Undefined | T = undefined,
        cast: Undefined | Callable[[str], T] = undefined,
    ) -> T | str:
        """
        Return the value for option or default if defined.
        """
        # We can't avoid __contains__ because value may be empty.
        value: T | str | None = None
        if option in os.environ:
            value = os.environ[option]
        elif option in self.repository:
            value = self.repository[option]
        else:
            if isinstance(default, Undefined):
                msg = (
                    f'{option!r} not found. '
                    'Declare it as envvar or define a default value.'
                )
                raise UndefinedValueError(msg)

            if not isinstance(default, str):
                return default

            value = default

        if isinstance(cast, Undefined):
            return value
        elif cast is bool:
            cast = _cast_boolean  # type: ignore

        assert not isinstance(cast, Undefined)

        msg = f"You're trying to cast a value of type {type(value)}"
        assert isinstance(value, str), msg
        return cast(value)

    __call__ = get


class RepositoryIni(RepositoryEmpty):
    """
    Retrieves option keys from .ini files.
    """

    SECTION = 'settings'

    def __init__(self, source: str | Path, encoding: str = DEFAULT_ENCODING) -> None:
        self.parser = ConfigParser()
        with Path(source).open(encoding=encoding) as file_:
            self.parser.read_file(file_)

    def __contains__(self, key: str) -> bool:
        return key in os.environ or self.parser.has_option(self.SECTION, key)

    def __getitem__(self, key: str) -> str:
        try:
            return self.parser.get(self.SECTION, key)
        except NoOptionError:
            raise KeyError(key)


class RepositoryEnv(RepositoryEmpty):
    """
    Retrieves option keys from .env files with fall back to os.environ.
    """

    def __init__(self, source: str | Path, encoding: str = DEFAULT_ENCODING) -> None:
        self.data: dict[str, str] = {}

        with Path(source).open(encoding=encoding) as file_:
            for line in file_:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                k = k.strip()
                v = v.strip()
                if len(v) >= 2 and (
                    (v[0] == "'" and v[-1] == "'") or (v[0] == '"' and v[-1] == '"')
                ):
                    v = v[1:-1]
                self.data[k] = v

    def __contains__(self, key: str) -> bool:
        return key in os.environ or key in self.data

    def __getitem__(self, key: str) -> str:
        return self.data[key]


class RepositorySecret(RepositoryEmpty):
    """
    Retrieves option keys from files,
    where title of file is a key, content of file is a value
    e.g. Docker swarm secrets
    """

    def __init__(self, source: str | Path = '/run/secrets/') -> None:
        self.data: dict[str, str] = {}

        for file in Path(source).iterdir():
            with file.open('r') as f:
                self.data[file.name] = f.read()

    def __contains__(self, key: str) -> bool:
        return key in os.environ or key in self.data

    def __getitem__(self, key: str) -> str:
        return self.data[key]


class AutoConfig:
    """
    Autodetects the config file and type.

    Parameters
    ----------
    search_path : str, path, optional
        Initial search path. If empty, the default search path is the
        caller's path.
    """

    SUPPORTED: dict[str, type[RepositoryEmpty]] = OrderedDict([  # noqa: RUF012
        ('settings.ini', RepositoryIni),
        ('.env', RepositoryEnv),
    ])

    encoding = DEFAULT_ENCODING

    def __init__(self, search_path: str | Path | None = None) -> None:
        self.search_path = search_path
        self.config: Config | None = None

    def _find_file(self, path: str | Path) -> Path | str:
        # look for all files in the current path
        path = Path(path).resolve()
        for config_file in self.SUPPORTED:
            file_path = path / config_file
            if file_path.is_file():
                return file_path

        # search the parent
        parent = path.parent
        root_dir = Path(os.sep).resolve()
        if parent and os.path.normcase(parent) != root_dir:
            return self._find_file(parent)

        # reached root without finding any files.
        return ''

    def _load(self, path: str | Path) -> None:
        # Avoid unintended permission errors
        try:
            filename = self._find_file(Path(path).resolve())
        except Exception:
            filename = ''

        Repository = self.SUPPORTED.get(Path(filename).name, RepositoryEmpty)  # noqa: N806
        self.config = Config(Repository(filename, encoding=self.encoding))

    def _caller_path(self) -> Path:
        # MAGIC! Get the caller's module path.
        frame = sys._getframe()
        path = Path(frame.f_back.f_back.f_code.co_filename).parent  # type: ignore
        return path

    @overload
    def __call__(  # type: ignore
        self, option: str, default: Undefined = ..., cast: Undefined = ...
    ) -> str: ...

    @overload
    def __call__(self, option: str, default: T, cast: Undefined = ...) -> str | T: ...

    @overload
    def __call__(
        self,
        option: str,
        default: Undefined = ...,
        cast: Callable[[str], T] = ...,  # type: ignore
    ) -> T: ...

    @overload
    def __call__(self, option: str, default: T, cast: Callable[[str], T]) -> T: ...

    def __call__(
        self,
        option: str,
        default: T | Undefined = undefined,
        cast: Callable[[str], T] | Undefined = undefined,
    ) -> T | str:
        if self.config is None:
            self._load(self.search_path or self._caller_path())

        assert self.config is not None, 'Config not loaded'
        return self.config.get(option, default=default, cast=cast)


# A pré-instantiated AutoConfig to improve decouple's usability
# now just import config and start using with no configuration.
config = AutoConfig()

# Helpers


class Csv(Generic[T]):
    """
    Produces a csv parser that return a list of transformed elements.
    """

    def __init__(
        self,
        cast: Callable[[str], T] = str,  # type: ignore
        delimiter: str = ',',
        strip: str = string.whitespace,
    ) -> None:
        """
        Parameters:
        cast -- callable that transforms the item just before it's added to the list.
        delimiter -- string of delimiters chars passed to shlex.
        strip -- string of non-relevant characters to be passed to str.strip after the
        split.
        post_process -- callable to post process all casted values. Default is `list`.
        """
        self.cast = cast
        self.delimiter = delimiter
        self.strip = strip

    def __call__(self, value: str | None) -> list[T]:
        """The actual transformation"""
        if value is None:
            return []

        def transform(s: str) -> T:
            return self.cast(s.strip(self.strip))

        splitter = shlex(value, posix=True)
        splitter.whitespace = self.delimiter
        splitter.whitespace_split = True
        return [transform(s) for s in splitter]


class Choices(Generic[T]):
    """
    Allows for cast and validation based on a list of choices.
    """

    def __init__(
        self,
        flat: list[T] | None = None,
        cast: Callable[[str], T] = str,  # type: ignore
        choices: tuple[tuple[T, Any], ...] | None = None,
    ) -> None:
        """
        Parameters:
        flat -- a flat list of valid choices.
        cast -- callable that transforms value before validation.
        choices -- tuple of Django-like choices.
        """
        self.flat = flat or []
        self.cast = cast
        self.choices = choices or ()

        self._valid_values = []
        self._valid_values.extend(self.flat)
        self._valid_values.extend([value for value, _ in self.choices])

    def __call__(self, value: str) -> T:
        transform = self.cast(value)
        if transform in self._valid_values:
            return transform

        raise ValueError(
            f'Value not in list: {value!r}; valid values are {self._valid_values!r}'
        )
