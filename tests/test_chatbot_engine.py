import unittest

from app.chatbot.engine import (
    ChatActionType,
    ChatStep,
    handleChatMessage,
)


class ChatbotEngineTest(unittest.TestCase):
    def test_times_question_does_not_select_venue(self):
        state = {
            "step": ChatStep.WAITING_VENUE_SELECTION.value,
            "sport": "futebol",
            "city": "Recife",
            "date": "2026-05-24",
            "selectedVenue": None,
            "selectedTime": None,
            "venues": [
                {"id": 1, "nome": "Sport Club do Recife", "esportes": ["Futebol Society"]},
                {"id": 2, "nome": "AABB Recife", "esportes": ["Futebol Society"]},
            ],
            "timeSlots": [],
        }

        result = handleChatMessage("horarios?", state)

        self.assertEqual(result["action"]["type"], ChatActionType.NONE.value)
        self.assertEqual(result["state"]["step"], ChatStep.WAITING_VENUE_SELECTION.value)
        self.assertIsNone(result["state"]["selectedVenue"])
        self.assertIn("primeiro escolha", result["reply"])

    def test_context_change_clears_selected_venue_and_time(self):
        state = {
            "step": ChatStep.WAITING_CONFIRMATION.value,
            "sport": "futebol",
            "city": "Recife",
            "date": "2026-05-24",
            "selectedVenue": {"id": 1, "nome": "Sport Club do Recife"},
            "selectedTime": {"id": 1, "hora_inicio": "18:00", "hora_fim": "19:00"},
            "venues": [{"id": 1, "nome": "Sport Club do Recife"}],
            "timeSlots": [{"id": 1, "hora_inicio": "18:00", "hora_fim": "19:00"}],
        }

        result = handleChatMessage(
            "quero marcar uma pelada de beach tennis amanha",
            state,
            known_cities=["Recife"],
        )

        self.assertEqual(result["state"]["sport"], "beach_tennis")
        self.assertEqual(result["state"]["city"], "Recife")
        self.assertEqual(result["state"]["date"], "2026-05-24")
        self.assertIsNone(result["state"]["selectedVenue"])
        self.assertIsNone(result["state"]["selectedTime"])
        self.assertEqual(result["action"]["type"], ChatActionType.FETCH_VENUES.value)

    def test_missing_city_asks_only_city(self):
        result = handleChatMessage("quero marcar beach tennis amanha", {})

        self.assertEqual(result["state"]["sport"], "beach_tennis")
        self.assertEqual(result["state"]["step"], ChatStep.WAITING_CITY.value)
        self.assertEqual(result["action"]["type"], ChatActionType.NONE.value)
        self.assertEqual(result["reply"], "Em qual cidade voce quer jogar?")

    def test_out_of_scope_returns_none_action(self):
        result = handleChatMessage("me manda receita de bolo", {})

        self.assertEqual(result["action"]["type"], ChatActionType.NONE.value)
        self.assertIn("Posso ajudar apenas", result["reply"])

    def test_never_confirms_without_venue_and_time(self):
        state = {
            "step": ChatStep.WAITING_CONFIRMATION.value,
            "sport": "futebol",
            "city": "Recife",
            "date": "2026-05-24",
            "selectedVenue": None,
            "selectedTime": None,
            "venues": [],
            "timeSlots": [],
        }

        result = handleChatMessage("confirmar", state)

        self.assertEqual(result["action"]["type"], ChatActionType.NONE.value)
        self.assertIn("Ainda falta escolher quadra e horario", result["reply"])


if __name__ == "__main__":
    unittest.main()

