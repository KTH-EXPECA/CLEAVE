.. _installation_gen:

Installation
############

Installation for general usage
==============================

**NOTE: Although these instructions will eventually be the recommended way of downloading and installing the framework, they are currently a work-in-progress, and do not work yet. For failsafe ways to install the framework, see section** :ref:`installation_dev` **below.**

From PyPI
----------

1. Set up a Python :code:`virtualenv` and activate it:

.. code-block:: bash

    $ virtualenv --python=python3.8 ./venv
    created virtual environment CPython3.8.3.final.0-64 in 212ms
    $ . ./venv/bin/activate
    (venv) $

2. Next, install the framework from PyPI using :code:`pip`:

.. code-block:: bash

    (venv) $ pip install cleave

3. Alternatively, if you already have set up a project with an associated virtualenv, you can add :code:`cleave` to your :code:`requirements.txt` :

.. code-block:: text

    # example requirements.txt
    ...
    numpy
    pandas
    cleave
    scipy


.. code-block:: bash

    (venv) $ pip install -Ur ./requirements.txt

From the repository
-------------------

1. Set up a :code:`virtualenv` and activate it as before:

.. code-block:: bash

    $ virtualenv --python=python3.8 ./venv
    created virtual environment CPython3.8.3.final.0-64 in 212ms
    $ . ./venv/bin/activate
    (venv) $

2. Install the package through :code:`pip` by explicitly pointing it toward the repository:

.. code-block:: bash

    (venv) $ pip install -U git+git://github.com/KTH-EXPECA/CLEAVE.git#egg=cleave

3. This can also be inserted into a :code:`requirements.txt` file:

.. code-block:: text

    # example requirements.txt
    ...
    numpy
    pandas
    -e git://github.com/KTH-EXPECA/CLEAVE.git#egg=cleave
    scipy

.. _installation_dev:

Installation for development
============================

1. Clone the CLEAVE repository:

.. code-block:: bash

   $ git clone git@github.com:KTH-EXPECA/CLEAVE.git
   $ cd ./CLEAVE

2.  Create a Python 3.8+ :code:`virtualenv` and install the development dependencies:

.. code-block:: bash

    $ virtualenv --python=python3.8 ./venv
    created virtual environment CPython3.8.3.final.0-64 in 212ms
    ...

    $ . ./venv/bin/activate
    (venv) $ pip install -Ur ./requirements.txt
    ...

(Optional) Set up the Sphinx documentation environment
------------------------------------------------------

1. Install the documentation dependencies:

.. code-block:: bash

  (venv) $ pip install -Ur requirements_docs.txt

2. Document code using the Numpy docstring format (see below).

3. Generate reStructured text files for the code by running :code:`sphinx-apidocs` from the top-level directory and passing it the output directory (:code:`docs/source`) and the :code:`cleave` package directory as arguments:

.. code-block:: bash

    $ sphinx-apidoc -fo docs/source ./cleave

4. Finally, to preview what the documentation will look like when published on `readthedocs <https://cleave.readthedocs.io>`_, build it with :code:`GNU Make`:

.. code-block:: bash

    $ cd docs/
    $ make html


The compiled HTML structure will be output to :code:`docs/build`, from where it can be viewed in a browser.
