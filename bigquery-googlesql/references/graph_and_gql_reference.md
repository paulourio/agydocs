# GoogleSQL Graph Query Language (GQL) and Property Graphs Specification

This specification defines the architectural model, schema declarations, pattern matching syntax, path quantifiers, and analytical functions for property graphs in GoogleSQL and BigQuery. It details graph creation, relational data mapping, linear pattern execution, path cost metrics, and information schema introspection.

```sql
-- Canonical GoogleSQL Property Graph and GQL Pattern
CREATE OR REPLACE PROPERTY GRAPH `finance_corp.transfers_network`
  NODE TABLES (
    `finance_corp.accounts`
      KEY (account_id)
      LABEL Account
      PROPERTIES (account_id, owner_name, balance_usd)
  )
  EDGE TABLES (
    `finance_corp.wire_transfers`
      KEY (transfer_id)
      SOURCE KEY (source_account_id) REFERENCES `finance_corp.accounts` (account_id)
      DESTINATION KEY (target_account_id) REFERENCES `finance_corp.accounts` (account_id)
      LABEL Transfers
      PROPERTIES (transfer_id, transfer_amount, transfer_ts)
  );

-- Bounded multi-hop traversal evaluating transaction flows
SELECT source_name, target_name, total_hops
  FROM GRAPH_TABLE (
    `finance_corp.transfers_network`
    MATCH (src:Account)-[t:Transfers]->{1, 3}(dst:Account)
    WHERE src.account_id != dst.account_id
    RETURN src.owner_name AS source_name,
           dst.owner_name AS target_name,
           PATH_LENGTH(t) AS total_hops
  );
```

---

## 1. Graph Architecture, Working Tables, and Launch Lifecycle

BigQuery Property Graph enables graph query capabilities directly on relational tables without exporting records to external graph engines.

### 1.1 Architecture and Relational Pipeline

Property graphs function as declarative metadata abstractions layered over existing relational tables. The database does not maintain redundant graph-native data structures on Colossus. Instead, the query compiler converts graph patterns into distributed relational execution DAGs.

```text
+-----------------------------------------------------------------------------------+
| Relational Storage Layer (Capacitor Columnar Files on Colossus)                   |
| - Node Tables: Primary entity records (Customers, Accounts, Devices)              |
| - Edge Tables: Relationship foreign key tuples (Transfers, Owns, Follows)         |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| Property Graph Catalog Metadata (Declarative Graph Schemas)                       |
| - Schema validation: Keys, labels, exposed properties, edge directionality        |
| - Introspection: INFORMATION_SCHEMA.PROPERTY_GRAPHS                               |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| GQL Compiler and Execution Planner                                                |
| - Lowers MATCH patterns into Hash Joins, Broadcast Joins, and Recursive Scans     |
| - Prunes unreferenced properties using standard Capacitor columnar skip lists     |
| - Evaluates cost metrics, shortest paths, and topological cycle predicates        |
+-----------------------------------------------------------------------------------+
```

### 1.2 Feature Availability and Launch Status

Graph features operate under designated Google Cloud launch stages:
- **Preview Feature Status:** Property Graph creation (`CREATE PROPERTY GRAPH`) and the `GRAPH_TABLE` operator are in Preview. Syntax, keywords, and engine execution behaviors remain subject to backward-compatible adjustments.
- **Preview Terminology:** Graph capabilities run without separate instance provisioning. Billing tracks normal slot usage during query execution.
- **Resource Locality:** The property graph metadata object and all underlying node and edge tables must reside in identical dataset projects and regional locations.

---

## 2. Property Graph Schema Definition (`CREATE PROPERTY GRAPH`)

Engineers define property graphs using declarative Data Definition Language statements. A graph consists of one or more node tables and optional edge tables.

### 2.1 Grammar and Structural Rules

```sql
CREATE [ OR REPLACE ] PROPERTY GRAPH [ IF NOT EXISTS ] graph_name
  NODE TABLES ( node_table_element [, ...] )
  [ EDGE TABLES ( edge_table_element [, ...] ) ];
```

- **`graph_name`:** Fully qualified or relative identifier (`project.dataset.graph_name`).
- **`NODE TABLES`:** Relational tables providing entity vertex definitions.
- **`EDGE TABLES`:** Relational tables mapping directed connections from source nodes to destination nodes.

### 2.2 Node Table Element Definition

