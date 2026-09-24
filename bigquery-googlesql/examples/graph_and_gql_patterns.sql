-- bqfmt: skip
-- ============================================================================
-- GoogleSQL Property Graphs and Graph Query Language (GQL) Patterns
--
-- This script provides production patterns for declaring property graphs,
-- querying topological paths using GRAPH_TABLE, performing bounded multi-hop
-- traversals, calculating weighted shortest paths, filtering cycles, and
-- integrating graph pattern matches directly into Pipe Syntax pipelines.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Base Relational Schema Setup
-- ----------------------------------------------------------------------------

CREATE SCHEMA IF NOT EXISTS `finance_network_02_str`
OPTIONS (
  location      = 'us-east4',
  description   = 'Financial graph relational working tables'
);

-- Customers Node Table
CREATE OR REPLACE TABLE `finance_network_02_str.customers`
(
  customer_id INT64 NOT NULL,
  full_name   STRING NOT NULL,
  city_name   STRING,
  tax_id      STRING,
  PRIMARY KEY (customer_id) NOT ENFORCED
);

-- Accounts Node Table
CREATE OR REPLACE TABLE `finance_network_02_str.accounts`
(
  account_id    INT64 NOT NULL,
  account_type  STRING NOT NULL,
  balance_usd   NUMERIC(14, 2) NOT NULL,
  is_blocked    BOOL NOT NULL,
  PRIMARY KEY (account_id) NOT ENFORCED
);

-- Account Ownership Edge Table
CREATE OR REPLACE TABLE `finance_network_02_str.account_ownership`
(
  ownership_id INT64 NOT NULL,
  customer_id  INT64 NOT NULL,
  account_id   INT64 NOT NULL,
  assigned_ts  TIMESTAMP NOT NULL,
  PRIMARY KEY (ownership_id) NOT ENFORCED,
  CONSTRAINT fk_customer FOREIGN KEY (customer_id) REFERENCES `finance_network_02_str.customers` (customer_id) NOT ENFORCED,
  CONSTRAINT fk_account FOREIGN KEY (account_id) REFERENCES `finance_network_02_str.accounts` (account_id) NOT ENFORCED
);

-- Transfers Edge Table
CREATE OR REPLACE TABLE `finance_network_02_str.transfers`
(
  transfer_id   INT64 NOT NULL,
  src_acct_id   INT64 NOT NULL,
  dst_acct_id   INT64 NOT NULL,
  transfer_amt  NUMERIC(14, 2) NOT NULL,
  transfer_ts   TIMESTAMP NOT NULL,
  PRIMARY KEY (transfer_id) NOT ENFORCED,
  CONSTRAINT fk_src FOREIGN KEY (src_acct_id) REFERENCES `finance_network_02_str.accounts` (account_id) NOT ENFORCED,
  CONSTRAINT fk_dst FOREIGN KEY (dst_acct_id) REFERENCES `finance_network_02_str.accounts` (account_id) NOT ENFORCED
);

-- ----------------------------------------------------------------------------
-- 2. Property Graph DDL Declaration
-- ----------------------------------------------------------------------------

CREATE OR REPLACE PROPERTY GRAPH `finance_network_02_str.FinGraph`
  NODE TABLES (
    `finance_network_02_str.customers`
      KEY (customer_id)
      LABEL Customer
      PROPERTIES (customer_id, full_name, city_name),
    `finance_network_02_str.accounts`
      KEY (account_id)
      LABEL Account
      PROPERTIES (account_id, account_type, balance_usd, is_blocked)
  )
  EDGE TABLES (
    `finance_network_02_str.account_ownership`
      KEY (ownership_id)
      SOURCE KEY (customer_id) REFERENCES `finance_network_02_str.customers` (customer_id)
      DESTINATION KEY (account_id) REFERENCES `finance_network_02_str.accounts` (account_id)
      LABEL Owns
      NO PROPERTIES,
    `finance_network_02_str.transfers`
      KEY (transfer_id)
      SOURCE KEY (src_acct_id) REFERENCES `finance_network_02_str.accounts` (account_id)
      DESTINATION KEY (dst_acct_id) REFERENCES `finance_network_02_str.accounts` (account_id)
      LABEL Transfers
      PROPERTIES (transfer_id, transfer_amt, transfer_ts)
  );

-- ----------------------------------------------------------------------------
-- 3. Basic Pattern Matching with GRAPH_TABLE
-- ----------------------------------------------------------------------------

