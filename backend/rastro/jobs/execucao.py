"""Registro de execuções em `execucao_job` (progresso para retomada e resumo final)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text

from rastro.db.conexao import transacao


class Execucao:
    """Uma execução de job. Se houver execução anterior não concluída do mesmo tipo, retoma o progresso."""

    def __init__(self, tipo: str, retomar: bool = True) -> None:
        self.tipo = tipo
        self.progresso: dict[str, Any] = {}
        with transacao() as conn:
            anterior = None
            if retomar:
                anterior = conn.execute(
                    text(
                        "SELECT id, progresso FROM execucao_job WHERE tipo = :t"
                        " AND status IN ('rodando', 'erro') ORDER BY id DESC LIMIT 1"
                    ),
                    {"t": tipo},
                ).first()
            if anterior:
                self.id = anterior.id
                self.progresso = anterior.progresso or {}
                conn.execute(text("UPDATE execucao_job SET status = 'rodando' WHERE id = :id"), {"id": self.id})
            else:
                self.id = conn.execute(
                    text("INSERT INTO execucao_job (tipo) VALUES (:t) RETURNING id"), {"t": tipo}
                ).scalar_one()

    def salvar(self, **campos: Any) -> None:
        self.progresso.update(campos)
        with transacao() as conn:
            conn.execute(
                text("UPDATE execucao_job SET progresso = CAST(:p AS jsonb) WHERE id = :id"),
                {"p": json.dumps(self.progresso, default=str), "id": self.id},
            )

    def concluir(self, resumo: dict[str, Any], status: str = "concluido") -> None:
        with transacao() as conn:
            conn.execute(
                text(
                    "UPDATE execucao_job SET status = :s, fim = now(), resumo = CAST(:r AS jsonb),"
                    " progresso = CAST(:p AS jsonb) WHERE id = :id"
                ),
                {
                    "s": status,
                    "r": json.dumps(resumo, default=str),
                    "p": json.dumps(self.progresso, default=str),
                    "id": self.id,
                },
            )

    def falhar(self, erro: str) -> None:
        with transacao() as conn:
            conn.execute(
                text(
                    "UPDATE execucao_job SET status = 'erro', resumo = CAST(:r AS jsonb),"
                    " progresso = CAST(:p AS jsonb) WHERE id = :id"
                ),
                {
                    "r": json.dumps({"erro": erro[:2000]}),
                    "p": json.dumps(self.progresso, default=str),
                    "id": self.id,
                },
            )
