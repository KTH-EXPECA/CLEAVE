import os
import pathlib
import shlex
import subprocess
from typing import List

cmd = 'sphinx-apidoc -M -fo ./source ..'

env = os.environ.copy()
env['SPHINX_APIDOC_OPTIONS'] = 'members,private-members,show-inheritance'


# ignore all .py modules, just document packages
def _recurse_files(p: pathlib.Path) -> List[str]:
    if p.name == 'venv':
        return []
    elif p.is_file():
        if p.name.endswith('.py') and p.name != '__init__.py':
            return [str(pathlib.PurePosixPath(p))]
        else:
            return []
    else:
        results = []
        for child in p.iterdir():
            results += _recurse_files(child)
        return results


if __name__ == '__main__':
    ignr = ' '.join(_recurse_files(pathlib.Path('..')))
    p = subprocess.run(shlex.split(f'{cmd} {ignr}'), env=env)
