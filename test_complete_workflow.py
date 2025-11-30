"""
Test complet du workflow modulaire avec données réelles
"""
import sys
import os
from datetime import datetime

# Ajouter les chemins nécessaires
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

def test_complete_workflow():
    """Test du workflow complet avec des données réelles"""
    print("=== TEST WORKFLOW COMPLET ===")
    
    try:
        # Import des services
        from healthcare_worker_server.app.services.document_parser import DocumentParserService
        from healthcare_worker_server.app.services.complaint_analysis import ComplaintAnalysisService
        from healthcare_worker_server.app.services.pdf_generator import PDFReportService
        from healthcare_worker_server.app.tasks.workflow_orchestrator import ComplaintWorkflowOrchestrator
        
        # LLM provider de test avec réponses réalistes
        class RealisticLLMProvider:
            def __init__(self):
                self.model_name = "test_realistic_model"
            
            def generate_response(self, prompt):
                if "sentiment" in prompt.lower():
                    return '''{
    "sentiment_principal": "négatif",
    "intensite_emotionnelle": "modérée",
    "score_sentiment": -0.4,
    "mots_cles_emotionnels": ["insatisfait", "problème", "déçu"],
    "recommandations_reponse": "Adopter un ton empathique et proposer des solutions concrètes"
}'''
                elif "résumé" in prompt.lower() or "summary" in prompt.lower():
                    return '''{
    "resume_executif": "Patient exprime son mécontentement concernant l'attente prolongée aux urgences et le manque d'information durant son séjour.",
    "faits_principaux": ["Attente excessive", "Manque d'information", "Personnel peu disponible"],
    "services_concernes": ["Urgences", "Accueil"],
    "nature_probleme": "Problème d'organisation et de communication",
    "demande_plaignant": "Amélioration des délais et de la communication",
    "date_incident": "2025-01-10",
    "gravite_estimee": "modérée"
}'''
                elif "contact" in prompt.lower():
                    return '''{
    "personnes_mentionnees": [
        {
            "nom": "Dr Durand",
            "fonction": "Médecin urgentiste",
            "service": "Urgences",
            "contexte": "Médecin qui a pris en charge le patient"
        }
    ],
    "services_departements": [
        {
            "nom": "Service des Urgences",
            "contexte": "Service principal concerné par la plainte"
        },
        {
            "nom": "Accueil",
            "contexte": "Premier point de contact mentionné"
        }
    ],
    "coordonnees_trouvees": [],
    "interlocuteurs_cles": ["Dr Durand", "Responsable Urgences"]
}'''
                elif "juridique" in prompt.lower() or "legal" in prompt.lower():
                    return '''{
    "reponse_officielle": "Madame, Monsieur,\\n\\nNous avons pris connaissance de votre signalement concernant votre passage dans notre service des urgences le 10 janvier 2025 et tenons à vous remercier de nous avoir fait part de vos préoccupations.\\n\\nNotre établissement accorde une importance primordiale à la qualité des soins et à l'accueil de nos patients. Une enquête interne a été diligentée afin d'examiner les éléments que vous avez portés à notre attention, notamment concernant les délais d'attente et la communication.\\n\\nNous mettons tout en œuvre pour assurer l'amélioration continue de nos prestations et avons pris les mesures nécessaires pour éviter qu'une telle situation ne se reproduise.\\n\\nNous restons à votre disposition pour tout complément d'information et vous prions d'agréer nos salutations distinguées.\\n\\nLe Responsable Qualité",
    "points_cles": ["Accusé de réception", "Enquête interne", "Engagement amélioration", "Mesures prises"],
    "actions_proposees": ["Révision des procédures d'accueil", "Formation du personnel", "Amélioration de la communication"],
    "engagement_suivi": "Suivi régulier des améliorations et communication des résultats",
    "tone_juridique": "Professionnel, empathique, sans admission de responsabilité directe",
    "recommandations_internes": ["Révision des flux patients", "Formation communication", "Optimisation planning"]
}'''
                else:
                    return "Analyse effectuée avec succès."
        
        # Initialiser les services
        document_parser = DocumentParserService()
        llm_provider = RealisticLLMProvider()
        analysis_service = ComplaintAnalysisService(llm_provider)
        pdf_generator = PDFReportService()
        
        # Créer l'orchestrateur
        orchestrator = ComplaintWorkflowOrchestrator(
            document_parser=document_parser,
            analysis_service=analysis_service,
            pdf_generator=pdf_generator,
            llm_provider=llm_provider
        )
        
        # Données de plainte réalistes
        plainte_data = {
            "id": 999,
            "nom_plaignant": "Martin",
            "prenom_plaignant": "Jean",
            "telephone_plaignant": "0123456789",
            "email_plaignant": "jean.martin@email.com",
            "adresse_plaignant": "123 Rue de la Santé, 75001 Paris",
            "description_probleme": "J'ai été très déçu de mon passage aux urgences le 10 janvier. J'ai attendu plus de 4 heures sans aucune information. Le personnel semblait débordé et peu disponible. Le Dr Durand m'a finalement pris en charge mais j'aurais aimé être mieux informé durant l'attente. Je demande une amélioration de l'organisation du service.",
            "service_concerne": "Urgences",
            "date_creation": datetime.now().isoformat(),
            "statut": "NOUVELLE",
            "gravite_percue": "MOYENNE",
            "suivi_souhaite": True
        }
        
        print(f"Plainte de test: {plainte_data['nom_plaignant']} {plainte_data['prenom_plaignant']}")
        print(f"Service concerné: {plainte_data['service_concerne']}")
        print(f"Description: {plainte_data['description_probleme'][:100]}...")
        
        # Exécuter le workflow complet
        print("\n🚀 Exécution du workflow complet...")
        workflow_result = orchestrator.process_complaint_complete(plainte_data)
        
        # Analyser les résultats
        print("\n📊 RÉSULTATS:")
        print(f"✓ Succès global: {workflow_result['success']}")
        print(f"✓ Étapes complétées: {len(workflow_result['steps_completed'])}")
        print(f"✓ Étapes échouées: {len(workflow_result['steps_failed'])}")
        print(f"✓ Erreurs: {len(workflow_result['errors'])}")
        
        # Détail des étapes
        print("\n📋 ÉTAPES COMPLÉTÉES:")
        for step in workflow_result['steps_completed']:
            print(f"  ✓ {step}")
        
        if workflow_result['steps_failed']:
            print("\n❌ ÉTAPES ÉCHOUÉES:")
            for step in workflow_result['steps_failed']:
                print(f"  ✗ {step}")
        
        if workflow_result['errors']:
            print("\n🔍 ERREURS:")
            for error in workflow_result['errors']:
                print(f"  • {error}")
        
        # Vérifier les résultats d'analyse
        print("\n🔍 ANALYSES GÉNÉRÉES:")
        analysis_results = workflow_result.get('analysis_results', {})
        for analysis_type, result in analysis_results.items():
            print(f"  ✓ {analysis_type}: {'✓' if result.get('success', False) else '✗'}")
        
        # Vérifier la réponse juridique
        legal_response = workflow_result.get('legal_response')
        if legal_response:
            print(f"  ✓ Réponse juridique: {'✓' if legal_response.get('success', False) else '✗'}")
        
        # Vérifier le PDF
        pdf_report = workflow_result.get('pdf_report')
        if pdf_report:
            print(f"  ✓ Rapport PDF: {'✓' if pdf_report.get('success', False) else '✗'}")
            if pdf_report.get('success', False):
                print(f"    📄 Fichier: {pdf_report.get('file_path', 'N/A')}")
        
        # Statut final
        status = orchestrator.get_workflow_status(workflow_result)
        print(f"\n📈 STATUT FINAL:")
        print(f"  • Taux de réussite: {status['completion_rate']:.1f}%")
        print(f"  • Progression: {status['progress']}")
        print(f"  • PDF généré: {'Oui' if status['has_pdf'] else 'Non'}")
        
        return workflow_result['success']
        
    except Exception as e:
        print(f"❌ Erreur durant le test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_complete_workflow()
    
    if success:
        print("\n🎉 TEST COMPLET RÉUSSI! L'architecture modulaire est opérationnelle.")
    else:
        print("\n❌ Le test a échoué.")
    
    sys.exit(0 if success else 1)
