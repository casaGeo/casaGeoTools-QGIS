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


from typing import TYPE_CHECKING, LiteralString

from qgis.PyQt.QtCore import QCoreApplication

if TYPE_CHECKING:
    from qgis.core import QgsGeometry
    from shapely.geometry.base import BaseGeometry as ShapelyBaseGeometry


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


def ensure[T](value: T | None, /) -> T:
    assert value is not None
    return value


def geometry_as_shapely(geometry: "QgsGeometry", /) -> "ShapelyBaseGeometry":
    # See https://qgis.org/pyqgis/master/core/QgsGeometry.html#qgis.core.QgsGeometry.as_shapely
    return geometry.as_shapely()  # pyright: ignore[reportAttributeAccessIssue]


def geometry_from_shapely(geometry: "ShapelyBaseGeometry", /) -> "QgsGeometry":
    # See https://qgis.org/pyqgis/master/core/QgsGeometry.html#qgis.core.QgsGeometry.from_shapely
    return QgsGeometry.from_shapely(geometry)  # pyright: ignore[reportAttributeAccessIssue]


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
