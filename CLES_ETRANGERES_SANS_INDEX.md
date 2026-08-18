# Clés étrangères sans index : mesure du 13 août 2026

Un audit de la base de production relève **119 clés étrangères dont la colonne
portante n'a pas d'index**. C'est le genre de constat qui appelle un correctif
réflexe : créer les 119 index manquants. La mesure montre qu'il ne faut pas le faire
aujourd'hui, et dit à quel moment il le faudra.

## Pourquoi cela peut coûter

Sans index sur la colonne enfant, chaque suppression ou modification d'une ligne
parente oblige PostgreSQL à lire la table enfant en entier pour vérifier qu'aucune
ligne n'y fait référence. Sur une table de plusieurs millions de lignes, supprimer un
utilisateur devient une opération de plusieurs secondes qui verrouille au passage.

## Ce que dit la mesure

| Taille de la table enfant | Nombre de clés concernées |
|---|---|
| Plus d'un mégaoctet | 1 |
| Moins d'un mégaoctet | 118 |

La plus grosse table concernée, `information`, occupe 4,8 Mo. Une lecture complète de
4,8 Mo est instantanée : le coût théorique ne se manifeste pas.

## Pourquoi ne rien faire maintenant

Un index n'est pas gratuit. Il se met à jour à chaque insertion, chaque modification
et chaque suppression de la table qu'il couvre, il occupe de l'espace, et il doit
être reconstruit lors des opérations de maintenance. Créer 119 index pour un gain nul
ralentirait l'écriture partout, ce qui est exactement l'inverse du but poursuivi.

C'est le piège de l'audit automatique : il liste ce qui s'écarte d'une règle, sans
mesurer si l'écart coûte quelque chose. Ici, il ne coûte rien.

## Quand agir, et sur quoi

Trois tables grossissent avec l'usage réel de la plateforme, parce qu'elles reçoivent
une ligne par pointage, par participation et par action tracée :

- `presence` (`cree_par`, `terminal_id`)
- `participation` (`absence_motif`, `qualifie_par`)
- les partitions d'`audit` (`acteur_id`)

**Seuil retenu : cent mégaoctets.** Au-delà, la lecture complète se voit sur une
suppression, et l'index devient rentable. À la date de cette mesure, aucune des trois
n'atteint le mégaoctet.

## Comment surveiller

La requête qui a produit cette mesure, à relancer périodiquement :

```sql
SELECT co.conrelid::regclass::text AS enfant,
       a.attname                   AS colonne,
       pg_size_pretty(pg_total_relation_size(co.conrelid)) AS taille
  FROM pg_constraint co
  JOIN pg_namespace n ON n.oid = co.connamespace AND n.nspname = 'public'
  JOIN LATERAL unnest(co.conkey) AS k(attnum) ON true
  JOIN pg_attribute a ON a.attrelid = co.conrelid AND a.attnum = k.attnum
 WHERE co.contype = 'f'
   AND NOT EXISTS (SELECT 1 FROM pg_index i
                    WHERE i.indrelid = co.conrelid AND a.attnum = ANY(i.indkey))
   AND pg_total_relation_size(co.conrelid) > 100 * 1024 * 1024
 ORDER BY pg_total_relation_size(co.conrelid) DESC;
```

Elle ne rend rien tant que rien n'est à faire. Le jour où elle rend une ligne, créer
l'index correspondant **en concurrence**, pour ne pas bloquer les écritures :

```sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS presence_cree_par_idx
    ON presence (cree_par);
```

`CONCURRENTLY` ne peut pas s'exécuter dans une transaction : la commande se lance
seule, jamais dans une migration groupée.
