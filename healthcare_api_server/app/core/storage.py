"""
Utilitaires de stockage de fichiers (securite disque).

Ce module regroupe des helpers utilises lors de l'upload, du nommage,
de la verification et du nettoyage de fichiers sur le disque :
- protection contre le path-traversal (noms de fichiers et chemins cibles) ;
- nettoyage best-effort pour les rollbacks ;
- calcul d'empreinte SHA-256 du contenu.

Imports standards uniquement (os, hashlib, pathlib).
"""

import os
import hashlib
from pathlib import Path
from typing import Iterable, Optional, Union

from fastapi import HTTPException


def safe_storage_name(prefix: str, original_filename: str) -> str:
    """
    Construit un nom de fichier de stockage sur, prefixe et debarrasse de
    tout composant de chemin (anti path-traversal).

    On ne conserve que le nom de base du fichier fourni par l'utilisateur :
    tout separateur de repertoire (``/`` ou ``\\``) est elimine via
    ``os.path.basename``, en neutralisant au prealable les separateurs
    Windows pour garantir un comportement identique sur toutes les plateformes.

    Args:
        prefix: Prefixe a appliquer (ex. identifiant de plainte).
        original_filename: Nom de fichier d'origine fourni par le client.

    Returns:
        Une chaine de la forme ``f"{prefix}_{name}"`` ou ``name`` est le
        nom de base nettoye du fichier d'origine.
    """
    # On normalise d'abord les separateurs Windows en separateurs POSIX
    # afin que os.path.basename strip correctement le chemin meme sous Linux.
    normalise = (original_filename or "").replace("\\", "/")
    name = os.path.basename(normalise)
    return f"{prefix}_{name}"


def assert_within(
    base_dir: Union[str, os.PathLike],
    target_path: Union[str, os.PathLike],
) -> None:
    """
    Verifie que ``target_path`` se situe bien a l'interieur de ``base_dir``
    une fois les chemins resolus (anti path-traversal).

    Leve une ``HTTPException`` 400 ("Chemin invalide") si le chemin cible
    s'echappe du repertoire de base (ex. via ``..``).

    La verification utilise ``Path.is_relative_to`` lorsqu'elle est disponible
    (Python 3.9+) avec un repli via ``os.path.commonpath`` pour assurer la
    compatibilite.

    Args:
        base_dir: Repertoire de base autorise.
        target_path: Chemin cible a valider.

    Raises:
        HTTPException: 400 si le chemin cible n'est pas sous le repertoire de base.
    """
    base_resolved = Path(base_dir).resolve()
    target_resolved = Path(target_path).resolve()

    # Chemin nominal : is_relative_to (disponible des Python 3.9).
    try:
        if target_resolved.is_relative_to(base_resolved):
            return
        # Disponible mais hors du repertoire de base -> on rejette.
        raise HTTPException(status_code=400, detail="Chemin invalide")
    except AttributeError:
        # Repli compatibilite (< 3.9) : on compare via commonpath.
        try:
            commun = os.path.commonpath([str(base_resolved), str(target_resolved)])
        except ValueError:
            # Lecteurs differents sous Windows, ou chemins incomparables.
            raise HTTPException(status_code=400, detail="Chemin invalide")
        if commun != str(base_resolved):
            raise HTTPException(status_code=400, detail="Chemin invalide")


def cleanup_files(
    paths: Optional[Iterable[Optional[Union[str, os.PathLike]]]],
) -> None:
    """
    Supprime au mieux ("best-effort") les fichiers indiques.

    Concue pour les rollbacks disque : chaque erreur (fichier inexistant,
    permission, valeur ``None``) est ignoree silencieusement afin de ne
    jamais interrompre le nettoyage.

    Args:
        paths: Iterable de chemins a supprimer (les ``None`` sont tolerees).
               Si ``paths`` vaut ``None``, la fonction ne fait rien.
    """
    if not paths:
        return
    for chemin in paths:
        if not chemin:
            # On ignore les entrees None ou vides.
            continue
        try:
            if os.path.exists(chemin):
                os.remove(chemin)
        except OSError:
            # Best-effort : toute erreur de suppression est ignoree.
            pass


def file_sha256(path: Union[str, os.PathLike]) -> str:
    """
    Calcule l'empreinte SHA-256 (en hexadecimal) du contenu d'un fichier.

    La lecture se fait par blocs afin de gerer les fichiers volumineux sans
    tout charger en memoire.

    Args:
        path: Chemin du fichier a hacher.

    Returns:
        L'empreinte SHA-256 sous forme de chaine hexadecimale.
    """
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for bloc in iter(lambda: f.read(8192), b""):
            sha.update(bloc)
    return sha.hexdigest()