-- Identify direct account-to-account transfers above 10,000 USD
SELECT src_id, dst_id, amount, transfer_ts
  FROM GRAPH_TABLE (
    `finance_network_02_str.FinGraph`
    MATCH (src:Account)-[t:Transfers]->(dst:Account)
    WHERE t.transfer_amt >= 10000.00
      AND src.account_id != dst.account_id
    RETURN src.account_id  AS src_id,
           dst.account_id  AS dst_id,
           t.transfer_amt  AS amount,
           t.transfer_ts   AS transfer_ts
  )
 ORDER BY amount DESC
 LIMIT 50;

-- ----------------------------------------------------------------------------
-- 4. Bounded Multi-Hop Traversals and Path Functions
-- ----------------------------------------------------------------------------

-- Detect multi-hop money transfers between 2 and 4 hops with cycle filtering
SELECT initial_acct,
       terminal_acct,
       hop_count,
       is_cycle_free,
       first_vertex,
       last_vertex
  FROM GRAPH_TABLE (
    `finance_network_02_str.FinGraph`
    MATCH p = (a:Account)-[t:Transfers]->{2, 4}(b:Account)
    WHERE a.account_id != b.account_id
      AND IS_ACYCLIC(p)
    RETURN a.account_id             AS initial_acct,
           b.account_id             AS terminal_acct,
           PATH_LENGTH(p)           AS hop_count,
           IS_ACYCLIC(p)            AS is_cycle_free,
           ELEMENT_ID(PATH_FIRST(p)) AS first_vertex,
           ELEMENT_ID(PATH_LAST(p))  AS last_vertex
  )
 ORDER BY hop_count, initial_acct;

-- ----------------------------------------------------------------------------
-- 5. Shortest and Cheapest Path Search Modes
-- ----------------------------------------------------------------------------

-- Find any shortest path connecting two specific accounts
SELECT start_id, end_id, shortest_hops
  FROM GRAPH_TABLE (
    `finance_network_02_str.FinGraph`
    MATCH ANY SHORTEST (src:Account)-[t:Transfers]->{1, 5}(dst:Account)
    WHERE src.account_id = 1001 AND dst.account_id = 2005
    RETURN src.account_id AS start_id,
           dst.account_id AS end_id,
           PATH_LENGTH(t) AS shortest_hops
  );

-- Find cheapest transfer route evaluating accumulated transfer amounts
SELECT src_id, dst_id, min_fee_total
  FROM GRAPH_TABLE (
    `finance_network_02_str.FinGraph`
    MATCH ANY CHEAPEST (src:Account)-[t:Transfers COST t.transfer_amt]->{1, 4}(dst:Account)
    WHERE src.account_id = 1001 AND dst.account_id = 2005
    RETURN src.account_id    AS src_id,
           dst.account_id    AS dst_id,
           SUM(t.transfer_amt) AS min_fee_total
  );

-- ----------------------------------------------------------------------------
-- 6. Graph Predicates and Cycle Detection
-- ----------------------------------------------------------------------------

-- Identify triangular transfer loops where all three accounts are distinct
SELECT acct_a, acct_b, acct_c
  FROM GRAPH_TABLE (
    `finance_network_02_str.FinGraph`
    MATCH (a:Account)-[t1:Transfers]->(b:Account)-[t2:Transfers]->(c:Account)-[t3:Transfers]->(a)
    WHERE ALL_DIFFERENT(a, b, c)
      AND ALL_DIFFERENT(t1, t2, t3)
    RETURN a.account_id AS acct_a,
           b.account_id AS acct_b,
           c.account_id AS acct_c
  );

-- ----------------------------------------------------------------------------
-- 7. GoogleSQL Pipe Syntax Integration
-- ----------------------------------------------------------------------------

-- Stream GRAPH_TABLE results into linear pipe aggregations
FROM GRAPH_TABLE (
  `finance_network_02_str.FinGraph`
  MATCH (cust:Customer)-[:Owns]->(acct:Account)-[tx:Transfers]->(target:Account)
  WHERE cust.city_name = 'New York'
  RETURN cust.customer_id AS customer_id,
         cust.full_name   AS customer_name,
         tx.transfer_amt  AS transfer_amt
)
|> WHERE transfer_amt >= 5000.00
|> AGGREGATE
     COUNT(*)          AS outbound_tx_count,
     SUM(transfer_amt) AS total_outbound_amt
   GROUP BY customer_id, customer_name
|> WHERE outbound_tx_count >= 3
|> ORDER BY total_outbound_amt DESC;

-- ----------------------------------------------------------------------------
-- 8. Catalog Introspection via INFORMATION_SCHEMA
-- ----------------------------------------------------------------------------

SELECT property_graph_name,
       property_graph_catalog,
       property_graph_schema,
       last_modified_time
  FROM `finance_network_02_str.INFORMATION_SCHEMA.PROPERTY_GRAPHS`
 WHERE property_graph_name = 'FinGraph';
