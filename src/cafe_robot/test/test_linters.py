# Copyright 2024 sundar
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

from ament_copyright.main import main
import pytest


@pytest.mark.copyright
@pytest.mark.linter
def test_copyright():
    rc = main(argv=['.', 'test'])
    assert rc == 0, 'Found errors'


from ament_flake8.main import main_with_errors


@pytest.mark.flake8
@pytest.mark.linter
def test_flake8():
    rc, errors = main_with_errors(argv=[])
    assert rc == 0, \
        'Found %d code style errors / warnings:\n' % len(errors) + \
        '\n'.join(errors)


from ament_pep257.main import main as pep257_main


@pytest.mark.pep257
@pytest.mark.linter
def test_pep257():
    rc = pep257_main(argv=['.', 'test'])
    assert rc == 0, 'Found code style errors / warnings'
