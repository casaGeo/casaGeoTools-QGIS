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

import json as jsonlib
from typing import Any, override

from casageo.tools import (
    APIValueError,
    CasaGeoClient,
    CasaGeoError,
    NetworkRequestBackend,
)
from qgis.core import QgsFeedback, QgsNetworkAccessManager
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtNetwork import QNetworkReply, QNetworkRequest


class CasaGeoToolsQgisEnabledCasaGeoClient(CasaGeoClient):
    def __init__(
        self, *args, qgis_feedback: QgsFeedback | None = None, **kwargs
    ) -> None:
        self.__feedback = qgis_feedback
        super().__init__(*args, **kwargs)

    @override
    def setup_network_request_backend(self) -> NetworkRequestBackend:
        return QgisNetworkRequestBackend(self, feedback=self.__feedback)


class QgisNetworkRequestBackend(NetworkRequestBackend):
    def __init__(self, client: CasaGeoClient, *, feedback: QgsFeedback | None) -> None:
        self.auth_header = client.apikey.encode()
        self.server_url = QUrl(client.server_url)
        self.feedback = feedback

    @override
    def request(self, method: str, url: str, *, json: Any | None = None, **_) -> Any:
        NetworkError = QNetworkReply.NetworkError

        request = QNetworkRequest(self.server_url.resolved(QUrl(url)))
        request.setRawHeader(b"Authorization", self.auth_header)

        match method.upper():
            case "GET":
                reply = QgsNetworkAccessManager.blockingGet(
                    request, forceRefresh=True, feedback=self.feedback
                )
            case "POST":
                data = jsonlib.dumps(
                    json, ensure_ascii=False, allow_nan=False, separators=(",", ":")
                ).encode("utf-8")
                request.setHeader(
                    QNetworkRequest.KnownHeaders.ContentTypeHeader,
                    "application/json; charset=utf-8",
                )
                request.setHeader(
                    QNetworkRequest.KnownHeaders.ContentLengthHeader, str(len(data))
                )
                reply = QgsNetworkAccessManager.blockingPost(
                    request,
                    data,
                    forceRefresh=True,
                    feedback=self.feedback,
                )
            case _:
                raise ValueError(f"Unsupported method: {method}")

        # QByteArray does implement the buffer protocol, even though the
        # documentation doesn’t mention it.
        # noinspection bad-argument-type,unbound-local-variable
        response = str(reply.content(), "utf-8")

        match reply.error():
            case NetworkError.NoError:
                return jsonlib.loads(response)

            case NetworkError.OperationCanceledError:
                return None

            case NetworkError.ProtocolInvalidOperationError:
                raise APIValueError(response)

        msg = f"Request failed (code {reply.error()}): {reply.errorString()}"
        raise CasaGeoError(msg)

    @override
    def close(self) -> None:
        pass
