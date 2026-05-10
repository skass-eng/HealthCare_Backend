"""
Tâches Celery modulaires pour le traitement des plaintes
Utilise l'architecture modulaire avec l'orchestrateur
"""
import logging
import os
import sys
import redis
from typing import Dict, Any, Optional
from datetime import datetime

# Ajouter le répertoire parent au path pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import json

# Import des services modulaires
from healthcare_worker_server.app.services.document_parser import DocumentParserService
from healthcare_worker_server.app.services.complaint_analysis import ComplaintAnalysisService
from healthcare_worker_server.app.services.pdf_generator import PDFReportService
from healthcare_worker_server.app.services.llm_provider import get_llm_service
from healthcare_worker_server.app.tasks.workflow_orchestrator import ComplaintWorkflowOrchestrator

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import de l'app Celery depuis celery_worker_v2 pour utiliser la même instance
from celery_worker_v2 import app

# Configuration de la base de données
DATABASE_URL = "postgresql://postgres:242261@localhost:5430/hospital_complaints"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Connexion Redis pour les flags d'annulation
redis_client = redis.Redis(host='localhost', port=6379, db=3, decode_responses=True)

def is_task_cancelled(task_id: str) -> bool:
    """Vérifie si une tâche a été annulée via Redis"""
    try:
        return redis_client.get(f"cancelled_task:{task_id}") == "1"
    except Exception:
        return False

def mark_task_cancelled(task_id: str, ttl: int = 3600):
    """Marque une tâche comme annulée dans Redis (expire après 1h par défaut)"""
    try:
        redis_client.setex(f"cancelled_task:{task_id}", ttl, "1")
        logger.info(f"🛑 Tâche {task_id} marquée comme annulée")
        return True
    except Exception as e:
        logger.error(f"Erreur marquage annulation: {e}")
        return False

def clear_cancelled_task(task_id: str):
    """Supprime le flag d'annulation d'une tâche"""
    try:
        redis_client.delete(f"cancelled_task:{task_id}")
    except Exception:
        pass

# Initialisation des services (sera fait lors de l'exécution des tâches)
_services_initialized = False
_document_parser = None
_analysis_service = None
_pdf_generator = None
_orchestrator = None

def initialize_services():
    """Initialise tous les services nécessaires"""
    global _services_initialized, _document_parser, _analysis_service, _pdf_generator, _orchestrator
    
    if _services_initialized:
        return
    
    logger.info("🔧 Initialisation des services modulaires...")
    
    try:
        # Service de parsing de documents
        _document_parser = DocumentParserService()
        
        # Service LLM (utiliser le singleton)
        llm_provider = get_llm_service()
        
        # Service d'analyse IA
        _analysis_service = ComplaintAnalysisService(llm_provider)
        
        # Service de génération PDF
        _pdf_generator = PDFReportService()
        
        # Orchestrateur principal
        _orchestrator = ComplaintWorkflowOrchestrator(
            document_parser=_document_parser,
            analysis_service=_analysis_service,
            pdf_generator=_pdf_generator,
            llm_provider=llm_provider
        )
        
        _services_initialized = True
        logger.info("✅ Services initialisés avec succès")
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'initialisation des services: {str(e)}")
        raise

@app.task(bind=True, name="process_complaint_complete")
def process_complaint_complete(self, plainte_id: int, document_path: Optional[str] = None):
    """
    Tâche principale : Traitement complet d'une plainte selon le workflow défini
    
    Workflow:
    1. Parsing du document (conditionnel)
    2. Analyse complète (sentiment, résumé, contacts) 
    3. Génération de la réponse juridique
    4. Compilation et génération du PDF final
    """
    logger.info(f"🚀 Démarrage du traitement complet - Plainte ID: {plainte_id}")
    
    try:
        # Initialiser les services
        initialize_services()
        
        # Récupérer les données de la plainte
        plainte_data = get_plainte_data(plainte_id)
        if not plainte_data:
            error_msg = f"Plainte {plainte_id} non trouvée en base de données"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        
        # Exécuter le workflow complet via l'orchestrateur
        workflow_result = _orchestrator.process_complaint_complete(plainte_data, document_path)
        
        # Sauvegarder les résultats en base
        save_analysis_results(plainte_id, workflow_result)
        
        # Mettre à jour le statut de la plainte
        update_plainte_status(plainte_id, "ANALYSEE" if workflow_result["success"] else "ERREUR_ANALYSE")
        
        logger.info(f"✅ Traitement complet terminé - Plainte ID: {plainte_id}")
        return workflow_result
        
    except Exception as e:
        error_msg = f"Erreur lors du traitement complet: {str(e)}"
        logger.error(error_msg)
        update_plainte_status(plainte_id, "ERREUR_ANALYSE")
        return {"success": False, "error": error_msg, "plainte_id": plainte_id}

@app.task(bind=True, name="parse_document_only")
def parse_document_only(self, plainte_id: int, document_path: str):
    """
    Tâche spécialisée : Parsing de document uniquement
    """
    logger.info(f"📄 Parsing de document - Plainte ID: {plainte_id}")
    
    try:
        initialize_services()
        
        if not os.path.exists(document_path):
            error_msg = f"Document non trouvé: {document_path}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        
        # Parser le document
        parsing_result = _document_parser.extract_text_from_document(document_path)
        
        if parsing_result.get("success", False):
            # Sauvegarder le texte extrait en base
            save_extracted_text(plainte_id, parsing_result)
            logger.info(f"✅ Parsing terminé - Plainte ID: {plainte_id}")
        else:
            logger.error(f"❌ Échec du parsing - Plainte ID: {plainte_id}")
        
        return parsing_result
        
    except Exception as e:
        error_msg = f"Erreur lors du parsing: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}

@app.task(bind=True, name="analyze_complaint_sentiment")
def analyze_complaint_sentiment(self, plainte_id: int, complaint_text: str):
    """
    Tâche spécialisée : Analyse de sentiment uniquement
    """
    logger.info(f"😊 Analyse de sentiment - Plainte ID: {plainte_id}")
    
    try:
        initialize_services()
        
        # Analyser le sentiment
        sentiment_result = _analysis_service.analyze_sentiment(complaint_text)
        
        # Sauvegarder le résultat
        save_sentiment_analysis(plainte_id, sentiment_result)
        
        logger.info(f"✅ Analyse de sentiment terminée - Plainte ID: {plainte_id}")
        return {
            "success": sentiment_result.success,
            "content": sentiment_result.content,
            "confidence": sentiment_result.confidence,
            "error": sentiment_result.error
        }
        
    except Exception as e:
        error_msg = f"Erreur lors de l'analyse de sentiment: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}

@app.task(bind=True, name="generate_complaint_summary")
def generate_complaint_summary(self, plainte_id: int, complaint_text: str):
    """
    Tâche spécialisée : Génération de résumé uniquement
    """
    logger.info(f"📝 Génération de résumé - Plainte ID: {plainte_id}")
    
    try:
        initialize_services()
        
        # Générer le résumé
        summary_result = _analysis_service.generate_summary(complaint_text)
        
        # Sauvegarder le résultat
        save_summary_analysis(plainte_id, summary_result)
        
        logger.info(f"✅ Génération de résumé terminée - Plainte ID: {plainte_id}")
        return {
            "success": summary_result.success,
            "content": summary_result.content,
            "confidence": summary_result.confidence,
            "error": summary_result.error
        }
        
    except Exception as e:
        error_msg = f"Erreur lors de la génération de résumé: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}

