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

from collections.abc import Callable, Generator, Iterable, Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, LiteralString, cast, overload, override

from qgis.PyQt.QtCore import QCoreApplication, Qt

if TYPE_CHECKING:
    import datetime

    from qgis.core import (
        Qgis,
        QgsCoordinateReferenceSystem,
        QgsFeature,
        QgsFeatureRequest,
        QgsFeatureSink,
        QgsGeometry,
        QgsProcessingAlgorithm,
        QgsProcessingContext,
        QgsProcessingFeatureSource,
        QgsProcessingParameterDefinition,
    )
    from qgis.PyQt.QtCore import QDateTime
    from shapely.geometry.base import BaseGeometry as ShapelyBaseGeometry


def QT_VERSION_CHECK(major: int, minor: int = 0, patch: int = 0, /) -> int:
    return major << 16 | minor << 8 | patch


class Box[T]:
    __slots__ = ("value",)
    __match_args__ = ("value",)

    def __init__(self, value: T) -> None:
        self.value = value

    @override
    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.value!r})"


class ModuleNotAvailableError(Exception):
    def __init__(self, name: str):
        super().__init__(f"Module {name!r} is not available")
        self.name = name


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


@dataclass(kw_only=True)
class ProcessingFeatureSinkDefinition:
    name: str
    props: "QgsProcessingAlgorithm.VectorProperties"
    dest: str
    sink: "QgsFeatureSink"


@overload
def and_then[T0](val: T0, /) -> T0: ...
@overload
def and_then[T0, T1](
    val: T0 | None,
    f1: Callable[[T0], T1 | None],
    /,
) -> T1 | None: ...
@overload
def and_then[T0, T1, T2](
    val: T0 | None,
    f1: Callable[[T0], T1 | None],
    f2: Callable[[T1], T2 | None],
    /,
) -> T2 | None: ...
@overload
def and_then[T0, T1, T2, T3](
    val: T0 | None,
    f1: Callable[[T0], T1 | None],
    f2: Callable[[T1], T2 | None],
    f3: Callable[[T2], T3 | None],
    /,
) -> T3 | None: ...
@overload
def and_then[T0, T1, T2, T3, T4](
    val: T0 | None,
    f1: Callable[[T0], T1 | None],
    f2: Callable[[T1], T2 | None],
    f3: Callable[[T2], T3 | None],
    f4: Callable[[T3], T4 | None],
    /,
) -> T4 | None: ...
@overload
def and_then[T0, T1, T2, T3, T4, T5](
    val: T0 | None,
    f1: Callable[[T0], T1 | None],
    f2: Callable[[T1], T2 | None],
    f3: Callable[[T2], T3 | None],
    f4: Callable[[T3], T4 | None],
    f5: Callable[[T4], T5 | None],
    /,
) -> T5 | None: ...
def and_then(val: Any | None, /, *funcs: Callable[[Any], Any | None]) -> Any | None:
    for func in funcs:
        if val is None:
            break
        val = func(val)
    return val


def ensure[T](value: T | None, /) -> T:
    assert value is not None
    return value


def error_name(err: "Qgis.GeometryOperationResult", /) -> str:
    # The error code type is a subclass of IntEnum, while the typing
    # stubs incorrectly annotate it as just a subclass of int.

    # noinspection unresolved-references
    return err.name  # pyright: ignore[reportAttributeAccessIssue]


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


def parameter_crs_pairs(
    definitions: Iterable["QgsProcessingParameterDefinition"],
    parameters: dict[str | None, Any],
    context: "QgsProcessingContext",
) -> Generator[
    tuple["QgsProcessingParameterDefinition", "QgsCoordinateReferenceSystem"]
]:
    # QGIS should really supply a helper function or virtual function interface for this.
    # Adapted from https://github.com/qgis/QGIS/blob/96532a00a606b430bd510e89d243dad799e7cd76/src/core/processing/qgsprocessingalgorithm.cpp#L257

    from qgis.core import (
        QgsProcessingParameterExtent,
        QgsProcessingParameterFeatureSource,
        QgsProcessingParameterGeometry,
        QgsProcessingParameterMapLayer,
        QgsProcessingParameterMultipleLayers,
        QgsProcessingParameterPoint,
        QgsProcessingParameterRasterLayer,
        QgsProcessingParameters,
    )

    for definition in definitions:
        paramtype = definition.type()

        if (
            paramtype == QgsProcessingParameterMapLayer.typeName()
            or paramtype == QgsProcessingParameterRasterLayer.typeName()
        ):
            layer = QgsProcessingParameters.parameterAsLayer(
                definition, parameters, context
            )
            if layer is not None:
                yield definition, layer.crs()

        elif paramtype == QgsProcessingParameterFeatureSource.typeName():
            source = QgsProcessingParameters.parameterAsSource(
                definition, parameters, context
            )
            if source is not None:
                yield definition, source.sourceCrs()

        elif paramtype == QgsProcessingParameterMultipleLayers.typeName():
            layers = QgsProcessingParameters.parameterAsLayerList(
                definition, parameters, context
            )
            for layer in layers:
                yield definition, layer.crs()

        elif paramtype == QgsProcessingParameterExtent.typeName():
            yield (
                definition,
                QgsProcessingParameters.parameterAsExtentCrs(
                    definition, parameters, context
                ),
            )

        elif paramtype == QgsProcessingParameterPoint.typeName():
            yield (
                definition,
                QgsProcessingParameters.parameterAsPointCrs(
                    definition, parameters, context
                ),
            )

        elif paramtype == QgsProcessingParameterGeometry.typeName():
            yield (
                definition,
                QgsProcessingParameters.parameterAsGeometryCrs(
                    definition, parameters, context
                ),
            )


def isodatetime(dt: "QDateTime", /) -> str | None:
    return dt.toString(Qt.DateFormat.ISODateWithMs) if dt.isValid() else None


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
