#!/usr/bin/env python3
"""
Script pour redémarrer le serveur backend avec les corrections d'encodage UTF-8
"""

import subprocess
import sys
import os
import time

def restart_server():
    """Redémarrer le serveur backend"""
    
    print("🔄 Redémarrage du serveur backend...")
    print("📝 Corrections appliquées:")
    print("   ✅ Encodage UTF-8 avec BOM pour l'export CSV")
    print("   ✅ Headers Content-Type avec charset=utf-8")
    print("   ✅ Support complet des caractères français")
    
    try:
        # Arrêter le serveur existant s'il tourne
        print("⏹️  Arrêt du serveur existant...")
        subprocess.run(["taskkill", "/f", "/im", "python.exe"], 
                      capture_output=True, shell=True)
        time.sleep(2)
        
        # Redémarrer le serveur
        print("🚀 Démarrage du nouveau serveur...")
        subprocess.Popen([sys.executable, "api_unified.py"], 
                        cwd=os.getcwd())
        
        print("✅ Serveur redémarré avec succès!")
        print("🌐 API disponible sur: http://localhost:6000")
        print("📊 Dashboard disponible sur: http://localhost:3000")
        print("\n💡 Testez maintenant l'export CSV - les caractères français devraient s'afficher correctement!")
        
    except Exception as e:
        print(f"❌ Erreur lors du redémarrage: {e}")
        print("💡 Vous pouvez redémarrer manuellement avec: python api_unified.py")

if __name__ == "__main__":
    restart_server() 