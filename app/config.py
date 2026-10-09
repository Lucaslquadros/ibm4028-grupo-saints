"""Configuração da aplicação.

Regra da Aula 04: NENHUM segredo no código. Tudo vem de variável de ambiente.
  - Local  -> arquivo .env (está no .gitignore)
  - Azure  -> App Service > Configuration > Application Settings
  - Prod   -> Azure Key Vault para os segredos sensíveis (aula de Segurança, 09/10)
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Identidade da aplicação -------------------------------------------
    app_name: str = "Projeto 4 API"
    app_version: str = "0.1.0"
    environment: str = "local"  # local | staging | production
    debug: bool = False

    # --- Banco de dados -----------------------------------------------------
    # Local (padrão):  sqlite:///./projeto4.db
    # Azure SQL:       mssql+pyodbc://USER:SENHA@SERVIDOR.database.windows.net:1433/BANCO
    #                  ?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes
    database_url: str = "sqlite:///./projeto4.db"

    # --- Azure Blob Storage -------------------------------------------------
    # Vazio = modo local: os uploads vão para ./uploads_local/ em vez do Blob.
    azure_storage_connection_string: str = ""
    azure_storage_container: str = "uploads"

    # --- CORS ---------------------------------------------------------------
    # Em produção NUNCA use ["*"]. Liste o domínio real do frontend.
    cors_origins: list[str] = [
        "http://localhost:3000",  # React (create-react-app)
        "http://localhost:5173",  # Vite
        # "null" é a origem que o navegador manda quando o HTML é aberto por
        # duplo clique (file://). Serve só para o frontend/painel-teste.html.
        # REMOVA antes de subir para produção.
        "null",
    ]

    # --- Limites ------------------------------------------------------------
    max_upload_mb: int = 10


@lru_cache
def get_settings() -> Settings:
    """Cache: as settings são lidas do ambiente uma única vez por processo."""
    return Settings()


settings = get_settings()
