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

from typing import TYPE_CHECKING

from .utils import TrMethod

if TYPE_CHECKING:
    from .plugin import CasaGeoToolsPlugin


class CasaGeoToolsTranslations:
    __tr = TrMethod()

    # General
    unit_system_map: dict[str, str]
    political_view_map: dict[str, str]
    # Coder
    address_names_mode_map: dict[str, str]
    postal_code_mode_map: dict[str, str]
    # Spatial
    range_type_map: dict[str, str]
    range_unit_map: dict[str, str]
    transport_mode_map: dict[str, str]
    routing_mode_map: dict[str, str]
    direction_type_map: dict[str, str]
    avoidable_feature_map: dict[str, str]

    def __init__(self, plugin: "CasaGeoToolsPlugin") -> None:
        self.plugin = plugin
        self.retranslate()

    def retranslate(self):
        self.unit_system_map = {
            "metric": self.__tr("Metric", "Unit system"),
            "imperial": self.__tr("Imperial", "Unit system"),
        }
        self.political_view_map = {
            "ARG": self.__tr("Argentina", "Political view"),
            "EGY": self.__tr("Egypt", "Political view"),
            "KEN": self.__tr("Kenya", "Political view"),
            "IND": self.__tr("India", "Political view"),
            "MAR": self.__tr("Morocco", "Political view"),
            "PAK": self.__tr("Pakistan", "Political view"),
            "RUS": self.__tr("Russia", "Political view"),
            "SDN": self.__tr("Sudan", "Political view"),
            "SRB": self.__tr("Serbia", "Political view"),
            "SUR": self.__tr("Suriname", "Political view"),
            "SYR": self.__tr("Syria", "Political view"),
            "TUR": self.__tr("Türkiye", "Political view"),
            "TZA": self.__tr("Tanzania", "Political view"),
            "URY": self.__tr("Uruguay", "Political view"),
            "VNM": self.__tr("Vietnam", "Political view"),
            "XXX": self.__tr("International", "Political view"),
        }
        self.address_names_mode_map = {
            "default": self.__tr("Default", "Address names mode"),
            "matched": self.__tr("Matched", "Address names mode"),
            "normalized": self.__tr("Normalized", "Address names mode"),
        }
        self.postal_code_mode_map = {
            "default": self.__tr("Default", "Postal code mode"),
            "cityLookup": self.__tr("City lookup", "Postal code mode"),
            "districtLookup": self.__tr("District lookup", "Postal code mode"),
        }
        self.range_type_map = {
            "time": self.__tr("Time", "Range type"),
            "distance": self.__tr("Distance", "Range type"),
        }
        self.range_unit_map = {
            "minutes": self.__tr("Minutes", "Range unit"),
            "meters": self.__tr("Meters", "Range unit"),
        }
        self.transport_mode_map = {
            "car": self.__tr("Car", "Transport mode"),
            "pedestrian": self.__tr("Pedestrian", "Transport mode"),
            "bicycle": self.__tr("Bicycle", "Transport mode"),
            "truck": self.__tr("Truck", "Transport mode"),
        }
        self.routing_mode_map = {
            "fast": self.__tr("Fast", "Routing mode"),
            "short": self.__tr("Short", "Routing mode"),
        }
        self.direction_type_map = {
            "outgoing": self.__tr("Outgoing (From)", "Direction type"),
            "incoming": self.__tr("Incoming (To)", "Direction type"),
        }
        self.avoidable_feature_map = {
            "carShuttleTrain": self.__tr("Car shuttle trains", "Avoidable feature"),
            "controlledAccessHighway": self.__tr(
                "Controlled access highways", "Avoidable feature"
            ),
            "dirtRoad": self.__tr("Dirt roads", "Avoidable feature"),
            "ferry": self.__tr("Ferries", "Avoidable feature"),
            "seasonalClosure": self.__tr("Seasonal closures", "Avoidable feature"),
            "tollRoad": self.__tr("Toll roads", "Avoidable feature"),
            "tunnel": self.__tr("Tunnels", "Avoidable feature"),
            "uTurns": self.__tr("U-turns", "Avoidable feature"),
        }

    def translateUnitSystem(self, unit_system: str, /) -> str:
        return self.unit_system_map.get(unit_system, unit_system)

    def translatePoliticalView(self, political_view: str, /) -> str:
        return self.political_view_map.get(political_view, political_view)

    def translateAddressNamesMode(self, mode: str, /) -> str:
        return self.address_names_mode_map.get(mode, mode)

    def translatePostalCodeMode(self, mode: str, /) -> str:
        return self.postal_code_mode_map.get(mode, mode)

    def translateRangeType(self, range_type: str, /) -> str:
        return self.range_type_map.get(range_type, range_type)

    def translateRangeUnit(self, range_unit: str, /) -> str:
        return self.range_unit_map.get(range_unit, range_unit)

    def translateTransportMode(self, transport_mode: str, /) -> str:
        return self.transport_mode_map.get(transport_mode, transport_mode)

    def translateRoutingMode(self, routing_mode: str, /) -> str:
        return self.routing_mode_map.get(routing_mode, routing_mode)

    def translateDirectionType(self, direction_type: str, /) -> str:
        return self.direction_type_map.get(direction_type, direction_type)

    def translateAvoidableFeature(self, avoidable_feature: str, /) -> str:
        return self.avoidable_feature_map.get(avoidable_feature, avoidable_feature)
