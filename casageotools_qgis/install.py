import os
import re
import subprocess
import sys
from tempfile import NamedTemporaryFile

from qgis.core import Qgis, QgsMessageLog

from casageotools_qgis.resources import PLUGIN_IDENTIFIER

CONSTRAINTS_RX = re.compile("(gdal|numpy|pyqt.*?|sip)==", re.ASCII | re.IGNORECASE)


class ConstraintsEmptyError(Exception):
    pass


def _install_requirements(filename: str) -> None:
    QgsMessageLog.logMessage(
        f"Installing dependencies from {filename}",
        PLUGIN_IDENTIFIER,
        Qgis.MessageLevel.Info,
    )

    pip_freeze = subprocess.run(
        [sys.executable, "-s", "-m", "pip", "list", "--format=freeze"],
        capture_output=True,
        check=True,
        encoding="utf-8",
        env=dict(os.environ, PYTHONIOENCODING="utf-8"),
    )

    constraints = [
        c
        for c in pip_freeze.stdout.splitlines(keepends=True)
        if CONSTRAINTS_RX.match(c)
    ]

    if not constraints:
        raise ConstraintsEmptyError("Unable to pin critical system packages")

    QgsMessageLog.logMessage(
        "Pinning system packages:\n" + "".join(constraints),
        PLUGIN_IDENTIFIER,
        Qgis.MessageLevel.Info,
    )

    with NamedTemporaryFile(
        "w+",
        encoding="utf-8",
        delete_on_close=False,  # Required to be able to reopen the file under Windows.
    ) as constraints_file:
        constraints_file.writelines(constraints)
        constraints_file.close()
        pip_install = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--user",
                "--progress-bar=off",
                "--constraint",
                constraints_file.name,
                "--requirement",
                filename,
            ],
            capture_output=True,
            check=True,
            encoding="utf-8",
            env=dict(os.environ, PYTHONIOENCODING="utf-8"),
        )

        QgsMessageLog.logMessage(
            "Command output:\n" + pip_install.stdout,
            PLUGIN_IDENTIFIER,
            Qgis.MessageLevel.Info,
        )

        QgsMessageLog.logMessage(
            "Installation complete",
            PLUGIN_IDENTIFIER,
            Qgis.MessageLevel.Success,
            notifyUser=True,
        )


def install_requirements(filename: str) -> bool:
    try:
        _install_requirements(filename)
    except subprocess.CalledProcessError as err:
        QgsMessageLog.logMessage(
            f"{err}:\n" + err.stderr,
            PLUGIN_IDENTIFIER,
            Qgis.MessageLevel.Critical,
            notifyUser=True,
        )
        return False
    except ConstraintsEmptyError as err:
        QgsMessageLog.logMessage(
            f"{err}",
            PLUGIN_IDENTIFIER,
            Qgis.MessageLevel.Critical,
            notifyUser=True,
        )
        return False
    return True
