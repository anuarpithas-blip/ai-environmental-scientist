# AI Environmental Scientist

Darukaa.Earth — AI Biodiversity Intelligence Chatbot Challenge.

## What this project implements

- Local retrievable knowledge layer using TF-IDF vectors and cosine similarity.
- Text input.
- Structured JSON input.
- Environmental variable tracking.
- Clarifying questions for incomplete input.
- Session-based multi-turn memory.
- Multi-metric reasoning across soil, land, biodiversity, climate and human-impact groups.
- Evidence display showing the retrieved source text.
- Structured recommendations with recommendation, reasoning, impacted metrics, time horizon and confidence.

## Important source boundary

The bundled `data/challenge_knowledge.txt` is derived only from the supplied Darukaa.Earth challenge PDF.

The PDF specifies that the final system should index research papers, reports or environmental datasets. It does not provide those source documents itself. Therefore this starter project does not invent scientific studies, percentages or environmental facts.

Before final submission, add approved scientific documents/datasets to `data/` and update the retrieval/response layer so each scientific recommendation can cite those actual sources.

## Run locally

```bash
python -m venv .venv
```

Windows:
```bash
.venv\Scripts\activate
```

Install:
```bash
pip install -r requirements.txt
```

Run:
```bash
streamlit run app.py
```

## Architecture

User text/JSON
    ↓
Environmental input parser
    ↓
Local vector retrieval
    ↓
Multi-metric reasoning
    ↓
Clarifying questions when needed
    ↓
Evidence-backed recommendation
    ↓
Structured scientist response

## Submission checklist from the challenge

- GitHub repository link
- Live demo URL, where applicable
- README covering architecture, database/schema, local setup and CI/CD details
- Any required credentials/notes
- Word document submitted through the applied-job page

## Current limitation

The initial knowledge base is intentionally restricted to the supplied challenge PDF. Scientific grounding beyond that document requires adding the actual research papers, reports or environmental datasets that the challenge asks the candidate to index.
