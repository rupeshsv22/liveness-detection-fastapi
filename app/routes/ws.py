from __future__ import annotations
import base64
import json
import time
from datetime import datetime, timezone

import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import settings
from app.models.enums import ChallengeType, SessionStatus
from app.models.schemas import ChallengeItem, CompletionResponse, FrameResponse
from app.services.anti_spoof import compute_spoof_score
from app.services.blink_detector import BlinkDetector
from app.services.face_detector import FaceDetector
from app.services.head_pose import HeadPoseDetector
from app.services.scorer import calculate_liveness_score, is_passing
from app.services.session import session_manager

router = APIRouter(prefix="/api/liveness", tags=["liveness-ws"])


def _decode_frame(b64_string: str) -> np.ndarray | None:
    try:
        raw = base64.b64decode(b64_string)
        buf = np.frombuffer(raw, dtype=np.uint8)
        img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        return img
    except Exception:
        return None


def _challenge_to_dict(c: ChallengeItem | None) -> dict | None:
    if c is None:
        return None
    return {"type": c.type.value, "instruction": c.instruction, "order": c.order}


@router.websocket("/stream/{session_id}")
async def stream_frames(websocket: WebSocket, session_id: str):
    await websocket.accept()

    session = session_manager.get(session_id)
    if session is None or session.status == SessionStatus.EXPIRED:
        await websocket.send_json({"error": "Session not found or expired"})
        await websocket.close(code=4004)
        return

    session.status = SessionStatus.IN_PROGRESS
    session.touch()

    face_detector = FaceDetector()
    blink_detector = BlinkDetector()
    head_pose_detector = HeadPoseDetector()

    frame_count: int = 0
    no_face_streak: int = 0

    try:
        while True:
            # ── Receive frame ──────────────────────────────────────────────
            try:
                raw = await websocket.receive_text()
                data = json.loads(raw)
            except (WebSocketDisconnect, RuntimeError):
                break
            except Exception:
                await websocket.send_json(
                    FrameResponse(
                        face_detected=False,
                        face_count=0,
                        error="Invalid message format",
                    ).model_dump()
                )
                continue

            frame_count += 1
            session.touch()

            # ── Decode image ───────────────────────────────────────────────
            frame = _decode_frame(data.get("frame", ""))
            if frame is None:
                await websocket.send_json(
                    FrameResponse(
                        face_detected=False,
                        face_count=0,
                        error="Frame decode error",
                    ).model_dump()
                )
                continue

            # ── Face detection ─────────────────────────────────────────────
            face_result = face_detector.process(frame)

            if not face_result.detected or face_result.face_count != 1:
                no_face_streak += 1
                msg = ""
                if face_result.face_count > 1:
                    msg = "Multiple faces detected. Please ensure only one face is visible."
                elif no_face_streak >= settings.NO_FACE_FAIL_FRAMES:
                    # Auto-fail
                    session.status = SessionStatus.FAILED
                    session.completed_at = datetime.now(timezone.utc)
                    session.liveness_score = 0.0
                    session.passed = False
                    await websocket.send_json({"error": "No face detected. Session failed.", "session_complete": True, "liveness_score": 0.0, "passed": False})
                    break
                elif no_face_streak >= settings.NO_FACE_WARN_FRAMES:
                    msg = "No face detected. Please position your face in the frame."

                await websocket.send_json(
                    FrameResponse(
                        face_detected=False,
                        face_count=face_result.face_count,
                        message=msg,
                        current_challenge=_challenge_to_dict(session.current_challenge),
                    ).model_dump()
                )
                continue

            no_face_streak = 0
            landmarks = face_result.landmarks

            # ── Anti-spoof (every N frames) ────────────────────────────────
            spoof_score = 0.0
            if frame_count % settings.SPOOF_CHECK_INTERVAL == 0:
                roi = face_detector.get_face_roi(frame, landmarks)
                spoof_score = compute_spoof_score(roi)
                session.spoof_scores.append(spoof_score)
                if spoof_score > settings.SPOOF_THRESHOLD:
                    session.spoof_detected = True

            # ── Challenge processing ───────────────────────────────────────
            current = session.current_challenge
            challenge_completed = False

            if current is not None:
                if current.type in (ChallengeType.BLINK, ChallengeType.BLINK_TWICE):
                    blink_detector.update(face_detector, landmarks, face_result.image_shape)
                    if current.type == ChallengeType.BLINK:
                        challenge_completed = blink_detector.check_blink_once()
                    else:
                        challenge_completed = blink_detector.check_blink_twice()

                elif current.type in (ChallengeType.TURN_LEFT, ChallengeType.TURN_RIGHT, ChallengeType.NOD):
                    pose = head_pose_detector.estimate(face_detector, landmarks, face_result.image_shape)
                    if pose is not None:
                        pitch, yaw, _ = pose
                        if current.type == ChallengeType.TURN_LEFT:
                            challenge_completed = head_pose_detector.check_turn_left(yaw)
                        elif current.type == ChallengeType.TURN_RIGHT:
                            challenge_completed = head_pose_detector.check_turn_right(yaw)
                        elif current.type == ChallengeType.NOD:
                            challenge_completed = head_pose_detector.check_nod(pitch)

                if challenge_completed:
                    session.challenges_completed += 1
                    session.current_challenge_index += 1
                    # Reset detectors for next challenge
                    blink_detector.reset()
                    head_pose_detector.reset()

            # ── All challenges done? ───────────────────────────────────────
            if session.current_challenge is None and session.challenges_completed == len(session.challenges):
                session.completed_at = datetime.now(timezone.utc)
                session.status = SessionStatus.COMPLETED
                score = calculate_liveness_score(session)
                session.liveness_score = score
                session.passed = is_passing(score, session.spoof_detected)

                await websocket.send_json(
                    CompletionResponse(
                        liveness_score=score,
                        passed=session.passed,
                    ).model_dump()
                )
                break

            # ── Per-frame response ─────────────────────────────────────────
            next_challenge = session.current_challenge
            msg = next_challenge.instruction if next_challenge else ""

            resp = FrameResponse(
                face_detected=True,
                face_count=1,
                current_challenge=_challenge_to_dict(next_challenge),
                challenge_completed=challenge_completed,
                spoof_score=round(spoof_score, 4),
                spoof_detected=session.spoof_detected,
                message=msg,
            )
            await websocket.send_json(resp.model_dump())

    except WebSocketDisconnect:
        if session.status == SessionStatus.IN_PROGRESS:
            session.status = SessionStatus.EXPIRED
    finally:
        face_detector.close()
