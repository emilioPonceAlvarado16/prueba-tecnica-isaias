import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")


def _load_ssm_parameters() -> None:
    """En AWS los secretos viven en SSM Parameter Store (SecureString) bajo SSM_PREFIX, p.ej. /onb-demo."""
    prefix = os.environ.get("SSM_PREFIX")
    if not prefix:
        return
    import boto3

    ssm = boto3.client("ssm")
    for page in ssm.get_paginator("get_parameters_by_path").paginate(Path=prefix, WithDecryption=True):
        for param in page["Parameters"]:
            os.environ.setdefault(param["Name"].rsplit("/", 1)[-1].upper(), param["Value"])


_load_ssm_parameters()


@dataclass(frozen=True)
class Settings:
    database_url: str = os.environ.get("DATABASE_URL", "")
    openai_api_key: str | None = os.environ.get("OPENAI_API_KEY")
    chat_model: str = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4.1-mini")
    embedding_model: str = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    embedding_dims: int = 1536
    api_port: int = int(os.environ.get("API_PORT", "8010"))
    cors_origins: tuple[str, ...] = tuple(o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(","))
    provisioner: str = os.environ.get("PROVISIONER", "local")          # local | lambda
    provisioner_lambda_name: str = os.environ.get("PROVISIONER_LAMBDA_NAME", "onboarding-cognito-provisioner")
    demo_mode: bool = os.environ.get("DEMO_MODE", "true").lower() == "true"
    policies_dir: Path = REPO_ROOT / "policies" / "docs"
    cache_dir: Path = Path(os.environ.get("CACHE_DIR", str(REPO_ROOT / "backend" / ".cache")))
    # RAG
    rag_top_k: int = 4
    rag_min_score: float = 0.30
    ivfflat_probes: int = int(os.environ.get("IVFFLAT_PROBES", "3"))
    # Reglas (espejo de POL-KYC-001 / POL-PLA-002; ver domain/rules.py)
    min_identity_confidence: float = 0.80
    min_name_match: float = 0.60


settings = Settings()
