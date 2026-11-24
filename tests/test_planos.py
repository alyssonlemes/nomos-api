import unittest

from app.domain.planos import PLANOS, cabe, obter_plano


class PlanosTest(unittest.TestCase):
    def test_tres_opcoes(self):
        self.assertEqual(set(PLANOS), {"essencial", "profissional", "escritorio"})

    def test_codigo_desconhecido_cai_no_essencial(self):
        self.assertEqual(obter_plano(None).codigo, "essencial")
        self.assertEqual(obter_plano("inexistente").usuarios, 3)

    def test_limites_crescem_entre_os_planos(self):
        essencial = PLANOS["essencial"]
        profissional = PLANOS["profissional"]
        escritorio = PLANOS["escritorio"]
        self.assertLess(essencial.usuarios, profissional.usuarios)
        self.assertLess(profissional.usuarios, escritorio.usuarios)
        self.assertLess(essencial.processos, profissional.processos)
        self.assertLess(profissional.processos, escritorio.processos)

    def test_vaga_so_existe_abaixo_do_teto(self):
        self.assertTrue(cabe(2, 3))
        self.assertFalse(cabe(3, 3))


if __name__ == "__main__":
    unittest.main()
