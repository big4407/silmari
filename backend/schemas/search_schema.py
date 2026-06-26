from datetime import datetime
from pydantic import BaseModel, Field


# 페이징 처리에 필요한 스키마
class PagingInfo(BaseModel):
    """
    프론트 단에서 페이징 처리를 할 때 필요한 모든 정보
    React에서 이 정보로 페이지 버튼을 렌더링합니다:
    {has_prev && <button>이전</button>}
    <span>{page} / {total_pages}/</span>
    {has_next && <button>다음</button>}
    """

    total: int  # 전체 게시글 수
    total_pages: int  # 전체 페이지 수
    page: int  # 현재 페이지
    per_page: int  # 페이지 당 항목 수
    has_prev: bool  # 이전 페이지 존재 여부
    has_next: bool  # 다음 페이지 존재 여부


class SearchCreate(BaseModel):
    """
    검색을 시도할 때 필요한 schema
    아래의 변수들과 더불어 자동 생성되는 id, searched_at을 search 테이블에 저장하고,
    동시에 검색을 진행할 것
    """

    user_id: str = Field(max_length=20)
    message_sn: str | None = Field(default=None, max_length=22)

    missing_name: str | None = Field(default=None, max_length=20)
    gender: str | None = Field(default=None, max_length=1)  # M, F
    age: int | None = None
    clothing: str | None = Field(default=None, max_length=100)
    missing_location: str | None = Field(default=None, max_length=20)
    missing_time: datetime | None = None

    search_type: str = Field(
        default="1", max_length=1
    )  # 1 : SMS API에서 파싱한데이터, 2: 챗봇, 3: 자동검색(선택사항)


class SearchDetail(BaseModel):
    """
    검색 내역에서 상세 내용을 보여줄 때 사용할 스키마
    """

    id: int
    user_id: str
    message_sn: str | None
    missing_name: str | None
    gender: str | None
    age: int | None
    clothing: str | None
    missing_location: str | None
    missing_time: datetime | None
    searched_at: datetime
    search_type: str

    class Config:
        from_attributes = True


class SearchItem(BaseModel):
    """
    검색 목록에서 대략적인 내용만 보여줄 때 사용할 스키마
    """

    id: int
    missing_name: str | None
    gender: str | None
    age: int | None
    clothing: str | None
    missing_location: str | None
    searched_at: datetime
    search_type: str


class SearchListResponse(BaseModel):
    """
    검색 목록을 반환할 때 사용할 스키마
    """

    items: list[SearchItem]
    page_info: PagingInfo
