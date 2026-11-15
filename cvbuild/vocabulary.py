"""The technologies a job description is likely to name, and whole-term matching against them.

The vocabulary serves two checks: comparing a job description with a CV, and catching a reworded
bullet that names a technology the master profile does not contain.
"""

from __future__ import annotations

import re

# Each entry is "Canonical: alias, alias". Entries are separated by semicolons or new lines.
_VOCAB = """
Java; JavaScript: JS; TypeScript: TS; Python; C++; C#: CSharp; C; Go: Golang; Rust; Kotlin; Swift; PHP; Ruby; Scala; SQL; Bash: shell scripting
Spring Boot: SpringBoot, Spring; Spring MVC; Java EE: Jakarta EE, J2EE; Hibernate: JPA; Maven; Gradle; JUnit; Mockito
Node.js: NodeJS, Node; NestJS: Nest.js; Express: Express.js; FastAPI; Django; Flask; .NET: dotnet, ASP.NET; Laravel; Rails
REST: RESTful; GraphQL; gRPC; WebSocket: WebSockets; WebRTC; microservices: microservice, micro-services; event-driven; serverless
PostgreSQL: Postgres; MySQL; MongoDB; Redis; DynamoDB; Cassandra; Elasticsearch; SQLite; Oracle; SQL Server; Snowflake; BigQuery
RabbitMQ; Kafka; SQS; SNS; Pub/Sub; Celery
TypeORM; Sequelize; Prisma; Drizzle
AWS: Amazon Web Services; Azure; GCP: Google Cloud; Lambda; ECS; EKS; EC2; S3; RDS; CloudWatch; IAM; CloudFormation; CDK
Docker; Kubernetes: K8s; Helm; Terraform; Ansible; Nginx; Linux; OpenShift; Podman
CI/CD: continuous integration, continuous delivery; GitHub Actions; GitLab CI: GitLab CI/CD; Jenkins; ArgoCD; Git
Prometheus; Grafana; Datadog; OpenTelemetry; ELK
React; React Native; Next.js: NextJS; Angular; Vue: Vue.js; Svelte; Redux; Tailwind: Tailwind CSS; HTML; CSS; Expo
PyTorch; TensorFlow; scikit-learn; Hugging Face: Transformers; LangChain; LlamaIndex; OpenAI; Gemini; Claude; Bedrock
LLM: LLMs, large language model, large language models; RAG: retrieval-augmented; embeddings: vector database, vector store; fine-tuning; NLP; computer vision; MLOps; agents: multi-agent, agentic
JWT; OAuth: OAuth2, OAuth 2.0; RBAC; SSO; TLS; OWASP; encryption
Jest; pytest; Postman; Cypress; Playwright; Selenium; TDD: test-driven; unit testing: unit tests; integration testing: integration tests
Agile; Scrum; Jira; system design; distributed systems; data structures; algorithms; OOP: object-oriented; design patterns; caching; concurrency; multithreading; scalability; high availability; observability; Stripe; payments
"""


def _parse(source: str) -> dict[str, list[str]]:
    vocabulary: dict[str, list[str]] = {}
    for chunk in source.replace("\n", ";").split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        name, _, aliases = chunk.partition(":")
        name = name.strip()
        vocabulary[name] = [name, *[a.strip() for a in aliases.split(",") if a.strip()]]
    return vocabulary


VOCAB = _parse(_VOCAB)


def has_term(text: str, term: str) -> bool:
    """Whole-term match. Short terms (Go, C, AWS) are case-sensitive so ordinary words do not match."""
    flags = 0 if len(term) <= 3 else re.IGNORECASE
    pattern = r"(?<![A-Za-z0-9.])" + re.escape(term) + r"(?![A-Za-z0-9+#])"
    return re.search(pattern, text, flags) is not None


def terms_in(text: str, extra: list[str] | None = None) -> set[str]:
    """The canonical vocabulary terms found in `text`, plus any of `extra` that appear in it."""
    found = {name for name, aliases in VOCAB.items() if any(has_term(text, alias) for alias in aliases)}
    found.update(keyword for keyword in extra or [] if has_term(text, keyword))
    return found
