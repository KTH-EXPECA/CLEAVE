import os
import pathlib
import shlex
import subprocess
from typing import List

cmd = 'sphinx-apidoc -M -fo ./source ..'

env = os.environ.copy()
env['SPHINX_APIDOC_OPTIONS'] = 'members,private-members,show-inheritance'


if __name__ == '__main__':
    # ignr = ' '.join(_recurse_files(pathlib.Path('..')))
    p = subprocess.run(
        shlex.split(f'{cmd} ../setup.py ../cleave.py ../tests/*'),
                       env=env)
