"""Journalism deep-research benchmark.

A small, public, reproducible benchmark for what newsrooms actually care
about in a research agent: did it reach the primary source, and did it
surface the key fact correctly. Two checks per case, scored against a
human-authored answer key, run identically across every agent.

Self-contained: depends only on `pydantic-evals` plus each agent's SDK.
The Velora adapter is the one file that reaches into this repo's `src/`,
and it drops out cleanly when the agent isn't importable.
"""
