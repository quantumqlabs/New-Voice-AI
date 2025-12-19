import os
import requests
from dotenv import load_dotenv

load_dotenv()

class ElevenLabsTTS:
    def __init__(self):
        self.api_key = os.getenv('ELEVENLABS_API_KEY')
        self.voice_id = os.getenv('ELEVENLABS_VOICE_ID')
        self.base_url = "https://api.elevenlabs.io/v1"
        
        # Enhanced debugging
        print(f"\n{'='*50}")
        print("ELEVENLABS TTS INITIALIZATION")
        print(f"{'='*50}")
        print(f"API Key present: {bool(self.api_key)}")
        if self.api_key:
            print(f"API Key (first 10 chars): {self.api_key[:10]}...")
        print(f"Voice ID present: {bool(self.voice_id)}")
        if self.voice_id:
            print(f"Voice ID: {self.voice_id}")
        print(f"{'='*50}\n")
        
        if self.api_key and self.voice_id:
            self.enabled = True
            print(f"✅ ElevenLabs TTS enabled")
        else:
            self.enabled = False
            print("⚠️ ElevenLabs not configured")
            if not self.api_key:
                print("   ❌ Missing ELEVENLABS_API_KEY in .env")
            if not self.voice_id:
                print("   ❌ Missing ELEVENLABS_VOICE_ID in .env")
    
    def text_to_speech(self, text):
        if not self.enabled:
            print("⚠️ ElevenLabs disabled - API key or Voice ID missing")
            return None
        
        url = f"{self.base_url}/text-to-speech/{self.voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        
        data = {
            "text": text,
            "model_id": "eleven_turbo_v2_5",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "optimize_streaming_latency": 3,
                
                "style": 0.0,
                "use_speaker_boost": True
            }
        }
        
        try:
            print(f"\n[ELEVENLABS] Making request to: {url}")
            print(f"[ELEVENLABS] Text length: {len(text)} chars")
            
            response = requests.post(url, json=data, headers=headers, timeout=15)
            
            print(f"[ELEVENLABS] Response status: {response.status_code}")
            
            if response.status_code == 200:
                audio_size = len(response.content)
                print(f"[ELEVENLABS] ✅ Success! Audio size: {audio_size} bytes")
                return response.content
            else:
                print(f"[ELEVENLABS] ❌ Error: {response.status_code}")
                print(f"[ELEVENLABS] Response: {response.text[:200]}")
                return None
                
        except requests.exceptions.Timeout:
            print(f"[ELEVENLABS] ❌ Request timeout (15s)")
            return None
        except Exception as e:
            print(f"[ELEVENLABS] ❌ Error: {type(e).__name__}: {e}")
            return None