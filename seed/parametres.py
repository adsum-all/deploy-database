"""Real default system parameters for the ADSUM ``parametre`` table.

These are configuration defaults, not fictional business data. Each value is a
documented default that the organization direction confirms before production
(category and description make the intent explicit). No member, presence,
commission or other content data is seeded here (Constitution I1).
"""
from __future__ import annotations

# (cle, valeur, categorie, description)
DEFAULT_PARAMETERS: list[tuple[str, object, str, str]] = [
    (
        "retention_presence_jours",
        1095,
        "rgpd",
        "Retention of attendance history in days before anonymization or deletion. "
        "Default 36 months (cahier section 10.4). To confirm with the DPO.",
    ),
    (
        "retention_audit_jours",
        730,
        "rgpd",
        "Retention of audit log entries in days. Default 24 months, read restricted. "
        "To confirm with the DPO.",
    ),
    (
        "inactivite_anonymisation_jours",
        1095,
        "rgpd",
        "Inactivity period in days after which an inactive member is anonymized or "
        "deleted. Default 36 months. To confirm with the DPO.",
    ),
    (
        "seuil_assiduite",
        0.5,
        "assiduite",
        "Attendance ratio over the observation window below which a member is flagged "
        "as disengaging. Default 0.5 (50 percent). To confirm with the direction.",
    ),
    (
        "fenetre_assiduite_jours",
        90,
        "assiduite",
        "Observation window in days used to compute the attendance ratio. Default 90 days.",
    ),
    (
        "fenetre_scan_anti_doublon_secondes",
        0,
        "scan",
        "Extra anti duplicate window in seconds at check-in. The UNIQUE(membre, evenement) "
        "constraint already guarantees one presence per event, so the default is 0.",
    ),
    (
        "qr_version_cle_active",
        1,
        "securite",
        "Active QR signing key version (Ed25519). Incremented on key rotation; terminals "
        "verify with the matching public key version.",
    ),
]
