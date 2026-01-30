from __future__ import annotations

import json
import os
import wave
from pathlib import Path

from google.api_core.exceptions import NotFound, PermissionDenied
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech
from google.oauth2 import service_account

DEFAULT_ASR_MODEL = "chirp_3"
DEFAULT_ASR_LOCATION = "us"
DEFAULT_RECOGNIZER_ID = "default"


def _client(credentials_path: Path | None, location: str) -> SpeechClient:
    client_options = None
    if location != "global":
        client_options = {"api_endpoint": f"{location}-speech.googleapis.com"}
    if credentials_path is None:
        return SpeechClient(client_options=client_options)
    creds = service_account.Credentials.from_service_account_file(str(credentials_path))
    return SpeechClient(credentials=creds, client_options=client_options)


def _project_id_from_credentials(credentials_path: Path | None) -> str | None:
    if credentials_path is None:
        return None
    try:
        data = json.loads(Path(credentials_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    project_id = data.get("project_id")
    if isinstance(project_id, str) and project_id.strip():
        return project_id.strip()
    return None


def _resolve_project_id(credentials_path: Path | None) -> str:
    for env_key in ("GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_QUOTA_PROJECT"):
        value = os.getenv(env_key, "").strip()
        if value:
            return value
    project_id = _project_id_from_credentials(credentials_path)
    if project_id:
        return project_id
    raise ValueError(
        "Missing Google Cloud project ID. Set GOOGLE_CLOUD_PROJECT or provide a service account key."
    )


def _resolve_location() -> str:
    return os.getenv("GOOGLE_CLOUD_LOCATION", DEFAULT_ASR_LOCATION).strip() or DEFAULT_ASR_LOCATION


def _resolve_recognizer_name(project_id: str, location: str) -> tuple[str, str]:
    recognizer_value = os.getenv("GOOGLE_CLOUD_RECOGNIZER", "").strip()
    if recognizer_value:
        if recognizer_value.startswith("projects/"):
            return recognizer_value, ""
        return f"projects/{project_id}/locations/{location}/recognizers/{recognizer_value}", recognizer_value
    return f"projects/{project_id}/locations/{location}/recognizers/{DEFAULT_RECOGNIZER_ID}", DEFAULT_RECOGNIZER_ID


def _ensure_recognizer(
    client: SpeechClient,
    project_id: str,
    location: str,
    recognizer_name: str,
    recognizer_id: str,
    language: str,
    model: str,
) -> None:
    if recognizer_id == "" or recognizer_name.endswith("/_"):
        return
    try:
        client.get_recognizer(name=recognizer_name)
        return
    except NotFound:
        pass
    try:
        request = cloud_speech.CreateRecognizerRequest(
            parent=f"projects/{project_id}/locations/{location}",
            recognizer_id=recognizer_id,
            recognizer=cloud_speech.Recognizer(
                default_recognition_config=cloud_speech.RecognitionConfig(
                    auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
                    language_codes=[language],
                    model=model,
                ),
            ),
        )
        operation = client.create_recognizer(request=request)
        operation.result()
    except PermissionDenied as exc:
        raise ValueError(
            "Recognizer does not exist and cannot be created. "
            "Grant the service account the Speech-to-Text Admin role or create a recognizer in the "
            f"{location} location, then set GOOGLE_CLOUD_RECOGNIZER to its ID."
        ) from exc


def transcribe_wav(
    audio_path: Path,
    credentials_path: Path | None,
    language: str = "en-US",
    model: str | None = DEFAULT_ASR_MODEL,
) -> str:
    with wave.open(str(audio_path), "rb") as wav_file:
        audio_content = wav_file.readframes(wav_file.getnframes())

    location = _resolve_location()
    client = _client(credentials_path, location)
    project_id = _resolve_project_id(credentials_path)
    recognizer_name, recognizer_id = _resolve_recognizer_name(project_id, location)
    resolved_model = model or DEFAULT_ASR_MODEL
    _ensure_recognizer(
        client,
        project_id,
        location,
        recognizer_name,
        recognizer_id,
        language,
        resolved_model,
    )
    config = cloud_speech.RecognitionConfig(
        explicit_decoding_config=cloud_speech.ExplicitDecodingConfig(
            encoding=cloud_speech.ExplicitDecodingConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            audio_channel_count=1,
        ),
        language_codes=[language],
        model=resolved_model,
    )
    request = cloud_speech.RecognizeRequest(
        recognizer=recognizer_name,
        config=config,
        content=audio_content,
    )
    response = client.recognize(request=request)

    transcripts = []
    for result in response.results:
        if result.alternatives:
            transcripts.append(result.alternatives[0].transcript)

    return " ".join(transcripts).strip()
