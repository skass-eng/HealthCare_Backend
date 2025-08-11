#!/usr/bin/env python3
"""
WEBSOCKETS - HealthCare AI Architecture ODYSSEE
Communication temps réel inspirée d'ODYSSEE pour notifications d'analyses
Version: 1.0.0 - Architecture ODYSSEE
"""

from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.routing import APIRouter
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Union
import json
import asyncio
import logging
from uuid import UUID

from ..db.database import get_db
from shared.models import User, Plainte, Analyse
from shared.schemas import WebSocketMessage, NotificationAnalyseComplete
from ..core.auth import get_user_from_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSockets"])

class ConnectionManager:
    """
    Gestionnaire de connexions WebSocket inspiré d'ODYSSEE
    Gère les notifications temps réel des analyses terminées
    """
    
    def __init__(self):
        # Connexions actives par utilisateur (UUID ou int)
        self.active_connections: Dict[Union[UUID, int], List[WebSocket]] = {}
        # Connexions par plainte (pour notifications spécifiques)
        self.plainte_connections: Dict[UUID, List[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket, user_id: Union[UUID, int], plainte_id: Optional[UUID] = None):
        """Accepter une nouvelle connexion WebSocket"""
        # La connexion est déjà acceptée dans l'endpoint
        
        # Ajouter à la liste des connexions utilisateur
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        
        # Ajouter à la liste des connexions plainte si spécifié
        if plainte_id:
            if plainte_id not in self.plainte_connections:
                self.plainte_connections[plainte_id] = []
            self.plainte_connections[plainte_id].append(websocket)
        
        logger.info(f"✅ Connexion WebSocket établie - User: {user_id}, Plainte: {plainte_id}")
        
    def disconnect(self, websocket: WebSocket, user_id: Union[UUID, int], plainte_id: Optional[UUID] = None):
        """Déconnecter un WebSocket"""
        try:
            # Retirer des connexions utilisateur
            if user_id in self.active_connections:
                if websocket in self.active_connections[user_id]:
                    self.active_connections[user_id].remove(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            
            # Retirer des connexions plainte
            if plainte_id and plainte_id in self.plainte_connections:
                if websocket in self.plainte_connections[plainte_id]:
                    self.plainte_connections[plainte_id].remove(websocket)
                if not self.plainte_connections[plainte_id]:
                    del self.plainte_connections[plainte_id]
                    
            logger.info(f"📡 Connexion WebSocket fermée - User: {user_id}, Plainte: {plainte_id}")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la déconnexion WebSocket: {e}")
    
    async def send_personal_message(self, message: WebSocketMessage, user_id: Union[UUID, int]):
        """Envoyer un message à un utilisateur spécifique"""
        if user_id in self.active_connections:
            message_data = message.dict()
            disconnected_sockets = []
            
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_text(json.dumps(message_data, default=str))
                except Exception as e:
                    logger.error(f"❌ Erreur envoi message personnel: {e}")
                    disconnected_sockets.append(websocket)
            
            # Nettoyer les connexions fermées
            for ws in disconnected_sockets:
                self.disconnect(ws, user_id)
    
    async def send_plainte_message(self, message: WebSocketMessage, plainte_id: UUID):
        """Envoyer un message à tous les abonnés d'une plainte"""
        if plainte_id in self.plainte_connections:
            message_data = message.dict()
            disconnected_sockets = []
            
            for websocket in self.plainte_connections[plainte_id]:
                try:
                    await websocket.send_text(json.dumps(message_data, default=str))
                except Exception as e:
                    logger.error(f"❌ Erreur envoi message plainte: {e}")
                    disconnected_sockets.append(websocket)
            
            # Nettoyer les connexions fermées
            for ws in disconnected_sockets:
                for user_id in self.active_connections:
                    if ws in self.active_connections[user_id]:
                        self.disconnect(ws, user_id, plainte_id)
                        break
    
    async def broadcast(self, message: WebSocketMessage):
        """Diffuser un message à toutes les connexions actives"""
        message_data = message.dict()
        all_connections = []
        
        # Rassembler toutes les connexions
        for connections in self.active_connections.values():
            all_connections.extend(connections)
        
        # Envoyer à toutes les connexions
        for websocket in all_connections:
            try:
                await websocket.send_text(json.dumps(message_data, default=str))
            except Exception as e:
                logger.error(f"❌ Erreur broadcast: {e}")

# Instance globale du gestionnaire
manager = ConnectionManager()

@router.websocket("/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    db: Session = Depends(get_db)
):
    """
    WebSocket pour notifications générales utilisateur (comme ODYSSEE)
    """
    try:
        # Accepter la connexion d'abord
        await websocket.accept()
        
        # Récupérer user_id depuis les paramètres de requête
        query_params = websocket.query_params
        user_id_str = query_params.get("user_id")
        
        if not user_id_str:
            print("⚠️ WebSocket: user_id manquant dans les paramètres")
            await websocket.close(code=4001, reason="user_id manquant")
            return
        
        try:
            # Essayer d'abord comme UUID, puis comme entier
            try:
                user_id = UUID(user_id_str)
            except ValueError:
                # Si ce n'est pas un UUID valide, traiter comme un entier
                user_id = int(user_id_str)
        except ValueError:
            print(f"⚠️ WebSocket: user_id invalide: {user_id_str}")
            await websocket.close(code=4001, reason="user_id invalide")
            return
        
        print(f"🔌 WebSocket: Connexion acceptée pour user_id={user_id}")
        
        # TODO: Réactiver l'authentification plus tard
        # Récupérer le token depuis les headers ou paramètres de requête
        token = None
        
        # Essayer de récupérer depuis les headers
        auth_header = websocket.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Enlever "Bearer "
        
        # Essayer de récupérer depuis les paramètres de requête
        if not token:
            token = query_params.get("token")
        
        if not token:
            print("⚠️ WebSocket: Token manquant, mais connexion acceptée pour le test")
            # await websocket.close(code=4001, reason="Token manquant")
            # return
        
        # Vérifier l'authentification via token
        user = None
        if token:
            user = await get_user_from_token(token, db)
            if not user or str(user.id) != str(user_id):
                print(f"⚠️ WebSocket: Utilisateur non autorisé, mais connexion acceptée pour le test")
                # await websocket.close(code=4001, reason="Non autorisé")
                # return
        
        # Établir la connexion
        await manager.connect(websocket, user_id)
        
        try:
            # Envoyer un message de bienvenue
            welcome_message = WebSocketMessage(
                type="connection_established",
                data={
                    "message": "Connexion WebSocket établie",
                    "user_id": str(user_id),
                    "features": ["analyse_notifications", "plainte_updates"]
                },
                timestamp=datetime.now(),
                user_id=user_id
            )
            await manager.send_personal_message(welcome_message, user_id)
            
            # Boucle d'écoute des messages
            while True:
                try:
                    # Recevoir les messages du client (heartbeat, etc.)
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    
                    # Traiter les messages du client
                    if message.get("type") == "heartbeat":
                        await websocket.send_text(json.dumps({
                            "type": "heartbeat_ack",
                            "timestamp": datetime.now().isoformat()
                        }))
                    
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    logger.error(f"❌ Erreur réception message WebSocket: {e}")
                    break
                    
        finally:
            manager.disconnect(websocket, user_id)
            
    except Exception as e:
        logger.error(f"❌ Erreur WebSocket notifications: {e}")
        try:
            await websocket.close(code=4000, reason="Erreur serveur")
        except:
            pass

@router.websocket("/plainte/{plainte_id}")
async def websocket_plainte(
    websocket: WebSocket,
    plainte_id: UUID,
    token: str,
    db: Session = Depends(get_db)
):
    """
    WebSocket pour suivre les analyses d'une plainte spécifique (comme les widgets ODYSSEE)
    """
    try:
        # Vérifier l'authentification
        user = await get_user_from_token(token, db)
        if not user:
            await websocket.close(code=4001, reason="Non autorisé")
            return
        
        # Vérifier l'accès à la plainte
        plainte = db.query(Plainte).filter(Plainte.id == plainte_id).first()
        if not plainte:
            await websocket.close(code=4004, reason="Plainte non trouvée")
            return
        
        # Établir la connexion
        await manager.connect(websocket, user.id, plainte_id)
        
        try:
            # Envoyer l'état actuel des analyses
            analyses = db.query(Analyse).filter(Analyse.plainte_id == plainte_id).all()
            
            status_message = WebSocketMessage(
                type="plainte_status",
                data={
                    "plainte_id": str(plainte_id),
                    "statut": plainte.statut.value,
                    "analyses": [
                        {
                            "id": str(analyse.id),
                            "type": analyse.type_analyse.value,
                            "statut": analyse.statut.value,
                            "resultats": analyse.resultats
                        }
                        for analyse in analyses
                    ]
                },
                timestamp=datetime.now(),
                user_id=user.id
            )
            await manager.send_personal_message(status_message, user.id)
            
            # Boucle d'écoute
            while True:
                try:
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    
                    if message.get("type") == "request_update":
                        # Renvoyer l'état actuel
                        await manager.send_personal_message(status_message, user.id)
                        
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    logger.error(f"❌ Erreur réception message plainte WebSocket: {e}")
                    break
                    
        finally:
            manager.disconnect(websocket, user.id, plainte_id)
            
    except Exception as e:
        logger.error(f"❌ Erreur WebSocket plainte: {e}")
        try:
            await websocket.close(code=4000, reason="Erreur serveur")
        except:
            pass

# Fonctions utilitaires pour les Workers

async def notify_analyse_complete(analyse_id: UUID, db: Session):
    """
    Notifier la fin d'une analyse (appelé par les Workers Celery)
    """
    try:
        analyse = db.query(Analyse).filter(Analyse.id == analyse_id).first()
        if not analyse:
            logger.error(f"❌ Analyse non trouvée: {analyse_id}")
            return
        
        plainte = db.query(Plainte).filter(Plainte.id == analyse.plainte_id).first()
        if not plainte:
            logger.error(f"❌ Plainte non trouvée: {analyse.plainte_id}")
            return
        
        # Créer la notification
        notification = NotificationAnalyseComplete(
            plainte_id=analyse.plainte_id,
            analyse_id=analyse.id,
            type_analyse=analyse.type_analyse,
            statut=analyse.statut,
            resultats_resume={
                "score": analyse.resultats.get("score"),
                "classification": analyse.resultats.get("classification"),
                "resume": analyse.resultats.get("resume", "Analyse terminée")
            }
        )
        
        # Message WebSocket
        ws_message = WebSocketMessage(
            type="analyse_complete",
            data=notification.dict(),
            timestamp=datetime.now()
        )
        
        # Envoyer aux abonnés de la plainte
        await manager.send_plainte_message(ws_message, analyse.plainte_id)
        
        # Envoyer au créateur de la plainte
        if plainte.createur_id:
            await manager.send_personal_message(ws_message, plainte.createur_id)
        
        logger.info(f"✅ Notification analyse envoyée: {analyse_id}")
        
    except Exception as e:
        logger.error(f"❌ Erreur notification analyse: {e}")

async def notify_plainte_update(plainte_id: UUID, action: str, data: dict, db: Session):
    """
    Notifier une mise à jour de plainte
    """
    try:
        ws_message = WebSocketMessage(
            type="plainte_update",
            data={
                "plainte_id": str(plainte_id),
                "action": action,
                "data": data
            },
            timestamp=datetime.now()
        )
        
        # Envoyer aux abonnés de la plainte
        await manager.send_plainte_message(ws_message, plainte_id)
        
        logger.info(f"✅ Notification plainte envoyée: {plainte_id} - {action}")
        
    except Exception as e:
        logger.error(f"❌ Erreur notification plainte: {e}")

# Import datetime pour les timestamps
from datetime import datetime

# Endpoint WebSocket simple pour test
@router.websocket("/test")
async def websocket_test(websocket: WebSocket):
    """
    WebSocket de test simple
    """
    try:
        await websocket.accept()
        print("✅ WebSocket test: Connexion acceptée")
        
        # Envoyer un message de test
        await websocket.send_text(json.dumps({
            "type": "test",
            "message": "WebSocket fonctionne!",
            "timestamp": datetime.now().isoformat()
        }))
        
        # Attendre un message du client
        try:
            data = await websocket.receive_text()
            print(f"📨 WebSocket test: Message reçu: {data}")
            
            # Répondre
            await websocket.send_text(json.dumps({
                "type": "echo",
                "message": f"Echo: {data}",
                "timestamp": datetime.now().isoformat()
            }))
            
        except WebSocketDisconnect:
            print("📡 WebSocket test: Client déconnecté")
            
    except Exception as e:
        print(f"❌ WebSocket test: Erreur: {e}")
        try:
            await websocket.close(code=4000, reason="Erreur serveur")
        except:
            pass