# Frontend — Rastro da Emenda

Next.js (App Router, TypeScript, Tailwind) com a identidade visual QKV works.

```bash
npm install
API_URL=http://localhost:8000 npm run dev   # API FastAPI do backend
npm run build && API_URL=http://localhost:8000 npm start
```

- `API_URL`: URL da API lida em tempo de execução pelo servidor Next (componentes de servidor e o proxy `/api/*`, usado pelo mapa e pelo formulário de assinatura).
- `public/malha/municipios.json`: malha municipal do IBGE (qualidade mínima, coordenadas com 3 casas), gerada por `python3 scripts/preparar_malha.py`.

Páginas: `/` (busca, panorama e mapa), `/busca`, `/emendas/[id]` (ficha e dossiê), `/municipios/[codigo]`, `/parlamentares/[nome]`, `/como-funciona`.
