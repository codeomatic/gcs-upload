#!/usr/bin/env python
# Helper script to add and push git tags from settings

import importlib.util
from shlex import split
from subprocess import Popen, TimeoutExpired
from pathlib import Path


def call(arg: str) -> Popen:
    return Popen(split(arg))


def main():
    base = Path(__file__).parent.absolute()
    spec = importlib.util.spec_from_file_location("app", Path(base, 'app/settings.py'))
    app = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app)

    add = call(f'git tag {app.version}')

    if add.wait():
        print(f'Failed to add tag {app.version}')
        return
    print(f'Tag {app.version} was added')

    push = call(f'git push --tags')
    try:
        returncode = push.wait(timeout=20)
    except TimeoutExpired:
        push.kill()
        returncode = 1

    if not returncode:
        print('success')
        return

    print(f'Pushing tag {app.version} failed')

    remove = call(f'git tag --delete {app.version}')
    remove.wait()


if __name__ == '__main__':
    main()
