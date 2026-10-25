// Fenêtre « Mes fournisseurs » (US16b) : liste, modification en ligne, ajout, suppression protégée.
import { afficherErreurs, annoncerErreur, api, champ, ErreurApi, h, ouvrirFenetre, remplir } from '../commun.js';
import { ICONES } from './categories.js';

const nbLibelle = (nb) => (nb === 0 ? 'aucun produit' : nb === 1 ? '1 produit' : `${nb} produits`);

/** `surChangement()` est appelé à la fermeture si quelque chose a changé. */
export function ouvrirFournisseurs({ surChangement } = {}) {
  let fournisseurs = [];
  let enEdition = null;
  const refus = new Map(); // id → message de suppression refusée
  let modifie = false;

  const fenetre = ouvrirFenetre({
    titre: 'Mes fournisseurs',
    rubrique: "Carnet d'adresses",
    description: "Ils servent à regrouper ta liste d'achat. Un produit peut ne pas en avoir.",
    surFermeture: () => modifie && surChangement?.(),
  });
  const liste = h('ul', { class: 'liste-reglages' });
  const saisieNom = h('input', { class: 'saisie', type: 'text', autocomplete: 'off' });
  const saisieMail = h('input', { class: 'saisie', type: 'email', placeholder: 'mail (facultatif)', autocomplete: 'off' });
  const erreurAjout = h('p', { class: 'msg msg-erreur', role: 'alert', hidden: true });
  const formulaire = h('form', { class: 'encadre', novalidate: true, onsubmit: ajouter },
    h('span', { class: 'rubrique', style: { color: 'var(--prune)' } }, 'Nouveau fournisseur'),
    h('div', { class: 'grille-form' },
      champ({ nom: 'nom', libelle: 'Nom', obligatoire: true, controle: saisieNom }),
      champ({ nom: 'email', libelle: 'Mail', controle: saisieMail })),
    erreurAjout,
    h('button', { type: 'submit', class: 'btn btn-primaire', style: { alignSelf: 'flex-start' } }, '+ Ajouter'));
  fenetre.corps.append(liste, formulaire);
  remplir(fenetre.pied,
    h('span', { class: 'texte-doux gauche' }, 'Les changements sont enregistrés tout de suite.'),
    h('button', { type: 'button', class: 'btn btn-sombre', style: { background: 'var(--mauve)', borderColor: 'var(--mauve)' }, 'data-fermer': true }, "C'est bon !"));

  async function charger() {
    try {
      fournisseurs = await api('GET', '/fournisseurs');
      rendre();
    } catch (erreur) {
      annoncerErreur(erreur);
    }
  }

  async function supprimer(f) {
    refus.delete(f.id);
    try {
      await api('DELETE', `/fournisseurs/${f.id}`);
      modifie = true;
      await charger();
    } catch (erreur) {
      if (!(erreur instanceof ErreurApi)) throw erreur;
      refus.set(f.id, erreur.message);
      rendre();
    }
  }

  function formulaireEdition(f) {
    const controles = {
      nom: h('input', { class: 'saisie', type: 'text', value: f.nom }),
      email: h('input', { class: 'saisie', type: 'email', value: f.email ?? '' }),
      site_url: h('input', { class: 'saisie', type: 'url', value: f.site_url ?? '' }),
      notes: h('input', { class: 'saisie', type: 'text', value: f.notes ?? '' }),
    };
    const erreurGenerale = h('p', { class: 'msg msg-erreur', role: 'alert', hidden: true });
    const form = h('form', {
      class: 'edition', novalidate: true, 'aria-label': `Modifier ${f.nom}`,
      onsubmit: async (e) => {
        e.preventDefault();
        const corps = Object.fromEntries(Object.entries(controles).map(([k, c]) => [k, c.value]));
        try {
          await api('PATCH', `/fournisseurs/${f.id}`, corps);
          modifie = true;
          enEdition = null;
          await charger();
        } catch (erreur) {
          if (!(erreur instanceof ErreurApi)) throw erreur;
          const restants = afficherErreurs(form, erreur);
          erreurGenerale.textContent = restants.join(' ');
          erreurGenerale.hidden = restants.length === 0;
        }
      },
    },
    h('div', { class: 'grille-form' },
      champ({ nom: 'nom', libelle: 'Nom', obligatoire: true, controle: controles.nom }),
      champ({ nom: 'email', libelle: 'Mail', controle: controles.email }),
      champ({ nom: 'site_url', libelle: 'Site', controle: controles.site_url }),
      champ({ nom: 'notes', libelle: 'Notes', controle: controles.notes })),
    erreurGenerale,
    h('div', { class: 'ligne', style: { justifyContent: 'flex-end' } },
      h('button', { type: 'button', class: 'btn btn-discret btn-petit', onclick: () => { enEdition = null; rendre(); } }, 'Annuler'),
      h('button', { type: 'submit', class: 'btn btn-primaire btn-petit' }, 'Enregistrer')));
    setTimeout(() => controles.nom.focus());
    return form;
  }

  function rendre() {
    if (fournisseurs.length === 0) {
      remplir(liste, h('li', { class: 'vide' }, 'Aucun fournisseur pour le moment. Ajoute le premier ci-dessous.'));
      return;
    }
    remplir(liste, fournisseurs.map((f) => {
      const contact = [f.email, f.site_url, f.notes].filter(Boolean).join(' · ') || 'Pas encore de coordonnées';
      return h('li', {},
        h('div', { class: 'ligne-reglage' },
          h('div', { class: 'infos-reglage' }, h('span', { class: 'nom-fournisseur' }, f.nom), h('span', { class: 'texte-doux' }, contact)),
          h('span', { class: `pastille ${f.nb_produits ? 'p-brouillon' : 'p-annule'}` }, nbLibelle(f.nb_produits)),
          h('div', { class: 'actions' },
            h('button', {
              type: 'button', class: 'btn-rond', 'aria-label': `Modifier ${f.nom}`, 'aria-expanded': String(enEdition === f.id),
              onclick: () => { enEdition = enEdition === f.id ? null : f.id; rendre(); },
            }, ICONES.crayon()),
            h('button', { type: 'button', class: 'btn-rond danger', 'aria-label': `Supprimer ${f.nom}`, onclick: () => supprimer(f) }, ICONES.poubelle()))),
        refus.has(f.id) && h('p', { class: 'msg msg-erreur', role: 'alert' }, refus.get(f.id)),
        enEdition === f.id && formulaireEdition(f));
    }));
  }

  async function ajouter(evenement) {
    evenement.preventDefault();
    erreurAjout.hidden = true;
    try {
      await api('POST', '/fournisseurs', { nom: saisieNom.value, email: saisieMail.value });
      modifie = true;
      saisieNom.value = '';
      saisieMail.value = '';
      afficherErreurs(formulaire, { details: {} });
      await charger();
      saisieNom.focus();
    } catch (erreur) {
      if (!(erreur instanceof ErreurApi)) throw erreur;
      const restants = afficherErreurs(formulaire, erreur);
      erreurAjout.textContent = restants.join(' ');
      erreurAjout.hidden = restants.length === 0;
    }
  }

  charger();
  return fenetre;
}
