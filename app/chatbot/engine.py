from __future__ import annotations

import re
import unicodedata
from copy import deepcopy
from datetime import date, time, timedelta
from enum import StrEnum
from typing import Any


class ChatIntent(StrEnum):
    CREATE_RESERVATION = "CREATE_RESERVATION"
    ASK_AVAILABLE_VENUES = "ASK_AVAILABLE_VENUES"
    SELECT_VENUE = "SELECT_VENUE"
    ASK_AVAILABLE_TIMES = "ASK_AVAILABLE_TIMES"
    SELECT_TIME = "SELECT_TIME"
    CONFIRM_RESERVATION = "CONFIRM_RESERVATION"
    CANCEL_RESERVATION = "CANCEL_RESERVATION"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    CHANGE_RESERVATION_CONTEXT = "CHANGE_RESERVATION_CONTEXT"


class ChatStep(StrEnum):
    IDLE = "IDLE"
    WAITING_CITY = "WAITING_CITY"
    WAITING_VENUE_SELECTION = "WAITING_VENUE_SELECTION"
    WAITING_DATE = "WAITING_DATE"
    WAITING_TIME_SELECTION = "WAITING_TIME_SELECTION"
    WAITING_CONFIRMATION = "WAITING_CONFIRMATION"


class ChatActionType(StrEnum):
    NONE = "NONE"
    FETCH_VENUES = "FETCH_VENUES"
    FETCH_TIMES = "FETCH_TIMES"
    CREATE_RESERVATION = "CREATE_RESERVATION"
    CANCEL_RESERVATION = "CANCEL_RESERVATION"


SPORT_SYNONYMS = {
    "futebol": "futebol",
    "futebol society": "futebol",
    "society": "futebol",
    "futsal": "futebol",
    "pelada": "futebol",
    "bater bola": "futebol",
    "jogar bola": "futebol",
    "beach tennis": "beach_tennis",
    "beach tenis": "beach_tennis",
    "beachtennis": "beach_tennis",
    "tenis de praia": "beach_tennis",
    "tennis de praia": "beach_tennis",
    "tenis": "tenis",
    "tennis": "tenis",
    "volei": "volei",
    "volei de praia": "volei",
    "futevolei": "futevolei",
    "padel": "padel",
    "basquete": "basquete",
    "handebol": "handebol",
}

IN_SCOPE_TERMS = {
    "quadra",
    "reserva",
    "reservar",
    "marcar",
    "pelada",
    "jogar",
    "horario",
    "agenda",
    "cancelar",
    "desmarcar",
    "pagamento",
    "pix",
    "favorito",
    "favoritar",
    "comprovante",
    "futebol",
    "beach",
    "tenis",
    "volei",
    "futevolei",
    "cidade",
    "mapa",
}

TIME_QUESTION_TERMS = {
    "horarios",
    "horario",
    "tem horario",
    "quais horarios",
    "horarios?",
    "tem vaga",
    "disponibilidade",
}

CONFIRMATION_TERMS = {"sim", "ok", "confirmar", "confirmado", "pode", "fechar"}
CANCEL_TERMS = {"cancelar", "sair", "reiniciar", "nao", "não"}


def default_chat_state() -> dict[str, Any]:
    return {
        "step": ChatStep.IDLE.value,
        "sport": None,
        "city": None,
        "date": None,
        "selectedVenue": None,
        "selectedTime": None,
        "venues": [],
        "timeSlots": [],
    }


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value.lower().strip())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def normalize_sport(value: str | None) -> str | None:
    text = normalize_text(value).replace("_", " ")
    if not text:
        return None
    for synonym, canonical in sorted(SPORT_SYNONYMS.items(), key=lambda item: len(item[0]), reverse=True):
        normalized_synonym = normalize_text(synonym)
        if text == normalized_synonym or normalized_synonym in text:
            return canonical
    return text.replace(" ", "_")


def sport_label(sport: str | None) -> str:
    labels = {
        "futebol": "futebol",
        "beach_tennis": "beach tennis",
        "tenis": "tenis",
        "volei": "volei",
        "futevolei": "futevolei",
        "padel": "padel",
    }
    return labels.get(sport or "", (sport or "esporte").replace("_", " "))


