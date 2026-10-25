// Fenêtre « Archiver un produit » (US4).
import { annoncer, annoncerErreur, api, champ, h, ouvrirFenetre, remplir } from '../commun.js';

export function ouvrirFenetreArchiver({ produit, surArchive }) {
  const fenetre = ouvrirFenetre({
    titre: `Bye bye « ${produit.nom} » ?`,
    description: 'Il disparaît des listes, des alertes et des inventaires, mais son historique reste. Tu peux le désarchiver à tout moment.',
    etroite: true,
    classeCarte: 'fenetre-soleil',
  });
  const motif = h('input', { class: 'saisie', type: 'text', autocomplete: 'off', placeholder: "ex. Les clientes n'accrochent pas" });
  fenetre.corps.append(champ({ nom: 'motif', libelle: 'Pourquoi ? (facultatif)', controle: motif }));
  const archiver = h('button', {
    type: 'button', class: 'btn btn-sombre', style: { background: 'var(--mauve)', borderColor: 'var(--mauve)' },
    onclick: async () => {
      archiver.disabled = true;
      try {
        const resultat = await api('POST', `/produits/${produit.id}/archiver`, { motif: motif.value });
        fenetre.fermer();
        annoncer(`« ${resultat.nom} » est archivé. Retrouve-le dans l'onglet Archivés.`);
        surArchive?.(resultat);
      } catch (erreur) {
        annoncerErreur(erreur);
        archiver.disabled = false;
      }
    },
  }, 'Archiver');
  remplir(fenetre.pied, h('button', { type: 'button', class: 'btn btn-discret', 'data-fermer': true }, 'Je le garde'), archiver);
  setTimeout(() => motif.focus());
}

export async function desarchiver(produit, surDesarchive) {
  try {
    const resultat = await api('POST', `/produits/${produit.id}/desarchiver`);
    annoncer(`« ${resultat.nom} » est de retour dans tes produits actifs.`);
    surDesarchive?.(resultat);
  } catch (erreur) {
    annoncerErreur(erreur);
  }
}
