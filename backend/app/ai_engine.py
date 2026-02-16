def generate_reply(subject: str, body: str) -> str:
    """
    Temporary stub.
    Later we will connect OpenAI / local model here.
    """
    subject = (subject or "").strip()
    body = (body or "").strip()

    return (
        f"Subject received: {subject}\n\n"
        "Thank you for your email. We have received your message and will respond shortly.\n\n"
        "Regards,\n"
        "AI Mail SaaS"
    )
