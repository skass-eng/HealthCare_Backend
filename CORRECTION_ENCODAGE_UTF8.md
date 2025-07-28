# Correction de l'Encodage UTF-8 pour l'Export CSV

## Problème Identifié

Les fichiers CSV exportés affichaient des caractères français mal encodés :
- `Ã©` au lieu de `é`
- `Ã¨` au lieu de `è` 
- `Ã` au lieu de `à`
- `Ā` au lieu de `â`

## Cause du Problème

Le problème était dû à l'absence du **BOM (Byte Order Mark) UTF-8** dans les fichiers CSV exportés. Excel et d'autres applications ne reconnaissent pas automatiquement l'encodage UTF-8 sans ce marqueur.

## Solution Appliquée

### 1. Ajout du BOM UTF-8
```python
# Ajouter le BOM UTF-8 pour Excel
bom = '\ufeff'  # BOM UTF-8
content_with_bom = bom + csv_content
```

### 2. Encodage explicite en UTF-8
```python
# Encoder en UTF-8
content_bytes = content_with_bom.encode('utf-8')
```

### 3. Headers HTTP corrects
```python
return Response(
    content=content_bytes,
    media_type="text/csv; charset=utf-8",
    headers={
        "Content-Disposition": f"attachment; filename=...",
        "Content-Type": "text/csv; charset=utf-8"
    }
)
```

## Fichiers Modifiés

1. **`backend/api_unified.py`** (lignes 567-641)
   - Fonction `export_plaintes()` mise à jour

2. **`backend/api_unified_router.py`** (lignes 268-338)
   - Fonction `export_plaintes()` mise à jour

## Test de Validation

Un script de test a confirmé que :
- ✅ Le BOM UTF-8 est correctement ajouté
- ✅ L'encodage UTF-8 fonctionne
- ✅ Les caractères français s'affichent correctement

## Résultat

Maintenant, les exports CSV :
- ✅ Affichent correctement les caractères français (é, è, à, â, etc.)
- ✅ Sont compatibles avec Excel et autres applications
- ✅ Conservent l'encodage UTF-8 complet

## Utilisation

Pour tester la correction :
1. Redémarrez le serveur backend
2. Allez dans le dashboard
3. Utilisez la fonction d'export CSV
4. Ouvrez le fichier dans Excel - les caractères français devraient s'afficher correctement

## Notes Techniques

- **BOM UTF-8** : `\ufeff` (3 bytes: `EF BB BF`)
- **Encodage** : UTF-8 avec BOM
- **Headers** : `Content-Type: text/csv; charset=utf-8`
- **Compatibilité** : Excel, LibreOffice, Google Sheets, etc. 