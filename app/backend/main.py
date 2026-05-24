import json
import logging
import os
import re
import sys
import time as time_module
import traceback
import unicodedata
from datetime import date, datetime, time, timedelta

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from geopy.exc import GeocoderServiceError, GeocoderTimedOut, GeocoderUnavailable
from geopy.geocoders import Nominatim
import requests
from sqlalchemy import extract, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.backend.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.backend.services.groq_service import (
    GroqServiceError,
    generate_chat_completion,
    get_groq_api_key,
    test_groq_connection,
    validate_groq_environment,
)
from app.backend.routes.chat import router as chat_router
from app.backend.domain.reservations.service import (
    get_owner_reservations,
    get_user_reservations,
)
from app.backend.domain.venues.service import get_owner_venues, get_public_venues
from app.data.seed import seed
from app.database.session import SessionLocal, get_db, init_db
from app.models.entities import (
    BloqueioHorario,
    Endereco,
    Espaco,
    Esporte,
    Avaliacao,
    Favorito,
    HorarioFuncionamento,
    Pagamento,
    Proprietario,
    Reserva,
    Usuario,
)
from app.schemas.api import (
    AvaliacaoCreate,
    AvaliacaoOut,
    AvailabilitySlotOut,
    BloqueioHorarioCreate,
    BloqueioHorarioOut,
    ChatParseOut,
    ChatParseRequest,
    EnderecoOut,
    EspacoCreate,
    EspacoDetailOut,
    EspacoOut,
    HorarioFuncionamentoCreate,
    HorarioFuncionamentoOut,
    MonthlyRevenueOut,
    OwnerDashboardOut,
    PagamentoUpdate,
    ReservaCreate,
    ReservaOut,
    ReservaStatusUpdate,
    TokenOut,
    UserCreate,
    UserLogin,
    UserOut,
)

app = FastAPI(title="Joga & Joga API", version="0.1.0")
app.include_router(chat_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("JOGAYJOGA_AI_MODEL", "openai/gpt-oss-20b")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")


class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[36m",
        logging.INFO: "\033[32m",
        logging.WARNING: "\033[33m",
        logging.ERROR: "\033[31m",
        logging.CRITICAL: "\033[35m",
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, "")
        return f"{color}{super().format(record)}{self.RESET}"


chat_logger = logging.getLogger("jogayjoga.chat")
if not chat_logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        ColorFormatter(
            "%(asctime)s.%(msecs)03d %(levelname)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    chat_logger.addHandler(handler)
chat_logger.setLevel(logging.DEBUG)
chat_logger.propagate = False


def chat_log(tag: str, message: str, **data: object) -> None:
    payload = f" {json.dumps(data, ensure_ascii=False, default=str)}" if data else ""
    chat_logger.info(f"[{tag}] {message}{payload}")


def chat_log_error(tag: str, message: str, exc: Exception | None = None, **data: object) -> None:
    if exc:
        data["error_type"] = type(exc).__name__
        data["error"] = str(exc)
        data["stacktrace"] = traceback.format_exc()
    payload = f" {json.dumps(data, ensure_ascii=False, default=str)}" if data else ""
    chat_logger.error(f"[{tag}] {message}{payload}")


def mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def sanitize_groq_payload(payload: dict) -> dict:
    sanitized = json.loads(json.dumps(payload, ensure_ascii=False, default=str))
    for message in sanitized.get("messages", []):
        content = message.get("content")
        if isinstance(content, str) and len(content) > 1200:
            message["content"] = content[:1200] + "...[truncated]"
    return sanitized


def log_groq_environment() -> None:
    chat_log("ENV", "GROQ_API_KEY carregada", loaded=bool(GROQ_API_KEY))
    chat_log("ENV", "GROQ_API_KEY length", length=len(GROQ_API_KEY or ""))
    chat_log("ENV", "GROQ_API_KEY masked", key=mask_secret(GROQ_API_KEY))
    chat_log("ENV", "Groq config", base_url=GROQ_BASE_URL, model=GROQ_MODEL, timeout_seconds=12)
    validate_groq_environment()


@app.on_event("startup")
def startup() -> None:
    log_groq_environment()
    init_db()
    ensure_seed_data()


@app.middleware("http")
async def debug_exception_middleware(request: Request, call_next):
    started_at = time_module.perf_counter()
    try:
        response = await call_next(request)
        elapsed_ms = round((time_module.perf_counter() - started_at) * 1000, 2)
        if request.url.path.startswith("/ai") or request.url.path.startswith("/health/groq"):
            chat_log(
                "HTTP",
                "Request finalizada",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                elapsed_ms=elapsed_ms,
            )
        return response
    except Exception as exc:
        elapsed_ms = round((time_module.perf_counter() - started_at) * 1000, 2)
        chat_log_error(
            "GLOBAL ERROR",
            "Excecao nao tratada na API",
            exc,
            method=request.method,
            path=request.url.path,
            elapsed_ms=elapsed_ms,
        )
        raise


def ensure_seed_data() -> None:
    with SessionLocal() as db:
        has_spaces = db.scalar(select(Espaco).limit(1)) is not None

    if not has_spaces:
        seed(reset=False)


def user_to_out(user: Usuario) -> UserOut:
    return UserOut(
        id=user.id_usuario,
        nome=user.nome_completo,
        email=user.email,
        telefone=user.telefone,
        data_nascimento=user.data_nascimento,
        id_endereco_residencia=user.id_endereco_residencia,
        is_dono_quadra=bool(user.is_dono_quadra),
        is_proprietario=user.proprietario is not None,
    )


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Usuario:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token ausente.",
        )

    user_id = decode_access_token(authorization.split(" ", maxsplit=1)[1])
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido ou expirado.",
        )

    user = db.get(Usuario, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario nao encontrado.",
        )
    return user


