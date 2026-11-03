# Do zero aos 5 km

Plano de corrida de 12 semanas (5/11/2026 a 30/1/2027) com painel no GitHub Pages
e envio automático dos treinos para o relógio Garmin.

- **Painel:** uma página por sessão, com o passo a passo, o pace, o teto de FC e o que foi feito de fato.
- **Garmin:** todo dia às 06:10, um GitHub Action puxa suas atividades e envia as corridas dos próximos 7 dias
  como treinos estruturados, agendados no calendário. No relógio: *Treinos* ou *Calendário*.

## Configuração (uma vez)

### 1. Gerar o token do Garmin (no seu computador)

```bash
pip install -r requirements.txt
python scripts/make_token.py
```

O script pede e-mail, senha e o código MFA. A senha não é salva. Copie o texto impresso.

### 2. Guardar o token no GitHub

*Settings → Secrets and variables → Actions → New repository secret*

| Nome | Valor |
| --- | --- |
| `GARMIN_TOKENS` | o texto do passo 1 |
| `SITE_PASSWORD` | a senha de login do painel |
| `SECRETS_PAT` (opcional, recomendado) | um *fine-grained token* com acesso só a este repo e permissão **Secrets: Read and write** |

Com o `SECRETS_PAT`, o Action regrava o token renovado a cada execução, e você não precisa repetir o passo 1.
Sem ele, refaça o passo 1 quando o Action começar a falhar no login.

### 3. Ligar o GitHub Pages

*Settings → Pages → Source: **GitHub Actions***. Depois, em *Actions → Sincronizar Garmin e publicar → Run workflow*.

### 4. Definir o teto de FC

Em `config.json`, troque `"hr_cap": null` pela FC do primeiro limiar do seu teste ergométrico
(ou ~75% da FC máxima do teste). Ela vira alerta nos treinos do relógio.

## Ajustar o plano

- **Pace:** depois da sessão de 7/11, mude `pace_offset_sec` em `config.json`. Por exemplo, `30` deixa todas as faixas 30 s/km mais lentas.
- **Sessões:** edite a lista `SESSIONS` em `scripts/build_plan.py`.
- Um treino já enviado e depois alterado é atualizado no Garmin na próxima execução.

## Privacidade

O painel pede senha. As atividades (duração, distância, pace, FC; nunca o trajeto GPS) só são publicadas
criptografadas em `data/vault.json`, com AES-256-GCM e chave derivada da `SITE_PASSWORD` (PBKDF2, 310 mil iterações).
Elas não são gravadas no repositório. O plano em si (`data/plan.json`) é código-fonte e continua público.
Os tokens do Garmin ficam só nos Secrets. Para trocar a senha, mude o Secret e rode o workflow.

## Arquivos

| Caminho | O que faz |
| --- | --- |
| `scripts/build_plan.py` | gera `data/plan.json` |
| `scripts/fetch_garmin.py` | baixa atividades e marca cada sessão como feita, adaptada ou pulada |
| `scripts/push_garmin.py` | cria e agenda os treinos no Garmin (`--dry-run` para testar) |
| `scripts/make_token.py` | gera o token do Garmin (rodar localmente) |
| `site/` | o painel |

O acesso ao Garmin usa a biblioteca não oficial [python-garminconnect](https://github.com/cyberjunky/python-garminconnect).
Se o Garmin mudar o login, atualize a biblioteca em `requirements.txt`.
