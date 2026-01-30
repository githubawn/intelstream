import ipaddress
import socket
from urllib.parse import urlparse


class SSRFError(Exception):
    """Raised when a URL fails SSRF validation."""


BLOCKED_HOSTS = frozenset({
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
})


def _is_private_ip(ip_str: str) -> bool:
    """Check if an IP address is private, loopback, or link-local."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
    except ValueError:
        return False


def validate_url_for_ssrf(url: str) -> None:
    """
    Validate a URL to prevent SSRF attacks.

    Raises:
        SSRFError: If the URL points to a blocked host or internal IP.
    """
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise SSRFError("Only HTTP and HTTPS URLs are allowed")

    hostname = parsed.hostname
    if not hostname:
        raise SSRFError("URL must have a valid hostname")

    hostname_lower = hostname.lower()

    if hostname_lower in BLOCKED_HOSTS:
        raise SSRFError("URLs pointing to localhost are not allowed")

    if _is_private_ip(hostname_lower):
        raise SSRFError("URLs pointing to private IP addresses are not allowed")

    try:
        resolved_ips = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for _, _, _, _, sockaddr in resolved_ips:
            ip_str = str(sockaddr[0])
            if _is_private_ip(ip_str):
                raise SSRFError(
                    f"URL resolves to a private IP address ({ip_str})"
                )
    except socket.gaierror:
        pass


def is_safe_url(url: str) -> tuple[bool, str]:
    """
    Check if a URL is safe from SSRF attacks.

    Returns:
        Tuple of (is_safe, error_message). If is_safe is True, error_message is empty.
    """
    try:
        validate_url_for_ssrf(url)
        return True, ""
    except SSRFError as e:
        return False, str(e)
