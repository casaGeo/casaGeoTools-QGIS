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


from collections.abc import Iterator
from typing import TYPE_CHECKING, LiteralString, cast

from qgis.PyQt.QtCore import QCoreApplication

if TYPE_CHECKING:
    import datetime

    from qgis.core import (
        QgsFeature,
        QgsFeatureRequest,
        QgsGeometry,
        QgsProcessingFeatureSource,
    )
    from qgis.PyQt.QtCore import QDateTime
    from shapely.geometry.base import BaseGeometry as ShapelyBaseGeometry

    from .plugin import CasaGeoToolsPlugin


class TrMethod:
    def __set_name__(self, owner: type, name: str) -> None:
        self.context = owner.__name__

    def __call__(
        self,
        sourceText: LiteralString,
        disambiguation: LiteralString | None = None,
        /,
        n: int = -1,
    ) -> str:
        return QCoreApplication.translate(self.context, sourceText, disambiguation, n)


# def DECLARE_TR_FUNCTIONS[T: type](cls: T) -> T:
#     setattr(
#         cls,
#         f"_{cls.__name__}__tr",
#         staticmethod(partial(QCoreApplication.translate, cls.__name__)),
#     )
#     return cls


class CasaGeoToolsCoderTranslator:
    __tr = TrMethod()

    address_names_mode_map: dict[str, str]
    postal_code_mode_map: dict[str, str]

    def __init__(self, plugin: "CasaGeoToolsPlugin") -> None:
        self.plugin = plugin
        self.retranslate()

    def retranslate(self):
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

    def translateAddressNamesMode(self, mode: str) -> str:
        return self.address_names_mode_map.get(mode, mode)

    def translatePostalCodeMode(self, mode: str) -> str:
        return self.postal_code_mode_map.get(mode, mode)


class CasaGeoToolsSpatialTranslator:
    __tr = TrMethod()

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
            "outgoing": self.__tr("Outgoing", "Direction type"),
            "incoming": self.__tr("Incoming", "Direction type"),
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

    def translateRangeType(self, range_type: str) -> str:
        return self.range_type_map.get(range_type, range_type)

    def translateRangeUnit(self, range_unit: str) -> str:
        return self.range_unit_map.get(range_unit, range_unit)

    def translateTransportMode(self, transport_mode: str) -> str:
        return self.transport_mode_map.get(transport_mode, transport_mode)

    def translateRoutingMode(self, routing_mode: str) -> str:
        return self.routing_mode_map.get(routing_mode, routing_mode)

    def translateDirectionType(self, direction_type: str) -> str:
        return self.direction_type_map.get(direction_type, direction_type)

    def translateAvoidableFeature(self, avoidable_feature: str) -> str:
        return self.avoidable_feature_map.get(avoidable_feature, avoidable_feature)


def ensure[T](value: T | None, /) -> T:
    assert value is not None
    return value


def features_of(
    source: "QgsProcessingFeatureSource",
    request: "QgsFeatureRequest | None" = None,
) -> "Iterator[QgsFeature]":
    it = source.getFeatures() if request is None else source.getFeatures(request)
    return cast("Iterator[QgsFeature]", cast(object, it))


def geometry_as_shapely(geometry: "QgsGeometry", /) -> "ShapelyBaseGeometry":
    # See https://qgis.org/pyqgis/master/core/QgsGeometry.html#qgis.core.QgsGeometry.as_shapely
    return geometry.as_shapely()  # pyright: ignore[reportAttributeAccessIssue]


def geometry_from_shapely(geometry: "ShapelyBaseGeometry", /) -> "QgsGeometry":
    from qgis.core import QgsGeometry

    # See https://qgis.org/pyqgis/master/core/QgsGeometry.html#qgis.core.QgsGeometry.from_shapely
    return QgsGeometry.from_shapely(geometry)  # pyright: ignore[reportAttributeAccessIssue]


def pydatetime(dt: "QDateTime", /) -> "datetime.datetime | None":
    return dt.toPyDateTime() if dt.isValid() else None


def version_tuple(version: str) -> tuple[int, ...]:
    import re

    match = re.match(r"(\d+(?:.\d+)*)", version, re.ASCII)
    if match is None:
        raise ValueError(f"not a version string: {version!r}")

    return tuple(map(int, match[1].split(".")))


# class Box[T: "QObject"]:
#     def __init__(self) -> None:
#         self.__value: T | None = None
#         self.__connection: QMetaObject.Connection | None = None
#
#     def get(self) -> T | None:
#         return self.__value
#
#     def set(self, value: T) -> None:
#         self.clear()
#         self.__value = value
#         self.__connection = value.destroyed.connect(self.clear)
#
#     def clear(self) -> None:
#         self.__value = None
#         if self.__connection is not None:
#             self.__connection.disconnect()
#             self.__connection = None
#
#
# class cached_qobject_property[T: QObject](cached_property[T]):
#     @override
#     def __get__(self, instance, owner=None):
#         value = super().__get__(instance, owner)
#         if instance is not None:
#             value.destroyed.co
#         return value
#
#     def reset(self) -> None:
