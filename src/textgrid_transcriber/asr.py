from __future__ import annotations

import wave
from pathlib import Path

from google.cloud import speech
from google.oauth2 import service_account


def _client(credentials_path: Path | None) -> speech.SpeechClient:
    if credentials_path is None:
        return speech.SpeechClient()
    creds = service_account.Credentials.from_service_account_file(str(credentials_path))
    return speech.SpeechClient(credentials=creds)


def transcribe_wav(
    audio_path: Path,
    credentials_path: Path | None,
    language: str = "en-US",
    model: str | None = None,
) -> str:
    with wave.open(str(audio_path), "rb") as wav_file:
        sample_rate = wav_file.getframerate()
        audio_content = wav_file.readframes(wav_file.getnframes())

    client = _client(credentials_path)
    audio = speech.RecognitionAudio(content=audio_content)
    config_kwargs = {
        "encoding": speech.RecognitionConfig.AudioEncoding.LINEAR16,
        "sample_rate_hertz": sample_rate,
        "language_code": language,
    }
    if model:
        config_kwargs["model"] = model

    config = speech.RecognitionConfig(**config_kwargs)
    response = client.recognize(config=config, audio=audio)

    transcripts = []
    for result in response.results:
        if result.alternatives:
            transcripts.append(result.alternatives[0].transcript)

    return " ".join(transcripts).strip()
