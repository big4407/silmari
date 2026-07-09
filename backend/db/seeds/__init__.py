"""앱 기동 시 1회 적재하는 기준 데이터 시드."""

from backend.db.seeds.code_group_seed import seed_code_groups_if_empty
from backend.db.seeds.region_seed import seed_regions_if_empty
from backend.db.seeds.retention_policy_seed import seed_retention_policies_if_empty


def seed_bootstrap_data(db) -> None:
    """region · code_group · retention_policy 테이블이 비어 있을 때만 시드."""
    seed_code_groups_if_empty(db)
    seed_regions_if_empty(db)
    seed_retention_policies_if_empty(db)
