# TetherLens

A consistent challenge in tool tethering is that workers in the field often do not know **what needs to be secured, how a particular tool should be tethered, or what type of tethering equipment is appropriate for it**.

Manufacturers currently address this knowledge gap through initiatives such as posters, product selectors and formal training. These can be useful for safety managers and program leads, but they are less suited to the field-based worker who encounters an unfamiliar tool or situation while carrying out the work.

**TetherLens is an AI-powered tool tethering assistant designed for use in the field.**

The intended experience is simple: a worker photographs a tool using their phone, TetherLens identifies or narrows down the tool and its relevant characteristics, and then provides guidance on the tethering requirements for that tool.

TetherLens combines:

* **Computer vision** to identify tools and observable characteristics from photographs.
* A **verified tool database** containing manufacturer specifications and other relevant technical data.
* A structured **tethering knowledge base and rules engine** describing suitable attachment, tether, anchoring and containment requirements.
* A mobile-first interface designed to minimise the amount of information a worker must manually enter.

A core design principle is:

> **AI identifies. Verified data and engineering rules determine the recommendation.**

TetherLens is initially intended as a guidance and specification tool rather than an e-commerce platform or automated safety certification system.

## Project status

For the current ingestion implementation state, latest benchmark result, known gaps and next workstreams, see [`project-status.md`](project-status.md).

## Development workflow

Documentation is part of the definition of done for every pull request. **Every PR must include, at minimum, an update to [`project-status.md`](project-status.md)** so the operational handoff reflects the code that is actually being merged. PRs that materially change durable architecture, evidence semantics or recommendation behavior should also update the relevant design document(s).
