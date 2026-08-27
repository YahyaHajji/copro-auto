# Projet de notice de confidentialité — service de licence Copro Auto

> Version de travail à faire valider par un conseil marocain et à compléter avec l'identité commerciale, le numéro CNDP et l'hébergeur avant mise en production.

## Responsable et périmètre

Le responsable du traitement est **Yahya [identité/statut/adresse/email]**. Cette notice couvre l'activation, la sécurité et l'administration commerciale des licences Copro Auto. Les projets de copropriété, plans CAD et cinq documents Word restent sur le poste du client et ne sont pas transmis au serveur de licence.

## Données techniques traitées

- clé de licence : reçue lors de l'activation puis conservée côté serveur uniquement sous forme de HMAC non réversible ;
- empreinte pseudonymisée de l'appareil, nom du poste et version de l'application ;
- identifiants internes de licence et d'activation, plan, sièges, dates d'essai et d'expiration ;
- secret d'activation stocké sous forme de hachage ;
- événements administratifs, horodatages et données de sécurité ;
- adresse IP susceptible d'apparaître dans les journaux du proxy HTTPS.

Le service ne doit pas collecter de CIN, données cadastrales, noms de propriétaires, plans ou contenu des documents générés.

## Finalités et accès

Les données servent à activer les postes, appliquer le nombre de sièges, renouveler les baux signés, prévenir les abus, répondre au support et conserver la preuve contractuelle nécessaire. L'accès est limité au responsable et aux prestataires d'hébergement ou de maintenance contractuellement autorisés.

## Durées proposées à valider

- journaux techniques du proxy et de l'API : 90 jours ;
- activations et audit de licence : durée du contrat plus 24 mois ;
- données de facturation : durée légale applicable séparément ;
- sauvegardes chiffrées : rotation maximale de 35 jours après suppression dans la base active.

À l'issue, les données sont supprimées ou anonymisées, sauf obligation légale ou litige justifiant une conservation limitée.

## Droits, sécurité et transferts

La personne concernée peut demander information, accès, rectification ou opposition dans les limites du droit applicable à **[email de contact]**, avec preuve d'identité proportionnée. Une réclamation peut être adressée à la CNDP.

Les mesures prévues comprennent HTTPS, base PostgreSQL non exposée, secrets séparés, hachage/HMAC des identifiants sensibles, jetons Ed25519, contrôle des accès, sauvegardes chiffrées et journaux sans contenu de dossier.

Avant production, le responsable doit accomplir la formalité CNDP appropriée. Si le VPS ou un sous-traitant héberge les données hors du Maroc, le transfert ne doit commencer qu'après la procédure et les garanties requises.

## Références officielles à remettre au conseil

- [CNDP — conditions de traitement et obligations du responsable](https://www.cndp.ma/conditions/)
- [CNDP — déclaration, autorisation et transfert à l'étranger](https://www.cndp.ma/notifier-un-traitement/)
- [CNDP — mentions types d'information](https://www.cndp.ma/mentions-types/)
- [Loi n° 09-08](https://www.cndp.ma/images/lois/Loi-09-08-Fr.pdf)

Version : **[date]** — récépissé/autorisation CNDP : **[numéro après obtention]**.