def extract_number(message: str) -> int | None:
    match = re.search(r"(?:#\s*)?(\d+)", normalize_text(message))
    return int(match.group(1)) if match else None


def parse_chat_date(message: str | None) -> date | None:
    text = normalize_text(message)
    if "hoje" in text:
        return date.today()
    if "amanha" in text:
        return date.today() + timedelta(days=1)

    for separator in ["/", "-"]:
        for part in text.split():
            if separator not in part:
                continue
            values = part.strip(".,;").split(separator)
            try:
                if len(values) == 2:
                    day, month = [int(item) for item in values]
                    return date(date.today().year, month, day)
                if len(values) == 3:
                    if len(values[0]) == 4:
                        year, month, day = [int(item) for item in values]
                    else:
                        day, month, year = [int(item) for item in values]
                    return date(year, month, day)
            except ValueError:
                continue
    return None


def parse_chat_time(message: str | None) -> time | None:
    text = normalize_text(message).replace("as ", " ")
    for raw_token in text.split():
        token = raw_token.strip(".,;")
        if "h" in token:
            hour_text, minute_text = token.split("h", maxsplit=1)
            minute_text = minute_text or "00"
        elif ":" in token:
            hour_text, minute_text = token.split(":", maxsplit=1)
        else:
            continue
        try:
            hour = int(hour_text)
            minute = int(minute_text)
        except ValueError:
            continue
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return time(hour, minute)
    return None


def parse_date_text(message: str | None) -> str | None:
    parsed = parse_chat_date(message)
    return parsed.isoformat() if parsed else None


def parse_time_text(message: str | None) -> str | None:
    parsed = parse_chat_time(message)
    return parsed.strftime("%H:%M") if parsed else None


def is_in_scope(message: str, parsed: dict[str, Any] | None = None) -> bool:
    if parsed and parsed.get("in_scope") is not None:
        return bool(parsed["in_scope"])
    text = normalize_text(message)
    return any(term in text for term in IN_SCOPE_TERMS)


def detect_sport(message: str, parsed: dict[str, Any] | None = None) -> str | None:
    if parsed:
        sport = normalize_sport(parsed.get("sport"))
        if sport:
            return sport
    text = normalize_text(message)
    for synonym, canonical in sorted(SPORT_SYNONYMS.items(), key=lambda item: len(item[0]), reverse=True):
        if normalize_text(synonym) in text:
            return canonical
    return None


def detect_city(
    message: str,
    parsed: dict[str, Any] | None = None,
    known_cities: list[str] | None = None,
) -> str | None:
    parsed_city = parsed.get("city") if parsed else None
    if parsed_city:
        if known_cities:
            matched = match_name(parsed_city, [{"nome": city} for city in known_cities], key="nome")
            if matched:
                return matched["nome"]
        return str(parsed_city).strip().title()

    text = normalize_text(message)
    for city in sorted(known_cities or [], key=len, reverse=True):
        if normalize_text(city) in text:
            return city
    return None


def detect_date(message: str, parsed: dict[str, Any] | None = None) -> str | None:
    if parsed and parsed.get("date_text"):
        parsed_date = parse_date_text(str(parsed["date_text"]))
        if parsed_date:
            return parsed_date
    return parse_date_text(message)


def detect_time(message: str, parsed: dict[str, Any] | None = None) -> str | None:
    if parsed and parsed.get("time_text"):
        parsed_time = parse_time_text(str(parsed["time_text"]))
        if parsed_time:
            return parsed_time
    return parse_time_text(message)