def get_current_owner(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Proprietario:
    if not current_user.is_dono_quadra:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso exclusivo para donos de quadra.",
        )

    owner = current_user.proprietario
    if owner:
        return owner

    owner = Proprietario(id_usuario=current_user.id_usuario)
    db.add(owner)
    db.commit()
    db.refresh(owner)
    return owner


def get_current_player(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    if current_user.is_dono_quadra:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Use uma conta de usuario para fazer reservas.",
        )
    return current_user


def clean_optional_text(value: str | None, *, title_case: bool = False, upper: bool = False) -> str | None:
    if not value:
        return None
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        return None
    if upper:
        return cleaned.upper()
    if title_case:
        return cleaned.title()
    return cleaned


def normalize_chat_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower().strip())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def first_message_number(message: str) -> int | None:
    match = re.search(r"(?:#\s*)?(\d+)", message)
    return int(match.group(1)) if match else None


def extract_chat_time_text(message: str) -> str | None:
    match = re.search(r"\b([01]?\d|2[0-3])(?::|h)?([0-5]\d)?\b", message)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    return f"{hour:02d}:{minute:02d}"


def rule_parse_message(message: str) -> ChatParseOut:
    normalized = normalize_chat_text(message)
    in_scope_terms = [
        "quadra",
        "reserva",
        "reservar",
        "marcar",
        "jogar",
        "pelada",
        "cancelar",
        "desmarcar",
        "horario",
        "agenda",
        "pagamento",
        "comprovante",
        "pix",
        "favorito",
        "favoritar",
        "esporte",
        "futebol",
        "tenis",
        "beach",
        "volei",
        "futevolei",
        "preco",
        "cidade",
        "mapa",
        "minhas reservas",
    ]
    in_scope = any(term in normalized for term in in_scope_terms)
    chat_log("VALIDATOR", "Resultado do validador de dominio", isSportsDomain=in_scope)
    intent = "fora_do_escopo"
    if in_scope:
        if any(term in normalized for term in ["cancelar", "desmarcar"]):
            intent = "cancelar_reserva"
        elif any(term in normalized for term in ["minhas reservas", "ver reservas", "historico"]):
            intent = "ver_reservas"
        elif any(term in normalized for term in ["pix", "pagamento", "comprovante"]):
            intent = "pagamento"
        elif "favorito" in normalized or "favoritar" in normalized:
            intent = "favoritos"
        elif any(term in normalized for term in ["reservar", "reserva", "marcar", "jogar", "pelada", "horario"]):
            intent = "criar_reserva"
        else:
            intent = "buscar_quadras"

    first_number = first_message_number(normalized)
    result = ChatParseOut(
        provider="rules",
        in_scope=in_scope,
        intent=intent,
        date_text=(
            "amanha"
            if "amanha" in normalized
            else "hoje"
            if "hoje" in normalized
            else None
        ),
        time_text=extract_chat_time_text(normalized),
        space_number=first_number,
        slot_number=first_number,
        reservation_id=first_number,
        confirmation=normalized in {"sim", "ok", "confirmar", "pode", "confirmado"},
        cancel_flow=normalized in {"cancelar", "sair", "reiniciar", "nao"},
        normalized_message=normalized,
    )
    chat_log("INTENT", "Intent detectada por regras", intent=result.intent, parsed=result.model_dump())
    return result


def parse_ai_json_response(data: dict) -> dict | None:
    choices = data.get("choices") or []
    if choices:
        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return json.loads(content)

    output_text = data.get("output_text")
    if output_text:
        return json.loads(output_text)

    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                return json.loads(content["text"])
    return None


def service_parse_to_chat_out(parsed: dict, message: str) -> ChatParseOut:
    intent_map = {
        "CREATE_RESERVATION": "criar_reserva",
        "ASK_AVAILABLE_VENUES": "buscar_quadras",
        "SELECT_VENUE": "criar_reserva",
        "ASK_AVAILABLE_TIMES": "ver_disponibilidade",
        "SELECT_TIME": "criar_reserva",
        "CONFIRM_RESERVATION": "criar_reserva",
        "CANCEL_RESERVATION": "cancelar_reserva",
        "OUT_OF_SCOPE": "fora_do_escopo",
        "CHANGE_RESERVATION_CONTEXT": "criar_reserva",
    }
    intent = intent_map.get(str(parsed.get("intent", "")).upper(), "fora_do_escopo")
    date_text = parsed.get("date_text") or parsed.get("date_relative")
    return ChatParseOut(
        provider="groq",
        in_scope=bool(parsed.get("in_scope", intent != "fora_do_escopo")),
        intent=intent,
        sport=parsed.get("sport"),
        city=parsed.get("city"),
        date_text=date_text,
        time_text=parsed.get("time_text"),
        space_number=parsed.get("venue_number") or parsed.get("space_number"),
        slot_number=parsed.get("slot_number"),
        reservation_id=parsed.get("reservation_id"),
        confirmation=bool(parsed.get("confirmation", False)),
        cancel_flow=normalize_chat_text(message) in {"cancelar", "sair", "reiniciar", "nao"},
        normalized_message=normalize_chat_text(message),
    )


