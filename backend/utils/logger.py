"""애플리케이션 공통 로거 — silmari 네임스페이스."""
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger("silmari")
