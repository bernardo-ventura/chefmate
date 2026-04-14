"""
Configuração do banco de dados SQLite.
"""
from sqlmodel import SQLModel, create_engine, Session
from typing import Generator
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# URL do banco de dados
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./database.db")

# Engine do SQLite
# connect_args necessário para SQLite funcionar com múltiplas threads
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set True para ver SQL queries no console
    connect_args={"check_same_thread": False}
)


def create_db_and_tables():
    """Cria o banco de dados e todas as tabelas."""
    SQLModel.metadata.create_all(engine)
    print("✓ Database e tabelas criadas com sucesso!")


def get_session() -> Generator[Session, None, None]:
    """
    Dependency para obter uma sessão do banco de dados.
    Usado em FastAPI e outras partes do código.
    """
    with Session(engine) as session:
        yield session


def get_session_context():
    """Retorna uma sessão para uso em context manager."""
    return Session(engine)
