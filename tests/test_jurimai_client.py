import unittest

from app.services.jurimai_callback_service import (
    codigo_movimentacao,
    movimentos_no_aviso,
    permanecer_a_tratar,
)
from app.services.jurimai_client import JurimaiError, monitoramento_existente


class JurimaiMonitoramentoTest(unittest.TestCase):
    def test_reaproveita_processo_com_o_mesmo_cnj(self):
        encontrado = monitoramento_existente(
            [
                {"id": 4, "tipo": "cpf", "alvo": "11144477735", "ativo": True},
                {"id": 9, "tipo": "processo", "alvo": "0000001-00.2024.8.26.0100", "ativo": True},
            ],
            "00000010020248260100",
        )
        self.assertIsNotNone(encontrado)
        self.assertEqual(encontrado["id"], 9)

    def test_ignora_monitoramento_encerrado(self):
        self.assertIsNone(
            monitoramento_existente(
                [{"id": 9, "tipo": "processo", "alvo": "00000010020248260100", "ativo": False}],
                "00000010020248260100",
            )
        )

    def test_aviso_documentado_nao_traz_o_texto(self):
        aviso = {
            "evento": "monitoramento.novidade",
            "monitoramento_id": 128,
            "tipo": "processo",
            "alvo": "00000010020248260100",
            "novidades": ["00000010020248260100"],
        }
        self.assertIsNone(movimentos_no_aviso(aviso))

    def test_andamento_embutido_dispensa_nova_consulta(self):
        aviso = {
            "novidades": [
                {"data": "2026-05-20", "nome": "Conclusão para sentença", "descricao": "Conclusos."}
            ]
        }
        movimentos = movimentos_no_aviso(aviso)
        self.assertEqual(len(movimentos), 1)
        self.assertEqual(codigo_movimentacao(movimentos[0]), codigo_movimentacao(movimentos[0]))

    def test_primeira_carga_deixa_so_a_mais_recente_a_tratar(self):
        antigo = {"data": "2024-01-01", "nome": "Distribuição"}
        recente = {"data": "2026-05-20", "nome": "Sentença"}
        meio = {"data": "2025-03-03", "nome": "Audiência"}
        self.assertEqual(permanecer_a_tratar([antigo, recente, meio], True), [recente])

    def test_aviso_seguinte_deixa_todos_a_tratar(self):
        primeiro = {"data": "2026-05-20", "nome": "Conclusão"}
        segundo = {"data": "2026-05-21", "nome": "Sentença"}
        self.assertEqual(permanecer_a_tratar([primeiro, segundo], False), [primeiro, segundo])

    def test_erro_comum_nao_e_monitoramento(self):
        erro = JurimaiError("Token da Juri+ inválido.", 401, {"erro": "nao autorizado"})
        self.assertEqual(erro.status_code, 401)


if __name__ == "__main__":
    unittest.main()