def detect_intent(message: str, state: dict[str, Any], parsed: dict[str, Any] | None = None) -> ChatIntent:
    text = normalize_text(message)
    step = state.get("step", ChatStep.IDLE.value)
    parsed_intent = (parsed or {}).get("intent")

    if step == ChatStep.WAITING_CONFIRMATION.value and (
        text in CONFIRMATION_TERMS or (parsed or {}).get("confirmation")
    ):
        return ChatIntent.CONFIRM_RESERVATION
    if not is_in_scope(message, parsed):
        return ChatIntent.OUT_OF_SCOPE
    if step == ChatStep.WAITING_TIME_SELECTION.value and is_explicit_time_selection(message, state, parsed):
        return ChatIntent.SELECT_TIME
    if step == ChatStep.WAITING_VENUE_SELECTION.value and is_explicit_venue_selection(message, state, parsed):
        return ChatIntent.SELECT_VENUE
    if any(term in text for term in TIME_QUESTION_TERMS):
        return ChatIntent.ASK_AVAILABLE_TIMES
    if any(term in text for term in ["cancelar", "desmarcar"]):
        return ChatIntent.CANCEL_RESERVATION

    mapped = {
        "criar_reserva": ChatIntent.CREATE_RESERVATION,
        "ver_disponibilidade": ChatIntent.ASK_AVAILABLE_TIMES,
        "buscar_quadras": ChatIntent.ASK_AVAILABLE_VENUES,
        "cancelar_reserva": ChatIntent.CANCEL_RESERVATION,
        "fora_do_escopo": ChatIntent.OUT_OF_SCOPE,
    }.get(str(parsed_intent or ""))
    if mapped:
        return mapped

    if any(term in text for term in ["reservar", "reserva", "marcar", "pelada", "jogar"]):
        return ChatIntent.CREATE_RESERVATION
    if any(term in text for term in ["quadra", "quadras", "onde"]):
        return ChatIntent.ASK_AVAILABLE_VENUES
    return ChatIntent.OUT_OF_SCOPE


def is_explicit_venue_selection(
    message: str,
    state: dict[str, Any],
    parsed: dict[str, Any] | None = None,
) -> bool:
    text = normalize_text(message)
    if any(term in text for term in TIME_QUESTION_TERMS):
        return False
    venues = state.get("venues") or []
    number = (parsed or {}).get("space_number") or extract_number(message)
    if number and 1 <= int(number) <= len(venues):
        return True
    if match_name(message, venues, key="nome"):
        return True
    if text in {"essa", "esse", "quero essa", "quero esse", "esta", "este"} and len(venues) == 1:
        return True
    return False


def is_explicit_time_selection(
    message: str,
    state: dict[str, Any],
    parsed: dict[str, Any] | None = None,
) -> bool:
    slots = state.get("timeSlots") or []
    number = (parsed or {}).get("slot_number") or extract_number(message)
    if number and 1 <= int(number) <= len(slots):
        return True
    selected_time = detect_time(message, parsed)
    return selected_time is not None and any(slot.get("hora_inicio", "")[:5] == selected_time for slot in slots)


def match_name(value: str, items: list[dict[str, Any]], key: str = "nome") -> dict[str, Any] | None:
    text = normalize_text(value)
    for item in sorted(items, key=lambda candidate: len(str(candidate.get(key, ""))), reverse=True):
        name = str(item.get(key, ""))
        normalized_name = normalize_text(name)
        if normalized_name and (text == normalized_name or normalized_name in text):
            return item
    return None


