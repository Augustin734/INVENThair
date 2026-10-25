// Fenêtre « Mes catégories » (US16) : renommer, couleur, ordre, ajout, suppression avec fusion.
import { annoncerErreur, api, couleurCss, ErreurApi, h, ouvrirFenetre, remplir, texteSur } from '../commun.js';
import { selecteurCouleur } from '../selecteur_couleur.js';

const PIVOINE = { r: 176, g: 16, b: 80, a: 1 };
const nbLibelle = (nb) => (nb === 0 ? 'vide' : nb === 1 ? '1 produit' : `${nb} produits`);

function icone(d) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  for (const [k, v] of Object.entries({ width: 18, height: 18, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': 3, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'aria-hidden': 'true' })) svg.setAttribute(k, v);
  const chemin = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  chemin.setAttribute('d', d);
  svg.append(chemin);
  return svg;
}
export const ICONES = {
  haut: () => icone('M6 15l6-6 6 6'),
  bas: () => icone('M6 9l6 6 6-6'),
  poubelle: () => icone('M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13'),
  crayon: () => icone('M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z'),
};

/** `surChangement()` est appelé à la fermeture si quelque chose a changé. */
export function ouvrirCategories({ surChangement } = {}) {
  let categories = [];
  let enSuppression = null;
  let couleurPour = null; // id d'une catégorie, 'nouvelle' ou null
  let nouvelleCouleur = { ...PIVOINE };
  let modifie = false;

  const fenetre = ouvrirFenetre({
    titre: 'Mes catégories',
    rubrique: 'Rangement',
    description: "Renomme, choisis une couleur ou change l'ordre. Les filtres de la page Produits suivent.",
    surFermeture: () => modifie && surChangement?.(),
  });
  const liste = h('ul', { class: 'liste-reglages' });
  const zoneCouleur = h('div');
  const saisieNouvelle = h('input', { class: 'saisie', type: 'text', id: 'nouvelle-categorie', placeholder: 'ex. Strass & déco', autocomplete: 'off' });
  const apercuNouvelle = h('span', { class: 'damier rond-couleur', 'aria-hidden': 'true' }, h('span'));
  const erreurNouvelle = h('p', { class: 'erreur-champ', role: 'alert', hidden: true });
  const formulaire = h('form', { class: 'encadre', novalidate: true, onsubmit: ajouter },
    h('label', { for: 'nouvelle-categorie', class: 'rubrique', style: { color: 'var(--prune)' } }, 'Nouvelle catégorie'),
    h('div', { class: 'ligne' },
      saisieNouvelle,
      h('button', { type: 'button', class: 'btn btn-discret btn-encre', onclick: () => choisirCouleur('nouvelle') }, apercuNouvelle, 'Couleur…'),
      h('button', { type: 'submit', class: 'btn btn-primaire' }, '+ Ajouter')),
    erreurNouvelle);
  fenetre.corps.append(liste, zoneCouleur, formulaire);
  remplir(fenetre.pied,
    h('span', { class: 'texte-doux gauche' }, 'Les changements sont enregistrés tout de suite.'),
    h('button', { type: 'button', class: 'btn btn-sombre', style: { background: 'var(--mauve)', borderColor: 'var(--mauve)' }, 'data-fermer': true }, "C'est bon !"));

  async function charger() {
    try {
      categories = await api('GET', '/categories');
      rendre();
    } catch (erreur) {
      annoncerErreur(erreur);
    }
  }

  async function agir(action) {
    try {
      await action();
      modifie = true;
      await charger();
    } catch (erreur) {
      annoncerErreur(erreur);
      await charger();
    }
  }

  function choisirCouleur(cible) {
    couleurPour = couleurPour === cible ? null : cible;
    rendreCouleur();
  }

  function rendreCouleur() {
    Object.assign(apercuNouvelle.firstChild.style, { background: couleurCss(nouvelleCouleur) });
    if (couleurPour === null) return remplir(zoneCouleur);
    const categorie = categories.find((c) => c.id === couleurPour);
    const nom = categorie ? categorie.nom : saisieNouvelle.value.trim() || 'Nouvelle catégorie';
    remplir(zoneCouleur, selecteurCouleur({
      nom,
      couleur: categorie ? categorie.couleur : nouvelleCouleur,
      surAnnuler: () => choisirCouleur(couleurPour),
      surAppliquer: (couleur) => {
        const cible = couleurPour;
        couleurPour = null;
        if (cible === 'nouvelle') {
          nouvelleCouleur = couleur;
          rendreCouleur();
        } else {
          agir(() => api('PATCH', `/categories/${cible}`, { couleur }));
        }
      },
    }));
    zoneCouleur.querySelector('[role="tab"]')?.focus();
  }

  function deplacer(index, sens) {
    const ids = categories.map((c) => c.id);
    [ids[index], ids[index + sens]] = [ids[index + sens], ids[index]];
    agir(() => api('POST', '/categories/reordonner', { ids }));
  }

  function rendre() {
    const focus = document.activeElement?.dataset?.cle;
    remplir(liste, categories.map((c, i) => {
      const saisieNom = h('input', {
        class: 'saisie', type: 'text', value: c.nom, 'data-cle': `nom-${c.id}`,
        onchange: () => {
          const nom = saisieNom.value.trim();
          if (nom && nom !== c.nom) agir(() => api('PATCH', `/categories/${c.id}`, { nom }));
          else saisieNom.value = c.nom;
        },
      });
      const autres = categories.filter((x) => x.id !== c.id);
      const choixDestination = h('select', { class: 'saisie' }, autres.map((x) => h('option', { value: x.id }, x.nom)));
      return h('li', {},
        h('div', { class: 'ligne-reglage' },
          h('button', {
            type: 'button', class: 'damier rond-couleur grand', 'data-cle': `couleur-${c.id}`,
            'aria-label': `Choisir la couleur de ${c.nom}`, 'aria-expanded': String(couleurPour === c.id),
            onclick: () => choisirCouleur(c.id),
          }, h('span', { style: { background: couleurCss(c.couleur) } })),
          h('label', { class: 'nom-reglage' }, h('span', { class: 'sr' }, 'Nom de la catégorie'), saisieNom),
          h('span', { class: 'damier pastille-damier' },
            h('span', { style: { background: couleurCss(c.couleur), color: texteSur(c.couleur) } }, `${c.nom} · ${nbLibelle(c.nb_produits)}`)),
          h('div', { class: 'actions' },
            h('button', { type: 'button', class: 'btn-rond', 'data-cle': `haut-${c.id}`, 'aria-label': `Monter ${c.nom}`, disabled: i === 0, onclick: () => deplacer(i, -1) }, ICONES.haut()),
            h('button', { type: 'button', class: 'btn-rond', 'data-cle': `bas-${c.id}`, 'aria-label': `Descendre ${c.nom}`, disabled: i === categories.length - 1, onclick: () => deplacer(i, 1) }, ICONES.bas()),
            h('button', {
              type: 'button', class: 'btn-rond danger', 'data-cle': `suppr-${c.id}`, 'aria-label': `Supprimer ${c.nom}`,
              onclick: () => {
                if (c.nb_produits === 0) agir(() => api('DELETE', `/categories/${c.id}`));
                else { enSuppression = c.id; rendre(); choixDestination.focus(); }
              },
            }, ICONES.poubelle()))),
        enSuppression === c.id && h('div', { class: 'panneau-alerte' },
          h('p', {}, `« ${c.nom} » contient ${nbLibelle(c.nb_produits)}. Où veux-tu les ranger avant de la supprimer ?`),
          autres.length === 0
            ? h('p', { class: 'erreur-champ' }, "C'est ta seule catégorie : crée-en une autre d'abord.")
            : h('div', { class: 'ligne' },
              h('label', { class: 'ligne', style: { fontWeight: 800 } }, 'Déplacer vers', choixDestination),
              h('button', {
                type: 'button', class: 'btn btn-primaire btn-petit',
                onclick: () => { enSuppression = null; agir(() => api('DELETE', `/categories/${c.id}?fusionner_vers=${choixDestination.value}`)); },
              }, 'Déplacer et supprimer'),
              h('button', { type: 'button', class: 'btn btn-discret btn-petit', onclick: () => { enSuppression = null; rendre(); } }, 'Annuler'))));
    }));
    if (focus) liste.querySelector(`[data-cle="${focus}"]`)?.focus();
  }

  async function ajouter(evenement) {
    evenement.preventDefault();
    erreurNouvelle.hidden = true;
    const nom = saisieNouvelle.value.trim();
    if (!nom) {
      erreurNouvelle.textContent = 'Donne un nom à ta catégorie.';
      erreurNouvelle.hidden = false;
      saisieNouvelle.focus();
      return;
    }
    try {
      await api('POST', '/categories', { nom, couleur: nouvelleCouleur });
      modifie = true;
      saisieNouvelle.value = '';
      nouvelleCouleur = { ...PIVOINE };
      if (couleurPour === 'nouvelle') couleurPour = null;
      rendreCouleur();
      await charger();
      saisieNouvelle.focus();
    } catch (erreur) {
      if (!(erreur instanceof ErreurApi)) throw erreur;
      erreurNouvelle.textContent = erreur.message;
      erreurNouvelle.hidden = false;
    }
  }

  rendreCouleur();
  charger();
  return fenetre;
}