Each node element maps a relational table to a graph vertex classification:

```sql
table_name [ AS alias ]
  [ KEY ( key_column [, ...] ) ]
  [ LABEL label_name ]
  [ { PROPERTIES ( column [, ...] ) | PROPERTIES ALL COLUMNS | NO PROPERTIES } ]
```

- **`KEY`:** Identifies unique columns defining vertex identity. If omitted, the engine uses the table primary key.
- **`LABEL`:** Assigns a semantic label (such as `Account` or `Person`). If omitted, the label defaults to the table name.
- **`PROPERTIES`:** Declares columns exposed to graph pattern queries. Specifying `PROPERTIES ALL COLUMNS` exposes every column. Specifying `NO PROPERTIES` conceals all attributes.

### 2.3 Edge Table Element Definition

Edge elements link source vertex keys to destination vertex keys:

```sql
table_name [ AS alias ]
  [ KEY ( key_column [, ...] ) ]
  SOURCE KEY ( source_foreign_key [, ...] ) REFERENCES source_node_table [ ( source_node_key [, ...] ) ]
  DESTINATION KEY ( dest_foreign_key [, ...] ) REFERENCES dest_node_table [ ( dest_node_key [, ...] ) ]
  [ LABEL label_name ]
  [ { PROPERTIES ( column [, ...] ) | PROPERTIES ALL COLUMNS | NO PROPERTIES } ]
```

- **`SOURCE KEY`:** Foreign key columns identifying the originating vertex.
- **`DESTINATION KEY`:** Foreign key columns identifying the terminating vertex.
- **`REFERENCES`:** Declares the target node table element matching the source or destination endpoints.

### 2.4 Complete Financial Network Schema Example

```sql
-- bqfmt: skip
CREATE OR REPLACE PROPERTY GRAPH `finance_corp.fraud_detection_graph`
  NODE TABLES (
    `finance_corp.persons`
      KEY (person_id)
      LABEL Person
      PROPERTIES (person_id, full_name, tax_id),
    `finance_corp.bank_accounts`
      KEY (account_id)
      LABEL Account
      PROPERTIES (account_id, currency_code, opened_at)
  )
  EDGE TABLES (
    `finance_corp.account_ownership`
      KEY (ownership_id)
      SOURCE KEY (person_id) REFERENCES `finance_corp.persons` (person_id)
      DESTINATION KEY (account_id) REFERENCES `finance_corp.bank_accounts` (account_id)
      LABEL Owns
      NO PROPERTIES,
    `finance_corp.transactions_log`
      KEY (transaction_id)
      SOURCE KEY (origin_account_id) REFERENCES `finance_corp.bank_accounts` (account_id)
      DESTINATION KEY (dest_account_id) REFERENCES `finance_corp.bank_accounts` (account_id)
      LABEL Transfers
      PROPERTIES (transaction_id, amount, transfer_ts)
  );
```

### 2.5 Dropping Property Graphs

Drop statements remove graph definitions from dataset namespaces without altering underlying relational tables:

```sql
DROP PROPERTY GRAPH IF EXISTS `finance_corp.fraud_detection_graph`;
```

---

## 3. Querying Graphs in SQL: `GRAPH_TABLE` and Pipe Syntax

GoogleSQL exposes graph pattern matching through the `GRAPH_TABLE` table-valued operator. The operator executes graph logic and yields a tabular relation for downstream relational processing.

### 3.1 `GRAPH_TABLE` Syntax Structure

The `GRAPH_TABLE` operator appears directly inside the SQL `FROM` clause:

```sql
FROM GRAPH_TABLE (
  property_graph_name
  multi_linear_query_statement
) [ [ AS ] alias ]
```

Inside the operator block, engineers formulate standard GQL query statements:
- `MATCH`: Defines topological node and edge traversal patterns.
- `WHERE`: Filters paths using property expressions and graph predicates.
- `LET`: Binds intermediate calculated variables within graph traversal pipelines.
- `RETURN`: Projects graph attributes into standard relational columns.

```sql
SELECT source_user, dest_user, sent_amount
  FROM GRAPH_TABLE (
    `finance_corp.fraud_detection_graph`
    MATCH (p1:Person)-[:Owns]->(a1:Account)-[t:Transfers]->(a2:Account)<-[:Owns]-(p2:Person)
    WHERE t.amount > 50000.00
      AND p1.person_id != p2.person_id
    RETURN p1.full_name AS source_user,
           p2.full_name AS dest_user,
           t.amount     AS sent_amount
  )
 ORDER BY sent_amount DESC
 LIMIT 100;
```

