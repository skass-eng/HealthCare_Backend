#!/usr/bin/env python3
"""
PROVIDER LLM - HealthCare AI Architecture ODYSSEE
Service d'abstraction pour les différents fournisseurs LLM (inspiré d'ODYSSEE)
Version: 1.0.0 - Architecture ODYSSEE
"""

import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class LLMProvider(Enum):
    """Fournisseurs LLM supportés"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"

class BaseLLMService(ABC):
    """
    Classe de base pour les services LLM (pattern Strategy comme ODYSSEE)
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = None, **kwargs):
        self.api_key = api_key
        self.model = model
        self.config = kwargs
    
    @abstractmethod
    async def analyze(self, prompt: str, parameters: Dict[str, Any] = None) -> str:
        """Analyser un prompt et retourner la réponse"""
        pass
    
    @abstractmethod
    def parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parser une réponse JSON du LLM"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Vérifier la disponibilité du service LLM"""
        pass

class OpenAIService(BaseLLMService):
    """Service OpenAI (comme les widgets spécialisés ODYSSEE)"""
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo", **kwargs):
        super().__init__(api_key, model, **kwargs)
        
        try:
            import openai
            self.client = openai.AsyncOpenAI(api_key=api_key)
            self.model = model
        except ImportError:
            raise ImportError("Le package 'openai' est requis pour utiliser OpenAI")
    
    async def analyze(self, prompt: str, parameters: Dict[str, Any] = None) -> str:
        """Analyser avec OpenAI"""
        try:
            params = parameters or {}
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "Vous êtes un assistant spécialisé dans l'analyse des plaintes hospitalières. Répondez toujours en JSON valide."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=params.get("max_tokens", 2000),
                temperature=params.get("temperature", 0.1),
                response_format={"type": "json_object"}
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"❌ Erreur OpenAI: {e}")
            raise
    
    def parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parser la réponse JSON d'OpenAI"""
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"❌ Erreur parsing JSON OpenAI: {e}")
            return {"erreur": "Réponse invalide", "response_brute": response}
    
    async def health_check(self) -> bool:
        """Vérifier la disponibilité d'OpenAI"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=10
            )
            return True
        except:
            return False

class AnthropicService(BaseLLMService):
    """Service Anthropic Claude"""
    
    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307", **kwargs):
        super().__init__(api_key, model, **kwargs)
        
        try:
            import anthropic
            self.client = anthropic.AsyncAnthropic(api_key=api_key)
            self.model = model
        except ImportError:
            raise ImportError("Le package 'anthropic' est requis pour utiliser Claude")
    
    async def analyze(self, prompt: str, parameters: Dict[str, Any] = None) -> str:
        """Analyser avec Claude"""
        try:
            params = parameters or {}
            
            # Adapter le prompt pour Claude
            full_prompt = f"""Vous êtes un assistant spécialisé dans l'analyse des plaintes hospitalières.
            
{prompt}

Répondez uniquement avec un JSON valide, sans texte supplémentaire."""
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=params.get("max_tokens", 2000),
                temperature=params.get("temperature", 0.1),
                messages=[{"role": "user", "content": full_prompt}]
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"❌ Erreur Anthropic: {e}")
            raise
    
    def parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parser la réponse JSON de Claude"""
        try:
            # Claude peut parfois ajouter du texte avant/après le JSON
            response = response.strip()
            
            # Extraire le JSON s'il y a du texte supplémentaire
            start = response.find('{')
            end = response.rfind('}') + 1
            
            if start != -1 and end != 0:
                json_str = response[start:end]
                return json.loads(json_str)
            else:
                return json.loads(response)
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ Erreur parsing JSON Claude: {e}")
            return {"erreur": "Réponse invalide", "response_brute": response}
    
    async def health_check(self) -> bool:
        """Vérifier la disponibilité de Claude"""
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Test"}]
            )
            return True
        except:
            return False

