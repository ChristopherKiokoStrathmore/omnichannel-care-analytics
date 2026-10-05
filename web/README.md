# Care analytics demo

Next.js App Router frontend. The article is `/`, the interactive demo is `/demo`, and the committed KPI report is `/dashboard`.

On Vercel, set the project Root Directory to `web`.

```bash
npm install
npm run build
npm run dev
```

`data/kpis.json` is a copy of `reports/kpis.json`. The article and the KPI report format those integer counts the same way as `reports/headlines.md`, and the build fails if a displayed rate drifts from that file.

`data/demo-log.json` is the compact synthetic journey log plus the public Bitext taxonomy. `scripts/build_demo_log.py` writes it from the committed journeys. The live demo recomputes rates from that log. The build fails if an unfiltered rate drifts from the committed figures.
