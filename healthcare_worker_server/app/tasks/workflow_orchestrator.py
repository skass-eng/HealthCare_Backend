"""
Orchestrateur principal pour le workflow de traitement des plaintes
Coordonne toutes les étapes : parsing, analyse, génération PDF
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json
import os

logger = logging.getLogger(__name__)

class ComplaintWorkflowOrchestrator:
    """
    Orchestrateur principal pour le workflow complet de traitement des plaintes
    """
    
    def __init__(self, document_parser, analysis_service, pdf_generator, llm_provider=None):
        """
        Initialise l'orchestrateur avec tous les services nécessaires
        
        Args:
            document_parser: Service de parsing de documents
            analysis_service: Service d'analyse IA
            pdf_generator: Service de génération PDF
            llm_provider: Provider LLM
        """
        self.document_parser = document_parser
        self.analysis_service = analysis_service
        self.pdf_generator = pdf_generator
        self.llm_provider = llm_provider
    
    def process_complaint_complete(self, plainte_data: Dict[str, Any], 
                                 document_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Traite une plainte de manière complète selon le workflow défini
        
        Workflow:
        1. Parsing du document (si présent)
        2. Analyse complète (sentiment, résumé, contacts)
        3. Génération de la réponse juridique
        4. Compilation et génération du PDF final
        
        Args:
            plainte_data: Données de la plainte
            document_path: Chemin vers le document à parser (optionnel)
            
        Returns:
            Dict avec tous les résultats du traitement
        """
        logger.info(f"🚀 Démarrage du traitement complet - Plainte ID: {plainte_data.get('id', 'N/A')}")
        
        workflow_result = {
            "plainte_id": plainte_data.get('id'),
            "start_time": datetime.now().isoformat(),
            "steps_completed": [],
            "steps_failed": [],
            "extracted_text": None,
            "analysis_results": {},
            "legal_response": None,
            "pdf_report": None,
            "success": False,
            "errors": []
        }
        
        try:
            # ÉTAPE 1: Parsing du document (conditionnel)
            complaint_text = self._step_1_document_parsing(
                plainte_data, document_path, workflow_result
            )
            
            # ÉTAPE 2: Analyse complète de la plainte
            analysis_results = self._step_2_complete_analysis(
                complaint_text, workflow_result
            )
            
            # ÉTAPE 3: Génération de la réponse juridique
            legal_response = self._step_3_legal_response(
                complaint_text, analysis_results, workflow_result
            )
            
            # ÉTAPE 4: Compilation et génération du PDF
            pdf_result = self._step_4_pdf_generation(
                plainte_data, analysis_results, legal_response, workflow_result
            )
            
            # Finalisation
            workflow_result["end_time"] = datetime.now().isoformat()
            workflow_result["success"] = len(workflow_result["steps_failed"]) == 0
            
            logger.info(f"✅ Traitement complet terminé - Plainte ID: {plainte_data.get('id', 'N/A')}")
            return workflow_result
            
        except Exception as e:
            logger.error(f"❌ Erreur critique dans le workflow: {str(e)}")
            workflow_result["errors"].append(f"Erreur critique: {str(e)}")
            workflow_result["end_time"] = datetime.now().isoformat()
            workflow_result["success"] = False
            return workflow_result
    
    def _step_1_document_parsing(self, plainte_data: Dict[str, Any], 
                               document_path: Optional[str], 
                               workflow_result: Dict[str, Any]) -> str:
        """
        ÉTAPE 1: Parsing du document (conditionnel)
        """
        logger.info("📄 ÉTAPE 1: Parsing du document")
        
        # Utiliser la description de la plainte comme texte de base
        base_text = plainte_data.get('description_probleme', '')
        
        # Si un document est fourni, tenter de l'analyser
        if document_path and os.path.exists(document_path):
            logger.info(f"Document fourni: {document_path}")
            
            if self.document_parser.is_document_parseable(document_path):
                try:
                    parsing_result = self.document_parser.extract_text_from_document(document_path)
                    
                    if parsing_result.get('success', False):
                        extracted_text = parsing_result.get('text', '')
                        if extracted_text.strip():
                            # Combiner le texte extrait avec la description
                            combined_text = f"{base_text}\n\n--- Texte extrait du document ---\n{extracted_text}"
                            workflow_result["extracted_text"] = {
                                "source": "document_parsing",
                                "original_text": base_text,
                                "extracted_text": extracted_text,
                                "combined_text": combined_text,
                                "metadata": parsing_result.get('metadata', {})
                            }
                            workflow_result["steps_completed"].append("document_parsing")
                            logger.info("✅ Parsing du document réussi")
                            return combined_text
                        else:
                            logger.warning("Document vide après parsing")
                    else:
                        error_msg = f"Échec du parsing: {parsing_result.get('error', 'Erreur inconnue')}"
                        logger.error(error_msg)
                        workflow_result["errors"].append(error_msg)
                        workflow_result["steps_failed"].append("document_parsing")
                        
                except Exception as e:
                    error_msg = f"Erreur lors du parsing: {str(e)}"
                    logger.error(error_msg)
                    workflow_result["errors"].append(error_msg)
                    workflow_result["steps_failed"].append("document_parsing")
            else:
                logger.info("Document non supporté pour le parsing")
                workflow_result["steps_completed"].append("document_parsing_skipped")
        else:
            logger.info("Aucun document à parser - utilisation de la description manuelle")
            workflow_result["steps_completed"].append("document_parsing_skipped")
        
        # Retourner le texte de base si pas de document ou échec de parsing
        workflow_result["extracted_text"] = {
            "source": "manual_description",
            "text": base_text
        }
        return base_text
    
    def _step_2_complete_analysis(self, complaint_text: str, 
                                workflow_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        ÉTAPE 2: Analyse complète de la plainte (3 prompts distincts)
        """
        logger.info("🔍 ÉTAPE 2: Analyse complète de la plainte")
        
        try:
            # Effectuer l'analyse complète (sentiment, résumé, contacts)
            analysis_results = self.analysis_service.perform_complete_analysis(complaint_text)
            
            # Convertir les résultats en format sérialisable
            serializable_results = {}
            for key, result in analysis_results.items():
                serializable_results[key] = {
                    "success": result.success,
                    "content": result.content,
                    "confidence": result.confidence,
                    "metadata": result.metadata,
                    "error": result.error
                }
            
            workflow_result["analysis_results"] = serializable_results
            workflow_result["steps_completed"].append("complete_analysis")
            logger.info("✅ Analyse complète réussie")
            return serializable_results
            
        except Exception as e:
            error_msg = f"Erreur lors de l'analyse complète: {str(e)}"
            logger.error(error_msg)
            workflow_result["errors"].append(error_msg)
            workflow_result["steps_failed"].append("complete_analysis")
            return {}
    
    def _step_3_legal_response(self, complaint_text: str, 
                             analysis_results: Dict[str, Any],
                             workflow_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        ÉTAPE 3: Génération de la réponse juridique
        """
        logger.info("⚖️ ÉTAPE 3: Génération de la réponse juridique")
        
        try:
            # Préparer le résumé d'analyse pour la réponse juridique
            analysis_summary = self._prepare_analysis_summary(analysis_results)
            
            # Générer la réponse juridique
            legal_result = self.analysis_service.generate_legal_response(
                complaint_text, analysis_summary
            )
            
            # Convertir en format sérialisable
            legal_response = {
                "success": legal_result.success,
                "content": legal_result.content,
                "confidence": legal_result.confidence,
                "metadata": legal_result.metadata,
                "error": legal_result.error
            }
            
            workflow_result["legal_response"] = legal_response
            workflow_result["steps_completed"].append("legal_response")
            logger.info("✅ Réponse juridique générée")
            return legal_response
            
        except Exception as e:
            error_msg = f"Erreur lors de la génération de la réponse juridique: {str(e)}"
            logger.error(error_msg)
            workflow_result["errors"].append(error_msg)
            workflow_result["steps_failed"].append("legal_response")
            return None
    
    def _step_4_pdf_generation(self, plainte_data: Dict[str, Any],
                             analysis_results: Dict[str, Any],
                             legal_response: Optional[Dict[str, Any]],
                             workflow_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        ÉTAPE 4: Génération du rapport PDF final
        """
        logger.info("📋 ÉTAPE 4: Génération du rapport PDF")
        
        try:
            # Préparer le chemin de sortie
            plainte_id = plainte_data.get('id', 'unknown')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f"rapport_plainte_{plainte_id}_{timestamp}.pdf"
            output_dir = os.path.join(os.getcwd(), 'data', 'pdf_reports')
            output_path = os.path.join(output_dir, output_filename)
            
            # Compiler tous les résultats pour le PDF
            all_results = analysis_results.copy()
            if legal_response:
                all_results["legal_response"] = legal_response
            
            # Générer le PDF
            pdf_result = self.pdf_generator.generate_complaint_report(
                plainte_data, all_results, output_path
            )
            
            workflow_result["pdf_report"] = pdf_result
            
            if pdf_result.get("success", False):
                workflow_result["steps_completed"].append("pdf_generation")
                logger.info(f"✅ Rapport PDF généré: {output_path}")
            else:
                workflow_result["steps_failed"].append("pdf_generation")
                workflow_result["errors"].append(f"Échec génération PDF: {pdf_result.get('error', 'Erreur inconnue')}")
            
            return pdf_result
            
        except Exception as e:
            error_msg = f"Erreur lors de la génération PDF: {str(e)}"
            logger.error(error_msg)
            workflow_result["errors"].append(error_msg)
            workflow_result["steps_failed"].append("pdf_generation")
            return None
    
    def _prepare_analysis_summary(self, analysis_results: Dict[str, Any]) -> str:
        """Prépare un résumé des analyses pour la réponse juridique"""
        summary_parts = []
        
        # Résumé principal
        if "summary" in analysis_results and analysis_results["summary"].get("success"):
            try:
                summary_content = json.loads(analysis_results["summary"]["content"])
                summary_parts.append(f"Résumé: {summary_content.get('resume_executif', 'N/A')}")
                summary_parts.append(f"Nature du problème: {summary_content.get('nature_probleme', 'N/A')}")
            except json.JSONDecodeError:
                summary_parts.append("Résumé disponible en format texte")
        
        # Sentiment
        if "sentiment" in analysis_results and analysis_results["sentiment"].get("success"):
            try:
                sentiment_content = json.loads(analysis_results["sentiment"]["content"])
                summary_parts.append(f"Sentiment: {sentiment_content.get('sentiment_principal', 'N/A')} (intensité: {sentiment_content.get('intensite_emotionnelle', 'N/A')})")
            except json.JSONDecodeError:
                summary_parts.append("Analyse de sentiment disponible")
        
        # Contacts
        if "contacts" in analysis_results and analysis_results["contacts"].get("success"):
            summary_parts.append("Contacts identifiés dans la plainte")
        
        return " | ".join(summary_parts) if summary_parts else "Aucune analyse disponible"
    
    def get_workflow_status(self, workflow_result: Dict[str, Any]) -> Dict[str, Any]:
        """Retourne un résumé du statut du workflow"""
        total_steps = 4  # document_parsing, complete_analysis, legal_response, pdf_generation
        completed_steps = len(workflow_result.get("steps_completed", []))
        failed_steps = len(workflow_result.get("steps_failed", []))
        
        return {
            "overall_success": workflow_result.get("success", False),
            "progress": f"{completed_steps}/{total_steps}",
            "completion_rate": (completed_steps / total_steps) * 100,
            "steps_completed": workflow_result.get("steps_completed", []),
            "steps_failed": workflow_result.get("steps_failed", []),
            "error_count": len(workflow_result.get("errors", [])),
            "has_pdf": workflow_result.get("pdf_report", {}).get("success", False),
            "processing_time": self._calculate_processing_time(workflow_result)
        }
    
    def _calculate_processing_time(self, workflow_result: Dict[str, Any]) -> Optional[str]:
        """Calcule le temps de traitement total"""
        start_time = workflow_result.get("start_time")
        end_time = workflow_result.get("end_time")
        
        if start_time and end_time:
            try:
                start = datetime.fromisoformat(start_time)
                end = datetime.fromisoformat(end_time)
                duration = end - start
                return str(duration.total_seconds())
            except:
                return None
        return None
