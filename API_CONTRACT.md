# Android ↔ Windows API contract

Future endpoints:

GET  /api/status
POST /api/voice
POST /api/command
GET  /api/memory/recent

Every remote command must authenticate and pass the same permission layer used
by the desktop assistant.
