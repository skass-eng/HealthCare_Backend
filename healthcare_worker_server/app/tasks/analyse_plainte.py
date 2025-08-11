#!/usr/bin/env python3
"""
TÂCHES D'ANALYSE DE PLAINTES - HealthCare AI Architecture ODYSSEE
Tâches Celery principales pour l'analyse LLM des plaintes (inspiré des widgets ODYSSEE)
Version: 1.0.0 - Architecture ODYSSEE
"""

from datetime import datetime
from typing import Dict, Any, List
from uuid import UUID
import logging
import traceback

from sqlalchemy.orm import Session
from ..core.celery_app import healthcare_task, celery_app
from ..services.llm_provider import get_llm_service
from ....shared.models import Plainte, Analyse, TypeAnalyse, StatutAnalyse, AnalyseIA

logger = logging.getLogger(__name__)

# Import de la base de données (configuration partagée)
def get_database_session():
    """Récupérer une session de base de données pour les workers"""
    from ....healthcare_api_server.app.db.database import SessionLocal
    return SessionLocal()

@healthcare_task(name="healthcare_worker_server.tasks.analyse_plainte.process_plainte_analysis")
def process_plainte_analysis(self, task_data: Dict[str, Any]):
    """
    Tâche principale d'analyse de plainte (équivalent d'un widget ODYSSEE)
    Coordonne toutes les analyses demandées pour une plainte
    """
    try:
        plainte_id = UUID(task_data["plainte_id"])
        types_analyse = task_data["types_analyse"]
        user_id = UUID(task_data["user_id"])
        parametres = task_data.get("parametres", {})
        
        logger.info(f"🚀 Début analyse plainte {plainte_id} - Types: {types_analyse}")
        
        # Récupérer la session DB
        db = get_database_session()
        
        try:
            # Récupérer la plainte
            plainte = db.query(Plainte).filter(Plainte.id == plainte_id).first()
            if not plainte:
                raise ValueError(f"Plainte non trouvée: {plainte_id}")
            
            # Mettre à jour le statut de la plainte
            plainte.statut = "en_analyse"
            db.commit()
            
            # Résultats consolidés
            resultats_globaux = {
                "plainte_id": str(plainte_id),
                "analyses_completees": [],
                "analyses_echouees": [],
                "debut_analyse": datetime.now().isoformat(),
                "parametres": parametres
            }
            
            # Exécuter chaque type d'analyse demandé
            for type_analyse in types_analyse:
                try:
                    logger.info(f"🔍 Analyse {type_analyse} pour plainte {plainte_id}")
                    
                    # Créer l'enregistrement d'analyse
                    analyse = Analyse(
                        plainte_id=plainte_id,
                        type_analyse=TypeAnalyse(type_analyse),
                        statut=StatutAnalyse.EN_COURS,
                        parametres_entree=parametres,
                        task_id=self.request.id,
                        date_debut=datetime.now(),
                        analyste_id=user_id
                    )
                    
                    db.add(analyse)
                    db.commit()
                    db.refresh(analyse)
                    
                    # Exécuter l'analyse spécifique
                    resultat_analyse = await execute_specific_analysis(
                        type_analyse, plainte, parametres, db
                    )
                    
                    # Mettre à jour l'analyse avec les résultats
                    analyse.resultats = resultat_analyse
                    analyse.statut = StatutAnalyse.TERMINEE
                    analyse.date_fin = datetime.now()
                    analyse.duree_execution = (analyse.date_fin - analyse.date_debut).total_seconds()
                    
                    db.commit()
                    
                    resultats_globaux["analyses_completees"].append({
                        "type": type_analyse,
                        "analyse_id": str(analyse.id),
                        "resultats": resultat_analyse
                    })
                    
                    logger.info(f"✅ Analyse {type_analyse} terminée pour plainte {plainte_id}")
                    
                except Exception as e:
                    logger.error(f"❌ Erreur analyse {type_analyse}: {e}")
                    
                    # Marquer l'analyse comme échouée
                    if 'analyse' in locals():
                        analyse.statut = StatutAnalyse.ECHEC
                        analyse.erreur_message = str(e)
                        analyse.date_fin = datetime.now()
                        db.commit()
                    
                    resultats_globaux["analyses_echouees"].append({
                        "type": type_analyse,
                        "erreur": str(e)
                    })
            
            # Mettre à jour la plainte avec les résultats consolidés
            await update_plainte_from_analyses(plainte, resultats_globaux, db)
            
            # Mettre à jour le statut final de la plainte
            if resultats_globaux["analyses_echouees"]:
                plainte.statut = "analysee_partielle"
            else:
                plainte.statut = "analysee"
            
            db.commit()
            
            resultats_globaux["fin_analyse"] = datetime.now().isoformat()
            
            logger.info(f"🎉 Analyse complète terminée pour plainte {plainte_id}")
            
            # Notification WebSocket (si implémentée)
            try:
                await notify_analysis_complete(plainte_id, resultats_globaux)
            except Exception as e:
                logger.warning(f"⚠️ Erreur notification WebSocket: {e}")
            
            return resultats_globaux
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Erreur critique analyse plainte: {e}")
        logger.error(traceback.format_exc())
        
        # Marquer la plainte en erreur si possible
        try:
            db = get_database_session()
            plainte = db.query(Plainte).filter(Plainte.id == UUID(task_data["plainte_id"])).first()
            if plainte:
                plainte.statut = "erreur_analyse"
                db.commit()
            db.close()
        except:
            pass
        
        raise

