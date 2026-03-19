# ⚽ Copa UNASP 2026 — Sistema de Leilão (Versão Completa)

> Sistema web com backend, banco de dados e tela de telão. Desenvolvido para gerenciamento de leilão ao vivo com múltiplos dispositivos em simultâneo.

---

## 📋 Índice

- [Arquitetura](#-arquitetura)
- [Como Rodar](#-como-rodar)
- [Páginas](#-páginas)
- [API](#-api)
- [Como Personalizar](#-como-personalizar)
- [Estrutura de Arquivos](#-estrutura-de-arquivos)

---

## 🏗️ Arquitetura

```
Dispositivo A (Admin)   ──┐
Dispositivo B (Telão)   ──┤──► Python Server + SQLite (fonte da verdade)
Dispositivo C (Celular) ──┘
```

- **Backend:** Python 3 puro, sem dependências externas
- **Banco:** SQLite (arquivo `database.db`)
- **Frontend:** HTML + CSS + JS puro, duas páginas
- **Comunicação:** REST API + polling a cada 2 segundos
- **Regra principal:** toda lógica de negócio fica **somente no backend**

---

## 🚀 Como Rodar

### Pré-requisitos
- Python 3.8 ou superior (já vem instalado no Mac e Linux)
- Windows: baixar em [python.org](https://python.org)

### 1. Iniciar o servidor

```bash
cd backend
python3 server.py
```

Saída esperada:
```
╔══════════════════════════════════════════════════╗
║     ⚽  COPA UNASP 2026 — Servidor de Leilão     ║
╚══════════════════════════════════════════════════╝

  ✅ 9 craques inseridos no banco
  ✅ Banco de dados pronto

  🌐 Servidor: http://localhost:3000
  📋 Admin  →  http://localhost:3000/admin
  📺 Telão  →  http://localhost:3000/telao
```

### 2. Abrir as páginas

| Página | URL | Uso |
|--------|-----|-----|
| Admin | `http://localhost:3000/admin` | Operador registra as compras |
| Telão | `http://localhost:3000/telao` | Projetado na TV/datashow |

### 3. Uso em rede local (múltiplos dispositivos)

Para acessar de outros dispositivos na mesma rede Wi-Fi:

1. Descubra o IP do computador servidor:
   - **Mac/Linux:** `ifconfig | grep "inet "` ou `ip addr`
   - **Windows:** `ipconfig`

2. Substitua `localhost` pelo IP encontrado:
   - Admin: `http://192.168.x.x:3000/admin`
   - Telão: `http://192.168.x.x:3000/telao`

> ⚠️ O computador servidor **não pode dormir** enquanto o leilão estiver acontecendo.

---

## 📺 Páginas

### Admin (`/admin`)
- Formulário de registro de compras
- Seleção de craque (dropdown ou clique no cartão)
- Botões de posição: 🧱 Fixo / ⚡ Ala / 🎯 Pivô
- Grid completo dos craques com saldos
- Gráfico comparativo de saldos
- Histórico filtrado por craque
- Botão "Gerar Relatório Final" (modal copiável)
- Indicador de conexão com o servidor

### Telão (`/telao`)
- **Sem formulários** — somente visualização
- Banner animado a cada nova compra
- Ranking lateral (ordenado por saldo)
- Grid dos 9 craques com elencos
- Feed das últimas 10 compras
- Atualização automática sem reload

---

## 🔌 API

### `GET /api/craques`
Retorna todos os craques com saldos atualizados.

```json
[
  {
    "id": 1,
    "nome": "Araribóia",
    "selecao": "Brasil",
    "bandeira": "🇧🇷",
    "cor": "#009C3B",
    "cor_sec": "#FFDF00",
    "emoji": "⚽",
    "saldo": 85000
  }
]
```

### `GET /api/compras`
Retorna histórico completo, mais recente primeiro.

```json
[
  {
    "id": 3,
    "craque_id": 1,
    "craque": "Araribóia",
    "selecao": "Brasil",
    "bandeira": "🇧🇷",
    "jogador": "Vinicius Jr.",
    "posicao": "Ala",
    "valor": 15000,
    "timestamp": "2026-03-18 20:00:00"
  }
]
```

### `POST /api/compras`
Registra uma compra. O backend valida saldo e executa em transação atômica.

**Request:**
```json
{
  "craque_id": 1,
  "jogador": "Vinicius Jr.",
  "posicao": "Ala",
  "valor": 15000
}
```

**Resposta (sucesso):**
```json
{ "ok": true, "mensagem": "Vinicius Jr. comprado com sucesso!", "novo_saldo": 85000 }
```

**Resposta (erro):**
```json
{ "erro": "Saldo insuficiente. Araribóia tem apenas 5.000 créditos" }
```

### `POST /api/reset`
Apaga todas as compras e redefine saldos. Para ativar o botão na interface: `Shift + Alt + R`.

---

## 🎨 Como Personalizar

### Alterar nomes e seleções dos craques

Edite a lista `CRAQUES_INICIAIS` em `backend/server.py`:

```python
CRAQUES_INICIAIS = [
    # (id, nome,        selecao,     bandeira, cor_primaria, cor_secundaria, emoji)
    (1, "Araribóia",   "Brasil",    "🇧🇷",    "#009C3B",    "#FFDF00",      "⚽"),
    (2, "Cruzeirense", "Argentina", "🇦🇷",    "#74ACDF",    "#FFFFFF",      "🏆"),
    # ... adicione ou edite livremente
]
```

> ⚠️ Após editar, **apague o arquivo `database.db`** antes de reiniciar o servidor para que os novos dados sejam inseridos.

### Alterar saldo inicial

```python
SALDO_INICIAL = 100_000   # linha 13 de server.py
```

### Alterar a porta do servidor

```python
PORT = 3000   # linha 10 de server.py
```

### Alterar cores do tema

Edite as variáveis em `frontend/css/style.css`:

```css
:root {
  --vermelho: #E8003D;
  --azul:     #0033A0;
  --amarelo:  #FFD100;
  --roxo:     #6B1FA8;
}
```

### Alterar intervalo de polling

Em `frontend/js/main.js`:
```js
const POLL_INTERVAL = 2000;  // milissegundos (2000 = 2 segundos)
```

---

## 📁 Estrutura de Arquivos

```
projeto/
│
├── backend/
│   ├── server.py       ← Servidor HTTP + API REST + SQLite
│   └── database.db     ← Criado automaticamente na primeira execução
│
└── frontend/
    ├── admin.html      ← Painel do operador
    ├── telao.html      ← Tela pública (projetor/TV)
    ├── css/
    │   ├── style.css   ← Estilos compartilhados
    │   └── telao.css   ← Estilos exclusivos do telão
    ├── js/
    │   └── main.js     ← Renderização e utilitários compartilhados
    └── img/
        └── brasoes/    ← (opcional) imagens de brasões
```

---

## ✅ Checklist antes do evento

- [ ] Servidor iniciado no computador principal
- [ ] Admin acessível no navegador do operador
- [ ] Telão acessível e projetado na TV/datashow
- [ ] Testar uma compra de ponta a ponta
- [ ] Testar erro de saldo insuficiente
- [ ] Verificar atualização automática no telão (≤2s)
- [ ] Computador configurado para não dormir

---

*Feito com ⚽ — Copa UNASP 2026*
