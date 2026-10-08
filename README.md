# WEPAY Backend

Backend REST do WEPAY usando Python + Flask + MySQL.

## Arquitetura

`routes -> controllers -> services -> models -> database`

A regra financeira usa como fonte de verdade:

`despesas + despesa_divisoes + pagamentos`

A tabela `saldos` é recalculada a partir desses eventos.

## Configuração

1. Copie `.env.example` para `.env`.
2. Preencha as credenciais do MySQL.
3. Defina uma `SECRET_KEY` forte.
4. Configure SMTP somente se quiser email real.

O banco `wepay_db` e as tabelas podem ser criados automaticamente se o usuário do MySQL tiver permissão para criar banco.

## Instalação

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

## Execução

```bash
python app.py
```

API base local:

`http://127.0.0.1:5000`

## Testes

Para executar os testes:

```bash
pytest -q
```

Os testes automatizados usam SQLite apenas como banco temporário de teste. O banco oficial da aplicação permanece MySQL.