@app.task(bind=True, name="extract_complaint_contacts")
def extract_complaint_contacts(self, plainte_id: int, complaint_text: str):
    """
    Tâche spécialisée : Extraction de contacts uniquement
    """
    logger.info(f"👥 Extraction de contacts - Plainte ID: {plainte_id}")
    
    try:
        initialize_services()
        
        # Extraire les contacts
        contacts_result = _analysis_service.extract_contacts(complaint_text)
        
        # Sauvegarder le résultat
        save_contacts_analysis(plainte_id, contacts_result)
        
        logger.info(f"✅ Extraction de contacts terminée - Plainte ID: {plainte_id}")
        return {
            "success": contacts_result.success,
            "content": contacts_result.content,
            "confidence": contacts_result.confidence,
            "error": contacts_result.error
        }
        
    except Exception as e:
        error_msg = f"Erreur lors de l'extraction de contacts: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}

@app.task(bind=True, name="generate_legal_response")
def generate_legal_response(self, plainte_id: int, complaint_text: str, analysis_summary: str):
    """
    Tâche spécialisée : Génération de réponse juridique uniquement
    """
    logger.info(f"⚖️ Génération de réponse juridique - Plainte ID: {plainte_id}")
    
    try:
        initialize_services()
        
        # Générer la réponse juridique
        legal_result = _analysis_service.generate_legal_response(complaint_text, analysis_summary)
        
        # Sauvegarder le résultat
        save_legal_response(plainte_id, legal_result)
        
        logger.info(f"✅ Réponse juridique générée - Plainte ID: {plainte_id}")
        return {
            "success": legal_result.success,
            "content": legal_result.content,
            "confidence": legal_result.confidence,
            "error": legal_result.error
        }
        
    except Exception as e:
        error_msg = f"Erreur lors de la génération de réponse juridique: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}

@app.task(bind=True, name="generate_pdf_report")
def generate_pdf_report(self, plainte_id: int):
    """
    Tâche spécialisée : Génération de rapport PDF uniquement
    """
    logger.info(f"📋 Génération de rapport PDF - Plainte ID: {plainte_id}")
    
    try:
        initialize_services()
        
        # Récupérer toutes les données nécessaires
        plainte_data = get_plainte_data(plainte_id)
        analysis_results = get_all_analysis_results(plainte_id)
        
        if not plainte_data:
            error_msg = f"Données de plainte {plainte_id} non trouvées"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        
        # Générer le PDF
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"rapport_plainte_{plainte_id}_{timestamp}.pdf"
        output_dir = os.path.join(os.getcwd(), 'data', 'pdf_reports')
        output_path = os.path.join(output_dir, output_filename)
        
        pdf_result = _pdf_generator.generate_complaint_report(
            plainte_data, analysis_results, output_path
        )
        
        if pdf_result.get("success", False):
            # Sauvegarder le chemin du PDF en base
            save_pdf_path(plainte_id, output_path)
        
        logger.info(f"✅ Rapport PDF généré - Plainte ID: {plainte_id}")
        return pdf_result
        
    except Exception as e:
        error_msg = f"Erreur lors de la génération PDF: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}

# === Fonctions utilitaires pour la base de données ===

def get_plainte_data(plainte_id: int) -> Optional[Dict[str, Any]]:
    """Récupère les données d'une plainte"""
    try:
        with SessionLocal() as session:
            result = session.execute(
                text("SELECT * FROM plaintes WHERE id = :plainte_id"),
                {"plainte_id": plainte_id}
            )
            row = result.fetchone()
            if row:
                return dict(row._mapping)
            return None
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la plainte: {str(e)}")
        return None

def save_analysis_results(plainte_id: int, workflow_result: Dict[str, Any]):
    """Sauvegarde tous les résultats d'analyse dans la table analyses_ia - crée l'entrée si elle n'existe pas"""
    try:
        with SessionLocal() as session:
            # Extraire les données du workflow
            analysis_results = workflow_result.get("analysis_results", {})
            legal_response = workflow_result.get("legal_response", {})
            
            # Extraire le sentiment
            sentiment_data = analysis_results.get("sentiment", {})
            sentiment_content = sentiment_data.get("content", "{}")
            try:
                sentiment_json = json.loads(sentiment_content) if isinstance(sentiment_content, str) else sentiment_content
                sentiment = sentiment_json.get("sentiment_principal", "neutre")
                score_sentiment = sentiment_json.get("score_sentiment", 0.5)
            except:
                sentiment = "neutre"
                score_sentiment = 0.5
            
            # Extraire le résumé
            summary_data = analysis_results.get("summary", {})
            summary_content = summary_data.get("content", "{}")
            try:
                summary_json = json.loads(summary_content) if isinstance(summary_content, str) else summary_content
                resume_ia = summary_json.get("resume_executif", "")
                services_concernes = summary_json.get("services_concernes", [])
                service_suggere = services_concernes[0] if services_concernes else "Service Qualité"
            except:
                resume_ia = ""
                service_suggere = "Service Qualité"
            
            # Extraire la réponse juridique
            reponse_suggeree = ""
            if legal_response.get("success"):
                legal_content = legal_response.get("content", "")
                try:
                    legal_json = json.loads(legal_content) if isinstance(legal_content, str) else legal_content
                    reponse_suggeree = legal_json.get("reponse_officielle", "") or legal_json.get("reponse", "") or legal_content
                except:
                    reponse_suggeree = legal_content
            
            # Extraire les mots-clés
            mots_cles = []
            try:
                if sentiment_json.get("mots_cles_emotionnels"):
                    mots_cles = sentiment_json.get("mots_cles_emotionnels", [])
            except:
                pass
            
            # INSÉRER OU METTRE À JOUR l'entrée analyses_ia (crée si n'existe pas)
            session.execute(
                text("""
                    INSERT INTO analyses_ia (plainte_id, sentiment, score_sentiment, confiance_sentiment, 
                        service_suggere, resume_ia, reponse_suggeree, mots_cles_detectes, statut_analyse,
                        date_analyse, date_mise_a_jour)
                    VALUES (:plainte_id, :sentiment, :score_sentiment, :confiance_sentiment,
                        :service_suggere, :resume_ia, :reponse_suggeree, :mots_cles_detectes, :statut_analyse,
                        NOW(), NOW())
                    ON CONFLICT (plainte_id) DO UPDATE SET
                        sentiment = EXCLUDED.sentiment,
                        score_sentiment = EXCLUDED.score_sentiment,
                        confiance_sentiment = EXCLUDED.confiance_sentiment,
                        service_suggere = EXCLUDED.service_suggere,
                        resume_ia = EXCLUDED.resume_ia,
                        reponse_suggeree = EXCLUDED.reponse_suggeree,
                        mots_cles_detectes = EXCLUDED.mots_cles_detectes,
                        statut_analyse = EXCLUDED.statut_analyse,
                        date_analyse = NOW(),
                        date_mise_a_jour = NOW()
                """),
                {
                    "plainte_id": plainte_id,
                    "sentiment": sentiment,
                    "score_sentiment": score_sentiment,
                    "confiance_sentiment": sentiment_data.get("confidence", 0.8),
                    "service_suggere": service_suggere,
                    "resume_ia": resume_ia,
                    "reponse_suggeree": reponse_suggeree,
                    "mots_cles_detectes": mots_cles,
                    "statut_analyse": "complete" if workflow_result.get("success") else "erreur"
                }
            )
            session.commit()
            logger.info(f"✅ Résultats d'analyse sauvegardés pour plainte {plainte_id}")
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde des résultats: {str(e)}")

