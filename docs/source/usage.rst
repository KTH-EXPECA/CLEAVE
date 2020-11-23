.. _usage:

Usage
=====

Emulations of Networked Control Systems in CLEAVE are centered around two core concepts: Plants and Controllers. These terms follow the terminology used in Control Systems research: Plants are physical systems we wish to control, whereas Controllers are the computational elements which perform the necessary computations for the controlling of Plants.

In the context of CLEAVE emulations, the definition of Plants and Controllers are done through configuration files written in pure Python, which are then executed through the :code:`cleave.py` launcher script. A couple of examples of such configuration files can be found under the :code:`examples/` directory:

.. code-block:: bash

    // To run a plant configuration
    (venv) $ python cleave.py run-plant examples/plant_config.py

    // To run a controller configuration
    (venv) $ python cleave.py run-controller examples/controller_config.py

Check :code:`cleave.py --help` for more details and additional options.

In the following sections we will explain how to set up NCS emulations in CLEAVE by developing and configuring Plants and Controllers from scratch and connecting them.

Plants
------

These are the representations of the physical systems wish want to control. Plants in CLEAVE are usually physical simulations of some system we wish to monitor and act upon. Correspondingly, a Plant is composed of three subcomponents:

- A :code:`State`, which implements the discrete-time behavior of the simulated system.

- A collection of :code:`Sensor` objects, which measure specific properties of the :code:`State`, potentially transforming them, and send them to the Controller.

- A collection of :code:`Actuator` objects, which receive inputs from the Controller, potentially transform or distort them, and finally act upon specific properties of the :code:`State`.

