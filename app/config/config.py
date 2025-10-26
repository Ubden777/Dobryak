from dataclasses import dataclass
import os
from dotenv import load_dotenv

@dataclass
class DbConfig:
    host: str
    port: int
    user: str
    password: str
    name: str

@dataclass
class TgBot:
    token: str
    payment_provider_token: str

@dataclass
class Config:
    tg_bot: TgBot
    db: DbConfig

def load_config(path: str | None = ".env") -> Config:
    load_dotenv(path)

    return Config(
        tg_bot=TgBot(
            token=os.getenv("BOT_TOKEN"),
            payment_provider_token=os.getenv("PAYMENT_PROVIDER_TOKEN")
        ),
        db=DbConfig(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT")),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            name=os.getenv("DB_NAME")
        )
    )