def update_plainte_status(plainte_id: int, new_status: str):
    """Met à jour le statut d'une plainte - utilise les statuts valides de l'enum"""
    # Mapper les statuts internes vers les statuts valides de l'enum
    status_mapping = {
        "ANALYSEE": "EN_COURS",       # Après analyse -> En cours de traitement
        "ERREUR_ANALYSE": "EN_COURS",  # Même en cas d'erreur, on garde en cours
        "COMPLETE": "EN_COURS",
        "TRAITE": "TRAITE",
        "CLOTURE": "CLOTURE",
        "RECU": "RECU",
        "EN_COURS": "EN_COURS"
    }
    
    # Utiliser le mapping ou garder EN_COURS par défaut
    valid_status = status_mapping.get(new_status, "EN_COURS")
    
    try:
        with SessionLocal() as session:
            session.execute(
                text("UPDATE plaintes SET statut = :status, date_modification = NOW() WHERE id = :plainte_id"),
                {"status": valid_status, "plainte_id": plainte_id}
            )
            session.commit()
            logger.info(f"✅ Statut de plainte {plainte_id} mis à jour: {valid_status}")
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour du statut: {str(e)}")

def save_extracted_text(plainte_id: int, parsing_result: Dict[str, Any]):
    """Sauvegarde le texte extrait d'un document - crée l'entrée si elle n'existe pas"""
    try:
        with SessionLocal() as session:
            session.execute(
                text("""
                    INSERT INTO analyses_ia (plainte_id, statut_analyse, date_mise_a_jour)
                    VALUES (:plainte_id, 'texte_extrait', NOW())
                    ON CONFLICT (plainte_id) DO UPDATE SET
                        statut_analyse = 'texte_extrait',
                        date_mise_a_jour = NOW()
                """),
                {"plainte_id": plainte_id}
            )
            session.commit()
            logger.info(f"✅ Texte extrait enregistré pour plainte {plainte_id}")
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde du texte extrait: {str(e)}")

def save_sentiment_analysis(plainte_id: int, sentiment_result):
    """Sauvegarde l'analyse de sentiment dans la table analyses_ia - crée l'entrée si elle n'existe pas"""
    try:
        with SessionLocal() as session:
            # Extraire les données du sentiment
            try:
                sentiment_json = json.loads(sentiment_result.content) if isinstance(sentiment_result.content, str) else sentiment_result.content
                sentiment = sentiment_json.get("sentiment_principal", "neutre")
                score_sentiment = sentiment_json.get("score_sentiment", 0.5)
                mots_cles = sentiment_json.get("mots_cles_emotionnels", [])
            except:
                sentiment = "neutre"
                score_sentiment = 0.5
                mots_cles = []
            
            session.execute(
                text("""
                    INSERT INTO analyses_ia (plainte_id, sentiment, score_sentiment, confiance_sentiment, 
                        mots_cles_detectes, statut_analyse, date_mise_a_jour)
                    VALUES (:plainte_id, :sentiment, :score_sentiment, :confiance_sentiment, 
                        :mots_cles_detectes, 'en_cours', NOW())
                    ON CONFLICT (plainte_id) DO UPDATE SET
                        sentiment = EXCLUDED.sentiment,
                        score_sentiment = EXCLUDED.score_sentiment,
                        confiance_sentiment = EXCLUDED.confiance_sentiment,
                        mots_cles_detectes = EXCLUDED.mots_cles_detectes,
                        date_mise_a_jour = NOW()
                """),
                {
                    "plainte_id": plainte_id,
                    "sentiment": sentiment,
                    "score_sentiment": score_sentiment,
                    "confiance_sentiment": sentiment_result.confidence,
                    "mots_cles_detectes": mots_cles
                }
            )
            session.commit()
            logger.info(f"✅ Analyse de sentiment sauvegardée pour plainte {plainte_id}")
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde de l'analyse de sentiment: {str(e)}")

def save_summary_analysis(plainte_id: int, summary_result):
    """Sauvegarde le résumé dans la table analyses_ia - crée l'entrée si elle n'existe pas"""
    try:
        with SessionLocal() as session:
            # Extraire les données du résumé
            try:
                summary_json = json.loads(summary_result.content) if isinstance(summary_result.content, str) else summary_result.content
                resume_ia = summary_json.get("resume_executif", "")
                services_concernes = summary_json.get("services_concernes", [])
                service_suggere = services_concernes[0] if services_concernes else "Service Qualité"
            except:
                resume_ia = summary_result.content if isinstance(summary_result.content, str) else ""
                service_suggere = "Service Qualité"
            
            session.execute(
                text("""
                    INSERT INTO analyses_ia (plainte_id, resume_ia, service_suggere, confiance_service, 
                        statut_analyse, date_mise_a_jour)
                    VALUES (:plainte_id, :resume_ia, :service_suggere, :confiance_service, 'en_cours', NOW())
                    ON CONFLICT (plainte_id) DO UPDATE SET
                        resume_ia = EXCLUDED.resume_ia,
                        service_suggere = EXCLUDED.service_suggere,
                        confiance_service = EXCLUDED.confiance_service,
                        date_mise_a_jour = NOW()
                """),
                {
                    "plainte_id": plainte_id,
                    "resume_ia": resume_ia,
                    "service_suggere": service_suggere,
                    "confiance_service": summary_result.confidence
                }
            )
            session.commit()
            logger.info(f"✅ Résumé sauvegardé pour plainte {plainte_id}")
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde du résumé: {str(e)}")

def save_contacts_analysis(plainte_id: int, contacts_result):
    """Sauvegarde l'extraction de contacts - crée l'entrée si elle n'existe pas"""
    try:
        with SessionLocal() as session:
            session.execute(
                text("""
                    INSERT INTO analyses_ia (plainte_id, statut_analyse, date_mise_a_jour)
                    VALUES (:plainte_id, 'contacts_extraits', NOW())
                    ON CONFLICT (plainte_id) DO UPDATE SET
                        statut_analyse = 'contacts_extraits',
                        date_mise_a_jour = NOW()
                """),
                {"plainte_id": plainte_id}
            )
            session.commit()
            logger.info(f"✅ Contacts analysés pour plainte {plainte_id}")
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde de l'extraction de contacts: {str(e)}")

def save_legal_response(plainte_id: int, legal_result):
    """Sauvegarde la réponse juridique - crée l'entrée si elle n'existe pas"""
    try:
        with SessionLocal() as session:
            # Extraire le texte de la réponse juridique
            response_text = legal_result.content
            
            # Si c'est du JSON, essayer d'extraire la réponse officielle
            try:
                content_data = json.loads(legal_result.content)
                if isinstance(content_data, dict):
                    # Priorité: reponse_officielle > reponse > contenu
                    response_text = content_data.get('reponse_officielle') or content_data.get('reponse') or legal_result.content
            except (json.JSONDecodeError, TypeError):
                pass
            
            # INSERT ON CONFLICT pour créer ou mettre à jour
            session.execute(
                text("""
                    INSERT INTO analyses_ia (plainte_id, reponse_suggeree, statut_analyse, date_mise_a_jour)
                    VALUES (:plainte_id, :reponse_suggeree, 'complete', NOW())
                    ON CONFLICT (plainte_id) DO UPDATE SET
                        reponse_suggeree = EXCLUDED.reponse_suggeree,
                        statut_analyse = 'complete',
                        date_mise_a_jour = NOW()
                """),
                {
                    "plainte_id": plainte_id,
                    "reponse_suggeree": response_text
                }
            )
            session.commit()
            logger.info(f"✅ Réponse juridique sauvegardée pour plainte {plainte_id}")
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde de la réponse juridique: {str(e)}")

