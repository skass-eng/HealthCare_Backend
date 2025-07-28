"""
Processeur de fichiers pour le traitement complet des plaintes
Orchestre : extraction de texte + analyse IA + mise à jour BDD + déplacement
"""

import os
import shutil
import json
import logging
from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from services.pdf_extractor import pdf_extractor
from services.ai_analyzer import ai_analyzer
from services.llm_analyzer import LLMAnalyzer
from models import Plainte, FichierPlainte, SuggestionIA, ServiceEnum, PrioriteEnum, StatusEnum
from database import SessionLocal
from config import settings

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileProcessor:
    """Processeur de fichiers pour les plaintes"""
    
    def __init__(self):
        # Créer les dossiers nécessaires
        self.processed_dir = settings.DATA_TRAITES_DIR
        self.failed_dir = settings.DATA_ECHECS_DIR
        
        os.makedirs(self.processed_dir, exist_ok=True)
        os.makedirs(self.failed_dir, exist_ok=True)
        
        # Initialiser les analyseurs
        self.use_llm = settings.USE_LLM_ANALYSIS
        self.fallback_to_basic = settings.FALLBACK_TO_BASIC_AI
        
        # Initialiser le LLM si configuré
        self.llm_analyzer = None
        if self.use_llm:
            try:
                llm_config = settings.get_llm_config()
                
                # Vérifier si la configuration LLM est valide
                if llm_config.get('provider') == 'openai' and not llm_config.get('api_key'):
                    logger.warning("⚠️ LLM activé mais pas de clé OpenAI configurée - utilisation analyseur basique")
                    logger.info("💡 Pour activer le LLM : définissez OPENAI_API_KEY dans votre .env")
                else:
                    self.llm_analyzer = LLMAnalyzer(**llm_config)
                    logger.info(f"🤖 LLM Analyzer initialisé avec {llm_config['provider']}")
                    
            except Exception as e:
                logger.error(f"❌ Erreur initialisation LLM: {e}")
                if not self.fallback_to_basic:
                    raise
                logger.warning("🔄 Utilisation de l'analyseur basique en secours")
        
        logger.info("🚀 FileProcessor initialisé")
    
    def analyze_complaint_with_llm(self, text_content: str, fichier: FichierPlainte) -> Dict:
        """
        Analyser une plainte avec LLM ou fallback vers l'analyseur basique
        """
        metadata = {
            'filename': fichier.nom_original,
            'file_type': fichier.type_fichier.value if fichier.type_fichier else None,
            'upload_date': fichier.date_upload.isoformat() if fichier.date_upload else None,
            'file_size': fichier.taille_fichier
        }
        
        # Tentative d'analyse avec LLM
        if self.llm_analyzer:
            try:
                logger.info("🤖 Analyse avec LLM...")
                llm_result = self.llm_analyzer.analyze_complaint_complete(text_content, metadata)
                
                # NOUVEAU: Passer directement les résultats LLM (format multi-prompts)
                # Plus besoin de conversion vers l'ancien format !
                llm_result['analysis_method'] = 'LLM'
                llm_result['confidence'] = llm_result.get('confidence_score', 0.8)
                
                logger.info(f"✅ Analyse LLM terminée - Service: {llm_result.get('service')}, Sentiment: {llm_result.get('sentiment')}")
                logger.info(f"📞 Contact détecté - Nom: {llm_result.get('contact_info', {}).get('nom', 'N/A')}")
                
                return llm_result
                
            except Exception as e:
                logger.error(f"❌ Erreur analyse LLM: {e}")
                if not self.fallback_to_basic:
                    raise
                logger.warning("🔄 Basculement vers l'analyseur basique")
        
        # Fallback vers l'analyseur basique
        logger.info("🔧 Analyse avec l'analyseur basique...")
        basic_result = ai_analyzer.analyze_complaint(text_content)
        basic_result['analysis_method'] = 'Basic'
        basic_result['confidence'] = 0.6
        
        return basic_result
    
    def process_file(self, file_path: str, plainte_id: str) -> Dict[str, any]:
        """Traiter complètement un fichier de plainte"""
        logger.info(f"🔄 Début du traitement du fichier: {file_path}")
        
        db = SessionLocal()
        result = {
            'success': False,
            'file_path': file_path,
            'plainte_id': plainte_id,
            'steps_completed': [],
            'errors': [],
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Étape 1: Récupérer la plainte depuis la base
            plainte = db.query(Plainte).filter(Plainte.plainte_id == plainte_id).first()
            if not plainte:
                raise Exception(f"Plainte {plainte_id} non trouvée en base")
            
            fichier = db.query(FichierPlainte).filter(FichierPlainte.plainte_id == plainte.id).first()
            if not fichier:
                raise Exception(f"Fichier associé à la plainte {plainte_id} non trouvé")
            
            result['steps_completed'].append("Récupération plainte/fichier")
            
            # Étape 2: Extraction du texte
            extraction_result = self.extract_text_from_file(file_path, fichier.type_fichier.value)
            if not extraction_result.get('success', False):
                error_msg = extraction_result.get('error', 'Erreur inconnue lors de l\'extraction')
                raise Exception(f"Échec extraction texte: {error_msg}")
            
            text_content = extraction_result.get('text_content', '')
            if not text_content.strip():
                raise Exception("Aucun texte extrait du fichier - fichier peut-être vide ou corrompu")
            
            result['steps_completed'].append(f"Extraction texte ({len(text_content)} caractères)")
            
            # Étape 3: Analyse IA/LLM
            ai_analysis = self.analyze_complaint_with_llm(text_content, fichier)
            service_detected = ai_analysis.get('service') or ai_analysis.get('service_detecte', 'Inconnu')
            result['steps_completed'].append(f"Analyse IA - Service: {service_detected}")
            
            # Étape 4: Mise à jour de la plainte
            self.update_plainte_from_analysis(db, plainte, text_content, ai_analysis)
            result['steps_completed'].append("Mise à jour plainte en base")
            
            # Étape 5: Mise à jour du fichier avec extraction
            self.update_fichier_from_extraction(db, fichier, extraction_result)
            result['steps_completed'].append("Mise à jour métadonnées fichier en base")
            
            # Étape 6: Sauvegarder les suggestions IA
            self.save_ai_suggestions(db, plainte.id, ai_analysis)
            result['steps_completed'].append("Sauvegarde suggestions IA")
            
            # Étape 7: Déplacer le fichier vers le dossier traités
            new_file_path = self.move_file_to_processed(file_path, plainte_id)
            result['steps_completed'].append(f"Fichier déplacé vers: {new_file_path}")
            
            # Étape 8: Mettre à jour le chemin en base
            self.update_file_path_in_db(db, fichier, new_file_path)
            result['steps_completed'].append("Chemin mis à jour en base")
            
            result['success'] = True
            result['analysis_summary'] = {
                'service': ai_analysis.get('service_detecte'),
                'priorite': ai_analysis.get('priorite_detectee'),
                'sentiment': ai_analysis.get('sentiment_label'),
                'mots_cles': ai_analysis.get('mots_cles', [])[:5],  # Top 5 mots-clés
                'resume': ai_analysis.get('resume_automatique', '')[:100] + '...'
            }
            
            logger.info(f"✅ Traitement réussi pour {plainte_id}")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du traitement de {plainte_id}: {e}")
            result['errors'].append(str(e))
            
            # Déplacer le fichier vers le dossier d'échecs
            try:
                failed_path = self.move_file_to_failed(file_path, plainte_id)
                result['steps_completed'].append(f"Fichier déplacé vers échecs: {failed_path}")
            except Exception as move_error:
                result['errors'].append(f"Impossible de déplacer vers échecs: {move_error}")
            
            db.rollback()
        
        finally:
            db.close()
        
        return result
    
    def extract_text_from_file(self, file_path: str, file_type: str) -> Dict[str, any]:
        """Extraire le texte selon le type de fichier"""
        try:
            if file_type == 'pdf':
                pdf_result = pdf_extractor.process_pdf(file_path)
                
                # Normaliser le résultat pour avoir une structure cohérente
                return {
                    'success': pdf_result.get('extraction_success', False),
                    'text_content': pdf_result.get('text_content', ''),
                    'word_count': pdf_result.get('word_count', 0),
                    'char_count': pdf_result.get('char_count', 0),
                    'num_pages': pdf_result.get('num_pages', 0),
                    'confidence': pdf_result.get('confidence', 0.0),
                    'error': pdf_result.get('error', None)
                }
            else:
                # Pour l'instant, seuls les PDF sont supportés
                # TODO: Ajouter support pour images (OCR), Word, etc.
                return {
                    'success': False,
                    'error': f"Type de fichier {file_type} non supporté pour l'extraction",
                    'text_content': '',
                    'word_count': 0,
                    'char_count': 0
                }
        except Exception as e:
            logger.error(f"Erreur extraction fichier {file_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'text_content': '',
                'word_count': 0,
                'char_count': 0
            }
    
    def update_plainte_from_analysis(self, db: Session, plainte: Plainte, text_content: str, analysis: Dict) -> None:
        """Mettre à jour la plainte avec les résultats de l'analyse IA (nouveau format multi-prompts)"""
        
        logger.info(f"🔄 Mise à jour plainte avec analyse: {analysis.keys()}")
        
        # === NOUVEAU FORMAT MULTI-PROMPTS ===
        
        # Mettre à jour le service (nouveau format direct)
        service_value = analysis.get('service')
        if service_value:
            try:
                # Convertir la valeur string en enum
                plainte.service = ServiceEnum[service_value.upper()]
                logger.info(f"✅ Service mis à jour: {service_value}")
            except (KeyError, AttributeError) as e:
                logger.warning(f"⚠️ Service invalide: {service_value} - {e}")
        
        # Mettre à jour la priorité (nouveau format direct)
        priorite_value = analysis.get('priorite')
        if priorite_value:
            try:
                # Convertir la valeur string en enum
                plainte.priorite = PrioriteEnum[priorite_value.upper()]
                logger.info(f"✅ Priorité mise à jour: {priorite_value}")
            except (KeyError, AttributeError) as e:
                logger.warning(f"⚠️ Priorité invalide: {priorite_value} - {e}")
        
        # Mettre à jour le contenu et le résumé
        plainte.contenu_original = text_content
        plainte.contenu_resume = analysis.get('resume', '')
        
        # Mettre à jour les scores IA (nouveau format avec descriptions textuelles)
        sentiment_value = analysis.get('sentiment', 'Mécontent')
        plainte.score_sentiment = str(sentiment_value)
        logger.info(f"✅ Sentiment mis à jour: {sentiment_value}")
        
        score_urgence = analysis.get('score_urgence', 'Priorité modérée')
        plainte.score_urgence = str(score_urgence)
        logger.info(f"✅ Urgence mise à jour: {score_urgence}")
        
        # Sauvegarder les mots-clés en JSON (nouveau format)
        mots_cles = analysis.get('mots_cles', [])
        if mots_cles and isinstance(mots_cles, list):
            plainte.mots_cles = json.dumps(mots_cles, ensure_ascii=False)
            logger.info(f"✅ Mots-clés mis à jour: {len(mots_cles)} mots")
        
        # === EXTRACTION CONTACT (NOUVEAU FORMAT) ===
        contact_info = analysis.get('contact_info', {})
        
        # Nom du plaignant
        nom = contact_info.get('nom', '').strip() if contact_info.get('nom') else ''
        if nom:
            plainte.nom_plaignant = nom[:100]  # Limiter la longueur
            logger.info(f"✅ Nom plaignant mis à jour: {nom}")
        
        # Email du plaignant  
        email = contact_info.get('email', '').strip() if contact_info.get('email') else ''
        if email:
            plainte.email_plaignant = email[:100]
            logger.info(f"✅ Email plaignant mis à jour: {email}")
        
        # Téléphone du plaignant
        telephone = contact_info.get('telephone', '').strip() if contact_info.get('telephone') else ''
        if telephone:
            plainte.telephone_plaignant = telephone[:20]
            logger.info(f"✅ Téléphone plaignant mis à jour: {telephone}")
        
        # === MISE À JOUR DU TITRE ===
        titre_suggere = analysis.get('titre_suggere', '').strip()
        if titre_suggere and plainte.titre == "En cours d'analyse par l'IA...":
            plainte.titre = titre_suggere[:200]  # Limiter la longueur
            logger.info(f"✅ Titre mis à jour: {titre_suggere}")
        elif plainte.titre == "En cours d'analyse par l'IA...":
            # Générer un titre basé sur les nouvelles données
            service_name = plainte.service.value if plainte.service else 'Service non déterminé'
            
            # Simplifier la description du sentiment pour le titre
            sentiment_court = "négative"
            if plainte.score_sentiment:
                sentiment_text = plainte.score_sentiment.lower()
                if any(word in sentiment_text for word in ["content", "satisfait", "positif"]):
                    sentiment_court = "positive"
                elif "neutre" in sentiment_text:
                    sentiment_court = "neutre"
                else:
                    sentiment_court = "négative"
            
            plainte.titre = f"Plainte {sentiment_court} - {service_name}"
            logger.info(f"✅ Titre généré automatiquement: {plainte.titre}")
        
        # === SUPPORT ANCIEN FORMAT (pour compatibilité) ===
        # Si pas de nouveau format, essayer l'ancien format
        if not analysis.get('service') and analysis.get('service_detecte'):
            try:
                plainte.service = ServiceEnum(analysis['service_detecte'])
                logger.info(f"✅ Service (ancien format): {analysis['service_detecte']}")
            except (KeyError, ValueError):
                pass
        
        if not analysis.get('priorite') and analysis.get('priorite_detectee'):
            try:
                plainte.priorite = PrioriteEnum(analysis['priorite_detectee'])
                logger.info(f"✅ Priorité (ancien format): {analysis['priorite_detectee']}")
            except (KeyError, ValueError):
                pass
        
        # Commit des changements
        db.commit()
        logger.info(f"💾 Plainte {plainte.plainte_id} mise à jour en base de données")
    
    def update_fichier_from_extraction(self, db: Session, fichier: FichierPlainte, extraction: Dict) -> None:
        """Mettre à jour les informations du fichier après extraction"""
        fichier.texte_extrait = extraction.get('text_content', '')
        
        # Marquer comme traité seulement si l'extraction a réussi
        if extraction.get('success', False):
            fichier.est_traite = True
        else:
            fichier.est_traite = False
            
        # Commit des changements
        db.commit()
        logger.info(f"Fichier mis à jour en base - traité: {fichier.est_traite}, texte extrait: {len(fichier.texte_extrait)} caractères")
    
    def update_file_path_in_db(self, db: Session, fichier: FichierPlainte, new_path: str) -> None:
        """Mettre à jour le chemin du fichier dans la base de données"""
        old_path = fichier.chemin_fichier
        
        # Normaliser le nouveau chemin
        normalized_path = new_path.replace("\\", "/")
        
        # Mettre à jour le chemin et marquer comme traité
        fichier.chemin_fichier = normalized_path
        fichier.est_traite = True
        
        # Commit des changements
        db.commit()
        
        logger.info(f"📁 Chemin fichier mis à jour en base:")
        logger.info(f"   Ancien: {old_path}")
        logger.info(f"   Nouveau: {normalized_path}")
    
    def save_ai_suggestions(self, db: Session, plainte_id: int, analysis: Dict) -> None:
        """Sauvegarder les suggestions IA en base (format multi-prompts)"""
        
        # Déterminer le modèle utilisé
        model_name = "Multi-Prompts-LLM-v2.0" if analysis.get('analysis_method') == 'LLM' else "BasicAI-v1.0"
        confidence = analysis.get('confidence', 0.8)
        
        logger.info(f"💾 Sauvegarde suggestions IA pour plainte {plainte_id} avec modèle {model_name}")
        
        # === 1. SUGGESTION DE CLASSIFICATION ===
        service_info = []
        if analysis.get('service'):
            service_info.append(f"Service identifié: {analysis['service']}")
        if analysis.get('priorite'):
            service_info.append(f"Priorité: {analysis['priorite']}")
        if analysis.get('sentiment'):
            service_info.append(f"Sentiment: {analysis['sentiment']}")
        if analysis.get('score_urgence'):
            service_info.append(f"Urgence: {analysis['score_urgence']}")
        
        if service_info:
            classification_suggestion = SuggestionIA(
                plainte_id=plainte_id,
                type_suggestion="classification",
                contenu_suggestion="Classification automatique: " + " | ".join(service_info),
                score_confiance=confidence,
                modele_utilise=model_name
            )
            db.add(classification_suggestion)
            logger.info(f"✅ Suggestion classification ajoutée")
        
        # === 2. SUGGESTION DE CONTACT ===
        contact_info = analysis.get('contact_info', {})
        contact_details = []
        if contact_info.get('nom'):
            contact_details.append(f"Nom: {contact_info['nom']}")
        if contact_info.get('email'):
            contact_details.append(f"Email: {contact_info['email']}")
        if contact_info.get('telephone'):
            contact_details.append(f"Téléphone: {contact_info['telephone']}")
        
        if contact_details:
            contact_suggestion = SuggestionIA(
                plainte_id=plainte_id,
                type_suggestion="contact",
                contenu_suggestion="Informations de contact détectées: " + " | ".join(contact_details),
                score_confiance=confidence,
                modele_utilise=model_name
            )
            db.add(contact_suggestion)
            logger.info(f"✅ Suggestion contact ajoutée")
        
        # === 3. SUGGESTION DE RÉPONSE BASÉE SUR LE RÉSUMÉ ===
        resume = analysis.get('resume', '')
        if resume and len(resume.strip()) > 10:
            response_suggestion = SuggestionIA(
                plainte_id=plainte_id,
                type_suggestion="reponse",
                contenu_suggestion=f"Réponse suggérée basée sur l'analyse: {resume[:500]}...",
                score_confiance=confidence * 0.9,  # Légèrement moins confiant pour les réponses
                modele_utilise=model_name
            )
            db.add(response_suggestion)
            logger.info(f"✅ Suggestion réponse ajoutée")
        
        # === 4. SUGGESTIONS D'ACTIONS SPÉCIFIQUES ===
        suggestions_reponse = analysis.get('suggestions_reponse', [])
        if isinstance(suggestions_reponse, list):
            for i, suggestion_text in enumerate(suggestions_reponse[:5]):  # Limiter à 5 suggestions
                if suggestion_text and len(suggestion_text.strip()) > 5:
                    action_suggestion = SuggestionIA(
                        plainte_id=plainte_id,
                        type_suggestion="action",
                        contenu_suggestion=f"Action recommandée: {suggestion_text}",
                        score_confiance=confidence * 0.8,
                        modele_utilise=model_name
                    )
                    db.add(action_suggestion)
            if suggestions_reponse:
                logger.info(f"✅ {len(suggestions_reponse)} suggestions d'actions ajoutées")
        
        # === 5. SUGGESTION DE MOTS-CLÉS ===
        mots_cles = analysis.get('mots_cles', [])
        if isinstance(mots_cles, list) and mots_cles:
            mots_cles_text = ", ".join(mots_cles[:10])  # Limiter à 10 mots-clés
            keywords_suggestion = SuggestionIA(
                plainte_id=plainte_id,
                type_suggestion="mots_cles",
                contenu_suggestion=f"Mots-clés identifiés: {mots_cles_text}",
                score_confiance=confidence,
                modele_utilise=model_name
            )
            db.add(keywords_suggestion)
            logger.info(f"✅ Suggestion mots-clés ajoutée: {len(mots_cles)} mots")
        
        # === 6. SUGGESTION DE PRIORITÉ BASÉE SUR L'URGENCE ===
        if analysis.get('score_urgence') and analysis.get('sentiment'):
            priority_analysis = f"Analyse: {analysis['sentiment']} + {analysis['score_urgence']}"
            
            # Recommandations basées sur l'urgence et le sentiment
            if "Urgence vitale" in str(analysis.get('score_urgence', '')):
                action_text = "PRIORITÉ MAXIMALE: Intervention immédiate requise"
            elif "Urgence élevée" in str(analysis.get('score_urgence', '')):
                action_text = "PRIORITÉ HAUTE: Traitement dans les 24h"
            elif "Très en colère" in str(analysis.get('sentiment', '')):
                action_text = "ATTENTION: Patient très mécontent, contact prioritaire recommandé"
            else:
                action_text = "Suivi standard selon protocole habituel"
            
            priority_suggestion = SuggestionIA(
                plainte_id=plainte_id,
                type_suggestion="priorite",
                contenu_suggestion=f"{priority_analysis} → {action_text}",
                score_confiance=confidence,
                modele_utilise=model_name
            )
            db.add(priority_suggestion)
            logger.info(f"✅ Suggestion priorité ajoutée")
        
        # Sauvegarder toutes les suggestions
        try:
            db.commit()
            
            # Compter les suggestions ajoutées
            total_suggestions = db.query(SuggestionIA).filter(SuggestionIA.plainte_id == plainte_id).count()
            logger.info(f"🎉 {total_suggestions} suggestions IA sauvegardées pour plainte {plainte_id}")
            
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde suggestions: {e}")
            db.rollback()
            raise
    
    def move_file_to_processed(self, source_path: str, plainte_id: str) -> str:
        """Déplacer le fichier vers le dossier des fichiers traités"""
        filename = os.path.basename(source_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_filename = f"{timestamp}_{filename}"
        destination_path = os.path.join(self.processed_dir, new_filename)
        
        # Créer le dossier de destination si nécessaire
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        
        # Déplacer le fichier
        shutil.move(source_path, destination_path)
        
        # Normaliser le chemin pour utiliser des forward slashes
        destination_path = destination_path.replace("\\", "/")
        
        logger.info(f"📁 Fichier déplacé: {source_path} -> {destination_path}")
        return destination_path
    
    def move_file_to_failed(self, source_path: str, plainte_id: str) -> str:
        """Déplacer le fichier vers le dossier des échecs"""
        filename = os.path.basename(source_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_filename = f"FAILED_{timestamp}_{filename}"
        destination_path = os.path.join(self.failed_dir, new_filename)
        
        # Créer le dossier de destination si nécessaire
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        
        # Déplacer le fichier
        shutil.move(source_path, destination_path)
        
        # Normaliser le chemin pour utiliser des forward slashes
        destination_path = destination_path.replace("\\", "/")
        
        logger.warning(f"⚠️ Fichier déplacé vers échecs: {source_path} -> {destination_path}")
        return destination_path
    
    def get_files_to_process(self) -> list:
        """Obtenir la liste des fichiers à traiter"""
        files_to_process = []
        
        if not os.path.exists(settings.DATA_PLAINTES_DIR):
            return files_to_process
        
        # Lister tous les fichiers dans le dossier data/plaintes
        for filename in os.listdir(settings.DATA_PLAINTES_DIR):
            file_path = os.path.join(settings.DATA_PLAINTES_DIR, filename)
            
            if os.path.isfile(file_path):
                # Extraire l'ID de plainte du nom de fichier
                if filename.startswith("PL-"):
                    plainte_id = filename.split("_")[0]  # PL-2025-XXXXXXXX
                    files_to_process.append({
                        'file_path': file_path,
                        'filename': filename,
                        'plainte_id': plainte_id
                    })
        
        return files_to_process
    
    def process_all_pending_files(self) -> Dict[str, any]:
        """Traiter tous les fichiers en attente"""
        logger.info("🚀 Début du traitement de tous les fichiers en attente")
        
        files_to_process = self.get_files_to_process()
        
        results = {
            'total_files': len(files_to_process),
            'processed_successfully': 0,
            'failed': 0,
            'details': [],
            'timestamp': datetime.now().isoformat()
        }
        
        for file_info in files_to_process:
            result = self.process_file(file_info['file_path'], file_info['plainte_id'])
            results['details'].append(result)
            
            if result['success']:
                results['processed_successfully'] += 1
            else:
                results['failed'] += 1
        
        logger.info(f"✅ Traitement terminé: {results['processed_successfully']}/{results['total_files']} réussis")
        
        return results

    def process_service_files(self, service: ServiceEnum) -> Dict[str, any]:
        """Traiter les fichiers d'un service spécifique"""
        logger.info(f"🚀 Début du traitement des fichiers pour le service: {service.value}")
        
        # Récupérer les plaintes du service spécifique qui sont en attente
        db = SessionLocal()
        try:
            plaintes = db.query(Plainte).filter(
                Plainte.service == service,
                Plainte.status.in_([StatusEnum.EN_ATTENTE, StatusEnum.EN_COURS])
            ).all()
            
            if not plaintes:
                logger.info(f"ℹ️ Aucune plainte en attente pour le service {service.value}")
                return {
                    'total_files': 0,
                    'processed_successfully': 0,
                    'failed': 0,
                    'details': [],
                    'timestamp': datetime.now().isoformat()
                }
            
            results = {
                'total_files': len(plaintes),
                'processed_successfully': 0,
                'failed': 0,
                'details': [],
                'timestamp': datetime.now().isoformat()
            }
            
            for plainte in plaintes:
                # Chercher le fichier associé à cette plainte
                fichier = db.query(FichierPlainte).filter(FichierPlainte.plainte_id == plainte.id).first()
                
                if fichier and os.path.exists(fichier.chemin_fichier):
                    result = self.process_file(fichier.chemin_fichier, plainte.plainte_id)
                    results['details'].append(result)
                    
                    if result['success']:
                        results['processed_successfully'] += 1
                    else:
                        results['failed'] += 1
                else:
                    logger.warning(f"⚠️ Fichier non trouvé pour la plainte {plainte.plainte_id}")
                    results['failed'] += 1
                    results['details'].append({
                        'plainte_id': plainte.plainte_id,
                        'success': False,
                        'error': 'Fichier non trouvé'
                    })
            
            logger.info(f"✅ Traitement du service {service.value} terminé: {results['processed_successfully']}/{results['total_files']} réussis")
            
            return results
            
        finally:
            db.close()

# Instance globale
file_processor = FileProcessor() 