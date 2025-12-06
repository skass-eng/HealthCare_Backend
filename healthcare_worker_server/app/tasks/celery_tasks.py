"""
Tâches Celery modulaires pour le traitement des plaintes
Utilise l'architecture modulaire avec l'orchestrateur
"""
import logging
import os
import sys
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
DATABASE_URL = "postgresql://daniel:Gse45Dk78p@localhost/healthcare_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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
    """Sauvegarde tous les résultats d'analyse"""
    try:
        with SessionLocal() as session:
            # Sauvegarder en JSON dans la table analyses_ia
            session.execute(
                text("""
                    INSERT INTO analyses_ia (plainte_id, type_analyse, resultat, confidence, statut)
                    VALUES (:plainte_id, 'workflow_complete', :resultat, :confidence, :statut)
                    ON CONFLICT (plainte_id, type_analyse) 
                    DO UPDATE SET resultat = EXCLUDED.resultat, confidence = EXCLUDED.confidence, statut = EXCLUDED.statut
                """),
                {
                    "plainte_id": plainte_id,
                    "resultat": json.dumps(workflow_result, ensure_ascii=False),
                    "confidence": 0.9 if workflow_result.get("success", False) else 0.1,
                    "statut": "COMPLETE" if workflow_result.get("success", False) else "ERREUR"
                }
            )
            session.commit()
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde des résultats: {str(e)}")

def update_plainte_status(plainte_id: int, new_status: str):
    """Met à jour le statut d'une plainte"""
    try:
        with SessionLocal() as session:
            session.execute(
                text("UPDATE plaintes SET statut = :status WHERE id = :plainte_id"),
                {"status": new_status, "plainte_id": plainte_id}
            )
            session.commit()
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour du statut: {str(e)}")

def save_extracted_text(plainte_id: int, parsing_result: Dict[str, Any]):
    """Sauvegarde le texte extrait d'un document"""
    try:
        with SessionLocal() as session:
            session.execute(
                text("""
                    INSERT INTO analyses_ia (plainte_id, type_analyse, resultat, confidence, statut)
                    VALUES (:plainte_id, 'document_parsing', :resultat, :confidence, 'COMPLETE')
                    ON CONFLICT (plainte_id, type_analyse) 
                    DO UPDATE SET resultat = EXCLUDED.resultat, confidence = EXCLUDED.confidence
                """),
                {
                    "plainte_id": plainte_id,
                    "resultat": json.dumps(parsing_result, ensure_ascii=False),
                    "confidence": 0.9 if parsing_result.get("success", False) else 0.1
                }
            )
            session.commit()
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde du texte extrait: {str(e)}")

def save_sentiment_analysis(plainte_id: int, sentiment_result):
    """Sauvegarde l'analyse de sentiment"""
    try:
        with SessionLocal() as session:
            session.execute(
                text("""
                    INSERT INTO analyses_ia (plainte_id, type_analyse, resultat, confidence, statut)
                    VALUES (:plainte_id, 'sentiment', :resultat, :confidence, 'COMPLETE')
                    ON CONFLICT (plainte_id, type_analyse) 
                    DO UPDATE SET resultat = EXCLUDED.resultat, confidence = EXCLUDED.confidence
                """),
                {
                    "plainte_id": plainte_id,
                    "resultat": sentiment_result.content,
                    "confidence": sentiment_result.confidence
                }
            )
            session.commit()
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde de l'analyse de sentiment: {str(e)}")

def save_summary_analysis(plainte_id: int, summary_result):
    """Sauvegarde le résumé"""
    try:
        with SessionLocal() as session:
            session.execute(
                text("""
                    INSERT INTO analyses_ia (plainte_id, type_analyse, resultat, confidence, statut)
                    VALUES (:plainte_id, 'summary', :resultat, :confidence, 'COMPLETE')
                    ON CONFLICT (plainte_id, type_analyse) 
                    DO UPDATE SET resultat = EXCLUDED.resultat, confidence = EXCLUDED.confidence
                """),
                {
                    "plainte_id": plainte_id,
                    "resultat": summary_result.content,
                    "confidence": summary_result.confidence
                }
            )
            session.commit()
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde du résumé: {str(e)}")

def save_contacts_analysis(plainte_id: int, contacts_result):
    """Sauvegarde l'extraction de contacts"""
    try:
        with SessionLocal() as session:
            session.execute(
                text("""
                    INSERT INTO analyses_ia (plainte_id, type_analyse, resultat, confidence, statut)
                    VALUES (:plainte_id, 'contacts', :resultat, :confidence, 'COMPLETE')
                    ON CONFLICT (plainte_id, type_analyse) 
                    DO UPDATE SET resultat = EXCLUDED.resultat, confidence = EXCLUDED.confidence
                """),
                {
                    "plainte_id": plainte_id,
                    "resultat": contacts_result.content,
                    "confidence": contacts_result.confidence
                }
            )
            session.commit()
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde de l'extraction de contacts: {str(e)}")

def save_legal_response(plainte_id: int, legal_result):
    """Sauvegarde la réponse juridique"""
    try:
        with SessionLocal() as session:
            session.execute(
                text("""
                    INSERT INTO analyses_ia (plainte_id, type_analyse, resultat, confidence, statut)
                    VALUES (:plainte_id, 'legal_response', :resultat, :confidence, 'COMPLETE')
                    ON CONFLICT (plainte_id, type_analyse) 
                    DO UPDATE SET resultat = EXCLUDED.resultat, confidence = EXCLUDED.confidence
                """),
                {
                    "plainte_id": plainte_id,
                    "resultat": legal_result.content,
                    "confidence": legal_result.confidence
                }
            )
            session.commit()
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde de la réponse juridique: {str(e)}")

def save_pdf_path(plainte_id: int, pdf_path: str):
    """Sauvegarde le chemin du PDF généré"""
    try:
        with SessionLocal() as session:
            session.execute(
                text("UPDATE plaintes SET chemin_pdf = :pdf_path WHERE id = :plainte_id"),
                {"pdf_path": pdf_path, "plainte_id": plainte_id}
            )
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
def extract_pdf_data_async(self, task_id: str, pdf_text: str, filename: str):
    """
    Tâche asynchrone pour extraire les données d'un PDF via IA.
    Envoie le résultat via WebSocket quand terminé.
    
    Args:
        task_id: Identifiant unique de la tâche (pour le frontend)
        pdf_text: Texte extrait du PDF
        filename: Nom du fichier original
    
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
                "extraction": {
                    "donnees_structurees": extracted_data,
                    "texte_brut": pdf_text[:2000],  # Limiter la taille
                    "texte_longueur": len(pdf_text)
                },
                "confidence": extraction_result.confidence,
                "message": "Extraction réussie"
            }
            
            logger.info(f"✅ [Task {task_id}] Extraction réussie avec confiance {extraction_result.confidence}")
            
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
            
            logger.info(f"✅ [Task {task_id}] Extraction image réussie")
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
        return error_result
    finally:
        # Nettoyer le fichier temporaire
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
        except:
            pass


if __name__ == '__main__':
    logger.info("🚀 Démarrage du worker Celery modulaire")
    app.start()