async def execute_specific_analysis(
    type_analyse: str, 
    plainte: Plainte, 
    parametres: Dict[str, Any],
    db: Session
) -> Dict[str, Any]:
    """
    Exécuter une analyse spécifique selon le type (comme les widgets spécialisés ODYSSEE)
    """
    try:
        # Récupérer le service LLM
        llm_service = get_llm_service()
        
        if type_analyse == "sentiment":
            return await analyze_sentiment(plainte, llm_service, parametres)
        
        elif type_analyse == "classification":
            return await analyze_classification(plainte, llm_service, parametres)
        
        elif type_analyse == "priorite":
            return await analyze_priority(plainte, llm_service, parametres)
        
        elif type_analyse == "service_suggestion":
            return await suggest_service(plainte, llm_service, parametres, db)
        
        elif type_analyse == "action_recommendation":
            return await recommend_actions(plainte, llm_service, parametres)
        
        else:
            raise ValueError(f"Type d'analyse non supporté: {type_analyse}")
            
    except Exception as e:
        logger.error(f"❌ Erreur exécution analyse {type_analyse}: {e}")
        raise

async def analyze_sentiment(plainte: Plainte, llm_service, parametres: Dict[str, Any]) -> Dict[str, Any]:
    """Analyse de sentiment (équivalent widget sentiment ODYSSEE)"""
    try:
        prompt = f"""
        Analysez le sentiment de cette plainte hospitalière et donnez un score de -1 (très négatif) à +1 (très positif):
        
        Titre: {plainte.titre}
        Description: {plainte.description}
        
        Retournez un JSON avec:
        - score: nombre entre -1 et 1
        - emotion_principale: string (colère, tristesse, frustration, inquiétude, etc.)
        - intensite: string (faible, modérée, forte, très forte)
        - mots_cles_emotionnels: liste des mots/expressions émotionnels identifiés
        - resume: résumé de l'analyse émotionnelle
        """
        
        response = await llm_service.analyze(prompt, parametres)
        
        # Parser la réponse LLM
        result = llm_service.parse_json_response(response)
        
        # Valider et normaliser le score
        score = float(result.get("score", 0))
        score = max(-1, min(1, score))  # Borner entre -1 et 1
        
        return {
            "score_sentiment": score,
            "emotion_principale": result.get("emotion_principale", "neutre"),
            "intensite": result.get("intensite", "modérée"),
            "mots_cles_emotionnels": result.get("mots_cles_emotionnels", []),
            "resume": result.get("resume", "Analyse de sentiment terminée"),
            "confidence": result.get("confidence", 0.8),
            "methode": "llm_analysis"
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur analyse sentiment: {e}")
        return {
            "score_sentiment": 0,
            "erreur": str(e),
            "methode": "fallback"
        }

async def analyze_classification(plainte: Plainte, llm_service, parametres: Dict[str, Any]) -> Dict[str, Any]:
    """Classification automatique (équivalent widget classification ODYSSEE)"""
    try:
        prompt = f"""
        Classifiez cette plainte hospitalière selon les catégories suivantes:
        - Soins médicaux
        - Accueil et relation patient
        - Organisation des soins
        - Hôtellerie et restauration
        - Facturation et administratif
        - Accessibilité et locaux
        - Autre
        
        Titre: {plainte.titre}
        Description: {plainte.description}
        
        Retournez un JSON avec:
        - categorie_principale: catégorie la plus probable
        - sous_categorie: sous-catégorie spécifique
        - confidence: score de confiance (0-1)
        - mots_cles: mots-clés identifiés pour la classification
        - justification: explication du choix de classification
        """
        
        response = await llm_service.analyze(prompt, parametres)
        result = llm_service.parse_json_response(response)
        
        return {
            "categorie_principale": result.get("categorie_principale", "Autre"),
            "sous_categorie": result.get("sous_categorie", "Non spécifié"),
            "confidence": result.get("confidence", 0.7),
            "mots_cles": result.get("mots_cles", []),
            "justification": result.get("justification", "Classification automatique"),
            "methode": "llm_classification"
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur classification: {e}")
        return {
            "categorie_principale": "Autre",
            "erreur": str(e),
            "methode": "fallback"
        }

async def analyze_priority(plainte: Plainte, llm_service, parametres: Dict[str, Any]) -> Dict[str, Any]:
    """Analyse de priorité (équivalent widget priorité ODYSSEE)"""
    try:
        prompt = f"""
        Analysez la priorité de cette plainte hospitalière selon les critères:
        - CRITIQUE: risque vital, sécurité patient, urgence médicale
        - ELEVEE: impact significatif sur les soins, problème grave
        - NORMALE: problème standard nécessitant traitement
        - FAIBLE: amélioration, suggestion, problème mineur
        
        Titre: {plainte.titre}
        Description: {plainte.description}
        
        Retournez un JSON avec:
        - priorite: CRITIQUE/ELEVEE/NORMALE/FAIBLE
        - score_urgence: score de 0 (pas urgent) à 1 (très urgent)
        - criteres_identifies: liste des critères de priorité identifiés
        - delai_reponse_recommande: nombre de jours recommandé
        - justification: explication de l'évaluation de priorité
        """
        
        response = await llm_service.analyze(prompt, parametres)
        result = llm_service.parse_json_response(response)
        
        # Mapper les priorités
        priorite_mapping = {
            "CRITIQUE": ("critique", 1.0, 1),
            "ELEVEE": ("elevee", 0.7, 3),
            "NORMALE": ("normale", 0.4, 7),
            "FAIBLE": ("faible", 0.2, 14)
        }
        
        priorite_str = result.get("priorite", "NORMALE")
        priorite_info = priorite_mapping.get(priorite_str, priorite_mapping["NORMALE"])
        
        return {
            "priorite": priorite_info[0],
            "score_urgence": result.get("score_urgence", priorite_info[1]),
            "delai_reponse_recommande": result.get("delai_reponse_recommande", priorite_info[2]),
            "criteres_identifies": result.get("criteres_identifies", []),
            "justification": result.get("justification", "Évaluation automatique de priorité"),
            "methode": "llm_priority_analysis"
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur analyse priorité: {e}")
        return {
            "priorite": "normale",
            "score_urgence": 0.4,
            "erreur": str(e),
            "methode": "fallback"
        }

async def suggest_service(plainte: Plainte, llm_service, parametres: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """Suggestion de service approprié"""
    try:
        # Récupérer les services disponibles
        from ....shared.models import Service
        services = db.query(Service).filter(
            Service.organisation_id == plainte.organisation_id,
            Service.is_active == True
        ).all()
        
        services_info = [f"- {s.nom}: {s.description}" for s in services]
        
        prompt = f"""
        Suggérez le service hospitalier le plus approprié pour traiter cette plainte:
        
        Titre: {plainte.titre}
        Description: {plainte.description}
        
        Services disponibles:
        {chr(10).join(services_info)}
        
        Retournez un JSON avec:
        - service_suggere: nom du service recommandé
        - confidence: score de confiance (0-1)
        - justification: pourquoi ce service est approprié
        - services_alternatifs: liste d'autres services possibles
        """
        
        response = await llm_service.analyze(prompt, parametres)
        result = llm_service.parse_json_response(response)
        
        return {
            "service_suggere": result.get("service_suggere", "Direction Qualité"),
            "confidence": result.get("confidence", 0.6),
            "justification": result.get("justification", "Suggestion automatique"),
            "services_alternatifs": result.get("services_alternatifs", []),
            "methode": "llm_service_suggestion"
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur suggestion service: {e}")
        return {
            "service_suggere": "Direction Qualité",
            "erreur": str(e),
            "methode": "fallback"
        }

async def recommend_actions(plainte: Plainte, llm_service, parametres: Dict[str, Any]) -> Dict[str, Any]:
    """Recommandation d'actions correctives"""
    try:
        prompt = f"""
        Recommandez des actions correctives pour cette plainte hospitalière:
        
        Titre: {plainte.titre}
        Description: {plainte.description}
        
        Retournez un JSON avec:
        - actions_immediates: liste d'actions à prendre immédiatement
        - actions_moyen_terme: actions pour prévenir la récurrence
        - personnes_a_contacter: qui doit être informé/impliqué
        - suivi_recommande: modalités de suivi suggérées
        - prevention: mesures préventives pour éviter de nouveaux cas
        """
        
        response = await llm_service.analyze(prompt, parametres)
        result = llm_service.parse_json_response(response)
        
        return {
            "actions_immediates": result.get("actions_immediates", []),
            "actions_moyen_terme": result.get("actions_moyen_terme", []),
            "personnes_a_contacter": result.get("personnes_a_contacter", []),
            "suivi_recommande": result.get("suivi_recommande", "Suivi standard"),
            "prevention": result.get("prevention", []),
            "methode": "llm_action_recommendation"
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur recommandation actions: {e}")
        return {
            "actions_immediates": ["Accuser réception", "Transmettre au service concerné"],
            "erreur": str(e),
            "methode": "fallback"
        }

async def update_plainte_from_analyses(plainte: Plainte, resultats: Dict[str, Any], db: Session):
    """Mettre à jour la plainte avec les résultats d'analyses consolidés"""
    try:
        for analyse in resultats["analyses_completees"]:
            if analyse["type"] == "sentiment":
                plainte.score_sentiment = analyse["resultats"].get("score_sentiment")
            
            elif analyse["type"] == "priorite":
                priorite_str = analyse["resultats"].get("priorite", "normale")
                plainte.priorite = priorite_str
                plainte.score_urgence = analyse["resultats"].get("score_urgence")
            
            elif analyse["type"] == "classification":
                plainte.categorie_auto = analyse["resultats"].get("categorie_principale")
                mots_cles = analyse["resultats"].get("mots_cles", [])
                plainte.tags_auto = mots_cles
        
        # Mettre à jour les métadonnées
        plainte.metadata.update({
            "analyses_terminees": datetime.now().isoformat(),
            "resultats_consolides": resultats
        })
        
        db.commit()
        
    except Exception as e:
        logger.error(f"❌ Erreur mise à jour plainte: {e}")

async def notify_analysis_complete(plainte_id: UUID, resultats: Dict[str, Any]):
    """Notifier la fin d'analyse via WebSocket"""
    try:
        # Cette fonction serait implémentée pour envoyer une notification WebSocket
        # vers le frontend pour informer de la fin d'analyse
        pass
    except Exception as e:
        logger.warning(f"⚠️ Erreur notification: {e}")