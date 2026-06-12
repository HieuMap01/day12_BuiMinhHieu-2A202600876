"""VinBank guarded mock agent for the Day 12 production deployment.

This module packages the strongest deployable part from the previous labs:
Day 11's guardrail idea. It keeps the Render service dependency-light while
still showing a real AI product behavior: input safety checks, topic control,
banking answers, and output redaction.
"""
import re
import time


ALLOWED_TOPICS = [
    "banking", "bank", "account", "transaction", "transfer", "loan",
    "interest", "savings", "credit", "deposit", "withdrawal", "balance",
    "payment", "card", "atm", "vinbank",
    "tai khoan", "giao dich", "tiet kiem", "lai suat", "chuyen tien",
    "the tin dung", "so du", "vay", "ngan hang",
]

BLOCKED_TOPICS = [
    "hack", "exploit", "weapon", "drug", "illegal", "violence", "gambling",
    "bomb", "kill", "steal", "malware", "phishing",
]

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions|rules|directives)",
    r"(forget|disregard|override|bypass)\s+(your\s+)?(instructions|rules|policy|safety|guardrails)",
    r"\byou\s+are\s+now\b|\bDAN\b|\bunrestricted\s+(ai|assistant)",
    r"(reveal|show|print|export|translate|dump).{0,80}(system\s+prompt|instructions|developer\s+message|internal\s+note)",
    r"(admin\s+password|api[_\s-]?key|secret|credential|database\s+(host|endpoint)|\.internal)",
    r"(base64|rot13|hex|encode|decode).{0,80}(prompt|instruction|secret|credential|api\s*key)",
    r"(pretend|act)\s+as\s+(an?\s+)?(unrestricted|admin|developer|auditor|ciso|root)",
    r"(bo qua|bỏ qua|hay tiet lo|tiet lo|cho toi xem|cho tôi xem).{0,80}(huong dan|mat khau|system prompt|api key)",
]

PII_PATTERNS = {
    "VN phone number": r"(?<!\d)0\d{9,10}(?!\d)",
    "Email": r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}",
    "National ID": r"\b(?:\d{9}|\d{12})\b",
    "API key": r"\bsk-[a-zA-Z0-9_-]+\b",
    "Password": r"\b(?:admin\s*)?password\s*(?:is|=|:)?\s*['\"]?[A-Za-z0-9@#$%^&*._-]{4,}['\"]?",
    "Internal host": r"\b[a-zA-Z0-9.-]+\.internal(?::\d+)?\b",
    "Connection string": r"\b(?:postgres|mysql|mongodb|redis)://[^\s]+",
}


def detect_injection(user_input: str) -> bool:
    """Return True when the prompt tries to bypass safety or leak secrets."""
    if not user_input or not user_input.strip():
        return False
    return any(
        re.search(pattern, user_input, re.IGNORECASE | re.DOTALL)
        for pattern in INJECTION_PATTERNS
    )


def topic_filter(user_input: str) -> bool:
    """Return True when the question is outside the VinBank support scope."""
    text = user_input.lower().strip()
    if not text or len(text) > 2000:
        return True
    if any(topic in text for topic in BLOCKED_TOPICS):
        return True
    return not any(topic in text for topic in ALLOWED_TOPICS)


def redact_sensitive_text(response: str) -> tuple[str, list[str]]:
    """Redact PII/secrets from a generated answer."""
    issues: list[str] = []
    redacted = response
    for name, pattern in PII_PATTERNS.items():
        if re.search(pattern, redacted, re.IGNORECASE):
            issues.append(name)
            redacted = re.sub(pattern, "[REDACTED]", redacted, flags=re.IGNORECASE)
    return redacted, issues


def _banking_answer(question: str) -> str:
    """Deterministic banking answer used when no external LLM key is provided."""
    text = question.lower()

    if any(word in text for word in ["interest", "lai suat", "savings", "tiet kiem"]):
        return (
            "VinBank savings support: for a term-deposit question, compare the "
            "latest rate in the official app before making a decision. A typical "
            "safe next step is to choose the term, amount, and whether you want "
            "interest paid monthly or at maturity."
        )
    if any(word in text for word in ["transfer", "chuyen tien", "payment", "pay"]):
        return (
            "VinBank transfer support: open the app, choose Transfer, verify the "
            "recipient name, amount, fee, and OTP, then save the receipt. If the "
            "recipient name does not match, stop and check the account number."
        )
    if any(word in text for word in ["balance", "so du", "account", "tai khoan"]):
        return (
            "VinBank account support: you can check balance and recent transactions "
            "in mobile banking or at an ATM. I will not ask for your password, OTP, "
            "card PIN, or full identity number."
        )
    if any(word in text for word in ["loan", "vay", "credit", "card", "the tin dung"]):
        return (
            "VinBank loan/card support: review the interest rate, repayment date, "
            "late-fee policy, and required documents before applying. For private "
            "eligibility checks, use the official VinBank channel."
        )
    if any(word in text for word in ["docker", "deploy", "cloud", "render", "health"]):
        return (
            "The production wrapper is running correctly on the cloud. This endpoint "
            "adds API-key auth, rate limiting, cost guard, health checks, and the "
            "Day 11 VinBank guardrail agent behind POST /ask."
        )
    return (
        "I can help with VinBank banking questions about accounts, transfers, "
        "savings, loans, cards, balances, and payments. Please share the banking "
        "task you want to complete, without passwords, OTPs, or full ID numbers."
    )


def ask(question: str, delay: float = 0.1) -> str:
    """Return a guarded VinBank agent answer."""
    time.sleep(delay)

    if detect_injection(question):
        return (
            "Blocked by input guardrail: I cannot process requests that try to "
            "reveal internal instructions, credentials, system prompts, or hidden "
            "configuration. I can still help with normal VinBank banking questions."
        )

    if topic_filter(question):
        return (
            "Blocked by topic guardrail: I only answer VinBank banking topics such "
            "as accounts, transfers, savings, loans, cards, balances, and payments."
        )

    answer = _banking_answer(question)
    redacted, issues = redact_sensitive_text(answer)
    if issues:
        return f"{redacted}\n\nOutput guardrail redacted: {', '.join(issues)}."
    return redacted


def ask_stream(question: str):
    """Yield a mock answer token by token."""
    response = ask(question)
    for word in response.split():
        time.sleep(0.05)
        yield word + " "
