from datetime import date, time

from pydantic import BaseModel, Field, field_validator


def normalize_email(value: str) -> str:
    email = value.lower().strip()
    if "@" not in email or "." not in email.rsplit("@", maxsplit=1)[-1]:
        raise ValueError("Email invalido.")
    return email


class EnderecoCreate(BaseModel):
    cep: str | None = Field(default=None, max_length=10)
    logradouro: str | None = Field(default=None, max_length=150)
    bairro: str | None = Field(default=None, max_length=100)
    municipio: str | None = Field(default=None, max_length=100)
    estado: str | None = Field(default=None, max_length=2)


class UserCreate(BaseModel):
    nome_completo: str = Field(min_length=2, max_length=150)
    email: str = Field(max_length=100)
    senha: str = Field(min_length=6, max_length=128)
    cpf: str | None = Field(default=None, max_length=14)
    telefone: str | None = Field(default=None, max_length=20)
    data_nascimento: date | None = None
    id_endereco_residencia: int | None = None
    endereco_residencia: EnderecoCreate | None = None
    is_dono_quadra: bool = False

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)


class UserLogin(BaseModel):
    email: str = Field(max_length=100)
    senha: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)


class UserOut(BaseModel):
    id: int
    nome: str
    email: str
    telefone: str | None = None
    data_nascimento: date | None = None
    id_endereco_residencia: int | None = None
    is_dono_quadra: bool = False
    is_proprietario: bool = False


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class EnderecoOut(BaseModel):
    id: int
    cep: str | None = None
    logradouro: str | None = None
    bairro: str | None = None
    municipio: str | None = None
    estado: str | None = None


class EspacoOut(BaseModel):
    id: int
    nome: str
    endereco: EnderecoOut | None = None
    latitude: float | None = None
    longitude: float | None = None
    cobertura: str | None = None
    tamanho_quadra: str | None = None
    capacidade: int | None = None
    preco_hora: float | None = None
    qtd_quadras: int | None = None
    esportes: list[str] = []


class EspacoCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=150)
    endereco: EnderecoCreate
    esportes: list[str] = Field(default_factory=list)
    cobertura: str | None = Field(default="Nenhuma")
    preco_hora: float | None = Field(default=None, ge=0)
    qtd_quadras: int = Field(default=1, ge=1)

    @field_validator("cobertura")
    @classmethod
    def validate_cobertura(cls, value: str | None) -> str:
        if not value:
            return "Nenhuma"
        normalized = value.strip().title()
        if normalized not in {"Tela", "Telhado", "Nenhuma"}:
            raise ValueError("Cobertura deve ser Tela, Telhado ou Nenhuma.")
        return normalized

    @field_validator("esportes")
    @classmethod
    def validate_esportes(cls, value: list[str]) -> list[str]:
        esportes = [item.strip().title() for item in value if item.strip()]
        if not esportes:
            raise ValueError("Informe pelo menos um esporte.")
        return sorted(set(esportes))


class MonthlyRevenueOut(BaseModel):
    mes: str
    faturamento: float = 0
    reservas: int = 0


class OwnerDashboardOut(BaseModel):
    total_espacos: int = 0
    total_quadras: int = 0
    reservas_mes: int = 0
    faturamento_mes: float = 0
    ticket_medio_mes: float = 0
    faturamento_por_mes: list[MonthlyRevenueOut] = []


class ReservaCreate(BaseModel):
    id_espaco: int
    data_reserva: date
    hora_inicio: time
    hora_fim: time

    @field_validator("data_reserva")
    @classmethod
    def validate_data_reserva(cls, value: date) -> date:
        if value < date.today():
            raise ValueError("A data da reserva nao pode estar no passado.")
        return value

    @field_validator("hora_fim")
    @classmethod
    def validate_hora_fim(cls, value: time, info) -> time:
        hora_inicio = info.data.get("hora_inicio")
        if hora_inicio and value <= hora_inicio:
            raise ValueError("A hora final deve ser maior que a hora inicial.")
        return value


class ReservaOut(BaseModel):
    id: int
    id_usuario: int
    usuario: str | None = None
    id_espaco: int
    espaco: str | None = None
    data: date
    hora_inicio: time
    hora_fim: time
    status: str
    valor_total: float | None = None
    pagamento_status: str | None = None
    pagamento_metodo: str | None = None
    comprovante_url: str | None = None


class ReservaStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"confirmado", "cancelado", "concluido"}:
            raise ValueError("Status invalido.")
        return normalized


class AvailabilitySlotOut(BaseModel):
    hora_inicio: time
    hora_fim: time
    disponivel: bool
    vagas: int = 0


class AvaliacaoCreate(BaseModel):
    id_reserva: int
    nota: int = Field(ge=1, le=5)
    comentario: str | None = Field(default=None, max_length=500)


class AvaliacaoOut(BaseModel):
    id: int
    usuario: str | None = None
    espaco: str | None = None
    nota: int
    comentario: str | None = None
    criado_em: str | None = None


class EspacoDetailOut(EspacoOut):
    favorito: bool = False
    media_avaliacoes: float | None = None
    total_avaliacoes: int = 0
    avaliacoes: list[AvaliacaoOut] = []


class HorarioFuncionamentoCreate(BaseModel):
    dia_semana: int = Field(ge=0, le=6)
    hora_abertura: time
    hora_fechamento: time

    @field_validator("hora_fechamento")
    @classmethod
    def validate_hora_fechamento(cls, value: time, info) -> time:
        hora_abertura = info.data.get("hora_abertura")
        if hora_abertura and value <= hora_abertura:
            raise ValueError("Hora de fechamento deve ser maior que abertura.")
        return value


class HorarioFuncionamentoOut(BaseModel):
    id: int
    id_espaco: int
    dia_semana: int
    hora_abertura: time
    hora_fechamento: time
    ativo: bool = True


class BloqueioHorarioCreate(BaseModel):
    id_espaco: int
    data_bloqueio: date
    hora_inicio: time
    hora_fim: time
    motivo: str | None = Field(default=None, max_length=255)

    @field_validator("hora_fim")
    @classmethod
    def validate_bloqueio_hora_fim(cls, value: time, info) -> time:
        hora_inicio = info.data.get("hora_inicio")
        if hora_inicio and value <= hora_inicio:
            raise ValueError("Hora final deve ser maior que hora inicial.")
        return value


class BloqueioHorarioOut(BaseModel):
    id: int
    id_espaco: int
    data_bloqueio: date
    hora_inicio: time
    hora_fim: time
    motivo: str | None = None


class PagamentoUpdate(BaseModel):
    metodo: str = Field(default="pix", max_length=30)
    comprovante_url: str | None = Field(default=None, max_length=255)


class ChatParseRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    current_step: str | None = Field(default=None, max_length=50)


class ChatParseOut(BaseModel):
    provider: str = "rules"
    in_scope: bool = False
    intent: str = "fora_do_escopo"
    sport: str | None = None
    city: str | None = None
    date_text: str | None = None
    time_text: str | None = None
    space_number: int | None = None
    slot_number: int | None = None
    reservation_id: int | None = None
    confirmation: bool = False
    cancel_flow: bool = False
    normalized_message: str = ""