def groq_parse_message(payload: ChatParseRequest) -> ChatParseOut:
    if not get_groq_api_key():
        chat_log(
            "GROQ SKIP",
            "GROQ_API_KEY ausente; usando parser por regras",
            key_loaded=False,
            blocking_condition="missing_env_GROQ_API_KEY",
        )
        return rule_parse_message(payload.message)

    try:
        parsed = generate_chat_completion(
            [
                {
                    "role": "user",
                    "content": (
                        f"Etapa atual: {payload.current_step or 'idle'}\n"
                        f"Mensagem: {payload.message}"
                    ),
                }
            ]
        )
        result = service_parse_to_chat_out(parsed, payload.message)
        chat_log("GROQ PARSED", "JSON normalizado para ChatParseOut", parsed=result.model_dump())
        return result
    except GroqServiceError as exc:
        chat_log_error(
            "GROQ ERROR",
            "Servico Groq falhou; usando regras",
            exc,
            code=exc.code,
            details=exc.details,
        )
        return rule_parse_message(payload.message)

    schema = {
        "type": "object",
        "properties": {
            "in_scope": {"type": "boolean"},
            "intent": {
                "type": "string",
                "enum": [
                    "buscar_quadras",
                    "ver_disponibilidade",
                    "criar_reserva",
                    "cancelar_reserva",
                    "ver_reservas",
                    "favoritos",
                    "pagamento",
                    "duvida_app",
                    "fora_do_escopo",
                ],
            },
            "sport": {"type": ["string", "null"]},
            "city": {"type": ["string", "null"]},
            "date_text": {"type": ["string", "null"]},
            "time_text": {"type": ["string", "null"]},
            "space_number": {"type": ["integer", "null"]},
            "slot_number": {"type": ["integer", "null"]},
            "reservation_id": {"type": ["integer", "null"]},
            "confirmation": {"type": "boolean"},
            "cancel_flow": {"type": "boolean"},
            "normalized_message": {"type": "string"},
        },
        "required": [
            "in_scope",
            "intent",
            "sport",
            "city",
            "date_text",
            "time_text",
            "space_number",
            "slot_number",
            "reservation_id",
            "confirmation",
            "cancel_flow",
            "normalized_message",
        ],
        "additionalProperties": False,
    }
    system_prompt = (
        "Voce e um parser de intencoes para um app chamado Joga & Joga. "
        "Sua unica tarefa e transformar a mensagem do usuario em JSON. "
        "O escopo permitido e: buscar quadras, ver disponibilidade, criar reserva, "
        "cancelar reserva, ver reservas, favoritos, pagamento Pix e duvidas do app. "
        "Se a mensagem for fora desse escopo, marque in_scope=false e intent=fora_do_escopo. "
        "Nao responda em linguagem natural. Nao invente dados. Extraia apenas o que estiver no texto. "
        "Normalize sinonimos comuns: pelada, bater bola e jogar bola indicam futebol; "
        "marcar pelada ou marcar horario indicam criar_reserva. "
        "Se houver hora como 18h, 18:00 ou as 18, preencha time_text em HH:MM."
    )
    user_prompt = (
        f"Etapa atual: {payload.current_step or 'idle'}\n"
        f"Mensagem: {payload.message}\n\n"
        "Responda somente com JSON valido seguindo este schema:\n"
        f"{json.dumps(schema, ensure_ascii=False)}"
    )

    try:
        request_payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }
        chat_log(
            "GROQ REQUEST",
            "Enviando request para Groq",
            url=f"{GROQ_BASE_URL.rstrip('/')}/chat/completions",
            model=GROQ_MODEL,
            timeout_seconds=12,
            headers={"Authorization": f"Bearer {mask_secret(GROQ_API_KEY)}", "Content-Type": "application/json"},
        )
        chat_log("GROQ PAYLOAD", "Payload enviado para Groq", payload=sanitize_groq_payload(request_payload))
        started_at = time_module.perf_counter()
        response = requests.post(
            f"{GROQ_BASE_URL.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json=request_payload,
            timeout=12,
        )
        elapsed_ms = round((time_module.perf_counter() - started_at) * 1000, 2)
        chat_log(
            "GROQ RESPONSE",
            "Resposta recebida da Groq",
            status=response.status_code,
            elapsed_ms=elapsed_ms,
            body_preview=response.text[:1000],
        )
        response.raise_for_status()
        parsed = parse_ai_json_response(response.json())
        if not parsed:
            chat_log(
                "GROQ PARSE",
                "Resposta sem JSON parseavel; usando regras",
                blocking_condition="empty_or_unrecognized_groq_response",
            )
            return rule_parse_message(payload.message)
        result = ChatParseOut(provider="groq", **parsed)
        chat_log("GROQ PARSED", "JSON parseado da resposta", parsed=result.model_dump())
        return result
    except requests.Timeout as exc:
        chat_log_error("GROQ ERROR", "Timeout chamando Groq; usando regras", exc, timeout_seconds=12)
        return rule_parse_message(payload.message)
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        body = exc.response.text if exc.response is not None else None
        chat_log_error("GROQ ERROR", "HTTP error chamando Groq; usando regras", exc, status_code=status_code, body=body)
        return rule_parse_message(payload.message)
    except requests.RequestException as exc:
        chat_log_error("GROQ ERROR", "Network error chamando Groq; usando regras", exc)
        return rule_parse_message(payload.message)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        chat_log_error("GROQ ERROR", "Erro parseando resposta da Groq; usando regras", exc)
        return rule_parse_message(payload.message)


def geocode_endereco(endereco: Endereco) -> tuple[float | None, float | None]:
    full_parts = [
        endereco.logradouro,
        endereco.bairro,
        endereco.nome_municipio,
        endereco.nome_estado,
        endereco.cep,
        "Brasil",
    ]
    city_parts = [
        endereco.bairro,
        endereco.nome_municipio,
        endereco.nome_estado,
        "Brasil",
    ]
    queries = [
        ", ".join(part for part in full_parts if part),
        ", ".join(part for part in city_parts if part),
        ", ".join(
            part for part in [endereco.nome_municipio, endereco.nome_estado, "Brasil"] if part
        ),
    ]
    queries = [query for query in dict.fromkeys(queries) if query]
    if not queries:
        return None, None

    geolocator = Nominatim(user_agent="jogayjoga_owner_space_geocoder")
    for query in queries:
        try:
            location = geolocator.geocode(
                query,
                timeout=10,
                country_codes="br",
                addressdetails=False,
            )
        except (GeocoderTimedOut, GeocoderUnavailable, GeocoderServiceError):
            continue

        if location:
            return location.latitude, location.longitude

    return None, None


