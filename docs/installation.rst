.. Copyright 2026 casaGeo Data + Services GmbH <info@casageo.de>
   SPDX-License-Identifier: CC-BY-SA-4.0


=========================
Installation Instructions
=========================

This extension requires the ``casaGeoTools`` package and it’s dependencies to be
installed in your QGIS Python environment. Core functionality will be
unavailable otherwise.


Automatic Installation
======================

This is the recommended way to install Python dependencies for most users.

Open QGIS and click on :menuselection:`Plugins --> casaGeoTools --> Install
Python dependencies...`. This will install ``casaGeoTools`` and it’s
dependencies as user-packages into the Python environment used by QGIS.

.. note::
   If you are a Linux user and have installed QGIS using Flatpak, you have to
   take some extra steps. Read on below.


Linux – Flatpak
---------------

If you are using QGIS under Linux, you are likely using the Flatpak version. You
can check this by going to :menuselection:`Help --> About QGIS` and looking for
the words “Flatpak runtime”.

Flatpak applications run inside a sandbox to isolate them from the host system.
To install Python packages into the sandbox, you have to start QGIS with the
development runtime so it has access to ``pip``. To do this, just enter these
commands into the terminal::

   flatpak install "$(flatpak info --show-sdk org.qgis.qgis)"
   flatpak run --devel org.qgis.qgis

This will install the required development runtime and use it to start a new
instance of QGIS. There you can perform the automatic installation as described
above.


Manual Installation
===================

To manually install a Python dependency like ``casaGeoTools`` you need to **find
the correct Python interpreter** before entering the commands below into the
corresponding shell. It should be the same interpreter used by QGIS with all
corresponding environment variables set to the right values. You also have to
take care not to accidentally install a newer version of one of the QGIS core
dependencies, which is why the commands below use a ``constraints.txt`` file.


Windows
-------

Under Windows, you can use the ``python-qgis.bat`` launcher script that is part
of QGIS. This script is located in the ``bin`` directory of your QGIS
installation. Check the output of the commands below and remove the
``--dry-run`` argument if everything looks correct.

.. code-block:: batch

   python-qgis -s -m pip freeze | findstr /b /i /c:"gdal" /c:"numpy" /c:"pyqt" > %TEMP%\constraints.txt
   python-qgis -m pip install --user --dry-run --constraint %TEMP%\constraints.txt casaGeoTools


Linux – Native
--------------

Under Linux, if QGIS is installed using the native package manager, you can use
the system ``pip`` to install ``casaGeoTools`` into your home directory. Check
the output of the commands below and remove the ``--dry-run`` argument if
everything looks correct.

.. code-block:: bash

   python -s -m pip freeze | grep -iE '^(gdal|numpy|pyqt)' > /tmp/constraints.txt
   python -m pip install --user --dry-run --constraint /tmp/constraints.txt casaGeoTools


Linux – Flatpak
---------------

Under Linux, if QGIS is installed as a Flatpak, you have to install
``casaGeoTools`` into the isolated Flatpak environment. To do this, run the
commands below to install the development runtime for the QGIS Flatpak and open
a developer-mode shell inside the Flatpak environment.

.. code-block:: bash

   flatpak install "$(flatpak info --show-sdk org.qgis.qgis)"
   flatpak run --devel --command=bash org.qgis.qgis

Within the Flatpak environment, you can now use the same commands as for a
native Linux installation to install Python packages into the QGIS Python
environment. Check the output and remove the ``--dry-run`` argument if
everything looks correct.

.. code-block:: bash

   python -s -m pip freeze | grep -iE '^(gdal|numpy|pyqt)' > /tmp/constraints.txt
   python -m pip install --user --dry-run --constraint /tmp/constraints.txt casaGeoTools
