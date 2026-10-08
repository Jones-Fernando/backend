"""Testes de regras financeiras sem depender do Flask."""
import os
from decimal import Decimal

os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("DB_DRIVER", "sqlite")
os.environ.setdefault("TEST_DB_PATH", "/tmp/wepay_pytest.sqlite3")

import pytest

from database.connection import get_connection_context, cursor_for
from models.grupo_model import GrupoModel
from models.participante_model import ParticipanteModel
from models.despesa_model import DespesaModel
from models.despesa_pessoal_model import DespesaPessoalModel
from services.financeiro_service import FinanceiroService


@pytest.fixture(autouse=True)
def database_reset():
    path = os.environ["TEST_DB_PATH"]
    if os.path.exists(path):
        os.remove(path)
    # O módulo de conexão já havia criado o schema na importação; recriamos
    # explicitamente para cada teste usando o test_schema.
    from pathlib import Path
    schema = Path(__file__).resolve().parents[1] / "database" / "test_schema.sql"
    with get_connection_context() as conn:
        conn.executescript(schema.read_text(encoding="utf-8"))
        conn.commit()


def criar_base():
    with get_connection_context() as conn:
        c = cursor_for(conn)
        ids = []
        for i in range(1, 4):
            c.execute(
                "INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)",
                (f"Usuario {i}", f"u{i}@teste.com", "hash"),
            )
            ids.append(c.lastrowid)
        gid = GrupoModel.criar("Teste", "Grupo", ids[0], conn)
        ParticipanteModel.adicionar(gid, ids[0], "admin", conn)
        ParticipanteModel.adicionar(gid, ids[1], "participante", conn)
        ParticipanteModel.adicionar(gid, ids[2], "participante", conn)
        conn.commit()
        c.close()
    return ids, gid


def saldos_por_usuario(gid):
    return {
        int(row["usuario_id"]): Decimal(str(row["saldo"]))
        for row in FinanceiroService.saldos_grupo(gid)
    }


def test_divisao_igual_fecha_centavos():
    assert [r["valor"] for r in FinanceiroService.calcular_divisoes(100, [1, 2, 3], "igual")] == [Decimal("33.34"), Decimal("33.33"), Decimal("33.33")]


def test_divisao_porcentagem_fecha_exatamente():
    rows = FinanceiroService.calcular_divisoes(
        100, [1, 2, 3], "porcentagem", {"1": "33.33", "2": "33.33", "3": "33.34"}
    )
    assert sum((row["valor"] for row in rows), Decimal("0")) == Decimal("100.00")


def test_divisao_por_valores_valida_soma():
    rows = FinanceiroService.calcular_divisoes(
        100, [1, 2, 3], "valores", valores={"1": "10", "2": "20", "3": "70"}
    )
    assert sum((row["valor"] for row in rows), Decimal("0")) == Decimal("100.00")


def test_despesa_e_pagamento_zeram_saldos():
    ids, gid = criar_base()
    FinanceiroService.criar_despesa(gid, ids[0], "Jantar", 100, participantes=ids)
    assert saldos_por_usuario(gid) == {ids[0]: Decimal("66.66"), ids[1]: Decimal("-33.33"), ids[2]: Decimal("-33.33")}
    FinanceiroService.registrar_pagamento(gid, ids[1], ids[0], 33.33)
    FinanceiroService.registrar_pagamento(gid, ids[2], ids[0], 33.33)
    assert saldos_por_usuario(gid) == {ids[0]: Decimal("0.00"), ids[1]: Decimal("0.00"), ids[2]: Decimal("0.00")}


def test_edicao_recalcula_sem_duplicar_despesa():
    ids, gid = criar_base()
    did = FinanceiroService.criar_despesa(gid, ids[0], "Jantar", 100, participantes=ids)
    FinanceiroService.atualizar_despesa(did, "Jantar 2", 120, ids[0], participantes=ids)
    assert len(DespesaModel.buscar_por_id(did)["divisoes"]) == 3
    assert sum((row["valor"] for row in DespesaModel.buscar_por_id(did)["divisoes"]), Decimal("0")) == Decimal("120.00")


def test_despesa_pessoal_com_data_e_receita():
    ids, _ = criar_base()
    DespesaPessoalModel.criar(ids[0], "Mercado", 210, "Alimentação", "despesa", "2026-10-03")
    DespesaPessoalModel.criar(ids[0], "Salario", 1000, "Renda", "receita", "2026-10-03")
    resumo = DespesaPessoalModel.resumo_periodo(ids[0], "2026-10-01", "2026-10-31")
    assert Decimal(str(resumo["despesas"])) == Decimal("210.00")
    assert Decimal(str(resumo["receitas"])) == Decimal("1000.00")
    assert Decimal(str(resumo["saldo"])) == Decimal("790.00")
