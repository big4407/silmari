def compare_face(person_crop, reference_img_path: str) -> float:
    """실종자 사진과 얼굴 비교. 유사도 반환 (0.0 ~ 1.0)"""
    try:
        from deepface import DeepFace

        result = DeepFace.verify(
            person_crop,
            reference_img_path,
            model_name="VGG-Face",
            enforce_detection=False,
            silent=True,
        )
        return round(max(0.0, 1.0 - result["distance"]), 4)
    except Exception:
        return 0.0