def ensure_unique_owner_espaco(
    payload: EspacoCreate,
    owner: Proprietario,
    db: Session,
) -> None:
    endereco_payload = payload.endereco
    existing = db.scalar(
        select(Espaco)
        .join(Endereco, Espaco.id_endereco == Endereco.id_endereco)
        .where(
            Espaco.id_proprietario == owner.id_proprietario,
            func.lower(Espaco.nome_espaco) == payload.nome.strip().lower(),
            func.lower(func.coalesce(Endereco.logradouro, ""))
            == (endereco_payload.logradouro or "").strip().lower(),
            func.lower(func.coalesce(Endereco.bairro, ""))
            == (endereco_payload.bairro or "").strip().lower(),
            func.lower(func.coalesce(Endereco.nome_municipio, ""))
            == (endereco_payload.municipio or "").strip().lower(),
        )
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Essa quadra ja foi cadastrada para o seu perfil.",
        )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/groq")
def health_groq() -> dict[str, object]:
    log_groq_environment()
    result = test_groq_connection()
    chat_log("GROQ HEALTH", "Resultado do healthcheck Groq", result=result)
    return result


@app.get("/enderecos", response_model=list[EnderecoOut])
def list_enderecos(db: Session = Depends(get_db)) -> list[EnderecoOut]:
    enderecos = db.scalars(
        select(Endereco).order_by(
            Endereco.nome_municipio,
            Endereco.bairro,
            Endereco.logradouro,
        )
    ).all()
    return [EnderecoOut(**endereco.to_dict()) for endereco in enderecos]


@app.get("/espacos", response_model=list[EspacoOut])
def list_espacos(db: Session = Depends(get_db)) -> list[EspacoOut]:
    espacos = get_public_venues(db)
    return [EspacoOut(**espaco.to_dict()) for espaco in espacos]


def create_residential_address(payload: UserCreate, db: Session) -> int | None:
    if payload.id_endereco_residencia:
        endereco = db.get(Endereco, payload.id_endereco_residencia)
        if not endereco:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Endereco residencial nao encontrado.",
            )
        return payload.id_endereco_residencia

    if not payload.endereco_residencia:
        return None

    endereco_payload = payload.endereco_residencia
    has_address_data = any(
        [
            endereco_payload.cep,
            endereco_payload.logradouro,
            endereco_payload.bairro,
            endereco_payload.municipio,
            endereco_payload.estado,
        ]
    )
    if not has_address_data:
        return None

    endereco = Endereco(
        cep=clean_optional_text(endereco_payload.cep),
        logradouro=clean_optional_text(endereco_payload.logradouro),
        bairro=clean_optional_text(endereco_payload.bairro, title_case=True),
        nome_municipio=clean_optional_text(endereco_payload.municipio, title_case=True),
        nome_estado=clean_optional_text(endereco_payload.estado, upper=True),
    )
    db.add(endereco)
    db.flush()
    return endereco.id_endereco


@app.post("/auth/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> TokenOut:
    email = payload.email.lower().strip()
    existing_user = db.scalar(select(Usuario).where(Usuario.email == email))
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ja existe um usuario com esse email.",
        )

    id_endereco_residencia = create_residential_address(payload, db)

    user = Usuario(
        nome_completo=payload.nome_completo.strip(),
        cpf=payload.cpf.strip() if payload.cpf else None,
        email=email,
        senha_hash=hash_password(payload.senha),
        telefone=payload.telefone.strip() if payload.telefone else None,
        data_nascimento=payload.data_nascimento,
        id_endereco_residencia=id_endereco_residencia,
        is_dono_quadra=payload.is_dono_quadra,
    )
    try:
        db.add(user)
        db.flush()

        if payload.is_dono_quadra:
            db.add(Proprietario(id_usuario=user.id_usuario))

        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email ou CPF ja cadastrado.",
        ) from exc

    db.refresh(user)
    return TokenOut(access_token=create_access_token(user.id_usuario), user=user_to_out(user))


@app.post("/auth/login", response_model=TokenOut)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> TokenOut:
    email = payload.email.lower().strip()
    user = db.scalar(select(Usuario).where(Usuario.email == email))
    if not user or not verify_password(payload.senha, user.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha invalidos.",
        )

    return TokenOut(access_token=create_access_token(user.id_usuario), user=user_to_out(user))


@app.get("/auth/me", response_model=UserOut)
def me(current_user: Usuario = Depends(get_current_user)) -> UserOut:
    return user_to_out(current_user)


@app.post("/ai/parse", response_model=ChatParseOut)
def parse_chat_message(
    payload: ChatParseRequest,
    current_user: Usuario = Depends(get_current_user),
) -> ChatParseOut:
    chat_log(
        "CHAT",
        "Mensagem recebida",
        user_message=payload.message,
        current_step=payload.current_step,
        user_id=current_user.id_usuario,
    )
    try:
        parsed = groq_parse_message(payload)
        chat_log("CHAT", "Parse final retornado ao frontend", parsed=parsed.model_dump())
        return parsed
    except Exception as exc:
        chat_log_error("CHAT ERROR", "Erro global no parser do chatbot; usando regras", exc)
        return rule_parse_message(payload.message)


