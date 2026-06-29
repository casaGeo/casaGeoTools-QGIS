#  Copyright 2026 casaGeo Data + Services GmbH <info@casageo.de>
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
#  SPDX-License-Identifier: Apache-2.0

import os
from typing import cast

PLUGIN_DIRECTORY = os.path.dirname(cast(str, __file__))
PLUGIN_IDENTIFIER = os.path.basename(PLUGIN_DIRECTORY)

PLUGIN_ASSETS_DIRECTORY = os.path.join(PLUGIN_DIRECTORY, "assets")
PLUGIN_HELP_DIRECTORY = os.path.join(PLUGIN_DIRECTORY, "help")
PLUGIN_I18N_DIRECTORY = os.path.join(PLUGIN_DIRECTORY, "i18n")


def R(path: str | os.PathLike[str]) -> str:
    return os.path.join(PLUGIN_DIRECTORY, path)


# def plugin_version() -> str:
#     import configparser
#
#     config = configparser.ConfigParser()
#     config.read(os.path.join(PLUGIN_DIRECTORY, "metadata.txt"))
#     return config["general"]["version"]
