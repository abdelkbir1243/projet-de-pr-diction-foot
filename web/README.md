# Goalgebra — frontend

Plateforme web Next.js (App Router, TypeScript, Tailwind CSS v4, Radix UI, Recharts, Lucide).

```bash
npm install
npm run dev      # http://localhost:3000
npm run build    # génère les ~330 pages statiques
```

- Les données viennent de `data/*.json`, produits par le pipeline Python (`python -m footpred.web --sortie web/data` à la racine du dépôt).
- Variables d'environnement facultatives :
  - `FOOTBALL_DATA_API_KEY` : scores en direct via `/api/live` ;
  - `NEXT_PUBLIC_SITE_URL` : URL canonique, sitemap, Open Graph.

Architecture, mise à jour automatique et déploiement sur Vercel : voir [`../docs/plateforme_web.md`](../docs/plateforme_web.md).