def reserva_to_out(reserva: Reserva) -> ReservaOut:
    return ReservaOut(
        id=reserva.id_reserva,
        id_usuario=reserva.id_usuario,
        usuario=reserva.usuario.nome_completo if reserva.usuario else None,
        id_espaco=reserva.id_espaco,
        espaco=reserva.espaco.nome_espaco if reserva.espaco else None,
        data=reserva.data_reserva,
        hora_inicio=reserva.hora_inicio,
        hora_fim=reserva.hora_fim,
        status=reserva.status_reserva,
        valor_total=float(reserva.valor_total) if reserva.valor_total else None,
        pagamento_status=reserva.pagamento.status_pagamento if reserva.pagamento else None,
        pagamento_metodo=reserva.pagamento.metodo if reserva.pagamento else None,
        comprovante_url=reserva.pagamento.comprovante_url if reserva.pagamento else None,
    )


def avaliacao_to_out(avaliacao: Avaliacao) -> AvaliacaoOut:
    return AvaliacaoOut(
        id=avaliacao.id_avaliacao,
        usuario=avaliacao.usuario.nome_completo if avaliacao.usuario else None,
        espaco=avaliacao.espaco.nome_espaco if avaliacao.espaco else None,
        nota=avaliacao.nota,
        comentario=avaliacao.comentario,
        criado_em=avaliacao.criado_em.isoformat() if avaliacao.criado_em else None,
    )


def horario_to_out(horario: HorarioFuncionamento) -> HorarioFuncionamentoOut:
    return HorarioFuncionamentoOut(
        id=horario.id_horario,
        id_espaco=horario.id_espaco,
        dia_semana=horario.dia_semana,
        hora_abertura=horario.hora_abertura,
        hora_fechamento=horario.hora_fechamento,
        ativo=bool(horario.ativo),
    )


def bloqueio_to_out(bloqueio: BloqueioHorario) -> BloqueioHorarioOut:
    return BloqueioHorarioOut(
        id=bloqueio.id_bloqueio,
        id_espaco=bloqueio.id_espaco,
        data_bloqueio=bloqueio.data_bloqueio,
        hora_inicio=bloqueio.hora_inicio,
        hora_fim=bloqueio.hora_fim,
        motivo=bloqueio.motivo,
    )


def calculate_reservation_value(espaco: Espaco, payload: ReservaCreate) -> float | None:
    if espaco.preco_hora is None:
        return None

    start_at = datetime.combine(payload.data_reserva, payload.hora_inicio)
    end_at = datetime.combine(payload.data_reserva, payload.hora_fim)
    hours = (end_at - start_at).total_seconds() / 3600
    return round(float(espaco.preco_hora) * hours, 2)


def ensure_reservation_inside_business_hours(
    espaco: Espaco,
    payload: ReservaCreate,
    db: Session,
) -> None:
    weekday = payload.data_reserva.weekday()
    horarios = db.scalars(
        select(HorarioFuncionamento).where(
            HorarioFuncionamento.id_espaco == espaco.id_espaco,
            HorarioFuncionamento.dia_semana == weekday,
            HorarioFuncionamento.ativo == True,
        )
    ).all()
    if not horarios:
        return

    fits_any_window = any(
        payload.hora_inicio >= horario.hora_abertura
        and payload.hora_fim <= horario.hora_fechamento
        for horario in horarios
    )
    if not fits_any_window:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esse horario esta fora do funcionamento da quadra.",
        )


def ensure_reservation_not_blocked(
    espaco: Espaco,
    payload: ReservaCreate,
    db: Session,
) -> None:
    blocked = db.scalar(
        select(BloqueioHorario).where(
            BloqueioHorario.id_espaco == espaco.id_espaco,
            BloqueioHorario.data_bloqueio == payload.data_reserva,
            BloqueioHorario.hora_inicio < payload.hora_fim,
            BloqueioHorario.hora_fim > payload.hora_inicio,
        )
    )
    if blocked:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esse horario foi bloqueado pelo dono da quadra.",
        )


@app.get("/me/reservas", response_model=list[ReservaOut])
def my_reservas(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ReservaOut]:
    reservas = get_user_reservations(db, current_user.id_usuario)
    return [reserva_to_out(reserva) for reserva in reservas]


