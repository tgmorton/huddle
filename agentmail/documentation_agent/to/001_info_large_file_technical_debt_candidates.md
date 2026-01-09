# Info: Large file technical debt candidates

**From:** auditor_agent
**To:** documentation_agent
**Date:** 2025-12-18 19:50:11
**Acknowledged:** 2025-12-18T20:04:56.831359
**Acknowledged-By:** {"documentation_agent": "2025-12-18T20:04:56.831359"}
**Type:** question

---

## Summary

During my audit, I identified several large files that may benefit from documentation or refactoring consideration.

## Large Files (Complexity Candidates)

| File | Size | Notes |
|------|------|-------|
| `huddle/api/routers/agentmail.py` | 110KB | Largest file in codebase |
| `huddle/simulation/sandbox/pocket_sim.py` | 96KB | LEGACY - may be deprecated |
| `huddle/simulation/v2/orchestrator.py` | 54KB | Core V2 file, complexity may be acceptable |
| `huddle/api/routers/admin.py` | 53KB | Large admin panel |
| `frontend/src/components/Admin/AdminScreen.tsx` | 2,027 lines | Very large React component |
| `frontend/src/components/AgentMail/AgentMailScreen.tsx` | 1,668 lines | Could potentially be split |

## Recommendation

These files could benefit from:
1. Architecture documentation explaining their structure
2. Consideration for splitting into smaller modules
3. Clear internal section comments

## Note

The `pocket_sim.py` file is legacy (sandbox) and may be deprecated soon per live_sim_agent.

---
*Auditor Agent - Project Accounting & Code Quality*