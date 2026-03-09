"""
Mutual TLS (mTLS) — certificate chain verification and rotation.

WHY THIS MATTERS:
In a service mesh, all service-to-service communication is encrypted
with mutual TLS. Unlike regular TLS (where only the server proves its
identity), mTLS requires BOTH sides to present valid certificates.
This ensures:
  - Authentication: you know who you're talking to.
  - Encryption: traffic can't be eavesdropped.
  - Integrity: traffic can't be tampered with.

Key concepts:
  - Certificate chain: root CA -> intermediate CA -> leaf certificate.
    Each certificate is signed by the one above it.
  - Chain verification: check that every cert is valid (not expired),
    and each cert is issued by the previous one in the chain.
  - mTLS handshake: both client and server verify each other's chains.
  - Certificate rotation: replace certificates before they expire to
    avoid downtime. Istio/Linkerd automate this with short-lived certs.
"""

import time
from uuid import uuid4


class Certificate:
    """An X.509 certificate (simplified model).

    In real PKI, a certificate contains a public key, subject name,
    issuer name, validity period, and a digital signature from the
    issuer. We model the fields relevant to chain verification.
    """

    def __init__(
        self,
        subject: str,
        issuer: str,
        valid_from: float,
        valid_to: float,
        is_ca: bool = False,
        serial_number: str = None,
    ):
        self.subject = subject
        self.issuer = issuer
        self.valid_from = valid_from
        self.valid_to = valid_to
        self.is_ca = is_ca
        self.serial_number = serial_number or uuid4().hex[:16]

    def is_valid(self, current_time: float = None) -> bool:
        """Check if this certificate is currently valid (not expired).

        A certificate is valid if current_time falls within
        [valid_from, valid_to].
        """
        now = current_time if current_time is not None else time.time()
        return self.valid_from <= now <= self.valid_to

    def is_issued_by(self, issuer_cert: "Certificate") -> bool:
        """Check if this certificate was issued by the given CA.

        In real PKI, this would verify the digital signature. Here
        we check that this cert's issuer field matches the CA's
        subject field.
        """
        return self.issuer == issuer_cert.subject


class CertificateChain:
    """An ordered chain of certificates from root CA to leaf.

    The chain is ordered: certificates[0] is the root CA,
    certificates[-1] is the leaf (end-entity) certificate.

    Verification checks:
    1. All certificates are currently valid (not expired).
    2. Chain integrity: each cert is issued by the previous one.
    3. The root certificate is a CA (is_ca=True).
    """

    def __init__(self, certificates: list):
        self.certificates = certificates

    def verify(self, current_time: float = None) -> tuple:
        """Verify the certificate chain.

        Returns:
            A tuple of (is_valid: bool, reason: str).
            - (True, "valid") if the chain is valid.
            - (False, reason) with a description of the first error.
        """
        if not self.certificates:
            return False, "empty certificate chain"

        # Check root is a CA
        root = self.certificates[0]
        if not root.is_ca:
            return False, f"root certificate '{root.subject}' is not a CA"

        # Check all certificates are valid
        for cert in self.certificates:
            if not cert.is_valid(current_time):
                return False, f"certificate '{cert.subject}' is expired or not yet valid"

        # Check chain integrity: each cert (except root) is issued by the previous
        for i in range(1, len(self.certificates)):
            if not self.certificates[i].is_issued_by(self.certificates[i - 1]):
                return (
                    False,
                    f"certificate '{self.certificates[i].subject}' is not issued by "
                    f"'{self.certificates[i - 1].subject}'"
                )

        return True, "valid"

    def get_leaf(self) -> "Certificate":
        """Return the leaf (end-entity) certificate."""
        return self.certificates[-1]

    def get_root(self) -> "Certificate":
        """Return the root CA certificate."""
        return self.certificates[0]


class MtlsHandshake:
    """Mutual TLS handshake verification.

    In a normal TLS handshake, only the server presents a certificate.
    In mTLS, the client ALSO presents a certificate. Both sides verify
    each other's certificate chains.

    This is how service meshes authenticate services: service A proves
    it is service A, and service B proves it is service B, before any
    application data flows.
    """

    def handshake(
        self,
        client_chain: CertificateChain,
        server_chain: CertificateChain,
        current_time: float = None,
    ) -> tuple:
        """Perform mutual TLS verification.

        Both client and server certificate chains must be valid.

        Returns:
            A tuple of (success: bool, message: str).
        """
        client_valid, client_reason = client_chain.verify(current_time)
        if not client_valid:
            return False, f"client certificate invalid: {client_reason}"

        server_valid, server_reason = server_chain.verify(current_time)
        if not server_valid:
            return False, f"server certificate invalid: {server_reason}"

        return True, "mutual authentication successful"


class CertificateRotation:
    """Automated certificate rotation to prevent expiry-related outages.

    In production, Istio's Citadel (istiod) automatically rotates
    certificates before they expire. Short-lived certificates (e.g.
    24 hours) limit the blast radius of a compromised key.

    The buffer_days parameter determines how far in advance to rotate:
    if a cert expires within buffer_days from now, it should be rotated.
    """

    def should_rotate(self, cert: Certificate, buffer_days: int = 30) -> bool:
        """Check if a certificate should be rotated soon.

        Returns True if the certificate expires within buffer_days
        of the current time.
        """
        now = time.time()
        buffer_seconds = buffer_days * 86400  # 24 * 60 * 60
        return cert.valid_to <= (now + buffer_seconds)

    def rotate(self, old_cert: Certificate) -> Certificate:
        """Create a new certificate to replace an expiring one.

        The new certificate has:
        - Same subject and issuer as the old certificate.
        - New serial number.
        - Validity starting now and lasting 365 days.
        - Same is_ca flag.

        In production, the new certificate would be signed by the CA.
        """
        now = time.time()
        return Certificate(
            subject=old_cert.subject,
            issuer=old_cert.issuer,
            valid_from=now,
            valid_to=now + 365 * 86400,
            is_ca=old_cert.is_ca,
            serial_number=uuid4().hex[:16],
        )
