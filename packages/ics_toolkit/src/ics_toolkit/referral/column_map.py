"""Required columns and aliases for referral data files."""

REQUIRED_COLUMNS = [
    "Referrer Name",
    "Issue Date",
    "Referral Code",
    "Purchase Manager",
    "Branch",
    "Account Holder",
    "MRDB Account Hash",
    "Cert ID",
]

# Maps common alternative names (lowercase) -> canonical column name.
COLUMN_ALIASES: dict[str, str] = {
    "referrer": "Referrer Name",
    "referrer_name": "Referrer Name",
    "referrer name": "Referrer Name",
    "issue_date": "Issue Date",
    "issue date": "Issue Date",
    "date": "Issue Date",
    "referral_code": "Referral Code",
    "referral code": "Referral Code",
    "code": "Referral Code",
    "purchase_manager": "Purchase Manager",
    "purchase manager": "Purchase Manager",
    "staff": "Purchase Manager",
    "branch": "Branch",
    "branch_id": "Branch",
    "account_holder": "Account Holder",
    "account holder": "Account Holder",
    "new_account": "Account Holder",
    "mrdb_account_hash": "MRDB Account Hash",
    "mrdb account hash": "MRDB Account Hash",
    "mrdb": "MRDB Account Hash",
    "account_hash": "MRDB Account Hash",
    "cert_id": "Cert ID",
    "cert id": "Cert ID",
    "certificate_id": "Cert ID",
}
