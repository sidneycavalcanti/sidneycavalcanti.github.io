# Status dos serviços

Painel em tempo real dos serviços de que as empresas dependem: Microsoft 365, Azure, Google, AWS, Cloudflare, Slack, Zoom, GitHub, OpenAI, Claude e meios de pagamento (Mercado Pago, PagBank, Cielo e outros).

Abra em **https://sidneycavalcanti.github.io/dev.html**

## Como funciona

- `dev.html` lê direto, a cada minuto, as páginas oficiais de status que liberam o navegador (CORS). Clique num serviço para ver impacto, afetados, previsão de solução, próxima atualização e o histórico oficial. Botão PT/EN no topo; `dev.html#Microsoft 365` abre direto o painel do serviço.
- AWS, Azure e Microsoft 365 não liberam. O Action `.github/workflows/status.yml` roda `scripts/coletar.py` a cada 5 minutos e grava `status.json` no branch `dados` (sempre um commit só). A página lê esse arquivo.
- Para incluir um serviço, acrescente uma linha em `FONTES` no `dev.html`. Se ele usa Atlassian Statuspage (tem `/api/v2/summary.json`), basta `sp("Nome", "grupo", "https://status.exemplo.com")`.

## Testes

```bash
node scripts/testar.js           # leitores do dev.html contra as APIs reais
python3 scripts/test_coletar.py  # coletor, sem rede
```

O GitHub pausa Actions agendados depois de 60 dias sem commits no repositório. Se o status da AWS, Azure e M365 parar de atualizar, reative em *Actions → status → Enable workflow*.
