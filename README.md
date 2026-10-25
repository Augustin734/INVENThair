# INVENThair

Appli web locale de gestion de stock pour une onglerie : stock produit par produit, inventaires, alertes de seuil et liste d'achat. Tourne hors ligne sur un PC Linux, sans compte ni connexion internet.

La documentation de référence est dans [`docs/`](docs/) : [cadrage](docs/cadrage.md), [charte](docs/charte.md), [maquettes](docs/maquettes/).

## Installation (PC de Maud)

Prérequis : Linux avec un bureau (GNOME, KDE, Xfce…) et Python 3.11 ou plus récent.

```bash
git clone git@github.com:Augustin734/INVENThair.git
cd INVENThair
./install.sh
```

Une icône **INVENThair** apparaît sur le Bureau et dans le menu des applications. Un double-clic démarre l'appli et l'ouvre dans sa propre fenêtre (Chromium ou Chrome si présents, sinon le navigateur par défaut).

| Commande | Rôle |
| --- | --- |
| `./install.sh` | Installe ou met à jour l'appli et ses raccourcis (à relancer après un `git pull`) |
| `./lancer.sh` | Ce que fait le double-clic |
| `./stop.sh` | Arrête le serveur lancé depuis le Bureau |
| `./desinstaller.sh` | Retire les raccourcis (la base et les sauvegardes restent) |

Les données sont dans `inventhair.db`, les journaux dans `logs/inventhair.log`.

## Développement

```bash
./start.sh        # serveur sur http://localhost:8000, rechargement automatique
.venv/bin/pytest  # tests
```

- Documentation interactive de l'API : http://localhost:8000/docs
- Réglages : copier `.env.example` en `.env`.
- Organisation du code, règles et conventions Git : [`CLAUDE.md`](CLAUDE.md).
