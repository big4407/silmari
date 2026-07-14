from backend.db.database import SessionLocal
from backend.services.chatbot_service import ChatbotService


USER_ID = "0b3b4b93-3aa8-4af0-a16a-ff98e42437f9"


def main():
    db = SessionLocal()
    service = ChatbotService(db)

    print("실마리 챗봇 테스트를 시작합니다.")
    print("종료하려면 exit 입력\n")

    try:
        while True:
            message = input("USER > ")

            if message.lower() in ["exit", "quit", "q"]:
                break

            result = service.chat(
                user_id=USER_ID,
                message=message,
                session_id=None,
            )

            response = result.get("response", "")
            state = {k: v for k, v in result.items() if k != "response"}

            print(f"BOT  > {response}")
            print(
                f"STATE> region={state.get('region')}, time={state.get('start_time')}~{state.get('end_time')}, appearance={state.get('appearance')}, search_id={state.get('search_id')}"
            )
            print()

    finally:
        db.close()


if __name__ == "__main__":
    main()