### 3.2 Integration with GoogleSQL Pipe Syntax

Because `GRAPH_TABLE` evaluates to a standard relational tabular stream, engineers compose it directly within Pipe Syntax queries:

```sql
FROM GRAPH_TABLE (
  `finance_corp.fraud_detection_graph`
  MATCH (src:Account)-[t:Transfers]->(dst:Account)
  RETURN src.account_id AS src_id,
         dst.account_id AS dst_id,
         t.amount       AS amount
)
|> WHERE amount > 10000.00
|> AGGREGATE
     COUNT(*)    AS transfer_count,
     SUM(amount) AS gross_transferred
   GROUP BY src_id
|> WHERE transfer_count >= 5
|> ORDER BY gross_transferred DESC;
```

---

## 4. Pattern Matching and Graph Pattern Matching Language (GPML)

Graph Pattern Matching Language syntax models directional entities and multi-hop paths.

### 4.1 Basic Element Patterns

- **Nodes:** Enclosed in parentheses `(variable:Label {property_filters})`.
- **Edges:** Enclosed in square brackets `-[variable:Label {property_filters}]->`.
- **Directionality:**
  - Directed forward: `(a)-[e]->(b)`
  - Directed backward: `(a)<-[e]-(b)`
  - Undirected or bidirectional: `(a)-[e]-(b)`

### 4.2 Property Filter Expressions

Inline property filters declare conditions inside braces `{}`:

```sql
-- Inline equality filter
MATCH (a:Account {currency_code: 'USD', opened_at: CURRENT_DATE()})

-- Equivalent WHERE clause filter
MATCH (a:Account)
WHERE a.currency_code = 'USD' AND a.opened_at = CURRENT_DATE()
```

### 4.3 Quantified Path Patterns and Bounded Multi-Hop Traversals

Quantified path patterns match paths of variable or repeated length. Quantifiers follow subpaths or edge brackets.

| Quantifier Pattern | Repetition Range | Semantic Meaning |
| :--- | :--- | :--- |
| `-[e:Transfers]->{3}` | Exact: $3$ hops | Traverses exactly three consecutive edge steps |
| `-[e:Transfers]->{1, 5}` | Bounded: $1$ to $5$ hops | Matches paths between one and five hops |
| `-[e:Transfers]->{, 4}` | Bounded upper: $0$ to $4$ hops | Matches up to four hops (including zero-length paths) |
| `-[e:Transfers]->{2, }` | Bounded lower: $\ge 2$ hops | Matches two or more hops up to system execution limits |
| `-[e:Transfers]->+` | One or more: $\ge 1$ | Syntactic abbreviation for `{1, }` |
| `-[e:Transfers]->*` | Zero or more: $\ge 0$ | Syntactic abbreviation for `{0, }` |

```sql
-- Find accounts separated by 2 to 4 transfer hops
SELECT start_id, end_id, hop_count
  FROM GRAPH_TABLE (
    `finance_corp.fraud_detection_graph`
    MATCH (a:Account)-[t:Transfers]->{2, 4}(b:Account)
    RETURN a.account_id AS start_id,
           b.account_id AS end_id,
           PATH_LENGTH(t) AS hop_count
  );
```

### 4.4 Group Variables in Quantified Paths

When an edge or node variable is declared inside a quantified path pattern, it binds as a **group variable**. A group variable evaluates to an array containing elements gathered across the repeated traversal steps:

```sql
SELECT path_actors, transfer_chain
  FROM GRAPH_TABLE (
    `finance_corp.fraud_detection_graph`
    MATCH ((acc:Account)-[tx:Transfers]->()){1, 3}(final_acc:Account)
    RETURN ARRAY_AGG(acc.account_id) AS path_actors,
           ARRAY_AGG(tx.amount)      AS transfer_chain
  );
```

---

## 5. Path Search Prefixes and Cost Expressions

When multiple paths link two nodes, search prefixes restrict query matching to optimal or representative path instances.

### 5.1 Path Search Prefix Catalog

Engineers prefix `MATCH` statements with search modes to instruct the pathfinding engine:

