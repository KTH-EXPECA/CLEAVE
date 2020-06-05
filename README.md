# CLEAVE Project Metarepo
---

This metarepository contains all the repositories associated with the CLEAVE project for easy organization and maintenance.

## Cloning:

To clone the whole project at once:

```bash
git clone --recurse-submodules -j8 git@github.com:KTH-EXPECA/CLEAVE.git
```

or 

```bash
git clone git@github.com:KTH-EXPECA/CLEAVE.git
cd CLEAVE
git submodule update --init --recursive
```

For instructions on how to clone individual submodules, head to the respective Git repository pages.

## License

Copyright 2020 KTH Royal Institute of Technology

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this project except in compliance with the License. A copy of the license is included in the [LICENSE](LICENSE) file.

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
