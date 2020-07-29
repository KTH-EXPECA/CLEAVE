import subprocess
import shlex
import os

cmd = 'sphinx-apidoc.exe -M -fo ./source .. ' \
      '../setup.py ' \
      '../cleave/client/actuator.py ' \
      '../cleave/client/sensor.py ' \
      '../cleave/client/plant.py ' \
      '../cleave/network/handler.py ' \
      '../tests ' \
      '../examples'

env = os.environ.copy()
env['SPHINX_APIDOC_OPTIONS'] = 'members,private-members,show-inheritance'

if __name__ == '__main__':
    p = subprocess.run(shlex.split(cmd), env=env)