def save_pdf_path(plainte_id: int, pdf_path: str):
    """Sauvegarde le PDF généré comme document rattaché à la plainte"""
    try:
        import os
        from pathlib import Path
        
        with SessionLocal() as session:
            # Vérifier si un rapport PDF existe déjà pour cette plainte
            existing = session.execute(
                text("""
                    SELECT id FROM documents_plaintes 
                    WHERE plainte_id = :plainte_id 
                    AND nom_fichier LIKE 'rapport_plainte_%'
                """),
                {"plainte_id": plainte_id}
            ).fetchone()
            
            if existing:
                # Mettre à jour le document existant
                session.execute(
                    text("""
                        UPDATE documents_plaintes 
                        SET chemin_fichier = :pdf_path, 
                            taille_fichier = :file_size,
                            date_modification = NOW()
                        WHERE id = :doc_id
                    """),
                    {
                        "pdf_path": pdf_path, 
                        "file_size": os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0,
                        "doc_id": existing[0]
                    }
                )
                logger.info(f"📄 Rapport PDF mis à jour pour plainte {plainte_id}")
            else:
                # Créer un nouveau document
                filename = Path(pdf_path).name
                session.execute(
                    text("""
                        INSERT INTO documents_plaintes 
                        (plainte_id, nom_fichier, nom_stockage, chemin_fichier, type_fichier, 
                         taille_fichier, description, est_piece_jointe_originale, date_upload)
                        VALUES (:plainte_id, :nom_fichier, :nom_stockage, :chemin_fichier, 'PDF',
                                :taille_fichier, 'Rapport PDF généré automatiquement', false, NOW())
                    """),
                    {
                        "plainte_id": plainte_id,
                        "nom_fichier": filename,
                        "nom_stockage": filename,
                        "chemin_fichier": pdf_path,
                        "taille_fichier": os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0
                    }
                )
                logger.info(f"📄 Rapport PDF créé pour plainte {plainte_id}: {filename}")
            
            session.commit()
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde du chemin PDF: {str(e)}")

def get_all_analysis_results(plainte_id: int) -> Dict[str, Any]:
    """Récupère tous les résultats d'analyse pour une plainte"""
    try:
        with SessionLocal() as session:
            result = session.execute(
                text("SELECT type_analyse, resultat, confidence FROM analyses_ia WHERE plainte_id = :plainte_id"),
                {"plainte_id": plainte_id}
            )
            rows = result.fetchall()
            
            analysis_results = {}
            for row in rows:
                try:
                    # Tenter de parser le JSON, sinon garder le texte brut
                    content = json.loads(row[1]) if row[1] else {}
                except json.JSONDecodeError:
                    content = row[1]
                
                analysis_results[row[0]] = {
                    "success": True,
                    "content": content,
                    "confidence": row[2]
                }
            
            return analysis_results
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des analyses: {str(e)}")
        return {}


# ===== NOUVELLE TÂCHE: Extraction de données PDF asynchrone =====

