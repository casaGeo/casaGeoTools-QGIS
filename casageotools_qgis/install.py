import importlib.util
import os
import re
import subprocess
import sys
from tempfile import NamedTemporaryFile
from typing import override

from qgis.core import Qgis, QgsMessageLog, QgsTask

from .resources import PLUGIN_IDENTIFIER

CONSTRAINTS_RX = re.compile("(gdal|numpy|pyqt.*?|sip)==", re.ASCII | re.IGNORECASE)


class CasaGeoToolsInstallRequirementsTask(QgsTask):
    def __init__(self, filename: str, description: str | None = None):
        # TODO: Make this task cancellable and adjust the flags afterwards.
        super().__init__(description, QgsTask.Flags())
        self.filename = filename

    @override
    def run(self) -> bool:
        try:
            # TODO: Reimplement this task using subprocess.Popen so it is cancellable and reports progress using --progress-bar=raw.
            _install_requirements(self.filename)
        except subprocess.CalledProcessError as err:
            QgsMessageLog.logMessage(
                f"{err}:\n" + err.stderr,
                PLUGIN_IDENTIFIER,
                Qgis.MessageLevel.Critical,
                notifyUser=True,
            )
        except ConstraintsEmptyError as err:
            QgsMessageLog.logMessage(
                f"{err}",
                PLUGIN_IDENTIFIER,
                Qgis.MessageLevel.Critical,
                notifyUser=True,
            )
        # Letting an exception escape here would cause QGIS to crash.
        # This makes me think we should be catching BaseException, but
        # the QGIS-provided QgsTaskWrapper, which does basically the
        # same thing, just catches Exception.
        except Exception as err:
            QgsMessageLog.logMessage(
                f"{err}",
                PLUGIN_IDENTIFIER,
                Qgis.MessageLevel.Critical,
                notifyUser=True,
            )
        else:
            return True

        return False


class ConstraintsEmptyError(Exception):
    pass


def _install_requirements(filename: str) -> None:
    QgsMessageLog.logMessage(
        f"Installing dependencies from {filename}",
        PLUGIN_IDENTIFIER,
        Qgis.MessageLevel.Info,
    )

    process_encoding = "utf-8"
    process_environment = dict(os.environ, PYTHONIOENCODING="utf-8")

    # Pip might not be available, for example in the QGIS Flatpak.
    # We cannot run this unconditionally, because `ensurepip` might be
    # disabled in the presence of a system Python installation.
    # This is the case under Arch and Debian.
    if not importlib.util.find_spec("pip"):
        subprocess.run(
            [sys.executable, "-m", "ensurepip", "--user"],
            capture_output=True,
            check=True,
            encoding=process_encoding,
            env=process_environment,
        )

    # We cannot use `-s` here, because pip might only be available from
    # the user install directory. This is the case when we install pip
    # using `ensurepip --user`. Note that plain `ensurepip` will also
    # install to the user install directory when the system install
    # directory is not writable.
    pip_freeze = subprocess.run(
        [sys.executable, "-m", "pip", "list", "--format=freeze"],
        capture_output=True,
        check=True,
        encoding=process_encoding,
        env=process_environment,
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
            encoding=process_encoding,
            env=process_environment,
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
