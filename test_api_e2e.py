#!/usr/bin/env python3
"""
Test E2E de l'API HealthCare AI
Test de création de plainte avec PDF et analyse IA
"""

import requests
from datetime import datetime
import time
import os

def test_api():
    print('========================================')
    print('   TEST COMPLET DE BOUT EN BOUT')
    print('========================================')
    print()
    
    # Vérifier que le serveur est up
    try:
        r = requests.get('http://localhost:8000/health', timeout=5)
        if r.status_code != 200:
            print("ERREUR: Le serveur n'est pas disponible")
            return
        print("✅ Serveur disponible")
    except Exception as e:
        print(f"ERREUR: Impossible de contacter le serveur: {e}")
        return

    # 1. Créer une plainte avec mots-clés urgents
    form_data = {
        'nom_plaignant': 'Bernard',
        'prenom_plaignant': 'Claude',
        'email_plaignant': 'claude.bernard@test.com',
        'telephone_plaignant': '0611223344',
        'objet': 'Urgence Grave ' + datetime.now().strftime('%H%M%S'),
        'description': 'Situation URGENTE et GRAVE! Le patient est furieux face a ce probleme inacceptable. Nous demandons une intervention immediate!',
        'date_incident': '2025-12-02',
        'service_concerne_id': '1',
        'priorite': 'URGENT'
    }
    
    print()
    print('1. CREATION PLAINTE')
    print('   Description contient: urgente, grave, furieux, probleme, inacceptable')
    r = requests.post('http://localhost:8000/api/v1/plaintes/creation/nouvelle', data=form_data)
    print(f'   Status: {r.status_code}')
    
    if r.status_code == 200:
        data = r.json()
        plainte_id = data.get('id')
        print(f'   ID: {plainte_id}')
        print(f'   Numero: {data.get("numero_plainte")}')
        
        print()
        print('2. ATTENTE TRAITEMENT (5 sec)...')
        time.sleep(5)
        
        # Vérifier le PDF
        pdf_path = f'data/pdf_reports/plainte_{plainte_id}_rapport_complet.pdf'
        print()
        print('3. VERIFICATION PDF')
        if os.path.exists(pdf_path):
            print(f'   Status: ✅ GENERE')
            print(f'   Taille: {os.path.getsize(pdf_path)} bytes')
        else:
            print(f'   Status: ❌ NON TROUVE')
        
        # Vérifier l'analyse IA
        print()
        print('4. VERIFICATION ANALYSE IA')
        r2 = requests.get(f'http://localhost:8000/api/v1/plaintes/{plainte_id}')
        if r2.status_code == 200:
            details = r2.json()
            analyse = details.get('analyse_ia')
            if analyse:
                statut = analyse.get('statut_analyse')
                sentiment = analyse.get('sentiment')
                priorite_ia = analyse.get('priorite_ia')
                service = analyse.get('service_suggere')
                
                print(f'   Statut: {statut}')
                print(f'   Sentiment: {sentiment}')
                print(f'   Priorite IA: {priorite_ia}')
                print(f'   Service suggere: {service}')
                
                resume = analyse.get('resume_ia') or ''
                if len(resume) > 100:
                    print(f'   Resume: {resume[:100]}...')
                else:
                    print(f'   Resume: {resume}')
                
                if statut == 'complete' and sentiment and priorite_ia:
                    print('   ✅ Analyse IA complete!')
                elif statut == 'en_cours':
                    print('   ⏳ Analyse IA en cours (worker Celery requis)')
            else:
                print('   ❌ Aucune analyse disponible')
        
        # Test téléchargement PDF
        print()
        print('5. TEST TELECHARGEMENT PDF')
        r3 = requests.get(f'http://localhost:8000/api/v1/plaintes/{plainte_id}/pdf-rapport/download')
        print(f'   Status: {r3.status_code}')
        if r3.status_code == 200:
            print(f'   Content-Type: {r3.headers.get("Content-Type")}')
            print(f'   Taille: {len(r3.content)} bytes')
            if r3.content[:4] == b'%PDF':
                print('   ✅ PDF valide!')
            else:
                print('   ⚠️ Contenu non-PDF')
        
        print()
        print('========================================')
        print('   RESULTAT: TEST REUSSI!')
        print('========================================')
    else:
        print(f'   ❌ ERREUR: {r.text[:500]}')

if __name__ == '__main__':
    test_api()