| Search Prefix | Result Guarantee | Behavioral Mechanics |
| :--- | :--- | :--- |
| `ANY` | Non-deterministic single path | Returns any valid path satisfying pattern filters |
| `SHORTEST` | Minimal hop count | Evaluates path length and returns shortest instance |
| `ALL SHORTEST` | Exhaustive minimal hop set | Returns every path achieving the minimal hop count |
| `ANY SHORTEST` | Solitary minimal hop path | Returns one shortest path, breaking ties arbitrarily |
| `CHEAPEST` | Minimal cumulative cost | Returns path with lowest aggregated numeric weight |
| `ANY CHEAPEST` | Solitary minimal cost path | Returns one cheapest path, breaking ties arbitrarily |

### 5.2 Cost Expressions for Weighted Graphs

Cheapest path search modes require a declared `COST` expression inside the edge pattern:

```sql
-- Find lowest cumulative fee route between accounts within 5 hops
SELECT origin_acc, dest_acc, total_cost
  FROM GRAPH_TABLE (
    `finance_corp.fraud_detection_graph`
    MATCH ANY CHEAPEST (a:Account)-[t:Transfers COST t.amount]->{1, 5}(b:Account)
    WHERE a.account_id = 101 AND b.account_id = 999
    RETURN a.account_id AS origin_acc,
           b.account_id AS dest_acc,
           SUM(t.amount) AS total_cost
  );
```

Cost expressions must evaluate to non-negative numerical numbers (`INT64`, `FLOAT64`, or `NUMERIC`). Negative cost weights trigger execution errors.

---

## 6. Built-In GQL Functions Reference

GoogleSQL provides twelve specialized GQL functions for inspecting graph entities, extracting paths, and evaluating topologies.

### 6.1 Function Catalog Specification

| Function Signature | Return Type | Functional Description |
| :--- | :--- | :--- |
| `DESTINATION_NODE_ID(edge)` | `STRING` | Extracts unique opaque identifier of edge destination node. |
| `SOURCE_NODE_ID(edge)` | `STRING` | Extracts unique opaque identifier of edge source node. |
| `ELEMENT_ID(element)` | `STRING` | Returns unique opaque identifier for node or edge element. |
| `LABELS(element)` | `ARRAY<STRING>` | Returns list of string labels attached to graph element. |
| `PATH_FIRST(path)` | `GRAPH_ELEMENT` | Returns initial starting node element of graph path. |
| `PATH_LAST(path)` | `GRAPH_ELEMENT` | Returns terminal ending node element of graph path. |
| `PATH_LENGTH(path)` | `INT64` | Returns integer edge count traversed across graph path. |
| `NODES(path)` | `ARRAY<GRAPH_ELEMENT>` | Returns ordered array of node elements comprising path. |
| `EDGES(path)` | `ARRAY<GRAPH_ELEMENT>` | Returns ordered array of edge elements comprising path. |
| `IS_ACYCLIC(path)` | `BOOL` | Returns `TRUE` if path contains zero repeated node elements. |
| `IS_SIMPLE(path)` | `BOOL` | Synonym for `IS_ACYCLIC`; asserts no node repeats. |
| `IS_TRAIL(path)` | `BOOL` | Returns `TRUE` if path contains zero repeated edge elements. |

### 6.2 Path Inspection Examples

```sql
SELECT path_length, is_cycle_free, first_node, last_node
  FROM GRAPH_TABLE (
    `finance_corp.transfers_network`
    MATCH p = (a:Account)-[t:Transfers]->{1, 4}(b:Account)
    WHERE a.account_id = 5001
    RETURN PATH_LENGTH(p)                AS path_length,
           IS_ACYCLIC(p)                 AS is_cycle_free,
           ELEMENT_ID(PATH_FIRST(p))     AS first_node,
           ELEMENT_ID(PATH_LAST(p))      AS last_node
  );
```

---

## 7. Graph Predicates and Logical Operators

Graph predicates evaluate topological constraints across pattern variables.

### 7.1 Graph Predicates Specification

| Predicate Syntax | Evaluation Type | Behavioral Rules |
| :--- | :--- | :--- |
| `ALL_DIFFERENT(e1, e2, ...)` | `BOOL` | Confirms all arguments bind to distinct graph elements. Throws error if any element evaluates to `NULL`. |
| `node IS [NOT] SOURCE OF edge` | `BOOL` | Tests whether node element represents origin of edge. |
| `node IS [NOT] DESTINATION OF edge`| `BOOL` | Tests whether node element represents termination of edge. |
| `SAME(e1, e2, ...)` | `BOOL` | Asserts that listed elements bind to identical node or edge. |