def selected_venue_from_message(
    message: str,
    state: dict[str, Any],
    parsed: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    venues = state.get("venues") or []
    number = (parsed or {}).get("space_number") or extract_number(message)
    if number and 1 <= int(number) <= len(venues):
        return venues[int(number) - 1]
    matched = match_name(message, venues, key="nome")
    if matched:
        return matched
    if normalize_text(message) in {"essa", "esse", "quero essa", "quero esse"} and len(venues) == 1:
        return venues[0]
    return None


def selected_time_from_message(
    message: str,
    state: dict[str, Any],
    parsed: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    slots = state.get("timeSlots") or []
    number = (parsed or {}).get("slot_number") or extract_number(message)
    if number and 1 <= int(number) <= len(slots):
        return slots[int(number) - 1]
    selected_time = detect_time(message, parsed)
    if selected_time:
        for slot in slots:
            if slot.get("hora_inicio", "")[:5] == selected_time:
                return slot
    return None


def detect_context_change(new_input: dict[str, Any], state: dict[str, Any]) -> dict[str, bool]:
    return {
        "sport": bool(new_input.get("sport") and new_input.get("sport") != state.get("sport")),
        "city": bool(new_input.get("city") and new_input.get("city") != state.get("city")),
        "date": bool(new_input.get("date") and new_input.get("date") != state.get("date")),
    }


def merge_context_safely(state: dict[str, Any], new_input: dict[str, Any]) -> tuple[dict[str, Any], dict[str, bool]]:
    merged = deepcopy({**default_chat_state(), **(state or {})})
    changes = detect_context_change(new_input, merged)

    for key in ["sport", "city", "date"]:
        if new_input.get(key):
            merged[key] = new_input[key]

    if changes["sport"] or changes["city"]:
        merged["selectedVenue"] = None
        merged["selectedTime"] = None
        merged["venues"] = []
        merged["timeSlots"] = []
    elif changes["date"]:
        merged["selectedTime"] = None
        merged["timeSlots"] = []

    return merged, changes


def action(action_type: ChatActionType, params: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"type": action_type.value, "params": params or {}}


def response(reply: str, state: dict[str, Any], action_value: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"reply": reply, "state": state, "action": action_value or action(ChatActionType.NONE)}


def decide_next_action(state: dict[str, Any]) -> dict[str, Any]:
    if state.get("sport") and state.get("city") and not state.get("selectedVenue"):
        return action(
            ChatActionType.FETCH_VENUES,
            {"sport": state["sport"], "city": state["city"]},
        )
    if state.get("sport") and state.get("city") and state.get("selectedVenue") and state.get("date") and not state.get("selectedTime"):
        return action(
            ChatActionType.FETCH_TIMES,
            {
                "sport": state["sport"],
                "city": state["city"],
                "venueId": state["selectedVenue"]["id"],
                "date": state["date"],
            },
        )
    if state.get("sport") and state.get("city") and state.get("selectedVenue") and state.get("date") and state.get("selectedTime"):
        return action(
            ChatActionType.CREATE_RESERVATION,
            {
                "sport": state["sport"],
                "city": state["city"],
                "venueId": state["selectedVenue"]["id"],
                "date": state["date"],
                "timeSlotId": state["selectedTime"].get("id"),
                "hora_inicio": state["selectedTime"]["hora_inicio"],
                "hora_fim": state["selectedTime"]["hora_fim"],
            },
        )
    return action(ChatActionType.NONE)


def handleChatMessage(
    userMessage: str,
    currentState: dict[str, Any] | None,
    parsed: dict[str, Any] | None = None,
    known_cities: list[str] | None = None,
) -> dict[str, Any]:
    state = deepcopy({**default_chat_state(), **(currentState or {})})
    intent = detect_intent(userMessage, state, parsed)

    if intent == ChatIntent.OUT_OF_SCOPE:
        return response(
            "Posso ajudar apenas com reservas, quadras, horarios, favoritos, pagamentos e suas reservas.",
            state,
        )

    incoming = {
        "sport": detect_sport(userMessage, parsed),
        "city": detect_city(userMessage, parsed, known_cities),
        "date": detect_date(userMessage, parsed),
        "time": detect_time(userMessage, parsed),
    }
    state, changes = merge_context_safely(state, incoming)
    changed_context = any(changes.values())

    if intent == ChatIntent.CANCEL_RESERVATION:
        return response(
            "Para cancelar, me informe o ID da reserva ou abra Minhas reservas para escolher com seguranca.",
            state,
            action(ChatActionType.CANCEL_RESERVATION),
        )

    if intent == ChatIntent.ASK_AVAILABLE_TIMES and not state.get("selectedVenue"):
        if state.get("venues"):
            return response(
                "Para ver os horarios, primeiro escolha uma das quadras acima pelo numero ou nome.",
                state,
            )
        if state.get("sport") and state.get("city"):
            state["step"] = ChatStep.WAITING_VENUE_SELECTION.value
            return response(
                f"Vou buscar quadras de {sport_label(state['sport'])} em {state['city']} primeiro.",
                state,
                action(ChatActionType.FETCH_VENUES, {"sport": state["sport"], "city": state["city"]}),
            )
        return ask_for_missing_context(state)

    if intent == ChatIntent.SELECT_VENUE:
        selected = selected_venue_from_message(userMessage, state, parsed)
        if not selected:
            return response("Escolha uma quadra pelo numero ou pelo nome.", state)
        state["selectedVenue"] = selected
        state["selectedTime"] = None
        state["timeSlots"] = []
        if not state.get("date"):
            state["step"] = ChatStep.WAITING_DATE.value
            return response(
                f"Quadra escolhida: {selected['nome']}. Para qual data?",
                state,
            )
        state["step"] = ChatStep.WAITING_TIME_SELECTION.value
        return response(
            f"Vou buscar horarios em {selected['nome']} para {state['date']}.",
            state,
            decide_next_action(state),
        )

    if intent == ChatIntent.SELECT_TIME:
        selected = selected_time_from_message(userMessage, state, parsed)
        if not selected:
            return response("Escolha um horario pelo numero da lista ou pela hora.", state)
        state["selectedTime"] = selected
        state["step"] = ChatStep.WAITING_CONFIRMATION.value
        venue = state["selectedVenue"]
        return response(
            f"Confirmar reserva em {venue['nome']} no dia {state['date']} "
            f"das {selected['hora_inicio'][:5]} as {selected['hora_fim'][:5]}? Responda confirmar ou cancelar.",
            state,
        )

    if intent == ChatIntent.CONFIRM_RESERVATION:
        required = [state.get("sport"), state.get("city"), state.get("selectedVenue"), state.get("date"), state.get("selectedTime")]
        if not all(required):
            return response("Ainda falta escolher quadra e horario antes de confirmar.", state)
        return response("Vou confirmar sua reserva.", state, decide_next_action(state))

    if incoming.get("time") and not state.get("selectedTime"):
        state["requestedTime"] = incoming["time"]

    if changed_context and state.get("sport") and state.get("city"):
        state["step"] = ChatStep.WAITING_VENUE_SELECTION.value
        return response(
            f"Entendi, agora e {sport_label(state['sport'])}"
            f"{' para ' + state['date'] if state.get('date') else ''} em {state['city']}. "
            f"Vou buscar quadras de {sport_label(state['sport'])} disponiveis.",
            state,
            action(ChatActionType.FETCH_VENUES, {"sport": state["sport"], "city": state["city"]}),
        )

    if intent in {ChatIntent.CREATE_RESERVATION, ChatIntent.ASK_AVAILABLE_VENUES, ChatIntent.ASK_AVAILABLE_TIMES}:
        if not state.get("sport") or not state.get("city"):
            return ask_for_missing_context(state)
        state["step"] = ChatStep.WAITING_VENUE_SELECTION.value
        return response(
            f"Vou buscar quadras de {sport_label(state['sport'])} em {state['city']}.",
            state,
            action(ChatActionType.FETCH_VENUES, {"sport": state["sport"], "city": state["city"]}),
        )

    return ask_for_missing_context(state)


def ask_for_missing_context(state: dict[str, Any]) -> dict[str, Any]:
    if not state.get("sport"):
        state["step"] = ChatStep.IDLE.value
        return response("Qual esporte voce quer jogar?", state)
    if not state.get("city"):
        state["step"] = ChatStep.WAITING_CITY.value
        return response("Em qual cidade voce quer jogar?", state)
    if not state.get("selectedVenue"):
        state["step"] = ChatStep.WAITING_VENUE_SELECTION.value
        return response(
            f"Vou buscar quadras de {sport_label(state['sport'])} em {state['city']}.",
            state,
            action(ChatActionType.FETCH_VENUES, {"sport": state["sport"], "city": state["city"]}),
        )
    if not state.get("date"):
        state["step"] = ChatStep.WAITING_DATE.value
        return response("Para qual data?", state)
    if not state.get("selectedTime"):
        state["step"] = ChatStep.WAITING_TIME_SELECTION.value
        return response(
            "Vou buscar horarios disponiveis.",
            state,
            decide_next_action(state),
        )
    state["step"] = ChatStep.WAITING_CONFIRMATION.value
    return response("Confirma a reserva?", state)


def venue_supports_sport(venue: dict[str, Any], sport: str) -> bool:
    requested = normalize_sport(sport)
    for venue_sport in venue.get("esportes") or []:
        current = normalize_sport(str(venue_sport))
        if requested == current:
            return True
    return False


def filter_venues_for_state(venues: list[dict[str, Any]], state: dict[str, Any]) -> list[dict[str, Any]]:
    sport = state.get("sport")
    city = state.get("city")
    filtered = []
    for venue in venues:
        if sport and not venue_supports_sport(venue, sport):
            continue
        if city and (venue.get("endereco") or {}).get("municipio") != city:
            continue
        filtered.append(venue)
    return filtered
