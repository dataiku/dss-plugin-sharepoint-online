import contextlib
import datetime
import http.server
import ipaddress
import json
import ssl
import threading
import time
import socketserver

import pytest
import requests
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from sharepoint_client import SharePointClient
from sharepoint_constants import SharePointConstants


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


class SlowOidcHandler(http.server.BaseHTTPRequestHandler):
    delay_sec = 0.0
    paths = []

    def log_message(self, *args, **kwargs):
        pass

    def do_GET(self):
        self.__class__.paths.append(self.path)
        time.sleep(self.delay_sec)
        body = json.dumps({
            "authorization_endpoint": self.server.authority_url + "/oauth2/v2.0/authorize",
            "token_endpoint": self.server.authority_url + "/oauth2/v2.0/token",
        }).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def make_client():
    client = object.__new__(SharePointClient)
    client.client_id = "client-id"
    client.tenant_id = "tenant-id"
    client.client_certificate_thumbprint = "thumbprint"
    client.client_certificate = (
        "-----BEGIN PRIVATE KEY-----\n"
        "MIIEvQIBADANBgkqhkiG9w0BAQEFAASC\n"
        "-----END PRIVATE KEY-----"
    )
    client.passphrase = None
    client.sharepoint_origin = "https://tenant.sharepoint.com"
    client.sharepoint_tenant = "tenant"
    return client


def generate_localhost_certificate(cert_path, key_path):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow() - datetime.timedelta(minutes=1))
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
            ]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ))


@contextlib.contextmanager
def slow_oidc_server(tmp_path, delay_sec):
    cert_path = tmp_path / "localhost.pem"
    key_path = tmp_path / "localhost.key"
    generate_localhost_certificate(cert_path, key_path)

    SlowOidcHandler.delay_sec = delay_sec
    SlowOidcHandler.paths = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), SlowOidcHandler)
    server.authority_url = "https://localhost:{}/tenant-id".format(server.server_port)

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(str(cert_path), str(key_path))
    server.socket = context.wrap_socket(server.socket, server_side=True)

    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    try:
        yield server, cert_path, SlowOidcHandler.paths
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)


def test_certificate_app_auth_passes_timeout_to_msal(monkeypatch):
    import msal

    captured = {}

    class FakeConfidentialClientApplication:
        def __init__(self, *args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs

        def acquire_token_for_client(self, scopes):
            captured["scopes"] = scopes
            return {"access_token": "token"}

    monkeypatch.setattr(msal, "ConfidentialClientApplication", FakeConfidentialClientApplication)
    monkeypatch.setattr(SharePointConstants, "TIMEOUT_SEC", 17)

    token = make_client().get_certificate_app_access_token()

    assert token == "token"
    assert captured["kwargs"]["timeout"] == 17
    assert captured["kwargs"]["instance_discovery"] is False
    assert captured["kwargs"]["authority"] == "https://login.microsoftonline.com/tenant-id"


def test_username_password_auth_passes_timeout_to_msal(monkeypatch):
    import msal

    captured = {}

    class FakePublicClientApplication:
        def __init__(self, *args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs

        def acquire_token_by_username_password(self, username, password, scopes):
            captured["username"] = username
            captured["password"] = password
            captured["scopes"] = scopes
            return {"access_token": "token"}

    monkeypatch.setattr(msal, "PublicClientApplication", FakePublicClientApplication)
    monkeypatch.setattr(SharePointConstants, "TIMEOUT_SEC", 23)

    token = make_client().get_username_password_access_token("user@example.com", "password")

    assert token == "token"
    assert captured["kwargs"]["timeout"] == 23
    assert captured["kwargs"]["instance_discovery"] is False
    assert captured["kwargs"]["authority"] == "https://login.microsoftonline.com/tenant-id"


def test_username_password_auth_timeout_against_slow_mock_authority(monkeypatch, tmp_path):
    with slow_oidc_server(tmp_path, delay_sec=1.0) as (server, cert_path, paths):
        monkeypatch.setattr(SharePointConstants, "TIMEOUT_SEC", 0.2)
        monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(cert_path))
        client = make_client()
        client.MSAL_AUTHORITY_URL_TEMPLATE = "https://localhost:{}/{{}}".format(server.server_port)

        started = time.time()
        with pytest.raises(requests.exceptions.RequestException) as error:
            client.get_username_password_access_token("user@example.com", "password")

        assert "Read timed out" in str(error.value)
        assert time.time() - started < 0.9
        assert "/tenant-id/v2.0/.well-known/openid-configuration" in paths
