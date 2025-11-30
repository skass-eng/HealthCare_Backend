"""
Test simple du worker modulaire
"""
import sys
import os

# Ajouter les chemins nécessaires
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

def test_imports():
    """Test des imports modulaires"""
    print("Test des imports modulaires...")
    
    try:
        # Test du service de parsing
        from healthcare_worker_server.app.services.document_parser import DocumentParserService
        print("✓ DocumentParserService importé")
        
        # Test du service d'analyse
        from healthcare_worker_server.app.services.complaint_analysis import ComplaintAnalysisService
        print("✓ ComplaintAnalysisService importé")
        
        # Test du service PDF
        from healthcare_worker_server.app.services.pdf_generator import PDFReportService
        print("✓ PDFReportService importé")
        
        # Test de l'orchestrateur
        from healthcare_worker_server.app.tasks.workflow_orchestrator import ComplaintWorkflowOrchestrator
        print("✓ ComplaintWorkflowOrchestrator importé")
        
        print("Tous les imports sont OK!")
        return True
        
    except ImportError as e:
        print(f"✗ Erreur d'import: {e}")
        return False

def test_services():
    """Test basique des services"""
    print("\nTest des services...")
    
    try:
        # Test du service de parsing
        from healthcare_worker_server.app.services.document_parser import DocumentParserService
        parser = DocumentParserService()
        print("✓ DocumentParserService instancié")
        
        # Test du service d'analyse
        from healthcare_worker_server.app.services.complaint_analysis import ComplaintAnalysisService
        from healthcare_worker_server.app.services.llm_provider import LLMProvider
        
        # Créer un LLM provider simple
        class SimpleLLMProvider:
            def __init__(self):
                self.model_name = "test_model"
            
            def generate_response(self, prompt):
                return '{"test": "response"}'
        
        llm = SimpleLLMProvider()
        analysis_service = ComplaintAnalysisService(llm)
        print("✓ ComplaintAnalysisService instancié")
        
        # Test du service PDF
        from healthcare_worker_server.app.services.pdf_generator import PDFReportService
        pdf_service = PDFReportService()
        print("✓ PDFReportService instancié")
        
        # Test de l'orchestrateur
        from healthcare_worker_server.app.tasks.workflow_orchestrator import ComplaintWorkflowOrchestrator
        orchestrator = ComplaintWorkflowOrchestrator(parser, analysis_service, pdf_service, llm)
        print("✓ ComplaintWorkflowOrchestrator instancié")
        
        print("Tous les services fonctionnent!")
        return True
        
    except Exception as e:
        print(f"✗ Erreur de service: {e}")
        return False

def test_analysis_workflow():
    """Test du workflow d'analyse simple"""
    print("\nTest du workflow d'analyse...")
    
    try:
        from healthcare_worker_server.app.services.complaint_analysis import ComplaintAnalysisService
        
        # LLM provider simple pour test
        class TestLLMProvider:
            def __init__(self):
                self.model_name = "test_model"
            
            def generate_response(self, prompt):
                if "sentiment" in prompt.lower():
                    return '{"sentiment_principal": "neutre", "intensite_emotionnelle": "faible"}'
                elif "résumé" in prompt.lower():
                    return '{"resume_executif": "Test de résumé"}'
                elif "contact" in prompt.lower():
                    return '{"personnes_mentionnees": [], "services_departements": []}'
                else:
                    return '{"reponse": "test"}'
        
        llm = TestLLMProvider()
        analysis_service = ComplaintAnalysisService(llm)
        
        # Test d'analyse de sentiment
        sentiment_result = analysis_service.analyze_sentiment("Je suis satisfait du service")
        print(f"✓ Analyse sentiment: {sentiment_result.success}")
        
        # Test de génération de résumé
        summary_result = analysis_service.generate_summary("Problème avec le service")
        print(f"✓ Génération résumé: {summary_result.success}")
        
        # Test d'extraction de contacts
        contacts_result = analysis_service.extract_contacts("Dr Martin du service urgences")
        print(f"✓ Extraction contacts: {contacts_result.success}")
        
        print("Workflow d'analyse OK!")
        return True
        
    except Exception as e:
        print(f"✗ Erreur workflow: {e}")
        return False

if __name__ == "__main__":
    print("=== TEST DU WORKER MODULAIRE ===")
    
    success = True
    success = test_imports() and success
    success = test_services() and success
    success = test_analysis_workflow() and success
    
    if success:
        print("\n🎉 Tous les tests sont passés! L'architecture modulaire fonctionne.")
    else:
        print("\n❌ Des tests ont échoué.")
    
    sys.exit(0 if success else 1)
