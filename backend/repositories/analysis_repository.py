from sqlalchemy.orm import Session

from backend.db.models import Analysis, AnalysisDetail, AnalysisStatus


class AnalysisRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: str, search_id: int) -> Analysis:
        analysis = Analysis(
            user_id=user_id,
            search_id=search_id,
            analysis_status=AnalysisStatus.NOT_STARTED,
        )
        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)
        return analysis

    def add_details(self, analysis_id: int, details: list[dict]) -> list[AnalysisDetail]:
        rows = [AnalysisDetail(analysis_id=analysis_id, **d) for d in details]
        self.db.add_all(rows)
        self.db.commit()
        return rows

    def set_status(self, analysis: Analysis, status: AnalysisStatus) -> Analysis:
        analysis.analysis_status = status
        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)
        return analysis

    def find_by_search_id(self, search_id: int) -> list[Analysis]:
        return (
            self.db.query(Analysis)
            .filter(Analysis.search_id == search_id)
            .order_by(Analysis.created_at.desc())
            .all()
        )
