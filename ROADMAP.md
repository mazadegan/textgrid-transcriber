# TextGrid Transcriber Roadmap

## Overview

This document outlines the core pipeline and user workflow for **textgrid-transcriber**. The goal is to support non-technical users in splitting audio by TextGrid boundaries, transcribing each segment via ASR, and editing transcripts manually with automatic persistence.

---

## High-Level User Flow

1. User opens the application.
2. User selects:

   * an audio file (any supported format, ffmpeg supports lots of formats)
   * a corresponding TextGrid file
3. User clicks **Split**.
4. The application:

   * converts the audio file to WAV if necessary
   * splits the WAV file according to TextGrid boundaries
5. The application displays the list of audio splits.
6. For each split:

   * the user can play back the audio
   * the user can view and edit the transcription
   * the user can request ASR transcription (cached)
7. All transcription edits are automatically saved.

---

## Core Pipeline Stages

### 1. Input Selection

* User picks:

  * Audio file
  * TextGrid file
* Basic validation:

  * files exist
  * TextGrid tiers are readable, have right format

---

### 2. Audio Normalization

* Convert input audio to WAV format using embedded ffmpeg (must be cross platform!):
* Store normalized WAV as an internal working file

---

### 3. TextGrid Parsing

* Load TextGrid using kylebgorman/textgrid 
* Identify split boundaries based on:

  * tier selection (initially default tier)
  * interval start/end times
* Produce an ordered list of segments:

  * segment ID
  * start time
  * end time

---

### 4. Audio Splitting

* Slice normalized WAV using segment boundaries
* Store each split as an individual WAV file
* Associate metadata:

  * segment ID
  * file path
  * duration

---

### 5. Segment List UI Model

* Present segments as a selectable list
* Selecting a segment opens a new window, showing:

  * audio playback controls (top)
  * transcription editor (middle)
  * ASR transcription request button (bottom)

---

### 6. ASR Integration

* Each segment supports ASR transcription
* ASR behavior:

  * send split WAV to Google Cloud ASR
  * receive transcript text
  * cache result locally
* Cached transcripts are reused if ASR is requested again

---

### 7. Transcription Editing & Persistence

* Transcription field is editable by the user
* All changes are:

  * saved automatically on update
  * persisted to a project file / cache
* ASR output is treated as an initial draft, marked as unverified

---

## Scope-creep I'm avoiding

* No real-time waveform visualization
* No automatic re-alignment of TextGrid from edited text

---

## Next Steps (After Core Pipeline)

* Define project file format (JSON-based)
* Support tier selection (User might want to work on one tier at a time)
* Batch ASR transcription (Probably ideal, ASR all the segments in the background while you work on verifying the first ones to arrive)
* Export TextGrid with transcript
