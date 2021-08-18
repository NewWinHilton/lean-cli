# QUANTCONNECT.COM - Democratizing Finance, Empowering Individuals.
# Lean CLI v1.0. Copyright 2021 QuantConnect Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
from pathlib import Path

import requests

from lean.components.util.logger import Logger


class HTTPClient:
    """The HTTPClient class is a lightweight wrapper around the requests library with additional logging."""

    def __init__(self, logger: Logger) -> None:
        """Creates a new HTTPClient instance.

        :param logger: the logger to log debug messages with
        """
        self._logger = logger

    def get(self, url: str, **kwargs) -> requests.Response:
        """A wrapper around requests.get().

        An error is raised if the response is unsuccessful unless kwargs["raise_for_status"] == False.

        :param url: the request url
        :param kwargs: any kwargs to pass on to requests.get()
        :return: the response of the request
        """
        self._log_request("GET", url, **kwargs)

        raise_for_status = kwargs.pop("raise_for_status", True)
        response = requests.get(url, **kwargs)

        self._check_response(response, raise_for_status)
        return response

    def post(self, url: str, **kwargs) -> requests.Response:
        """A wrapper around requests.post().

        An error is raised if the response is unsuccessful unless kwargs["raise_for_status"] == False.

        :param url: the request url
        :param kwargs: any kwargs to pass on to requests.post()
        :return: the response of the request
        """
        self._log_request("POST", url, **kwargs)

        raise_for_status = kwargs.pop("raise_for_status", True)
        response = requests.post(url, **kwargs)

        self._check_response(response, raise_for_status)
        return response

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        """A wrapper around requests.request().

        An error is raised if the response is unsuccessful unless kwargs["raise_for_status"] == False.

        :param method: the request method
        :param url: the request url
        :param kwargs: any kwargs to pass on to requests.request()
        :return: the response of the request
        """
        self._log_request(method, url, **kwargs)

        raise_for_status = kwargs.pop("raise_for_status", True)
        response = requests.request(method, url, **kwargs)

        self._check_response(response, raise_for_status)
        return response

    def download_file(self, url: str, output_path: Path) -> None:
        """Downloads a file and shows a progress bar when possible.

        :param url: the url to the file to download
        :param output_path: the path to save the file contents to
        """
        response = self.get(url, stream=True)

        total_size_bytes = int(response.headers.get("content-length", 0))

        # Sometimes content length isn't set, don't show a progress bar in that case
        if total_size_bytes > 0:
            progress = self._logger.progress()
            progress_task = progress.add_task("")
        else:
            progress = progress_task = None

        try:
            with output_path.open("wb") as file:
                written_bytes = 0

                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)

                    if progress is not None:
                        written_bytes += len(chunk)
                        progress.update(progress_task, completed=(written_bytes / total_size_bytes) * 100)
        except KeyboardInterrupt as e:
            if progress is not None:
                progress.stop()
            raise e

        if progress is not None:
            progress.stop()

    def log_unsuccessful_response(self, response: requests.Response) -> None:
        """Logs an unsuccessful response's status code and body.

        :param response: the response to log
        """
        body = f"body:\n{response.text}" if response.text != "" else "empty body"
        self._logger.debug(f"Request was not successful, status code {response.status_code}, {body}")

    def _log_request(self, method: str, url: str, **kwargs) -> None:
        """Logs a request.

        :param method: the request method
        :param url: the request url
        :param kwargs: any kwargs passed to a request.* method
        """
        message = f"--> {method.upper()} {url}"

        data = next((kwargs.get(key) for key in ["json", "data", "params"] if key in kwargs), None)
        if data is not None and data != {}:
            message += f" with data:\n{json.dumps(data, indent=4)}"

        self._logger.debug(message)

    def _check_response(self, response: requests.Response, raise_for_status: bool) -> None:
        """Checks a response, logging a debug message if it wasn't successful.

        :param response: the response to check
        :param raise_for_status: True if an error needs to be raised if the request wasn't successful, False if not
        """
        if response.status_code < 200 or response.status_code >= 300:
            self.log_unsuccessful_response(response)

        if raise_for_status:
            response.raise_for_status()
