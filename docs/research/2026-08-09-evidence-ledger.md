# Evidence Ledger — 2026-08-09

**Scope:** broad architecture validation for the durable knowledge graph.

**Method note:** This ledger intentionally favors primary sources: official product/database documentation, standards bodies, original repositories, and original research papers. Inclusion means the source informed the comparison; it does **not** mean every claim made by the source is accepted. Vendor benchmark claims are treated as vendor claims unless independently replicated.

**Source count:** 127

## Source-quality rules used

- Standards/specification questions: standards body or official protocol specification first.
- Database behavior/limits: official database documentation first.
- Open-source implementation behavior: project documentation/repository/issues/releases first.
- Research claims: original paper/preprint first; replication status recorded separately when used as evidence.
- Vendor benchmark numbers are not treated as independent evidence merely because they are precise.
- New/preprint work is used to plan extension points, not to anchor the durable source-of-truth contract.

## Ledger

### Graphiti / Zep

1. [Graphiti repository](https://github.com/getzep/graphiti)
2. [Graphiti graph namespacing](https://help.getzep.com/graphiti/core-concepts/graph-namespacing)
3. [Graphiti custom entity and edge types](https://help.getzep.com/graphiti/core-concepts/custom-entity-and-edge-types)
4. [Graphiti MCP server README](https://github.com/getzep/graphiti/blob/main/mcp_server/README.md)
5. [Zep repository](https://github.com/getzep/zep)
6. [Graphiti documentation home](https://help.getzep.com/graphiti/)
7. [Graphiti getting started overview](https://help.getzep.com/graphiti/getting-started/overview)
8. [Graphiti adding episodes](https://help.getzep.com/graphiti/core-concepts/adding-episodes)
9. [Graphiti search](https://help.getzep.com/graphiti/core-concepts/search)
10. [Graphiti GitHub issues](https://github.com/getzep/graphiti/issues)

### Neo4j

11. [Neo4j Operations Manual](https://neo4j.com/docs/operations-manual/current/)
12. [Backup and restore](https://neo4j.com/docs/operations-manual/current/backup-restore/)
13. [Offline backup / dump](https://neo4j.com/docs/operations-manual/current/backup-restore/offline-backup/)
14. [Restore backup](https://neo4j.com/docs/operations-manual/current/backup-restore/restore-backup/)
15. [Database administration](https://neo4j.com/docs/operations-manual/current/database-administration/)
16. [Neo4j migration guide](https://neo4j.com/docs/upgrade-migration-guide/current/)
17. [Cypher constraints](https://neo4j.com/docs/cypher-manual/current/constraints/)
18. [Cypher indexes](https://neo4j.com/docs/cypher-manual/current/indexes/)
19. [Full-text indexes](https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/full-text-indexes/)
20. [Vector indexes](https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/vector-indexes/)
21. [Composite databases](https://neo4j.com/docs/operations-manual/current/database-administration/composite-databases/)
22. [Neo4j Graph Data Science manual](https://neo4j.com/docs/graph-data-science/current/)

### PostgreSQL / pgvector / Citus

23. [PostgreSQL documentation](https://www.postgresql.org/docs/current/)
24. [PostgreSQL full-text search](https://www.postgresql.org/docs/current/textsearch.html)
25. [PostgreSQL text-search indexes](https://www.postgresql.org/docs/current/textsearch-indexes.html)
26. [PostgreSQL partitioning](https://www.postgresql.org/docs/current/ddl-partitioning.html)
27. [PostgreSQL row security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
28. [PostgreSQL logical replication](https://www.postgresql.org/docs/current/logical-replication.html)
29. [PostgreSQL continuous archiving / PITR](https://www.postgresql.org/docs/current/continuous-archiving.html)
30. [pgvector repository](https://github.com/pgvector/pgvector)
31. [Citus documentation](https://docs.citusdata.com/)
32. [Citus data modeling](https://docs.citusdata.com/en/stable/sharding/data_modeling.html)
33. [Citus multi-tenant tutorial](https://docs.citusdata.com/en/stable/get_started/tutorial_multi_tenant.html)
34. [PostgREST documentation](https://postgrest.org/en/stable/)
35. [PostgREST database authorization](https://postgrest.org/en/stable/explanations/db_authz.html)
36. [PostgREST schema isolation](https://postgrest.org/en/stable/references/api/schemas.html)

### Supabase

37. [Supabase self-hosting](https://supabase.com/docs/guides/self-hosting)
38. [Supabase Docker self-hosting](https://supabase.com/docs/guides/self-hosting/docker)
39. [Supabase row-level security](https://supabase.com/docs/guides/database/postgres/row-level-security)
40. [Supabase Auth](https://supabase.com/docs/guides/auth)
41. [Supabase JWTs](https://supabase.com/docs/guides/auth/jwts)
42. [Supabase vector columns](https://supabase.com/docs/guides/ai/vector-columns)
43. [Supabase hybrid search](https://supabase.com/docs/guides/ai/hybrid-search)

### Qdrant

44. [Qdrant documentation](https://qdrant.tech/documentation/)
45. [Qdrant multitenancy](https://qdrant.tech/documentation/guides/multiple-partitions/)
46. [Qdrant distributed deployment](https://qdrant.tech/documentation/guides/distributed_deployment/)
47. [Qdrant collections](https://qdrant.tech/documentation/concepts/collections/)
48. [Qdrant filtering](https://qdrant.tech/documentation/concepts/filtering/)
49. [Qdrant payload](https://qdrant.tech/documentation/concepts/payload/)
50. [Qdrant indexing](https://qdrant.tech/documentation/concepts/indexing/)
51. [Qdrant snapshots](https://qdrant.tech/documentation/concepts/snapshots/)

### Milvus

52. [Milvus multi-tenancy](https://milvus.io/docs/multi_tenancy.md)
53. [Milvus partition key](https://milvus.io/docs/use-partition-key.md)
54. [Milvus partitions](https://milvus.io/docs/manage-partitions.md)
55. [Milvus resource groups](https://milvus.io/docs/resource_group.md)
56. [Milvus architecture overview](https://milvus.io/docs/architecture_overview.md)
57. [Milvus backup](https://milvus.io/docs/backup_restore.md)

### Weaviate

58. [Weaviate multi-tenancy](https://docs.weaviate.io/weaviate/manage-collections/multi-tenancy)
59. [Weaviate hybrid search](https://docs.weaviate.io/weaviate/search/hybrid)
60. [Weaviate BM25](https://docs.weaviate.io/weaviate/search/bm25)
61. [Weaviate filters](https://docs.weaviate.io/weaviate/search/filters)
62. [Weaviate replication architecture](https://docs.weaviate.io/weaviate/concepts/replication-architecture/consistency)
63. [Weaviate tenant states](https://docs.weaviate.io/weaviate/manage-collections/multi-tenancy#tenant-states)
64. [Weaviate collections](https://docs.weaviate.io/weaviate/manage-collections)
65. [Weaviate backups](https://docs.weaviate.io/deploy/configuration/backups)

### Semantic web / provenance standards

66. [W3C PROV-O](https://www.w3.org/TR/prov-o/)
67. [W3C PROV Primer](https://www.w3.org/TR/prov-primer/)
68. [W3C PROV Links](https://www.w3.org/TR/prov-links/)
69. [W3C RDF 1.2 Concepts](https://www.w3.org/TR/rdf12-concepts/)
70. [W3C RDF 1.2 Semantics](https://www.w3.org/TR/rdf12-semantics/)
71. [W3C RDF Schema 1.1](https://www.w3.org/TR/rdf-schema/)
72. [W3C SKOS Reference](https://www.w3.org/TR/skos-reference/)
73. [W3C OWL 2 Overview](https://www.w3.org/TR/owl2-overview/)
74. [W3C OWL 2 Structural Specification](https://www.w3.org/TR/owl2-syntax/)
75. [W3C SHACL 1.2 Core](https://www.w3.org/TR/shacl12-core/)
76. [Apache Jena](https://jena.apache.org/)
77. [Apache Jena Fuseki](https://jena.apache.org/documentation/fuseki2/)
78. [RDFLib documentation](https://rdflib.readthedocs.io/en/stable/)
79. [pySHACL repository](https://github.com/RDFLib/pySHACL)
80. [Oxigraph](https://github.com/oxigraph/oxigraph)

### Portable schemas / events

81. [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12)
82. [JSON Schema specification](https://json-schema.org/specification)
83. [CloudEvents repository/spec](https://github.com/cloudevents/spec)
84. [CloudEvents site](https://cloudevents.io/)
85. [CloudEvents Primer](https://github.com/cloudevents/spec/blob/main/cloudevents/primer.md)
86. [CloudEvents JSON format](https://github.com/cloudevents/spec/blob/main/cloudevents/formats/json-format.md)

### Harness / context / agent protocols

87. [OpenAI Harness engineering](https://openai.com/index/harness-engineering/)
88. [OpenAI Codex](https://openai.com/codex/)
89. [OpenAI Symphony](https://openai.com/index/open-source-codex-orchestration-symphony/)
90. [Anthropic effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
91. [Anthropic effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
92. [Anthropic building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
93. [Anthropic contextual retrieval](https://www.anthropic.com/engineering/contextual-retrieval)
94. [MCP specification 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28)
95. [MCP server tools specification](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)
96. [MCP build server guide](https://modelcontextprotocol.io/docs/develop/build-server)
97. [MCP TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk)
98. [Agent Skills specification](https://agentskills.io/)
99. [Agent Skills repository](https://github.com/agentskills/agentskills)
100. [OpenAI Codex Skills documentation](https://developers.openai.com/codex/skills/)

### Memory / GraphRAG / RAG research

101. [MemGPT paper](https://arxiv.org/abs/2310.08560)
102. [Letta repository](https://github.com/letta-ai/letta)
103. [Letta documentation](https://docs.letta.com/)
104. [Mem0 repository](https://github.com/mem0ai/mem0)
105. [HippoRAG paper](https://arxiv.org/abs/2405.14831)
106. [HippoRAG repository](https://github.com/OSU-NLP-Group/HippoRAG)
107. [Microsoft GraphRAG repository](https://github.com/microsoft/graphrag)
108. [Microsoft GraphRAG documentation](https://microsoft.github.io/graphrag/)
109. [LightRAG paper](https://arxiv.org/abs/2410.05779)
110. [LightRAG repository](https://github.com/HKUDS/LightRAG)
111. [Original RAG paper](https://arxiv.org/abs/2005.11401)
112. [FLARE active retrieval](https://arxiv.org/abs/2305.06983)

### Local retrieval / embeddings

113. [Model2Vec repository](https://github.com/MinishLab/model2vec)
114. [MinishLab organization](https://github.com/MinishLab)
115. [FastEmbed repository](https://github.com/qdrant/fastembed)
116. [BGE-M3 paper](https://arxiv.org/abs/2402.03216)
117. [FlagEmbedding repository](https://github.com/FlagOpen/FlagEmbedding)
118. [ColBERTv2 paper](https://arxiv.org/abs/2112.01488)
119. [ColBERT repository](https://github.com/stanford-futuredata/ColBERT)

### Long context / serving

120. [Kimi Linear paper](https://arxiv.org/abs/2510.26692)
121. [Kimi Linear repository](https://github.com/MoonshotAI/Kimi-Linear)
122. [MoBA paper](https://arxiv.org/abs/2502.13189)
123. [Mooncake paper](https://arxiv.org/abs/2407.00079)
124. [Mooncake repository](https://github.com/kvcache-ai/Mooncake)

### Truth maintenance / evolving knowledge

125. [Doyle — A Truth Maintenance System (MIT)](https://dspace.mit.edu/handle/1721.1/6951)
126. [de Kleer — An Assumption-based TMS](https://www.sciencedirect.com/science/article/pii/0004370286900809)
127. [Know-Evolve temporal KG paper](https://arxiv.org/abs/1705.05742)
