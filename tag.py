#!/usr/bin/env python
# Helper script to add and push git tags from settings

import importlib.util
from shlex import split
from subprocess import Popen, TimeoutExpired
from pathlib import Path


def call(arg: str) -> Popen:
    return Popen(split(arg))


def main():
    current = Path(__file__).parent.absolute()
    base = current.parent
    spec = importlib.util.spec_from_file_location("app", Path(base, 'app/main.py'))
    app = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app)

    add = call(f'git tag {app.__version__}')

    if add.wait():
        print(f'Failed to add tag {app.__version__}')
        return
    print(f'Tag {app.__version__} was added')

    push = call(f'git push --tags')
    try:
        returncode = push.wait(timeout=5)
    except TimeoutExpired:
        push.kill()
        returncode = 1

    if not returncode:
        print('success')
        return

    print(f'Pushing tag {app.__version__} failed')

    remove = call(f'git tag --delete {app.__version__}')
    remove.wait()


if __name__ == '__main__':
    main()