def notify_websocket(event_type: str, data: Dict[str, Any]):
    """
    Envoie une notification via Redis pub/sub pour le WebSocket
    Le serveur FastAPI écoute ce canal et transmet aux clients connectés
    """
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        
        message = json.dumps({
            "event": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
        
        r.publish('websocket_notifications', message)
        logger.info(f"📡 Notification WebSocket envoyée: {event_type}")
    except Exception as e:
        logger.warning(f"⚠️ Impossible d'envoyer la notification WebSocket: {e}")


@app.task(bind=True, name="extract_pdf_data_async")
def extract_pdf_data_async(self, task_id: str, pdf_text: str, filename: str, temp_file_path: str = None):
    """
    Tâche asynchrone pour extraire les données d'un PDF via IA.
    Envoie le résultat via WebSocket quand terminé.
    
    Args:
        task_id: Identifiant unique de la tâche (pour le frontend)
        pdf_text: Texte extrait du PDF
        filename: Nom du fichier original
        temp_file_path: Chemin vers le fichier PDF temporaire (pour création plainte)
    
    Returns:
        Dict avec les données extraites
    """
    logger.info(f"🔬 [Task {task_id}] Démarrage extraction PDF async: {filename}")
    
    # Notifier le début du traitement - Étape 1: Réception
    notify_websocket("pdf_extraction_started", {
        "task_id": task_id,
        "filename": filename,
        "status": "processing",
        "step": 1,
        "message": "Fichier reçu, préparation de l'analyse..."
    })
    
    try:
        # Initialiser les services
        initialize_services()
        
        # Notifier l'étape 2: Extraction du texte
        notify_websocket("pdf_extraction_progress", {
            "task_id": task_id,
            "step": 2,
            "message": "Extraction du texte en cours..."
        })
        
        # Extraire les données avec le service d'analyse IA
        logger.info(f"🤖 [Task {task_id}] Appel du service d'analyse IA...")
        
        # Notifier l'étape 3: Analyse IA
        notify_websocket("pdf_extraction_progress", {
            "task_id": task_id,
            "step": 3,
            "message": "Analyse IA des données..."
        })
        
        extraction_result = _analysis_service.extract_complaint_data_from_pdf(pdf_text)
        
        if extraction_result.success:
            # Parser le contenu JSON
            try:
                extracted_data = json.loads(extraction_result.content)
            except json.JSONDecodeError:
                extracted_data = {"raw_content": extraction_result.content}
            
            result = {
                "success": True,
                "task_id": task_id,
                "filename": filename,
                "temp_file_path": temp_file_path,  # Chemin du fichier temp pour création plainte
                "extraction": {
                    "donnees_structurees": extracted_data,
                    "texte_brut": pdf_text[:2000],  # Limiter la taille
                    "texte_longueur": len(pdf_text)
                },
                "confidence": extraction_result.confidence,
                "message": "Extraction réussie"
            }
            
            logger.info(f"✅ [Task {task_id}] Extraction réussie avec confiance {extraction_result.confidence}. Fichier temp: {temp_file_path}")
            
            # Notifier le succès via WebSocket
            notify_websocket("pdf_extraction_complete", result)
            
            return result
        else:
            error_result = {
                "success": False,
                "task_id": task_id,
                "filename": filename,
                "error": extraction_result.error or "Erreur d'extraction inconnue",
                "message": "Échec de l'extraction"
            }
            
            logger.error(f"❌ [Task {task_id}] Échec extraction: {extraction_result.error}")
            
            # Notifier l'échec via WebSocket
            notify_websocket("pdf_extraction_failed", error_result)
            
            return error_result
            
    except Exception as e:
        error_msg = f"Erreur lors de l'extraction PDF: {str(e)}"
        logger.error(f"❌ [Task {task_id}] {error_msg}")
        
        error_result = {
            "success": False,
            "task_id": task_id,
            "filename": filename,
            "error": error_msg,
            "message": "Erreur interne"
        }
        
        # Notifier l'erreur via WebSocket
        notify_websocket("pdf_extraction_failed", error_result)
        
        return error_result


@app.task(bind=True, name="extract_image_data_async")
def extract_image_data_async(self, task_id: str, image_path: str, filename: str):
    """
    Tâche asynchrone pour extraire les données d'une image via OCR + IA.
    
    Args:
        task_id: Identifiant unique de la tâche
        image_path: Chemin vers l'image temporaire
        filename: Nom du fichier original
    
    Note: Le fichier temp n'est PAS supprimé ici - il sera utilisé pour créer la plainte
    """
    logger.info(f"📷 [Task {task_id}] Démarrage extraction image async: {filename}")
    
    # Notifier le début du traitement
    notify_websocket("image_extraction_started", {
        "task_id": task_id,
        "filename": filename,
        "status": "processing",
        "message": "OCR et analyse IA en cours..."
    })
    
    try:
        initialize_services()
        
        # Importer le service OCR
        from healthcare_worker_server.app.services.image_ocr import ImageOCRService
        ocr_service = ImageOCRService()
        
        # 1. Extraire le texte via OCR (utiliser extract_text_from_file pour un chemin de fichier)
        logger.info(f"🔍 [Task {task_id}] Extraction OCR depuis fichier: {image_path}")
        ocr_result = ocr_service.extract_text_from_file(image_path)
        
        if not ocr_result.get("success"):
            raise Exception(ocr_result.get("error", "Échec OCR"))
        
        ocr_text = ocr_result.get("text", "")
        ocr_confidence = ocr_result.get("confidence", 0)
        
        # 2. Analyser avec IA
        logger.info(f"🤖 [Task {task_id}] Analyse IA du texte OCR...")
        extraction_result = _analysis_service.extract_complaint_data_from_pdf(ocr_text)
        
        if extraction_result.success:
            try:
                extracted_data = json.loads(extraction_result.content)
            except json.JSONDecodeError:
                extracted_data = {"raw_content": extraction_result.content}
            
            result = {
                "success": True,
                "task_id": task_id,
                "filename": filename,
                "temp_file_path": image_path,  # Chemin du fichier temp pour création plainte
                "extraction": {
                    "donnees_structurees": extracted_data,
                    "texte_brut": ocr_text[:2000],
                    "texte_longueur": len(ocr_text)
                },
                "ocr_info": {
                    "confiance": ocr_confidence,
                    "qualite": ocr_result.get("quality", "unknown")
                },
                "confidence": extraction_result.confidence,
                "message": "Extraction réussie"
            }
            
            logger.info(f"✅ [Task {task_id}] Extraction image réussie. Fichier temp conservé: {image_path}")
            notify_websocket("image_extraction_complete", result)
            
            return result
        else:
            raise Exception(extraction_result.error or "Échec analyse IA")
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ [Task {task_id}] Erreur: {error_msg}")
        
        error_result = {
            "success": False,
            "task_id": task_id,
            "filename": filename,
            "error": error_msg
        }
        
        notify_websocket("image_extraction_failed", error_result)
        
        # En cas d'erreur, on peut supprimer le fichier temp
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
                logger.info(f"🗑️ [Task {task_id}] Fichier temp supprimé après erreur")
        except:
            pass
        
        return error_result
    # Note: PAS de finally avec suppression - le fichier est conservé pour créer la plainte


# ==================== TRAITEMENT ARCHIVE FICHIER ASYNC ====================

@app.task(bind=True, name="process_archive_file_async")
def process_archive_file_async(
    self,
    task_id: str,
    temp_file_path: str,
    filename: str,
    source_archive: str,
    batch_id: str,
    processing_order: int,
    auto_assign_service: bool = True
):
    """
    Tâche asynchrone pour traiter un fichier d'archive et créer une plainte.
    Même mécanisme que extract_pdf_data_async mais crée directement la plainte.
    
    Args:
        task_id: Identifiant unique de la tâche (pour le frontend)
        temp_file_path: Chemin vers le fichier temporaire uploadé
        filename: Nom du fichier original
        source_archive: Nom du dossier d'archive source
        batch_id: ID du batch de traitement
        processing_order: Position dans le batch
        auto_assign_service: Si True, assigne au service détecté par l'IA
    
    Returns:
        Dict avec les résultats de la création de la plainte
    """
    from pathlib import Path
    from shared.models import Plainte, Service, DocumentPlainte, StatutPlainte, PrioritePlainte, TypeFichier
    from sqlalchemy import or_
    import shutil
    from datetime import datetime
    
    logger.info(f"📂 [Archive Task {task_id}] Démarrage: {filename} (batch: {batch_id}, ordre: {processing_order})")
    
    # Vérifier si la tâche a été annulée avant de commencer
    if is_task_cancelled(task_id):
        logger.info(f"🛑 [Archive Task {task_id}] Tâche annulée avant démarrage")
        notify_websocket("archive_file_cancelled", {
            "task_id": task_id,
            "batch_id": batch_id,
            "filename": filename,
            "message": "Tâche annulée"
        })
        return {"success": False, "filename": filename, "cancelled": True, "error": "Tâche annulée par l'utilisateur"}
    
    # Notifier le début du traitement
    notify_websocket("archive_file_started", {
        "task_id": task_id,
        "batch_id": batch_id,
        "filename": filename,
        "processing_order": processing_order,
        "status": "processing",
        "step": 1,
        "message": "Fichier reçu, extraction du texte..."
    })
    
    try:
        initialize_services()
        
        path = Path(temp_file_path)
        
        if not path.exists():
            raise Exception(f"Fichier temporaire non trouvé: {temp_file_path}")
        
        # Déterminer le type de fichier
        suffix = path.suffix.lower()
        is_pdf = suffix == '.pdf'
        is_image = suffix in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
        
        if not is_pdf and not is_image:
            raise Exception(f"Type de fichier non supporté: {suffix}")
        
        # Notifier étape 2: Extraction du texte
        notify_websocket("archive_file_progress", {
            "task_id": task_id,
            "batch_id": batch_id,
            "step": 2,
            "message": "Extraction du texte en cours..."
        })
        
        # Extraction du texte
        extracted_text = ""
        extraction_confidence = 0.0
        
        if is_pdf:
            try:
                extraction_result = _document_parser.extract_text_from_document(str(path))
                if extraction_result.get("success"):
                    extracted_text = extraction_result.get("text", "")
                    logger.info(f"📝 [Archive Task {task_id}] Texte PDF extrait: {len(extracted_text)} caractères")
            except Exception as e:
                logger.warning(f"⚠️ [Archive Task {task_id}] Erreur extraction PDF: {e}")
            
            # Fallback PyPDF2
            if not extracted_text:
                try:
                    import PyPDF2
                    with open(path, 'rb') as f:
                        pdf_reader = PyPDF2.PdfReader(f)
                        for page in pdf_reader.pages:
                            page_text = page.extract_text()
                            if page_text:
                                extracted_text += page_text + "\n"
                    logger.info(f"📝 [Archive Task {task_id}] Texte PDF extrait (fallback): {len(extracted_text)} caractères")
                except Exception as e:
                    logger.warning(f"⚠️ [Archive Task {task_id}] Erreur fallback PDF: {e}")
        
        elif is_image:
            try:
                from healthcare_worker_server.app.services.image_ocr import get_ocr_service
                ocr_service = get_ocr_service()
                ocr_result = ocr_service.extract_text_from_file(str(path))
                
                if ocr_result.get("success"):
                    extracted_text = ocr_result.get("text", "")
                    extraction_confidence = ocr_result.get("confidence", 0.0)
                    logger.info(f"📝 [Archive Task {task_id}] Texte OCR extrait: {len(extracted_text)} caractères (confiance: {extraction_confidence})")
            except Exception as e:
                logger.warning(f"⚠️ [Archive Task {task_id}] Erreur OCR: {e}")
        
        if not extracted_text:
            raise Exception("Impossible d'extraire du texte du fichier")
        
        # Vérifier l'annulation après extraction
        if is_task_cancelled(task_id):
            logger.info(f"🛑 [Archive Task {task_id}] Tâche annulée après extraction")
            notify_websocket("archive_file_cancelled", {
                "task_id": task_id,
                "batch_id": batch_id,
                "filename": filename,
                "message": "Tâche annulée après extraction"
            })
            return {"success": False, "filename": filename, "cancelled": True, "error": "Tâche annulée par l'utilisateur"}
        
        # Notifier étape 3: Analyse IA
        notify_websocket("archive_file_progress", {
            "task_id": task_id,
            "batch_id": batch_id,
            "step": 3,
            "message": "Analyse IA des données..."
        })
        
        # Analyse IA
        extracted_data = None
        try:
            analysis_result = _analysis_service.extract_complaint_data_from_pdf(extracted_text)
            if analysis_result.success:
                extracted_data = json.loads(analysis_result.content)
                logger.info(f"🤖 [Archive Task {task_id}] Analyse IA réussie avec confiance: {analysis_result.confidence}")
        except Exception as e:
            logger.warning(f"⚠️ [Archive Task {task_id}] Erreur analyse IA: {e} - Utilisation données basiques")
        
        # Vérifier l'annulation après analyse IA
        if is_task_cancelled(task_id):
            logger.info(f"🛑 [Archive Task {task_id}] Tâche annulée après analyse IA")
            notify_websocket("archive_file_cancelled", {
                "task_id": task_id,
                "batch_id": batch_id,
                "filename": filename,
                "message": "Tâche annulée après analyse"
            })
            return {"success": False, "filename": filename, "cancelled": True, "error": "Tâche annulée par l'utilisateur"}
        
        # Notifier étape 4: Création de la plainte
        notify_websocket("archive_file_progress", {
            "task_id": task_id,
            "batch_id": batch_id,
            "step": 4,
            "message": "Création de la plainte..."
        })
        
        # Construire les données de la plainte
        titre = f"Plainte importée: {filename}"
        description = extracted_text[:5000]
        nom_plaignant = "Non spécifié"
        prenom_plaignant = "Non spécifié"
        email_plaignant = None
        telephone_plaignant = None
        date_incident = None
        priorite = "MOYEN"
        service_id = None
        
        if extracted_data:
            plaignant = extracted_data.get("plaignant", {})
            nom_plaignant = plaignant.get("nom") or nom_plaignant
            prenom_plaignant = plaignant.get("prenom") or prenom_plaignant
            email_plaignant = plaignant.get("email")
            telephone_plaignant = plaignant.get("telephone")
            
            plainte_data = extracted_data.get("plainte", {})
            titre = plainte_data.get("titre") or titre
            description = plainte_data.get("description") or description
            date_incident = plainte_data.get("date_incident")
            
            analyse = extracted_data.get("analyse", {})
            priorite = analyse.get("priorite_suggeree") or priorite
        
        # Créer une session de base de données
        db = SessionLocal()
        
        try:
            # Service auto ou par défaut
            if auto_assign_service and extracted_data:
                service_concerne = extracted_data.get("plainte", {}).get("service_concerne")
                if service_concerne:
                    service = db.query(Service).filter(
                        or_(
                            Service.nom.ilike(f"%{service_concerne}%"),
                            Service.code_service.ilike(f"%{service_concerne}%")
                        )
                    ).first()
                    if service:
                        service_id = service.id
                        logger.info(f"🏥 [Archive Task {task_id}] Service auto-détecté: {service.nom}")
            
            if not service_id:
                default_service = db.query(Service).filter(
                    or_(Service.code_service == "ADM", Service.nom.ilike("%administratif%"))
                ).first()
                if default_service:
                    service_id = default_service.id
                else:
                    first_service = db.query(Service).first()
                    if first_service:
                        service_id = first_service.id
                    else:
                        raise Exception("Aucun service disponible dans la base de données")
            
            # Générer numéro de plainte
            current_year = datetime.now().year
            prefix = f"PL_{current_year}_"
            
            last_plainte = db.query(Plainte.numero_plainte).filter(
                Plainte.numero_plainte.like(f"{prefix}%")
            ).order_by(Plainte.numero_plainte.desc()).first()
            
            if last_plainte and last_plainte[0]:
                try:
                    last_num = int(last_plainte[0].replace(prefix, ""))
                    next_num = last_num + 1
                except ValueError:
                    next_num = 1
            else:
                next_num = 1
            
            numero_plainte = f"{prefix}{str(next_num).zfill(4)}"
            
            # Vérifier unicité
            while db.query(Plainte).filter(Plainte.numero_plainte == numero_plainte).first():
                next_num += 1
                numero_plainte = f"{prefix}{str(next_num).zfill(4)}"
            
            # Créer la plainte
            try:
                priorite_enum = PrioritePlainte(priorite.upper())
            except ValueError:
                priorite_enum = PrioritePlainte.MOYEN
            
            new_plainte = Plainte(
                numero_plainte=numero_plainte,
                titre=titre,
                description=description,
                statut=StatutPlainte.RECU,
                priorite=priorite_enum,
                service_id=service_id,
                date_incident=datetime.strptime(date_incident, "%Y-%m-%d").date() if date_incident and isinstance(date_incident, str) else None,
                nom_plaignant=nom_plaignant,
                prenom_plaignant=prenom_plaignant,
                email_plaignant=email_plaignant,
                telephone_plaignant=telephone_plaignant,
                mode_reception="archive_import"
            )
            
            db.add(new_plainte)
            db.flush()
            
            # Copier le fichier vers le dossier documents
            if is_image:
                docs_dir = Path("data/documents/images_originales")
            else:
                docs_dir = Path("data/documents/pdf_originaux")
            
            docs_dir.mkdir(parents=True, exist_ok=True)
            
            safe_filename = filename.replace(" ", "_").replace("/", "_").replace("\\", "_")
            final_filename = f"{numero_plainte}_{safe_filename}"
            dest_path = docs_dir / final_filename
            
            shutil.copy2(str(path), str(dest_path))
            
            # Créer le document associé
            type_fichier = TypeFichier.PDF if is_pdf else TypeFichier.IMAGE
            
            document = DocumentPlainte(
                plainte_id=new_plainte.id,
                nom_fichier=filename,
                nom_stockage=final_filename,
                chemin_fichier=str(dest_path),
                type_fichier=type_fichier,
                taille_fichier=path.stat().st_size,
                est_piece_jointe_originale=True
            )
            
            db.add(document)
            db.commit()
            db.refresh(new_plainte)
            
            logger.info(f"✅ [Archive Task {task_id}] Plainte {numero_plainte} créée depuis {filename}")
            
            # 🚀 IMPORTANT: Lancer l'analyse IA complète (sentiment, résumé, réponse juridique, PDF)
            try:
                logger.info(f"🚀 [Archive Task {task_id}] Lancement de l'analyse IA complète pour plainte {new_plainte.id}...")
                
                # Récupérer les données de la plainte
                plainte_data = get_plainte_data(new_plainte.id)
                
                if plainte_data:
                    # Exécuter le workflow complet via l'orchestrateur
                    workflow_result = _orchestrator.process_complaint_complete(plainte_data, str(dest_path))
                    
                    # Sauvegarder les résultats (inclut la réponse juridique)
                    save_analysis_results(new_plainte.id, workflow_result)
                    
                    # 📄 IMPORTANT: Sauvegarder le chemin du PDF généré
                    pdf_report = workflow_result.get("pdf_report", {})
                    if pdf_report.get("success") and pdf_report.get("file_path"):
                        save_pdf_path(new_plainte.id, pdf_report["file_path"])
                        logger.info(f"📄 [Archive Task {task_id}] PDF rattaché: {pdf_report['file_path']}")
                    
                    # Mettre à jour le statut
                    update_plainte_status(new_plainte.id, "EN_COURS")
                    
                    logger.info(f"✅ [Archive Task {task_id}] Analyse IA complète terminée pour plainte {new_plainte.id}")
                else:
                    logger.warning(f"⚠️ [Archive Task {task_id}] Données plainte non trouvées pour analyse IA")
                    
            except Exception as analysis_error:
                logger.warning(f"⚠️ [Archive Task {task_id}] Erreur analyse IA (non bloquante): {analysis_error}")
            
            # Nettoyer le fichier temporaire
            try:
                if path.exists():
                    os.remove(str(path))
                    logger.info(f"🗑️ [Archive Task {task_id}] Fichier temp supprimé")
            except:
                pass
            
            # Récupérer le service pour la réponse
            service = db.query(Service).filter(Service.id == service_id).first()
            
            result = {
                "success": True,
                "task_id": task_id,
                "batch_id": batch_id,
                "filename": filename,
                "processing_order": processing_order,
                "plainte_id": new_plainte.id,
                "numero_plainte": numero_plainte,
                "plainte": {
                    "id": new_plainte.id,
                    "numero_plainte": numero_plainte,
                    "titre": titre[:100] + "..." if len(titre) > 100 else titre,
                    "statut": new_plainte.statut.value if hasattr(new_plainte.statut, 'value') else str(new_plainte.statut),
                    "priorite": new_plainte.priorite.value if hasattr(new_plainte.priorite, 'value') else str(new_plainte.priorite),
                    "service_id": service_id,
                    "service_nom": service.nom if service else "Non défini"
                },
                "plaignant": {
                    "nom": nom_plaignant,
                    "prenom": prenom_plaignant
                },
                "message": f"Plainte {numero_plainte} créée avec succès"
            }
            
            # Notifier le succès via WebSocket
            notify_websocket("archive_file_complete", result)
            
            return result
            
        finally:
            db.close()
            
    except Exception as e:
        error_msg = f"Erreur lors du traitement: {str(e)}"
        logger.error(f"❌ [Archive Task {task_id}] {error_msg}")
        
        error_result = {
            "success": False,
            "task_id": task_id,
            "batch_id": batch_id,
            "filename": filename,
            "processing_order": processing_order,
            "error": error_msg,
            "message": "Échec du traitement"
        }
        
        # Notifier l'erreur via WebSocket
        notify_websocket("archive_file_failed", error_result)
        
        return error_result


# ==================== TRAITEMENT ARCHIVE BATCH ====================

@app.task(bind=True, name="process_archive_batch")
def process_archive_batch(
    self,
    files_list: list,
    batch_id: str,
    options: dict = None
) -> dict:
    """
    Traitement batch de fichiers d'archive pour création de plaintes.
    
    Cette tâche traite une liste de fichiers (PDF/images) et crée
    automatiquement des plaintes pour chacun.
    
    Args:
        files_list: Liste de fichiers [{"filepath": "...", "filename": "..."}]
        batch_id: ID unique du batch pour le suivi
        options: Options de traitement {
            "auto_assign_service": bool,
            "batch_size": int,
            "continue_on_error": bool
        }
    
    Returns:
        Résultat du traitement avec statistiques
    """
    from pathlib import Path
    from shared.models import Plainte, Service, DocumentPlainte, StatutPlainte, PrioritePlainte, TypeFichier
    
    if options is None:
        options = {}
    
    auto_assign_service = options.get("auto_assign_service", True)
    continue_on_error = options.get("continue_on_error", True)
    
    logger.info(f"📦 [Batch {batch_id}] Démarrage traitement de {len(files_list)} fichiers")
    
    # Notifier le démarrage
    notify_websocket("archive_batch_started", {
        "batch_id": batch_id,
        "total_files": len(files_list),
        "message": f"Démarrage du traitement de {len(files_list)} fichiers"
    })
    
    results = []
    success_count = 0
    fail_count = 0
    
    try:
        initialize_services()
        
        # Créer une session de base de données
        db = SessionLocal()
        
        try:
            for index, file_info in enumerate(files_list):
                file_path = file_info.get("filepath")
                filename = file_info.get("filename", Path(file_path).name if file_path else "unknown")
                
                # Notifier le début du traitement de ce fichier
                notify_websocket("archive_file_processing", {
                    "batch_id": batch_id,
                    "file_id": f"file_{index}",
                    "filename": filename,
                    "current_index": index + 1,
                    "total": len(files_list),
                    "progress": 25,
                    "message": f"Traitement de {filename}..."
                })
                
                try:
                    result = process_single_archive_file(
                        db=db,
                        file_path=file_path,
                        filename=filename,
                        batch_id=batch_id,
                        processing_order=index + 1,
                        auto_assign_service=auto_assign_service
                    )
                    
                    if result.get("success"):
                        success_count += 1
                        notify_websocket("archive_file_complete", {
                            "batch_id": batch_id,
                            "file_id": f"file_{index}",
                            "filename": filename,
                            "plainte_id": result.get("plainte_id"),
                            "plainte_numero": result.get("numero_plainte"),
                            "current_index": index + 1,
                            "total": len(files_list)
                        })
                    else:
                        fail_count += 1
                        notify_websocket("archive_file_failed", {
                            "batch_id": batch_id,
                            "file_id": f"file_{index}",
                            "filename": filename,
                            "error": result.get("error", "Erreur inconnue"),
                            "current_index": index + 1,
                            "total": len(files_list)
                        })
                    
                    results.append(result)
                    
                except Exception as file_error:
                    fail_count += 1
                    error_msg = str(file_error)
                    logger.error(f"❌ [Batch {batch_id}] Erreur fichier {filename}: {error_msg}")
                    
                    notify_websocket("archive_file_failed", {
                        "batch_id": batch_id,
                        "file_id": f"file_{index}",
                        "filename": filename,
                        "error": error_msg,
                        "current_index": index + 1,
                        "total": len(files_list)
                    })
                    
                    results.append({
                        "success": False,
                        "filename": filename,
                        "error": error_msg
                    })
                    
                    if not continue_on_error:
                        logger.info(f"⏹️ [Batch {batch_id}] Arrêt sur erreur (continue_on_error=False)")
                        break
            
        finally:
            db.close()
        
        # Notifier la fin du batch
        notify_websocket("archive_batch_complete", {
            "batch_id": batch_id,
            "success_count": success_count,
            "fail_count": fail_count,
            "total": len(files_list),
            "message": f"Traitement terminé: {success_count} réussies, {fail_count} échecs"
        })
        
        logger.info(f"✅ [Batch {batch_id}] Terminé: {success_count} réussies, {fail_count} échecs")
        
        return {
            "success": True,
            "batch_id": batch_id,
            "total_files": len(files_list),
            "success_count": success_count,
            "fail_count": fail_count,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"❌ [Batch {batch_id}] Erreur globale: {str(e)}")
        
        notify_websocket("archive_batch_failed", {
            "batch_id": batch_id,
            "error": str(e),
            "message": f"Erreur lors du traitement batch: {str(e)}"
        })
        
        return {
            "success": False,
            "batch_id": batch_id,
            "error": str(e),
            "results": results
        }


def process_single_archive_file(
    db,
    file_path: str,
    filename: str,
    batch_id: str,
    processing_order: int,
    auto_assign_service: bool = True
) -> dict:
    """
    Traite un seul fichier d'archive et crée la plainte correspondante.
    
    Args:
        db: Session de base de données
        file_path: Chemin absolu vers le fichier
        filename: Nom du fichier
        batch_id: ID du batch
        processing_order: Ordre dans le batch
        auto_assign_service: Si True, assigne au service détecté
        
    Returns:
        Dictionnaire avec le résultat du traitement
    """
    from pathlib import Path
    from shared.models import Plainte, Service, DocumentPlainte, StatutPlainte, PrioritePlainte, TypeFichier
    from sqlalchemy import or_
    import shutil
    
    # Initialiser les services (nécessaire pour l'orchestrateur)
    initialize_services()
    
    logger.info(f"📄 Traitement fichier archive: {filename}")
    
    path = Path(file_path)
    
    if not path.exists():
        return {"success": False, "filename": filename, "error": "Fichier non trouvé"}
    
    # Déterminer le type de fichier
    suffix = path.suffix.lower()
    is_pdf = suffix == '.pdf'
    is_image = suffix in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
    
    if not is_pdf and not is_image:
        return {"success": False, "filename": filename, "error": f"Type de fichier non supporté: {suffix}"}
    
    # Extraction du texte
    extracted_text = ""
    extraction_confidence = 0.0
    
    if is_pdf:
        try:
            extraction_result = _document_parser.extract_text_from_document(str(path))
            if extraction_result.get("success"):
                extracted_text = extraction_result.get("text", "")
        except Exception as e:
            logger.warning(f"Erreur extraction PDF: {e}")
        
        # Fallback PyPDF2
        if not extracted_text:
            try:
                import PyPDF2
                with open(path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            extracted_text += page_text + "\n"
            except Exception as e:
                logger.warning(f"Erreur fallback PDF: {e}")
    
    elif is_image:
        try:
            from healthcare_worker_server.app.services.image_ocr import get_ocr_service
            ocr_service = get_ocr_service()
            ocr_result = ocr_service.extract_text_from_file(str(path))
            
            if ocr_result.get("success"):
                extracted_text = ocr_result.get("text", "")
                extraction_confidence = ocr_result.get("confidence", 0.0)
        except Exception as e:
            logger.warning(f"Erreur OCR: {e}")
    
    if not extracted_text:
        return {"success": False, "filename": filename, "error": "Impossible d'extraire du texte"}
    
    # Analyse IA
    extracted_data = None
    try:
        analysis_result = _analysis_service.extract_complaint_data_from_pdf(extracted_text)
        if analysis_result.success:
            extracted_data = json.loads(analysis_result.content)
    except Exception as e:
        logger.warning(f"Erreur analyse IA: {e}")
    
    # Construire les données de la plainte
    titre = f"Plainte importée: {filename}"
    description = extracted_text[:5000]
    nom_plaignant = "Non spécifié"
    prenom_plaignant = "Non spécifié"
    email_plaignant = None
    telephone_plaignant = None
    date_incident = None
    priorite = "MOYEN"
    service_id = None
    
    if extracted_data:
        plaignant = extracted_data.get("plaignant", {})
        nom_plaignant = plaignant.get("nom") or nom_plaignant
        prenom_plaignant = plaignant.get("prenom") or prenom_plaignant
        email_plaignant = plaignant.get("email")
        telephone_plaignant = plaignant.get("telephone")
        
        plainte_data = extracted_data.get("plainte", {})
        titre = plainte_data.get("titre") or titre
        description = plainte_data.get("description") or description
        date_incident = plainte_data.get("date_incident")
        
        analyse = extracted_data.get("analyse", {})
        priorite = analyse.get("priorite_suggeree") or priorite
        
        if auto_assign_service:
            service_concerne = plainte_data.get("service_concerne")
            if service_concerne:
                service = db.query(Service).filter(
                    or_(
                        Service.nom.ilike(f"%{service_concerne}%"),
                        Service.code_service.ilike(f"%{service_concerne}%")
                    )
                ).first()
                if service:
                    service_id = service.id
    
    # Service par défaut
    if not service_id:
        default_service = db.query(Service).filter(
            or_(Service.code_service == "ADM", Service.nom.ilike("%administratif%"))
        ).first()
        if default_service:
            service_id = default_service.id
        else:
            first_service = db.query(Service).first()
            if first_service:
                service_id = first_service.id
            else:
                return {"success": False, "filename": filename, "error": "Aucun service disponible"}
    
    # Générer numéro de plainte (même logique que plaintes_creation.py)
    current_year = datetime.now().year
    prefix = f"PL_{current_year}_"
    
    last_plainte = db.query(Plainte.numero_plainte).filter(
        Plainte.numero_plainte.like(f"{prefix}%")
    ).order_by(Plainte.numero_plainte.desc()).first()
    
    if last_plainte and last_plainte[0]:
        try:
            last_num = int(last_plainte[0].replace(prefix, ""))
            next_num = last_num + 1
        except ValueError:
            next_num = 1
    else:
        next_num = 1
    
    numero_plainte = f"{prefix}{str(next_num).zfill(4)}"
    
    # Vérification de sécurité: s'assurer que le numéro n'existe pas déjà
    max_attempts = 100  # Éviter boucle infinie
    attempts = 0
    while db.query(Plainte).filter(Plainte.numero_plainte == numero_plainte).first() and attempts < max_attempts:
        next_num += 1
        numero_plainte = f"{prefix}{str(next_num).zfill(4)}"
        attempts += 1
    
    if attempts >= max_attempts:
        # Fallback: utiliser un UUID partiel pour garantir l'unicité
        import uuid
        numero_plainte = f"{prefix}{str(uuid.uuid4())[:8].upper()}"
    
    logger.info(f"📝 [Archive] Numéro de plainte généré: {numero_plainte}")
    
    # Créer la plainte
    try:
        priorite_enum = PrioritePlainte(priorite.upper())
    except ValueError:
        priorite_enum = PrioritePlainte.MOYEN
    
    now = datetime.now()
    new_plainte = Plainte(
        numero_plainte=numero_plainte,
        titre=titre,
        description=description,
        statut=StatutPlainte.RECU,
        priorite=priorite_enum,
        service_id=service_id,
        date_creation=now,
        date_modification=now,
        date_incident=datetime.strptime(date_incident, "%Y-%m-%d").date() if date_incident and isinstance(date_incident, str) else None,
        nom_plaignant=nom_plaignant,
        prenom_plaignant=prenom_plaignant,
        email_plaignant=email_plaignant,
        telephone_plaignant=telephone_plaignant,
        mode_reception="archive_import"
    )
    
    db.add(new_plainte)
    db.flush()
    
    # Copier le fichier vers le dossier documents
    if is_image:
        docs_dir = Path("data/documents/images_originales")
    else:
        docs_dir = Path("data/documents/pdf_originaux")
    
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    safe_filename = filename.replace(" ", "_").replace("/", "_").replace("\\", "_")
    final_filename = f"{numero_plainte}_{safe_filename}"
    dest_path = docs_dir / final_filename
    
    shutil.copy2(str(path), str(dest_path))
    
    # Créer le document associé
    type_fichier = TypeFichier.PDF if is_pdf else TypeFichier.IMAGE
    
    document = DocumentPlainte(
        plainte_id=new_plainte.id,
        nom_fichier=filename,
        nom_stockage=final_filename,
        chemin_fichier=str(dest_path),
        type_fichier=type_fichier,
        taille_fichier=path.stat().st_size,
        est_piece_jointe_originale=True
    )
    
    db.add(document)
    db.commit()
    db.refresh(new_plainte)
    
    logger.info(f"✅ Plainte {numero_plainte} créée depuis {filename}")
    
    # 🚀 IMPORTANT: Lancer l'analyse IA complète (sentiment, résumé, réponse juridique, PDF)
    try:
        logger.info(f"🚀 Lancement de l'analyse IA complète pour plainte {new_plainte.id}...")
        
        # Récupérer les données de la plainte
        plainte_data = get_plainte_data(new_plainte.id)
        
        if plainte_data:
            # Exécuter le workflow complet via l'orchestrateur
            workflow_result = _orchestrator.process_complaint_complete(plainte_data, str(dest_path))
            
            # Sauvegarder les résultats (inclut la réponse juridique)
            save_analysis_results(new_plainte.id, workflow_result)
            
            # 📄 IMPORTANT: Sauvegarder le chemin du PDF généré
            pdf_report = workflow_result.get("pdf_report", {})
            if pdf_report.get("success") and pdf_report.get("file_path"):
                save_pdf_path(new_plainte.id, pdf_report["file_path"])
                logger.info(f"📄 PDF rattaché: {pdf_report['file_path']}")
            
            # Mettre à jour le statut
            update_plainte_status(new_plainte.id, "EN_COURS")
            
            logger.info(f"✅ Analyse IA complète terminée pour plainte {new_plainte.id}")
        else:
            logger.warning(f"⚠️ Données plainte non trouvées pour analyse IA")
            
    except Exception as analysis_error:
        logger.warning(f"⚠️ Erreur analyse IA (non bloquante): {analysis_error}")
    
    return {
        "success": True,
        "filename": filename,
        "plainte_id": new_plainte.id,
        "numero_plainte": numero_plainte
    }


if __name__ == '__main__':
    logger.info("🚀 Démarrage du worker Celery modulaire")
    app.start()
