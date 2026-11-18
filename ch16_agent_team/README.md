# Bölüm 16 — Script’ten agent ekibine
### Chapter 16 — From scripts to an agent team

QR-16 · Kitabın deposu / book repository: https://github.com/fhattat/meridian-data-book

**[BOOK_CODE.md](BOOK_CODE.md)**: bölümdeki bütün kodlar, kitaptaki sırası ve alt bölüm başlıklarıyla / every code block of the chapter in book order.

## Çalıştırma / Run

Depo kökünden, `export PYTHONPATH=.` ile (Makefile bunu kendisi yapar) / from the repository root:

```bash
python ch16_agent_team/mcp_server.py   # pip install mcp
python ch16_agent_team/morning_agent.py --day 2027-04-15   # needs ask_llm()
python ch16_agent_team/fanout_metadata.py
python ch16_agent_team/orchestrator_agent.py "Bring the bz_returns source onto the platform"
python ch16_agent_team/build_toolkit_site.py
```

## Dosyalar / Files

- [build_toolkit_site.py](build_toolkit_site.py)
- [fanout_metadata.py](fanout_metadata.py)
- [mcp_server.py](mcp_server.py)
- [morning_agent.py](morning_agent.py)
- [orchestrator_agent.py](orchestrator_agent.py)

Veri sentetiktir / all data is synthetic (see the main README).
