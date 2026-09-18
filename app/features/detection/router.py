import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile

from app.core.config import get_settings
from app.deps import DbSession, get_optional_user_id
from app.models.detection import DetectionRecord, SegmentScore
from app.schemas.detection import BatchDetectionResultOut, DetectionResultOut, SegmentResultOut
from app.services.audio_preprocessor import AudioPreprocessor, UnsupportedAudioError
from app.services.onnx_analyzer import get_analyzer
from app.services.threshold_service import get_current_threshold

logger = logging.getLogger(__name__)
router = APIRouter(tags=["detection"])


@router.get("/health")
def health() -> dict:
    analyzer = get_analyzer()
    return {
        "status": "ok",
        "model_version": analyzer.model_version,
        "using_mock_model": "mock" in analyzer.model_version.lower(),
    }


@router.post("/predict", response_model=BatchDetectionResultOut)
def predict(
    db: DbSession,
    files: Annotated[list[UploadFile], File(...)],
    user_id: Annotated[UUID | None, Depends(get_optional_user_id)] = None,
) -> BatchDetectionResultOut:
    settings = get_settings()
    preprocessor = AudioPreprocessor()
    analyzer = get_analyzer()
    threshold = get_current_threshold(db, settings)

    results: list[DetectionResultOut] = []
    failed_files: list[str] = []

    for upload in files:
        raw_bytes = upload.file.read()
        filename = upload.filename or "unknown"

        if not preprocessor.validate_format(filename, len(raw_bytes)):
            failed_files.append(filename)
            continue

        try:
            buffer = preprocessor.process(raw_bytes, filename)
        except UnsupportedAudioError:
            failed_files.append(filename)
            continue

        report = analyzer.analyze(buffer, threshold=threshold)
        buffer.release()  # ปล่อยข้อมูลเสียงออกจาก memory ทันทีหลังได้ผลลัพธ์

        record = DetectionRecord(
            **report.to_record_kwargs(
                user_id=user_id,
                original_filename=filename,
                file_size_bytes=len(raw_bytes),
                audio_format=buffer.source_format,
            )
        )
        db.add(record)
        db.flush()  # ให้ record.id ถูก generate ก่อนสร้าง segment

        for seg in report.segments:
            db.add(
                SegmentScore(
                    detection_id=record.id,
                    segment_index=seg.index,
                    start_seconds=seg.start_seconds,
                    end_seconds=seg.end_seconds,
                    spoof_probability=seg.spoof_probability,
                )
            )
        db.commit()

        results.append(
            DetectionResultOut(
                id=record.id,
                original_filename=filename,
                duration_seconds=report.duration_seconds,
                sample_rate=report.sample_rate,
                num_segments=report.num_segments,
                mean_probability=report.mean_spoof_probability,
                max_probability=report.max_spoof_probability,
                threshold_used=report.threshold,
                verdict=report.verdict,
                possible_partial_spoof=report.possible_partial_spoof,
                model_version=report.model_version,
                processing_ms=report.processing_ms,
                segments=[SegmentResultOut(**seg.__dict__) for seg in report.segments],
                saved_to_history=user_id is not None,
            )
        )

    return BatchDetectionResultOut(results=results, failed_files=failed_files)
