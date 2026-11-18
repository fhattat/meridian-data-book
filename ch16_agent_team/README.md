# Chapter 16 — From scripts to an agent team

QR-16 · book repository: https://github.com/fhattat/meridian-data-book

**[BOOK_CODE.md](BOOK_CODE.md)**: every code block of the chapter, in book order, under the book's section headings.

## Run

From the repository root, with `export PYTHONPATH=.` (the Makefile sets it for you):

```bash
python ch16_agent_team/mcp_server.py   # pip install mcp
python ch16_agent_team/morning_agent.py --day 2027-04-15   # needs ask_llm()
python ch16_agent_team/fanout_metadata.py
python ch16_agent_team/orchestrator_agent.py "Bring the bz_returns source onto the platform"
python ch16_agent_team/build_toolkit_site.py
```

## Files

- [build_toolkit_site.py](build_toolkit_site.py)
- [fanout_metadata.py](fanout_metadata.py)
- [mcp_server.py](mcp_server.py)
- [morning_agent.py](morning_agent.py)
- [orchestrator_agent.py](orchestrator_agent.py)

All data is synthetic (see the main README).
