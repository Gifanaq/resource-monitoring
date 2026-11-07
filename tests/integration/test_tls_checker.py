import asyncio
import shutil
import ssl
import subprocess
from contextlib import suppress
from datetime import UTC, datetime, timedelta

import pytest

from src.domain.entities.service import Service
from src.domain.entities.tls import TlsState
from src.infrastructure.adapters.tls_checker import TlsCertificateChecker


@pytest.fixture(scope="module")
def certificates(tmp_path_factory):
    root = tmp_path_factory.mktemp("tls")

    executable = shutil.which("openssl")
    assert executable is not None

    def openssl(*args: str) -> None:
        subprocess.run(  # noqa: S603
            [executable, *args], cwd=root, check=True, capture_output=True, timeout=20
        )

    openssl(
        "req",
        "-x509",
        "-newkey",
        "rsa:2048",
        "-nodes",
        "-keyout",
        "ca.key",
        "-out",
        "ca.pem",
        "-days",
        "365",
        "-subj",
        "/CN=TPUMON Test CA",
        "-addext",
        "keyUsage=critical,keyCertSign,cRLSign",
    )
    openssl(
        "req",
        "-newkey",
        "rsa:2048",
        "-nodes",
        "-keyout",
        "server.key",
        "-out",
        "server.csr",
        "-subj",
        "/CN=localhost",
    )
    (root / "index").touch()
    (root / "serial").write_text("01\n")
    (root / "ca.cnf").write_text(
        "[ca]\ndefault_ca=local\n[local]\ndatabase=index\nserial=serial\n"
        "new_certs_dir=.\ncertificate=ca.pem\nprivate_key=ca.key\n"
        "default_md=sha256\npolicy=policy\nx509_extensions=server\n"
        "[policy]\ncommonName=supplied\n[server]\n"
        "basicConstraints=critical,CA:FALSE\n"
        "keyUsage=critical,digitalSignature,keyEncipherment\n"
        "extendedKeyUsage=serverAuth\nsubjectAltName=DNS:localhost\n"
        "authorityKeyIdentifier=keyid,issuer\nsubjectKeyIdentifier=hash\n"
    )
    now = datetime.now(UTC)
    for name, start, end in [
        ("valid", now - timedelta(days=1), now + timedelta(days=30)),
        ("expired", now - timedelta(days=30), now - timedelta(days=1)),
    ]:
        openssl(
            "ca",
            "-batch",
            "-config",
            "ca.cnf",
            "-in",
            "server.csr",
            "-out",
            name + ".pem",
            "-startdate",
            start.strftime("%Y%m%d%H%M%SZ"),
            "-enddate",
            end.strftime("%Y%m%d%H%M%SZ"),
            "-notext",
        )
        (root / "index").write_text("")
    return root


@pytest.mark.parametrize(
    ("certificate", "hostname", "trusted", "expected"),
    [
        ("valid", "localhost", True, TlsState.VALID),
        ("expired", "localhost", True, TlsState.ERROR),
        ("valid", "127.0.0.1", True, TlsState.ERROR),
        ("valid", "localhost", False, TlsState.ERROR),
    ],
)
def test_real_verified_tls_handshake(
    certificates, certificate, hostname, trusted, expected
):
    async def run():
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(
            certificates / (certificate + ".pem"), certificates / "server.key"
        )
        client_context = ssl.create_default_context()
        if trusted:
            client_context.load_verify_locations(certificates / "ca.pem")
        handlers = set()

        async def connected(_reader, writer):
            task = asyncio.current_task()
            handlers.add(task)
            try:
                writer.close()
                with suppress(OSError):
                    await writer.wait_closed()
            finally:
                handlers.discard(task)

        server = await asyncio.start_server(connected, "127.0.0.1", 0, ssl=context)
        async with server:
            port = server.sockets[0].getsockname()[1]
            result = await TlsCertificateChecker(client_context).check(
                Service(1, "local", f"https://{hostname}:{port}", timeout_sec=1)
            )
        if handlers:
            await asyncio.gather(*handlers)
        assert result.state is expected
        if expected is TlsState.ERROR:
            assert result.error == "SSLCertVerificationError"
            assert result.expires_at is None
        else:
            assert result.expires_at > datetime.now(UTC) + timedelta(days=29)

    asyncio.run(run())
