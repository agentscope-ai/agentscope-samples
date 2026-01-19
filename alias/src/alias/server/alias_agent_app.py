# -*- coding: utf-8 -*-
from agentscope_runtime.engine.app import AgentApp

from alias.runtime.runtime_compat.runner.alias_runner import AliasRunner

PORT = 8090


def run_app(
    host: str = "127.0.0.1",
    port: int = PORT,
    web_ui: bool = False,
    chat_mode: str = "general",
) -> None:
    agent_app = AgentApp(
        runner=AliasRunner(
            default_chat_mode=chat_mode,
        ),
        app_name="Alias",
        app_description=(
            "An LLM-empowered agent built on AgentScope and AgentScope-Runtime"
        ),
    )
    agent_app.run(host=host, port=port, web_ui=web_ui)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(prog="alias_agent_runtime")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument(
        "--web-ui",
        action="store_true",
        help="Start AgentScope Runtime WebUI (default: False)",
    )
    parser.add_argument(
        "--chat-mode",
        default="general",
        choices=["general", "dr", "browser", "ds", "finance"],
        help=(
            "Default chat mode used by AliasRunner when request doesn't "
            "specify chat_mode."
        ),
    )
    args = parser.parse_args()

    print(
        "[alias_agent_runtime] config:",
        f"host={args.host}",
        f"port={args.port}",
        f"web_ui={args.web_ui}",
        f"chat_mode={args.chat_mode}",
    )

    run_app(
        host=args.host,
        port=args.port,
        web_ui=args.web_ui,
        chat_mode=args.chat_mode,
    )


if __name__ == "__main__":
    main()
