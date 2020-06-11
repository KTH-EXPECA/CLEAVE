#  Copyright (c) 2020 KTH Royal Institute of Technology
#
#  Licensed under the Apache License, Version 2.0 (the 'License');
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an 'AS IS' BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#   limitations under the License.
#
#  Licensed under the Apache License, Version 2.0 (the 'License');
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an 'AS IS' BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#   limitations under the License.

import setuptools

with open('cleave/client/README.md', 'r') as fp:
    client_desc = fp.read()

with open('cleave/backend/README.md', 'r') as fp:
    backend_desc = fp.read()

long_description = f'{client_desc}\n{backend_desc}'

setuptools.setup(
    name='cleave',
    version='0.0.1',
    author='KTH Royal Institute of Technology',  # TODO: Change?
    author_email='molguin@kth.se',  # TODO: Change?
    description='The CLEAVE (ControL bEnchmArking serVice on the Edge) '
                'framework for emulating and evaluating control applications '
                'on edge computing architectures.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url=None,  # TODO
    packages=setuptools.find_packages(),
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Topic :: System :: Networking',
        'Topic :: System :: Benchmark',
        'Topic :: System :: Emulators'
    ],
    python_requires='>=3.8',
)
