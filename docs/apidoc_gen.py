import subprocess
import shlex
import os

cmd = 'sphinx-apidoc -M -fo ./source .. ' \
      '../setup.py ' \
      '../cleave/client/base/actuator.py ' \
      '../cleave/client/base/sensor.py ' \
      '../cleave/client/base/plant.py ' \
      '../cleave/network/client.py ' \
      '../tests ' \
      '../examples'

env = os.environ.copy()
env['SPHINX_APIDOC_OPTIONS'] = 'members,private-members,show-inheritance'

if __name__ == '__main__':
    p = subprocess.run(shlex.split(cmd), env=env)