class OllamaService(BaseLLMService):
    """Service Ollama (local)"""
    
    def __init__(self, model: str = "llama2", base_url: str = "http://localhost:11434", **kwargs):
        super().__init__(None, model, **kwargs)
        self.base_url = base_url
        
        try:
            import httpx
            self.client = httpx.AsyncClient()
        except ImportError:
            raise ImportError("Le package 'httpx' est requis pour utiliser Ollama")
    
    async def analyze(self, prompt: str, parameters: Dict[str, Any] = None) -> str:
        """Analyser avec Ollama"""
        try:
            params = parameters or {}
            
            full_prompt = f"""Vous êtes un assistant spécialisé dans l'analyse des plaintes hospitalières.
            
{prompt}

Répondez uniquement avec un JSON valide."""
            
            payload = {
                "model": self.model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": params.get("temperature", 0.1),
                    "num_predict": params.get("max_tokens", 2000)
                }
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120
            )
            
            response.raise_for_status()
            result = response.json()
            
            return result.get("response", "")
            
        except Exception as e:
            logger.error(f"❌ Erreur Ollama: {e}")
            raise
    
    def parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parser la réponse JSON d'Ollama"""
        try:
            # Ollama peut retourner du texte avant/après le JSON
            response = response.strip()
            
            # Extraire le JSON
            start = response.find('{')
            end = response.rfind('}') + 1
            
            if start != -1 and end != 0:
                json_str = response[start:end]
                return json.loads(json_str)
            else:
                # Fallback si pas de JSON détecté
                return {"erreur": "Pas de JSON trouvé", "response_brute": response}
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ Erreur parsing JSON Ollama: {e}")
            return {"erreur": "Réponse invalide", "response_brute": response}
    
    async def health_check(self) -> bool:
        """Vérifier la disponibilité d'Ollama"""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except:
            return False

class FallbackService(BaseLLMService):
    """Service de fallback quand aucun LLM n'est disponible"""
    
    def __init__(self):
        super().__init__()
    
    async def analyze(self, prompt: str, parameters: Dict[str, Any] = None) -> str:
        """Retourner une réponse de fallback"""
        logger.warning("🔄 Utilisation du service de fallback LLM")
        
        # Analyser le prompt pour donner une réponse basique
        if "sentiment" in prompt.lower():
            return json.dumps({
                "score_sentiment": 0,
                "emotion_principale": "neutre",
                "intensite": "modérée",
                "resume": "Analyse de fallback - service LLM indisponible"
            })
        
        elif "classif" in prompt.lower():
            return json.dumps({
                "categorie_principale": "Autre",
                "sous_categorie": "Non spécifié",
                "confidence": 0.1,
                "justification": "Classification de fallback"
            })
        
        elif "priorite" in prompt.lower():
            return json.dumps({
                "priorite": "NORMALE",
                "score_urgence": 0.4,
                "delai_reponse_recommande": 7,
                "justification": "Priorité de fallback"
            })
        
        else:
            return json.dumps({
                "resultat": "Service LLM indisponible",
                "methode": "fallback"
            })
    
    def parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parser directement (déjà en JSON)"""
        return json.loads(response)
    
    async def health_check(self) -> bool:
        """Toujours disponible"""
        return True

# Factory pattern pour créer le service LLM approprié
def create_llm_service(provider: str = None) -> BaseLLMService:
    """
    Factory pour créer le service LLM (pattern Factory comme ODYSSEE)
    """
    if provider is None:
        provider = os.getenv("LLM_PROVIDER", "openai")
    
    try:
        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY manquante")
            
            model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
            return OpenAIService(api_key=api_key, model=model)
        
        elif provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY manquante")
            
            model = os.getenv("LLM_MODEL", "claude-3-haiku-20240307")
            return AnthropicService(api_key=api_key, model=model)
        
        elif provider == "ollama":
            model = os.getenv("LLM_MODEL", "llama2")
            base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434")
            return OllamaService(model=model, base_url=base_url)
        
        else:
            raise ValueError(f"Provider LLM non supporté: {provider}")
    
    except Exception as e:
        logger.error(f"❌ Erreur création service LLM {provider}: {e}")
        logger.info("🔄 Utilisation du service de fallback")
        return FallbackService()

# Instance globale (singleton pattern comme ODYSSEE)
_llm_service_instance = None

def get_llm_service() -> BaseLLMService:
    """
    Récupérer l'instance singleton du service LLM
    """
    global _llm_service_instance
    
    if _llm_service_instance is None:
        _llm_service_instance = create_llm_service()
        logger.info(f"✅ Service LLM initialisé: {type(_llm_service_instance).__name__}")
    
    return _llm_service_instance

async def test_llm_services():
    """
    Tester tous les services LLM disponibles
    """
    providers = ["openai", "anthropic", "ollama"]
    results = {}
    
    for provider in providers:
        try:
            service = create_llm_service(provider)
            is_healthy = await service.health_check()
            results[provider] = {
                "available": True,
                "healthy": is_healthy,
                "service": type(service).__name__
            }
        except Exception as e:
            results[provider] = {
                "available": False,
                "error": str(e)
            }
    
    return results