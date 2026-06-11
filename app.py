"""Interactive command-line interface for the AI chatbot."""

from __future__ import annotations

from config import Config, ConfigError
from chatbot import Chatbot
from storage import ConversationStore

EXIT_COMMANDS = {"exit", "quit", "/exit", "/quit"}
CLEAR_COMMANDS = {"clear", "/clear", "reset"}
LIST_COMMANDS = {"list", "/list"}
RESUME_COMMANDS = {"resume", "/resume"}
DELETE_COMMANDS = {"delete", "/delete"}
NEW_COMMANDS = {"new", "/new"}

WELCOME = (
    "AI Chatbot ready.\n"
    "  - Type your message and press Enter.\n"
    "  - 'list' to see saved conversations.\n"
    "  - 'resume <id>' to continue a saved conversation.\n"
    "  - 'delete <id>' to remove a saved conversation.\n"
    "  - 'new' to start a fresh conversation.\n"
    "  - 'clear' to reset the current context.\n"
    "  - 'exit' or 'quit' to leave.\n"
)


class ChatCLI:
    """Thin presentation layer around the :class:`Chatbot` service."""

    def __init__(self, bot: Chatbot, store: ConversationStore | None = None) -> None:
        self._bot = bot
        self._store = store

    def run(self) -> None:
        print(WELCOME)
        while True:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                return

            if not user_input:
                continue

            keyword, _, arg = user_input.partition(" ")
            command = keyword.lower()
            arg = arg.strip()

            if command in EXIT_COMMANDS:
                print("Goodbye!")
                return
            if command in CLEAR_COMMANDS:
                self._bot.clear()
                print("Conversation context cleared.")
                continue
            if command in LIST_COMMANDS:
                self._list_conversations()
                continue
            if command in RESUME_COMMANDS:
                self._resume(arg)
                continue
            if command in DELETE_COMMANDS:
                self._delete(arg)
                continue
            if command in NEW_COMMANDS:
                self._bot.start_new()
                print("Started a new conversation.")
                continue

            self._respond(user_input)

    def _respond(self, user_input: str) -> None:
        print("Bot: ", end="", flush=True)
        streamed = False
        try:
            for token in self._bot.stream(user_input):
                print(token, end="", flush=True)
                streamed = True
        except Exception as exc:  # noqa: BLE001 - surface API/network errors gracefully
            prefix = "\n" if streamed else ""
            print(f"{prefix}Error: {exc}")
            return
        print()
        self._print_usage()

    def _print_usage(self) -> None:
        usage = self._bot.last_usage
        if usage is None:
            return
        cost = self._bot.estimate_cost(usage)
        print(
            f"[usage] prompt={usage.prompt_tokens} "
            f"completion={usage.completion_tokens} "
            f"total={usage.total_tokens} | approx cost=${cost:.6f}"
        )

    def _list_conversations(self) -> None:
        if self._store is None:
            print("Persistence is disabled.")
            return
        summaries = self._store.list_conversations()
        if not summaries:
            print("No saved conversations yet.")
            return
        print("Saved conversations:")
        for summary in summaries:
            marker = "*" if summary.id == self._bot.conversation_id else " "
            timestamp = summary.updated_at.strftime("%Y-%m-%d %H:%M")
            print(
                f" {marker} [{summary.id}] {summary.title} "
                f"({summary.message_count} msgs, {timestamp})"
            )

    def _resume(self, arg: str) -> None:
        if self._store is None:
            print("Persistence is disabled.")
            return
        conversation_id = self._parse_id(arg)
        if conversation_id is None:
            return
        try:
            count = self._bot.resume(conversation_id)
        except KeyError:
            print(f"No conversation with id {conversation_id}.")
            return
        print(f"Resumed conversation {conversation_id} ({count} messages loaded).")

    def _delete(self, arg: str) -> None:
        if self._store is None:
            print("Persistence is disabled.")
            return
        conversation_id = self._parse_id(arg)
        if conversation_id is None:
            return
        if self._store.delete_conversation(conversation_id):
            print(f"Deleted conversation {conversation_id}.")
            if self._bot.conversation_id == conversation_id:
                self._bot.start_new()
        else:
            print(f"No conversation with id {conversation_id}.")

    @staticmethod
    def _parse_id(arg: str) -> int | None:
        try:
            return int(arg)
        except ValueError:
            print("Usage: resume <id> | delete <id>  (id must be a number)")
            return None


def main() -> None:
    try:
        config = Config.load()
    except ConfigError as exc:
        print(f"Configuration error: {exc}")
        return

    store = ConversationStore(config.database_url)
    bot = Chatbot(config, store=store)
    ChatCLI(bot, store).run()


if __name__ == "__main__":
    main()
