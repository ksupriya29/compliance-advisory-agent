# ⚖️ Compliance Advisory & Triage Agent

An AI-powered compliance assistant that provides **policy-grounded answers** using Retrieval-Augmented Generation (RAG), risk-based triage, and human-in-the-loop escalation.

The system helps organizations handle compliance queries safely by ensuring responses are generated **only from approved internal policy documents** and automatically escalating high-risk issues to human reviewers.

---

## 🚀 Features

### 📚 Policy-Grounded AI Responses

* Uses internal compliance documents as the only source of information.
* Prevents AI hallucination by refusing to answer when no relevant policy information is found.
* Provides transparent and reliable compliance guidance.

### 🔍 Retrieval-Augmented Generation (RAG)

* Documents are processed and converted into searchable embeddings.
* User queries retrieve relevant policy sections.
* LLM generates responses based on retrieved context.

### ⚠️ Risk-Based Triage

The system classifies queries based on compliance risk:

| Risk Level | Action                               |
| ---------- | ------------------------------------ |
| Low        | Generate AI response                 |
| Medium     | Review policy context                |
| High       | Escalate to human compliance officer |

### 👥 Human-in-the-Loop Escalation

High-risk questions are automatically routed for manual review.

Examples:

* GDPR data breaches
* Customer PII handling
* Legal compliance decisions
* Employment law questions

### 📋 Audit Logging

Every interaction is recorded with:

* Query
* Response status
* Risk level
* Escalation decision
* Unique audit ID

---

## 🏗️ Architecture

```
                User Query
                    |
                    ▼
          Compliance Risk Classifier
                    |
                    ▼
          Retrieve Relevant Policies
                    |
                    ▼
             RAG Pipeline
                    |
                    ▼
             Llama 3.2 LLM
                    |
          ┌─────────┴─────────┐
          ▼                   ▼
     Safe Response       Human Review
                              |
                              ▼
                         Audit Log
```

---

## 🛠️ Tech Stack

### AI / LLM

* Llama 3.2
* Retrieval-Augmented Generation (RAG)

### Backend

* Python
* LangChain
* Vector Database

### Frontend

* Streamlit

### Data Processing

* PDF/DOCX policy document ingestion
* Text chunking
* Embeddings

### Storage

* Vector store for document retrieval
* Audit logs

---

## 📂 Project Structure

```
compliance-triage-agent/
│
├── app.py                 # Streamlit application
├── requirements.txt       # Dependencies
├── README.md
│
├── src/
│   ├── ingest.py          # Document ingestion pipeline
│   ├── retrieve.py        # Policy retrieval logic
│   ├── governance.py      # Risk classification & escalation
│
├── data/
│   └── policies/          # Internal compliance documents
│
└── logs/
    └── audit logs
```

---

## ⚙️ Installation

### Clone Repository

```bash
git clone https://github.com/ksupriya29/compliance-advisory-agent.git

cd compliance-advisory-agent
```

### Create Virtual Environment

```bash
python -m venv venv
```

Activate:

Windows:

```bash
venv\Scripts\activate
```

Linux/Mac:

```bash
source venv/bin/activate
```

---

## 📦 Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 🔑 Environment Variables

Create a `.env` file:

```
LLM_API_KEY=your_api_key_here
```

Never commit API keys to GitHub.

---

## 📄 Ingest Policy Documents

Run the ingestion pipeline:

```bash
python src/ingest.py
```

This will:

* Load compliance documents
* Split text into chunks
* Generate embeddings
* Store them in the vector database

---

## ▶️ Run Application

Start the Streamlit application:

```bash
streamlit run app.py
```

Open:

```
http://localhost:8501
```

---

## 💬 Example Queries

### Answered Queries

```
What is the password policy?
```

```
How should employees report security incidents?
```

---

### Escalated Queries

```
How should we handle a GDPR data breach?
```

```
Can we share customer PII with a marketing vendor?
```

---

## 🔒 Security Design Principles

* No unsupported compliance advice
* No external knowledge used for answers
* Human approval for high-risk cases
* Complete audit trail
* Secure handling of confidential policies

---

## 🎯 Use Cases

* Enterprise compliance teams
* Data protection offices
* HR compliance
* Information security teams
* Legal operations

---

## 🔮 Future Enhancements

* Role-based authentication
* Reviewer dashboard
* Email notifications for escalations
* Multi-document policy management
* Cloud deployment
* Advanced compliance analytics

---

## 👩‍💻 Author

**Supriya K**
Computer Science Engineering Student

---

## 📜 License

This project is for educational and demonstration purposes.