```sql
-- Detect circular wash trading between accounts
SELECT a1_id, a2_id, a3_id
  FROM GRAPH_TABLE (
    `finance_corp.fraud_detection_graph`
    MATCH (a1:Account)-[t1:Transfers]->(a2:Account)-[t2:Transfers]->(a3:Account)-[t3:Transfers]->(a1)
    WHERE ALL_DIFFERENT(t1, t2, t3)
      AND ALL_DIFFERENT(a1, a2, a3)
    RETURN a1.account_id AS a1_id,
           a2.account_id AS a2_id,
           a3.account_id AS a3_id
  );
```

### 7.2 Label Logical Expressions

Within node and edge pattern labels, GoogleSQL supports compact logical operators:
- **`&` (AND):** Matches vertices having both labels (`(n:Customer & Borrower)`).
- **`|` (OR):** Matches vertices having either label (`(n:Person | Corporation)`).
- **`!` (NOT):** Matches vertices lacking designated label (`(n:Account & !Blocked)`).

---

## 8. Relational Flattening: `GRAPH_EXPAND` and Schema Introspection

For operational pipelines requiring automated flattened denormalization, BigQuery provides the `GRAPH_EXPAND` Table-Valued Function and administrative procedures.

### 8.1 The `GRAPH_EXPAND` TVF

The `GRAPH_EXPAND` function flattens hierarchical graph definitions into a denormalized relational table using automated `LEFT JOIN` operations across node and edge schemas:

```sql
SELECT *
  FROM GRAPH_EXPAND('finance_corp.fraud_detection_graph');
```

Output column names derive from `<Label>_<property_name>` (for example, `Person_full_name`, `Account_currency_code`).

### 8.2 Inspecting Expanded Schema with `BQ.SHOW_GRAPH_EXPAND_SCHEMA`

Engineers inspect the dynamically derived schema of an expanded graph before running queries:

```sql
DECLARE expanded_schema_json STRING;
CALL BQ.SHOW_GRAPH_EXPAND_SCHEMA(
  'finance_corp.fraud_detection_graph',
  expanded_schema_json
);
SELECT expanded_schema_json;
```

---

## 9. System Catalog Auditing (`INFORMATION_SCHEMA.PROPERTY_GRAPHS`)

Query `INFORMATION_SCHEMA.PROPERTY_GRAPHS` to inspect graph catalog definitions and active states:

```sql
SELECT property_graph_name,
       property_graph_catalog,
       property_graph_schema,
       last_modified_time
  FROM `finance_corp.INFORMATION_SCHEMA.PROPERTY_GRAPHS`
 WHERE property_graph_name = 'fraud_detection_graph';
```

---

## 10. Graph Engineering Anti-Patterns and Execution Safeguards

Graph queries generate intense compute loads when queries lack bounds. Engineers must observe these safeguards:

- **Unbounded Multi-Hop Traversal:** Executing `-[e:Transfers]->*` without an upper bound invites exponential graph explosion. Always declare explicit upper bounds (such as `{1, 4}`).
- **Cartesian Disconnected Matching:** Writing disconnected match patterns (`MATCH (a:Account), (b:Person)`) generates full Cartesian products between entity populations.
- **Bare Projection of Graph Elements:** Selecting bare graph elements (`RETURN p`) causes serialization overhead. Project explicit primitive scalar attributes (`RETURN a.account_id, t.amount`).
- **Null Safety in Property Filters:** Property filters like `{status: NULL}` do not evaluate standard SQL null comparisons. Formulate explicit `WHERE element.property IS NULL` filters instead.

---

## 11. Related References and Operational Tooling

- **Executable SQL Patterns:** Inspect [Graph and GQL Patterns](../examples/graph_and_gql_patterns.sql) for runnable graph traversal examples.
- **Pipe Syntax Guide:** Consult [Pipe Query Syntax Reference](pipe_syntax.md) for streaming dataflow integration.
- **DDL Specifications:** Consult [DDL Reference](ddl_reference.md) for dataset and table definitions.
- **Anti-Patterns Catalog:** Consult [Anti-Patterns Catalog](../resources/anti_patterns_catalog.md) for query performance hazards.
