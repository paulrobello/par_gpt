import json
import os
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Default configuration similar to DEFAULT_OBSIDIAN_CONFIG in Node.js
DEFAULT_OBSIDIAN_CONFIG: dict[str, str | int | bool] = {
    "protocol": "https",
    "host": "localhost",
    "port": 27124,
    "verifySSL": True,
    "timeout": 5,  # in seconds
    "maxContentLength": 50 * 1024 * 1024,
    "maxBodyLength": 50 * 1024 * 1024,
}


class ObsidianError(Exception):
    """
    Custom exception for Obsidian client errors.
    """

    def __init__(self, message: str, code: int, data: Any | None = None):
        super().__init__(message)
        self.code = code
        self.data = data

class ObsidianClient:
    """
    A client to interact with the Obsidian Local REST API.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """
        Initialize the Obsidian client.

        Args:
            config: A dictionary with configuration options. Must include "apiKey".
        Raises:
            ObsidianError: If the API key is missing.
        """
        if "apiKey" not in config or not config["apiKey"]:
            raise ObsidianError(
                "Missing API key. To fix this:\n"
                "1. Install the 'Local REST API' plugin in Obsidian\n"
                "2. Enable the plugin in Obsidian Settings\n"
                "3. Copy your API key from Obsidian Settings > Local REST API\n"
                "4. Provide the API key in your configuration",
                40100,
            )

        # Determine if we are in a development environment.
        mcp_env = os.getenv("ENV")
        is_dev = (mcp_env == "development") or (mcp_env is None)

        # Read environment variables with fallbacks.
        env_config = {
            "protocol": os.getenv("OBSIDIAN_PROTOCOL", DEFAULT_OBSIDIAN_CONFIG["protocol"]),
            "host": os.getenv("OBSIDIAN_HOST", DEFAULT_OBSIDIAN_CONFIG["host"]),
            "port": int(os.getenv("OBSIDIAN_PORT", DEFAULT_OBSIDIAN_CONFIG["port"])),
            "verifySSL": (
                os.getenv("VERIFY_SSL", "false").lower() == "true"
                if os.getenv("VERIFY_SSL") is not None
                else (False if is_dev else True)
            ),
            "timeout": int(os.getenv("REQUEST_TIMEOUT", "5000")),
            "maxContentLength": int(os.getenv("MAX_CONTENT_LENGTH", str(DEFAULT_OBSIDIAN_CONFIG["maxContentLength"]))),
            "maxBodyLength": int(os.getenv("MAX_BODY_LENGTH", str(DEFAULT_OBSIDIAN_CONFIG["maxBodyLength"]))),
        }

        self.config: dict[str, Any] = {
            "protocol": env_config["protocol"],
            "host": env_config["host"],
            "port": env_config["port"],
            "verifySSL": config.get("verifySSL", env_config["verifySSL"]),
            "apiKey": config["apiKey"],
            "timeout": config.get("timeout", env_config["timeout"]),
            "maxContentLength": config.get("maxContentLength", env_config["maxContentLength"]),
            "maxBodyLength": config.get("maxBodyLength", env_config["maxBodyLength"]),
        }

        # Prepare the session.
        self.session = requests.Session()
        self.base_url = f"{self.config['protocol']}://{self.config['host']}:{self.config['port']}"

        # Set SSL verification.
        self.session.verify = self.config["verifySSL"]

        # Configure default headers.
        headers = self.get_headers()
        # Add additional security headers.
        headers.update(
            {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block",
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            }
        )
        self.session.headers.update(headers)

        # if not self.config["verifySSL"]:
        #     print(
        #         "WARNING: SSL verification is disabled. While this works for development, it's not recommended for production.\n"
        #         "To properly configure SSL certificates:\n"
        #         "1. Go to Obsidian Settings > Local REST API\n"
        #         "2. Under 'How to Access', copy the certificate\n"
        #         "3. For Windows users:\n"
        #         "   - Open 'certmgr.msc' (Windows Certificate Manager)\n"
        #         "   - Go to 'Trusted Root Certification Authorities' > 'Certificates'\n"
        #         "   - Right-click > 'All Tasks' > 'Import' and follow the wizard\n"
        #         "   - Select the certificate file you copied from Obsidian\n"
        #         "4. For other systems:\n"
        #         "   - macOS: Add to Keychain Access\n"
        #         "   - Linux: Add to ca-certificates"
        #     )

    def get_headers(self) -> dict[str, str]:
        """
        Construct the HTTP headers for the client.

        Returns:
            A dictionary of sanitized headers.
        """
        headers: dict[str, str] = {
            "Authorization": f"Bearer {self.config['apiKey']}",
            "Accept": "application/json",
            "User-Agent": os.environ.get("USER_AGENT", "ObsidianClient"),
        }
        # Sanitize header values.
        return {key: self.sanitize_header(value) for key, value in headers.items()}

    @staticmethod
    def sanitize_header(value: str) -> str:
        """
        Remove any potentially harmful characters from header values.

        Args:
            value: The header string to sanitize.
        Returns:
            The sanitized header string.
        """
        return re.sub(r"[^\w\s\-\._~:/?#\[\]@!$&'()*+,;=]", "", value)

    def validate_file_path(self, filepath: str) -> None:
        """
        Validate a file path to prevent path traversal or absolute path usage.

        Args:
            filepath: The file path to validate.
        Raises:
            ObsidianError: If the file path is invalid.
        """
        normalized_path = filepath.replace("\\", "/")
        if "../" in normalized_path or "..\\" in normalized_path:
            raise ObsidianError("Invalid file path: Path traversal not allowed", 40001)
        if normalized_path.startswith("/") or re.match(r"^[a-zA-Z]:", normalized_path):
            raise ObsidianError("Invalid file path: Absolute paths not allowed", 40002)

    def get_error_code(self, status: int) -> int:
        """
        Map HTTP status codes to application-specific error codes.

        Args:
            status: The HTTP status code.
        Returns:
            An integer representing the error code.
        """
        if status == 400:
            return 40000
        elif status == 401:
            return 40100
        elif status == 403:
            return 40300
        elif status == 404:
            return 40400
        elif status == 405:
            return 40500
        elif status == 409:
            return 40900
        elif status == 429:
            return 42900
        elif status == 500:
            return 50000
        elif status == 501:
            return 50100
        elif status == 502:
            return 50200
        elif status == 503:
            return 50300
        elif status == 504:
            return 50400
        else:
            if 400 <= status < 500:
                return 40000 + (status - 400) * 100
            if 500 <= status < 600:
                return 50000 + (status - 500) * 100
            return 50000

    def safe_request(self, operation: Callable[[], Any]) -> Any:
        """
        Wrap HTTP requests with error handling.

        Args:
            operation: A callable that performs an HTTP request.
        Returns:
            The result of the HTTP request.
        Raises:
            ObsidianError: With a detailed message on failure.
        """
        try:
            result = operation()
            return result
        except requests.exceptions.SSLError as e:
            raise ObsidianError(
                "SSL certificate verification failed. You have two options:\n\n"
                "Option 1 - Enable HTTP (not recommended for production):\n"
                "1. Go to Obsidian Settings > Local REST API\n"
                "2. Enable 'Enable Non-encrypted (HTTP) Server'\n"
                "3. Update your client config to use 'http' protocol\n\n"
                "Option 2 - Configure HTTPS (recommended):\n"
                "1. Go to Obsidian Settings > Local REST API\n"
                "2. Under 'How to Access', copy the certificate\n"
                "3. Add the certificate to your system's trusted certificates:\n"
                "   - On macOS: Add to Keychain Access\n"
                "   - On Windows: Add to Certificate Manager\n"
                "   - On Linux: Add to ca-certificates\n"
                "For development only: Set verifySSL: false in client config\n\n"
                f"Original error: {str(e)}",
                50001,
                {"code": "SSLError", "config": {"verifySSL": self.config["verifySSL"]}},
            )
        except requests.exceptions.ConnectionError as e:
            # Check for connection refused message.
            if "Connection refused" in str(e):
                raise ObsidianError(
                    f"Connection refused. To fix this:\n"
                    f"1. Ensure Obsidian is running\n"
                    f"2. Verify the 'Local REST API' plugin is enabled in Obsidian Settings\n"
                    f"3. Check that you're using the correct host ({self.config['host']}) and port ({self.config['port']})\n"
                    "4. Make sure HTTPS is enabled in the plugin settings",
                    50002,
                    {"code": "ConnectionError"},
                )
            raise ObsidianError(str(e), 50000)
        except requests.exceptions.HTTPError as e:
            response = e.response
            status = response.status_code if response is not None else 500
            error_code = self.get_error_code(status)
            message = str(e)
            # Special handling for 401 errors.
            if status == 401:
                message = (
                    "Authentication failed. To fix this:\n"
                    "1. Go to Obsidian Settings > Local REST API\n"
                    "2. Copy your API key from the settings\n"
                    "3. Update your configuration with the new API key\n"
                    "Note: The API key changes when you regenerate certificates"
                )
                error_code = 40100
            raise ObsidianError(message, error_code)
        except Exception as e:
            raise ObsidianError(str(e), 50000) from e

    def _request(self, method: str, endpoint: str, **kwargs: Any) -> requests.Response:
        """
        Helper to make an HTTP request and apply the global timeout.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: The API endpoint (should start with a slash).
            kwargs: Additional parameters for requests.
        Returns:
            The HTTP response.
        """
        url = urljoin(self.base_url, endpoint)
        # Convert timeout from milliseconds to seconds.
        kwargs.setdefault("timeout", self.config["timeout"])
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response

    def list_files_in_vault(self) -> list[dict[str, Any]]:
        """
        list all files in the vault.

        Returns:
            A list of file metadata dictionaries.
        """
        return self.safe_request(lambda: self._request("GET", "/vault/").json().get("files", []))

    def list_files_in_dir(self, dirpath: str) -> list[dict[str, Any]]:
        """
        list files in a specific directory in the vault.

        Args:
            dirpath: The relative directory path.
        Returns:
            A list of file metadata dictionaries.
        """
        self.validate_file_path(dirpath)
        endpoint = f"/vault/{dirpath}/"
        return self.safe_request(lambda: self._request("GET", endpoint).json().get("files", []))

    def get_file_contents(self, filepath: str) -> str:
        """
        Retrieve the contents of a file.

        Args:
            filepath: The relative file path.
        Returns:
            The file contents as a string.
        """
        self.validate_file_path(filepath)
        endpoint = f"/vault/{filepath}"
        return self.safe_request(lambda: self._request("GET", endpoint).text)

    def search(self, query: str, context_length: int = 100) -> list[dict[str, Any]]:
        """
        Perform a simple search.

        Args:
            query: The search query.
            context_length: The context length (default 100).
        Returns:
            A list of simple search result dictionaries.
        """
        params = {"query": query, "contextLength": context_length}
        return self.safe_request(lambda: self._request("POST", "/search/simple/", params=params).json())

    def append_content(self, filepath: str, content: str) -> None:
        """
        Append content to a file.

        Args:
            filepath: The relative file path.
            content: The content to append.
        Raises:
            ObsidianError: If content is invalid.
        """
        self.validate_file_path(filepath)
        if not content or not isinstance(content, str):
            raise ObsidianError("Invalid content: Content must be a non-empty string", 40003)
        endpoint = f"/vault/{filepath}"
        self.safe_request(
            lambda: self._request(
                "POST",
                endpoint,
                data=content,
                headers={"Content-Type": "text/markdown"},
            )
        )

    def update_content(self, filepath: str, content: str) -> None:
        """
        Replace the content of a file.

        Args:
            filepath: The relative file path.
            content: The new content.
        Raises:
            ObsidianError: If content is invalid.
        """
        self.validate_file_path(filepath)
        if not content or not isinstance(content, str):
            raise ObsidianError("Invalid content: Content must be a non-empty string", 40003)
        endpoint = f"/vault/{filepath}"
        self.safe_request(
            lambda: self._request(
                "PUT",
                endpoint,
                data=content,
                headers={"Content-Type": "text/markdown"},
            )
        )

    def search_json(self, query: dict[str, Any]) -> list[dict[str, Any]] | list[Any]:
        """
        Perform a JSON Logic search.

        Args:
            query: A JSON Logic query as a dictionary.
        Returns:
            A list of search result dictionaries.
        """
        # Determine if this is a tag search.
        query_str = json.dumps(query)
        is_tag_search = '"contains"' in query_str and '"#"' in query_str
        headers = {
            "Content-Type": "application/vnd.olrapi.jsonlogic+json",
            "Accept": "application/vnd.olrapi.note+json",
        }
        response = self.safe_request(lambda: self._request("POST", "/search/", json=query, headers=headers))
        data = response.json()
        # Depending on the search type, the data structure may differ.
        return data  # caller can inspect the result as needed

    def get_status(self) -> dict[str, Any]:
        """
        Get the status of the Obsidian server.

        Returns:
            A dictionary containing status information.
        """
        return self.safe_request(lambda: self._request("GET", "/").json())

    def list_commands(self) -> list[dict[str, Any]]:
        """
        list available commands.

        Returns:
            A list of command dictionaries.
        """
        response = self.safe_request(lambda: self._request("GET", "/commands/").json())
        return response.get("commands", [])

    def execute_command(self, command_id: str) -> None:
        """
        Execute a command by its ID.

        Args:
            command_id: The command identifier.
        """
        endpoint = f"/commands/{command_id}/"
        self.safe_request(lambda: self._request("POST", endpoint))

    def open_file(self, filepath: str, new_leaf: bool = False) -> None:
        """
        Open a file in Obsidian.

        Args:
            filepath: The relative file path.
            new_leaf: Whether to open in a new leaf (default False).
        """
        self.validate_file_path(filepath)
        endpoint = f"/open/{filepath}"
        params = {"newLeaf": new_leaf}
        self.safe_request(lambda: self._request("POST", endpoint, params=params))

    def get_active_file(self) -> dict[str, Any]:
        """
        Get the currently active file.

        Returns:
            A dictionary representing the active file.
        """
        headers = {"Accept": "application/vnd.olrapi.note+json"}
        return self.safe_request(lambda: self._request("GET", "/active/", headers=headers).json())

    def update_active_file(self, content: str) -> None:
        """
        Update the content of the active file.

        Args:
            content: The new content.
        """
        self.safe_request(
            lambda: self._request(
                "PUT",
                "/active/",
                data=content,
                headers={"Content-Type": "text/markdown"},
            )
        )

    def delete_active_file(self) -> None:
        """
        Delete the active file.
        """
        self.safe_request(lambda: self._request("DELETE", "/active/"))

    def patch_active_file(
        self,
        operation: str,
        target_type: str,
        target: str,
        content: str,
        options: dict[str, Any] | None = None,
    ) -> None:
        """
        Patch the active file with an operation.

        Args:
            operation: "append", "prepend", or "replace".
            target_type: "heading", "block", or "frontmatter".
            target: The target identifier.
            content: The content to patch.
            options: Optional parameters (delimiter, trimWhitespace, contentType).
        """
        options = options or {}
        headers: dict[str, str] = {
            "Operation": operation,
            "Target-Type": target_type,
            "Target": target,
            "Content-Type": options.get("contentType", "text/markdown"),
        }
        if "delimiter" in options:
            headers["Target-Delimiter"] = options["delimiter"]
        if "trimWhitespace" in options:
            headers["Trim-Target-Whitespace"] = str(options["trimWhitespace"])
        self.safe_request(lambda: self._request("PATCH", "/active/", data=content, headers=headers))

    def get_periodic_note(self, period: str) -> dict[str, Any]:
        """
        Get a periodic note.

        Args:
            period: The period type (e.g. "daily", "weekly").
        Returns:
            A dictionary representing the periodic note.
        """
        headers = {"Accept": "application/vnd.olrapi.note+json"}
        endpoint = f"/periodic/{period}/"
        return self.safe_request(lambda: self._request("GET", endpoint, headers=headers).json())

    def update_periodic_note(self, period: str, content: str) -> None:
        """
        Update a periodic note.

        Args:
            period: The period type.
            content: The new content.
        """
        endpoint = f"/periodic/{period}/"
        self.safe_request(
            lambda: self._request(
                "PUT",
                endpoint,
                data=content,
                headers={"Content-Type": "text/markdown"},
            )
        )

    def delete_periodic_note(self, period: str) -> None:
        """
        Delete a periodic note.

        Args:
            period: The period type.
        """
        endpoint = f"/periodic/{period}/"
        self.safe_request(lambda: self._request("DELETE", endpoint))

    def patch_periodic_note(
        self,
        period: str,
        operation: str,
        target_type: str,
        target: str,
        content: str,
        options: dict[str, Any] | None = None,
    ) -> None:
        """
        Patch a periodic note.

        Args:
            period: The period type.
            operation: "append", "prepend", or "replace".
            target_type: "heading", "block", or "frontmatter".
            target: The target identifier.
            content: The patch content.
            options: Optional parameters (delimiter, trimWhitespace, contentType).
        """
        options = options or {}
        headers: dict[str, str] = {
            "Operation": operation,
            "Target-Type": target_type,
            "Target": target,
            "Content-Type": options.get("contentType", "text/markdown"),
        }
        if "delimiter" in options:
            headers["Target-Delimiter"] = options["delimiter"]
        if "trimWhitespace" in options:
            headers["Trim-Target-Whitespace"] = str(options["trimWhitespace"])
        endpoint = f"/periodic/{period}/"
        self.safe_request(lambda: self._request("PATCH", endpoint, data=content, headers=headers))


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv(Path("~/.par_gpt.env").expanduser())

    client = ObsidianClient({"apiKey": os.environ.get("OBSIDIAN_API_KEY"), "verifySSL": False})
    print(client.get_active_file())
