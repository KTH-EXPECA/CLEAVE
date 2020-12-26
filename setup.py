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

import setuptools

with open('./README.md', 'r') as fp:
    long_description = fp.read()

with open('./requirements.txt', 'r') as fp:
    reqs = fp.readlines()

with open('./requirements_viz.txt', 'r') as fp:
    viz_reqs = fp.readlines()

with open('./requirements_docs.txt', 'r') as fp:
    doc_reqs = fp.readlines()

setuptools.setup(
    name='cleave',
    version='0.1.0a',
    author='KTH Royal Institute of Technology',  # TODO: Change?
    author_email='molguin@kth.se',  # TODO: Change?
    description='The CLEAVE (ControL bEnchmArking serVice on the Edge) '
                'framework for emulating and evaluating control applications '
                'on edge computing architectures.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/KTH-EXPECA/CLEAVE',
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
    install_requires=reqs,
    extras_require={
        'viz' : viz_reqs,
        'docs': doc_reqs
    },
    python_requires='>=3.8',
)
