import unittest

from app.services.escavador_client import EscavadorError, monitoramento_de_conflito


class EscavadorConflitoTest(unittest.TestCase):
    def test_reaproveita_monitoramento_quando_o_numero_ja_existe(self):
        erro = EscavadorError(
            "Você já monitora este processo",
            422,
            {
                "appends": {
                    "monitoramento": {
                        "id": 17,
                        "status": "PENDENTE",
                        "frequencia": "DIARIA",
                    }
                }
            },
        )
        monitoramento = monitoramento_de_conflito(erro)
        self.assertIsNotNone(monitoramento)
        self.assertEqual(monitoramento["id"], 17)

    def test_outro_erro_nao_vira_monitoramento(self):
        erro = EscavadorError("Token do Escavador inválido.", 401, {"error": "Unauthenticated"})
        self.assertIsNone(monitoramento_de_conflito(erro))


if __name__ == "__main__":
    unittest.main()
