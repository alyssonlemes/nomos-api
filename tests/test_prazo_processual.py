import unittest
from datetime import date

from app.domain.prazo_processual import (
    STATUS_ABERTO,
    STATUS_CONFERIR,
    STATUS_NENHUM,
    calcular_vencimento,
    decidir_prazo,
)


class PrazoProcessualTest(unittest.TestCase):
    def test_cinco_dias_uteis_a_partir_de_terca(self):
        vencimento = calcular_vencimento(date(2024, 10, 1), 5)
        self.assertEqual(vencimento, date(2024, 10, 9))

    def test_pula_feriado_nacional(self):
        vencimento = calcular_vencimento(date(2024, 11, 14), 1)
        self.assertEqual(vencimento, date(2024, 11, 19))

    def test_texto_com_quantidade_de_dias_abre_prazo(self):
        calculado = decidir_prazo(
            tipo="PUBLICACAO",
            conteudo="Fica intimado para manifestação no prazo de 5 dias.",
            data_movimentacao=date(2024, 10, 1),
        )
        self.assertEqual(calculado.status, STATUS_ABERTO)
        self.assertEqual(calculado.dias, 5)
        self.assertEqual(calculado.data_vencimento, date(2024, 10, 9))

    def test_decisao_sem_dias_fica_para_conferir(self):
        calculado = decidir_prazo(
            tipo="ANDAMENTO",
            conteudo="Pedido de Liminar/Antecipação de Tutela",
            texto_extra="Decisão > Concessão > Antecipação de tutela",
            data_movimentacao=date(2024, 10, 1),
        )
        self.assertEqual(calculado.status, STATUS_CONFERIR)
        self.assertIsNone(calculado.data_vencimento)

    def test_juntada_comum_nao_gera_prazo(self):
        calculado = decidir_prazo(
            tipo="ANDAMENTO",
            conteudo="Juntada de petição",
            data_movimentacao=date(2024, 10, 1),
        )
        self.assertEqual(calculado.status, STATUS_NENHUM)


if __name__ == "__main__":
    unittest.main()
