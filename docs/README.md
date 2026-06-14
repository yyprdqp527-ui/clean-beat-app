# Démo CleanBeat (GitHub Pages)

Contenu minimal pour déployer une démo statique sur GitHub Pages.

Étapes pour publier sur GitHub Pages (branch `main`, dossier `docs/`)

1. Ajouter, committer et pousser les fichiers :

```bash
git add docs/index.html docs/service-worker.js docs/demo-data.json docs/README.md
git commit -m "Ajout demo static pour GitHub Pages"
git push origin main
```

2. Dans le dépôt GitHub > Settings > Pages :
   - Source : `Deploy from a branch`
   - Branche : `main`
   - Dossier : `/docs`

3. Ouvre l'URL fournie par GitHub Pages (HTTPS). Sur ton téléphone, ouvre l'URL une première fois pour remplir le cache du service worker, puis tu peux déconnecter et la démonstration restera utilisable.

Remarques :
- Le service worker est volontairement minimal ; si tu veux que d'autres ressources (images, CSS) soient mises en cache, ajoute leurs chemins dans `URLS_TO_CACHE`.
- Si tu veux, je peux préparer une version plus fidèle en extrayant plus d'actifs depuis `templates/`.