@app.get("/me/favoritos", response_model=list[EspacoOut])
def my_favoritos(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[EspacoOut]:
    espacos = db.scalars(
        select(Espaco)
        .join(Favorito, Favorito.id_espaco == Espaco.id_espaco)
        .where(Favorito.id_usuario == current_user.id_usuario)
        .order_by(Espaco.nome_espaco)
    ).unique().all()
    return [EspacoOut(**espaco.to_dict()) for espaco in espacos]


@app.post("/me/favoritos/{espaco_id}", response_model=EspacoOut)
def add_favorito(
    espaco_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EspacoOut:
    espaco = db.get(Espaco, espaco_id)
    if not espaco:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quadra nao encontrada.")
    existing = db.scalar(
        select(Favorito).where(
            Favorito.id_usuario == current_user.id_usuario,
            Favorito.id_espaco == espaco_id,
        )
    )
    if not existing:
        db.add(Favorito(id_usuario=current_user.id_usuario, id_espaco=espaco_id))
        db.commit()
    return EspacoOut(**espaco.to_dict())


@app.delete("/me/favoritos/{espaco_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorito(
    espaco_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    favorito = db.scalar(
        select(Favorito).where(
            Favorito.id_usuario == current_user.id_usuario,
            Favorito.id_espaco == espaco_id,
        )
    )
    if favorito:
        db.delete(favorito)
        db.commit()


@app.get("/espacos/{espaco_id}", response_model=EspacoDetailOut)
def espaco_detail(
    espaco_id: int,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> EspacoDetailOut:
    espaco = db.get(Espaco, espaco_id)
    if not espaco:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quadra nao encontrada.")

    current_user_id = None
    if authorization and authorization.lower().startswith("bearer "):
        current_user_id = decode_access_token(authorization.split(" ", maxsplit=1)[1])

    avaliacoes = db.scalars(
        select(Avaliacao)
        .where(Avaliacao.id_espaco == espaco_id)
        .order_by(Avaliacao.criado_em.desc())
        .limit(10)
    ).all()
    avg = db.scalar(select(func.avg(Avaliacao.nota)).where(Avaliacao.id_espaco == espaco_id))
    total = db.scalar(select(func.count(Avaliacao.id_avaliacao)).where(Avaliacao.id_espaco == espaco_id))
    favorito = False
    if current_user_id:
        favorito = db.scalar(
            select(Favorito).where(
                Favorito.id_usuario == current_user_id,
                Favorito.id_espaco == espaco_id,
            )
        ) is not None

    return EspacoDetailOut(
        **EspacoOut(**espaco.to_dict()).model_dump(),
        favorito=favorito,
        media_avaliacoes=round(float(avg), 2) if avg else None,
        total_avaliacoes=int(total or 0),
        avaliacoes=[avaliacao_to_out(avaliacao) for avaliacao in avaliacoes],
    )


def iter_slots(open_at: time, close_at: time) -> list[tuple[time, time]]:
    start = datetime.combine(date.today(), open_at)
    end = datetime.combine(date.today(), close_at)
    slots = []
    while start + timedelta(hours=1) <= end:
        slots.append((start.time(), (start + timedelta(hours=1)).time()))
        start += timedelta(minutes=30)
    return slots


@app.get("/espacos/{espaco_id}/disponibilidade", response_model=list[AvailabilitySlotOut])
def espaco_disponibilidade(
    espaco_id: int,
    data: date,
    db: Session = Depends(get_db),
) -> list[AvailabilitySlotOut]:
    espaco = db.get(Espaco, espaco_id)
    if not espaco:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quadra nao encontrada.")

    horarios = db.scalars(
        select(HorarioFuncionamento).where(
            HorarioFuncionamento.id_espaco == espaco_id,
            HorarioFuncionamento.dia_semana == data.weekday(),
            HorarioFuncionamento.ativo == True,
        )
    ).all()
    windows = [(h.hora_abertura, h.hora_fechamento) for h in horarios] or [(time(6, 0), time(23, 0))]
    capacity = espaco.qtd_quadras or 1
    result = []
    for open_at, close_at in windows:
        for slot_start, slot_end in iter_slots(open_at, close_at):
            reservations = db.scalar(
                select(func.count(Reserva.id_reserva)).where(
                    Reserva.id_espaco == espaco_id,
                    Reserva.data_reserva == data,
                    Reserva.status_reserva != "cancelado",
                    Reserva.hora_inicio < slot_end,
                    Reserva.hora_fim > slot_start,
                )
            )
            blocked = db.scalar(
                select(BloqueioHorario).where(
                    BloqueioHorario.id_espaco == espaco_id,
                    BloqueioHorario.data_bloqueio == data,
                    BloqueioHorario.hora_inicio < slot_end,
                    BloqueioHorario.hora_fim > slot_start,
                )
            )
            vagas = max(capacity - int(reservations or 0), 0)
            result.append(
                AvailabilitySlotOut(
                    hora_inicio=slot_start,
                    hora_fim=slot_end,
                    disponivel=not blocked and vagas > 0,
                    vagas=0 if blocked else vagas,
                )
            )
    return result


@app.post("/reservas", response_model=ReservaOut, status_code=status.HTTP_201_CREATED)
def create_reserva(
    payload: ReservaCreate,
    current_user: Usuario = Depends(get_current_player),
    db: Session = Depends(get_db),
) -> ReservaOut:
    espaco = db.get(Espaco, payload.id_espaco)
    if not espaco:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quadra nao encontrada.",
        )

    ensure_reservation_inside_business_hours(espaco, payload, db)
    ensure_reservation_not_blocked(espaco, payload, db)

    overlapping_count = db.scalar(
        select(func.count(Reserva.id_reserva)).where(
            Reserva.id_espaco == payload.id_espaco,
            Reserva.data_reserva == payload.data_reserva,
            Reserva.status_reserva != "cancelado",
            Reserva.hora_inicio < payload.hora_fim,
            Reserva.hora_fim > payload.hora_inicio,
        )
    )
    capacity = espaco.qtd_quadras or 1
    if int(overlapping_count or 0) >= capacity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esse horario ja esta indisponivel para essa quadra.",
        )

    reserva = Reserva(
        id_usuario=current_user.id_usuario,
        id_espaco=payload.id_espaco,
        data_reserva=payload.data_reserva,
        hora_inicio=payload.hora_inicio,
        hora_fim=payload.hora_fim,
        status_reserva="confirmado",
        valor_total=calculate_reservation_value(espaco, payload),
    )
    db.add(reserva)
    db.commit()
    db.refresh(reserva)
    return reserva_to_out(reserva)


@app.patch("/me/reservas/{reserva_id}/cancelar", response_model=ReservaOut)
def cancel_my_reserva(
    reserva_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReservaOut:
    reserva = db.get(Reserva, reserva_id)
    if not reserva or reserva.id_usuario != current_user.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reserva nao encontrada.",
        )
    if reserva.status_reserva == "cancelado":
        return reserva_to_out(reserva)

    reserva.status_reserva = "cancelado"
    db.commit()
    db.refresh(reserva)
    return reserva_to_out(reserva)


@app.patch("/me/reservas/{reserva_id}/pagamento", response_model=ReservaOut)
def update_my_pagamento(
    reserva_id: int,
    payload: PagamentoUpdate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReservaOut:
    reserva = db.get(Reserva, reserva_id)
    if not reserva or reserva.id_usuario != current_user.id_usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reserva nao encontrada.")
    if reserva.status_reserva == "cancelado":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reserva cancelada nao aceita pagamento.")

    pagamento = reserva.pagamento
    if not pagamento:
        pagamento = Pagamento(
            id_reserva=reserva.id_reserva,
            valor=reserva.valor_total,
            taxa_plataforma=0,
            valor_repasse=reserva.valor_total,
        )
        db.add(pagamento)

    pagamento.metodo = payload.metodo
    pagamento.comprovante_url = payload.comprovante_url
    pagamento.status_pagamento = "pago" if payload.comprovante_url else "pendente"
    db.commit()
    db.refresh(reserva)
    return reserva_to_out(reserva)


@app.post("/me/avaliacoes", response_model=AvaliacaoOut, status_code=status.HTTP_201_CREATED)
def create_my_avaliacao(
    payload: AvaliacaoCreate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AvaliacaoOut:
    reserva = db.get(Reserva, payload.id_reserva)
    if not reserva or reserva.id_usuario != current_user.id_usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reserva nao encontrada.")
    if reserva.status_reserva != "concluido":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A avaliacao so fica disponivel apos a reserva ser concluida.",
        )

    existing = db.scalar(
        select(Avaliacao).where(
            Avaliacao.id_usuario == current_user.id_usuario,
            Avaliacao.id_reserva == reserva.id_reserva,
        )
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Essa reserva ja foi avaliada.")

    avaliacao = Avaliacao(
        id_usuario=current_user.id_usuario,
        id_espaco=reserva.id_espaco,
        id_reserva=reserva.id_reserva,
        nota=payload.nota,
        comentario=payload.comentario,
    )
    db.add(avaliacao)
    db.commit()
    db.refresh(avaliacao)
    return avaliacao_to_out(avaliacao)


@app.get("/owner/reservas", response_model=list[ReservaOut])
def owner_reservas(
    data: date | None = None,
    owner: Proprietario = Depends(get_current_owner),
    db: Session = Depends(get_db),
) -> list[ReservaOut]:
    owner_space_ids = db.scalars(
        select(Espaco.id_espaco).where(Espaco.id_proprietario == owner.id_proprietario)
    ).all()
    reservas = get_owner_reservations(db, owner_space_ids, data)
    return [reserva_to_out(reserva) for reserva in reservas]


@app.patch("/owner/reservas/{reserva_id}/status", response_model=ReservaOut)
def update_owner_reserva_status(
    reserva_id: int,
    payload: ReservaStatusUpdate,
    owner: Proprietario = Depends(get_current_owner),
    db: Session = Depends(get_db),
) -> ReservaOut:
    reserva = db.get(Reserva, reserva_id)
    if not reserva:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reserva nao encontrada.",
        )
    owner_space_ids = db.scalars(
        select(Espaco.id_espaco).where(Espaco.id_proprietario == owner.id_proprietario)
    ).all()
    if reserva.id_espaco not in owner_space_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reserva nao encontrada.",
        )

    reserva.status_reserva = payload.status
    db.commit()
    db.refresh(reserva)
    return reserva_to_out(reserva)


@app.get("/owner/horarios", response_model=list[HorarioFuncionamentoOut])
def owner_horarios(
    owner: Proprietario = Depends(get_current_owner),
    db: Session = Depends(get_db),
) -> list[HorarioFuncionamentoOut]:
    owner_space_ids = db.scalars(
        select(Espaco.id_espaco).where(Espaco.id_proprietario == owner.id_proprietario)
    ).all()
    if not owner_space_ids:
        return []
    horarios = db.scalars(
        select(HorarioFuncionamento)
        .where(HorarioFuncionamento.id_espaco.in_(owner_space_ids))
        .order_by(HorarioFuncionamento.id_espaco, HorarioFuncionamento.dia_semana)
    ).all()
    return [horario_to_out(horario) for horario in horarios]


@app.post("/owner/espacos/{espaco_id}/horarios", response_model=HorarioFuncionamentoOut, status_code=status.HTTP_201_CREATED)
def create_owner_horario(
    espaco_id: int,
    payload: HorarioFuncionamentoCreate,
    owner: Proprietario = Depends(get_current_owner),
    db: Session = Depends(get_db),
) -> HorarioFuncionamentoOut:
    espaco = db.get(Espaco, espaco_id)
    if not espaco or espaco.id_proprietario != owner.id_proprietario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quadra nao encontrada.")

    horario = HorarioFuncionamento(
        id_espaco=espaco_id,
        dia_semana=payload.dia_semana,
        hora_abertura=payload.hora_abertura,
        hora_fechamento=payload.hora_fechamento,
        ativo=True,
    )
    db.add(horario)
    db.commit()
    db.refresh(horario)
    return horario_to_out(horario)


@app.get("/owner/bloqueios", response_model=list[BloqueioHorarioOut])
def owner_bloqueios(
    owner: Proprietario = Depends(get_current_owner),
    db: Session = Depends(get_db),
) -> list[BloqueioHorarioOut]:
    owner_space_ids = db.scalars(
        select(Espaco.id_espaco).where(Espaco.id_proprietario == owner.id_proprietario)
    ).all()
    if not owner_space_ids:
        return []
    bloqueios = db.scalars(
        select(BloqueioHorario)
        .where(BloqueioHorario.id_espaco.in_(owner_space_ids))
        .order_by(BloqueioHorario.data_bloqueio.desc(), BloqueioHorario.hora_inicio)
    ).all()
    return [bloqueio_to_out(bloqueio) for bloqueio in bloqueios]


@app.post("/owner/bloqueios", response_model=BloqueioHorarioOut, status_code=status.HTTP_201_CREATED)
def create_owner_bloqueio(
    payload: BloqueioHorarioCreate,
    owner: Proprietario = Depends(get_current_owner),
    db: Session = Depends(get_db),
) -> BloqueioHorarioOut:
    espaco = db.get(Espaco, payload.id_espaco)
    if not espaco or espaco.id_proprietario != owner.id_proprietario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quadra nao encontrada.")
    bloqueio = BloqueioHorario(
        id_espaco=payload.id_espaco,
        data_bloqueio=payload.data_bloqueio,
        hora_inicio=payload.hora_inicio,
        hora_fim=payload.hora_fim,
        motivo=payload.motivo,
    )
    db.add(bloqueio)
    db.commit()
    db.refresh(bloqueio)
    return bloqueio_to_out(bloqueio)


@app.get("/owner/espacos", response_model=list[EspacoOut])
def owner_espacos(
    owner: Proprietario = Depends(get_current_owner),
    db: Session = Depends(get_db),
) -> list[EspacoOut]:
    espacos = get_owner_venues(db, owner.id_proprietario)
    return [EspacoOut(**espaco.to_dict()) for espaco in espacos]


@app.post("/owner/espacos", response_model=EspacoOut, status_code=status.HTTP_201_CREATED)
def create_owner_espaco(
    payload: EspacoCreate,
    owner: Proprietario = Depends(get_current_owner),
    db: Session = Depends(get_db),
) -> EspacoOut:
    ensure_unique_owner_espaco(payload, owner, db)

    endereco_payload = payload.endereco
    endereco = Endereco(
        cep=clean_optional_text(endereco_payload.cep),
        logradouro=clean_optional_text(endereco_payload.logradouro),
        bairro=clean_optional_text(endereco_payload.bairro, title_case=True),
        nome_municipio=clean_optional_text(endereco_payload.municipio, title_case=True),
        nome_estado=clean_optional_text(endereco_payload.estado, upper=True),
    )
    db.add(endereco)
    db.flush()
    latitude, longitude = geocode_endereco(endereco)
    if latitude is None or longitude is None:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Nao foi possivel encontrar coordenadas para esse endereco. "
                "Confira rua, bairro, cidade, UF e CEP antes de cadastrar."
            ),
        )

    esportes = []
    for nome_esporte in payload.esportes:
        esporte = db.scalar(select(Esporte).where(Esporte.nome_esporte == nome_esporte))
        if not esporte:
            esporte = Esporte(nome_esporte=nome_esporte)
            db.add(esporte)
            db.flush()
        esportes.append(esporte)

    espaco = Espaco(
        nome_espaco=payload.nome.strip(),
        id_endereco=endereco.id_endereco,
        id_proprietario=owner.id_proprietario,
        latitude=latitude,
        longitude=longitude,
        cobertura=payload.cobertura,
        preco_hora=payload.preco_hora,
        qtd_quadras=payload.qtd_quadras,
        esportes=esportes,
    )
    db.add(espaco)
    db.commit()
    db.refresh(espaco)
    return EspacoOut(**espaco.to_dict())


