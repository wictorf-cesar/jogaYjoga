from datetime import datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    Time,
)
from sqlalchemy.orm import relationship

from database import Base

# ── Tabela associativa N:N (espaco <-> esporte) ──
espaco_esportes = Table(
    "espaco_esportes",
    Base.metadata,
    Column("id_espaco", Integer, ForeignKey("espacos.id_espaco"), primary_key=True),
    Column("id_esporte", Integer, ForeignKey("esportes.id_esporte"), primary_key=True),
)


class Endereco(Base):
    __tablename__ = "enderecos"

    id_endereco = Column(Integer, primary_key=True, autoincrement=True)
    cep = Column(String(10))
    logradouro = Column(String(150))
    bairro = Column(String(100))
    nome_municipio = Column(String(100))
    nome_estado = Column(String(2))
    codigo_ibge = Column(Integer)

    def to_dict(self):
        return {
            "id": self.id_endereco,
            "cep": self.cep,
            "logradouro": self.logradouro,
            "bairro": self.bairro,
            "municipio": self.nome_municipio,
            "estado": self.nome_estado,
            "codigo_ibge": self.codigo_ibge,
        }


class Usuario(Base):
    __tablename__ = "usuarios"

    id_usuario = Column(Integer, primary_key=True, autoincrement=True)
    nome_completo = Column(String(150), nullable=False)
    cpf = Column(String(14), unique=True)
    email = Column(String(100), unique=True, nullable=False)
    senha_hash = Column(String(255), nullable=False)
    telefone = Column(String(20))
    data_nascimento = Column(Date)
    id_endereco_residencia = Column(Integer, ForeignKey("enderecos.id_endereco"))
    data_cadastro = Column(DateTime, default=datetime.utcnow)

    endereco = relationship("Endereco", foreign_keys=[id_endereco_residencia])
    proprietario = relationship("Proprietario", back_populates="usuario", uselist=False)
    reservas = relationship("Reserva", back_populates="usuario")
    avaliacoes = relationship("Avaliacao", back_populates="usuario")

    def to_dict(self):
        return {
            "id": self.id_usuario,
            "nome": self.nome_completo,
            "email": self.email,
            "telefone": self.telefone,
            "data_nascimento": self.data_nascimento.isoformat()
            if self.data_nascimento
            else None,
            "data_cadastro": self.data_cadastro.isoformat()
            if self.data_cadastro
            else None,
            "is_proprietario": self.proprietario is not None,
        }


class Proprietario(Base):
    __tablename__ = "proprietarios"

    id_proprietario = Column(Integer, primary_key=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    cnpj = Column(String(18), unique=True)
    razao_social = Column(String(150))
    chave_pix = Column(String(100))

    usuario = relationship("Usuario", back_populates="proprietario")
    espacos = relationship("Espaco", back_populates="proprietario")

    def to_dict(self):
        return {
            "id": self.id_proprietario,
            "id_usuario": self.id_usuario,
            "cnpj": self.cnpj,
            "razao_social": self.razao_social,
            "chave_pix": self.chave_pix,
        }


class Esporte(Base):
    __tablename__ = "esportes"

    id_esporte = Column(Integer, primary_key=True, autoincrement=True)
    nome_esporte = Column(String(50), unique=True, nullable=False)

    espacos = relationship(
        "Espaco", secondary=espaco_esportes, back_populates="esportes"
    )

    def to_dict(self):
        return {
            "id": self.id_esporte,
            "nome": self.nome_esporte,
        }


class Espaco(Base):
    __tablename__ = "espacos"

    id_espaco = Column(Integer, primary_key=True, autoincrement=True)
    nome_espaco = Column(String(150), nullable=False)
    id_endereco = Column(Integer, ForeignKey("enderecos.id_endereco"))
    id_proprietario = Column(Integer, ForeignKey("proprietarios.id_proprietario"))
    latitude = Column(Numeric(10, 8))
    longitude = Column(Numeric(11, 8))
    tamanho_quadra = Column(String(50))
    cobertura = Column(Enum("Tela", "Telhado", "Nenhuma", name="tipo_cobertura"))
    capacidade_pessoas = Column(Integer)
    preco_hora = Column(Numeric(10, 2))
    qtd_quadras = Column(Integer, default=1)

    endereco = relationship("Endereco")
    proprietario = relationship("Proprietario", back_populates="espacos")
    esportes = relationship(
        "Esporte", secondary=espaco_esportes, back_populates="espacos"
    )
    reservas = relationship("Reserva", back_populates="espaco")
    avaliacoes = relationship("Avaliacao", back_populates="espaco")

    def to_dict(self):
        return {
            "id": self.id_espaco,
            "nome": self.nome_espaco,
            "endereco": self.endereco.to_dict() if self.endereco else None,
            "proprietario": self.proprietario.to_dict() if self.proprietario else None,
            "latitude": float(self.latitude) if self.latitude else None,
            "longitude": float(self.longitude) if self.longitude else None,
            "tamanho_quadra": self.tamanho_quadra,
            "cobertura": self.cobertura,
            "capacidade": self.capacidade_pessoas,
            "preco_hora": float(self.preco_hora) if self.preco_hora else None,
            "qtd_quadras": self.qtd_quadras,
            "esportes": [e.nome_esporte for e in self.esportes],
        }


class Reserva(Base):
    __tablename__ = "reservas"

    id_reserva = Column(Integer, primary_key=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    id_espaco = Column(Integer, ForeignKey("espacos.id_espaco"), nullable=False)
    data_reserva = Column(Date, nullable=False)
    hora_inicio = Column(Time, nullable=False)
    hora_fim = Column(Time, nullable=False)
    status_reserva = Column(
        Enum("pendente", "confirmado", "cancelado", name="status_reserva"),
        default="pendente",
    )
    valor_total = Column(Numeric(10, 2))
    criado_em = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("Usuario", back_populates="reservas")
    espaco = relationship("Espaco", back_populates="reservas")

    def to_dict(self):
        return {
            "id": self.id_reserva,
            "id_usuario": self.id_usuario,
            "espaco": self.espaco.nome_espaco if self.espaco else None,
            "data": self.data_reserva.isoformat() if self.data_reserva else None,
            "hora_inicio": self.hora_inicio.isoformat() if self.hora_inicio else None,
            "hora_fim": self.hora_fim.isoformat() if self.hora_fim else None,
            "status": self.status_reserva,
            "valor_total": float(self.valor_total) if self.valor_total else None,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
        }


class Avaliacao(Base):
    __tablename__ = "avaliacoes"

    id_avaliacao = Column(Integer, primary_key=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    id_espaco = Column(Integer, ForeignKey("espacos.id_espaco"), nullable=False)
    id_reserva = Column(Integer, ForeignKey("reservas.id_reserva"))
    nota = Column(Integer, nullable=False)  # 1-5
    comentario = Column(String(500))
    criado_em = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("Usuario", back_populates="avaliacoes")
    espaco = relationship("Espaco", back_populates="avaliacoes")
    reserva = relationship("Reserva")

    def to_dict(self):
        return {
            "id": self.id_avaliacao,
            "id_usuario": self.id_usuario,
            "espaco": self.espaco.nome_espaco if self.espaco else None,
            "nota": self.nota,
            "comentario": self.comentario,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
        }
