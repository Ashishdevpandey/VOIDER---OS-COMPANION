"""
TTS Service for VOIDER
Handles Text-to-Speech using edge-tts (high-quality neural voices)
"""

import logging
import asyncio
import edge_tts
from typing import List, Dict, Optional
import os
import tempfile

logger = logging.getLogger(__name__)

class TTSService:
    def __init__(self, default_voice: str = "en-US-AnaNeural"):
        self.default_voice = default_voice
        logger.info(f"TTS Service initialized with default voice: {default_voice}")

    async def get_voices(self) -> List[Dict]:
        """List all available neural voices"""
        try:
            voices = await edge_tts.VoicesManager.create()
            # Filter for some common high-quality English voices
            # Specifically looking for the "Cute" one requested
            preferred_ids = [
                "en-US-AnaNeural",    # Cute
                "en-US-JennyNeural",  # Conversational
                "en-US-AriaNeural",   # Confident
                "en-GB-SoniaNeural",  # Friendly
                "en-US-MichelleNeural",
                "en-US-EmmaNeural"
            ]
            
            all_voices = voices.find(Language="en")
            result = []
            for v in all_voices:
                if v["ShortName"] in preferred_ids or "en-US" in v["ShortName"]:
                    result.append({
                        "id": v["ShortName"],
                        "name": v["FriendlyName"],
                        "gender": v["Gender"],
                        "style": "Cute" if "Ana" in v["ShortName"] else "General"
                    })
            return result
        except Exception as e:
            logger.error(f"Failed to fetch voices: {e}")
            return []

    async def generate_audio(self, text: str, voice: Optional[str] = None) -> str:
        """Generate audio file and return the path"""
        voice = voice or self.default_voice
        
        # Create a temporary file
        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        
        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(path)
            return path
        except Exception as e:
            logger.error(f"TTS generation error: {e}")
            if os.path.exists(path):
                os.unlink(path)
            raise

# Singleton factory
_tts_service: Optional[TTSService] = None

def get_tts_service(default_voice: str = "en-US-AnaNeural") -> TTSService:
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService(default_voice=default_voice)
    return _tts_service