@app.get("/owner/dashboard", response_model=OwnerDashboardOut)
def owner_dashboard(
    owner: Proprietario = Depends(get_current_owner),
    db: Session = Depends(get_db),
) -> OwnerDashboardOut:
    today = date.today()
    owner_space_ids = db.scalars(
        select(Espaco.id_espaco).where(Espaco.id_proprietario == owner.id_proprietario)
    ).all()

    if not owner_space_ids:
        return OwnerDashboardOut()

    total_quadras = db.scalar(
        select(func.coalesce(func.sum(Espaco.qtd_quadras), 0)).where(
            Espaco.id_espaco.in_(owner_space_ids)
        )
    )

    current_month_rows = db.execute(
        select(
            func.count(Reserva.id_reserva),
            func.coalesce(func.sum(Reserva.valor_total), 0),
        ).where(
            Reserva.id_espaco.in_(owner_space_ids),
            extract("year", Reserva.data_reserva) == today.year,
            extract("month", Reserva.data_reserva) == today.month,
            Reserva.status_reserva != "cancelado",
        )
    ).one()

    monthly_rows = db.execute(
        select(
            extract("year", Reserva.data_reserva).label("ano"),
            extract("month", Reserva.data_reserva).label("mes"),
            func.count(Reserva.id_reserva).label("reservas"),
            func.coalesce(func.sum(Reserva.valor_total), 0).label("faturamento"),
        )
        .where(
            Reserva.id_espaco.in_(owner_space_ids),
            Reserva.status_reserva != "cancelado",
        )
        .group_by("ano", "mes")
        .order_by("ano", "mes")
    ).all()

    reservas_mes = int(current_month_rows[0] or 0)
    faturamento_mes = float(current_month_rows[1] or 0)

    return OwnerDashboardOut(
        total_espacos=len(owner_space_ids),
        total_quadras=int(total_quadras or 0),
        reservas_mes=reservas_mes,
        faturamento_mes=faturamento_mes,
        ticket_medio_mes=faturamento_mes / reservas_mes if reservas_mes else 0,
        faturamento_por_mes=[
            MonthlyRevenueOut(
                mes=f"{int(row.ano):04d}-{int(row.mes):02d}",
                faturamento=float(row.faturamento or 0),
                reservas=int(row.reservas or 0),
            )
            for row in monthly_rows
        ],
    )
