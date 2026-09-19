import re

# ---------------------------------------------------------------------------
# Prompt Injection Patterns
# ---------------------------------------------------------------------------
PROMPT_INJECTION_PATTERNS = [
    re.compile(
        r"(?i)\b(ignore|disregard|forget|bypass|override)\s+(all\s+)?(previous|prior|above|system|initial)\s+(instructions|prompts?|rules|directives?|guidelines?)\b"
    ),
    re.compile(
        r"(?i)\b(you are now|act as|dan mode|developer mode|jailbreak|unrestricted mode|god mode)\b"
    ),
    re.compile(
        r"(?i)\b(reveal|display|output|print|show|repeat)\s+(the\s+)?(system\s+prompt|initial\s+instructions|system\s+instructions|developer\s+prompt)\b"
    ),
    re.compile(
        r"(?i)\b(system instructions?:|system prompt:|assistant instructions?:)\b"
    ),
]

# ---------------------------------------------------------------------------
# Dangerous Code / Shell / SQL Injections
# ---------------------------------------------------------------------------
DANGEROUS_EXECUTION_PATTERNS = [
    re.compile(
        r"(?i)\b(__import__|import\s+os|import\s+subprocess|import\s+sys|subprocess\.Popen|os\.system|os\.popen|eval\s*\(|exec\s*\()"
    ),
    re.compile(
        r"(?i)\b(drop\s+table|drop\s+database|truncate\s+table|delete\s+from\s+[a-zA-Z0-9_]+\s*;?)\b"
    ),
    re.compile(
        r"(?i)\b(rm\s+-rf|chmod\s+777|curl\s+.*\|\s*sh|wget\s+.*\|\s*sh)\b"
    ),
]

# ---------------------------------------------------------------------------
# PII Patterns
# ---------------------------------------------------------------------------
EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"
)

# Standard international and domestic phone numbers
PHONE_PATTERN = re.compile(
    r"(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b"
)

# Major credit card formats (Visa, MC, Amex, Discover)
CREDIT_CARD_PATTERN = re.compile(
    r"\b(?:\d{4}[-\s]?){3}\d{4}\b"
)

# SSN / Tax ID (e.g. 000-00-0000)
SSN_PATTERN = re.compile(
    r"\b\d{3}-\d{2}-\d{4}\b"
)

# Bank Account / Routing / IFSC identifiers
BANK_ACCOUNT_PATTERN = re.compile(
    r"\b(?:bank|account|acct|iban|ifsc|routing)\s*[:#]?\s*([A-Za-z0-9]{8,20})\b",
    re.IGNORECASE,
)

IFSC_CODE_PATTERN = re.compile(
    r"\b[A-Z]{4}0[A-Z0-9]{6}\b"
)

# ---------------------------------------------------------------------------
# Disallowed URLs / Network Destinations
# ---------------------------------------------------------------------------
DISALLOWED_URL_PATTERN = re.compile(
    r"(?i)\bhttps?://(localhost|127\.0\.0\.1|0\.0\.0\.0|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|169\.254\.\d{1,3}\.\d{1,3})\b"
)

# Citation ID validation pattern
CITATION_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

