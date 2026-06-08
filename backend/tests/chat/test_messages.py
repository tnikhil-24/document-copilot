from app.chat.messages import ChatTurnMessage, UIMessage, UIMessagePart, to_internal, to_ui_message


class TestToInternal:
    def test_flattens_text_parts_into_plain_text(self) -> None:
        message = UIMessage(
            id="msg-1",
            role="user",
            parts=[
                UIMessagePart(type="text", text="What did "),
                UIMessagePart(type="text", text="Netflix's 2023 10-K say about content costs?"),
            ],
        )

        assert to_internal(message) == ChatTurnMessage(
            role="user", text="What did Netflix's 2023 10-K say about content costs?"
        )


class TestToUIMessage:
    def test_wraps_plain_text_in_a_single_text_part(self) -> None:
        message = ChatTurnMessage(role="assistant", text="Here's what the filing says.")

        assert to_ui_message(message, message_id="msg-2") == UIMessage(
            id="msg-2",
            role="assistant",
            parts=[UIMessagePart(type="text", text="Here's what the filing says.")],
        )


class TestRoundTrip:
    def test_ui_message_survives_internal_and_back(self) -> None:
        original = UIMessage(id="msg-3", role="user", parts=[UIMessagePart(type="text", text="Hello there")])

        assert to_ui_message(to_internal(original), message_id=original.id) == original

    def test_internal_message_survives_ui_and_back(self) -> None:
        original = ChatTurnMessage(role="assistant", text="Hi — how can I help you today?")

        assert to_internal(to_ui_message(original, message_id="msg-4")) == original
