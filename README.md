# ⚽ Copa UNASP 2026 — Sistema de Leilão

> Sistema web profissional para gerenciamento de leilão esportivo ao vivo. Backend com banco de dados, painel administrativo protegido por senha, telão fullscreen com animações e apresentação final épica.

**Desenvolvido por Robson & Neo Lucca**

---

## 📋 Índice

- [Visão Geral](#-visão-geral)
- [Funcionalidades](#-funcionalidades)
- [Deploy (Railway)](#-deploy-railway)
- [Como Usar no Evento](#-como-usar-no-evento)
- [Páginas](#-páginas)
- [API](#-api)
- [Como Personalizar](#-como-personalizar)
- [Estrutura de Arquivos](#-estrutura-de-arquivos)
- [Checklist do Evento](#-checklist-do-evento)

---

## 🌐 Visão Geral

```
Operador (Admin)   ──┐
Telão (TV/Projetor) ──┤──► Railway (nuvem) + SQLite
Qualquer dispositivo ──┘         ↑
                           fonte da verdade
```

- **Backend:** Python 3 puro, sem dependências externas
- **Banco:** SQLite — dados persistidos no servidor
- **Frontend:** HTML + CSS + JS puro, duas páginas
- **Deploy:** Railway — link público, sem instalar nada
- **Atualização:** polling automático a cada 6 segundos
- **Regra principal:** toda lógica de negócio fica **somente no backend**

---

## ✨ Funcionalidades

### Painel Admin (`/admin`)
- 🔒 Tela de login com senha antes de qualquer acesso
- Formulário de registro de compras com validação
- Seleção de craque via dropdown ou clique direto no cartão
- Posições: 🧤 Goleiro / 🧱 Fixo / ⚡ Ala / 🎯 Pivô
- Saldo descontado automaticamente — backend impede saldo negativo
- Histórico completo com botão **↩ Desfazer** por compra
- Filtro do histórico por craque
- Gráfico comparativo de saldos em tempo real
- Barra de estatísticas: total gasto, jogadores, média, líder
- Botão **🏁 Finalizar Leilão** — ativa a apresentação no telão
- Botão **📄 Gerar Relatório Final** — texto copiável para WhatsApp
- Botão de reset oculto (`Shift + Alt + R`) para testes

### Telão (`/telao`)
- Grid 3×3 fullscreen — sem scroll, pensado para projetor
- Brasões reais de cada seleção
- Saldo em destaque com barra de progresso colorida (verde → laranja → vermelho)
- Overlay "Aguardando início do leilão" antes da primeira compra
- **Notificação animada** a cada nova compra — overlay central com brasão, nome do jogador e valor
- **Indicador de brilho dourado** no cartão do craque que acabou de comprar
- **Carrossel automático** após 30s sem compra — exibe cada craque em destaque
- Ranking compacto + feed das últimas compras no rodapé
- **Apresentação final** ao clicar "Finalizar Leilão":
  - Cada craque em tela cheia com brasão animado, nome, saldo e elenco completo
  - Jogadores entram um por um com animação
  - Dots de navegação e barra de progresso
- **Tela de encerramento** com troféu 🏆, fogos de artifício, 100 confetes coloridos e brasões de todas as seleções

---

## 🚀 Deploy (Railway)

O sistema está hospedado no Railway e acessível por qualquer pessoa com o link — sem instalar nada.

| Página | URL |
|--------|-----|
| Admin  | `https://copa-unasp-2026-production-f2dd.up.railway.app/admin` |
| Telão  | `https://copa-unasp-2026-production-f2dd.up.railway.app/telao` |

### Como atualizar após mudanças

1. Edite o arquivo desejado no GitHub (clique no lápis ✏️)
2. Clique em **"Commit changes"**
3. O Railway detecta e atualiza o site automaticamente em ~1 minuto

### Plano gratuito do Railway

O Railway oferece **$5 de crédito por mês** gratuitamente. Para um sistema leve como esse, o crédito dura o mês inteiro. Não há risco durante o evento.

---

## 🎯 Como Usar no Evento

### Antes do evento
1. Acesse o admin e faça um **teste completo** — registre algumas compras, teste desfazer, teste o telão
2. Depois, clique em **Resetar Sistema** (`Shift + Alt + R`) para zerar tudo
3. Deixe o telão aberto no projetor/TV em modo tela cheia (`F11`)

### Durante o leilão
1. O operador abre o **admin** no celular ou computador
2. Digita a senha: `neorobson`
3. Seleciona o craque, digita o jogador, escolhe a posição e o valor
4. Clica em **⚽ Registrar Compra**
5. O telão atualiza automaticamente em até 6 segundos

### Ao encerrar
1. Clique em **🏁 Finalizar Leilão** no admin
2. O telão entra na apresentação final automaticamente
3. Após mostrar todos os craques, exibe a tela de encerramento com fogos
4. Clique em **📄 Gerar Relatório Final** para copiar o resumo completo

---

## 📺 Páginas

### Admin — detalhes
- O carrossel do telão para automaticamente quando uma nova compra é registrada
- Se errar uma compra, use o botão **↩ Desfazer** na linha do histórico — o saldo é devolvido
- O botão "Finalizar Leilão" vira "Reabrir Leilão" após clicar, caso precise voltar ao modo normal

### Telão — detalhes
- Projetado para funcionar em qualquer resolução horizontal (16:9)
- Nenhum botão, input ou formulário — só visualização
- O carrossel inicia sozinho após 30 segundos sem compras e para quando uma compra é feita
- A apresentação final mostra cada craque por 7 segundos antes de avançar

---

## 🔌 API

### `GET /api/craques`
Retorna todos os craques com saldos atualizados.

```json
[
  {
    "id": 1,
    "nome": "Neo Lucca",
    "selecao": "Portugal",
    "bandeira": "img/portugal.png",
    "cor": "#006400",
    "cor_sec": "#FF0000",
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
    "craque": "Neo Lucca",
    "selecao": "Portugal",
    "bandeira": "img/portugal.png",
    "jogador": "Cristiano Ronaldo",
    "posicao": "Ala",
    "valor": 15000,
    "timestamp": "2026-03-18 20:00:00"
  }
]
```

### `POST /api/compras`
Registra uma compra com validação de saldo em transação atômica.

```json
{
  "craque_id": 1,
  "jogador": "Cristiano Ronaldo",
  "posicao": "Ala",
  "valor": 15000
}
```

### `DELETE /api/compras/{id}`
Desfaz uma compra e devolve o saldo ao craque.

### `GET /api/status`
Retorna se o leilão foi finalizado `{ "finalizado": true/false }`.

### `POST /api/finalizar` / `POST /api/reabrir`
Finaliza ou reabre o leilão — controla a apresentação no telão.

### `POST /api/reset`
Apaga todas as compras e redefine saldos (usado para testes).

---

## 🎨 Como Personalizar

### Alterar craques e seleções

Edite `CRAQUES_INICIAIS` em `backend/server.py`:

```python
CRAQUES_INICIAIS = [
    # (id, nome,        selecao,      brasao,              cor_primaria, cor_secundaria)
    (1, "Neo Lucca",  "Portugal",  "img/portugal.png",  "#006400",    "#FF0000"),
    (2, "Ricardo",    "Holanda",   "img/holanda.png",   "#FF6600",    "#FFFFFF"),
    # ... edite livremente
]
```

> ⚠️ Após editar os craques, o sistema precisa ser **resetado** para os novos dados aparecerem (porque o banco já existe). Use o botão de reset no admin ou apague o `database.db` se estiver rodando localmente.

### Alterar o saldo inicial

```python
SALDO_INICIAL = 100_000  # backend/server.py, linha 13
```

### Alterar a senha do admin

```js
const SENHA = "neorobson";  // frontend/admin.html, dentro do <script>
```

### Alterar o intervalo de atualização

```js
const POLL = 6000;  // frontend/telao.html e frontend/admin.html
                    // valor em milissegundos (6000 = 6 segundos)
```

### Alterar cores do tema

```css
/* frontend/css/style.css */
:root {
  --vermelho: #E8003D;
  --azul:     #0033A0;
  --amarelo:  #FFD100;
  --roxo:     #6B1FA8;
}
```

### Alterar o tempo da apresentação final

```js
const SECS_APRES = 7;  // frontend/telao.html — segundos por craque
```

### Substituir brasões

Coloque os arquivos PNG em `frontend/img/` com os nomes correspondentes e atualize os caminhos em `CRAQUES_INICIAIS` no `server.py`.

---

## 📁 Estrutura de Arquivos

```
projeto/
│
├── Procfile            ← Railway: como iniciar o servidor
├── railway.json        ← Railway: configuração de build
├── requirements.txt    ← Railway: dependências (vazio — usa só stdlib)
├── runtime.txt         ← Railway: versão do Python
├── README.md           ← Este arquivo
│
├── backend/
│   ├── server.py       ← Servidor HTTP + API REST + SQLite (tudo aqui)
│   └── database.db     ← Criado automaticamente na primeira execução
│
└── frontend/
    ├── admin.html      ← Painel do operador (com login)
    ├── telao.html      ← Tela pública fullscreen (projetor/TV)
    ├── css/
    │   └── style.css   ← Estilos compartilhados
    ├── js/
    │   └── main.js     ← Renderização e utilitários compartilhados
    └── img/
        ├── portugal.png
        ├── holanda.png
        ├── uruguai.png
        ├── argentina.png
        ├── espanha.png
        ├── inglaterra.png
        ├── alemanha.png
        ├── franca.png
        └── croacia.png
```

---

## ✅ Checklist do Evento

### Dias antes
- [ ] Testar login no admin com a senha `neorobson`
- [ ] Registrar compras de teste e verificar se o telão atualiza
- [ ] Testar o botão "Desfazer" no histórico
- [ ] Testar "Finalizar Leilão" e ver a apresentação completa
- [ ] Resetar o sistema após os testes

### No dia do evento
- [ ] Abrir o telão no projetor/TV e pressionar `F11` (tela cheia)
- [ ] Conferir que o telão está mostrando "Aguardando início do leilão"
- [ ] Abrir o admin no dispositivo do operador
- [ ] Fazer uma compra de teste ao vivo para confirmar que o telão atualiza
- [ ] Desfazer a compra de teste antes de começar

### Para encerrar
- [ ] Clicar em "Finalizar Leilão" no admin
- [ ] Aguardar a apresentação final percorrer todos os craques
- [ ] Clicar em "Gerar Relatório Final" e copiar para o WhatsApp

---

*⚽ Copa UNASP 2026 — Desenvolvido por Robson & Neo Lucca*
