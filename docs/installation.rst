.. Copyright 2026 casaGeo Data + Services GmbH <info@casageo.de>
   SPDX-License-Identifier: CC-BY-SA-4.0


=========================
Installation Instructions
=========================

This extension requires the ``casaGeoTools`` package and it’s dependencies to be
installed in your QGIS Python environment. Core functionality will be
unavailable otherwise. You can find the list of dependencies and their required
versions in the file ``requirements.txt`` in the plugin directory.

The recommended way to install this plugin’s Python dependencies is to use the
automatic installation method described below.


Automatic Installation
======================

Open QGIS and click on :menuselection:`Plugins --> casaGeoTools --> Install
Python dependencies...`. This will install ``casaGeoTools`` and it’s
dependencies as user-packages into the Python environment used by QGIS.


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

Under Windows, start the OSGeo4W Shell that comes bundled with your QGIS
installation. You can find it in the QGIS folder on your desktop, or by
right-clicking QGIS in the Start Menu and selecting Open File Location.

Enter the commands below into the OSGeo4W Shell, check the output, and remove
the ``--dry-run`` argument if everything looks correct.

.. code-block:: bat

   python3 -m pip --version || python3 -m ensurepip --user
   python3 -m pip list --format=freeze ^
      | findstr /b /i /r "gdal= numpy= pyqt[^=]*= sip=" > %TEMP%\constraints.txt ^
      || (echo. & echo ERROR: Unable to pin critical system packages) >&2
   python3 -m pip install --user --dry-run --constraint %TEMP%\constraints.txt ^
      casaGeoTools

.. note::
   QGIS will only pick up on these changes after a restart. If you’ve had
   QGIS running in the background while following these steps, restart it now.


Linux
-----

Under Linux, QGIS may be installed either as a native package or as a Flatpak.
You can check which one is the case by going to :menuselection:`Help --> About
QGIS` and looking for the words “Flatpak runtime”.

If you are using a native package, enter the commands below into the terminal
directly. If you are using the Flatpak version, run ``flatpak run --command=bash
org.qgis.qgis`` to open a shell in the isolated Flatpak environment before
entering the commands below.

Check the output of each command and remove the ``--dry-run`` argument if
everything looks correct.

.. code-block:: bash

   python3 -m pip --version || python3 -m ensurepip --user
   python3 -m pip list --format=freeze \
      | grep -iE '^(gdal=|numpy=|pyqt[^=]*=|sip=)' > /tmp/constraints.txt \
      || (echo; echo ERROR: Unable to pin critical system packages) >&2
   python3 -m pip install --user --dry-run --constraint /tmp/constraints.txt \
      casaGeoTools

.. note::
   QGIS will only pick up on these changes after a restart. If you’ve had
   QGIS running in the background while following these steps, restart it now.

If you installed QGIS some other way, check the relevant documentation on how to
access the QGIS Python environment and install Python packages.
