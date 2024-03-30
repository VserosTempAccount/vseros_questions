from dataclasses import dataclass

@dataclass()
class Config:
    bot_token: str = "[REDACTED]"

    db_host: str = "[REDACTED]"
    db_port: int = 3306
    db_name: str = "[REDACTED]"
    db_user: str = "[REDACTED]"
    db_passwd: str = "[REDACTED]"

    cypher_key: str = "[REDACTED]"

    bot_url: str = "https://t.me/an_questions_bot"
    bank_creds: str = "[REDACTED]"
    owner_tg_id: int = 1034507582
    owner_tg_tag: str = "[REDACTED]"

    user_agreement_link: str = "https://justmarfix.ru/user_agreement"